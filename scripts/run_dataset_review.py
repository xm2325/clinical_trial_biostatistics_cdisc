from __future__ import annotations

import json
from pathlib import Path

from cdisc_portfolio.io import sha256_file
from cdisc_portfolio.review import REVIEW_FILES, run_dataset_review


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    review = run_dataset_review(OUTPUT_DIR)
    review_path = OUTPUT_DIR / "analysis_dataset_review.csv"
    review.to_csv(review_path, index=False)

    required = review.loc[review["required"].eq(True)]
    all_required_passed = bool(required["passed"].all())
    reviewed_sha256 = {
        name: sha256_file(OUTPUT_DIR / filename)
        for name, filename in REVIEW_FILES.items()
    }
    metrics = {
        "analysis_version": "0.9.0",
        "required_review_checks": int(len(required)),
        "required_review_passed": int(required["passed"].sum()),
        "all_required_review_passed": all_required_passed,
        "review_areas": sorted(review["area"].unique().tolist()),
        "reviewed_outputs_sha256": reviewed_sha256,
    }
    metrics_path = OUTPUT_DIR / "analysis_dataset_review_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failed = required.loc[~required["passed"]]
    summary = [
        "# Analysis-dataset and TLF review summary",
        "",
        "- Version: 0.9.0.",
        "- Status: Independent portfolio reviewer gate over generated analysis datasets and TLF-style outputs; not sponsor/CRO production review or independent second-programmer sign-off.",
        f"- Required reviewer checks: {int(required['passed'].sum())}/{len(required)} passed.",
        f"- Review areas: {', '.join(sorted(review['area'].unique()))}.",
        f"- Reviewed generated files: {len(REVIEW_FILES)}; SHA256 recorded for every reviewed file.",
        "",
        "The gate checks cross-dataset parentage, treatment/population consistency, ACTOT baseline/change derivations, exact MMRM source-row traceability, and safety/efficacy TLF denominator reconciliation.",
    ]
    if not failed.empty:
        summary.extend(["", "## Failed required checks"])
        for row in failed.itertuples():
            summary.append(f"- {row.check}: {row.detail}")
    (OUTPUT_DIR / "analysis_dataset_review_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    print((OUTPUT_DIR / "analysis_dataset_review_summary.md").read_text(encoding="utf-8"))
    if not all_required_passed:
        raise SystemExit("Required analysis-dataset/TLF reviewer checks failed")


if __name__ == "__main__":
    main()

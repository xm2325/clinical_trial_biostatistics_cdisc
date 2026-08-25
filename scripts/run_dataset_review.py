from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.contracts import load_dataset_contracts, review_dataset_contracts  # noqa: E402
from cdisc_portfolio.io import sha256_file  # noqa: E402
from cdisc_portfolio.review import REVIEW_FILES, load_review_frames, review_frames  # noqa: E402

OUTPUT_DIR = ROOT / "outputs"
CONTRACT_PATH = ROOT / "spec" / "analysis_dataset_contracts.json"


def main() -> None:
    # v0.23 repair boundary: T20/T21/T22 have just run using the temporary
    # planned-randomisation MI inputs. Restore the byte-preserved original
    # actual-treatment-labelled analysis files before any generic dataset review,
    # then verify the executed rbmi target counts and reference-based evidence.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "restore_mi_assignment_inputs.py")],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_mi_assignment_audit.py")],
        check=True,
    )

    frames = load_review_frames(OUTPUT_DIR)
    review = review_frames(frames)
    contract_spec = load_dataset_contracts(CONTRACT_PATH)
    contract_review = review_dataset_contracts(frames, contract_spec)
    review = pd.concat([review, contract_review], ignore_index=True)

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
        "dataset_contract_sha256": sha256_file(CONTRACT_PATH),
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
        "- Machine-readable dataset contracts: ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM; contract specification SHA256 recorded.",
        "",
        "The gate checks metadata contracts, cross-dataset parentage, treatment/population consistency, ACTOT baseline/change derivations, exact MMRM source-row traceability, and safety/efficacy TLF denominator reconciliation.",
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

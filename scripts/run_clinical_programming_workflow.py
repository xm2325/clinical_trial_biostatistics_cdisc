from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.clinical_programming_workflow import (  # noqa: E402
    run_clinical_programming_workflow,
)

OUT = ROOT / "outputs"
SPEC_PATH = ROOT / "spec" / "clinical_programming_workflow_v0_25.csv"


def main() -> None:
    result = run_clinical_programming_workflow(ROOT, SPEC_PATH)
    OUT.mkdir(parents=True, exist_ok=True)

    result.checks.to_csv(OUT / "clinical_programming_workflow_qc.csv", index=False)
    result.release_manifest.to_csv(
        OUT / "clinical_programming_release_manifest.csv",
        index=False,
    )
    (OUT / "clinical_programming_workflow_metrics.json").write_text(
        json.dumps(result.metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    failed = result.checks.loc[
        result.checks["required"].eq(True) & ~result.checks["passed"].eq(True)
    ]
    lines = [
        "# Clinical programming workflow summary",
        "",
        "- Version: 0.25.0.",
        f"- Controlled packages: {result.metrics['program_packages']}.",
        f"- Analysis-dataset packages: {result.metrics['analysis_dataset_packages']}.",
        f"- TLF packages: {result.metrics['tlf_packages']}.",
        f"- Packages with cross-language reconstruction: {result.metrics['cross_language_packages']}.",
        f"- Required checks: {result.metrics['required_passed']}/{result.metrics['required_checks']} passed.",
        f"- Controlled claim: `{result.metrics['controlled_claim'] or 'NOT_READY'}`.",
        "",
        "The gate ties declared SDTM/source domains and analysis inputs to controlled production programs, specifications, generated deliverables, key/column contracts, QC evidence and SHA256 release identities.",
        "",
        "Evidence boundary: independent public-data portfolio evidence only. It is not sponsor/CRO production, formal second-programmer sign-off, formal ADaM conformance, or regulatory submission readiness.",
    ]
    if not failed.empty:
        lines.extend(["", "## Failed required checks"])
        for row in failed.itertuples(index=False):
            lines.append(f"- {row.program_id} / {row.check}: {row.detail}")
    (OUT / "clinical_programming_workflow_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result.metrics, indent=2, sort_keys=True))
    print((OUT / "clinical_programming_workflow_summary.md").read_text(encoding="utf-8"))

    if not result.metrics["all_required_passed"]:
        raise SystemExit("Clinical programming workflow gate failed")


if __name__ == "__main__":
    main()

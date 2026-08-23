from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mmrm_validation import validate_mmrm_cross_package


OUT = ROOT / "outputs"
SPEC_PATH = ROOT / "spec" / "mmrm_cross_package_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    spec_bytes = SPEC_PATH.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    primary_path = ROOT / spec["primary_source"]
    independent_path = ROOT / spec["independent_source"]
    primary_analysis_path = ROOT / spec["primary_analysis_dataset"]
    independent_analysis_path = ROOT / spec["independent_analysis_dataset"]
    required_paths = {
        "primary MMRM contrast source": primary_path,
        "independent MMRM contrast source": independent_path,
        "primary MMRM analysis dataset": primary_analysis_path,
        "independent MMRM analysis dataset": independent_analysis_path,
    }
    for label, path in required_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {label}: {path}")

    primary = pd.read_csv(primary_path)
    independent = pd.read_csv(independent_path)
    primary_analysis = pd.read_csv(primary_analysis_path)
    independent_analysis = pd.read_csv(independent_analysis_path)
    result = validate_mmrm_cross_package(
        primary,
        independent,
        primary_analysis,
        independent_analysis,
        spec,
    )
    result.metrics.update(
        {
            "validation_spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
            "primary_source_sha256": _sha256(primary_path),
            "independent_source_sha256": _sha256(independent_path),
            "primary_analysis_dataset_sha256": _sha256(primary_analysis_path),
            "independent_analysis_dataset_sha256": _sha256(independent_analysis_path),
        }
    )

    OUT.mkdir(parents=True, exist_ok=True)
    comparison_path = OUT / "mmrm_cross_package_validation.csv"
    qc_path = OUT / "mmrm_cross_package_qc.csv"
    metrics_path = OUT / "mmrm_cross_package_validation_metrics.json"
    summary_path = OUT / "mmrm_cross_package_validation_summary.md"

    result.comparison.to_csv(comparison_path, index=False)
    result.qc.to_csv(qc_path, index=False)
    metrics_path.write_text(json.dumps(result.metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# MMRM cross-package validation summary",
        "",
        "- Primary implementation: `mmrm::mmrm`, REML, unstructured covariance, Satterthwaite inference.",
        "- Independent reconstruction: `nlme::gls`, REML, `corSymm + varIdent` unstructured covariance.",
        "- Validation scope: independent analysis-row identity plus Week 24 active-vs-placebo point estimates and model-based standard errors.",
        "- Degrees of freedom and p-values are not compared because the inferential df methods differ by design.",
        f"- Primary/independent analysis rows: {result.metrics['primary_analysis_records']}/{result.metrics['independent_analysis_records']}.",
        f"- Primary/independent analysis subjects: {result.metrics['primary_analysis_subjects']}/{result.metrics['independent_analysis_subjects']}.",
        f"- Analysis key sets match: {result.metrics['analysis_key_sets_match']}.",
        f"- Analysis exact-field mismatch rows: {result.metrics['analysis_exact_mismatch_rows']}.",
        f"- Analysis numeric-field mismatch rows: {result.metrics['analysis_numeric_mismatch_rows']}.",
        f"- Maximum analysis-row numeric absolute difference: {result.metrics['max_analysis_numeric_abs_difference']}.",
        f"- Estimate absolute tolerance: {result.metrics['estimate_abs_tolerance']:.6g}.",
        f"- SE absolute tolerance: {result.metrics['se_abs_tolerance']:.6g}.",
        f"- Required QC: {result.metrics['required_passed']}/{result.metrics['required_checks']} passed.",
        f"- Maximum estimate absolute difference: {result.metrics['max_estimate_abs_difference']}.",
        f"- Maximum SE absolute difference: {result.metrics['max_se_abs_difference']}.",
        f"- Validation spec SHA256: `{result.metrics['validation_spec_sha256']}`.",
        f"- Primary contrast source SHA256: `{result.metrics['primary_source_sha256']}`.",
        f"- Independent contrast source SHA256: `{result.metrics['independent_source_sha256']}`.",
        f"- Primary analysis-dataset SHA256: `{result.metrics['primary_analysis_dataset_sha256']}`.",
        f"- Independent analysis-dataset SHA256: `{result.metrics['independent_analysis_dataset_sha256']}`.",
        "",
        "## Comparison",
        "",
    ]
    if result.comparison.empty:
        lines.append("Comparison unavailable.")
    else:
        for row in result.comparison.itertuples(index=False):
            lines.append(
                f"- {row.contrast}: primary estimate={row.primary_estimate:.6f}, independent={row.independent_estimate:.6f}, "
                f"|diff|={row.estimate_abs_difference:.6g}; primary SE={row.primary_SE:.6f}, "
                f"independent SE={row.independent_SE:.6f}, |diff|={row.se_abs_difference:.6g}; "
                f"pass={'yes' if row.cross_package_pass else 'no'}."
            )
    lines.extend(
        [
            "",
            "Evidence boundary: this is a distinct-package re-programming exercise by the portfolio author, not formal independent second-programmer validation or sponsor/regulatory production QC.",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not result.metrics["all_required_passed"]:
        failed = result.qc[(result.qc["required"]) & (~result.qc["passed"])]
        raise SystemExit("Cross-package MMRM validation failed: " + "; ".join(failed["check"].tolist()))


if __name__ == "__main__":
    main()

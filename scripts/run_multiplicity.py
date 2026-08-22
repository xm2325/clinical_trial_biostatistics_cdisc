from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.multiplicity import evaluate_primary_multiplicity


SPEC_PATH = ROOT / "spec" / "multiplicity.json"
PLANNING_PATH = ROOT / "spec" / "protocol_design.json"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    spec_bytes = SPEC_PATH.read_bytes()
    planning_bytes = PLANNING_PATH.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    planning = json.loads(planning_bytes.decode("utf-8"))

    source_path = ROOT / spec["source_output"]
    if not source_path.is_file():
        raise SystemExit(f"Missing primary MMRM contrast output: {source_path}")
    contrasts = pd.read_csv(source_path)

    result = evaluate_primary_multiplicity(spec, planning, contrasts)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    decision_path = OUTPUT_DIR / "table23_actot_multiplicity.csv"
    qc_path = OUTPUT_DIR / "multiplicity_qc.csv"
    metrics_path = OUTPUT_DIR / "multiplicity_metrics.json"
    summary_path = OUTPUT_DIR / "multiplicity_summary.md"

    result.decisions.to_csv(decision_path, index=False)
    result.qc.to_csv(qc_path, index=False)

    required = result.qc.loc[result.qc["required"]]
    required_passed = int(required["passed"].sum())
    required_total = int(len(required))
    all_passed = bool(required["passed"].all())

    decisions = result.decisions
    metrics = {
        "analysis_version": spec["version"],
        "multiplicity_spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "planning_spec_sha256": hashlib.sha256(planning_bytes).hexdigest(),
        "family_id": spec["family"]["id"],
        "method": spec["family"]["method"],
        "family_alpha": float(spec["family"]["family_alpha"]),
        "comparison_count": int(spec["decision_rule"]["comparison_count"]),
        "local_alpha": float(spec["decision_rule"]["local_alpha"]),
        "hypotheses": int(len(decisions)),
        "familywise_rejections": int(decisions["reject_familywise"].sum()) if len(decisions) else 0,
        "required_qc_passed": required_passed,
        "required_qc_checks": required_total,
        "all_required_qc_passed": all_passed,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ACTOT primary multiplicity decision summary",
        "",
        f"- Analysis version: {spec['version']}.",
        f"- Family: {spec['family']['id']}.",
        f"- Method: {spec['family']['method']}.",
        f"- Family-wise two-sided alpha: {metrics['family_alpha']:.3f}.",
        f"- Controlled comparisons: {metrics['comparison_count']}; local Bonferroni alpha: {metrics['local_alpha']:.3f}.",
        f"- Family-wise rejections: {metrics['familywise_rejections']}/{metrics['hypotheses']}.",
        f"- Required multiplicity QC: {required_passed}/{required_total} passed.",
        "",
        "| Hypothesis | Contrast | Raw p | Adjusted p | Reject family-wise |",
        "|---|---|---:|---:|---|",
    ]
    for row in decisions.itertuples(index=False):
        lines.append(
            f"| {row.hypothesis_id} | {row.contrast} | {row.raw_p_value:.6f} | "
            f"{row.adjusted_p_value:.6f} | {'Yes' if row.reject_familywise else 'No'} |"
        )
    lines.extend(
        [
            "",
            "This layer applies the Bonferroni family already declared in the illustrative protocol-design specification to the primary Week 24 unstructured MMRM contrasts. It does not change the underlying MMRM and does not place sensitivity analyses in the confirmatory family.",
            "",
            f"Evidence boundary: {spec['evidence_boundary']}",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(summary_path.read_text(encoding="utf-8"))
    if not all_passed:
        raise SystemExit("Required multiplicity QC failed")


if __name__ == "__main__":
    main()

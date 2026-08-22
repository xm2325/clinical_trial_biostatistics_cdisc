from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.design import evaluate_continuous_design


SPEC_PATH = ROOT / "spec" / "protocol_design.json"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    spec_bytes = SPEC_PATH.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    result = evaluate_continuous_design(spec)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scenarios_path = OUTPUT_DIR / "protocol_design_scenarios.csv"
    qc_path = OUTPUT_DIR / "protocol_design_qc.csv"
    metrics_path = OUTPUT_DIR / "protocol_design_metrics.json"
    summary_path = OUTPUT_DIR / "protocol_design_summary.md"

    result.scenarios.to_csv(scenarios_path, index=False)
    result.qc.to_csv(qc_path, index=False)

    required = result.qc.loc[result.qc["required"]]
    required_passed = int(required["passed"].sum())
    required_total = int(len(required))
    all_passed = bool(required["passed"].all())

    metrics = {
        "analysis_version": spec["analysis_version"],
        "design_spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "scenario_count": int(len(result.scenarios)),
        "required_qc_passed": required_passed,
        "required_qc_checks": required_total,
        "all_required_qc_passed": all_passed,
        "family_alpha": float(spec["multiplicity"]["family_alpha"]),
        "per_comparison_alpha": float(result.scenarios["per_comparison_alpha"].iloc[0]),
        "dropout_rate": float(spec["dropout_rate"]),
        "common_sd": float(spec["common_sd"]),
        "minimum_total_randomised": int(result.scenarios["total_randomised"].min()),
        "maximum_total_randomised": int(result.scenarios["total_randomised"].max()),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Protocol design and sample-size summary",
        "",
        f"- Analysis version: {spec['analysis_version']}.",
        f"- Status: {spec['design_status']}",
        f"- Endpoint: {spec['endpoint']['parameter']} {spec['endpoint']['summary']} at {spec['endpoint']['timepoint']}.",
        f"- Family-wise two-sided alpha: {metrics['family_alpha']:.3f}; Bonferroni per-comparison alpha: {metrics['per_comparison_alpha']:.3f} for two active-versus-placebo comparisons.",
        f"- Common planning SD: {metrics['common_sd']:.1f}; anticipated dropout: {100 * metrics['dropout_rate']:.0f}%.",
        f"- Required design QC: {required_passed}/{required_total} passed.",
        "",
        "| Scenario | Effect | Target power | Evaluable N/arm | Randomised N/arm | Total randomised | Achieved power |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result.scenarios.itertuples(index=False):
        lines.append(
            f"| {row.scenario_id} | {row.effect:.1f} | {row.target_power:.0%} | "
            f"{row.evaluable_n_per_arm} | {row.randomised_n_per_arm} | {row.total_randomised} | "
            f"{row.achieved_power_at_evaluable_n:.3f} |"
        )
    lines.extend(
        [
            "",
            "The calculation is a normal-approximation planning demonstration. It is not presented as the original trial's sample-size calculation and does not use the observed treatment effect as a prospective assumption.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(summary_path.read_text(encoding="utf-8"))
    if not all_passed:
        raise SystemExit("Required protocol-design QC failed")


if __name__ == "__main__":
    main()

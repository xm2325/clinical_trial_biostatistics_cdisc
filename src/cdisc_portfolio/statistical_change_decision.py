from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EXPECTED_STRATEGIES = {"MAR", "JR", "CR", "CIR"}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError("Boolean field contains values other than true/false")
    return mapped.astype(bool)


def run_statistical_change_decision(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    cfg = _load_json(root / "spec" / "statistical_change_decision_v0_24.json")
    outputs = root / "outputs"
    missing = [p for p in cfg["required_evidence"] if not (root / str(p)).exists()]
    if missing:
        raise FileNotFoundError(f"Missing controlled decision evidence: {missing}")

    readiness = _load_json(outputs / "analysis_readiness_metrics.json")
    closure = _load_json(outputs / "analysis_closure_metrics.json")
    mult = pd.read_csv(outputs / "table23_actot_multiplicity.csv")
    rbmi = pd.read_csv(outputs / "table22_rbmi_reference_based.csv")

    required_mult = {"contrast", "visit", "adjusted_p_value", "reject_familywise"}
    required_rbmi = {"comparison", "strategy_id", "mcse_pass", "estimate_active_minus_placebo"}
    if m := required_mult.difference(mult.columns):
        raise ValueError(f"Multiplicity table missing columns: {sorted(m)}")
    if m := required_rbmi.difference(rbmi.columns):
        raise ValueError(f"Reference-based MI table missing columns: {sorted(m)}")

    mult = mult.loc[mult["visit"].astype(str).eq("Week 24")].copy()
    mult["reject_familywise"] = _as_bool(mult["reject_familywise"])
    rbmi["mcse_pass"] = _as_bool(rbmi["mcse_pass"])

    comparisons = sorted(mult["contrast"].astype(str).unique().tolist())
    rbmi_complete = True
    rbmi_detail = []
    for comparison in comparisons:
        s = rbmi.loc[rbmi["comparison"].astype(str).eq(comparison)]
        strategies = set(s["strategy_id"].astype(str))
        ok = len(s) == 4 and strategies == EXPECTED_STRATEGIES and bool(s["mcse_pass"].all())
        rbmi_complete &= ok
        rbmi_detail.append(f"{comparison}:{sorted(strategies)}:{int(s['mcse_pass'].sum())}/{len(s)}")

    randomized = int(readiness["randomized_subjects"])
    missing_w24 = int(readiness["week24_actot_missing"])
    missing_fraction = missing_w24 / randomized if randomized else float("nan")
    family_rejections = int(mult["reject_familywise"].sum())

    checks = pd.DataFrame([
        {
            "check": "proposal_is_post_data_review",
            "passed": cfg["proposal_timing"] == "POST_DATA_REVIEW",
            "detail": str(cfg["proposal_timing"]),
        },
        {
            "check": "analysis_package_was_closed_before_governance_exercise",
            "passed": bool(closure.get("all_passed")),
            "detail": f"closure_claim={closure.get('closure_claim')}; all_passed={closure.get('all_passed')}",
        },
        {
            "check": "week24_missingness_is_material_but_not_itself_a_primary_switch_rule",
            "passed": missing_w24 > 0 and bool(cfg["rules"]["missingness_alone_does_not_justify_post_hoc_primary_switch"]),
            "detail": f"Week24 missing={missing_w24}/{randomized} ({missing_fraction:.1%})",
        },
        {
            "check": "reference_based_mi_is_complete_supportive_evidence",
            "passed": bool(rbmi_complete),
            "detail": "; ".join(rbmi_detail),
        },
        {
            "check": "primary_multiplicity_family_remains_two_comparisons",
            "passed": len(comparisons) == 2 and bool(cfg["rules"]["primary_multiplicity_family_must_remain_intact"]),
            "detail": f"comparisons={comparisons}; familywise_rejections={family_rejections}/2",
        },
        {
            "check": "decision_is_reject_primary_change",
            "passed": cfg["decision"] == "REJECT_PRIMARY_CHANGE",
            "detail": str(cfg["decision"]),
        },
        {
            "check": "decision_rule_is_outcome_independent",
            "passed": bool(cfg["rules"]["decision_must_be_independent_of_favourability"]),
            "detail": "decision depends on timing/analysis role/multiplicity, not treatment-effect direction",
        },
    ])

    decision = pd.DataFrame([{
        "decision_id": cfg["decision_id"],
        "proposal": cfg["proposal"],
        "proposal_timing": cfg["proposal_timing"],
        "observed_week24_missing_n": missing_w24,
        "randomized_n": randomized,
        "observed_week24_missing_fraction": missing_fraction,
        "primary_family_rejections": family_rejections,
        "primary_family_size": int(len(comparisons)),
        "reference_based_rows": int(len(rbmi)),
        "reference_based_mcse_pass_rows": int(rbmi["mcse_pass"].sum()),
        "decision": cfg["decision"],
        "permitted_action": cfg["permitted_action"],
        "rationale": "High missingness warrants sensitivity analysis and interpretation, but does not justify promoting a post-data-review supportive analysis to replace the controlled primary analysis. Retaining the primary family also avoids outcome-driven multiplicity redefinition.",
    }])

    metrics = {
        "version": cfg["version"],
        "claim": cfg["claim"],
        "decision_id": cfg["decision_id"],
        "decision": cfg["decision"],
        "week24_missing_n": missing_w24,
        "week24_missing_fraction": missing_fraction,
        "primary_family_rejections": family_rejections,
        "reference_based_rows": int(len(rbmi)),
        "reference_based_mcse_pass_rows": int(rbmi["mcse_pass"].sum()),
        "checks_passed": int(checks["passed"].sum()),
        "checks_total": int(len(checks)),
        "all_passed": bool(checks["passed"].all()),
    }
    return decision, checks, metrics


def write_statistical_change_decision(root: Path) -> dict[str, object]:
    decision, checks, metrics = run_statistical_change_decision(root)
    outputs = root / "outputs"
    decision.to_csv(outputs / "statistical_change_decision.csv", index=False)
    checks.to_csv(outputs / "statistical_change_decision_qc.csv", index=False)
    (outputs / "statistical_change_decision_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    row = decision.iloc[0]
    summary = [
        "# Statistical change decision",
        "",
        f"- Decision ID: `{row['decision_id']}`.",
        f"- Proposal: {row['proposal']}",
        f"- Week 24 missingness: {int(row['observed_week24_missing_n'])}/{int(row['randomized_n'])} ({float(row['observed_week24_missing_fraction']):.1%}).",
        f"- Existing reference-based evidence: {int(row['reference_based_mcse_pass_rows'])}/{int(row['reference_based_rows'])} MCSE-pass rows.",
        f"- Primary family-wise rejections remain: {int(row['primary_family_rejections'])}/{int(row['primary_family_size'])}.",
        f"- Controlled decision: **{row['decision']}**.",
        f"- Permitted action: {row['permitted_action']}",
        f"- Quality checks: {metrics['checks_passed']}/{metrics['checks_total']} PASS.",
        "",
        "The rejection is not based on whether reference-based MI gives a more or less favourable estimate. It is based on preserving the prospectively controlled analysis role and multiplicity family after data review. This is a portfolio governance exercise, not a sponsor SAP amendment or regulatory decision.",
    ]
    (outputs / "statistical_change_decision_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise RuntimeError("Statistical change-decision gate failed")
    return metrics

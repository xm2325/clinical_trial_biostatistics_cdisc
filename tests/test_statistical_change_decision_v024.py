from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cdisc_portfolio.statistical_change_decision import run_statistical_change_decision


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.24.0",
        "claim": "PORTFOLIO_STATISTICAL_CHANGE_DECISION_READY",
        "decision_id": "SCD-001",
        "proposal": "Replace primary MMRM with reference-based MI because missingness is high.",
        "proposal_timing": "POST_DATA_REVIEW",
        "current_primary_analysis": "MMRM",
        "proposed_primary_analysis": "Reference-based MI",
        "required_current_role": "CONFIRMATORY_PRIMARY",
        "required_proposed_role": "SUPPORTIVE_SENSITIVITY",
        "decision": "REJECT_PRIMARY_CHANGE",
        "permitted_action": "Retain primary MMRM; use RBMI as sensitivity.",
        "rules": {
            "missingness_alone_does_not_justify_post_hoc_primary_switch": True,
            "supportive_sensitivity_cannot_be_promoted_post_hoc_to_rescue_primary": True,
            "primary_multiplicity_family_must_remain_intact": True,
            "decision_must_be_independent_of_favourability": True,
            "existing_sensitivity_evidence_must_be_complete": True
        },
        "required_evidence": [
            "outputs/analysis_readiness_metrics.json",
            "outputs/table23_actot_multiplicity.csv",
            "outputs/table22_rbmi_reference_based.csv",
            "outputs/rbmi_reference_qc.csv",
            "outputs/analysis_closure_metrics.json"
        ],
        "interpretation_boundary": ["test"]
    }
    (tmp_path / "spec" / "statistical_change_decision_v0_24.json").write_text(json.dumps(cfg))
    (tmp_path / "outputs" / "analysis_readiness_metrics.json").write_text(json.dumps({
        "randomized_subjects": 254,
        "week24_actot_missing": 138
    }))
    (tmp_path / "outputs" / "analysis_closure_metrics.json").write_text(json.dumps({
        "all_passed": True,
        "closure_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE"
    }))
    pd.DataFrame([
        {"contrast": "Low vs Placebo", "visit": "Week 24", "adjusted_p_value": 0.34, "reject_familywise": False},
        {"contrast": "High vs Placebo", "visit": "Week 24", "adjusted_p_value": 0.84, "reject_familywise": False}
    ]).to_csv(tmp_path / "outputs" / "table23_actot_multiplicity.csv", index=False)
    rows = []
    for comp in ["Low vs Placebo", "High vs Placebo"]:
        for strategy in ["MAR", "JR", "CR", "CIR"]:
            rows.append({
                "comparison": comp,
                "strategy_id": strategy,
                "mcse_pass": True,
                "estimate_active_minus_placebo": -1.0
            })
    pd.DataFrame(rows).to_csv(tmp_path / "outputs" / "table22_rbmi_reference_based.csv", index=False)
    pd.DataFrame([{"check": "mcse", "passed": True}]).to_csv(tmp_path / "outputs" / "rbmi_reference_qc.csv", index=False)
    return tmp_path


def test_post_hoc_primary_switch_is_rejected_with_complete_sensitivity_evidence(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    decision, checks, metrics = run_statistical_change_decision(root)
    assert metrics["all_passed"] is True
    assert metrics["decision"] == "REJECT_PRIMARY_CHANGE"
    assert metrics["week24_missing_n"] == 138
    assert metrics["reference_based_mcse_pass_rows"] == 8
    assert decision.iloc[0]["decision"] == "REJECT_PRIMARY_CHANGE"
    assert checks["passed"].all()


def test_incomplete_reference_based_evidence_blocks_decision_gate(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    rbmi = pd.read_csv(root / "outputs" / "table22_rbmi_reference_based.csv")
    rbmi = rbmi.loc[~((rbmi["comparison"] == "High vs Placebo") & (rbmi["strategy_id"] == "CIR"))]
    rbmi.to_csv(root / "outputs" / "table22_rbmi_reference_based.csv", index=False)
    _, checks, metrics = run_statistical_change_decision(root)
    assert metrics["all_passed"] is False
    row = checks.loc[checks["check"].eq("reference_based_mi_is_complete_supportive_evidence")].iloc[0]
    assert bool(row["passed"]) is False

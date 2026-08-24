from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.statistical_review_queries import (
    assess_statistical_review_queries,
    write_statistical_review_query_outputs,
)


LOW = "Xanomeline Low Dose vs Placebo"
HIGH = "Xanomeline High Dose vs Placebo"


def _json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.22.0",
        "review_claim": "PORTFOLIO_STATISTICAL_REVIEW_RESPONSE_READY",
        "required_interpretation_claim": "PORTFOLIO_STATISTICAL_INTERPRETATION_READY",
        "required_query_ids": ["SRQ-001", "SRQ-002", "SRQ-003", "SRQ-004", "SRQ-005"],
        "required_inputs": [
            "outputs/analysis_readiness_metrics.json",
            "outputs/csr_interpretation_metrics.json",
            "outputs/csr_interpretation_extension_metrics.json",
            "outputs/csr_conclusion_matrix.csv",
            "outputs/csr_fixed_delta_context.csv",
            "outputs/table23_actot_multiplicity.csv",
            "outputs/table22_rbmi_reference_based.csv",
            "outputs/table7_teae_risk_difference.csv",
            "outputs/table25_retention_pairwise.csv",
            "outputs/adtte_retention_style.csv",
        ],
        "rules": {
            "primary_response_must_follow_familywise_decision": True,
            "missing_data_response_must_report_missingness_and_tipping": True,
            "treatment_mismatch_response_must_reconcile_to_analysis_data": True,
            "safety_response_must_remain_descriptive": True,
            "retention_response_must_remain_exploratory": True,
        },
        "prohibited_claim_fragments": [
            "demonstrated efficacy",
            "confirmed efficacy",
            "statistically significant efficacy",
            "fully robust",
            "proves safety",
            "benefit-risk is positive",
            "regulatory ready",
            "submission ready",
            "sponsor approved",
        ],
        "evidence_boundary": "test portfolio boundary",
    }
    _json(tmp_path / "spec" / "statistical_review_queries_v0_22.json", cfg)
    _json(
        tmp_path / "outputs" / "analysis_readiness_metrics.json",
        {
            "all_passed": True,
            "randomized_subjects": 254,
            "week24_actot_observed": 116,
            "week24_actot_missing": 138,
            "planned_actual_treatment_mismatches": 1,
        },
    )
    _json(
        tmp_path / "outputs" / "csr_interpretation_metrics.json",
        {
            "all_passed": True,
            "interpretation_claim": "PORTFOLIO_STATISTICAL_INTERPRETATION_READY",
            "primary_familywise_rejections": 0,
            "primary_hypotheses": 2,
        },
    )
    _json(
        tmp_path / "outputs" / "csr_interpretation_extension_metrics.json",
        {"all_passed": True},
    )

    pd.DataFrame(
        [
            {"contrast": LOW, "adjusted_p_value": 0.338669, "reject_familywise": False},
            {"contrast": HIGH, "adjusted_p_value": 0.843940, "reject_familywise": False},
        ]
    ).to_csv(tmp_path / "outputs" / "table23_actot_multiplicity.csv", index=False)

    rbmi = []
    for comparison in (LOW, HIGH):
        for strategy in ("MAR", "JR", "CR", "CIR"):
            rbmi.append({"comparison": comparison, "strategy_id": strategy, "mcse_pass": True})
    pd.DataFrame(rbmi).to_csv(tmp_path / "outputs" / "table22_rbmi_reference_based.csv", index=False)

    pd.DataFrame(
        [
            {"section": "FIXED_DELTA_SENSITIVITY", "comparison": LOW, "estimate": 1.5621},
            {"section": "FIXED_DELTA_SENSITIVITY", "comparison": HIGH, "estimate": 1.0333},
        ]
    ).to_csv(tmp_path / "outputs" / "csr_fixed_delta_context.csv", index=False)

    pd.DataFrame(
        [
            {"comparison": LOW, "risk_difference": 0.12},
            {"comparison": HIGH, "risk_difference": 0.19},
        ]
    ).to_csv(tmp_path / "outputs" / "table7_teae_risk_difference.csv", index=False)

    pd.DataFrame(
        [
            {
                "comparison": LOW,
                "hazard_ratio": 3.1,
                "interpretation": "HR > 1 indicates a higher study-discontinuation hazard than placebo; exploratory only",
            },
            {
                "comparison": HIGH,
                "hazard_ratio": 2.9,
                "interpretation": "HR > 1 indicates a higher study-discontinuation hazard than placebo; exploratory only",
            },
        ]
    ).to_csv(tmp_path / "outputs" / "table25_retention_pairwise.csv", index=False)

    pd.DataFrame(
        [
            {"USUBJID": "01", "TRT01P": "Placebo", "TRT01A": "Placebo"},
            {"USUBJID": "02", "TRT01P": "Low", "TRT01A": "High"},
        ]
    ).to_csv(tmp_path / "outputs" / "adtte_retention_style.csv", index=False)

    pd.DataFrame(
        [
            {"section": "PRIMARY_EFFICACY", "analysis_role": "CONFIRMATORY_DECISION", "decision": "NO_FAMILYWISE_REJECTION"},
            {"section": "PRIMARY_EFFICACY", "analysis_role": "CONFIRMATORY_DECISION", "decision": "NO_FAMILYWISE_REJECTION"},
            {"section": "SAFETY", "analysis_role": "DESCRIPTIVE_SAFETY", "decision": "DESCRIPTIVE_ONLY"},
            {"section": "SAFETY", "analysis_role": "DESCRIPTIVE_SAFETY", "decision": "DESCRIPTIVE_ONLY"},
            {"section": "RETENTION", "analysis_role": "EXPLORATORY_RETENTION", "decision": "EXPLORATORY_ONLY"},
            {"section": "RETENTION", "analysis_role": "EXPLORATORY_RETENTION", "decision": "EXPLORATORY_ONLY"},
        ]
    ).to_csv(tmp_path / "outputs" / "csr_conclusion_matrix.csv", index=False)
    return tmp_path


def test_happy_path_generates_five_controlled_reviewer_responses(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    metrics = write_statistical_review_query_outputs(root)
    assert metrics["all_passed"] is True
    assert metrics["query_rows"] == 5
    assert metrics["primary_familywise_rejections"] == 0
    assert metrics["week24_missing"] == 138
    assert metrics["planned_actual_treatment_mismatches"] == 1
    rows = pd.read_csv(root / "outputs" / "statistical_review_queries.csv")
    assert set(rows["query_id"]) == {"SRQ-001", "SRQ-002", "SRQ-003", "SRQ-004", "SRQ-005"}
    text = (root / "outputs" / "statistical_review_query_response.md").read_text().lower()
    assert "no confirmatory efficacy success conclusion" in text
    assert "54.3%" in text
    assert "supportive sensitivity evidence only" in text
    assert "higher discontinuation hazard" in text


def test_failed_prior_interpretation_blocks_review_pack(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    _json(
        root / "outputs" / "csr_interpretation_metrics.json",
        {
            "all_passed": False,
            "interpretation_claim": "PORTFOLIO_STATISTICAL_INTERPRETATION_READY",
            "primary_familywise_rejections": 0,
            "primary_hypotheses": 2,
        },
    )
    _, checks, metrics = assess_statistical_review_queries(root)
    assert metrics["all_passed"] is False
    assert any("v0.20 readiness and v0.21 interpretation" in row["check"] and not row["passed"] for row in checks)


def test_missingness_denominator_drift_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    readiness = json.loads((root / "outputs" / "analysis_readiness_metrics.json").read_text())
    readiness["week24_actot_missing"] = 137
    _json(root / "outputs" / "analysis_readiness_metrics.json", readiness)
    _, checks, metrics = assess_statistical_review_queries(root)
    assert metrics["all_passed"] is False
    assert any("missingness denominator reconciles" in row["check"] and not row["passed"] for row in checks)


def test_treatment_mismatch_count_drift_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    readiness = json.loads((root / "outputs" / "analysis_readiness_metrics.json").read_text())
    readiness["planned_actual_treatment_mismatches"] = 0
    _json(root / "outputs" / "analysis_readiness_metrics.json", readiness)
    _, checks, metrics = assess_statistical_review_queries(root)
    assert metrics["all_passed"] is False
    assert any("mismatch response reconciles" in row["check"] and not row["passed"] for row in checks)


def test_safety_role_promotion_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    matrix = pd.read_csv(root / "outputs" / "csr_conclusion_matrix.csv")
    matrix.loc[matrix["section"].eq("SAFETY"), "analysis_role"] = "CONFIRMATORY_SAFETY"
    matrix.to_csv(root / "outputs" / "csr_conclusion_matrix.csv", index=False)
    _, checks, metrics = assess_statistical_review_queries(root)
    assert metrics["all_passed"] is False
    assert any("safety reviewer response remains descriptive" == row["check"] and not row["passed"] for row in checks)


def test_retention_hazard_direction_error_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    retention = pd.read_csv(root / "outputs" / "table25_retention_pairwise.csv")
    retention.loc[0, "interpretation"] = "HR > 1 indicates lower discontinuation hazard; confirmatory"
    retention.to_csv(root / "outputs" / "table25_retention_pairwise.csv", index=False)
    _, checks, metrics = assess_statistical_review_queries(root)
    assert metrics["all_passed"] is False
    assert any("retention reviewer response preserves hazard direction" in row["check"] and not row["passed"] for row in checks)


def test_regulatory_review_claim_configuration_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "statistical_review_queries_v0_22.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["review_claim"] = "REGULATORY_RESPONSE_APPROVED"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="portfolio-scoped"):
        assess_statistical_review_queries(root)

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.csr_interpretation import assess_csr_interpretation, write_csr_interpretation_outputs


LOW = "Xanomeline Low Dose vs Placebo"
HIGH = "Xanomeline High Dose vs Placebo"


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.21.0",
        "primary_family_id": "ACTOT_W24_ACTIVE_VS_PLACEBO",
        "primary_visit": "Week 24",
        "primary_comparisons": [LOW, HIGH],
        "reference_based_strategies": ["MAR", "JR", "CR", "CIR"],
        "primary_estimate_tolerance": 1e-8,
        "required_closure_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE",
        "interpretation_claim": "PORTFOLIO_STATISTICAL_INTERPRETATION_READY",
        "rules": {
            "efficacy_success_requires_familywise_rejection": True,
            "sensitivity_is_supportive_not_confirmatory": True,
            "safety_is_descriptive": True,
            "retention_is_exploratory": True,
            "retention_hr_above_one_means_higher_discontinuation_hazard": True,
        },
        "required_inputs": [
            "outputs/analysis_closure_metrics.json",
            "outputs/mmrm_treatment_contrasts.csv",
            "outputs/table23_actot_multiplicity.csv",
            "outputs/table22_rbmi_reference_based.csv",
            "outputs/table7_teae_risk_difference.csv",
            "outputs/table25_retention_pairwise.csv",
        ],
        "prohibited_claim_fragments": [
            "demonstrated efficacy",
            "confirmed efficacy",
            "statistically significant efficacy",
            "submission ready",
            "regulatory ready",
        ],
        "evidence_boundary": "test portfolio boundary",
    }
    _write_json(tmp_path / "spec" / "csr_interpretation_v0_21.json", cfg)
    _write_json(
        tmp_path / "outputs" / "analysis_closure_metrics.json",
        {"closure_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE", "all_passed": True},
    )

    pd.DataFrame(
        [
            {"contrast": LOW, "AVISIT": "Week 24", "estimate": -1.6, "SE": 1.1, "lower.CL": -3.8, "upper.CL": 0.6, "p.value": 0.17, "covariance": "Unstructured"},
            {"contrast": HIGH, "AVISIT": "Week 24", "estimate": -0.9, "SE": 1.2, "lower.CL": -3.3, "upper.CL": 1.5, "p.value": 0.42, "covariance": "Unstructured"},
        ]
    ).to_csv(tmp_path / "outputs" / "mmrm_treatment_contrasts.csv", index=False)

    pd.DataFrame(
        [
            {"family_id": "ACTOT_W24_ACTIVE_VS_PLACEBO", "contrast": LOW, "visit": "Week 24", "estimate": -1.6, "raw_p_value": 0.17, "adjusted_p_value": 0.34, "reject_familywise": False, "family_alpha": 0.05},
            {"family_id": "ACTOT_W24_ACTIVE_VS_PLACEBO", "contrast": HIGH, "visit": "Week 24", "estimate": -0.9, "raw_p_value": 0.42, "adjusted_p_value": 0.84, "reject_familywise": False, "family_alpha": 0.05},
        ]
    ).to_csv(tmp_path / "outputs" / "table23_actot_multiplicity.csv", index=False)

    rbmi_rows = []
    for comparison, base in [(LOW, -1.4), (HIGH, -0.7)]:
        for i, strategy in enumerate(["MAR", "JR", "CR", "CIR"]):
            estimate = base + 0.2 * i
            rbmi_rows.append(
                {
                    "comparison": comparison,
                    "strategy_id": strategy,
                    "estimate_active_minus_placebo": estimate,
                    "ci95_lower": estimate - 2.0,
                    "ci95_upper": estimate + 2.0,
                    "p_value": 0.3 + i * 0.1,
                    "mcse_pass": True,
                }
            )
    pd.DataFrame(rbmi_rows).to_csv(
        tmp_path / "outputs" / "table22_rbmi_reference_based.csv", index=False
    )

    pd.DataFrame(
        [
            {"comparison": LOW, "risk_difference": 0.12, "ci95_lower": 0.01, "ci95_upper": 0.23, "fisher_p": 0.05},
            {"comparison": HIGH, "risk_difference": 0.19, "ci95_lower": 0.08, "ci95_upper": 0.29, "fisher_p": 0.002},
        ]
    ).to_csv(tmp_path / "outputs" / "table7_teae_risk_difference.csv", index=False)

    pd.DataFrame(
        [
            {"comparison": LOW, "hazard_ratio": 3.1, "ci95_lower": 2.0, "ci95_upper": 4.9, "cox_p_value": 0.000001, "interpretation": "HR > 1 indicates a higher study-discontinuation hazard than placebo; exploratory only"},
            {"comparison": HIGH, "hazard_ratio": 2.9, "ci95_lower": 1.9, "ci95_upper": 4.6, "cox_p_value": 0.000004, "interpretation": "HR > 1 indicates a higher study-discontinuation hazard than placebo; exploratory only"},
        ]
    ).to_csv(tmp_path / "outputs" / "table25_retention_pairwise.csv", index=False)
    return tmp_path


def test_happy_path_generates_controlled_conclusion_matrix(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    metrics = write_csr_interpretation_outputs(root)
    assert metrics["all_passed"] is True
    assert metrics["primary_familywise_rejections"] == 0
    assert metrics["conclusion_rows"] == 8
    matrix = pd.read_csv(root / "outputs" / "csr_conclusion_matrix.csv")
    assert set(matrix["section"]) == {
        "PRIMARY_EFFICACY",
        "MISSING_DATA_SENSITIVITY",
        "SAFETY",
        "RETENTION",
    }
    efficacy = matrix.loc[matrix["section"].eq("PRIMARY_EFFICACY")]
    assert set(efficacy["decision"]) == {"NO_FAMILYWISE_REJECTION"}
    text = (root / "outputs" / "csr_statistical_interpretation.md").read_text().lower()
    assert "no confirmatory efficacy success conclusion" in text
    assert "higher study-discontinuation hazard" in text


def test_failed_evidence_closure_blocks_interpretation(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    _write_json(
        root / "outputs" / "analysis_closure_metrics.json",
        {"closure_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE", "all_passed": False},
    )
    _, checks, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "v0.20 evidence closure is complete before interpretation" and not row["passed"]
        for row in checks
    )


def test_primary_estimate_drift_between_mmrm_and_multiplicity_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table23_actot_multiplicity.csv")
    table.loc[table["contrast"].eq(LOW), "estimate"] = -9.9
    table.to_csv(root / "outputs" / "table23_actot_multiplicity.csv", index=False)
    _, checks, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "multiplicity decision rows reconcile to primary MMRM estimates" and not row["passed"]
        for row in checks
    )


def test_missing_reference_based_strategy_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table22_rbmi_reference_based.csv")
    table = table.loc[~(table["comparison"].eq(LOW) & table["strategy_id"].eq("CIR"))]
    table.to_csv(root / "outputs" / "table22_rbmi_reference_based.csv", index=False)
    _, checks, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "reference-based sensitivity strategies and MCSE gates are complete" and not row["passed"]
        for row in checks
    )


def test_mcse_failure_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table22_rbmi_reference_based.csv")
    table.loc[0, "mcse_pass"] = False
    table.to_csv(root / "outputs" / "table22_rbmi_reference_based.csv", index=False)
    _, _, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is False


def test_retention_hazard_direction_misinterpretation_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table25_retention_pairwise.csv")
    table.loc[0, "interpretation"] = "HR > 1 indicates lower discontinuation hazard; confirmatory"
    table.to_csv(root / "outputs" / "table25_retention_pairwise.csv", index=False)
    _, checks, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "retention source interpretation preserves hazard direction and exploratory status" and not row["passed"]
        for row in checks
    )


def test_familywise_rejection_changes_only_controlled_primary_decision(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table23_actot_multiplicity.csv")
    table.loc[table["contrast"].eq(LOW), "reject_familywise"] = True
    table.loc[table["contrast"].eq(LOW), "adjusted_p_value"] = 0.02
    table.to_csv(root / "outputs" / "table23_actot_multiplicity.csv", index=False)
    rows, _, metrics = assess_csr_interpretation(root)
    assert metrics["all_passed"] is True
    assert metrics["primary_familywise_rejections"] == 1
    low = next(
        row for row in rows
        if row["section"] == "PRIMARY_EFFICACY" and row["comparison"] == LOW
    )
    assert low["decision"] == "FAMILYWISE_REJECTED"
    sensitivity = next(
        row for row in rows
        if row["section"] == "MISSING_DATA_SENSITIVITY" and row["comparison"] == LOW
    )
    assert sensitivity["analysis_role"] == "SUPPORTIVE_SENSITIVITY"


def test_interpretation_overclaim_configuration_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "csr_interpretation_v0_21.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["interpretation_claim"] = "REGULATORY_READY"
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="portfolio-scoped"):
        assess_csr_interpretation(root)

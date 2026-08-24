from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cdisc_portfolio.csr_interpretation_extension import (
    assess_csr_interpretation_extension,
    write_csr_interpretation_extension_outputs,
)


LOW = "Xanomeline Low Dose vs Placebo"
HIGH = "Xanomeline High Dose vs Placebo"
SCENARIOS = ["COMMON_WORSENING", "ACTIVE_ONLY_WORSENING", "DIVERGENT_WORSENING"]


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.21.0",
        "primary_comparisons": [LOW, HIGH],
        "fixed_delta_scenarios": SCENARIOS,
        "primary_estimate_tolerance": 1e-8,
        "rules": {
            "multiplicity_reject_flag_must_match_adjusted_and_local_p_rules": True,
            "fixed_delta_is_supportive_not_confirmatory": True,
            "direction_tipping_context_must_be_reported": True,
        },
        "required_inputs": [
            "outputs/table23_actot_multiplicity.csv",
            "outputs/table19_actot_directional_tipping_points.csv",
            "outputs/csr_conclusion_matrix.csv",
            "outputs/csr_statistical_interpretation.md",
        ],
    }
    (tmp_path / "spec" / "csr_interpretation_extension_v0_21.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )

    pd.DataFrame(
        [
            {"contrast": LOW, "estimate": -1.6, "raw_p_value": 0.17, "adjusted_p_value": 0.34, "local_alpha": 0.025, "family_alpha": 0.05, "reject_familywise": False},
            {"contrast": HIGH, "estimate": -0.9, "raw_p_value": 0.42, "adjusted_p_value": 0.84, "local_alpha": 0.025, "family_alpha": 0.05, "reject_familywise": False},
        ]
    ).to_csv(tmp_path / "outputs" / "table23_actot_multiplicity.csv", index=False)

    rows = []
    values = {
        LOW: [("COMMON_WORSENING", 3.98, 4.0), ("ACTIVE_ONLY_WORSENING", 2.24, 2.5), ("DIVERGENT_WORSENING", 1.56, 2.0)],
        HIGH: [("COMMON_WORSENING", 3.44, 3.5), ("ACTIVE_ONLY_WORSENING", 1.59, 2.0), ("DIVERGENT_WORSENING", 1.03, 1.5)],
    }
    estimates = {LOW: -1.6, HIGH: -0.9}
    for comparison, items in values.items():
        for scenario, delta, grid_delta in items:
            rows.append(
                {
                    "scenario_id": scenario,
                    "comparison": comparison,
                    "primary_estimate": estimates[comparison],
                    "direction_tipping_delta": delta,
                    "tipping_within_grid": True,
                    "first_grid_delta_nonnegative": grid_delta,
                    "significance_tipping_status": "not_applicable_primary_not_significant",
                }
            )
    pd.DataFrame(rows).to_csv(
        tmp_path / "outputs" / "table19_actot_directional_tipping_points.csv", index=False
    )

    pd.DataFrame(
        [
            {"section": "PRIMARY_EFFICACY", "analysis_role": "CONFIRMATORY_DECISION", "comparison": LOW, "estimate": -1.6, "ci95_lower": -3.8, "ci95_upper": 0.6, "p_value": 0.17, "adjusted_p_value": 0.34, "decision": "NO_FAMILYWISE_REJECTION", "controlled_interpretation": "no confirmatory claim", "evidence_source": "primary"},
            {"section": "PRIMARY_EFFICACY", "analysis_role": "CONFIRMATORY_DECISION", "comparison": HIGH, "estimate": -0.9, "ci95_lower": -3.3, "ci95_upper": 1.5, "p_value": 0.42, "adjusted_p_value": 0.84, "decision": "NO_FAMILYWISE_REJECTION", "controlled_interpretation": "no confirmatory claim", "evidence_source": "primary"},
        ]
    ).to_csv(tmp_path / "outputs" / "csr_conclusion_matrix.csv", index=False)
    (tmp_path / "outputs" / "csr_statistical_interpretation.md").write_text(
        "# CSR-style statistical interpretation pack\n\n## Missing-data sensitivity\n\nReference-based MI context.\n\n## Safety\n\nSafety context.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_extension_adds_fixed_delta_context_and_matrix_rows(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    metrics = write_csr_interpretation_extension_outputs(root)
    assert metrics["all_passed"] is True
    assert metrics["fixed_delta_rows"] == 6
    assert metrics["fixed_delta_conclusion_rows"] == 2
    matrix = pd.read_csv(root / "outputs" / "csr_conclusion_matrix.csv")
    fixed = matrix.loc[matrix["section"].eq("FIXED_DELTA_SENSITIVITY")]
    assert len(fixed) == 2
    low = fixed.loc[fixed["comparison"].eq(LOW)].iloc[0]
    high = fixed.loc[fixed["comparison"].eq(HIGH)].iloc[0]
    assert abs(float(low["estimate"]) - 1.56) < 1e-12
    assert abs(float(high["estimate"]) - 1.03) < 1e-12
    summary = (root / "outputs" / "csr_statistical_interpretation.md").read_text()
    assert "## Fixed-delta directional sensitivity" in summary
    assert "direction is assumption-sensitive" in summary
    assert summary.index("## Fixed-delta directional sensitivity") < summary.index("## Safety")


def test_reject_flag_inconsistent_with_p_rules_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table23_actot_multiplicity.csv")
    table.loc[0, "reject_familywise"] = True
    table.to_csv(root / "outputs" / "table23_actot_multiplicity.csv", index=False)
    _, checks, metrics = assess_csr_interpretation_extension(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "family-wise reject flags match local-alpha and adjusted-p decision rules" and not row["passed"]
        for row in checks
    )


def test_missing_fixed_delta_scenario_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table19_actot_directional_tipping_points.csv")
    table = table.loc[~(table["comparison"].eq(LOW) & table["scenario_id"].eq("DIVERGENT_WORSENING"))]
    table.to_csv(root / "outputs" / "table19_actot_directional_tipping_points.csv", index=False)
    _, checks, metrics = assess_csr_interpretation_extension(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "fixed-delta tipping table contains exactly the controlled scenarios per comparison" and not row["passed"]
        for row in checks
    )


def test_fixed_delta_primary_estimate_drift_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    table = pd.read_csv(root / "outputs" / "table19_actot_directional_tipping_points.csv")
    table.loc[0, "primary_estimate"] = -99.0
    table.to_csv(root / "outputs" / "table19_actot_directional_tipping_points.csv", index=False)
    _, checks, metrics = assess_csr_interpretation_extension(root)
    assert metrics["all_passed"] is False
    assert any(
        row["check"] == "fixed-delta primary estimates reconcile to the multiplicity table" and not row["passed"]
        for row in checks
    )

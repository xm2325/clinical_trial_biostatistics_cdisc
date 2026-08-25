from __future__ import annotations

import json
from pathlib import Path

from cdisc_portfolio.design_operating_characteristics import run_design_operating_characteristics


def test_design_operating_characteristics_runs_and_controls_null_fwer(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    cfg = {
        "version": "0.24.0",
        "claim": "PORTFOLIO_DESIGN_OPERATING_CHARACTERISTICS_READY",
        "seed": 42,
        "replicates": 500,
        "alpha_family": 0.05,
        "multiplicity": "Bonferroni across two active-versus-placebo comparisons",
        "allocation": {"Placebo": 86, "Xanomeline Low Dose": 84, "Xanomeline High Dose": 84},
        "visits_weeks": [0, 8, 16, 24],
        "baseline_mean": 27.0,
        "baseline_sd": 7.5,
        "residual_sd": 8.0,
        "within_subject_rho": 0.55,
        "planned_week24_effects": {"Placebo": 0.0, "Xanomeline Low Dose": -3.0, "Xanomeline High Dose": -3.0},
        "null_week24_effects": {"Placebo": 0.0, "Xanomeline Low Dose": 0.0, "Xanomeline High Dose": 0.0},
        "scenarios": [
            {"id": "S01", "label": "20% MAR", "dropout_week24": 0.20, "mnar_shift": 0.0},
            {"id": "S02", "label": "35% MAR", "dropout_week24": 0.35, "mnar_shift": 0.0},
            {"id": "S03", "label": "50% MAR", "dropout_week24": 0.50, "mnar_shift": 0.0}
        ],
        "quality_gates": {
            "max_null_familywise_error": 0.10,
            "max_mcse_probability": 0.023,
            "require_monotone_observed_n_under_mar": true
        },
        "interpretation_boundary": ["test"]
    }
    (tmp_path / "spec" / "design_operating_characteristics_v0_24.json").write_text(json.dumps(cfg))
    table, checks, metrics = run_design_operating_characteristics(tmp_path)
    assert len(table) == 3
    assert metrics["all_passed"] is True
    assert table.sort_values("dropout_week24")["mean_week24_observed_n"].is_monotonic_decreasing
    assert checks["passed"].all()


def test_mnar_stress_exposes_full_data_bias(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    cfg = {
        "version": "0.24.0",
        "claim": "PORTFOLIO_DESIGN_OPERATING_CHARACTERISTICS_READY",
        "seed": 7,
        "replicates": 500,
        "alpha_family": 0.05,
        "multiplicity": "Bonferroni",
        "allocation": {"Placebo": 86, "Xanomeline Low Dose": 84, "Xanomeline High Dose": 84},
        "visits_weeks": [0, 8, 16, 24],
        "baseline_mean": 27.0,
        "baseline_sd": 7.5,
        "residual_sd": 8.0,
        "within_subject_rho": 0.55,
        "planned_week24_effects": {"Placebo": 0.0, "Xanomeline Low Dose": -3.0, "Xanomeline High Dose": -3.0},
        "null_week24_effects": {"Placebo": 0.0, "Xanomeline Low Dose": 0.0, "Xanomeline High Dose": 0.0},
        "scenarios": [
            {"id": "S01", "label": "20% MAR", "dropout_week24": 0.20, "mnar_shift": 0.0},
            {"id": "S02", "label": "35% MAR", "dropout_week24": 0.35, "mnar_shift": 0.0},
            {"id": "S03", "label": "35% MNAR", "dropout_week24": 0.35, "mnar_shift": 2.0}
        ],
        "quality_gates": {
            "max_null_familywise_error": 0.10,
            "max_mcse_probability": 0.023,
            "require_monotone_observed_n_under_mar": true
        },
        "interpretation_boundary": ["test"]
    }
    (tmp_path / "spec" / "design_operating_characteristics_v0_24.json").write_text(json.dumps(cfg))
    table, _, _ = run_design_operating_characteristics(tmp_path)
    mar = table.loc[table["scenario_id"].eq("S02")].iloc[0]
    mnar = table.loc[table["scenario_id"].eq("S03")].iloc[0]
    assert abs(float(mnar["low_bias_vs_full_data"])) > abs(float(mar["low_bias_vs_full_data"]))
    assert abs(float(mnar["high_bias_vs_full_data"])) > abs(float(mar["high_bias_vs_full_data"]))

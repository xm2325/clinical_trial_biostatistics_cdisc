from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mnar_sensitivity import delta_values, run_delta_sensitivity, validate_sensitivity_spec


def _spec() -> dict:
    return {
        "version": "0.12.0",
        "method": "fixed_delta_pattern_mixture_mean_shift",
        "endpoint": {"parameter": "ACTOT", "visit": "Week 24", "measure": "change_from_baseline", "scale_direction": "lower_better"},
        "reference_analysis": {"method": "MMRM", "covariance": "Unstructured", "missing_data_assumption": "MAR"},
        "delta_grid": {"start": 0.0, "stop": 6.0, "step": 0.5, "units": "ACTOT points"},
        "scenarios": [
            {"id": "COMMON_WORSENING", "label": "common", "active_multiplier": 1.0, "placebo_multiplier": 1.0},
            {"id": "ACTIVE_ONLY_WORSENING", "label": "active", "active_multiplier": 1.0, "placebo_multiplier": 0.0},
            {"id": "DIVERGENT_WORSENING", "label": "divergent", "active_multiplier": 1.0, "placebo_multiplier": -1.0},
        ],
        "tipping_definition": {"primary": "effect_direction_crosses_zero", "alpha": 0.05},
    }


def _contrasts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"contrast": "Xanomeline Low Dose vs Placebo", "AVISIT": "Week 24", "estimate": -1.6, "SE": 1.1, "df": 100.0, "lower.CL": -3.8, "upper.CL": 0.6, "p.value": 0.15, "covariance": "Unstructured"},
            {"contrast": "Xanomeline High Dose vs Placebo", "AVISIT": "Week 24", "estimate": -0.9, "SE": 1.0, "df": 100.0, "lower.CL": -2.9, "upper.CL": 1.1, "p.value": 0.37, "covariance": "Unstructured"},
        ]
    )


def _missingness() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"TRT01A": "Placebo", "AVISIT": "Week 24", "target_n": 100, "observed_n": 70, "missing_n": 30},
            {"TRT01A": "Xanomeline Low Dose", "AVISIT": "Week 24", "target_n": 100, "observed_n": 30, "missing_n": 70},
            {"TRT01A": "Xanomeline High Dose", "AVISIT": "Week 24", "target_n": 100, "observed_n": 40, "missing_n": 60},
        ]
    )


def test_fixed_delta_sensitivity_reproduces_primary_and_tips_direction():
    grid, tipping, qc, metrics, _ = run_delta_sensitivity(_spec(), _contrasts(), _missingness())
    assert metrics["all_required_passed"]
    assert qc.loc[qc["required"], "passed"].all()
    assert len(grid) == 3 * 2 * 13
    zero = grid[np.isclose(grid["delta"], 0.0)]
    assert np.allclose(zero["shifted_estimate"], zero["primary_estimate"], atol=1e-12, rtol=0)

    common_low = tipping[(tipping["scenario_id"] == "COMMON_WORSENING") & (tipping["comparison"] == "Xanomeline Low Dose vs Placebo")].iloc[0]
    assert common_low["direction_tipping_delta"] == pytest.approx(4.0)
    active_low = tipping[(tipping["scenario_id"] == "ACTIVE_ONLY_WORSENING") & (tipping["comparison"] == "Xanomeline Low Dose vs Placebo")].iloc[0]
    assert active_low["direction_tipping_delta"] == pytest.approx(1.6 / 0.7)
    divergent_low = tipping[(tipping["scenario_id"] == "DIVERGENT_WORSENING") & (tipping["comparison"] == "Xanomeline Low Dose vs Placebo")].iloc[0]
    assert divergent_low["direction_tipping_delta"] == pytest.approx(1.6 / 1.0)


def test_missingness_denominator_corruption_is_blocking():
    bad = _missingness()
    bad.loc[bad["TRT01A"] == "Xanomeline Low Dose", "observed_n"] = 31
    grid, _, qc, metrics, _ = run_delta_sensitivity(_spec(), _contrasts(), bad)
    assert grid.empty
    assert not metrics["all_required_passed"]
    row = qc[qc["check"] == "Week 24 missingness denominators and proportions reconcile"].iloc[0]
    assert not bool(row["passed"])


def test_spec_rejects_wrong_endpoint_direction_and_wrong_reference_assumption():
    spec = copy.deepcopy(_spec())
    spec["endpoint"]["scale_direction"] = "higher_better"
    spec["reference_analysis"]["missing_data_assumption"] = "MNAR"
    checks = validate_sensitivity_spec(spec)
    failed = set(checks.loc[~checks["passed"], "check"])
    assert "Sensitivity endpoint matches ACTOT Week 24 change with lower values better" in failed
    assert "Reference analysis is the primary unstructured MAR MMRM" in failed


def test_delta_grid_rejects_unreachable_stop():
    spec = copy.deepcopy(_spec())
    spec["delta_grid"] = {"start": 0.0, "stop": 1.0, "step": 0.3}
    with pytest.raises(ValueError, match="reachable exactly"):
        delta_values(spec)


def test_significance_tipping_note_fails_if_primary_becomes_significant():
    contrasts = _contrasts()
    contrasts.loc[:, "p.value"] = [0.01, 0.02]
    _, _, qc, metrics, _ = run_delta_sensitivity(_spec(), contrasts, _missingness())
    assert not metrics["all_required_passed"]
    row = qc[qc["check"].str.startswith("Loss-of-significance tipping")].iloc[0]
    assert not bool(row["passed"])


def test_repository_sensitivity_spec_is_machine_validated():
    spec = json.loads((ROOT / "spec" / "mnar_sensitivity.json").read_text(encoding="utf-8"))
    checks = validate_sensitivity_spec(spec)
    assert checks["passed"].all()

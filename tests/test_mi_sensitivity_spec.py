import copy
import json
from pathlib import Path

import pytest

from cdisc_portfolio.mi_spec import validate_mi_spec

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "spec" / "mi_sensitivity.json"


def _spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_v013_mi_spec_passes_executable_validator():
    validate_mi_spec(_spec())


def test_v013_mi_spec_has_controlled_rbmi_method_and_precision():
    spec = _spec()
    imp = spec["imputation"]
    assert spec["version"] == "0.13.0"
    assert imp["package"] == "rbmi"
    assert imp["required_version"] == "1.6.1"
    assert imp["method"] == "approxbayes"
    assert imp["covariance"] == "us"
    assert imp["same_covariance_across_groups"] is True
    assert imp["reml"] is True
    assert imp["n_imputations"] == 200
    assert 0 < imp["failure_threshold"] <= 0.10
    assert 0 < imp["max_mcse_estimate_to_se_ratio"] <= 0.075


def test_v013_mi_spec_has_complete_pairwise_comparisons():
    spec = _spec()
    comparisons = spec["analysis"]["comparisons"]
    assert [c["active_arm"] for c in comparisons] == [
        "Xanomeline Low Dose",
        "Xanomeline High Dose",
    ]
    assert all(c["reference_arm"] == "Placebo" for c in comparisons)
    assert len({c["seed"] for c in comparisons}) == 2
    assert all(isinstance(c["seed"], int) and c["seed"] > 0 for c in comparisons)


def test_v013_mi_spec_keeps_mar_and_delta_scenarios_distinct():
    spec = _spec()
    scenarios = {x["id"]: x for x in spec["scenarios"]}
    assert set(scenarios) == {"MAR", "ACTIVE_PLUS_1", "ACTIVE_PLUS_2", "DIVERGENT_1"}
    assert scenarios["MAR"]["active_delta"] == 0
    assert scenarios["MAR"]["placebo_delta"] == 0
    assert scenarios["ACTIVE_PLUS_1"]["active_delta"] == 1
    assert scenarios["ACTIVE_PLUS_1"]["placebo_delta"] == 0
    assert scenarios["ACTIVE_PLUS_2"]["active_delta"] == 2
    assert scenarios["ACTIVE_PLUS_2"]["placebo_delta"] == 0
    assert scenarios["DIVERGENT_1"]["active_delta"] == 1
    assert scenarios["DIVERGENT_1"]["placebo_delta"] == -1


def test_v013_mi_spec_preserves_longitudinal_history_and_week24_analysis():
    spec = _spec()
    assert spec["imputation"]["visits"] == ["8", "16", "24"]
    assert spec["endpoint"]["analysis_visit"] == "24"
    assert spec["endpoint"]["direction"] == "lower_is_better"
    assert "BASE*VISIT" in spec["imputation"]["imputation_model_covariates"]
    assert "TRT01A*VISIT" in spec["imputation"]["imputation_model_covariates"]
    assert spec["analysis"]["covariates"] == ["BASE"]
    assert spec["analysis"]["pooling"] == "Rubin"


def test_v013_negative_control_rejects_uncontrolled_imputation_count():
    broken = copy.deepcopy(_spec())
    broken["imputation"]["n_imputations"] = 50
    with pytest.raises(ValueError, match="n_imputations"):
        validate_mi_spec(broken)


def test_v013_negative_control_rejects_reference_arm_change():
    broken = copy.deepcopy(_spec())
    broken["analysis"]["comparisons"][0]["reference_arm"] = "Xanomeline High Dose"
    with pytest.raises(ValueError, match="reference arm"):
        validate_mi_spec(broken)


def test_v013_negative_control_rejects_relaxed_mcse_gate():
    broken = copy.deepcopy(_spec())
    broken["imputation"]["max_mcse_estimate_to_se_ratio"] = 0.20
    with pytest.raises(ValueError, match="mcse"):
        validate_mi_spec(broken)


def test_v013_negative_control_rejects_delta_scenario_change():
    broken = copy.deepcopy(_spec())
    broken["scenarios"][2]["active_delta"] = 3.0
    with pytest.raises(ValueError, match="delta"):
        validate_mi_spec(broken)

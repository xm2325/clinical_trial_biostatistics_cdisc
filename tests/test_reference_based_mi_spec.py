import copy
import json
from pathlib import Path

import pytest

from cdisc_portfolio.reference_mi_spec import validate_reference_based_mi_spec

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "spec" / "reference_based_mi.json"


def _spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_v014_reference_based_mi_spec_passes_validator():
    validate_reference_based_mi_spec(_spec())


def test_v014_uses_recorded_discontinuation_and_fixed_visit_timing():
    spec = _spec()
    ice = spec["intercurrent_event"]
    assert ice["event"] == "recorded_treatment_discontinuation"
    assert ice["subject_flag"] == "DCSFL"
    assert ice["nominal_visit_days"] == {"8": 56, "16": 112, "24": 168}
    assert ice["require_zero_observed_post_ice_for_strategy_switch"] is True


def test_v014_reference_strategies_are_controlled_rbmi_methods():
    spec = _spec()
    rb = spec["reference_based_imputation"]
    assert rb["required_version"] == "1.6.1"
    assert rb["reference_arm"] == "Placebo"
    assert rb["initial_draw_strategy"] == "JR"
    assert rb["strategies"] == ["MAR", "JR", "CR", "CIR"]
    assert rb["reference_arm_discontinuers_strategy"] == "MAR"
    assert rb["reuse_parameter_draws_across_strategies"] is True
    assert rb["reuse_ice_timing_across_strategies"] is True


def test_v014_preserves_v013_imputation_and_analysis_base():
    spec = _spec()
    assert spec["base_imputation_spec"] == "spec/mi_sensitivity.json"
    assert spec["analysis"]["method"] == "Week 24 ANCOVA"
    assert spec["analysis"]["covariates"] == ["BASE"]
    assert spec["analysis"]["pooling"] == "Rubin"
    assert spec["reference_based_imputation"]["max_mcse_estimate_to_se_ratio"] <= 0.075


def test_v014_negative_control_rejects_j2r_alias_in_code_spec():
    broken = copy.deepcopy(_spec())
    broken["reference_based_imputation"]["strategies"][1] = "J2R"
    with pytest.raises(ValueError, match="strategy set"):
        validate_reference_based_mi_spec(broken)


def test_v014_negative_control_rejects_reference_arm_change():
    broken = copy.deepcopy(_spec())
    broken["reference_based_imputation"]["reference_arm"] = "Xanomeline Low Dose"
    with pytest.raises(ValueError, match="Placebo"):
        validate_reference_based_mi_spec(broken)


def test_v014_negative_control_rejects_relaxed_mcse_gate():
    broken = copy.deepcopy(_spec())
    broken["reference_based_imputation"]["max_mcse_estimate_to_se_ratio"] = 0.20
    with pytest.raises(ValueError, match="MCSE"):
        validate_reference_based_mi_spec(broken)


def test_v014_negative_control_rejects_post_ice_switch_without_observation_gate():
    broken = copy.deepcopy(_spec())
    broken["intercurrent_event"]["require_zero_observed_post_ice_for_strategy_switch"] = False
    with pytest.raises(ValueError, match="zero observed post-ICE"):
        validate_reference_based_mi_spec(broken)

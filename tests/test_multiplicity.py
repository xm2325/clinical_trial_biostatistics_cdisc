import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.multiplicity import (
    evaluate_primary_multiplicity,
    validate_multiplicity_spec,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "spec" / "multiplicity.json"
PLANNING_PATH = ROOT / "spec" / "protocol_design.json"


def _spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _planning():
    return json.loads(PLANNING_PATH.read_text(encoding="utf-8"))


def _contrasts():
    return pd.DataFrame(
        [
            {
                "contrast": "Xanomeline Low Dose vs Placebo",
                "AVISIT": "Week 24",
                "estimate": -1.6,
                "SE": 1.1,
                "df": 180.0,
                "lower.CL": -3.8,
                "upper.CL": 0.6,
                "p.value": 0.02,
                "covariance": "Unstructured",
            },
            {
                "contrast": "Xanomeline High Dose vs Placebo",
                "AVISIT": "Week 24",
                "estimate": -0.9,
                "SE": 1.0,
                "df": 180.0,
                "lower.CL": -2.9,
                "upper.CL": 1.1,
                "p.value": 0.40,
                "covariance": "Unstructured",
            },
        ]
    )


def test_v015_multiplicity_spec_passes_validator_and_matches_planning():
    validate_multiplicity_spec(_spec(), _planning())


def test_v015_family_matches_existing_protocol_design_bonferroni_rule():
    spec = _spec()
    planning = _planning()
    assert planning["multiplicity"]["method"] == spec["family"]["method"] == "Bonferroni"
    assert planning["multiplicity"]["family_alpha"] == spec["family"]["family_alpha"] == 0.05
    assert planning["multiplicity"]["active_vs_control_comparisons"] == spec["decision_rule"]["comparison_count"] == 2
    assert spec["decision_rule"]["local_alpha"] == 0.025


def test_v015_multiplicity_decision_uses_adjusted_p_and_equivalent_local_alpha_rule():
    result = evaluate_primary_multiplicity(_spec(), _planning(), _contrasts())
    decisions = result.decisions.set_index("hypothesis_id")
    assert len(decisions) == 2
    assert decisions.loc["H_LOW", "adjusted_p_value"] == pytest.approx(0.04)
    assert bool(decisions.loc["H_LOW", "reject_familywise"]) is True
    assert decisions.loc["H_HIGH", "adjusted_p_value"] == pytest.approx(0.80)
    assert bool(decisions.loc["H_HIGH", "reject_familywise"]) is False
    assert bool(result.qc.loc[result.qc["required"], "passed"].all()) is True


def test_v015_negative_control_rejects_family_alpha_change():
    broken = copy.deepcopy(_spec())
    broken["family"]["family_alpha"] = 0.10
    with pytest.raises(ValueError, match="family alpha"):
        validate_multiplicity_spec(broken, _planning())


def test_v015_negative_control_rejects_comparison_count_change():
    broken = copy.deepcopy(_spec())
    broken["decision_rule"]["comparison_count"] = 3
    with pytest.raises(ValueError, match="comparison count"):
        validate_multiplicity_spec(broken, _planning())


def test_v015_negative_control_rejects_non_bonferroni_method():
    broken = copy.deepcopy(_spec())
    broken["family"]["method"] = "Holm"
    with pytest.raises(ValueError, match="Bonferroni"):
        validate_multiplicity_spec(broken, _planning())


def test_v015_negative_control_rejects_visit_change():
    broken = copy.deepcopy(_spec())
    broken["family"]["visit"] = "Week 16"
    with pytest.raises(ValueError, match="Week 24"):
        validate_multiplicity_spec(broken, _planning())


def test_v015_negative_control_rejects_covariance_change():
    broken = copy.deepcopy(_spec())
    broken["family"]["covariance"] = "AR1 heterogeneous"
    with pytest.raises(ValueError, match="Unstructured"):
        validate_multiplicity_spec(broken, _planning())


def test_v015_evaluation_fails_if_one_primary_hypothesis_is_missing():
    broken_input = _contrasts().iloc[[0]].copy()
    result = evaluate_primary_multiplicity(_spec(), _planning(), broken_input)
    required = result.qc.loc[result.qc["required"]]
    assert bool(required["passed"].all()) is False
    assert any("exactly two" in x.lower() or "exact controlled hypothesis" in x.lower() for x in required.loc[~required["passed"], "check"])


def test_v015_evaluation_rejects_missing_required_source_columns():
    broken_input = _contrasts().drop(columns=["p.value"])
    with pytest.raises(ValueError, match="missing columns"):
        evaluate_primary_multiplicity(_spec(), _planning(), broken_input)

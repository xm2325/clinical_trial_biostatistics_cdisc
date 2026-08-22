import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.design import evaluate_continuous_design
from cdisc_portfolio.sample_size import (
    bonferroni_alpha,
    inflate_for_dropout,
    two_arm_continuous_n_per_arm,
    two_arm_continuous_power,
)


def _spec():
    return json.loads((ROOT / "spec" / "protocol_design.json").read_text())


def test_bonferroni_alpha_for_two_active_comparisons():
    assert bonferroni_alpha(0.05, 2) == pytest.approx(0.025)


def test_dropout_inflation_is_ceiling_based():
    assert inflate_for_dropout(110, 0.15) == 130


def test_continuous_power_meets_target_after_ceiling():
    n = two_arm_continuous_n_per_arm(effect=2.5, sd=6.0, alpha=0.025, power=0.80)
    assert n == 110
    assert two_arm_continuous_power(n, effect=2.5, sd=6.0, alpha=0.025) >= 0.80


def test_protocol_design_expected_scenario_counts_and_qc():
    result = evaluate_continuous_design(_spec())
    assert len(result.scenarios) == 6
    assert result.qc.loc[result.qc["required"], "passed"].all()
    assert result.scenarios["per_comparison_alpha"].nunique() == 1
    assert result.scenarios["per_comparison_alpha"].iloc[0] == pytest.approx(0.025)


def test_protocol_design_effect_and_power_monotonicity():
    result = evaluate_continuous_design(_spec()).scenarios
    p80 = result[result["target_power"] == 0.80].sort_values("effect")
    assert p80["evaluable_n_per_arm"].tolist() == sorted(
        p80["evaluable_n_per_arm"].tolist(), reverse=True
    )
    effect_25 = result[result["effect"] == 2.5].sort_values("target_power")
    assert effect_25["evaluable_n_per_arm"].iloc[1] > effect_25["evaluable_n_per_arm"].iloc[0]


def test_protocol_design_rejects_duplicate_scenario_ids():
    spec = _spec()
    spec["scenarios"][1]["scenario_id"] = spec["scenarios"][0]["scenario_id"]
    with pytest.raises(ValueError, match="duplicate scenario_id"):
        evaluate_continuous_design(spec)

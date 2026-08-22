from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .sample_size import (
    bonferroni_alpha,
    inflate_for_dropout,
    two_arm_continuous_n_per_arm,
    two_arm_continuous_power,
)


@dataclass(frozen=True)
class DesignResult:
    scenarios: pd.DataFrame
    qc: pd.DataFrame


REQUIRED_SCENARIO_FIELDS = {"scenario_id", "effect", "power"}


def evaluate_continuous_design(spec: dict[str, Any]) -> DesignResult:
    """Evaluate a machine-readable continuous-endpoint planning specification."""
    family_alpha = float(spec["multiplicity"]["family_alpha"])
    comparisons = int(spec["multiplicity"]["active_vs_control_comparisons"])
    per_comparison_alpha = bonferroni_alpha(family_alpha, comparisons)
    dropout_rate = float(spec["dropout_rate"])
    sd = float(spec["common_sd"])
    arms = list(spec["allocation"]["arms"])
    scenarios = list(spec["scenarios"])

    if len(arms) < 2:
        raise ValueError("at least two treatment arms are required")
    if sd <= 0:
        raise ValueError("common_sd must be positive")
    if not scenarios:
        raise ValueError("at least one design scenario is required")

    seen_ids: set[str] = set()
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        missing = REQUIRED_SCENARIO_FIELDS.difference(scenario)
        if missing:
            raise ValueError(f"scenario missing required fields: {sorted(missing)}")
        scenario_id = str(scenario["scenario_id"])
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        seen_ids.add(scenario_id)

        effect = float(scenario["effect"])
        target_power = float(scenario["power"])
        n_evaluable = two_arm_continuous_n_per_arm(
            effect=effect,
            sd=sd,
            alpha=per_comparison_alpha,
            power=target_power,
        )
        n_randomised = inflate_for_dropout(n_evaluable, dropout_rate)
        achieved_power = two_arm_continuous_power(
            n_per_arm=n_evaluable,
            effect=effect,
            sd=sd,
            alpha=per_comparison_alpha,
        )
        rows.append(
            {
                "scenario_id": scenario_id,
                "effect": effect,
                "common_sd": sd,
                "standardised_effect": effect / sd,
                "target_power": target_power,
                "family_alpha": family_alpha,
                "comparisons": comparisons,
                "per_comparison_alpha": per_comparison_alpha,
                "dropout_rate": dropout_rate,
                "evaluable_n_per_arm": n_evaluable,
                "randomised_n_per_arm": n_randomised,
                "total_randomised": n_randomised * len(arms),
                "achieved_power_at_evaluable_n": achieved_power,
            }
        )

    out = pd.DataFrame(rows).sort_values(["effect", "target_power"]).reset_index(drop=True)
    qc_rows: list[dict[str, Any]] = []

    def add_check(check: str, passed: bool, detail: str, required: bool = True) -> None:
        qc_rows.append({"check": check, "passed": bool(passed), "required": required, "detail": detail})

    add_check(
        "Bonferroni per-comparison alpha matches family alpha / comparisons",
        abs(per_comparison_alpha * comparisons - family_alpha) < 1e-12,
        f"family alpha={family_alpha}; comparisons={comparisons}; per-comparison alpha={per_comparison_alpha}",
    )
    add_check(
        "Dropout inflation does not reduce per-arm sample size",
        bool((out["randomised_n_per_arm"] >= out["evaluable_n_per_arm"]).all()),
        f"dropout rate={dropout_rate}",
    )
    add_check(
        "Back-calculated achieved power meets each target",
        bool((out["achieved_power_at_evaluable_n"] + 1e-12 >= out["target_power"]).all()),
        f"minimum margin={(out['achieved_power_at_evaluable_n'] - out['target_power']).min():.6g}",
    )
    add_check(
        "Scenario identifiers are unique",
        out["scenario_id"].nunique() == len(out),
        f"unique={out['scenario_id'].nunique()}; rows={len(out)}",
    )
    add_check(
        "Total randomised equals per-arm randomised N times number of arms",
        bool((out["total_randomised"] == out["randomised_n_per_arm"] * len(arms)).all()),
        f"arms={len(arms)}",
    )

    effect_monotonic = True
    effect_details: list[str] = []
    for target_power, g in out.groupby("target_power"):
        g = g.sort_values("effect")
        values = g["evaluable_n_per_arm"].tolist()
        passed = all(a >= b for a, b in zip(values, values[1:]))
        effect_monotonic &= passed
        effect_details.append(f"power={target_power}: {values}")
    add_check(
        "Required N is non-increasing as assumed effect increases",
        effect_monotonic,
        "; ".join(effect_details),
    )

    power_monotonic = True
    power_details: list[str] = []
    for effect, g in out.groupby("effect"):
        g = g.sort_values("target_power")
        values = g["evaluable_n_per_arm"].tolist()
        passed = all(a <= b for a, b in zip(values, values[1:]))
        power_monotonic &= passed
        power_details.append(f"effect={effect}: {values}")
    add_check(
        "Required N is non-decreasing as target power increases",
        power_monotonic,
        "; ".join(power_details),
    )

    qc = pd.DataFrame(qc_rows)
    return DesignResult(scenarios=out, qc=qc)

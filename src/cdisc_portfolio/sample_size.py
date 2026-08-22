from __future__ import annotations

import math
from scipy.stats import norm


def _validate_alpha_power(alpha: float, power: float | None = None) -> None:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if power is not None and not 0 < power < 1:
        raise ValueError("power must be in (0, 1)")


def bonferroni_alpha(family_alpha: float, comparisons: int) -> float:
    """Return the per-comparison two-sided alpha under Bonferroni control."""
    _validate_alpha_power(family_alpha)
    if comparisons < 1:
        raise ValueError("comparisons must be at least 1")
    return family_alpha / comparisons


def inflate_for_dropout(n_evaluable: int, dropout_rate: float) -> int:
    """Inflate an evaluable per-arm sample size for anticipated dropout."""
    if n_evaluable < 1:
        raise ValueError("n_evaluable must be positive")
    if not 0 <= dropout_rate < 1:
        raise ValueError("dropout_rate must be in [0, 1)")
    return math.ceil(n_evaluable / (1 - dropout_rate))


def two_arm_continuous_n_per_arm(
    effect: float,
    sd: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Equal-allocation normal-approximation sample size for a two-sided mean difference."""
    if effect <= 0 or sd <= 0:
        raise ValueError("effect and sd must be positive")
    _validate_alpha_power(alpha, power)
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    n = 2 * (sd ** 2) * (z_alpha + z_power) ** 2 / (effect ** 2)
    return math.ceil(n)


def two_arm_continuous_power(
    n_per_arm: int,
    effect: float,
    sd: float,
    alpha: float = 0.05,
) -> float:
    """Normal-approximation power for a two-sided equal-allocation mean comparison."""
    if n_per_arm < 2:
        raise ValueError("n_per_arm must be at least 2")
    if effect <= 0 or sd <= 0:
        raise ValueError("effect and sd must be positive")
    _validate_alpha_power(alpha)
    z_alpha = norm.ppf(1 - alpha / 2)
    noncentrality = effect * math.sqrt(n_per_arm / (2 * sd ** 2))
    return float(norm.sf(z_alpha - noncentrality) + norm.cdf(-z_alpha - noncentrality))


def two_arm_binary_n_per_arm(
    p_control: float,
    p_treatment: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Equal-allocation normal-approximation sample size for a two-sided proportion difference."""
    if not (0 < p_control < 1 and 0 < p_treatment < 1) or p_control == p_treatment:
        raise ValueError("probabilities must be in (0,1) and unequal")
    _validate_alpha_power(alpha, power)
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    p_bar = (p_control + p_treatment) / 2
    numerator = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_power * math.sqrt(p_control * (1 - p_control) + p_treatment * (1 - p_treatment))
    ) ** 2
    n = numerator / (p_treatment - p_control) ** 2
    return math.ceil(n)

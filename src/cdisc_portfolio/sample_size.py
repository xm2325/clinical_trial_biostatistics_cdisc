from __future__ import annotations

import math
from scipy.stats import norm


def two_arm_continuous_n_per_arm(effect: float, sd: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Equal-allocation normal-approximation sample size for a two-sided difference in means."""
    if effect <= 0 or sd <= 0:
        raise ValueError("effect and sd must be positive")
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    n = 2 * (sd ** 2) * (z_alpha + z_power) ** 2 / (effect ** 2)
    return math.ceil(n)


def two_arm_binary_n_per_arm(p_control: float, p_treatment: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Equal-allocation normal-approximation sample size for a two-sided difference in proportions."""
    if not (0 < p_control < 1 and 0 < p_treatment < 1) or p_control == p_treatment:
        raise ValueError("probabilities must be in (0,1) and unequal")
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    p_bar = (p_control + p_treatment) / 2
    numerator = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_power * math.sqrt(p_control * (1 - p_control) + p_treatment * (1 - p_treatment))
    ) ** 2
    n = numerator / (p_treatment - p_control) ** 2
    return math.ceil(n)

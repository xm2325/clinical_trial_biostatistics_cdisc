from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

from v081_robust_bayesian_provider_effects import (
    CANDIDATE_FAMILIES,
    fit_family,
    posterior_predictive_checks_family,
    standardised_effect_quadrature,
)


def synthetic_panel(seed: int = 20260828) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = ["2026-01", "2026-02", "2026-03"]
    mu = np.array([0.55, 0.63, 0.70])
    rows = []
    for provider_index in range(32):
        # Heavy-tailed truth is deliberate for testing numerical robustness, not
        # for asserting that the real NHS provider distribution is Student-t.
        u = 0.32 * np.sqrt(1.0 / 3.0) * rng.standard_t(3)
        for month_index, month in enumerate(months):
            n = int(rng.integers(35, 120))
            probability = float(expit(mu[month_index] + u))
            y = int(rng.binomial(n, probability))
            rows.append(
                {
                    "ORG_CODE2": f"P{provider_index:03d}",
                    "ORG_NAME2": f"Provider {provider_index:03d}",
                    "month": month,
                    "n": n,
                    "y": y,
                    "raw_rate": y / n,
                }
            )
    return pd.DataFrame(rows)


def test_all_quadrature_rules_are_probability_rules_with_standardised_variance():
    for family in CANDIDATE_FAMILIES:
        nodes, log_weights = standardised_effect_quadrature(family, points=81)
        weights = np.exp(log_weights)
        assert np.isclose(weights.sum(), 1.0, atol=1e-10)
        assert abs(float(np.sum(weights * nodes))) < 1e-10
        # Quantile quadrature approximates t tails; tolerance is intentionally
        # looser than for the Normal Gaussian-Hermite rule.
        assert 0.80 < float(np.sum(weights * nodes * nodes)) < 1.05


def test_all_candidate_families_fit_synthetic_panel():
    panel = synthetic_panel()
    for index, family in enumerate(CANDIDATE_FAMILIES):
        fit = fit_family(
            panel,
            family,
            posterior_draws=250,
            quadrature_points=41,
            seed=10 + index,
        )
        assert fit["success"], (family.name, fit["message"])
        assert fit["tau_mean"] > 0
        assert fit["hessian_eigenvalues_clipped"] == 0
        assert fit["month_summary"]["population_rate_mean"].between(0, 1).all()


def test_student_t_ppc_outputs_are_bounded_and_complete():
    panel = synthetic_panel()
    family = CANDIDATE_FAMILIES[-1]
    fit = fit_family(panel, family, posterior_draws=300, quadrature_points=41, seed=22)
    ppc, persistence = posterior_predictive_checks_family(
        panel, fit, replicates=80, seed=23
    )
    assert len(ppc) == 9
    assert set(ppc["metric"]) == {
        "low_tail_count_le_50",
        "high_tail_count_ge_85",
        "provider_rate_sd",
    }
    assert ppc["two_sided_bayesian_p"].between(0, 1).all()
    assert 0 <= persistence["two_sided_bayesian_p"] <= 1

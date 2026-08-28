from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

from v08_download_nhs_activity import collect_links
from v08_nhs_dynamic_bayesian import (
    PRIMARY_PRIOR,
    fit_dynamic_model,
    gh_rule,
    log_posterior,
    prepare_model_arrays,
    provider_posterior_summary,
    two_sided_predictive_p,
)


def synthetic_panel(seed: int = 20260828) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = ["2026-01", "2026-02", "2026-03"]
    mu = np.array([0.55, 0.65, 0.72])
    rows = []
    for provider_index in range(30):
        u = rng.normal(0.0, 0.35)
        for month_index, month in enumerate(months):
            n = int(rng.integers(45, 130))
            p = float(expit(mu[month_index] + u))
            y = int(rng.binomial(n, p))
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


def test_link_collector_retains_anchor_text_and_href():
    html = '<a class="download" href="/file.csv"><span>NHS Talking Therapies Monthly Activity Data File</span> - January 2026</a>'
    links = collect_links(html)
    assert links == [
        ("/file.csv", "NHS Talking Therapies Monthly Activity Data File - January 2026")
    ]


def test_dynamic_log_posterior_is_finite():
    panel = synthetic_panel()
    prepared = prepare_model_arrays(panel)
    nodes, log_weights = gh_rule(15)
    parameters = np.r_[np.repeat(0.65, 3), np.log(0.25)]
    value = log_posterior(
        parameters,
        prepared["groups"],
        3,
        PRIMARY_PRIOR,
        nodes,
        log_weights,
    )
    assert np.isfinite(value)


def test_dynamic_fit_and_provider_partial_pooling():
    panel = synthetic_panel()
    fit = fit_dynamic_model(panel, posterior_draws=350, seed=7)
    assert fit["success"], fit["message"]
    assert len(fit["month_summary"]) == 3
    assert fit["tau_mean"] > 0
    assert 0 < fit["month_summary"]["population_rate_mean"].min() < 1
    assert fit["month_summary"]["population_rate_mean"].max() < 1
    providers, provider_month = provider_posterior_summary(panel, fit)
    assert len(providers) == 30
    assert len(provider_month) == 90
    assert provider_month["posterior_rate"].between(0, 1).all()
    assert np.isfinite(provider_month["shrinkage_percentage_points"]).all()


def test_two_sided_predictive_p_is_bounded():
    values = np.arange(10, dtype=float)
    p = two_sided_predictive_p(values, 5.0)
    assert 0 <= p <= 1

import numpy as np
import pandas as pd

from v05_bayesian_partial_pooling import (
    PRIMARY_PRIOR,
    conditional_posterior_mean,
    extract_provider_counts,
    fit_hyperposterior,
    summarise_hyperposterior,
)
from v05_posterior_predictive_checks import posterior_predictive_checks


def _activity_rows():
    rows = []
    for group_type, code, name, n, y, pct in [
        ("England", "all", "all Providers", 1000, 680, 68.0),
        ("Provider", "A", "Small service", 10, 9, 90.0),
        ("Provider", "B", "Large service", 1000, 900, 90.0),
        ("Provider", "C", "Middle service", 100, 65, 65.0),
        ("Provider", "D", "Suppressed service", "*", "*", "*"),
    ]:
        for measure, value in [
            ("Count_FinishedCourseTreatment", n),
            ("Count_ReliableImprovement", y),
            ("Percentage_ReliableImprovement", pct),
        ]:
            rows.append(
                {
                    "GROUP_TYPE": group_type,
                    "ORG_CODE2": code,
                    "ORG_NAME2": name,
                    "MEASURE_NAME": measure,
                    "MEASURE_VALUE_SUPPRESSED": value,
                }
            )
    return pd.DataFrame(rows)


def test_extract_provider_counts_excludes_suppressed_and_reproduces_england_rate():
    providers, meta = extract_provider_counts(_activity_rows())
    assert providers["ORG_CODE2"].tolist() == ["A", "C", "B"]
    assert meta["provider_rows_complete"] == 3
    assert meta["suppressed_or_missing_provider_rows_excluded"] == 1
    assert np.isclose(meta["england_reliable_improvement_rate"], 0.68)


def test_partial_pooling_is_stronger_for_small_denominator_at_same_raw_rate():
    alpha, beta = 14.0, 6.0  # prior population mean 0.70
    y = np.array([9, 900])
    n = np.array([10, 1000])
    post = conditional_posterior_mean(y, n, alpha, beta)
    raw = y / n
    shrinkage = np.abs(post - raw)
    assert shrinkage[0] > shrinkage[1]
    assert post[0] < raw[0]
    assert post[1] < raw[1]


def test_hyperposterior_is_normalised_and_finite():
    y = np.array([9, 900, 65, 350, 140])
    n = np.array([10, 1000, 100, 500, 200])
    fit = fit_hyperposterior(y, n, PRIMARY_PRIOR)
    assert np.isclose(fit["weights"].sum(), 1.0)
    assert np.all(np.isfinite(fit["weights"]))
    summary = summarise_hyperposterior(fit)
    assert 0.0 < summary["m_q025"] < summary["m_q975"] < 1.0
    assert 0.0 < summary["kappa_q025"] < summary["kappa_q975"]


def test_posterior_predictive_checks_return_finite_prespecified_diagnostics():
    providers, _ = extract_provider_counts(_activity_rows())
    fit = fit_hyperposterior(providers["y"].to_numpy(), providers["n"].to_numpy(), PRIMARY_PRIOR)
    checks, intervals, summary = posterior_predictive_checks(
        providers, fit, n_replicates=250, seed=1234
    )
    assert len(checks) == 5
    assert len(intervals) == len(providers)
    assert np.all(np.isfinite(checks["bayesian_p_two_sided"]))
    assert checks["bayesian_p_two_sided"].between(0.0, 1.0).all()
    assert 0.0 <= summary["provider_95pct_population_predictive_coverage"] <= 1.0

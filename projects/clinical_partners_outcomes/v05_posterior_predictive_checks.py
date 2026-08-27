from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from v03_nhs_schema_audit import read_csv_flex
from v05_bayesian_partial_pooling import PRIMARY_PRIOR, extract_provider_counts, fit_hyperposterior


def discrepancy_statistics(rates: np.ndarray) -> dict[str, float]:
    rates = np.asarray(rates, dtype=float)
    return {
        "provider_rate_sd": float(np.std(rates, ddof=1)),
        "provider_rate_iqr": float(np.quantile(rates, 0.75) - np.quantile(rates, 0.25)),
        "providers_at_or_below_50pct": float(np.sum(rates <= 0.50)),
        "providers_at_or_above_85pct": float(np.sum(rates >= 0.85)),
        "max_absolute_deviation_from_provider_median": float(np.max(np.abs(rates - np.median(rates)))),
    }


def posterior_predictive_checks(
    providers: pd.DataFrame,
    fit: dict,
    *,
    n_replicates: int = 2000,
    seed: int = 20260827,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if n_replicates < 200:
        raise ValueError("Use at least 200 posterior predictive replicates")

    rng = np.random.default_rng(seed)
    n = providers["n"].to_numpy(dtype=int)
    y = providers["y"].to_numpy(dtype=int)
    observed_rates = y / n
    observed_stats = discrepancy_statistics(observed_rates)

    weights = np.asarray(fit["weights"], dtype=float)
    alpha = np.asarray(fit["alpha"], dtype=float)
    beta = np.asarray(fit["beta"], dtype=float)
    grid_idx = np.arange(len(weights))

    replicated_rates = np.empty((n_replicates, len(providers)), dtype=float)
    replicated_stats: list[dict[str, float]] = []

    sampled_grid = rng.choice(grid_idx, size=n_replicates, replace=True, p=weights)
    for r, idx in enumerate(sampled_grid):
        theta = rng.beta(alpha[idx], beta[idx], size=len(providers))
        y_rep = rng.binomial(n, theta)
        rates_rep = y_rep / n
        replicated_rates[r, :] = rates_rep
        stats = discrepancy_statistics(rates_rep)
        stats["replicate"] = float(r)
        replicated_stats.append(stats)

    stats_df = pd.DataFrame(replicated_stats)
    check_rows: list[dict[str, float | str]] = []
    for name, observed in observed_stats.items():
        rep = stats_df[name].to_numpy(dtype=float)
        upper = float(np.mean(rep >= observed))
        lower = float(np.mean(rep <= observed))
        two_sided = min(1.0, 2.0 * min(upper, lower))
        check_rows.append(
            {
                "statistic": name,
                "observed": observed,
                "predictive_mean": float(np.mean(rep)),
                "predictive_q025": float(np.quantile(rep, 0.025)),
                "predictive_q50": float(np.quantile(rep, 0.50)),
                "predictive_q975": float(np.quantile(rep, 0.975)),
                "bayesian_p_upper": upper,
                "bayesian_p_two_sided": two_sided,
            }
        )
    checks = pd.DataFrame(check_rows)

    provider_intervals = providers[["ORG_CODE2", "ORG_NAME2", "n", "y", "raw_rate"]].copy()
    provider_intervals = provider_intervals.rename(
        columns={"ORG_CODE2": "provider_code", "ORG_NAME2": "provider_name"}
    )
    provider_intervals["predictive_q025"] = np.quantile(replicated_rates, 0.025, axis=0)
    provider_intervals["predictive_q50"] = np.quantile(replicated_rates, 0.50, axis=0)
    provider_intervals["predictive_q975"] = np.quantile(replicated_rates, 0.975, axis=0)
    provider_intervals["observed_inside_95pct_population_predictive_interval"] = (
        (provider_intervals["raw_rate"] >= provider_intervals["predictive_q025"])
        & (provider_intervals["raw_rate"] <= provider_intervals["predictive_q975"])
    )

    summary = {
        "n_providers": int(len(providers)),
        "n_posterior_predictive_replicates": int(n_replicates),
        "provider_95pct_population_predictive_coverage": float(
            provider_intervals["observed_inside_95pct_population_predictive_interval"].mean()
        ),
        "minimum_two_sided_bayesian_p": float(checks["bayesian_p_two_sided"].min()),
        "maximum_two_sided_bayesian_p": float(checks["bayesian_p_two_sided"].max()),
    }
    return checks, provider_intervals, summary


def write_report(outdir: Path, checks: pd.DataFrame, summary: dict) -> None:
    flagged = checks[checks["bayesian_p_two_sided"] < 0.05]
    if flagged.empty:
        interpretation = (
            "None of the prespecified aggregate discrepancy statistics has a two-sided Bayesian "
            "posterior-predictive p-value below 0.05. This does not prove model adequacy; it means "
            "these checks do not show a large mismatch between observed and replicated provider-rate heterogeneity."
        )
    else:
        names = ", ".join(flagged["statistic"].astype(str))
        interpretation = (
            f"The following discrepancy statistics have two-sided Bayesian posterior-predictive p-values below 0.05: {names}. "
            "The Beta-Binomial hierarchy should therefore not be treated as an adequate final service model without investigating this mismatch."
        )

    report = f"""# v0.5 posterior predictive checks

The posterior predictive checks use the same provider denominators as the observed June 2026 NHS Talking Therapies data. For each replicate, hyperparameters are drawn from the fitted hyperposterior, a provider probability is drawn from the Beta population distribution, and a new reliable-improvement count is drawn from the Binomial observation model.

The checks are intended to test whether the fitted hierarchy can reproduce broad features of the observed provider-rate distribution. They are not a test of Clinical Partners data and they do not validate provider quality comparisons.

Provider population-predictive 95% interval coverage: **{100 * summary['provider_95pct_population_predictive_coverage']:.1f}%**.

Minimum two-sided Bayesian posterior-predictive p-value across the prespecified discrepancy statistics: **{summary['minimum_two_sided_bayesian_p']:.3f}**.

{checks.to_markdown(index=False)}

## Interpretation

{interpretation}

A satisfactory aggregate PPC does not address omitted case mix, time trends, clinician effects, outcome-definition differences, suppression mechanisms or patient-level dependence. Those require richer data and a more detailed model.
"""
    (outdir / "V05_POSTERIOR_PREDICTIVE_CHECKS.md").write_text(report)


def main(path: Path, outdir: Path, n_replicates: int) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flex(path)
    providers, _ = extract_provider_counts(df)
    fit = fit_hyperposterior(providers["y"].to_numpy(), providers["n"].to_numpy(), PRIMARY_PRIOR)
    checks, provider_intervals, summary = posterior_predictive_checks(
        providers, fit, n_replicates=n_replicates
    )

    checks.to_csv(outdir / "v05_posterior_predictive_discrepancies.csv", index=False)
    provider_intervals.to_csv(outdir / "v05_provider_population_predictive_intervals.csv", index=False)
    (outdir / "v05_posterior_predictive_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_report(outdir, checks, summary)

    print("V05_POSTERIOR_PREDICTIVE_SUMMARY:", json.dumps(summary))
    print("V05_POSTERIOR_PREDICTIVE_CHECKS:\n", checks.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=2000)
    args = parser.parse_args()
    main(args.data, args.out, args.replicates)

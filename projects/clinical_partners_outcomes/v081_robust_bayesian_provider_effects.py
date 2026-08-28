from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy.optimize import minimize
from scipy.special import expit, logit, logsumexp
from scipy.stats import t as student_t

from v08_nhs_dynamic_bayesian import (
    PRIMARY_PRIOR,
    DynamicPrior,
    finite_hessian,
    load_provider_month_panel,
    normal_logpdf,
    prepare_model_arrays,
    regularised_covariance,
    two_sided_predictive_p,
)


@dataclass(frozen=True)
class EffectFamily:
    name: str
    df: float | None


CANDIDATE_FAMILIES = (
    EffectFamily("normal", None),
    EffectFamily("student_t_df10", 10.0),
    EffectFamily("student_t_df5", 5.0),
    EffectFamily("student_t_df3", 3.0),
)


def standardised_effect_quadrature(
    family: EffectFamily,
    points: int = 61,
) -> tuple[np.ndarray, np.ndarray]:
    """Return nodes/weights for a mean-zero, variance-one provider effect.

    Normal effects use Gaussian-Hermite quadrature. Student-t effects use a
    Gauss-Legendre rule on U(0,1) followed by the t quantile transform. For
    df>2 the raw t variate is multiplied by sqrt((df-2)/df), so ``tau`` has
    the same interpretation across all candidate families: provider-effect SD
    on the log-odds scale.
    """

    if family.df is None:
        nodes, weights = hermgauss(points)
        return np.sqrt(2.0) * nodes.astype(float), (
            np.log(weights.astype(float)) - 0.5 * np.log(np.pi)
        )

    if family.df <= 2:
        raise ValueError("Student-t variance standardisation requires df > 2")
    gl_nodes, gl_weights = leggauss(points)
    probability = 0.5 * (gl_nodes + 1.0)
    weights = 0.5 * gl_weights
    scale = np.sqrt((family.df - 2.0) / family.df)
    nodes = student_t.ppf(probability, df=family.df) * scale
    return nodes.astype(float), np.log(weights.astype(float))


def integrated_log_likelihood(
    parameters: np.ndarray,
    groups: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]],
    n_months: int,
    effect_nodes: np.ndarray,
    effect_log_weights: np.ndarray,
) -> float:
    parameters = np.asarray(parameters, dtype=float)
    mu = parameters[:n_months]
    tau = float(np.exp(parameters[n_months]))
    u_nodes = tau * effect_nodes
    total = 0.0
    for _, month_index, y, n in groups:
        eta = mu[month_index][None, :] + u_nodes[:, None]
        node_ll = np.sum(
            y[None, :] * eta - n[None, :] * np.logaddexp(0.0, eta), axis=1
        )
        total += float(logsumexp(effect_log_weights + node_ll))
    return total


def log_posterior_family(
    parameters: np.ndarray,
    groups: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]],
    n_months: int,
    prior: DynamicPrior,
    effect_nodes: np.ndarray,
    effect_log_weights: np.ndarray,
) -> float:
    parameters = np.asarray(parameters, dtype=float)
    mu = parameters[:n_months]
    log_tau = float(parameters[n_months])
    lp = integrated_log_likelihood(
        parameters,
        groups,
        n_months,
        effect_nodes,
        effect_log_weights,
    )
    lp += float(normal_logpdf(mu[0], prior.intercept_mean, prior.intercept_sd))
    if n_months > 1:
        lp += float(np.sum(normal_logpdf(np.diff(mu), 0.0, prior.month_step_sd)))
    lp += float(normal_logpdf(log_tau, prior.log_tau_mean, prior.log_tau_sd))
    return lp


def population_rate_draws_family(
    parameter_draws: np.ndarray,
    n_months: int,
    effect_nodes: np.ndarray,
    effect_log_weights: np.ndarray,
) -> np.ndarray:
    mu = parameter_draws[:, :n_months]
    tau = np.exp(np.clip(parameter_draws[:, n_months], -4.0, 0.7))
    weights = np.exp(effect_log_weights)
    rates = np.empty((len(parameter_draws), n_months), dtype=float)
    for month_index in range(n_months):
        eta = (
            mu[:, month_index, None]
            + tau[:, None] * effect_nodes[None, :]
        )
        rates[:, month_index] = np.sum(expit(eta) * weights[None, :], axis=1)
    return rates


def fit_family(
    panel: pd.DataFrame,
    family: EffectFamily,
    prior: DynamicPrior = PRIMARY_PRIOR,
    posterior_draws: int = 2200,
    quadrature_points: int = 61,
    seed: int = 20260828,
) -> dict:
    prepared = prepare_model_arrays(panel)
    months = prepared["months"]
    groups = prepared["groups"]
    n_months = len(months)
    effect_nodes, effect_log_weights = standardised_effect_quadrature(
        family, quadrature_points
    )

    overall = (
        panel.groupby("month", sort=True)[["y", "n"]]
        .sum()
        .assign(rate=lambda x: x["y"] / x["n"])
    )
    initial_mu = np.array(
        [
            logit(np.clip(float(overall.loc[month, "rate"]), 0.01, 0.99))
            for month in months
        ]
    )
    initial = np.r_[initial_mu, np.log(0.20)]

    def objective(theta: np.ndarray) -> float:
        value = log_posterior_family(
            theta,
            groups,
            n_months,
            prior,
            effect_nodes,
            effect_log_weights,
        )
        return 1e100 if not np.isfinite(value) else -value

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        bounds=[(-4.0, 4.0)] * n_months + [(-4.0, 0.7)],
        options={"maxiter": 700, "ftol": 1e-10, "maxls": 50},
    )
    map_parameters = np.asarray(result.x, dtype=float)
    hessian = finite_hessian(objective, map_parameters)
    covariance, hessian_meta = regularised_covariance(hessian)

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(map_parameters, covariance, size=posterior_draws)
    draws[:, :n_months] = np.clip(draws[:, :n_months], -4.0, 4.0)
    draws[:, n_months] = np.clip(draws[:, n_months], -4.0, 0.7)
    rates = population_rate_draws_family(
        draws,
        n_months,
        effect_nodes,
        effect_log_weights,
    )
    tau_draws = np.exp(draws[:, n_months])

    month_rows: list[dict] = []
    for idx, month in enumerate(months):
        q025, q50, q975 = np.quantile(rates[:, idx], [0.025, 0.5, 0.975])
        month_rows.append(
            {
                "month": month,
                "population_rate_mean": float(rates[:, idx].mean()),
                "population_rate_q025": float(q025),
                "population_rate_q50": float(q50),
                "population_rate_q975": float(q975),
                "observed_count_weighted_rate": float(overall.loc[month, "rate"]),
            }
        )

    tau_q025, tau_q50, tau_q975 = np.quantile(tau_draws, [0.025, 0.5, 0.975])
    return {
        "family": family,
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "map_log_posterior": float(-result.fun),
        "map_integrated_log_likelihood": float(
            integrated_log_likelihood(
                map_parameters,
                groups,
                n_months,
                effect_nodes,
                effect_log_weights,
            )
        ),
        "map_parameters": map_parameters,
        "covariance": covariance,
        "draws": draws,
        "population_rate_draws": rates,
        "months": months,
        "providers": prepared["providers"],
        "panel": prepared["panel"],
        "tau_mean": float(tau_draws.mean()),
        "tau_q025": float(tau_q025),
        "tau_q50": float(tau_q50),
        "tau_q975": float(tau_q975),
        "month_summary": pd.DataFrame(month_rows),
        "effect_nodes": effect_nodes,
        "effect_log_weights": effect_log_weights,
        **hessian_meta,
    }


def simulate_provider_effects(
    rng: np.random.Generator,
    family: EffectFamily,
    tau: float,
    size: int,
) -> np.ndarray:
    if family.df is None:
        return rng.normal(0.0, tau, size=size)
    scale = np.sqrt((family.df - 2.0) / family.df)
    return tau * scale * rng.standard_t(family.df, size=size)


def posterior_predictive_checks_family(
    panel: pd.DataFrame,
    fit: dict,
    replicates: int = 700,
    seed: int = 20260828,
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    family: EffectFamily = fit["family"]
    months = fit["months"]
    month_to_index = {month: i for i, month in enumerate(months)}
    providers = sorted(panel["ORG_CODE2"].unique())
    provider_to_index = {provider: i for i, provider in enumerate(providers)}
    work = panel.copy()
    month_idx = work["month"].map(month_to_index).to_numpy(dtype=int)
    provider_idx = work["ORG_CODE2"].map(provider_to_index).to_numpy(dtype=int)
    n = work["n"].to_numpy(dtype=int)
    draws = fit["draws"]
    draw_idx = rng.choice(len(draws), size=replicates, replace=len(draws) < replicates)

    metrics = ["low_tail_count_le_50", "high_tail_count_ge_85", "provider_rate_sd"]
    observed: dict[str, dict[str, float]] = {}
    predictive = {
        month: {metric: np.empty(replicates, dtype=float) for metric in metrics}
        for month in months
    }
    for month in months:
        frame = work[work["month"].eq(month)]
        rates = frame["y"].to_numpy(dtype=float) / frame["n"].to_numpy(dtype=float)
        observed[month] = {
            "low_tail_count_le_50": float(np.sum(rates <= 0.50)),
            "high_tail_count_ge_85": float(np.sum(rates >= 0.85)),
            "provider_rate_sd": float(np.std(rates, ddof=1)),
        }

    first_month, last_month = months[0], months[-1]
    observed_pivot = work[work["month"].isin([first_month, last_month])].pivot(
        index="ORG_CODE2", columns="month", values="raw_rate"
    ).dropna()
    observed_correlation = float(
        observed_pivot[first_month].corr(observed_pivot[last_month])
    )
    predictive_correlation = np.empty(replicates, dtype=float)

    for replicate, parameter_index in enumerate(draw_idx):
        parameter = draws[parameter_index]
        mu = parameter[: len(months)]
        tau = float(np.exp(parameter[len(months)]))
        provider_effect = simulate_provider_effects(
            rng,
            family,
            tau,
            len(providers),
        )
        probability = expit(mu[month_idx] + provider_effect[provider_idx])
        y_rep = rng.binomial(n, probability)
        rate_rep = y_rep / n

        for month in months:
            mask = work["month"].eq(month).to_numpy()
            values = rate_rep[mask]
            predictive[month]["low_tail_count_le_50"][replicate] = np.sum(
                values <= 0.50
            )
            predictive[month]["high_tail_count_ge_85"][replicate] = np.sum(
                values >= 0.85
            )
            predictive[month]["provider_rate_sd"][replicate] = np.std(
                values, ddof=1
            )

        temporary = pd.DataFrame(
            {
                "provider": work["ORG_CODE2"].to_numpy(),
                "month": work["month"].to_numpy(),
                "rate": rate_rep,
            }
        )
        pivot = temporary[
            temporary["month"].isin([first_month, last_month])
        ].pivot(index="provider", columns="month", values="rate").dropna()
        predictive_correlation[replicate] = pivot[first_month].corr(
            pivot[last_month]
        )

    rows: list[dict] = []
    for month in months:
        for metric in metrics:
            values = predictive[month][metric]
            value = observed[month][metric]
            q025, q50, q975 = np.quantile(values, [0.025, 0.5, 0.975])
            rows.append(
                {
                    "family": family.name,
                    "month": month,
                    "metric": metric,
                    "observed": value,
                    "predictive_mean": float(values.mean()),
                    "predictive_q025": float(q025),
                    "predictive_q50": float(q50),
                    "predictive_q975": float(q975),
                    "two_sided_bayesian_p": two_sided_predictive_p(values, value),
                }
            )

    q025, q50, q975 = np.quantile(
        predictive_correlation, [0.025, 0.5, 0.975]
    )
    persistence = {
        "family": family.name,
        "first_month": first_month,
        "last_month": last_month,
        "common_providers": int(len(observed_pivot)),
        "observed_provider_rate_correlation": observed_correlation,
        "predictive_mean": float(np.nanmean(predictive_correlation)),
        "predictive_q025": float(q025),
        "predictive_q50": float(q50),
        "predictive_q975": float(q975),
        "two_sided_bayesian_p": two_sided_predictive_p(
            predictive_correlation, observed_correlation
        ),
    }
    return pd.DataFrame(rows), persistence


def candidate_diagnostics(
    fit: dict,
    ppc: pd.DataFrame,
    persistence: dict,
) -> dict:
    latest_month = fit["months"][-1]
    latest_low = ppc[
        ppc["month"].eq(latest_month)
        & ppc["metric"].eq("low_tail_count_le_50")
    ].iloc[0]
    return {
        "family": fit["family"].name,
        "df": fit["family"].df,
        "fit_success": bool(fit["success"]),
        "iterations": int(fit["iterations"]),
        "map_integrated_log_likelihood": float(fit["map_integrated_log_likelihood"]),
        "tau_mean": float(fit["tau_mean"]),
        "tau_q025": float(fit["tau_q025"]),
        "tau_q975": float(fit["tau_q975"]),
        "n_ppc_failures_p_lt_0_05": int(
            (ppc["two_sided_bayesian_p"] < 0.05).sum()
        ),
        "n_tail_failures_p_lt_0_05": int(
            (
                ppc["metric"].isin(
                    ["low_tail_count_le_50", "high_tail_count_ge_85"]
                )
                & (ppc["two_sided_bayesian_p"] < 0.05)
            ).sum()
        ),
        "latest_month_low_tail_observed": float(latest_low["observed"]),
        "latest_month_low_tail_predictive_mean": float(latest_low["predictive_mean"]),
        "latest_month_low_tail_predictive_q975": float(latest_low["predictive_q975"]),
        "latest_month_low_tail_p": float(latest_low["two_sided_bayesian_p"]),
        "persistence_observed": float(
            persistence["observed_provider_rate_correlation"]
        ),
        "persistence_predictive_mean": float(persistence["predictive_mean"]),
        "persistence_predictive_q025": float(persistence["predictive_q025"]),
        "persistence_predictive_q975": float(persistence["predictive_q975"]),
        "persistence_p": float(persistence["two_sided_bayesian_p"]),
        "hessian_min_eigenvalue": float(fit["hessian_min_eigenvalue"]),
        "hessian_eigenvalues_clipped": int(fit["hessian_eigenvalues_clipped"]),
    }


def write_report(
    outdir: Path,
    metadata: dict,
    comparison: pd.DataFrame,
    ppc_all: pd.DataFrame,
) -> None:
    latest = sorted(ppc_all["month"].unique())[-1]
    latest_ppc = ppc_all[ppc_all["month"].eq(latest)].copy()
    report = f"""# v0.8.1 Robust Bayesian provider-effect sensitivity

## Why this analysis exists

v0.8 added six months of repeated NHS Talking Therapies provider outcome counts and a persistent Normal provider random intercept. That model reproduced broad January-to-June provider-rate persistence but still under-predicted extreme provider rates and provider-level dispersion. v0.8.1 asks a narrower model-criticism question: **is the lack of fit primarily caused by the Normal random-effect tail assumption?**

## Prespecified candidate models

Every candidate keeps the same Binomial likelihood and smoothed monthly population effects:

`y_jt ~ Binomial(n_jt, p_jt)`

`logit(p_jt) = mu_t + u_j`

Only the provider-effect distribution changes:

- Normal;
- Student-t df=10;
- Student-t df=5;
- Student-t df=3.

Student-t effects are variance-standardised, so `tau` remains the provider-effect standard deviation on the log-odds scale. Degrees of freedom are fixed **before** fitting; they are not tuned continuously to make a posterior predictive check pass. Provider effects are integrated numerically and all four models have the same number of estimated parameters.

The real-data panel contains **{metadata['providers']} providers**, **{metadata['provider_month_rows']} provider-month observations**, and **{metadata['n_months']} months**.

## Model comparison

{comparison.to_markdown(index=False, floatfmt='.4f')}

`n_ppc_failures_p_lt_0_05` counts failures across 18 prespecified month-by-discrepancy posterior predictive checks: lower-tail count, upper-tail count and provider-rate SD in each of six months. A lower count is diagnostically better, but no candidate is declared adequate solely because it has the fewest failures.

## Latest-month posterior predictive checks

{latest_ppc[['family','metric','observed','predictive_mean','predictive_q025','predictive_q975','two_sided_bayesian_p']].to_markdown(index=False, floatfmt='.4f')}

## Interpretation boundary

A heavier-tailed random-effect model can reveal that exchangeable Normal provider effects were too restrictive, but it cannot identify *why* some providers have unusually high or low aggregate outcome rates. Public provider counts lack patient-level case mix, clinician assignment, treatment composition and referral-pathway detail. A remaining PPC failure therefore motivates measured service/case-mix structure or richer temporal heterogeneity rather than further distributional tuning alone.
"""
    (outdir / "V081_ROBUST_PROVIDER_EFFECTS_REPORT.md").write_text(report)


def run_analysis(
    data_dir: Path,
    outdir: Path,
    min_months: int = 4,
    posterior_draws: int = 2200,
    ppc_replicates: int = 700,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    panel, metadata = load_provider_month_panel(data_dir, min_months=min_months)

    comparison_rows: list[dict] = []
    ppc_frames: list[pd.DataFrame] = []
    persistence_rows: list[dict] = []
    month_frames: list[pd.DataFrame] = []

    for family_index, family in enumerate(CANDIDATE_FAMILIES):
        fit = fit_family(
            panel,
            family,
            posterior_draws=posterior_draws,
            seed=20260828 + family_index,
        )
        ppc, persistence = posterior_predictive_checks_family(
            panel,
            fit,
            replicates=ppc_replicates,
            seed=20260910 + family_index,
        )
        comparison_rows.append(candidate_diagnostics(fit, ppc, persistence))
        ppc_frames.append(ppc)
        persistence_rows.append(persistence)
        month_summary = fit["month_summary"].copy()
        month_summary.insert(0, "family", family.name)
        month_frames.append(month_summary)

    comparison = pd.DataFrame(comparison_rows)
    ppc_all = pd.concat(ppc_frames, ignore_index=True)
    persistence_all = pd.DataFrame(persistence_rows)
    month_all = pd.concat(month_frames, ignore_index=True)

    # Diagnostic ordering is prespecified: fewer PPC failures, then fewer tail
    # failures, then smaller latest-month lower-tail mean discrepancy. This is a
    # ranking for model criticism, not an automatic acceptance rule.
    comparison["latest_low_tail_abs_mean_error"] = (
        comparison["latest_month_low_tail_observed"]
        - comparison["latest_month_low_tail_predictive_mean"]
    ).abs()
    comparison = comparison.sort_values(
        [
            "n_ppc_failures_p_lt_0_05",
            "n_tail_failures_p_lt_0_05",
            "latest_low_tail_abs_mean_error",
        ]
    ).reset_index(drop=True)

    best = comparison.iloc[0]
    normal = comparison[comparison["family"].eq("normal")].iloc[0]
    any_candidate_adequate = bool(
        (comparison["n_ppc_failures_p_lt_0_05"] == 0).any()
    )
    payload = {
        "version": "0.8.1",
        "dataset": "Official NHS Talking Therapies Monthly Activity Data Files, Jan-Jun 2026",
        "data": metadata,
        "candidate_families": [family.name for family in CANDIDATE_FAMILIES],
        "selection_rule": (
            "Diagnostic ordering only: minimise 18 prespecified PPC failures, then tail failures, "
            "then latest-month lower-tail mean error; no model is accepted solely by rank."
        ),
        "best_diagnostic_family": str(best["family"]),
        "best_n_ppc_failures": int(best["n_ppc_failures_p_lt_0_05"]),
        "normal_n_ppc_failures": int(normal["n_ppc_failures_p_lt_0_05"]),
        "best_n_tail_failures": int(best["n_tail_failures_p_lt_0_05"]),
        "normal_n_tail_failures": int(normal["n_tail_failures_p_lt_0_05"]),
        "any_candidate_passes_all_prespecified_ppcs": any_candidate_adequate,
        "interpretation_boundary": (
            "Heavy-tailed random effects are a distributional sensitivity analysis of aggregate provider heterogeneity; "
            "they do not identify patient case mix, clinician effects or causal service quality."
        ),
    }

    comparison.to_csv(outdir / "v081_family_comparison.csv", index=False)
    ppc_all.to_csv(outdir / "v081_family_ppc.csv", index=False)
    persistence_all.to_csv(outdir / "v081_persistence_ppc.csv", index=False)
    month_all.to_csv(outdir / "v081_month_posterior_summary.csv", index=False)
    (outdir / "v081_robust_provider_effects_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    write_report(outdir, metadata, comparison, ppc_all)

    print("V081_SUMMARY:", json.dumps(payload))
    print("V081_COMPARISON:\n", comparison.to_string(index=False))
    print("V081_LATEST_PPC:\n", ppc_all[ppc_all["month"].eq("2026-06")].to_string(index=False))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-months", type=int, default=4)
    parser.add_argument("--posterior-draws", type=int, default=2200)
    parser.add_argument("--ppc-replicates", type=int, default=700)
    args = parser.parse_args()
    run_analysis(
        args.data_dir,
        args.out,
        min_months=args.min_months,
        posterior_draws=args.posterior_draws,
        ppc_replicates=args.ppc_replicates,
    )

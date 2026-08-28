from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import expit, logit, logsumexp

from v03_nhs_schema_audit import read_csv_flex
from v05_bayesian_partial_pooling import extract_provider_counts, weighted_quantile


@dataclass(frozen=True)
class DynamicPrior:
    name: str
    intercept_mean: float
    intercept_sd: float
    month_step_sd: float
    log_tau_mean: float
    log_tau_sd: float


PRIMARY_PRIOR = DynamicPrior(
    "primary",
    intercept_mean=float(logit(0.68)),
    intercept_sd=1.0,
    month_step_sd=0.15,
    log_tau_mean=float(np.log(0.25)),
    log_tau_sd=0.8,
)
BROAD_PRIOR = DynamicPrior(
    "broad",
    intercept_mean=float(logit(0.68)),
    intercept_sd=1.8,
    month_step_sd=0.35,
    log_tau_mean=float(np.log(0.25)),
    log_tau_sd=1.3,
)


def normal_logpdf(x: np.ndarray | float, mean: float, sd: float) -> np.ndarray | float:
    z = (np.asarray(x) - mean) / sd
    return -0.5 * z * z - np.log(sd) - 0.5 * np.log(2.0 * np.pi)


def load_provider_month_panel(data_dir: Path, min_months: int = 4) -> tuple[pd.DataFrame, dict]:
    rows: list[pd.DataFrame] = []
    source_meta: dict[str, dict] = {}
    files = sorted(data_dir.glob("monthly_activity_????-??.csv"))
    if not files:
        raise FileNotFoundError(f"No monthly_activity_YYYY-MM.csv files in {data_dir}")

    for path in files:
        month = path.stem.replace("monthly_activity_", "")
        frame = read_csv_flex(path)
        providers, meta = extract_provider_counts(frame)
        providers = providers.copy()
        providers["month"] = month
        rows.append(providers[["ORG_CODE2", "ORG_NAME2", "month", "n", "y", "raw_rate"]])
        source_meta[month] = meta

    panel = pd.concat(rows, ignore_index=True)
    panel["month"] = panel["month"].astype(str)
    month_order = sorted(panel["month"].unique())
    provider_months = panel.groupby("ORG_CODE2")["month"].nunique()
    keep = provider_months[provider_months >= min_months].index
    filtered = panel[panel["ORG_CODE2"].isin(keep)].copy()
    filtered = filtered.sort_values(["ORG_CODE2", "month"]).reset_index(drop=True)

    if filtered["month"].nunique() < 3:
        raise ValueError("Dynamic model requires at least three months")
    if filtered["ORG_CODE2"].nunique() < 20:
        raise ValueError("Dynamic model requires at least twenty providers")

    metadata = {
        "source_files": [path.name for path in files],
        "months": month_order,
        "n_months": len(month_order),
        "provider_month_rows_before_continuity_filter": int(len(panel)),
        "provider_month_rows": int(len(filtered)),
        "providers_before_continuity_filter": int(panel["ORG_CODE2"].nunique()),
        "providers": int(filtered["ORG_CODE2"].nunique()),
        "min_months_required": int(min_months),
        "providers_observed_all_months": int(
            (filtered.groupby("ORG_CODE2")["month"].nunique() == len(month_order)).sum()
        ),
        "monthly_source_metadata": source_meta,
    }
    return filtered, metadata


def prepare_model_arrays(panel: pd.DataFrame) -> dict:
    months = sorted(panel["month"].unique())
    month_to_index = {month: i for i, month in enumerate(months)}
    providers = sorted(panel["ORG_CODE2"].unique())
    provider_to_index = {provider: i for i, provider in enumerate(providers)}
    work = panel.copy()
    work["month_index"] = work["month"].map(month_to_index).astype(int)
    work["provider_index"] = work["ORG_CODE2"].map(provider_to_index).astype(int)
    groups = []
    for provider_index, frame in work.groupby("provider_index", sort=True):
        groups.append(
            (
                int(provider_index),
                frame["month_index"].to_numpy(dtype=int),
                frame["y"].to_numpy(dtype=float),
                frame["n"].to_numpy(dtype=float),
            )
        )
    return {
        "panel": work,
        "months": months,
        "providers": providers,
        "groups": groups,
    }


def gh_rule(points: int = 25) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(points)
    log_weights = np.log(weights) - 0.5 * np.log(np.pi)
    return nodes.astype(float), log_weights.astype(float)


def log_posterior(
    parameters: np.ndarray,
    groups: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]],
    n_months: int,
    prior: DynamicPrior,
    gh_nodes: np.ndarray,
    gh_log_weights: np.ndarray,
) -> float:
    parameters = np.asarray(parameters, dtype=float)
    mu = parameters[:n_months]
    log_tau = float(parameters[n_months])
    tau = float(np.exp(log_tau))
    u_nodes = np.sqrt(2.0) * tau * gh_nodes

    lp = float(normal_logpdf(mu[0], prior.intercept_mean, prior.intercept_sd))
    if n_months > 1:
        lp += float(np.sum(normal_logpdf(np.diff(mu), 0.0, prior.month_step_sd)))
    lp += float(normal_logpdf(log_tau, prior.log_tau_mean, prior.log_tau_sd))

    for _, month_index, y, n in groups:
        eta = mu[month_index][None, :] + u_nodes[:, None]
        node_ll = np.sum(y[None, :] * eta - n[None, :] * np.logaddexp(0.0, eta), axis=1)
        lp += float(logsumexp(gh_log_weights + node_ll))
    return lp


def negative_log_posterior(*args, **kwargs) -> float:
    value = log_posterior(*args, **kwargs)
    if not np.isfinite(value):
        return 1e100
    return -value


def finite_hessian(function, x: np.ndarray, eps: float = 1e-3) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = len(x)
    hessian = np.zeros((n, n), dtype=float)
    f0 = float(function(x))
    for i in range(n):
        ei = np.zeros(n)
        ei[i] = eps
        hessian[i, i] = (function(x + ei) - 2.0 * f0 + function(x - ei)) / (eps * eps)
        for j in range(i + 1, n):
            ej = np.zeros(n)
            ej[j] = eps
            value = (
                function(x + ei + ej)
                - function(x + ei - ej)
                - function(x - ei + ej)
                + function(x - ei - ej)
            ) / (4.0 * eps * eps)
            hessian[i, j] = value
            hessian[j, i] = value
    return 0.5 * (hessian + hessian.T)


def regularised_covariance(hessian: np.ndarray) -> tuple[np.ndarray, dict]:
    eigenvalues, eigenvectors = np.linalg.eigh(hessian)
    floor = 1e-5
    clipped = np.maximum(eigenvalues, floor)
    covariance = eigenvectors @ np.diag(1.0 / clipped) @ eigenvectors.T
    return covariance, {
        "hessian_min_eigenvalue": float(eigenvalues.min()),
        "hessian_max_eigenvalue": float(eigenvalues.max()),
        "hessian_eigenvalues_clipped": int(np.sum(eigenvalues < floor)),
    }


def population_rate_draws(
    parameter_draws: np.ndarray,
    n_months: int,
    gh_nodes: np.ndarray,
    gh_log_weights: np.ndarray,
) -> np.ndarray:
    mu = parameter_draws[:, :n_months]
    tau = np.exp(np.clip(parameter_draws[:, n_months], -4.0, 0.5))
    weights = np.exp(gh_log_weights)
    rates = np.empty((len(parameter_draws), n_months), dtype=float)
    for month_index in range(n_months):
        eta = mu[:, month_index, None] + np.sqrt(2.0) * tau[:, None] * gh_nodes[None, :]
        rates[:, month_index] = np.sum(expit(eta) * weights[None, :], axis=1)
    return rates


def fit_dynamic_model(
    panel: pd.DataFrame,
    prior: DynamicPrior = PRIMARY_PRIOR,
    posterior_draws: int = 3000,
    seed: int = 20260828,
) -> dict:
    prepared = prepare_model_arrays(panel)
    months = prepared["months"]
    groups = prepared["groups"]
    n_months = len(months)
    gh_nodes, gh_log_weights = gh_rule(25)

    overall = (
        panel.groupby("month", sort=True)[["y", "n"]].sum().assign(rate=lambda x: x["y"] / x["n"])
    )
    initial_mu = np.array(
        [logit(np.clip(float(overall.loc[month, "rate"]), 0.01, 0.99)) for month in months]
    )
    initial = np.r_[initial_mu, np.log(0.20)]

    objective = lambda theta: negative_log_posterior(
        theta, groups, n_months, prior, gh_nodes, gh_log_weights
    )
    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        bounds=[(-4.0, 4.0)] * n_months + [(-4.0, 0.5)],
        options={"maxiter": 600, "ftol": 1e-10, "maxls": 40},
    )
    map_parameters = np.asarray(result.x, dtype=float)
    hessian = finite_hessian(objective, map_parameters)
    covariance, hessian_meta = regularised_covariance(hessian)

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(map_parameters, covariance, size=posterior_draws)
    draws[:, :n_months] = np.clip(draws[:, :n_months], -4.0, 4.0)
    draws[:, n_months] = np.clip(draws[:, n_months], -4.0, 0.5)
    rates = population_rate_draws(draws, n_months, gh_nodes, gh_log_weights)
    tau_draws = np.exp(draws[:, n_months])

    month_rows = []
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
        "prior": prior.name,
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "map_log_posterior": float(-result.fun),
        "map_parameters": map_parameters,
        "covariance": covariance,
        "draws": draws,
        "population_rate_draws": rates,
        "months": months,
        "providers": prepared["providers"],
        "groups": groups,
        "panel": prepared["panel"],
        "tau_mean": float(tau_draws.mean()),
        "tau_q025": float(tau_q025),
        "tau_q50": float(tau_q50),
        "tau_q975": float(tau_q975),
        "month_summary": pd.DataFrame(month_rows),
        **hessian_meta,
    }


def provider_posterior_summary(panel: pd.DataFrame, fit: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    months = fit["months"]
    mu = fit["map_parameters"][: len(months)]
    tau = float(np.exp(fit["map_parameters"][len(months)]))
    gh_nodes, gh_log_weights = gh_rule(41)
    u_nodes = np.sqrt(2.0) * tau * gh_nodes
    month_to_index = {month: i for i, month in enumerate(months)}

    provider_rows: list[dict] = []
    provider_month_rows: list[dict] = []
    for provider_code, frame in panel.groupby("ORG_CODE2", sort=True):
        month_index = frame["month"].map(month_to_index).to_numpy(dtype=int)
        y = frame["y"].to_numpy(dtype=float)
        n = frame["n"].to_numpy(dtype=float)
        eta = mu[month_index][None, :] + u_nodes[:, None]
        node_ll = np.sum(y[None, :] * eta - n[None, :] * np.logaddexp(0.0, eta), axis=1)
        log_weights = gh_log_weights + node_ll
        log_weights -= logsumexp(log_weights)
        weights = np.exp(log_weights)
        u_mean = float(np.sum(weights * u_nodes))
        u_q025 = weighted_quantile(u_nodes, weights, 0.025)
        u_q975 = weighted_quantile(u_nodes, weights, 0.975)
        provider_name = str(frame["ORG_NAME2"].iloc[-1])
        provider_rows.append(
            {
                "provider_code": provider_code,
                "provider_name": provider_name,
                "months_observed": int(len(frame)),
                "random_intercept_mean": u_mean,
                "random_intercept_q025": u_q025,
                "random_intercept_q975": u_q975,
                "pooled_raw_rate": float(frame["y"].sum() / frame["n"].sum()),
            }
        )
        for row in frame.itertuples(index=False):
            idx = month_to_index[row.month]
            posterior_rate = float(np.sum(weights * expit(mu[idx] + u_nodes)))
            provider_month_rows.append(
                {
                    "provider_code": provider_code,
                    "provider_name": provider_name,
                    "month": row.month,
                    "n": int(row.n),
                    "y": int(row.y),
                    "raw_rate": float(row.raw_rate),
                    "posterior_rate": posterior_rate,
                    "shrinkage_percentage_points": 100.0 * (posterior_rate - float(row.raw_rate)),
                }
            )
    return pd.DataFrame(provider_rows), pd.DataFrame(provider_month_rows)


def two_sided_predictive_p(replicates: np.ndarray, observed: float) -> float:
    ge = float(np.mean(replicates >= observed))
    le = float(np.mean(replicates <= observed))
    return float(min(1.0, 2.0 * min(ge, le)))


def posterior_predictive_checks(
    panel: pd.DataFrame,
    fit: dict,
    replicates: int = 600,
    seed: int = 20260828,
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
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

    metric_names = ["low_tail_count_le_50", "high_tail_count_ge_85", "provider_rate_sd"]
    observed_by_month: dict[str, dict[str, float]] = {}
    rep_by_month = {
        month: {metric: np.empty(replicates, dtype=float) for metric in metric_names}
        for month in months
    }

    for month in months:
        frame = work[work["month"].eq(month)]
        rates = frame["y"].to_numpy(dtype=float) / frame["n"].to_numpy(dtype=float)
        observed_by_month[month] = {
            "low_tail_count_le_50": float(np.sum(rates <= 0.50)),
            "high_tail_count_ge_85": float(np.sum(rates >= 0.85)),
            "provider_rate_sd": float(np.std(rates, ddof=1)),
        }

    first_month, last_month = months[0], months[-1]
    observed_pivot = work[work["month"].isin([first_month, last_month])].pivot(
        index="ORG_CODE2", columns="month", values="raw_rate"
    ).dropna()
    observed_corr = float(observed_pivot[first_month].corr(observed_pivot[last_month]))
    rep_corr = np.empty(replicates, dtype=float)

    for r, parameter_index in enumerate(draw_idx):
        parameter = draws[parameter_index]
        mu = parameter[: len(months)]
        tau = float(np.exp(parameter[len(months)]))
        u = rng.normal(0.0, tau, size=len(providers))
        probability = expit(mu[month_idx] + u[provider_idx])
        y_rep = rng.binomial(n, probability)
        rate_rep = y_rep / n
        for month in months:
            mask = work["month"].eq(month).to_numpy()
            values = rate_rep[mask]
            rep_by_month[month]["low_tail_count_le_50"][r] = np.sum(values <= 0.50)
            rep_by_month[month]["high_tail_count_ge_85"][r] = np.sum(values >= 0.85)
            rep_by_month[month]["provider_rate_sd"][r] = np.std(values, ddof=1)

        temp = pd.DataFrame(
            {
                "provider": work["ORG_CODE2"].to_numpy(),
                "month": work["month"].to_numpy(),
                "rate": rate_rep,
            }
        )
        pivot = temp[temp["month"].isin([first_month, last_month])].pivot(
            index="provider", columns="month", values="rate"
        ).dropna()
        rep_corr[r] = pivot[first_month].corr(pivot[last_month])

    rows: list[dict] = []
    for month in months:
        for metric in metric_names:
            values = rep_by_month[month][metric]
            observed = observed_by_month[month][metric]
            q025, q50, q975 = np.quantile(values, [0.025, 0.5, 0.975])
            rows.append(
                {
                    "month": month,
                    "metric": metric,
                    "observed": observed,
                    "predictive_mean": float(values.mean()),
                    "predictive_q025": float(q025),
                    "predictive_q50": float(q50),
                    "predictive_q975": float(q975),
                    "two_sided_bayesian_p": two_sided_predictive_p(values, observed),
                }
            )
    q025, q50, q975 = np.quantile(rep_corr, [0.025, 0.5, 0.975])
    persistence = {
        "first_month": first_month,
        "last_month": last_month,
        "common_providers": int(len(observed_pivot)),
        "observed_provider_rate_correlation": observed_corr,
        "predictive_mean": float(np.nanmean(rep_corr)),
        "predictive_q025": float(q025),
        "predictive_q50": float(q50),
        "predictive_q975": float(q975),
        "two_sided_bayesian_p": two_sided_predictive_p(rep_corr, observed_corr),
    }
    return pd.DataFrame(rows), persistence


def compare_priors(primary: dict, broad: dict) -> dict:
    left = primary["month_summary"].set_index("month")
    right = broad["month_summary"].set_index("month")
    diff = 100.0 * (
        left["population_rate_mean"] - right["population_rate_mean"]
    ).abs()
    return {
        "max_month_population_rate_change_percentage_points": float(diff.max()),
        "median_month_population_rate_change_percentage_points": float(diff.median()),
        "tau_mean_primary": float(primary["tau_mean"]),
        "tau_mean_broad": float(broad["tau_mean"]),
        "absolute_tau_mean_change": float(abs(primary["tau_mean"] - broad["tau_mean"])),
    }


def write_report(
    outdir: Path,
    metadata: dict,
    primary: dict,
    provider_summary: pd.DataFrame,
    provider_month: pd.DataFrame,
    ppc: pd.DataFrame,
    persistence: dict,
    sensitivity: dict,
) -> None:
    month_table = primary["month_summary"].copy()
    month_table[["population_rate_mean", "population_rate_q025", "population_rate_q975", "observed_count_weighted_rate"]] *= 100.0
    june = ppc[ppc["month"].eq(primary["months"][-1])].copy()
    report = f"""# v0.8 Dynamic Bayesian service hierarchy

## Research question

Can repeated provider-level NHS Talking Therapies outcome counts explain the lower-tail lack of fit seen in the v0.5 single-month exchangeable Beta-Binomial model, while preserving denominator-aware partial pooling?

## Real public data

The workflow downloads the official NHS Talking Therapies Monthly Activity Data Files for {primary['months'][0]} through {primary['months'][-1]}. After requiring at least {metadata['min_months_required']} observed months, the analysis contains **{metadata['providers']} providers** and **{metadata['provider_month_rows']} provider-month count pairs**. No Clinical Partners patient data are used.

## Model

For provider j and month t:

`y_jt ~ Binomial(n_jt, p_jt)`

`logit(p_jt) = mu_t + u_j`

`u_j ~ Normal(0, tau^2)`

The monthly population logits follow a first-order smoothing prior, `mu_t - mu_(t-1) ~ Normal(0, sigma_month^2)`. Provider random effects are integrated out with Gaussian-Hermite quadrature. Posterior uncertainty for the month effects and provider heterogeneity is approximated by a Laplace expansion at the posterior mode and checked under a broader prior.

Optimiser success: **{primary['success']}** ({primary['message']}). Posterior provider heterogeneity `tau`: mean **{primary['tau_mean']:.3f}**, 95% interval **{primary['tau_q025']:.3f}-{primary['tau_q975']:.3f}** on the log-odds scale.

## Population outcome trajectory

{month_table[['month','observed_count_weighted_rate','population_rate_mean','population_rate_q025','population_rate_q975']].to_markdown(index=False, floatfmt='.2f')}

The model does not treat these month-to-month changes as causal effects. They are repeated service-level outcome summaries with persistent provider heterogeneity.

## Provider partial pooling

Median absolute provider-month shrinkage is **{provider_month['shrinkage_percentage_points'].abs().median():.2f} percentage points**; the 90th percentile is **{provider_month['shrinkage_percentage_points'].abs().quantile(0.90):.2f} percentage points**. Provider random effects are estimated from all observed months rather than from one denominator in isolation.

## Posterior predictive checks

The v0.5 model failed a June lower-tail check. v0.8 repeats lower- and upper-tail provider checks month by month and also checks the persistence of provider rates from the first to the last month.

Latest-month checks:

{june[['metric','observed','predictive_mean','predictive_q025','predictive_q975','two_sided_bayesian_p']].to_markdown(index=False, floatfmt='.3f')}

First-to-last provider-rate correlation: observed **{persistence['observed_provider_rate_correlation']:.3f}** versus predictive mean **{persistence['predictive_mean']:.3f}** (95% predictive interval {persistence['predictive_q025']:.3f}-{persistence['predictive_q975']:.3f}; two-sided Bayesian p={persistence['two_sided_bayesian_p']:.3f}).

A failed PPC is retained as model criticism, not treated as a software failure. If the dynamic logit-normal hierarchy still misses an important tail or persistence feature, the next scientific model should test heavier-tailed provider effects, case-mix/service-type information where public data support it, or richer temporal structure.

## Prior sensitivity

Maximum monthly population-rate posterior-mean change under the broader prior: **{sensitivity['max_month_population_rate_change_percentage_points']:.3f} percentage points**. Absolute change in posterior mean `tau`: **{sensitivity['absolute_tau_mean_change']:.3f}**.

## Interpretation boundary

This is a provider-by-month public-data demonstration of Bayesian hierarchical modelling, repeated service outcomes, partial pooling, posterior uncertainty and model criticism. The public aggregate files do not expose patient-to-clinician assignments, patient-level case mix, treatment timestamps or referral pathways. It therefore does not claim clinician effects, patient-level causal effects or a Clinical Partners production model.
"""
    (outdir / "V08_DYNAMIC_BAYESIAN_SERVICE_REPORT.md").write_text(report)


def run_analysis(
    data_dir: Path,
    outdir: Path,
    min_months: int = 4,
    posterior_draws: int = 3000,
    ppc_replicates: int = 600,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    panel, metadata = load_provider_month_panel(data_dir, min_months=min_months)
    primary = fit_dynamic_model(panel, PRIMARY_PRIOR, posterior_draws=posterior_draws)
    broad = fit_dynamic_model(panel, BROAD_PRIOR, posterior_draws=max(1200, posterior_draws // 2), seed=20260829)
    provider_summary, provider_month = provider_posterior_summary(panel, primary)
    ppc, persistence = posterior_predictive_checks(panel, primary, replicates=ppc_replicates)
    sensitivity = compare_priors(primary, broad)

    panel.to_csv(outdir / "v08_provider_month_counts.csv", index=False)
    primary["month_summary"].to_csv(outdir / "v08_month_posterior_summary.csv", index=False)
    provider_summary.to_csv(outdir / "v08_provider_random_effects.csv", index=False)
    provider_month.to_csv(outdir / "v08_provider_month_partial_pooling.csv", index=False)
    ppc.to_csv(outdir / "v08_dynamic_ppc.csv", index=False)

    latest_month = primary["months"][-1]
    latest_low = ppc[(ppc["month"].eq(latest_month)) & (ppc["metric"].eq("low_tail_count_le_50"))].iloc[0]
    payload = {
        "version": "0.8",
        "dataset": "Official NHS Talking Therapies Monthly Activity Data Files",
        "data": metadata,
        "model": {
            "formula": "y_jt ~ Binomial(n_jt,p_jt); logit(p_jt)=mu_t+u_j; u_j~Normal(0,tau^2)",
            "temporal_prior": "first-order Gaussian prior on consecutive month population logits",
            "provider_integration": "25-point Gaussian-Hermite quadrature",
            "posterior_uncertainty": "finite-difference Hessian Laplace approximation at MAP",
            "fit_success": bool(primary["success"]),
            "fit_message": primary["message"],
            "iterations": primary["iterations"],
            "tau_mean": primary["tau_mean"],
            "tau_q025": primary["tau_q025"],
            "tau_q975": primary["tau_q975"],
            "hessian_min_eigenvalue": primary["hessian_min_eigenvalue"],
            "hessian_eigenvalues_clipped": primary["hessian_eigenvalues_clipped"],
        },
        "latest_month_lower_tail_ppc": {
            "month": latest_month,
            "observed": float(latest_low["observed"]),
            "predictive_mean": float(latest_low["predictive_mean"]),
            "predictive_q025": float(latest_low["predictive_q025"]),
            "predictive_q975": float(latest_low["predictive_q975"]),
            "two_sided_bayesian_p": float(latest_low["two_sided_bayesian_p"]),
        },
        "provider_rate_persistence_ppc": persistence,
        "prior_sensitivity": sensitivity,
        "median_abs_provider_month_shrinkage_pp": float(provider_month["shrinkage_percentage_points"].abs().median()),
        "p90_abs_provider_month_shrinkage_pp": float(provider_month["shrinkage_percentage_points"].abs().quantile(0.90)),
        "interpretation_boundary": (
            "Provider-by-month public aggregate evidence only; no patient-clinician hierarchy, patient-level case mix, "
            "referral pathway or causal attribution is claimed."
        ),
    }
    (outdir / "v08_dynamic_bayesian_summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    write_report(outdir, metadata, primary, provider_summary, provider_month, ppc, persistence, sensitivity)
    print("V08_DYNAMIC_BAYESIAN:", json.dumps(payload))
    print("V08_MONTHS:\n", primary["month_summary"].to_string(index=False))
    print("V08_PPC:\n", ppc.to_string(index=False))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-months", type=int, default=4)
    parser.add_argument("--posterior-draws", type=int, default=3000)
    parser.add_argument("--ppc-replicates", type=int, default=600)
    args = parser.parse_args()
    run_analysis(
        args.data_dir,
        args.out,
        min_months=args.min_months,
        posterior_draws=args.posterior_draws,
        ppc_replicates=args.ppc_replicates,
    )

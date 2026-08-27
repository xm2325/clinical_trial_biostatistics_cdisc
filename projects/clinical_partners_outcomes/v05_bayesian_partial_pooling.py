from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import betaln, expit, logit, logsumexp

from v03_nhs_schema_audit import read_csv_flex

VALUE_COL = "MEASURE_VALUE_SUPPRESSED"
DENOMINATOR = "Count_FinishedCourseTreatment"
SUCCESS = "Count_ReliableImprovement"
PERCENTAGE = "Percentage_ReliableImprovement"


@dataclass(frozen=True)
class PriorSpec:
    name: str
    u_mean: float
    u_sd: float
    v_mean: float
    v_sd: float


PRIMARY_PRIOR = PriorSpec("primary", 0.0, 1.5, float(np.log(30.0)), 1.2)
BROAD_PRIOR = PriorSpec("broad", 0.0, 2.5, float(np.log(20.0)), 2.0)


def normal_logpdf(x: np.ndarray, mean: float, sd: float) -> np.ndarray:
    z = (x - mean) / sd
    return -0.5 * z * z - np.log(sd) - 0.5 * np.log(2.0 * np.pi)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    x = np.asarray(values)[order]
    w = np.asarray(weights)[order]
    cdf = np.cumsum(w)
    cdf /= cdf[-1]
    return float(np.interp(q, cdf, x))


def conditional_posterior_mean(y: np.ndarray, n: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    return (np.asarray(y, dtype=float) + alpha) / (np.asarray(n, dtype=float) + alpha + beta)


def extract_provider_counts(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = {"GROUP_TYPE", "ORG_CODE2", "ORG_NAME2", "MEASURE_NAME", VALUE_COL}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"NHS monthly activity file missing required columns: {missing}")

    work = df[["GROUP_TYPE", "ORG_CODE2", "ORG_NAME2", "MEASURE_NAME", VALUE_COL]].copy()
    work["value"] = pd.to_numeric(work[VALUE_COL], errors="coerce")

    provider = work[
        work["GROUP_TYPE"].eq("Provider")
        & work["MEASURE_NAME"].isin([DENOMINATOR, SUCCESS, PERCENTAGE])
    ].copy()
    pivot = provider.pivot_table(
        index=["ORG_CODE2", "ORG_NAME2"], columns="MEASURE_NAME", values="value", aggfunc="first"
    ).reset_index()

    pivot = pivot.dropna(subset=[DENOMINATOR, SUCCESS]).copy()
    pivot["n"] = pivot[DENOMINATOR].round().astype(int)
    pivot["y"] = pivot[SUCCESS].round().astype(int)
    pivot = pivot[(pivot["n"] > 0) & (pivot["y"] >= 0) & (pivot["y"] <= pivot["n"])].copy()
    pivot["raw_rate"] = pivot["y"] / pivot["n"]
    pivot = pivot.sort_values(["n", "ORG_CODE2"]).reset_index(drop=True)

    england = work[
        work["GROUP_TYPE"].eq("England")
        & work["MEASURE_NAME"].isin([DENOMINATOR, SUCCESS, PERCENTAGE])
    ].drop_duplicates("MEASURE_NAME")
    eng = dict(zip(england["MEASURE_NAME"], england["value"]))
    eng_n = int(round(float(eng[DENOMINATOR])))
    eng_y = int(round(float(eng[SUCCESS])))
    eng_rate = eng_y / eng_n
    published_pct = float(eng.get(PERCENTAGE, np.nan))

    if np.isfinite(published_pct) and not np.isclose(100.0 * eng_rate, published_pct, atol=0.051):
        raise ValueError(
            f"England reliable-improvement count ratio {100 * eng_rate:.3f}% does not match published {published_pct:.3f}%"
        )

    metadata = {
        "provider_rows_complete": int(len(pivot)),
        "england_finished_course_treatment": eng_n,
        "england_reliable_improvement": eng_y,
        "england_reliable_improvement_rate": float(eng_rate),
        "england_published_percentage": published_pct,
        "suppressed_or_missing_provider_rows_excluded": int(
            provider[["ORG_CODE2", "ORG_NAME2"]].drop_duplicates().shape[0] - len(pivot)
        ),
    }
    return pivot, metadata


def fit_hyperposterior(y: np.ndarray, n: np.ndarray, prior: PriorSpec) -> dict:
    y = np.asarray(y, dtype=float)
    n = np.asarray(n, dtype=float)
    if y.ndim != 1 or n.ndim != 1 or len(y) != len(n) or len(y) < 3:
        raise ValueError("y and n must be one-dimensional arrays with at least three providers")
    if np.any(y < 0) or np.any(n <= 0) or np.any(y > n):
        raise ValueError("Counts must satisfy 0 <= y <= n and n > 0")

    # Grid is on unconstrained u=logit(m) and v=log(kappa).
    u_grid = np.linspace(logit(0.35), logit(0.90), 181)
    v_grid = np.linspace(np.log(1.0), np.log(500.0), 181)
    u, v = np.meshgrid(u_grid, v_grid, indexing="ij")
    m = expit(u)
    kappa = np.exp(v)
    alpha = m * kappa
    beta = (1.0 - m) * kappa

    logp = normal_logpdf(u, prior.u_mean, prior.u_sd) + normal_logpdf(v, prior.v_mean, prior.v_sd)
    for yj, nj in zip(y, n):
        logp += betaln(yj + alpha, nj - yj + beta) - betaln(alpha, beta)
    logp -= logsumexp(logp)
    weights = np.exp(logp)

    return {
        "u": u.ravel(),
        "v": v.ravel(),
        "m": m.ravel(),
        "kappa": kappa.ravel(),
        "alpha": alpha.ravel(),
        "beta": beta.ravel(),
        "weights": weights.ravel(),
        "prior": prior,
    }


def summarise_hyperposterior(fit: dict) -> dict:
    w = fit["weights"]
    out = {"prior": fit["prior"].name}
    for key in ("m", "kappa"):
        values = fit[key]
        out[f"{key}_mean"] = float(np.sum(w * values))
        out[f"{key}_q025"] = weighted_quantile(values, w, 0.025)
        out[f"{key}_q50"] = weighted_quantile(values, w, 0.50)
        out[f"{key}_q975"] = weighted_quantile(values, w, 0.975)
    return out


def provider_posterior_summary(
    providers: pd.DataFrame,
    fit: dict,
    reference_rate: float,
    seed: int = 20260827,
    draws_per_provider: int = 6000,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    w = fit["weights"]
    alpha = fit["alpha"]
    beta = fit["beta"]
    grid_idx = np.arange(len(w))

    rows: list[dict] = []
    for row in providers.itertuples(index=False):
        y = int(row.y)
        n = int(row.n)
        conditional_means = (y + alpha) / (n + alpha + beta)
        posterior_mean = float(np.sum(w * conditional_means))

        idx = rng.choice(grid_idx, size=draws_per_provider, replace=True, p=w)
        draws = rng.beta(y + alpha[idx], n - y + beta[idx])
        q025, q50, q975 = np.quantile(draws, [0.025, 0.5, 0.975])
        raw_rate = float(row.raw_rate)
        rows.append(
            {
                "provider_code": row.ORG_CODE2,
                "provider_name": row.ORG_NAME2,
                "finished_course_treatment": n,
                "reliable_improvement": y,
                "raw_rate": raw_rate,
                "posterior_mean": posterior_mean,
                "posterior_median": float(q50),
                "posterior_q025": float(q025),
                "posterior_q975": float(q975),
                "shrinkage_percentage_points": 100.0 * (posterior_mean - raw_rate),
                "abs_shrinkage_percentage_points": 100.0 * abs(posterior_mean - raw_rate),
                "probability_above_england_rate": float(np.mean(draws > reference_rate)),
            }
        )
    return pd.DataFrame(rows).sort_values("finished_course_treatment").reset_index(drop=True)


def fit_one_analysis(providers: pd.DataFrame, prior: PriorSpec, reference_rate: float) -> tuple[dict, pd.DataFrame]:
    fit = fit_hyperposterior(providers["y"].to_numpy(), providers["n"].to_numpy(), prior)
    summary = summarise_hyperposterior(fit)
    provider_summary = provider_posterior_summary(providers, fit, reference_rate)
    return summary, provider_summary


def prior_sensitivity(primary: pd.DataFrame, broad: pd.DataFrame) -> pd.DataFrame:
    cols = ["provider_code", "posterior_mean"]
    merged = primary[cols].merge(broad[cols], on="provider_code", suffixes=("_primary", "_broad"))
    merged["absolute_change_percentage_points"] = 100.0 * (
        merged["posterior_mean_primary"] - merged["posterior_mean_broad"]
    ).abs()
    return merged.sort_values("absolute_change_percentage_points", ascending=False).reset_index(drop=True)


def write_report(
    outdir: Path,
    metadata: dict,
    hyper: dict,
    provider_summary: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> None:
    smallest = provider_summary.nsmallest(5, "finished_course_treatment")
    largest = provider_summary.nlargest(5, "finished_course_treatment")
    report = f"""# v0.5 Bayesian partial-pooling service benchmark

## Data and estimand

This analysis uses the official NHS Talking Therapies June 2026 Monthly Activity Data File. It does not use Clinical Partners patient data. The provider-level estimand is the probability of reliable improvement among people who finished a course of treatment.

England count check: `{metadata['england_reliable_improvement']:,} / {metadata['england_finished_course_treatment']:,} = {100 * metadata['england_reliable_improvement_rate']:.1f}%`.

Complete provider count pairs used: **{metadata['provider_rows_complete']}**. Provider rows with suppressed or missing count pairs excluded: **{metadata['suppressed_or_missing_provider_rows_excluded']}**.

## Model

For provider j:

`y_j ~ Binomial(n_j, theta_j)`

`theta_j ~ Beta(alpha, beta)`

with `alpha = m * kappa`, `beta = (1-m) * kappa`. The hyperparameters are estimated jointly from all provider count pairs on a numerical posterior grid. This is a Beta-Binomial hierarchical Bayesian model: providers with small denominators receive more partial pooling toward the provider population distribution, while providers with large denominators are driven more strongly by their own data.

Primary-prior posterior provider-population mean `m`: **{100 * hyper['m_mean']:.2f}%** (95% credible interval {100 * hyper['m_q025']:.2f}% to {100 * hyper['m_q975']:.2f}%). Posterior concentration `kappa`: **{hyper['kappa_mean']:.1f}** (95% credible interval {hyper['kappa_q025']:.1f} to {hyper['kappa_q975']:.1f}).

## What partial pooling changes

Median absolute provider shrinkage: **{provider_summary['abs_shrinkage_percentage_points'].median():.2f} percentage points**. The 90th percentile is **{provider_summary['abs_shrinkage_percentage_points'].quantile(0.90):.2f} percentage points**.

Small-denominator examples:

{smallest[['provider_code','finished_course_treatment','raw_rate','posterior_mean','posterior_q025','posterior_q975']].to_markdown(index=False)}

Large-denominator examples:

{largest[['provider_code','finished_course_treatment','raw_rate','posterior_mean','posterior_q025','posterior_q975']].to_markdown(index=False)}

## Prior sensitivity

Maximum absolute provider posterior-mean change under the broader prior: **{sensitivity['absolute_change_percentage_points'].max():.3f} percentage points**. Median change: **{sensitivity['absolute_change_percentage_points'].median():.3f} percentage points**.

## Interpretation limits

This is a service-level demonstration of the partial-pooling logic requested in the Clinical Partners job description. It is not a Clinical Partners model and it is not a provider quality ranking. The NHS aggregate data do not provide patient-level case mix, treatment assignment, clinician hierarchy, repeated item-level outcome measures, or enough information for causal attribution. A production Clinical Partners version would add patient-level longitudinal outcomes, service and clinician random effects, baseline severity and other case-mix covariates, missing-data modelling, and clinically reviewed endpoints.
"""
    (outdir / "V05_BAYESIAN_PARTIAL_POOLING_REPORT.md").write_text(report)


def main(path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flex(path)
    providers, metadata = extract_provider_counts(df)

    primary_hyper, primary = fit_one_analysis(
        providers, PRIMARY_PRIOR, metadata["england_reliable_improvement_rate"]
    )
    broad_hyper, broad = fit_one_analysis(
        providers, BROAD_PRIOR, metadata["england_reliable_improvement_rate"]
    )
    sensitivity = prior_sensitivity(primary, broad)

    primary.to_csv(outdir / "v05_provider_partial_pooling.csv", index=False)
    sensitivity.to_csv(outdir / "v05_prior_sensitivity.csv", index=False)
    payload = {
        "data": metadata,
        "primary_hyperposterior": primary_hyper,
        "broad_hyperposterior": broad_hyper,
        "median_abs_shrinkage_percentage_points": float(primary["abs_shrinkage_percentage_points"].median()),
        "p90_abs_shrinkage_percentage_points": float(primary["abs_shrinkage_percentage_points"].quantile(0.90)),
        "max_prior_sensitivity_percentage_points": float(sensitivity["absolute_change_percentage_points"].max()),
        "median_prior_sensitivity_percentage_points": float(sensitivity["absolute_change_percentage_points"].median()),
    }
    (outdir / "v05_bayesian_partial_pooling_summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    write_report(outdir, metadata, primary_hyper, primary, sensitivity)

    print("V05_BAYESIAN_PARTIAL_POOLING:", json.dumps(payload))
    print("V05_SMALLEST_DENOMINATORS:\n", primary.nsmallest(8, "finished_course_treatment").to_string(index=False))
    print("V05_LARGEST_SHRINKAGE:\n", primary.nlargest(8, "abs_shrinkage_percentage_points").to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

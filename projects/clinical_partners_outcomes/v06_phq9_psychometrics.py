from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, logsumexp
from scipy.stats import chi2, multivariate_normal, norm


ITEMS = [f"DPQ{i:03d}" for i in range(10, 100, 10)]
RACE_LABELS = {
    1: "Mexican American",
    2: "Other Hispanic",
    3: "Non-Hispanic White",
    4: "Non-Hispanic Black",
    6: "Non-Hispanic Asian",
    7: "Other or multiracial",
}
XPORT_NEAR_ZERO_TOL = 1e-12


def normalize_xport_numeric(series: pd.Series) -> pd.Series:
    """Normalize the near-zero representation produced for SAS XPORT numeric zero.

    In CDC NHANES DPQ_L, pandas can decode SAS numeric zero as the tiny positive
    value 5.397605346934028e-79. The published CDC item frequencies confirm that
    these values are the response code 0 ("Not at all"). Values whose magnitude
    is below a conservative tolerance are therefore restored to exact zero before
    validating the PHQ-9 0-3 response codes.
    """

    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    return numeric.mask(numeric.notna() & (numeric.abs() < XPORT_NEAR_ZERO_TOL), 0.0)


def softplus(x: np.ndarray | float) -> np.ndarray:
    return np.logaddexp(0.0, x)


def inv_softplus(y: np.ndarray | float) -> np.ndarray:
    y = np.maximum(np.asarray(y, dtype=float), 1e-6)
    return np.log(np.expm1(y))


def bh_fdr(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    q_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(n, dtype=float)
    q[order] = np.minimum(q_sorted, 1.0)
    return q


def weighted_cronbach_alpha(x: np.ndarray, weights: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()
    mean = (x * weights[:, None]).sum(axis=0)
    centred = x - mean
    cov = (centred * weights[:, None]).T @ centred
    k = x.shape[1]
    total_var = np.ones(k) @ cov @ np.ones(k)
    if total_var <= 0:
        return float("nan")
    return float(k / (k - 1) * (1 - np.trace(cov) / total_var))


def _weighted_thresholds(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    counts = np.array([weights[x == c].sum() for c in range(4)], dtype=float)
    probs = counts / counts.sum()
    cumulative = np.clip(np.cumsum(probs)[:3], 1e-5, 1 - 1e-5)
    return norm.ppf(cumulative)


def _bvncdf(x: float, y: float, rho: float) -> float:
    if np.isneginf(x) or np.isneginf(y):
        return 0.0
    if np.isposinf(x) and np.isposinf(y):
        return 1.0
    if np.isposinf(x):
        return float(norm.cdf(y))
    if np.isposinf(y):
        return float(norm.cdf(x))
    return float(
        multivariate_normal.cdf(
            [x, y],
            mean=[0.0, 0.0],
            cov=[[1.0, rho], [rho, 1.0]],
        )
    )


def polychoric_pair(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    x = np.asarray(x, dtype=int)
    y = np.asarray(y, dtype=int)
    weights = np.asarray(weights, dtype=float)
    tx = np.r_[-np.inf, _weighted_thresholds(x, weights), np.inf]
    ty = np.r_[-np.inf, _weighted_thresholds(y, weights), np.inf]
    cells = np.zeros((4, 4), dtype=float)
    for i in range(4):
        for j in range(4):
            cells[i, j] = weights[(x == i) & (y == j)].sum()

    def objective(rho: float) -> float:
        log_likelihood = 0.0
        for i in range(4):
            for j in range(4):
                if cells[i, j] == 0:
                    continue
                prob = (
                    _bvncdf(tx[i + 1], ty[j + 1], rho)
                    - _bvncdf(tx[i], ty[j + 1], rho)
                    - _bvncdf(tx[i + 1], ty[j], rho)
                    + _bvncdf(tx[i], ty[j], rho)
                )
                log_likelihood += cells[i, j] * math.log(max(prob, 1e-12))
        return -log_likelihood

    result = minimize_scalar(
        objective,
        bounds=(-0.95, 0.95),
        method="bounded",
        options={"xatol": 1e-4},
    )
    return float(result.x)


def polychoric_matrix(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=int)
    k = x.shape[1]
    corr = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            rho = polychoric_pair(x[:, i], x[:, j], weights)
            corr[i, j] = corr[j, i] = rho

    # Pairwise estimation can leave a very small non-PSD numerical component.
    values, vectors = np.linalg.eigh(corr)
    values = np.clip(values, 1e-6, None)
    corr_psd = (vectors * values) @ vectors.T
    scale = np.sqrt(np.diag(corr_psd))
    corr_psd = corr_psd / np.outer(scale, scale)
    np.fill_diagonal(corr_psd, 1.0)
    return corr_psd


def one_factor_audit(corr: np.ndarray) -> dict:
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    first_vector = eigenvectors[:, order[0]]
    loadings = first_vector * np.sqrt(eigenvalues[0])
    if loadings.sum() < 0:
        loadings = -loadings
    predicted = np.outer(loadings, loadings)
    off_diagonal = ~np.eye(len(loadings), dtype=bool)
    residual_rms = float(
        np.sqrt(np.mean((corr[off_diagonal] - predicted[off_diagonal]) ** 2))
    )
    return {
        "eigenvalues": eigenvalues.tolist(),
        "first_to_second_eigenvalue_ratio": float(
            eigenvalues[0] / max(eigenvalues[1], 1e-8)
        ),
        "first_eigenvalue_variance_fraction": float(
            eigenvalues[0] / eigenvalues.sum()
        ),
        "one_factor_loadings": loadings.tolist(),
        "offdiag_residual_rms": residual_rms,
    }


def unpack_item_block(
    raw: np.ndarray,
    n_items: int = 9,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw, dtype=float).reshape(n_items, 4)
    discrimination = np.exp(np.clip(raw[:, 0], -2.5, 2.5))
    b1 = raw[:, 1]
    b2 = b1 + softplus(raw[:, 2])
    b3 = b2 + softplus(raw[:, 3])
    thresholds = np.c_[b1, b2, b3]
    return discrimination, thresholds


def pack_initial_from_data(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=int)
    raw = np.zeros((x.shape[1], 4), dtype=float)
    for item in range(x.shape[1]):
        counts = np.array(
            [weights[x[:, item] == c].sum() for c in range(4)],
            dtype=float,
        )
        probs = counts / counts.sum()
        p_ge = np.clip(
            [1 - probs[0], 1 - probs[:2].sum(), probs[3]],
            1e-4,
            1 - 1e-4,
        )
        thresholds = -np.log(np.asarray(p_ge) / (1 - np.asarray(p_ge)))
        thresholds = np.maximum.accumulate(thresholds + np.arange(3) * 1e-4)
        raw[item, 0] = 0.0
        raw[item, 1] = thresholds[0]
        raw[item, 2] = inv_softplus(max(thresholds[1] - thresholds[0], 0.1))
        raw[item, 3] = inv_softplus(max(thresholds[2] - thresholds[1], 0.1))
    return raw.ravel()


def category_probabilities(
    discrimination: float,
    thresholds: np.ndarray,
    theta: np.ndarray,
) -> np.ndarray:
    theta = np.asarray(theta, dtype=float)
    survival = expit(discrimination * (theta[:, None] - thresholds[None, :]))
    probs = np.empty((len(theta), 4), dtype=float)
    probs[:, 0] = 1 - survival[:, 0]
    probs[:, 1] = survival[:, 0] - survival[:, 1]
    probs[:, 2] = survival[:, 1] - survival[:, 2]
    probs[:, 3] = survival[:, 2]
    return np.clip(probs, 1e-12, 1.0)


def aggregate_patterns(
    x: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.int8)
    weights = np.asarray(weights, dtype=float)
    frame = pd.DataFrame(x)
    frame["_weight"] = weights
    grouped = (
        frame.groupby(
            list(range(x.shape[1])),
            sort=False,
            observed=True,
        )["_weight"]
        .sum()
        .reset_index()
    )
    return (
        grouped.iloc[:, : x.shape[1]].to_numpy(dtype=np.int8),
        grouped["_weight"].to_numpy(dtype=float),
    )


def gh_quadrature(n: int = 15) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = np.polynomial.hermite.hermgauss(n)
    return np.sqrt(2.0) * nodes, weights / np.sqrt(np.pi)


def pattern_log_likelihood(
    item_raw: np.ndarray,
    patterns: np.ndarray,
    pattern_weights: np.ndarray,
    theta: np.ndarray,
    quadrature_weights: np.ndarray,
    replacement: tuple[int, np.ndarray] | None = None,
) -> float:
    discrimination, thresholds = unpack_item_block(
        item_raw,
        patterns.shape[1],
    )
    if replacement is not None:
        item_index, replacement_raw = replacement
        replacement_a, replacement_b = unpack_item_block(
            np.asarray(replacement_raw),
            1,
        )
        discrimination[item_index] = replacement_a[0]
        thresholds[item_index] = replacement_b[0]

    conditional = np.zeros((len(theta), patterns.shape[0]), dtype=float)
    for item in range(patterns.shape[1]):
        probs = category_probabilities(
            discrimination[item],
            thresholds[item],
            theta,
        )
        conditional += np.log(probs)[:, patterns[:, item]]
    marginal = logsumexp(
        conditional + np.log(quadrature_weights)[:, None],
        axis=0,
    )
    return float(np.dot(pattern_weights, marginal))


def fit_pooled_grm(
    x: np.ndarray,
    weights: np.ndarray,
    maxiter: int = 180,
) -> dict:
    patterns, pattern_weights = aggregate_patterns(x, weights)
    theta, quadrature_weights = gh_quadrature()
    initial = pack_initial_from_data(x, weights)

    def objective(raw: np.ndarray) -> float:
        return -pattern_log_likelihood(
            raw,
            patterns,
            pattern_weights,
            theta,
            quadrature_weights,
        )

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        options={"maxiter": maxiter, "ftol": 1e-8, "maxls": 30},
    )
    discrimination, thresholds = unpack_item_block(result.x, x.shape[1])
    return {
        "success": bool(result.success),
        "message": str(result.message),
        "loglik": float(-result.fun),
        "raw": result.x,
        "a": discrimination,
        "b": thresholds,
        "n_patterns": int(len(patterns)),
        "iterations": int(result.nit),
    }


def fit_multigroup_invariance(
    x: np.ndarray,
    weights: np.ndarray,
    group: np.ndarray,
    pooled_raw: np.ndarray,
    free_item: int | None = None,
    maxiter: int = 120,
    initial_latent_mean: float = 0.0,
    initial_latent_sd: float = 1.0,
) -> dict:
    group = np.asarray(group, dtype=int)
    theta_reference, quadrature_weights = gh_quadrature()
    grouped_patterns = {}
    for group_value in (0, 1):
        mask = group == group_value
        grouped_patterns[group_value] = aggregate_patterns(
            x[mask],
            weights[mask],
        )

    initial = np.r_[
        pooled_raw,
        initial_latent_mean,
        np.log(max(initial_latent_sd, 1e-6)),
    ]
    if free_item is not None:
        initial = np.r_[
            initial,
            pooled_raw.reshape(x.shape[1], 4)[free_item],
        ]

    n_item_parameters = x.shape[1] * 4

    def objective(parameters: np.ndarray) -> float:
        item_raw = parameters[:n_item_parameters]
        comparison_mean = parameters[n_item_parameters]
        comparison_sd = float(
            np.exp(
                np.clip(
                    parameters[n_item_parameters + 1],
                    -1.5,
                    1.5,
                )
            )
        )
        total_log_likelihood = 0.0
        for group_value in (0, 1):
            patterns, pattern_weights = grouped_patterns[group_value]
            theta = (
                theta_reference
                if group_value == 0
                else comparison_mean + comparison_sd * theta_reference
            )
            replacement = None
            if free_item is not None and group_value == 1:
                replacement = (free_item, parameters[-4:])
            total_log_likelihood += pattern_log_likelihood(
                item_raw,
                patterns,
                pattern_weights,
                theta,
                quadrature_weights,
                replacement=replacement,
            )
        return -total_log_likelihood

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        options={"maxiter": maxiter, "ftol": 1e-8, "maxls": 30},
    )
    return {
        "success": bool(result.success),
        "message": str(result.message),
        "loglik": float(-result.fun),
        "raw": result.x,
        "comparison_latent_mean": float(result.x[n_item_parameters]),
        "comparison_latent_sd": float(
            np.exp(
                np.clip(
                    result.x[n_item_parameters + 1],
                    -1.5,
                    1.5,
                )
            )
        ),
        "iterations": int(result.nit),
    }


def item_information(
    discrimination: np.ndarray,
    thresholds: np.ndarray,
    theta_grid: np.ndarray,
) -> np.ndarray:
    theta_grid = np.asarray(theta_grid, dtype=float)
    information = np.zeros(
        (len(theta_grid), len(discrimination)),
        dtype=float,
    )
    for item in range(len(discrimination)):
        survival = expit(
            discrimination[item]
            * (theta_grid[:, None] - thresholds[item][None, :])
        )
        derivative_survival = (
            discrimination[item] * survival * (1 - survival)
        )
        probs = np.empty((len(theta_grid), 4), dtype=float)
        derivatives = np.empty((len(theta_grid), 4), dtype=float)
        probs[:, 0] = 1 - survival[:, 0]
        derivatives[:, 0] = -derivative_survival[:, 0]
        probs[:, 1] = survival[:, 0] - survival[:, 1]
        derivatives[:, 1] = (
            derivative_survival[:, 0] - derivative_survival[:, 1]
        )
        probs[:, 2] = survival[:, 1] - survival[:, 2]
        derivatives[:, 2] = (
            derivative_survival[:, 1] - derivative_survival[:, 2]
        )
        probs[:, 3] = survival[:, 2]
        derivatives[:, 3] = derivative_survival[:, 2]
        probs = np.clip(probs, 1e-12, 1.0)
        information[:, item] = (
            derivatives * derivatives / probs
        ).sum(axis=1)
    return information


def prepare_nhanes(
    dpq_path: str | Path,
    demo_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dpq = pd.read_sas(dpq_path, format="xport")
    demo = pd.read_sas(demo_path, format="xport")
    demographic_columns = [
        "SEQN",
        "RIAGENDR",
        "RIDAGEYR",
        "RIDRETH3",
        "WTMEC2YR",
    ]
    if "INDFMPIR" in demo.columns:
        demographic_columns.append("INDFMPIR")
    merged = dpq[["SEQN"] + ITEMS].merge(
        demo[demographic_columns],
        on="SEQN",
        how="inner",
        validate="one_to_one",
    )

    for item in ITEMS:
        numeric = normalize_xport_numeric(merged[item])
        merged[item] = numeric.where(numeric.isin([0, 1, 2, 3]))

    complete = merged.dropna(
        subset=ITEMS + ["RIAGENDR", "RIDAGEYR", "WTMEC2YR"]
    ).copy()
    for item in ITEMS:
        complete[item] = complete[item].astype(int)
    complete["sex"] = complete["RIAGENDR"].map(
        {1: "Male", 2: "Female"}
    )
    complete["sex_binary"] = complete["RIAGENDR"].map(
        {1: 0, 2: 1}
    ).astype(int)
    complete["age_group"] = pd.cut(
        complete["RIDAGEYR"],
        bins=[17, 39, 59, np.inf],
        labels=["18-39", "40-59", "60+"],
    )
    complete["race_ethnicity"] = complete["RIDRETH3"].map(
        RACE_LABELS
    )
    complete["analysis_weight"] = (
        complete["WTMEC2YR"] / complete["WTMEC2YR"].mean()
    )
    return merged, complete


def run_analysis(
    dpq_path: str | Path,
    demo_path: str | Path,
    outdir: str | Path,
    dif_maxiter: int = 120,
) -> dict:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    merged, cohort = prepare_nhanes(dpq_path, demo_path)
    x = cohort[ITEMS].to_numpy(dtype=int)
    weights = cohort["analysis_weight"].to_numpy(dtype=float)

    item_counts = {}
    for item in ITEMS:
        item_counts[item] = {
            "zero": int((merged[item] == 0).sum()),
            "valid_0_to_3": int(merged[item].notna().sum()),
        }

    alpha = weighted_cronbach_alpha(x, weights)
    polychoric = polychoric_matrix(x, weights)
    factor = one_factor_audit(polychoric)
    pd.DataFrame(
        polychoric,
        index=ITEMS,
        columns=ITEMS,
    ).to_csv(outdir / "v06_phq9_polychoric.csv")
    pd.DataFrame(
        {
            "item": ITEMS,
            "loading": factor["one_factor_loadings"],
        }
    ).to_csv(outdir / "v06_one_factor_loadings.csv", index=False)

    grm = fit_pooled_grm(x, weights)
    item_parameters = pd.DataFrame(
        {
            "item": ITEMS,
            "discrimination_a": grm["a"],
            "threshold_b1": grm["b"][:, 0],
            "threshold_b2": grm["b"][:, 1],
            "threshold_b3": grm["b"][:, 2],
        }
    )
    item_parameters.to_csv(
        outdir / "v06_grm_item_parameters.csv",
        index=False,
    )

    theta_grid = np.array([-2, -1, 0, 1, 2], dtype=float)
    information = item_information(grm["a"], grm["b"], theta_grid)
    information_table = pd.DataFrame(information, columns=ITEMS)
    information_table.insert(0, "theta", theta_grid)
    information_table["test_information"] = information.sum(axis=1)
    information_table["conditional_sem"] = 1 / np.sqrt(
        information_table["test_information"]
    )
    information_table["two_measurement_95pct_change_threshold"] = (
        1.96 * np.sqrt(2) * information_table["conditional_sem"]
    )
    information_table.to_csv(
        outdir / "v06_test_information_reliable_change_readiness.csv",
        index=False,
    )

    sex_group = cohort["sex_binary"].to_numpy(dtype=int)
    invariant = fit_multigroup_invariance(
        x,
        weights,
        sex_group,
        grm["raw"],
        free_item=None,
        maxiter=dif_maxiter,
    )
    dif_rows = []
    shared_item_raw = invariant["raw"][: len(ITEMS) * 4]
    for item_index, item_name in enumerate(ITEMS):
        alternative = fit_multigroup_invariance(
            x,
            weights,
            sex_group,
            shared_item_raw,
            free_item=item_index,
            maxiter=dif_maxiter,
            initial_latent_mean=invariant["comparison_latent_mean"],
            initial_latent_sd=invariant["comparison_latent_sd"],
        )
        statistic = max(
            0.0,
            2 * (alternative["loglik"] - invariant["loglik"]),
        )
        p_value = float(chi2.sf(statistic, 4))
        dif_rows.append(
            {
                "item": item_name,
                "lrt_chi2_df4": statistic,
                "p_value": p_value,
                "alternative_loglik": alternative["loglik"],
                "fit_success": alternative["success"],
            }
        )
    dif = pd.DataFrame(dif_rows)
    dif["q_value_bh"] = bh_fdr(dif["p_value"].to_numpy())
    dif["dif_flag_fdr_0_05"] = dif["q_value_bh"] < 0.05
    dif.to_csv(outdir / "v06_sex_dif_anchor_lrt.csv", index=False)
    flagged_items = dif.loc[
        dif["dif_flag_fdr_0_05"],
        "item",
    ].tolist()

    summary = {
        "version": "0.6",
        "dataset": (
            "NHANES August 2021-August 2023 public DPQ_L + DEMO_L"
        ),
        "items": ITEMS,
        "source_item_counts_after_xport_normalization": item_counts,
        "cohort": {
            "merged_rows": int(len(merged)),
            "complete_nine_item_rows": int(len(cohort)),
            "female_rows": int((cohort["sex_binary"] == 1).sum()),
            "male_rows": int((cohort["sex_binary"] == 0).sum()),
            "age_min": float(cohort["RIDAGEYR"].min()),
            "age_max": float(cohort["RIDAGEYR"].max()),
            "weight": (
                "WTMEC2YR normalized to mean 1 for pseudo-likelihood "
                "estimation"
            ),
        },
        "classical_reliability": {
            "weighted_cronbach_alpha": alpha,
        },
        "ordinal_factor_structure": factor,
        "graded_response_model": {
            "fit_success": grm["success"],
            "message": grm["message"],
            "loglik": grm["loglik"],
            "unique_response_patterns": grm["n_patterns"],
            "iterations": grm["iterations"],
        },
        "sex_measurement_invariance_screen": {
            "reference_group": "Male",
            "comparison_group": "Female",
            "shared_item_fit_success": invariant["success"],
            "shared_item_loglik": invariant["loglik"],
            "comparison_latent_mean": invariant[
                "comparison_latent_mean"
            ],
            "comparison_latent_sd": invariant["comparison_latent_sd"],
            "n_items_flagged_fdr_0_05": int(
                dif["dif_flag_fdr_0_05"].sum()
            ),
            "flagged_items_fdr_0_05": flagged_items,
            "minimum_q_value": float(dif["q_value_bh"].min()),
            "method": (
                "One-item-at-a-time anchored multi-group GRM likelihood-"
                "ratio screen; the eight remaining PHQ-9 symptom items "
                "serve as anchors."
            ),
        },
        "reliable_change_boundary": {
            "status": "readiness_only",
            "reason": (
                "NHANES DPQ_L is cross-sectional. Conditional test "
                "information and measurement-error thresholds are "
                "estimated, but observed within-person reliable change "
                "is not estimable without repeated item-level "
                "administrations."
            ),
        },
        "interpretation_boundary": (
            "This is a public-population psychometric audit, not a "
            "Clinical Partners instrument validation. Survey-weighted "
            "pseudo-likelihood is used for item-parameter estimation; "
            "the workflow does not claim full design-based standard errors."
        ),
    }
    (outdir / "v06_psychometrics_summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    report = f"""# v0.6 NHANES PHQ-9 item-level psychometrics

## Data

- Public NHANES August 2021-August 2023 `DPQ_L` and `DEMO_L`.
- Complete nine-item PHQ-9 cohort: **{len(cohort):,}** adults.
- The analysis uses `DPQ010`-`DPQ090`; `DPQ100` functional impairment is not treated as a tenth PHQ-9 symptom item.
- MEC examination weight `WTMEC2YR` is normalized to mean one for weighted pseudo-likelihood estimation.
- The workflow explicitly normalizes the SAS XPORT near-zero representation back to response code 0 and checks the resulting item frequencies against the public CDC codebook.

## Ordinal factor structure

- Weighted Cronbach alpha: **{alpha:.3f}**
- First/second polychoric eigenvalue ratio: **{factor['first_to_second_eigenvalue_ratio']:.2f}**
- First eigenvalue variance fraction: **{factor['first_eigenvalue_variance_fraction']:.3f}**
- One-factor off-diagonal residual RMS: **{factor['offdiag_residual_rms']:.3f}**

These values are an ordinal factor-structure audit, not a claim that a one-factor model is clinically sufficient.

## Graded-response IRT

A four-category graded-response model is fitted by marginal maximum likelihood with Gaussian quadrature. Each item has one discrimination parameter and three ordered thresholds. The ordinal 0-3 response scale is retained rather than treated as continuous.

Fit success: **{grm['success']}**. Unique observed response patterns: **{grm['n_patterns']}**.

## DIF and measurement invariance

Sex-related item invariance is screened with anchored multi-group GRM likelihood-ratio tests. The baseline model shares all item parameters across male and female groups while allowing the female latent mean and scale to differ. Each alternative frees one item's discrimination and thresholds in the female group while the other eight items remain anchors.

Items flagged after Benjamini-Hochberg FDR 0.05: **{int(dif['dif_flag_fdr_0_05'].sum())}/9**. Flagged items: **{', '.join(flagged_items) if flagged_items else 'none'}**.

A flagged item is evidence of possible DIF under this model, not evidence of bias by itself. Clinical interpretation requires item-content review and sensitivity analysis.

## Reliable-change boundary

NHANES provides one public PHQ-9 administration per participant in this cycle. v0.6 therefore does **not** estimate observed within-person reliable change. It reports conditional test information, conditional SEM, and the latent-score difference that would exceed two independent measurement errors at the 95% level. A genuine reliable-change analysis needs repeated item-level administrations.

## Clinical Partners boundary

This analysis demonstrates item-level psychometric modelling on real public mental-health data. It is not a validation of Clinical Partners questionnaires, patient pathways, or clinicians. A production study would repeat the measurement model in the target population and test invariance across clinically relevant groups, services, assessment modes, and time.
"""
    (outdir / "V06_PSYCHOMETRICS_REPORT.md").write_text(report)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpq", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dif-maxiter", type=int, default=120)
    args = parser.parse_args()
    summary = run_analysis(
        args.dpq,
        args.demo,
        args.out,
        dif_maxiter=args.dif_maxiter,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

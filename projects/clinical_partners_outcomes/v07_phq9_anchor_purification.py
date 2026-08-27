from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import chi2

from v06_phq9_psychometrics import (
    ITEMS,
    aggregate_patterns,
    bh_fdr,
    category_probabilities,
    fit_pooled_grm,
    gh_quadrature,
    prepare_nhanes,
    unpack_item_block,
)


def pattern_log_likelihood_multi(
    item_raw: np.ndarray,
    patterns: np.ndarray,
    pattern_weights: np.ndarray,
    theta: np.ndarray,
    quadrature_weights: np.ndarray,
    replacements: dict[int, np.ndarray] | None = None,
) -> float:
    """Marginal GRM log likelihood with zero or more group-specific item blocks."""

    discrimination, thresholds = unpack_item_block(
        np.asarray(item_raw, dtype=float), patterns.shape[1]
    )
    if replacements:
        for item_index, replacement_raw in replacements.items():
            replacement_a, replacement_b = unpack_item_block(
                np.asarray(replacement_raw, dtype=float), 1
            )
            discrimination[item_index] = replacement_a[0]
            thresholds[item_index] = replacement_b[0]

    conditional = np.zeros((len(theta), patterns.shape[0]), dtype=float)
    for item in range(patterns.shape[1]):
        probs = category_probabilities(
            discrimination[item], thresholds[item], theta
        )
        conditional += np.log(probs)[:, patterns[:, item]]

    marginal = logsumexp(
        conditional + np.log(quadrature_weights)[:, None], axis=0
    )
    return float(np.dot(pattern_weights, marginal))


def fit_multigroup_free_items(
    x: np.ndarray,
    weights: np.ndarray,
    group: np.ndarray,
    pooled_raw: np.ndarray,
    free_items: Iterable[int] = (),
    maxiter: int = 140,
    initial_latent_mean: float = 0.0,
    initial_latent_sd: float = 1.0,
) -> dict:
    """Fit a two-group GRM with an arbitrary set of items free in group 1.

    Group 0 fixes the latent mean/SD to 0/1. Group 1 has an estimated latent
    mean and SD. Items in ``free_items`` receive a separate discrimination and
    three separate thresholds in group 1; all remaining items are anchors.
    """

    x = np.asarray(x, dtype=int)
    weights = np.asarray(weights, dtype=float)
    group = np.asarray(group, dtype=int)
    free_items = tuple(sorted(set(int(i) for i in free_items)))
    if not set(np.unique(group)).issubset({0, 1}) or len(np.unique(group)) != 2:
        raise ValueError("group must contain both binary values 0 and 1")

    theta_reference, quadrature_weights = gh_quadrature()
    grouped_patterns: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for group_value in (0, 1):
        mask = group == group_value
        grouped_patterns[group_value] = aggregate_patterns(
            x[mask], weights[mask]
        )

    pooled_raw = np.asarray(pooled_raw, dtype=float)
    n_item_parameters = x.shape[1] * 4
    shared_initial = pooled_raw[:n_item_parameters]
    initial = np.r_[
        shared_initial,
        initial_latent_mean,
        np.log(max(initial_latent_sd, 1e-6)),
    ]
    pooled_blocks = shared_initial.reshape(x.shape[1], 4)
    if free_items:
        initial = np.r_[initial, *[pooled_blocks[i] for i in free_items]]

    free_offsets = {
        item_index: n_item_parameters + 2 + block_index * 4
        for block_index, item_index in enumerate(free_items)
    }

    def objective(parameters: np.ndarray) -> float:
        item_raw = parameters[:n_item_parameters]
        comparison_mean = float(parameters[n_item_parameters])
        comparison_sd = float(
            np.exp(np.clip(parameters[n_item_parameters + 1], -1.5, 1.5))
        )
        total_log_likelihood = 0.0
        for group_value in (0, 1):
            patterns, pattern_weights = grouped_patterns[group_value]
            theta = (
                theta_reference
                if group_value == 0
                else comparison_mean + comparison_sd * theta_reference
            )
            replacements = None
            if group_value == 1 and free_items:
                replacements = {
                    item_index: parameters[offset : offset + 4]
                    for item_index, offset in free_offsets.items()
                }
            total_log_likelihood += pattern_log_likelihood_multi(
                item_raw,
                patterns,
                pattern_weights,
                theta,
                quadrature_weights,
                replacements=replacements,
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
        "shared_raw": result.x[:n_item_parameters],
        "comparison_latent_mean": float(result.x[n_item_parameters]),
        "comparison_latent_sd": float(
            np.exp(np.clip(result.x[n_item_parameters + 1], -1.5, 1.5))
        ),
        "free_items": list(free_items),
        "iterations": int(result.nit),
    }


def dif_screen(
    x: np.ndarray,
    weights: np.ndarray,
    group: np.ndarray,
    pooled_raw: np.ndarray,
    background_free_items: Iterable[int] = (),
    maxiter: int = 140,
) -> pd.DataFrame:
    """Test all items while allowing known/suspected DIF items to remain free.

    For target item j, the null model frees the background DIF items except j;
    the alternative additionally frees j. The 4-df LRT therefore tests that
    item's discrimination plus three thresholds conditional on the current
    anchor specification.
    """

    background = set(int(i) for i in background_free_items)
    rows: list[dict] = []
    for item_index, item_name in enumerate(ITEMS):
        null_free = background - {item_index}
        alternative_free = null_free | {item_index}
        null_model = fit_multigroup_free_items(
            x,
            weights,
            group,
            pooled_raw,
            free_items=null_free,
            maxiter=maxiter,
        )
        alternative = fit_multigroup_free_items(
            x,
            weights,
            group,
            null_model["shared_raw"],
            free_items=alternative_free,
            maxiter=maxiter,
            initial_latent_mean=null_model["comparison_latent_mean"],
            initial_latent_sd=null_model["comparison_latent_sd"],
        )
        statistic = max(
            0.0, 2.0 * (alternative["loglik"] - null_model["loglik"])
        )
        rows.append(
            {
                "item": item_name,
                "item_index": item_index,
                "background_free_items": ",".join(
                    ITEMS[i] for i in sorted(null_free)
                ),
                "n_anchor_items_in_null": len(ITEMS) - len(null_free),
                "null_loglik": null_model["loglik"],
                "alternative_loglik": alternative["loglik"],
                "lrt_chi2_df4": statistic,
                "p_value": float(chi2.sf(statistic, 4)),
                "null_fit_success": null_model["success"],
                "alternative_fit_success": alternative["success"],
            }
        )
    result = pd.DataFrame(rows)
    result["q_value_bh"] = bh_fdr(result["p_value"].to_numpy())
    result["dif_flag_fdr_0_05"] = result["q_value_bh"] < 0.05
    return result


def iterative_anchor_purification(
    x: np.ndarray,
    weights: np.ndarray,
    group: np.ndarray,
    pooled_raw: np.ndarray,
    maxiter: int = 140,
    max_rounds: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, set[int], bool]:
    """Iterate DIF detection until the FDR flag set stabilises."""

    flagged: set[int] = set()
    history: list[pd.DataFrame] = []
    converged = False
    for round_number in range(1, max_rounds + 1):
        screen = dif_screen(
            x,
            weights,
            group,
            pooled_raw,
            background_free_items=flagged,
            maxiter=maxiter,
        )
        screen.insert(0, "purification_round", round_number)
        screen["background_flagged_at_round_start"] = ",".join(
            ITEMS[i] for i in sorted(flagged)
        )
        history.append(screen)
        new_flagged = set(
            screen.loc[screen["dif_flag_fdr_0_05"], "item_index"].astype(int)
        )
        if new_flagged == flagged:
            converged = True
            flagged = new_flagged
            break
        flagged = new_flagged

    full_history = pd.concat(history, ignore_index=True)
    final_screen = history[-1].copy()
    return full_history, final_screen, flagged, converged


def leave_one_anchor_out_sensitivity(
    x: np.ndarray,
    weights: np.ndarray,
    group: np.ndarray,
    pooled_raw: np.ndarray,
    final_flagged: set[int],
    maxiter: int = 140,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Re-run the final screen after freeing each purified anchor in turn."""

    final_anchors = [i for i in range(len(ITEMS)) if i not in final_flagged]
    runs: list[pd.DataFrame] = []
    for omitted_anchor in final_anchors:
        background = set(final_flagged) | {omitted_anchor}
        screen = dif_screen(
            x,
            weights,
            group,
            pooled_raw,
            background_free_items=background,
            maxiter=maxiter,
        )
        screen.insert(0, "omitted_anchor", ITEMS[omitted_anchor])
        runs.append(screen)

    if not runs:
        empty = pd.DataFrame()
        return empty, empty

    all_runs = pd.concat(runs, ignore_index=True)
    summary = (
        all_runs.groupby("item", as_index=False)
        .agg(
            n_leave_one_anchor_out_runs=("omitted_anchor", "nunique"),
            n_flagged_fdr_0_05=("dif_flag_fdr_0_05", "sum"),
            min_q_value=("q_value_bh", "min"),
            max_q_value=("q_value_bh", "max"),
        )
    )
    summary["flag_fraction"] = (
        summary["n_flagged_fdr_0_05"]
        / summary["n_leave_one_anchor_out_runs"]
    )
    return all_runs, summary


def binary_group_screen(
    cohort: pd.DataFrame,
    x_columns: list[str],
    group_mask_reference: pd.Series,
    group_mask_comparison: pd.Series,
    pooled_raw: np.ndarray,
    background_free: set[int],
    maxiter: int,
    comparison_name: str,
) -> tuple[pd.DataFrame, dict]:
    mask = group_mask_reference | group_mask_comparison
    subset = cohort.loc[mask].copy()
    group = np.where(group_mask_comparison.loc[subset.index], 1, 0)
    weights = subset["WTMEC2YR"].to_numpy(dtype=float)
    weights = weights / weights.mean()
    x = subset[x_columns].to_numpy(dtype=int)
    screen = dif_screen(
        x,
        weights,
        group,
        pooled_raw,
        background_free_items=background_free,
        maxiter=maxiter,
    )
    screen.insert(0, "comparison", comparison_name)
    metadata = {
        "comparison": comparison_name,
        "reference_n": int((group == 0).sum()),
        "comparison_n": int((group == 1).sum()),
        "flagged_items": screen.loc[
            screen["dif_flag_fdr_0_05"], "item"
        ].tolist(),
        "n_flagged": int(screen["dif_flag_fdr_0_05"].sum()),
    }
    return screen, metadata


def design_structure_audit(cohort: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = {"SDMVSTRA", "SDMVPSU"}
    if not required.issubset(cohort.columns):
        return pd.DataFrame(), {
            "available": False,
            "reason": "SDMVSTRA/SDMVPSU not present in prepared cohort",
        }
    table = (
        cohort.groupby(["SDMVSTRA", "SDMVPSU"], dropna=False)
        .agg(
            complete_case_n=("SEQN", "size"),
            weight_sum=("WTMEC2YR", "sum"),
        )
        .reset_index()
    )
    n_strata = int(table["SDMVSTRA"].nunique())
    n_psu = int(len(table))
    return table, {
        "available": True,
        "n_masked_strata_in_complete_case_domain": n_strata,
        "n_masked_psu_in_complete_case_domain": n_psu,
        "naive_design_df_psu_minus_strata": n_psu - n_strata,
        "inference_boundary": (
            "These fields document the NHANES masked variance structure. "
            "The v0.7 GRM likelihood-ratio p-values are weighted pseudo-"
            "likelihood results and are not labelled as Taylor-linearised "
            "design-based standard errors. Formal NHANES survey inference "
            "should retain the full sample and use domain/subpopulation "
            "analysis with SDMVSTRA, SDMVPSU and WTMEC2YR."
        ),
    }


def run_analysis(
    dpq_path: str | Path,
    demo_path: str | Path,
    outdir: str | Path,
    dif_maxiter: int = 140,
    purification_rounds: int = 5,
) -> dict:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    _, cohort = prepare_nhanes(dpq_path, demo_path)

    x = cohort[ITEMS].to_numpy(dtype=int)
    weights = cohort["analysis_weight"].to_numpy(dtype=float)
    sex_group = cohort["sex_binary"].to_numpy(dtype=int)
    pooled = fit_pooled_grm(x, weights, maxiter=max(dif_maxiter, 180))

    history, final_screen, flagged, purification_converged = (
        iterative_anchor_purification(
            x,
            weights,
            sex_group,
            pooled["raw"],
            maxiter=dif_maxiter,
            max_rounds=purification_rounds,
        )
    )
    final_anchors = [i for i in range(len(ITEMS)) if i not in flagged]
    history.to_csv(outdir / "v07_sex_dif_purification_history.csv", index=False)
    final_screen.to_csv(outdir / "v07_sex_dif_purified_final.csv", index=False)

    loo_runs, loo_summary = leave_one_anchor_out_sensitivity(
        x,
        weights,
        sex_group,
        pooled["raw"],
        final_flagged=flagged,
        maxiter=dif_maxiter,
    )
    if not loo_runs.empty:
        loo_runs.to_csv(
            outdir / "v07_sex_dif_leave_one_anchor_out.csv", index=False
        )
        loo_summary.to_csv(
            outdir / "v07_sex_dif_anchor_sensitivity_summary.csv", index=False
        )

    equal_weights = np.ones(len(cohort), dtype=float)
    equal_weight_screen = dif_screen(
        x,
        equal_weights,
        sex_group,
        pooled["raw"],
        background_free_items=flagged,
        maxiter=dif_maxiter,
    )
    equal_weight_screen.to_csv(
        outdir / "v07_sex_dif_equal_weight_sensitivity.csv", index=False
    )

    age_screen, age_meta = binary_group_screen(
        cohort,
        ITEMS,
        cohort["age_group"].eq("18-39"),
        cohort["age_group"].eq("60+"),
        pooled["raw"],
        background_free=flagged,
        maxiter=dif_maxiter,
        comparison_name="18-39 reference vs 60+ comparison",
    )
    age_screen.to_csv(outdir / "v07_age_dif_exploratory.csv", index=False)

    race_screen, race_meta = binary_group_screen(
        cohort,
        ITEMS,
        cohort["race_ethnicity"].eq("Non-Hispanic White"),
        cohort["race_ethnicity"].eq("Non-Hispanic Black"),
        pooled["raw"],
        background_free=flagged,
        maxiter=dif_maxiter,
        comparison_name=(
            "Non-Hispanic White reference vs Non-Hispanic Black comparison"
        ),
    )
    race_screen.to_csv(outdir / "v07_race_dif_exploratory.csv", index=False)

    design_table, design_meta = design_structure_audit(cohort)
    if not design_table.empty:
        design_table.to_csv(outdir / "v07_design_structure_audit.csv", index=False)

    primary_flagged = [ITEMS[i] for i in sorted(flagged)]
    primary_anchors = [ITEMS[i] for i in final_anchors]
    equal_flagged = equal_weight_screen.loc[
        equal_weight_screen["dif_flag_fdr_0_05"], "item"
    ].tolist()
    stable_loo = []
    if not loo_summary.empty:
        stable_loo = loo_summary.loc[
            loo_summary["flag_fraction"] == 1.0, "item"
        ].tolist()

    summary = {
        "version": "0.7",
        "dataset": "NHANES August 2021-August 2023 public DPQ_L + DEMO_L",
        "cohort_n": int(len(cohort)),
        "primary_question": (
            "Does the v0.6 sex DIF signal survive iterative anchor purification "
            "and reasonable anchor/weighting sensitivity checks?"
        ),
        "sex_anchor_purification": {
            "converged": bool(purification_converged),
            "rounds_run": int(history["purification_round"].max()),
            "final_flagged_items_fdr_0_05": primary_flagged,
            "n_final_flagged": len(primary_flagged),
            "final_anchor_items": primary_anchors,
            "n_final_anchors": len(primary_anchors),
        },
        "anchor_sensitivity": {
            "leave_one_anchor_out_runs": int(len(final_anchors)),
            "items_flagged_in_every_leave_one_anchor_out_run": stable_loo,
            "equal_weight_flagged_items": equal_flagged,
        },
        "exploratory_group_screens": {
            "age": age_meta,
            "race_ethnicity": race_meta,
            "boundary": (
                "Age and race/ethnicity screens transfer the sex-purified "
                "anchor specification and are exploratory. They are not "
                "confirmatory measurement-invariance tests."
            ),
        },
        "nhanes_design_structure": design_meta,
        "interpretation_boundary": (
            "v0.7 improves anchor contamination and sensitivity handling for "
            "weighted GRM DIF analysis. It does not claim that flagged items "
            "are biased, and its likelihood-ratio p-values are not presented "
            "as full Taylor-linearised NHANES complex-survey inference."
        ),
    }
    (outdir / "v07_anchor_purification_summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    report = f"""# v0.7 PHQ-9 DIF anchor purification and sensitivity

## Primary sex DIF result

The v0.6 screen treated the other eight PHQ-9 items as anchors for every item test. v0.7 removes that assumption. Items currently identified as DIF are allowed to have group-specific discrimination and thresholds while the remaining candidate anchors identify the male/female latent scale. All nine item tests are repeated with Benjamini-Hochberg FDR correction until the flagged set stabilises.

- Purification converged: **{purification_converged}**
- Purification rounds: **{int(history['purification_round'].max())}**
- Final flagged items: **{', '.join(primary_flagged) if primary_flagged else 'none'}**
- Final anchor items: **{', '.join(primary_anchors) if primary_anchors else 'none'}**

A stable DIF flag is still a model-based non-invariance signal, not proof of item bias.

## Anchor sensitivity

Each final anchor is freed in turn and the complete nine-item DIF screen is re-run. The output reports each item's flag fraction across these leave-one-anchor-out analyses.

Items flagged in every leave-one-anchor-out run: **{', '.join(stable_loo) if stable_loo else 'none'}**

The final purified background-free specification is also re-run with equal observation weights. Equal-weight flagged items: **{', '.join(equal_flagged) if equal_flagged else 'none'}**.

This comparison asks whether the main item-level signal depends strongly on the survey weighting point estimates. It is not a replacement for NHANES design-based variance estimation.

## Exploratory age and race/ethnicity screens

Using the sex-purified anchor specification as a fixed sensitivity anchor set:

- {age_meta['comparison']}: N={age_meta['reference_n']:,} vs {age_meta['comparison_n']:,}; flagged items: {', '.join(age_meta['flagged_items']) if age_meta['flagged_items'] else 'none'}.
- {race_meta['comparison']}: N={race_meta['reference_n']:,} vs {race_meta['comparison_n']:,}; flagged items: {', '.join(race_meta['flagged_items']) if race_meta['flagged_items'] else 'none'}.

These are exploratory cross-group screens. A production invariance study would pre-specify clinically meaningful groups, assess sample support, purify anchors within each comparison, and review item content before interpreting group differences.

## NHANES survey-design boundary

The demographic file exposes `SDMVSTRA` and `SDMVPSU`, and v0.7 audits their presence in the complete-case analysis domain. The GRM uses `WTMEC2YR` for weighted pseudo-likelihood point estimation. The current custom IRT likelihood does not implement Taylor-series linearised standard errors, so the LRT p-values are not labelled as full complex-survey inference. Formal NHANES inference should retain the full survey sample and use domain/subpopulation analysis with the masked variance units and MEC weights.

## Scientific interpretation

v0.7 is designed to answer whether the strong v0.6 sex-DIF result was an artefact of assuming eight clean anchors. The important result is therefore the stability of the flag set after purification and anchor perturbation, not the number of significant p-values alone.
"""
    (outdir / "V07_ANCHOR_PURIFICATION_REPORT.md").write_text(report)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpq", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dif-maxiter", type=int, default=140)
    parser.add_argument("--purification-rounds", type=int, default=5)
    args = parser.parse_args()
    summary = run_analysis(
        args.dpq,
        args.demo,
        args.out,
        dif_maxiter=args.dif_maxiter,
        purification_rounds=args.purification_rounds,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

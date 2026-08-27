from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analysis import SAFE_CANDIDATES, binary_metrics, parse_index, split_by_participant

RANDOM_STATE = 42
PHQ_RELIABLE_CHANGE_POINTS = 6.0
PHQ_CASE_CUTOFF = 10.0
SCHEDULED_MONTHS = [3, 6, 9, 12]

BASELINE_AVAILABILITY_CANDIDATES = [
    "birthyear", "educ", "height", "weight", "bmi", "money", "money_assistance",
    "household", "comorbid_migraines", "comorbid_neuropathic", "comorbid_arthritis",
    "comorbid_cancer", "comorbid_diabetes_typ1", "sex", "race_black", "race_white",
    "race_asian", "race_hispanic", "trauma", "insurance", "num_migraine_days",
]


def build_logistic(df: pd.DataFrame, columns: list[str], class_weight: str | None = None) -> Pipeline:
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in columns if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    return Pipeline([
        ("prep", ColumnTransformer(transformers=transformers)),
        ("model", LogisticRegression(max_iter=3000, class_weight=class_weight, random_state=RANDOM_STATE)),
    ])


def interval_scores(df: pd.DataFrame) -> pd.DataFrame:
    required = ["phq9_score_start", "phq9_score_end"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"PHQ-9 score columns missing from source release: {missing}")
    x = df[df["phq9_score_start"].notna() & df["phq9_score_end"].notna()].copy()
    x["phq9_score_start"] = x["phq9_score_start"].astype(float)
    x["phq9_score_end"] = x["phq9_score_end"].astype(float)
    if not x["phq9_score_start"].between(0, 27).all():
        raise ValueError("PHQ-9 start scores outside the valid 0-27 range")
    if not x["phq9_score_end"].between(0, 27).all():
        raise ValueError("PHQ-9 end scores outside the valid 0-27 range")
    x["score_change"] = x["phq9_score_end"] - x["phq9_score_start"]
    x["reliable_improvement_phq9"] = x["score_change"] <= -PHQ_RELIABLE_CHANGE_POINTS
    x["reliable_deterioration_phq9"] = x["score_change"] >= PHQ_RELIABLE_CHANGE_POINTS
    x["no_reliable_change_phq9"] = ~(x["reliable_improvement_phq9"] | x["reliable_deterioration_phq9"])
    x["crossed_below_phq9_case_cutoff"] = (
        (x["phq9_score_start"] >= PHQ_CASE_CUTOFF) & (x["phq9_score_end"] < PHQ_CASE_CUTOFF)
    )
    x["reliably_improved_and_below_cutoff"] = (
        x["reliable_improvement_phq9"] & x["crossed_below_phq9_case_cutoff"]
    )
    x["relative_reduction"] = np.where(
        x["phq9_score_start"] > 0,
        (x["phq9_score_start"] - x["phq9_score_end"]) / x["phq9_score_start"],
        np.nan,
    )
    x["relative_reduction_ge_20pct"] = x["relative_reduction"] >= 0.20
    return x


def build_unique_longitudinal_scores(interval: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    start = interval[["participant_id", "study_month", "phq9_score_start"]].copy()
    start["measurement_month"] = start["study_month"] - 3
    start["score"] = start["phq9_score_start"]
    start["source"] = "interval_start"
    end = interval[["participant_id", "study_month", "phq9_score_end"]].copy()
    end["measurement_month"] = end["study_month"]
    end["score"] = end["phq9_score_end"]
    end["source"] = "interval_end"
    stacked = pd.concat([
        start[["participant_id", "measurement_month", "score", "source"]],
        end[["participant_id", "measurement_month", "score", "source"]],
    ], ignore_index=True)
    consistency = stacked.groupby(["participant_id", "measurement_month"], as_index=False).agg(
        n_source_rows=("score", "size"), score_min=("score", "min"), score_max=("score", "max"), score=("score", "mean")
    )
    consistency["score_range"] = consistency["score_max"] - consistency["score_min"]
    conflicts = consistency[consistency["score_range"] > 1e-9].copy()
    longitudinal = consistency[["participant_id", "measurement_month", "score"]].copy()
    longitudinal["quarter"] = longitudinal["measurement_month"] / 3.0
    return longitudinal, conflicts


def fit_mixed_model(longitudinal: pd.DataFrame) -> dict[str, object]:
    model_df = longitudinal.copy()
    model_df["month_c"] = model_df["measurement_month"] - model_df["measurement_month"].mean()
    try:
        fit = smf.mixedlm("score ~ month_c", model_df, groups=model_df["participant_id"], re_formula="1").fit(
            reml=False, method="lbfgs", maxiter=500, disp=False
        )
        ci = fit.conf_int()
        return {
            "status": "success",
            "n_observations": int(fit.nobs),
            "n_participants": int(model_df["participant_id"].nunique()),
            "intercept_at_mean_month": float(fit.params["Intercept"]),
            "month_coefficient": float(fit.params["month_c"]),
            "month_coefficient_ci95_low": float(ci.loc["month_c", 0]),
            "month_coefficient_ci95_high": float(ci.loc["month_c", 1]),
            "participant_random_intercept_variance": float(fit.cov_re.iloc[0, 0]),
            "residual_variance": float(fit.scale),
            "converged": bool(fit.converged),
            "interpretation": "Descriptive population time trend with participant random intercepts. It is not a treatment-effect estimate.",
        }
    except Exception as exc:
        return {
            "status": "failed", "n_observations": int(len(model_df)),
            "n_participants": int(model_df["participant_id"].nunique()),
            "error": f"{type(exc).__name__}: {exc}",
        }


def save_longitudinal_summary(longitudinal: pd.DataFrame, outdir: Path) -> None:
    summary = longitudinal.groupby("measurement_month", as_index=False).agg(
        n=("score", "size"), mean_score=("score", "mean"), sd_score=("score", "std")
    ).sort_values("measurement_month")
    summary["se"] = summary["sd_score"] / np.sqrt(summary["n"])
    summary["ci95_low"] = summary["mean_score"] - 1.96 * summary["se"]
    summary["ci95_high"] = summary["mean_score"] + 1.96 * summary["se"]
    summary.to_csv(outdir / "phq9_longitudinal_summary.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ax.errorbar(summary["measurement_month"], summary["mean_score"], yerr=1.96 * summary["se"], marker="o", capsize=3)
    ax.set(xlabel="Study month", ylabel="Mean PHQ-9 score")
    fig.tight_layout()
    fig.savefig(outdir / "phq9_longitudinal_mean_ci.png", dpi=220)
    plt.close(fig)


def score_change_outputs(interval: pd.DataFrame, outdir: Path) -> dict[str, object]:
    counts = pd.DataFrame({
        "classification": [
            "reliable_improvement_phq9", "no_reliable_change_phq9", "reliable_deterioration_phq9",
            "crossed_below_phq9_case_cutoff", "reliably_improved_and_below_cutoff", "relative_reduction_ge_20pct",
        ],
        "n": [
            int(interval["reliable_improvement_phq9"].sum()), int(interval["no_reliable_change_phq9"].sum()),
            int(interval["reliable_deterioration_phq9"].sum()), int(interval["crossed_below_phq9_case_cutoff"].sum()),
            int(interval["reliably_improved_and_below_cutoff"].sum()), int(interval["relative_reduction_ge_20pct"].sum()),
        ],
    })
    counts["proportion_all_intervals"] = counts["n"] / len(interval)
    counts.to_csv(outdir / "phq9_change_classifications.csv", index=False)
    baseline_case = interval[interval["phq9_score_start"] >= PHQ_CASE_CUTOFF]
    summary = {
        "n_intervals": int(len(interval)), "n_participants": int(interval["participant_id"].nunique()),
        "mean_start": float(interval["phq9_score_start"].mean()), "mean_end": float(interval["phq9_score_end"].mean()),
        "mean_change_end_minus_start": float(interval["score_change"].mean()),
        "median_change_end_minus_start": float(interval["score_change"].median()),
        "reliable_improvement_rate_phq9": float(interval["reliable_improvement_phq9"].mean()),
        "reliable_deterioration_rate_phq9": float(interval["reliable_deterioration_phq9"].mean()),
        "baseline_case_intervals": int(len(baseline_case)),
        "case_cutoff_crossing_rate_among_baseline_cases": float(baseline_case["crossed_below_phq9_case_cutoff"].mean()) if len(baseline_case) else float("nan"),
        "reliably_improved_and_below_cutoff_rate_among_baseline_cases": float(baseline_case["reliably_improved_and_below_cutoff"].mean()) if len(baseline_case) else float("nan"),
        "relative_reduction_ge_20pct_rate_among_baseline_cases": float(baseline_case["relative_reduction_ge_20pct"].mean()) if len(baseline_case) else float("nan"),
        "threshold_note": "The 6-point PHQ-9 threshold is used as a PHQ-specific reliable-change rule. Crossing below 10 is reported separately. These are not labelled full NHS Talking Therapies reliable improvement/recovery because a paired anxiety measure is not used here.",
        "mcid_sensitivity_note": "The 20% relative reduction flag is a sensitivity analysis motivated by UK primary-care MCID work; it is not treated as a universal PHQ-9 MCID.",
    }
    (outdir / "phq9_score_change_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def availability_grid(df: pd.DataFrame) -> pd.DataFrame:
    participants = pd.DataFrame({"participant_id": sorted(df["participant_id"].unique())})
    schedule = pd.DataFrame({"scheduled_month": SCHEDULED_MONTHS})
    participants["_key"] = 1
    schedule["_key"] = 1
    grid = participants.merge(schedule, on="_key").drop(columns="_key")
    observed = df[df["phq9_score_end"].notna()][["participant_id", "study_month"]].drop_duplicates().rename(columns={"study_month": "scheduled_month"})
    observed["phq_endpoint_available"] = 1
    grid = grid.merge(observed, on=["participant_id", "scheduled_month"], how="left")
    grid["phq_endpoint_available"] = grid["phq_endpoint_available"].fillna(0).astype(int)
    baseline = df.sort_values(["participant_id", "study_month"]).groupby("participant_id", as_index=False).first()
    baseline_cols = [c for c in BASELINE_AVAILABILITY_CANDIDATES if c in baseline.columns]
    return grid.merge(baseline[["participant_id"] + baseline_cols], on="participant_id", how="left")


def availability_audit(df: pd.DataFrame, outdir: Path) -> dict[str, object]:
    grid = availability_grid(df)
    by_month = grid.groupby("scheduled_month", as_index=False).agg(
        n_expected=("participant_id", "size"), n_available=("phq_endpoint_available", "sum"),
        availability_rate=("phq_endpoint_available", "mean")
    ).sort_values("scheduled_month")
    by_month.to_csv(outdir / "phq_endpoint_availability_by_scheduled_month.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(by_month["scheduled_month"], by_month["availability_rate"], marker="o")
    ax.set(xlabel="Scheduled study month", ylabel="PHQ endpoint availability in release", ylim=(0, 1))
    fig.tight_layout()
    fig.savefig(outdir / "phq_endpoint_availability_by_scheduled_month.png", dpi=220)
    plt.close(fig)
    features = [c for c in BASELINE_AVAILABILITY_CANDIDATES if c in grid.columns] + ["scheduled_month"]
    train_idx, test_idx = split_by_participant(grid)
    train, test = grid.iloc[train_idx].copy(), grid.iloc[test_idx].copy()
    model = build_logistic(train, features, class_weight=None)
    model.fit(train[features], train["phq_endpoint_available"])
    p = model.predict_proba(test[features])[:, 1]
    metrics = binary_metrics(test["phq_endpoint_available"].to_numpy(), p)
    metrics.update({
        "expected_participant_quarters": int(len(grid)), "participants": int(grid["participant_id"].nunique()),
        "availability_rate_all": float(grid["phq_endpoint_available"].mean()),
        "n_baseline_predictors_plus_scheduled_month": int(len(features)),
        "participant_overlap": int(len(set(train["participant_id"]) & set(test["participant_id"]))),
        "interpretation": "This models PHQ endpoint availability in the public analytical release over the four planned quarterly assessment months. Absence can reflect questionnaire non-completion, study attrition or preprocessing/eligibility rules, so it is not identified as a clinical missingness mechanism.",
    })
    (outdir / "phq_endpoint_availability_model.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


def deterioration_calibration_comparison(df: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    analysis_df = df[df["phq9_cat_start"].notna() & df["phq9_cat_end"].notna()].copy()
    analysis_df["deterioration"] = (analysis_df["phq9_cat_end"].astype(float) > analysis_df["phq9_cat_start"].astype(float)).astype(int)
    features = [c for c in SAFE_CANDIDATES if c in analysis_df.columns]
    train_idx, test_idx = split_by_participant(analysis_df)
    train, test = analysis_df.iloc[train_idx].copy(), analysis_df.iloc[test_idx].copy()
    records = []
    for label, weight in [("unweighted", None), ("class_weight_balanced", "balanced")]:
        model = build_logistic(train, features, class_weight=weight)
        model.fit(train[features], train["deterioration"])
        p = model.predict_proba(test[features])[:, 1]
        records.append({"model": label, **binary_metrics(test["deterioration"].to_numpy(), p)})
    comparison = pd.DataFrame(records)
    comparison.to_csv(outdir / "deterioration_probability_model_comparison.csv", index=False)
    return comparison


def main(data_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = parse_index(pd.read_parquet(data_path))
    interval = interval_scores(df)
    change_summary = score_change_outputs(interval, outdir)
    longitudinal, conflicts = build_unique_longitudinal_scores(interval)
    conflicts.to_csv(outdir / "phq9_longitudinal_score_conflicts.csv", index=False)
    longitudinal.to_csv(outdir / "phq9_longitudinal_scores.csv", index=False)
    save_longitudinal_summary(longitudinal, outdir)
    mixed = fit_mixed_model(longitudinal)
    mixed["n_conflicting_participant_months"] = int(len(conflicts))
    (outdir / "phq9_mixed_model.json").write_text(json.dumps(mixed, indent=2) + "\n")
    availability = availability_audit(df, outdir)
    calibration_compare = deterioration_calibration_comparison(df, outdir)
    unweighted = calibration_compare.loc[calibration_compare["model"] == "unweighted"].iloc[0]
    balanced = calibration_compare.loc[calibration_compare["model"] == "class_weight_balanced"].iloc[0]
    summary = {
        "source_rows": int(len(df)), "source_participants": int(df["participant_id"].nunique()),
        "score_intervals": int(len(interval)), "score_interval_participants": int(interval["participant_id"].nunique()),
        "unique_longitudinal_measurements": int(len(longitudinal)), "mixed_model_status": mixed["status"],
        "reliable_improvement_rate_phq9": change_summary["reliable_improvement_rate_phq9"],
        "reliable_deterioration_rate_phq9": change_summary["reliable_deterioration_rate_phq9"],
        "phq_endpoint_availability_rate": availability["availability_rate_all"],
        "availability_model_auc": availability["roc_auc"],
        "deterioration_unweighted_auc": float(unweighted["roc_auc"]),
        "deterioration_unweighted_brier": float(unweighted["brier"]),
        "deterioration_unweighted_calibration_intercept": float(unweighted["calibration_intercept"]),
        "deterioration_unweighted_calibration_slope": float(unweighted["calibration_slope"]),
        "deterioration_balanced_brier": float(balanced["brier"]),
        "deterioration_balanced_calibration_intercept": float(balanced["calibration_intercept"]),
        "deterioration_balanced_calibration_slope": float(balanced["calibration_slope"]),
        "timing_boundary": "The released candidate features can include information collected within the 3-month sample. This module therefore calls the task participant-held-out deterioration classification, not a deployable prospective risk forecast. A production risk model would freeze features at a prespecified prediction time.",
    }
    (outdir / "v02_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = f"""# v0.2 score-level longitudinal and calibration audit

## Score-level evidence

- Real PSYCHE-D source rows: {summary['source_rows']:,}
- Source participants: {summary['source_participants']:,}
- Three-month intervals with start/end PHQ-9 scores: {summary['score_intervals']:,}
- Participants contributing score intervals: {summary['score_interval_participants']:,}
- Unique participant-month PHQ-9 measurements reconstructed: {summary['unique_longitudinal_measurements']:,}
- PHQ-9 reliable-improvement rate (decrease >= 6 points): {summary['reliable_improvement_rate_phq9']:.3f}
- PHQ-9 reliable-deterioration rate (increase >= 6 points): {summary['reliable_deterioration_rate_phq9']:.3f}

## Repeated measures

Mixed-effects fit status: {summary['mixed_model_status']}.

The mixed model is a descriptive longitudinal model with participant random intercepts. It is not interpreted as a treatment effect.

## Outcome availability

- Expected participant-quarter assessments in the audit grid: {availability['expected_participant_quarters']:,}
- PHQ endpoint availability in the released analytical file: {availability['availability_rate_all']:.3f}
- Baseline/scheduled-month model AUC for endpoint availability: {availability['roc_auc']:.3f}

This fixes the v0.1 diagnostic problem: conditioning on rows with `phq9_cat_start` selected a set where the endpoint was always observed. v0.2 instead constructs the four expected quarterly assessment opportunities for every participant. Absence in the public analytical file still cannot be identified specifically as questionnaire non-response; study attrition and preprocessing can also contribute.

## Probability calibration check

Unweighted logistic baseline:
- AUC: {unweighted['roc_auc']:.3f}
- Brier: {unweighted['brier']:.3f}
- calibration intercept: {unweighted['calibration_intercept']:.3f}
- calibration slope: {unweighted['calibration_slope']:.3f}

Class-weight-balanced logistic baseline:
- AUC: {balanced['roc_auc']:.3f}
- Brier: {balanced['brier']:.3f}
- calibration intercept: {balanced['calibration_intercept']:.3f}
- calibration slope: {balanced['calibration_slope']:.3f}

Class weighting can be useful for some classification objectives, but it changes probability estimates. For a clinical risk score, calibration should be assessed directly rather than assuming class balancing improves the probability model.

## Timing boundary

{summary['timing_boundary']}

## Clinical-change boundary

The 6-point PHQ-9 threshold is used for PHQ-specific reliable improvement/deterioration. A PHQ-9 score below 10 is reported separately as a caseness-cutoff crossing. This module does not call those combined quantities full NHS Talking Therapies reliable improvement or reliable recovery because the service definition also considers the paired anxiety measure. A 20% relative score reduction is included only as an MCID sensitivity analysis, not as a universal threshold.
"""
    (outdir / "V02_SCORE_LONGITUDINAL_REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

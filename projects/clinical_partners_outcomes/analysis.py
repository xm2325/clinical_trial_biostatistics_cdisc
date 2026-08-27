from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42

# Restricted to variables used or explicitly considered by the released PSYCHE-D
# pipeline. PHQ-9 end-state variables and generated phase-1 probabilities are
# intentionally excluded to avoid outcome leakage.
SAFE_CANDIDATES = [
    "birthyear",
    "educ",
    "height",
    "weight",
    "bmi",
    "money",
    "money_assistance",
    "household",
    "comorbid_migraines",
    "comorbid_neuropathic",
    "comorbid_arthritis",
    "comorbid_cancer",
    "comorbid_diabetes_typ1",
    "sex",
    "race_black",
    "race_white",
    "race_asian",
    "race_hispanic",
    "trauma",
    "insurance",
    "num_migraine_days",
    "med_start",
    "med_stop",
    "med_dose",
    "nonmed_start",
    "nonmed_stop",
    "life_meditation",
    "life_stress",
    "life_activity_eating",
    "life_red_stop_alcoh",
    "sleep_asleep_mean_recent",
    "sleep_in_bed_mean_recent",
    "sleep_ratio_asleep_in_bed_mean_recent",
    "sleep_main_start_hour_adj_range",
    "steps_lpa_sum_recent",
    "steps_mvpa_sum_recent",
    "steps_rolling_6_median_recent",
    "steps_rolling_6_max_recent",
]


def parse_index(df: pd.DataFrame) -> pd.DataFrame:
    """Recover participant and study month from the released participant_month index."""
    out = df.copy()
    values = out.index.astype(str).tolist()
    parts = [value.rsplit("_", 1) for value in values]
    if any(len(part) != 2 or not part[0] or not part[1] for part in parts):
        raise ValueError("Expected PSYCHE-D index in participant_month form")
    out["participant_id"] = [part[0] for part in parts]
    out["study_month"] = pd.to_numeric([part[1] for part in parts], errors="raise").astype(int)
    return out


def infer_feature_types(df: pd.DataFrame, columns: list[str]) -> tuple[list[str], list[str]]:
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in columns if c not in numeric]
    return numeric, categorical


def build_logistic(df: pd.DataFrame, columns: list[str]) -> Pipeline:
    numeric, categorical = infer_feature_types(df, columns)
    transformers = []
    if numeric:
        transformers.append(
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    prep = ColumnTransformer(transformers=transformers)
    return Pipeline(
        [
            ("prep", prep),
            (
                "model",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def split_by_participant(df: pd.DataFrame, test_size: float = 0.25) -> tuple[np.ndarray, np.ndarray]:
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(df, groups=df["participant_id"]))
    train_users = set(df.iloc[train_idx]["participant_id"])
    test_users = set(df.iloc[test_idx]["participant_id"])
    if train_users & test_users:
        raise AssertionError("Participant leakage detected")
    return train_idx, test_idx


def calibration_intercept_slope(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    if len(np.unique(y)) < 2:
        return float("nan"), float("nan")
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000)
    model.fit(logit, y)
    return float(model.intercept_[0]), float(model.coef_[0, 0])


def binary_metrics(y: np.ndarray, p: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    intercept, slope = calibration_intercept_slope(y, p)
    return {
        "n": int(len(y)),
        "prevalence": float(np.mean(y)),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan"),
        "average_precision": float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else float("nan"),
        "brier": float(brier_score_loss(y, p)),
        "precision_at_0_5": float(precision_score(y, pred, zero_division=0)),
        "sensitivity_at_0_5": float(tp / (tp + fn)) if tp + fn else float("nan"),
        "specificity_at_0_5": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }


def save_calibration(y: np.ndarray, p: np.ndarray, outdir: Path) -> None:
    prob_true, prob_pred = calibration_curve(y, p, n_bins=8, strategy="quantile")
    pd.DataFrame({"mean_predicted_probability": prob_pred, "observed_rate": prob_true}).to_csv(
        outdir / "calibration_curve.csv", index=False
    )
    fig, ax = plt.subplots(figsize=(5.5, 5.0))
    ax.plot([0, 1], [0, 1], "--", linewidth=1, label="Ideal")
    ax.plot(prob_pred, prob_true, marker="o", linewidth=1.5, label="Grouped test set")
    ax.set(xlabel="Predicted deterioration probability", ylabel="Observed deterioration rate")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(outdir / "calibration_curve.png", dpi=220)
    plt.close(fig)


def subgroup_metrics(test: pd.DataFrame, y: np.ndarray, p: np.ndarray) -> pd.DataFrame:
    work = test.copy()
    work["_y"] = y
    work["_p"] = p
    records: list[dict] = []
    for variable in ["sex", "race_black", "race_hispanic", "insurance"]:
        if variable not in work.columns:
            continue
        for level, grp in work.groupby(variable, dropna=False):
            if len(grp) < 50 or grp["_y"].nunique() < 2:
                continue
            m = binary_metrics(grp["_y"].to_numpy(), grp["_p"].to_numpy())
            records.append({"variable": variable, "level": str(level), **m})
    return pd.DataFrame.from_records(records)


def endpoint_missingness_audit(df: pd.DataFrame, features: list[str], outdir: Path) -> dict[str, float]:
    audit = df.copy()
    audit["endpoint_observed"] = audit["phq9_cat_end"].notna().astype(int)
    eligible = audit[audit["phq9_cat_start"].notna()].copy()
    month = (
        eligible.groupby("study_month", as_index=False)
        .agg(n=("participant_id", "size"), endpoint_observed_rate=("endpoint_observed", "mean"))
        .sort_values("study_month")
    )
    month.to_csv(outdir / "endpoint_observation_by_month.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(month["study_month"], month["endpoint_observed_rate"], marker="o")
    ax.set(xlabel="Study month", ylabel="PHQ-9 endpoint observed proportion", ylim=(0, 1))
    fig.tight_layout()
    fig.savefig(outdir / "endpoint_observation_by_month.png", dpi=220)
    plt.close(fig)

    if eligible["endpoint_observed"].nunique() < 2:
        return {"n": int(len(eligible)), "observed_rate": float(eligible["endpoint_observed"].mean())}

    train_idx, test_idx = split_by_participant(eligible)
    train = eligible.iloc[train_idx]
    test = eligible.iloc[test_idx]
    model = build_logistic(train, features)
    model.fit(train[features], train["endpoint_observed"])
    p = model.predict_proba(test[features])[:, 1]
    m = binary_metrics(test["endpoint_observed"].to_numpy(), p)
    m["observed_rate_all"] = float(eligible["endpoint_observed"].mean())
    m["interpretation"] = (
        "AUC above 0.5 indicates that observed baseline/behavioural variables predict PHQ-9 endpoint availability; "
        "this is evidence against treating missingness as obviously MCAR, not proof of MAR or MNAR."
    )
    return m


def transition_table(analysis_df: pd.DataFrame, outdir: Path) -> None:
    counts = pd.crosstab(
        analysis_df["phq9_cat_start"], analysis_df["phq9_cat_end"], dropna=False
    )
    counts.to_csv(outdir / "phq9_category_transition_counts.csv")
    row_rates = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)
    row_rates.to_csv(outdir / "phq9_category_transition_row_rates.csv")


def main(data_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_parquet(data_path)
    df = parse_index(raw)

    required = {"phq9_cat_start", "phq9_cat_end"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Released PSYCHE-D schema missing required variables: {missing}")

    phq_cols = sorted(c for c in df.columns if "phq" in c.lower())
    pd.DataFrame({"phq_related_column": phq_cols}).to_csv(outdir / "phq_schema_columns.csv", index=False)
    pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(df[c].dtype) for c in df.columns],
            "missing_fraction": [float(df[c].isna().mean()) for c in df.columns],
        }
    ).to_csv(outdir / "schema_audit.csv", index=False)

    features = [c for c in SAFE_CANDIDATES if c in df.columns]
    if len(features) < 5:
        raise RuntimeError(f"Only {len(features)} safe candidate predictors found; refusing to run a weak model")

    analysis_df = df[df["phq9_cat_start"].notna() & df["phq9_cat_end"].notna()].copy()
    analysis_df["deterioration"] = (
        analysis_df["phq9_cat_end"].astype(float) > analysis_df["phq9_cat_start"].astype(float)
    ).astype(int)

    cohort = {
        "raw_rows": int(len(df)),
        "participants": int(df["participant_id"].nunique()),
        "study_month_min": int(df["study_month"].min()),
        "study_month_max": int(df["study_month"].max()),
        "analysis_rows_with_start_and_end": int(len(analysis_df)),
        "analysis_participants": int(analysis_df["participant_id"].nunique()),
        "deterioration_prevalence": float(analysis_df["deterioration"].mean()),
        "n_safe_predictors": int(len(features)),
        "raw_phq_total_score_detected": bool(
            any("score" in c.lower() and "phq" in c.lower() for c in phq_cols)
        ),
        "note": "Deterioration follows the released PSYCHE-D definition: end PHQ-9 category greater than start category.",
    }
    (outdir / "cohort_flow.json").write_text(json.dumps(cohort, indent=2) + "\n")
    pd.DataFrame({"safe_predictor": features}).to_csv(outdir / "safe_predictors_used.csv", index=False)

    transition_table(analysis_df, outdir)

    train_idx, test_idx = split_by_participant(analysis_df)
    train = analysis_df.iloc[train_idx].copy()
    test = analysis_df.iloc[test_idx].copy()
    model = build_logistic(train, features)
    model.fit(train[features], train["deterioration"])
    p_test = model.predict_proba(test[features])[:, 1]
    predictive = binary_metrics(test["deterioration"].to_numpy(), p_test)
    predictive.update(
        {
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_participants": int(train["participant_id"].nunique()),
            "test_participants": int(test["participant_id"].nunique()),
            "participant_overlap": int(
                len(set(train["participant_id"]) & set(test["participant_id"]))
            ),
        }
    )
    (outdir / "deterioration_model_metrics.json").write_text(json.dumps(predictive, indent=2) + "\n")
    save_calibration(test["deterioration"].to_numpy(), p_test, outdir)

    sg = subgroup_metrics(test, test["deterioration"].to_numpy(), p_test)
    sg.to_csv(outdir / "subgroup_metrics.csv", index=False)

    missingness = endpoint_missingness_audit(df, features, outdir)
    (outdir / "missingness_audit.json").write_text(json.dumps(missingness, indent=2) + "\n")

    report = f"""# Clinical outcomes real-data audit — PSYCHE-D

## Cohort

- Rows in release: {cohort['raw_rows']:,}
- Unique participants: {cohort['participants']:,}
- Rows with observed start/end PHQ-9 category: {cohort['analysis_rows_with_start_and_end']:,}
- Participants in modelling cohort: {cohort['analysis_participants']:,}
- Deterioration prevalence: {cohort['deterioration_prevalence']:.3f}
- Safe predictors used: {cohort['n_safe_predictors']}

## Participant-held-out deterioration model

- ROC-AUC: {predictive['roc_auc']:.3f}
- Average precision: {predictive['average_precision']:.3f}
- Brier score: {predictive['brier']:.3f}
- Calibration intercept: {predictive['calibration_intercept']:.3f}
- Calibration slope: {predictive['calibration_slope']:.3f}
- Train/test participant overlap: {predictive['participant_overlap']}

## Missingness

- Endpoint observation model ROC-AUC: {missingness.get('roc_auc', float('nan')):.3f}
- Overall endpoint-observed rate among rows with baseline category: {missingness.get('observed_rate_all', missingness.get('observed_rate', float('nan'))):.3f}

The missingness model is a diagnostic: predictability of observation status is evidence against assuming MCAR without investigation. It does not identify MAR versus MNAR.

## Clinical interpretation boundary

This stage reproduces a category-based deterioration target supported by the released PSYCHE-D schema. It does **not** claim treatment effectiveness, diagnosis, reliable change, MCID, or causal effects. Reliable-change analysis will only be added if a valid raw PHQ-9 total/item score is present in the public release or another licensed open dataset is linked.
"""
    (outdir / "REAL_DATA_REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

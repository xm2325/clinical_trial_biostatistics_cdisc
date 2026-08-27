from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

from analysis import SAFE_CANDIDATES, binary_metrics, parse_index, split_by_participant
from v02_score_longitudinal import (
    PHQ_RELIABLE_CHANGE_POINTS,
    build_logistic,
    build_unique_longitudinal_scores,
    interval_scores,
)

RANDOM_STATE = 42

# These variables come from the PSYCHE-D screener/baseline domain and are treated
# as fixed participant attributes. Unlike lifestyle, medication-change and wearable
# summaries, they do not use information collected later within the 3-month interval.
STATIC_BASELINE_CANDIDATES = [
    "birthyear", "educ", "height", "weight", "bmi", "money", "money_assistance",
    "household", "comorbid_migraines", "comorbid_neuropathic", "comorbid_arthritis",
    "comorbid_cancer", "comorbid_diabetes_typ1", "sex", "race_black", "race_white",
    "race_asian", "race_hispanic", "trauma", "insurance", "num_migraine_days",
]


def baseline_table(df: pd.DataFrame) -> pd.DataFrame:
    """Freeze screener-like variables at each participant's first released row."""
    cols = [c for c in STATIC_BASELINE_CANDIDATES if c in df.columns]
    ordered = df.sort_values(["participant_id", "study_month"])
    return ordered.groupby("participant_id", as_index=False).first()[["participant_id"] + cols]


def prospective_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Build a strict t0 dataset and a broader interval-feature comparator.

    The strict model can use the PHQ-9 score at interval start plus participant
    baseline/screener variables frozen from the first released row. The broad
    comparator uses the same outcome rows but may include variables whose source
    collection can occur during the interval; it is therefore an analysis reference,
    not a deployment-safe prospective feature set.
    """
    intervals = interval_scores(df)
    base = baseline_table(df)
    drop_baseline = [c for c in STATIC_BASELINE_CANDIDATES if c in intervals.columns]
    intervals = intervals.drop(columns=drop_baseline, errors="ignore").merge(base, on="participant_id", how="left")
    intervals["reliable_deterioration"] = (
        intervals["score_change"] >= PHQ_RELIABLE_CHANGE_POINTS
    ).astype(int)
    strict_features = ["phq9_score_start"] + [c for c in STATIC_BASELINE_CANDIDATES if c in intervals.columns]
    broad_features = ["phq9_score_start"] + [c for c in SAFE_CANDIDATES if c in intervals.columns]
    broad_features = list(dict.fromkeys(broad_features))
    return intervals, strict_features, broad_features


def fit_comparable_models(
    df: pd.DataFrame,
    strict_features: list[str],
    broad_features: list[str],
    outdir: Path,
) -> dict[str, object]:
    train_idx, test_idx = split_by_participant(df)
    train, test = df.iloc[train_idx].copy(), df.iloc[test_idx].copy()
    y_train = train["reliable_deterioration"].to_numpy()
    y_test = test["reliable_deterioration"].to_numpy()

    records = []
    prediction_frames = []
    for label, features, deployment_safe in [
        ("strict_t0", strict_features, True),
        ("broad_interval_reference", broad_features, False),
    ]:
        model = build_logistic(train, features, class_weight=None)
        model.fit(train[features], y_train)
        p = model.predict_proba(test[features])[:, 1]
        metrics = binary_metrics(y_test, p)
        metrics.update({
            "model": label,
            "deployment_safe_t0_features": deployment_safe,
            "n_features": int(len(features)),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_participants": int(train["participant_id"].nunique()),
            "test_participants": int(test["participant_id"].nunique()),
            "participant_overlap": int(len(set(train["participant_id"]) & set(test["participant_id"]))),
        })
        records.append(metrics)
        prediction_frames.append(pd.DataFrame({
            "participant_id": test["participant_id"].astype(str).to_numpy(),
            "study_month": test["study_month"].to_numpy(),
            "outcome": y_test,
            "model": label,
            "probability": p,
        }))

    comparison = pd.DataFrame(records)
    comparison.to_csv(outdir / "v03_prospective_model_comparison.csv", index=False)
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        outdir / "v03_prospective_heldout_predictions.csv", index=False
    )

    strict = comparison.loc[comparison["model"] == "strict_t0"].iloc[0]
    broad = comparison.loc[comparison["model"] == "broad_interval_reference"].iloc[0]
    summary = {
        "endpoint": f"PHQ-9 increase >= {PHQ_RELIABLE_CHANGE_POINTS:g} points over the next 3-month interval",
        "outcome_prevalence": float(df["reliable_deterioration"].mean()),
        "strict_t0_n_features": int(len(strict_features)),
        "broad_reference_n_features": int(len(broad_features)),
        "strict_t0_roc_auc": float(strict["roc_auc"]),
        "strict_t0_average_precision": float(strict["average_precision"]),
        "strict_t0_brier": float(strict["brier"]),
        "strict_t0_calibration_intercept": float(strict["calibration_intercept"]),
        "strict_t0_calibration_slope": float(strict["calibration_slope"]),
        "broad_reference_roc_auc": float(broad["roc_auc"]),
        "broad_reference_brier": float(broad["brier"]),
        "participant_overlap": int(strict["participant_overlap"]),
        "interpretation": (
            "The strict model uses only interval-start PHQ-9 plus participant baseline/screener variables. "
            "The broader model is reported only as a leakage-risk reference because lifestyle, medication-change "
            "or wearable summaries may use information collected after prediction time."
        ),
    }
    (outdir / "v03_prospective_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def participant_trajectory_features(longitudinal: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for participant_id, grp in longitudinal.groupby("participant_id"):
        g = grp.sort_values("measurement_month")
        if len(g) < 3 or g["measurement_month"].nunique() < 3:
            continue
        x = g["measurement_month"].to_numpy(dtype=float)
        y = g["score"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        fitted = intercept + slope * x
        rows.append({
            "participant_id": str(participant_id),
            "n_measurements": int(len(g)),
            "baseline_score": float(y[0]),
            "last_score": float(y[-1]),
            "slope_per_month": float(slope),
            "residual_sd": float(np.sqrt(np.mean((y - fitted) ** 2))),
        })
    return pd.DataFrame(rows)


def select_gmm(features: pd.DataFrame, outdir: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    x_raw = features[["baseline_score", "slope_per_month"]].to_numpy(dtype=float)
    scaler = StandardScaler()
    x = scaler.fit_transform(x_raw)
    candidates = []
    models: dict[int, GaussianMixture] = {}
    for k in range(2, 6):
        gmm = GaussianMixture(n_components=k, covariance_type="full", random_state=RANDOM_STATE, n_init=20)
        labels = gmm.fit_predict(x)
        counts = np.bincount(labels, minlength=k)
        min_fraction = float(counts.min() / len(labels))
        candidates.append({
            "k": k,
            "bic": float(gmm.bic(x)),
            "aic": float(gmm.aic(x)),
            "min_class_fraction": min_fraction,
        })
        models[k] = gmm
    selection = pd.DataFrame(candidates)
    selection.to_csv(outdir / "v03_trajectory_gmm_selection.csv", index=False)
    eligible = selection[selection["min_class_fraction"] >= 0.05]
    chosen_row = (eligible if len(eligible) else selection).sort_values("bic").iloc[0]
    k = int(chosen_row["k"])
    chosen = models[k]
    labels = chosen.predict(x)

    # Repeated-initialisation stability on the same participant feature matrix.
    aris = []
    for seed in range(10):
        alt = GaussianMixture(n_components=k, covariance_type="full", random_state=seed + 100, n_init=10)
        alt_labels = alt.fit_predict(x)
        aris.append(adjusted_rand_score(labels, alt_labels))

    assigned = features.copy()
    assigned["trajectory_class"] = labels
    assigned.to_csv(outdir / "v03_trajectory_participant_classes.csv", index=False)
    class_summary = assigned.groupby("trajectory_class", as_index=False).agg(
        n_participants=("participant_id", "size"),
        mean_baseline_score=("baseline_score", "mean"),
        mean_last_score=("last_score", "mean"),
        mean_slope_per_month=("slope_per_month", "mean"),
        mean_residual_sd=("residual_sd", "mean"),
    )
    class_summary["proportion"] = class_summary["n_participants"] / len(assigned)
    class_summary.to_csv(outdir / "v03_trajectory_class_summary.csv", index=False)

    summary = {
        "n_participants_with_at_least_3_scores": int(len(assigned)),
        "selected_k": k,
        "selection_rule": "lowest BIC among solutions with every class >=5% of participants; otherwise lowest BIC",
        "selected_bic": float(chosen_row["bic"]),
        "minimum_class_fraction": float(class_summary["proportion"].min()),
        "repeated_initialisation_mean_ari": float(np.mean(aris)),
        "repeated_initialisation_min_ari": float(np.min(aris)),
        "interpretation": (
            "These are exploratory model-based trajectory phenotypes formed from baseline PHQ-9 and individual "
            "linear slope. They are not validated biological or clinical subtypes."
        ),
    }
    (outdir / "v03_trajectory_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return assigned, summary


def save_trajectory_plot(longitudinal: pd.DataFrame, assigned: pd.DataFrame, outdir: Path) -> None:
    merged = longitudinal.merge(assigned[["participant_id", "trajectory_class"]], on="participant_id", how="inner")
    summary = merged.groupby(["trajectory_class", "measurement_month"], as_index=False).agg(
        n=("score", "size"), mean_score=("score", "mean"), sd_score=("score", "std")
    )
    summary["se"] = summary["sd_score"] / np.sqrt(summary["n"])
    summary.to_csv(outdir / "v03_trajectory_observed_means.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for cls, grp in summary.groupby("trajectory_class"):
        ax.plot(grp["measurement_month"], grp["mean_score"], marker="o", label=f"Class {cls}")
    ax.set(xlabel="Study month", ylabel="Observed mean PHQ-9 score")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(outdir / "v03_trajectory_observed_means.png", dpi=220)
    plt.close(fig)


def main(data_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = parse_index(pd.read_parquet(data_path))

    intervals, strict_features, broad_features = prospective_dataset(df)
    prospective = fit_comparable_models(intervals, strict_features, broad_features, outdir)

    longitudinal, conflicts = build_unique_longitudinal_scores(intervals)
    if len(conflicts):
        raise AssertionError(f"Conflicting PHQ-9 scores at shared interval boundaries: {len(conflicts)}")
    traj_features = participant_trajectory_features(longitudinal)
    assigned, trajectory = select_gmm(traj_features, outdir)
    save_trajectory_plot(longitudinal, assigned, outdir)

    combined = {
        "version": "0.3",
        "prospective": prospective,
        "trajectory": trajectory,
        "boundaries": [
            "The prospective model predicts a 3-month PHQ-9 reliable deterioration endpoint, not diagnosis or treatment effect.",
            "The broad interval-feature model is a leakage-risk comparator, not a deployment candidate.",
            "Trajectory classes are exploratory phenotypes and require external clinical validation before any subtype claim.",
        ],
    }
    (outdir / "v03_summary.json").write_text(json.dumps(combined, indent=2) + "\n")

    report = f"""# v0.3 prospective prediction and trajectory report\n\n## Strict prediction-time experiment\n\n- Endpoint: {prospective['endpoint']}\n- Endpoint prevalence: {prospective['outcome_prevalence']:.3f}\n- Strict t0 ROC-AUC: {prospective['strict_t0_roc_auc']:.3f}\n- Strict t0 average precision: {prospective['strict_t0_average_precision']:.3f}\n- Strict t0 Brier score: {prospective['strict_t0_brier']:.3f}\n- Strict t0 calibration intercept: {prospective['strict_t0_calibration_intercept']:.3f}\n- Strict t0 calibration slope: {prospective['strict_t0_calibration_slope']:.3f}\n- Broad interval-reference ROC-AUC: {prospective['broad_reference_roc_auc']:.3f}\n- Broad interval-reference Brier: {prospective['broad_reference_brier']:.3f}\n- Train/test participant overlap: {prospective['participant_overlap']}\n\nThe strict model uses only the PHQ-9 score available at the start of the interval plus baseline/screener variables frozen per participant. The broader model is deliberately not called prospective because its source features can include information gathered within the future interval.\n\n## Exploratory trajectory phenotyping\n\n- Participants with at least three PHQ-9 measurements: {trajectory['n_participants_with_at_least_3_scores']:,}\n- Selected number of classes: {trajectory['selected_k']}\n- Minimum class fraction: {trajectory['minimum_class_fraction']:.3f}\n- Mean repeated-initialisation ARI: {trajectory['repeated_initialisation_mean_ari']:.3f}\n- Minimum repeated-initialisation ARI: {trajectory['repeated_initialisation_min_ari']:.3f}\n\nThe classes are based on baseline PHQ-9 and participant-specific linear slope. They are descriptive model-based phenotypes rather than validated clinical subtypes.\n"""
    (outdir / "V03_PROSPECTIVE_TRAJECTORY_REPORT.md").write_text(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

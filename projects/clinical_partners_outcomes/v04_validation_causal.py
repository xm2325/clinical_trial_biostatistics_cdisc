from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from analysis import binary_metrics, parse_index, split_by_participant
from v02_score_longitudinal import build_logistic, build_unique_longitudinal_scores
from v03_prospective_trajectory import (
    participant_trajectory_features,
    prospective_dataset,
)

RANDOM_STATE = 42
BOOTSTRAP_REPLICATES = 300
EARLY_ENDPOINT_MONTHS = (3, 6)
LATE_ENDPOINT_MONTHS = (9, 12)


def temporal_participant_disjoint_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a forward-time evaluation with participant separation.

    Participants are first separated using the existing deterministic group split.
    Training then uses only early interval endpoints (months 3/6), while testing uses
    only late interval endpoints (months 9/12) from held-out participants. Because an
    interval ending at month m starts at m-3, this trains at t0 months 0/3 and tests
    at t0 months 6/9.
    """
    train_idx, test_idx = split_by_participant(df)
    train_users = set(df.iloc[train_idx]["participant_id"].astype(str))
    test_users = set(df.iloc[test_idx]["participant_id"].astype(str))
    train = df[
        df["participant_id"].astype(str).isin(train_users)
        & df["study_month"].isin(EARLY_ENDPOINT_MONTHS)
    ].copy()
    test = df[
        df["participant_id"].astype(str).isin(test_users)
        & df["study_month"].isin(LATE_ENDPOINT_MONTHS)
    ].copy()
    overlap = set(train["participant_id"].astype(str)) & set(test["participant_id"].astype(str))
    if overlap:
        raise AssertionError("Temporal validation participant leakage detected")
    if train.empty or test.empty:
        raise ValueError("Temporal validation produced an empty train or test set")
    if train["reliable_deterioration"].nunique() < 2 or test["reliable_deterioration"].nunique() < 2:
        raise ValueError("Temporal validation requires both outcome classes in train and test")
    return train, test


def fit_temporal_validation(
    intervals: pd.DataFrame,
    strict_features: list[str],
    outdir: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    train, test = temporal_participant_disjoint_split(intervals)
    model = build_logistic(train, strict_features, class_weight=None)
    model.fit(train[strict_features], train["reliable_deterioration"].to_numpy())
    p = model.predict_proba(test[strict_features])[:, 1]
    y = test["reliable_deterioration"].to_numpy()
    metrics = binary_metrics(y, p)
    metrics.update({
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_participants": int(train["participant_id"].nunique()),
        "test_participants": int(test["participant_id"].nunique()),
        "participant_overlap": 0,
        "train_endpoint_months": list(EARLY_ENDPOINT_MONTHS),
        "test_endpoint_months": list(LATE_ENDPOINT_MONTHS),
        "train_prediction_time_months": [m - 3 for m in EARLY_ENDPOINT_MONTHS],
        "test_prediction_time_months": [m - 3 for m in LATE_ENDPOINT_MONTHS],
        "n_features": int(len(strict_features)),
    })
    predictions = pd.DataFrame({
        "participant_id": test["participant_id"].astype(str).to_numpy(),
        "study_month": test["study_month"].to_numpy(),
        "prediction_time_month": test["study_month"].to_numpy() - 3,
        "outcome": y,
        "probability": p,
    })
    predictions.to_csv(outdir / "v04_temporal_heldout_predictions.csv", index=False)

    by_month = []
    for month, grp in predictions.groupby("study_month"):
        m = binary_metrics(grp["outcome"].to_numpy(), grp["probability"].to_numpy())
        m.update({
            "study_month": int(month),
            "prediction_time_month": int(month - 3),
            "participants": int(grp["participant_id"].nunique()),
        })
        by_month.append(m)
    pd.DataFrame(by_month).sort_values("study_month").to_csv(
        outdir / "v04_temporal_metrics_by_month.csv", index=False
    )
    (outdir / "v04_temporal_validation_summary.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return predictions, metrics


def cluster_bootstrap_metrics(
    predictions: pd.DataFrame,
    n_boot: int = BOOTSTRAP_REPLICATES,
    seed: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cluster bootstrap by participant for uncertainty in held-out metrics."""
    rng = np.random.default_rng(seed)
    participant_ids = predictions["participant_id"].astype(str).drop_duplicates().to_numpy()
    records: list[dict[str, float | int]] = []
    grouped = {pid: grp.copy() for pid, grp in predictions.groupby(predictions["participant_id"].astype(str))}
    for replicate in range(n_boot):
        sampled = rng.choice(participant_ids, size=len(participant_ids), replace=True)
        frames = [grouped[str(pid)] for pid in sampled]
        boot = pd.concat(frames, ignore_index=True)
        m = binary_metrics(boot["outcome"].to_numpy(), boot["probability"].to_numpy())
        m["replicate"] = replicate
        records.append(m)
    reps = pd.DataFrame(records)
    metric_names = [
        "roc_auc", "average_precision", "brier",
        "calibration_intercept", "calibration_slope",
    ]
    summary_rows = []
    point = binary_metrics(predictions["outcome"].to_numpy(), predictions["probability"].to_numpy())
    for name in metric_names:
        values = pd.to_numeric(reps[name], errors="coerce").dropna().to_numpy(dtype=float)
        summary_rows.append({
            "metric": name,
            "point_estimate": float(point[name]),
            "bootstrap_replicates_requested": int(n_boot),
            "bootstrap_replicates_finite": int(len(values)),
            "ci95_low": float(np.quantile(values, 0.025)),
            "ci95_high": float(np.quantile(values, 0.975)),
        })
    return reps, pd.DataFrame(summary_rows)


def save_bootstrap_uncertainty(predictions: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    reps, summary = cluster_bootstrap_metrics(predictions)
    reps.to_csv(outdir / "v04_temporal_cluster_bootstrap_replicates.csv", index=False)
    summary.to_csv(outdir / "v04_temporal_cluster_bootstrap_ci.csv", index=False)
    return summary


def decision_curve(predictions: pd.DataFrame, thresholds: np.ndarray | None = None) -> pd.DataFrame:
    if thresholds is None:
        thresholds = np.arange(0.02, 0.201, 0.01)
    y = predictions["outcome"].to_numpy(dtype=int)
    p = predictions["probability"].to_numpy(dtype=float)
    n = len(y)
    prevalence = float(np.mean(y))
    rows = []
    for threshold in thresholds:
        threshold = float(threshold)
        pred = p >= threshold
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        weight = threshold / (1.0 - threshold)
        rows.append({
            "threshold": threshold,
            "net_benefit_model": float(tp / n - fp / n * weight),
            "net_benefit_treat_all": float(prevalence - (1.0 - prevalence) * weight),
            "net_benefit_treat_none": 0.0,
            "flagged_fraction": float(np.mean(pred)),
        })
    return pd.DataFrame(rows)


def save_decision_curve(predictions: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    dca = decision_curve(predictions)
    dca.to_csv(outdir / "v04_temporal_decision_curve.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    ax.plot(dca["threshold"], dca["net_benefit_model"], label="Strict t0 model")
    ax.plot(dca["threshold"], dca["net_benefit_treat_all"], linestyle="--", label="Treat all")
    ax.axhline(0.0, linewidth=1.0, label="Treat none")
    ax.set(xlabel="Risk threshold", ylabel="Net benefit")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(outdir / "v04_temporal_decision_curve.png", dpi=220)
    plt.close(fig)
    return dca


def fit_scaled_gmm(
    features: pd.DataFrame,
    columns: list[str],
    k: int,
    covariance_type: str = "full",
    seed: int = RANDOM_STATE,
) -> np.ndarray:
    x = StandardScaler().fit_transform(features[columns].to_numpy(dtype=float))
    model = GaussianMixture(
        n_components=k,
        covariance_type=covariance_type,
        random_state=seed,
        n_init=20,
    )
    return model.fit_predict(x)


def leave_last_trajectory_features(longitudinal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for participant_id, grp in longitudinal.groupby("participant_id"):
        g = grp.sort_values("measurement_month")
        if len(g) < 4 or g["measurement_month"].nunique() < 4:
            continue
        reduced = g.iloc[:-1]
        x = reduced["measurement_month"].to_numpy(dtype=float)
        y = reduced["score"].to_numpy(dtype=float)
        slope, _ = np.polyfit(x, y, 1)
        rows.append({
            "participant_id": str(participant_id),
            "n_measurements_full": int(len(g)),
            "baseline_score": float(y[0]),
            "slope_per_month": float(slope),
        })
    return pd.DataFrame(rows)


def trajectory_sensitivity(
    longitudinal: pd.DataFrame,
    outdir: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    primary_path = outdir / "v03_trajectory_participant_classes.csv"
    summary_path = outdir / "v03_trajectory_summary.json"
    if not primary_path.exists() or not summary_path.exists():
        raise FileNotFoundError("Run v0.3 trajectory analysis before v0.4 sensitivity analysis")
    primary = pd.read_csv(primary_path, dtype={"participant_id": str})
    v03_summary = json.loads(summary_path.read_text())
    k = int(v03_summary["selected_k"])
    features = participant_trajectory_features(longitudinal)
    merged = primary[["participant_id", "trajectory_class"]].merge(features, on="participant_id", how="inner")
    primary_labels = merged["trajectory_class"].to_numpy()

    scenarios: list[dict[str, object]] = []

    residual_labels = fit_scaled_gmm(
        merged, ["baseline_score", "slope_per_month", "residual_sd"], k=k, covariance_type="full", seed=101
    )
    scenarios.append({
        "scenario": "add_residual_sd",
        "n_participants": int(len(merged)),
        "k": k,
        "ari_vs_v03_primary": float(adjusted_rand_score(primary_labels, residual_labels)),
        "minimum_class_fraction": float(np.bincount(residual_labels, minlength=k).min() / len(residual_labels)),
        "purpose": "Tests sensitivity to within-person trajectory noise in addition to baseline and slope.",
    })

    diag_labels = fit_scaled_gmm(
        merged, ["baseline_score", "slope_per_month"], k=k, covariance_type="diag", seed=102
    )
    scenarios.append({
        "scenario": "diagonal_covariance",
        "n_participants": int(len(merged)),
        "k": k,
        "ari_vs_v03_primary": float(adjusted_rand_score(primary_labels, diag_labels)),
        "minimum_class_fraction": float(np.bincount(diag_labels, minlength=k).min() / len(diag_labels)),
        "purpose": "Tests dependence of classes on the GMM covariance specification.",
    })

    leave_last = leave_last_trajectory_features(longitudinal)
    ll = primary[["participant_id", "trajectory_class"]].merge(leave_last, on="participant_id", how="inner")
    if len(ll) >= max(100, 20 * k):
        ll_labels = fit_scaled_gmm(
            ll, ["baseline_score", "slope_per_month"], k=k, covariance_type="full", seed=103
        )
        scenarios.append({
            "scenario": "leave_last_measurement_out",
            "n_participants": int(len(ll)),
            "k": k,
            "ari_vs_v03_primary": float(adjusted_rand_score(ll["trajectory_class"].to_numpy(), ll_labels)),
            "minimum_class_fraction": float(np.bincount(ll_labels, minlength=k).min() / len(ll_labels)),
            "purpose": "Tests whether class assignment is overly dependent on the final PHQ-9 measurement.",
        })

    result = pd.DataFrame(scenarios)
    result.to_csv(outdir / "v04_trajectory_sensitivity.csv", index=False)
    summary = {
        "selected_k_from_v03": k,
        "n_primary_participants": int(len(merged)),
        "n_sensitivity_scenarios": int(len(result)),
        "minimum_ari_across_scenarios": float(result["ari_vs_v03_primary"].min()),
        "mean_ari_across_scenarios": float(result["ari_vs_v03_primary"].mean()),
        "interpretation": (
            "ARI values quantify agreement with the v0.3 exploratory phenotype solution under alternative feature, "
            "covariance and leave-last-out specifications. They do not validate clinical subtypes."
        ),
    }
    (outdir / "v04_trajectory_sensitivity_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return result, summary


def target_trial_readiness(feature_dictionary: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    candidates = [
        "med_start", "med_stop", "med_dose", "nonmed_start", "nonmed_stop",
        "life_meditation", "life_activity_eating", "meds_migraine",
    ]
    fd = feature_dictionary.rename(columns={
        "Feature name": "feature_name",
        "Category": "category",
        "Subcategory": "subcategory",
        "Description": "description",
        "Notes": "notes",
    }).copy()
    rows = []
    for feature in candidates:
        match = fd[fd["feature_name"].astype(str) == feature]
        if match.empty:
            rows.append({
                "feature_name": feature,
                "subcategory": "missing",
                "description": "",
                "t0_eligible_exposure": False,
                "reason": "Candidate not found in released feature dictionary.",
            })
            continue
        r = match.iloc[0]
        subcategory = str(r.get("subcategory", ""))
        description = str(r.get("description", ""))
        text = f"{subcategory} {description}".lower()
        is_dynamic = "dynamic" in text or "past month" in text
        is_static_baseline = "static" in text and "baseline" in text
        if is_dynamic:
            eligible = False
            reason = (
                "Dynamic/past-month feature: the release does not establish that this value is measured at the start "
                "of the three-month outcome interval, so treatment assignment can occur after time zero."
            )
        elif is_static_baseline:
            eligible = False
            reason = (
                "Measured at baseline, but this variable is a baseline state/covariate rather than the treatment strategy "
                "of interest for a medication-initiation target trial."
            )
        else:
            eligible = False
            reason = "Timing or intervention meaning is not sufficient to define treatment assignment at time zero."
        rows.append({
            "feature_name": feature,
            "subcategory": subcategory,
            "description": description,
            "t0_eligible_exposure": eligible,
            "reason": reason,
        })
    audit = pd.DataFrame(rows)
    specification = {
        "causal_question": "Effect of starting a new medication at the beginning of a three-month interval on PHQ-9 reliable deterioration over the following three months.",
        "eligibility": "Participant has an observed interval-start PHQ-9 score and is otherwise eligible for the PSYCHE-D analytical interval.",
        "treatment_strategies": ["start a new medication at time zero", "do not start a new medication at time zero"],
        "assignment": "Observational; would require adjustment for measured pre-treatment confounders.",
        "time_zero": "Beginning of the three-month PHQ-9 prediction interval.",
        "follow_up": "Three months.",
        "outcome": "PHQ-9 increase of at least 6 points by interval end.",
        "causal_contrast": "Intention-to-treat-like contrast between treatment strategies, if treatment assignment were observed at time zero.",
        "minimum_identification_assumptions": ["consistency", "conditional exchangeability", "positivity", "well-defined time zero", "non-informative outcome observation conditional on adjustment"],
        "estimation_status": "withheld",
        "reason_estimation_withheld": (
            "The released med_start feature is described as 'Started a new medication, past month' and is Dynamic. "
            "Its timestamp is not established as preceding the three-month outcome interval. Estimating a treatment effect "
            "would therefore risk immortal-time/reverse-timing bias and does not meet the prespecified time-zero gate."
        ),
        "required_next_data": (
            "Patient-level treatment start timestamp, PHQ-9 measurement timestamp, pre-treatment covariates, treatment indication, "
            "follow-up/censoring information and a prespecified handling rule for treatment changes after time zero."
        ),
    }
    return audit, specification


def save_target_trial_readiness(feature_dictionary_path: Path, outdir: Path) -> dict[str, object]:
    fd = pd.read_csv(feature_dictionary_path, sep="\t")
    audit, spec = target_trial_readiness(fd)
    audit.to_csv(outdir / "v04_target_trial_exposure_timing_audit.csv", index=False)
    (outdir / "v04_target_trial_specification.json").write_text(json.dumps(spec, indent=2) + "\n")
    return spec


def main(data_path: Path, feature_dictionary_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = parse_index(pd.read_parquet(data_path))
    intervals, strict_features, _ = prospective_dataset(df)

    predictions, temporal = fit_temporal_validation(intervals, strict_features, outdir)
    bootstrap = save_bootstrap_uncertainty(predictions, outdir)
    dca = save_decision_curve(predictions, outdir)

    longitudinal, conflicts = build_unique_longitudinal_scores(intervals)
    if len(conflicts):
        raise AssertionError(f"Conflicting PHQ-9 scores at shared interval boundaries: {len(conflicts)}")
    _, trajectory = trajectory_sensitivity(longitudinal, outdir)
    target_trial = save_target_trial_readiness(feature_dictionary_path, outdir)

    def ci(metric: str) -> dict[str, float]:
        r = bootstrap.loc[bootstrap["metric"] == metric].iloc[0]
        return {
            "point": float(r["point_estimate"]),
            "ci95_low": float(r["ci95_low"]),
            "ci95_high": float(r["ci95_high"]),
        }

    dca_superior = dca[
        (dca["net_benefit_model"] > dca["net_benefit_treat_all"])
        & (dca["net_benefit_model"] > dca["net_benefit_treat_none"])
    ]
    summary = {
        "version": "0.4",
        "temporal_validation": temporal,
        "cluster_bootstrap_300": {
            "roc_auc": ci("roc_auc"),
            "average_precision": ci("average_precision"),
            "brier": ci("brier"),
            "calibration_intercept": ci("calibration_intercept"),
            "calibration_slope": ci("calibration_slope"),
        },
        "decision_curve": {
            "thresholds_evaluated": int(len(dca)),
            "threshold_min": float(dca["threshold"].min()),
            "threshold_max": float(dca["threshold"].max()),
            "n_thresholds_model_better_than_treat_all_and_none": int(len(dca_superior)),
            "interpretation": "Decision-curve net benefit is a threshold analysis, not a recommendation for a clinical intervention threshold.",
        },
        "trajectory_sensitivity": trajectory,
        "target_trial": {
            "estimation_status": target_trial["estimation_status"],
            "reason_estimation_withheld": target_trial["reason_estimation_withheld"],
        },
        "boundaries": [
            "Temporal validation is forward in study time and participant-disjoint, but remains internal validation within one observational study.",
            "Cluster-bootstrap intervals quantify sampling uncertainty in this held-out set; they do not measure transportability to Clinical Partners patients.",
            "Decision-curve analysis does not define a clinical threshold without an explicit intervention and harm/benefit model.",
            "Trajectory sensitivity measures algorithmic stability, not clinical subtype validity.",
            "The medication causal effect is intentionally not estimated because treatment timing does not satisfy the target-trial time-zero gate.",
        ],
    }
    (outdir / "v04_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    report = f"""# v0.4 validation, uncertainty and causal-readiness report

## Forward-time participant-disjoint validation

The strict t0 model is trained on interval endpoints at months {EARLY_ENDPOINT_MONTHS} (prediction times 0 and 3 months) and evaluated on held-out participants at interval endpoints {LATE_ENDPOINT_MONTHS} (prediction times 6 and 9 months).

- Train rows: {temporal['train_rows']:,}
- Test rows: {temporal['test_rows']:,}
- Train participants: {temporal['train_participants']:,}
- Test participants: {temporal['test_participants']:,}
- Participant overlap: {temporal['participant_overlap']}
- ROC-AUC: {temporal['roc_auc']:.3f}
- Average precision: {temporal['average_precision']:.3f}
- Brier score: {temporal['brier']:.3f}
- Calibration intercept: {temporal['calibration_intercept']:.3f}
- Calibration slope: {temporal['calibration_slope']:.3f}

This is harder than a random participant split because it shifts both participant identity and study time. It is still internal validation within PSYCHE-D, not external validation in a clinical service.

## Cluster-bootstrap uncertainty

Three hundred bootstrap samples resample held-out participants rather than individual interval rows. The output reports 95% percentile intervals for ROC-AUC, average precision, Brier score, calibration intercept and calibration slope.

## Decision curve

The held-out temporal predictions are evaluated over risk thresholds 0.02 to 0.20. Net benefit is compared with treat-all and treat-none reference strategies. The result is an evaluation of whether the model could add decision value under hypothetical thresholds; it does not select a clinical threshold.

## Trajectory sensitivity

- v0.3 selected classes: {trajectory['selected_k_from_v03']}
- Sensitivity scenarios: {trajectory['n_sensitivity_scenarios']}
- Mean ARI versus v0.3 primary solution: {trajectory['mean_ari_across_scenarios']:.3f}
- Minimum ARI: {trajectory['minimum_ari_across_scenarios']:.3f}

The sensitivity analysis changes the feature set, covariance structure and, where enough repeated measurements exist, removes the final measurement before re-estimating slope.

## Target-trial readiness gate

A target-trial specification is written for medication initiation at interval start, but the treatment effect is not estimated. The released `med_start` variable is Dynamic and means “Started a new medication, past month”; the release does not establish that it is measured before the three-month outcome interval. A causal estimate would therefore violate the prespecified time-zero requirement.
"""
    (outdir / "V04_VALIDATION_CAUSAL_REPORT.md").write_text(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--feature-dictionary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.feature_dictionary, args.out)

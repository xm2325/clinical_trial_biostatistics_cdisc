import numpy as np
import pandas as pd

from v04_validation_causal import (
    cluster_bootstrap_metrics,
    decision_curve,
    target_trial_readiness,
    temporal_participant_disjoint_split,
)


def test_temporal_split_is_forward_and_participant_disjoint():
    rows = []
    for participant in range(80):
        for month in (3, 6, 9, 12):
            rows.append({
                "participant_id": str(participant),
                "study_month": month,
                "reliable_deterioration": int((participant + month) % 7 == 0),
            })
    df = pd.DataFrame(rows)
    train, test = temporal_participant_disjoint_split(df)
    assert set(train["study_month"]) <= {3, 6}
    assert set(test["study_month"]) <= {9, 12}
    assert set(train["participant_id"]).isdisjoint(set(test["participant_id"]))
    assert train["reliable_deterioration"].nunique() == 2
    assert test["reliable_deterioration"].nunique() == 2


def test_cluster_bootstrap_returns_interval_for_core_metrics():
    rows = []
    rng = np.random.default_rng(11)
    for participant in range(60):
        for month in (9, 12):
            y = int((participant + month) % 6 == 0)
            p = np.clip(0.04 + 0.35 * y + rng.normal(0, 0.04), 0.001, 0.999)
            rows.append({
                "participant_id": str(participant),
                "study_month": month,
                "outcome": y,
                "probability": p,
            })
    predictions = pd.DataFrame(rows)
    reps, summary = cluster_bootstrap_metrics(predictions, n_boot=40, seed=3)
    assert len(reps) == 40
    assert set(summary["metric"]) == {
        "roc_auc", "average_precision", "brier", "calibration_intercept", "calibration_slope"
    }
    assert (summary["ci95_high"] >= summary["ci95_low"]).all()


def test_decision_curve_has_treat_none_zero_and_valid_flag_fraction():
    predictions = pd.DataFrame({
        "participant_id": ["a", "b", "c", "d"],
        "outcome": [0, 0, 1, 1],
        "probability": [0.03, 0.08, 0.12, 0.30],
    })
    out = decision_curve(predictions, thresholds=np.array([0.05, 0.10, 0.20]))
    assert np.allclose(out["net_benefit_treat_none"], 0.0)
    assert out["flagged_fraction"].between(0, 1).all()


def test_target_trial_gate_rejects_dynamic_past_month_exposure():
    feature_dictionary = pd.DataFrame({
        "Feature name": ["med_start", "meds_migraine"],
        "Category": ["Demographic", "Demographic"],
        "Subcategory": ["Dynamic", "Static"],
        "Description": [
            "Started a new medication, past month",
            "Takes daily prescription migraine medication, at baseline",
        ],
        "Notes": [np.nan, "boolean"],
    })
    audit, spec = target_trial_readiness(feature_dictionary)
    med = audit.loc[audit["feature_name"] == "med_start"].iloc[0]
    baseline = audit.loc[audit["feature_name"] == "meds_migraine"].iloc[0]
    assert not bool(med["t0_eligible_exposure"])
    assert "time zero" in med["reason"]
    assert not bool(baseline["t0_eligible_exposure"])
    assert spec["estimation_status"] == "withheld"

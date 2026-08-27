import numpy as np
import pandas as pd

from analysis import SAFE_CANDIDATES, binary_metrics, parse_index, split_by_participant


def test_parse_index_recovers_participant_and_month():
    df = pd.DataFrame({"x": [1, 2, 3]}, index=["34_12", "34_3", "7_1"])
    out = parse_index(df)
    assert out["participant_id"].tolist() == ["34", "34", "7"]
    assert out["study_month"].tolist() == [12, 3, 1]


def test_group_split_has_zero_participant_overlap():
    rows = []
    for participant in range(40):
        for month in (3, 6, 9):
            rows.append({"participant_id": str(participant), "study_month": month})
    df = pd.DataFrame(rows)
    train_idx, test_idx = split_by_participant(df)
    train_users = set(df.iloc[train_idx]["participant_id"])
    test_users = set(df.iloc[test_idx]["participant_id"])
    assert train_users.isdisjoint(test_users)
    assert train_users
    assert test_users


def test_binary_metrics_are_finite_for_two_class_input():
    y = np.array([0, 0, 1, 1, 0, 1])
    p = np.array([0.1, 0.3, 0.8, 0.7, 0.2, 0.9])
    metrics = binary_metrics(y, p)
    for key in ["roc_auc", "average_precision", "brier", "calibration_intercept", "calibration_slope"]:
        assert np.isfinite(metrics[key])


def test_safe_candidates_do_not_include_phq9_endpoint_or_generated_probability():
    lowered = [name.lower() for name in SAFE_CANDIDATES]
    assert not any("phq9_cat_end" in name for name in lowered)
    assert not any(name.startswith("proba_cat") for name in lowered)

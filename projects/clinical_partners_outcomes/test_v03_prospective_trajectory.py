import numpy as np
import pandas as pd

from v03_prospective_trajectory import participant_trajectory_features, prospective_dataset


def test_prospective_dataset_uses_interval_start_and_baseline_only_for_strict_model():
    idx = ["u1_3", "u1_6", "u2_3", "u2_6"]
    df = pd.DataFrame({
        "phq9_score_start": [10, 12, 8, 9],
        "phq9_score_end": [12, 19, 9, 15],
        "phq9_cat_start": [2, 2, 1, 1],
        "phq9_cat_end": [2, 3, 1, 3],
        "birthyear": [1980, 1980, 1990, 1990],
        "sex": [1, 1, 0, 0],
        "med_start": [0, 1, 0, 1],
        "sleep_asleep_mean_recent": [400, 300, 420, 280],
    }, index=idx)
    from analysis import parse_index
    parsed = parse_index(df)
    intervals, strict, broad = prospective_dataset(parsed)
    assert "phq9_score_start" in strict
    assert "birthyear" in strict
    assert "sex" in strict
    assert "med_start" not in strict
    assert "sleep_asleep_mean_recent" not in strict
    assert "med_start" in broad
    assert intervals.loc[intervals["study_month"] == 6, "reliable_deterioration"].sum() == 2


def test_participant_trajectory_features_requires_three_measurements():
    longitudinal = pd.DataFrame({
        "participant_id": ["a", "a", "a", "b", "b"],
        "measurement_month": [0, 3, 6, 0, 3],
        "score": [12.0, 9.0, 6.0, 8.0, 9.0],
    })
    f = participant_trajectory_features(longitudinal)
    assert f["participant_id"].tolist() == ["a"]
    assert np.isclose(f.iloc[0]["slope_per_month"], -1.0)
    assert np.isclose(f.iloc[0]["baseline_score"], 12.0)

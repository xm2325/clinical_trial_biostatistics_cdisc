import pandas as pd

from v02_score_longitudinal import (
    PHQ_RELIABLE_CHANGE_POINTS,
    availability_grid,
    build_unique_longitudinal_scores,
    interval_scores,
)


def test_phq_reliable_change_classification():
    df = pd.DataFrame({
        "phq9_score_start": [15, 15, 8],
        "phq9_score_end": [8, 22, 7],
        "participant_id": ["a", "b", "c"],
        "study_month": [3, 3, 3],
    })
    out = interval_scores(df)
    assert PHQ_RELIABLE_CHANGE_POINTS == 6.0
    assert out["reliable_improvement_phq9"].tolist() == [True, False, False]
    assert out["reliable_deterioration_phq9"].tolist() == [False, True, False]
    assert out["crossed_below_phq9_case_cutoff"].tolist() == [True, False, False]


def test_longitudinal_reconstruction_deduplicates_shared_quarter_boundary():
    interval = pd.DataFrame({
        "participant_id": ["a", "a"],
        "study_month": [3, 6],
        "phq9_score_start": [15.0, 10.0],
        "phq9_score_end": [10.0, 7.0],
    })
    longitudinal, conflicts = build_unique_longitudinal_scores(interval)
    assert conflicts.empty
    assert longitudinal["measurement_month"].tolist() == [0, 3, 6]
    assert longitudinal["score"].tolist() == [15.0, 10.0, 7.0]


def test_availability_grid_treats_absent_quarter_row_as_unavailable():
    rows = []
    for participant in ["a", "b"]:
        for month in [1, 2, 3, 4, 5, 6]:
            if participant == "b" and month == 6:
                continue
            rows.append({
                "participant_id": participant,
                "study_month": month,
                "phq9_score_end": 12.0 if month in [3, 6] else None,
                "sex": 0,
            })
    df = pd.DataFrame(rows)
    grid = availability_grid(df)
    b6 = grid[(grid["participant_id"] == "b") & (grid["scheduled_month"] == 6)]
    assert int(b6["phq_endpoint_available"].iloc[0]) == 0
    a6 = grid[(grid["participant_id"] == "a") & (grid["scheduled_month"] == 6)]
    assert int(a6["phq_endpoint_available"].iloc[0]) == 1

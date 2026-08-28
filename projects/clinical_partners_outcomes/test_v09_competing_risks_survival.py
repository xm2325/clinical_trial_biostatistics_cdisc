from __future__ import annotations

import numpy as np
import pandas as pd

from v09_competing_risks_survival import (
    build_first_change_person_period,
    cumulative_incidence,
    fit_cause_specific_cloglog,
    participant_bootstrap_cif,
)


def test_first_change_stops_at_event_and_first_missing_visit():
    measurements = pd.DataFrame(
        [
            # p1 improves first at month 6; month 9 must never enter risk set.
            ("p1", 0, 15), ("p1", 3, 13), ("p1", 6, 8), ("p1", 9, 20),
            # p2 is censored at month 3 missing; month 6 is deliberately ignored.
            ("p2", 0, 10), ("p2", 6, 18),
            # p3 deteriorates at month 3.
            ("p3", 0, 7), ("p3", 3, 14),
            # p4 stays event-free through month 12.
            ("p4", 0, 12), ("p4", 3, 11), ("p4", 6, 10), ("p4", 9, 11), ("p4", 12, 12),
        ],
        columns=["participant_id", "measurement_month", "score"],
    )
    person_period, participant = build_first_change_person_period(measurements)

    p1 = participant.set_index("participant_id").loc["p1"]
    assert p1["event_type"] == "improvement"
    assert p1["event_month"] == 6
    assert set(person_period.loc[person_period["participant_id"].eq("p1"), "interval_end_month"]) == {3, 6}

    p2 = participant.set_index("participant_id").loc["p2"]
    assert p2["censor_reason"] == "first_missing_scheduled_measurement"
    assert p2["censor_month"] == 0
    assert not person_period["participant_id"].eq("p2").any()

    p3 = participant.set_index("participant_id").loc["p3"]
    assert p3["event_type"] == "deterioration"
    assert p3["event_month"] == 3


def test_cumulative_incidence_competing_events_sum_with_survival():
    measurements = pd.DataFrame(
        [
            ("a", 0, 12), ("a", 3, 5),
            ("b", 0, 8), ("b", 3, 15),
            ("c", 0, 10), ("c", 3, 10), ("c", 6, 10), ("c", 9, 10), ("c", 12, 10),
            ("d", 0, 11), ("d", 3, 11), ("d", 6, 4),
        ],
        columns=["participant_id", "measurement_month", "score"],
    )
    person_period, participant = build_first_change_person_period(measurements)
    cif = cumulative_incidence(person_period)
    total = cif["survival_no_reliable_change"] + cif["cif_improvement"] + cif["cif_deterioration"]
    assert np.allclose(total, 1.0, atol=1e-12)
    assert cif["cif_improvement"].is_monotonic_increasing
    assert cif["cif_deterioration"].is_monotonic_increasing

    boot = participant_bootstrap_cif(person_period, pd.concat([participant] * 30, ignore_index=True).assign(
        participant_id=lambda x: [f"{pid}_{i}" for i, pid in enumerate(x["participant_id"])]
    ), replicates=5, seed=3)
    # The synthetic bootstrap call above has no matching person-period ids and is
    # intentionally only a shape smoke test for zero-weight risk sets.
    assert len(boot) == 12


def synthetic_person_period(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for participant in range(500):
        baseline_z = rng.normal()
        for month in (3, 6, 9, 12):
            p_improve = float(np.clip(0.07 + 0.02 * baseline_z + 0.005 * month, 0.01, 0.35))
            p_deteriorate = float(np.clip(0.06 - 0.015 * baseline_z + 0.002 * month, 0.01, 0.30))
            draw = rng.random()
            improve = draw < p_improve
            deteriorate = (not improve) and draw < p_improve + p_deteriorate
            rows.append(
                {
                    "participant_id": participant,
                    "interval_end_month": month,
                    "baseline_phq9": 12 + 4 * baseline_z,
                    "baseline_phq9_z": baseline_z,
                    "current_phq9": np.nan,
                    "change_from_baseline": np.nan,
                    "event_improvement": int(improve),
                    "event_deterioration": int(deteriorate),
                    "event_any": int(improve or deteriorate),
                }
            )
            if improve or deteriorate:
                break
    return pd.DataFrame(rows)


def test_cause_specific_cloglog_models_converge():
    person_period = synthetic_person_period()
    for outcome in ("event_improvement", "event_deterioration"):
        result = fit_cause_specific_cloglog(person_period, outcome)
        assert result["converged"]
        assert result["events"] >= 20
        assert result["baseline_phq9_z_hazard_ratio"] > 0
        assert 0 <= result["time_interaction_p"] <= 1

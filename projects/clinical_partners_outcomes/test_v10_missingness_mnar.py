from __future__ import annotations

import numpy as np
import pandas as pd

from v09_competing_risks_survival import build_first_change_person_period
from v10_missingness_mnar import (
    SCORE_COLUMNS,
    apply_delta,
    build_observation_risk_rows,
    fit_ipcw_observation_model,
    generate_mar_imputations,
    pooled_mi_sensitivity,
    rubin_pool,
    time_varying_weighted_cif,
)


def synthetic_wide(n: int = 120, seed: int = 20260828) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    baseline = np.clip(rng.normal(12, 4, size=n), 0, 27)
    data = {"phq0": baseline}
    previous = baseline.copy()
    for month in (3, 6, 9, 12):
        score = np.clip(previous + rng.normal(-0.4, 3.0, size=n), 0, 27)
        # Missingness depends on severity/history so IPCW has a real signal.
        probability_observed = 1 / (1 + np.exp(-(
            1.8 - 0.08 * baseline - 0.03 * previous - 0.18 * (month / 3 - 1)
        )))
        observed = rng.random(n) < probability_observed
        # Keep month 3 reasonably well observed so every synthetic participant
        # does not immediately disappear from the risk set.
        if month == 3:
            observed |= rng.random(n) < 0.45
        score[~observed] = np.nan
        data[f"phq{month}"] = score
        previous = np.where(observed, score, previous)
    wide = pd.DataFrame(data, index=[f"p{i:03d}" for i in range(n)])
    wide.index.name = "participant_id"
    return wide


def synthetic_design(wide: pd.DataFrame) -> pd.DataFrame:
    design = wide.copy()
    index_number = np.arange(len(wide))
    design["sex_F"] = (index_number % 2 == 0).astype(float)
    design["sex_M"] = (index_number % 2 == 1).astype(float)
    return design


def wide_observed_measurements(wide: pd.DataFrame) -> pd.DataFrame:
    long = (
        wide.reset_index()
        .melt(
            id_vars="participant_id",
            value_vars=SCORE_COLUMNS,
            var_name="score_month",
            value_name="score",
        )
        .dropna(subset=["score"])
    )
    long["measurement_month"] = (
        long["score_month"].str.replace("phq", "", regex=False).astype(int)
    )
    return long[["participant_id", "measurement_month", "score"]]


def test_rubin_pool_reduces_to_within_variance_when_estimates_identical():
    pooled = rubin_pool(
        np.array([0.20, 0.20, 0.20, 0.20]),
        np.array([0.0004, 0.0004, 0.0004, 0.0004]),
    )
    assert np.isclose(pooled["estimate"], 0.20)
    assert np.isclose(pooled["between_variance"], 0.0)
    assert np.isclose(pooled["se"], 0.02)
    assert np.isclose(pooled["fraction_missing_information"], 0.0)


def test_mar_imputation_preserves_observed_scores_and_fills_missing():
    wide = synthetic_wide(n=80)
    design = synthetic_design(wide)
    imputations = generate_mar_imputations(
        wide,
        design,
        n_imputations=3,
        seed=11,
    )
    assert len(imputations) == 3
    observed = wide.notna()
    for imputed in imputations:
        assert imputed.notna().all().all()
        assert imputed.apply(lambda s: s.between(0, 27).all()).all()
        for column in SCORE_COLUMNS:
            mask = observed[column]
            assert np.allclose(
                imputed.loc[mask, column],
                wide.loc[mask, column],
            )


def test_delta_changes_only_originally_missing_followup_and_clips():
    wide = synthetic_wide(n=40)
    base = wide.fillna(26.0)
    shifted = apply_delta(base, wide, delta=6.0)
    for column in SCORE_COLUMNS:
        if column == "phq0":
            assert np.allclose(shifted[column], base[column])
            continue
        observed = wide[column].notna()
        missing = ~observed
        assert np.allclose(
            shifted.loc[observed, column], base.loc[observed, column]
        )
        assert (shifted.loc[missing, column] >= base.loc[missing, column]).all()
        assert shifted.loc[missing, column].between(0, 27).all()


def test_mi_delta_sensitivity_has_expected_shape_and_direction():
    wide = synthetic_wide(n=90)
    imputations = generate_mar_imputations(
        wide,
        synthetic_design(wide),
        n_imputations=3,
        seed=31,
    )
    result = pooled_mi_sensitivity(
        wide,
        imputations,
        delta_grid=(0.0, 3.0),
    )
    assert len(result) == 2 * 4 * 3
    assert result["estimate"].notna().all()
    assert result["fraction_missing_information"].between(0, 1).all()
    deterioration = result[
        result["estimand"].eq("cif_deterioration")
        & result["month"].eq(12)
    ].set_index("delta_points_added_to_missing_phq9")["estimate"]
    # Making only missing follow-up scores worse should not reduce the estimated
    # first-deterioration cumulative incidence in this deterministic delta map.
    assert deterioration.loc[3.0] >= deterioration.loc[0.0]


def test_ipcw_weights_are_finite_and_weighted_cif_is_valid():
    wide = synthetic_wide(n=160, seed=9)
    risk_rows = build_observation_risk_rows(wide)
    weights, diagnostics = fit_ipcw_observation_model(risk_rows)
    assert len(weights) > 100
    assert weights["ipcw_weight"].notna().all()
    assert (weights["ipcw_weight"] > 0).all()
    assert np.isfinite(weights["ipcw_weight"]).all()
    assert 0 <= diagnostics["roc_auc"] <= 1
    assert 0 <= diagnostics["brier"] <= 1

    measurements = wide_observed_measurements(wide)
    person_period, _ = build_first_change_person_period(measurements)
    weighted = person_period.merge(
        weights,
        on=["participant_id", "interval_end_month"],
        how="left",
        validate="one_to_one",
    )
    assert weighted["ipcw_weight"].notna().all()
    cif = time_varying_weighted_cif(weighted)
    total = (
        cif["survival_no_reliable_change"]
        + cif["cif_improvement"]
        + cif["cif_deterioration"]
    )
    assert np.allclose(total, 1.0, atol=1e-10)
    assert cif["cif_improvement"].is_monotonic_increasing
    assert cif["cif_deterioration"].is_monotonic_increasing

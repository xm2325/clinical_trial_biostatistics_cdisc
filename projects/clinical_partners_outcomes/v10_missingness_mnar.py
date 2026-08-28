from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from analysis import parse_index
from v09_competing_risks_survival import (
    BASELINE_MONTH,
    FOLLOWUP_MONTHS,
    build_all_score_measurements,
    build_first_change_person_period,
    cumulative_incidence,
)

DELTA_GRID = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 6.0)
SCORE_MONTHS = (0, 3, 6, 9, 12)
SCORE_COLUMNS = [f"phq{month}" for month in SCORE_MONTHS]


def build_score_wide(measurements: pd.DataFrame) -> pd.DataFrame:
    wide = measurements.pivot(
        index="participant_id", columns="measurement_month", values="score"
    ).reindex(columns=SCORE_MONTHS)
    wide = wide[wide[BASELINE_MONTH].notna()].copy()
    wide.columns = SCORE_COLUMNS
    wide.index.name = "participant_id"
    return wide.sort_index()


def missingness_summary(wide: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, column in zip(SCORE_MONTHS, SCORE_COLUMNS):
        rows.append(
            {
                "month": month,
                "n": int(len(wide)),
                "observed": int(wide[column].notna().sum()),
                "missing": int(wide[column].isna().sum()),
                "missing_rate": float(wide[column].isna().mean()),
            }
        )
    return pd.DataFrame(rows)


def imputation_design_matrix(
    wide: pd.DataFrame,
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray]:
    matrix = wide.copy()
    first = (
        df.sort_values(["participant_id", "study_month"])
        .groupby("participant_id", as_index=False)
        .first()
        .set_index("participant_id")
        .reindex(wide.index)
    )
    categorical = [
        column for column in ("sex", "insurance", "trauma") if column in first.columns
    ]
    if categorical:
        dummy = pd.get_dummies(
            first[categorical].astype("string"),
            prefix=categorical,
            dummy_na=True,
            dtype=float,
        )
        matrix = pd.concat([matrix, dummy], axis=1)
    missing_followup = wide[[f"phq{m}" for m in FOLLOWUP_MONTHS]].isna().to_numpy()
    return matrix.astype(float), missing_followup


def generate_mar_imputations(
    wide: pd.DataFrame,
    design: pd.DataFrame,
    n_imputations: int = 20,
    seed: int = 20260828,
) -> list[pd.DataFrame]:
    original_scores = wide.to_numpy(dtype=float)
    observed = np.isfinite(original_scores)
    imputations: list[pd.DataFrame] = []
    for index in range(n_imputations):
        imputer = IterativeImputer(
            estimator=BayesianRidge(),
            sample_posterior=True,
            max_iter=20,
            initial_strategy="median",
            skip_complete=True,
            min_value=0.0,
            max_value=27.0,
            random_state=seed + index,
        )
        transformed = imputer.fit_transform(design)
        scores = transformed[:, : len(SCORE_COLUMNS)].copy()
        scores[observed] = original_scores[observed]
        scores = np.clip(scores, 0.0, 27.0)
        frame = pd.DataFrame(scores, index=wide.index, columns=SCORE_COLUMNS)
        imputations.append(frame)
    return imputations


def apply_delta(
    imputed: pd.DataFrame,
    original_wide: pd.DataFrame,
    delta: float,
) -> pd.DataFrame:
    result = imputed.copy()
    for month in FOLLOWUP_MONTHS:
        column = f"phq{month}"
        missing = original_wide[column].isna()
        result.loc[missing, column] = np.clip(
            result.loc[missing, column].to_numpy(dtype=float) + delta,
            0.0,
            27.0,
        )
    return result


def wide_to_measurements(wide: pd.DataFrame) -> pd.DataFrame:
    long = (
        wide.reset_index()
        .melt(
            id_vars="participant_id",
            value_vars=SCORE_COLUMNS,
            var_name="score_month",
            value_name="score",
        )
    )
    long["measurement_month"] = long["score_month"].str.replace("phq", "", regex=False).astype(int)
    return long[["participant_id", "measurement_month", "score"]].sort_values(
        ["participant_id", "measurement_month"]
    )


def complete_event_summary(wide: pd.DataFrame) -> pd.DataFrame:
    measurements = wide_to_measurements(wide)
    _, participant = build_first_change_person_period(measurements)
    if participant["censor_reason"].eq("first_missing_scheduled_measurement").any():
        raise AssertionError("Imputed complete panel unexpectedly contains missing-visit censoring")
    return participant


def rubin_pool(q: np.ndarray, u: np.ndarray) -> dict:
    q = np.asarray(q, dtype=float)
    u = np.asarray(u, dtype=float)
    m = len(q)
    q_bar = float(q.mean())
    u_bar = float(u.mean())
    between = float(np.var(q, ddof=1)) if m > 1 else 0.0
    extra = (1.0 + 1.0 / m) * between
    total = u_bar + extra
    se = float(np.sqrt(max(total, 0.0)))
    if between <= 1e-16 or extra <= 1e-16:
        df = float("inf")
        critical = 1.96
    else:
        df = float((m - 1) * (1.0 + u_bar / extra) ** 2)
        critical = float(student_t.ppf(0.975, df))
    fmi = float(extra / total) if total > 0 else 0.0
    return {
        "estimate": q_bar,
        "se": se,
        "ci95_low": float(q_bar - critical * se),
        "ci95_high": float(q_bar + critical * se),
        "within_variance": u_bar,
        "between_variance": between,
        "rubin_df": df,
        "fraction_missing_information": fmi,
    }


def pooled_mi_sensitivity(
    original_wide: pd.DataFrame,
    imputations: list[pd.DataFrame],
    delta_grid: tuple[float, ...] = DELTA_GRID,
) -> pd.DataFrame:
    rows: list[dict] = []
    n = len(original_wide)
    for delta in delta_grid:
        summaries = [
            complete_event_summary(apply_delta(imputed, original_wide, delta))
            for imputed in imputations
        ]
        for month in FOLLOWUP_MONTHS:
            values_by_estimand: dict[str, list[float]] = {
                "cif_improvement": [],
                "cif_deterioration": [],
                "cif_difference_improvement_minus_deterioration": [],
            }
            variances_by_estimand = {key: [] for key in values_by_estimand}
            for participant in summaries:
                improve = (
                    participant["event_type"].eq("improvement")
                    & participant["event_month"].fillna(999).le(month)
                ).astype(float).to_numpy()
                deteriorate = (
                    participant["event_type"].eq("deterioration")
                    & participant["event_month"].fillna(999).le(month)
                ).astype(float).to_numpy()
                difference = improve - deteriorate
                for name, vector in (
                    ("cif_improvement", improve),
                    ("cif_deterioration", deteriorate),
                    ("cif_difference_improvement_minus_deterioration", difference),
                ):
                    values_by_estimand[name].append(float(vector.mean()))
                    variances_by_estimand[name].append(float(np.var(vector, ddof=1) / n))
            for estimand in values_by_estimand:
                pooled = rubin_pool(
                    np.asarray(values_by_estimand[estimand]),
                    np.asarray(variances_by_estimand[estimand]),
                )
                rows.append(
                    {
                        "delta_points_added_to_missing_phq9": delta,
                        "month": month,
                        "estimand": estimand,
                        "n_imputations": len(imputations),
                        **pooled,
                    }
                )
    result = pd.DataFrame(rows)
    for column in ("ci95_low", "ci95_high"):
        probability_estimand = result["estimand"].isin(
            ["cif_improvement", "cif_deterioration"]
        )
        result.loc[probability_estimand, column] = result.loc[
            probability_estimand, column
        ].clip(0.0, 1.0)
    return result


def build_observation_risk_rows(wide: pd.DataFrame) -> pd.DataFrame:
    baseline_mean = float(wide["phq0"].mean())
    baseline_sd = float(wide["phq0"].std(ddof=0))
    rows: list[dict] = []
    for participant_id, row in wide.iterrows():
        baseline = float(row["phq0"])
        last_score = baseline
        for month in FOLLOWUP_MONTHS:
            score = row[f"phq{month}"]
            observed = bool(pd.notna(score))
            rows.append(
                {
                    "participant_id": participant_id,
                    "month": month,
                    "observed_next": int(observed),
                    "baseline_phq9_z": (baseline - baseline_mean) / baseline_sd,
                    "last_observed_phq9_z": (last_score - baseline_mean) / baseline_sd,
                    "last_change_from_baseline": last_score - baseline,
                }
            )
            if not observed:
                break
            score = float(score)
            change = score - baseline
            if abs(change) >= 6.0:
                break
            last_score = score
    return pd.DataFrame(rows)


def fit_ipcw_observation_model(
    risk_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    work = risk_rows.copy()
    month_variation = work.groupby("month")["observed_next"].nunique()
    variable_months = month_variation[month_variation > 1].index.tolist()
    if not variable_months:
        raise ValueError("No scheduled month has observation variation")
    train = work[work["month"].isin(variable_months)].copy()
    x = pd.get_dummies(
        train[["month"]], columns=["month"], prefix="month", dtype=float
    )
    x["baseline_phq9_z"] = train["baseline_phq9_z"].to_numpy(dtype=float)
    x["last_observed_phq9_z"] = train["last_observed_phq9_z"].to_numpy(dtype=float)
    x["last_change_from_baseline"] = train["last_change_from_baseline"].to_numpy(dtype=float)
    model = LogisticRegression(max_iter=3000, C=1.0)
    model.fit(x, train["observed_next"])
    probability = model.predict_proba(x)[:, 1]
    auc = float(roc_auc_score(train["observed_next"], probability))
    brier = float(brier_score_loss(train["observed_next"], probability))

    work["predicted_observation_probability"] = 1.0
    work.loc[train.index, "predicted_observation_probability"] = np.clip(
        probability, 0.05, 0.995
    )
    month_numerator = work.groupby("month")["observed_next"].mean().to_dict()
    work["stabilising_numerator"] = work["month"].map(month_numerator).astype(float)

    weight_rows = []
    for participant_id, frame in work.groupby("participant_id", sort=False):
        cumulative = 1.0
        for row in frame.sort_values("month").itertuples(index=False):
            cumulative *= row.stabilising_numerator / row.predicted_observation_probability
            if row.observed_next:
                weight_rows.append(
                    {
                        "participant_id": participant_id,
                        "interval_end_month": int(row.month),
                        "ipcw_weight_raw": float(cumulative),
                    }
                )
            else:
                break
    weights = pd.DataFrame(weight_rows)
    q01, q99 = np.quantile(weights["ipcw_weight_raw"], [0.01, 0.99])
    lower = max(0.1, float(q01))
    upper = min(10.0, float(q99))
    if upper < lower:
        upper = lower
    weights["ipcw_weight"] = weights["ipcw_weight_raw"].clip(lower, upper)
    clipped = ~np.isclose(weights["ipcw_weight"], weights["ipcw_weight_raw"])
    diagnostics = {
        "variable_observation_months": [int(x) for x in variable_months],
        "n_observation_risk_rows": int(len(work)),
        "n_model_rows": int(len(train)),
        "observation_rate_model_rows": float(train["observed_next"].mean()),
        "roc_auc": auc,
        "brier": brier,
        "predicted_probability_min_after_floor": float(
            work["predicted_observation_probability"].min()
        ),
        "predicted_probability_max": float(
            work["predicted_observation_probability"].max()
        ),
        "raw_weight_q01": float(q01),
        "raw_weight_q50": float(weights["ipcw_weight_raw"].median()),
        "raw_weight_q99": float(q99),
        "raw_weight_max": float(weights["ipcw_weight_raw"].max()),
        "truncation_lower": lower,
        "truncation_upper": upper,
        "fraction_weights_truncated": float(clipped.mean()),
        "boundary": (
            "IPCW models remaining observed at the next scheduled PHQ-9 visit among the current event-free risk set. "
            "It cannot distinguish questionnaire non-response from attrition or source preprocessing."
        ),
    }
    return weights, diagnostics


def time_varying_weighted_cif(person_period: pd.DataFrame) -> pd.DataFrame:
    survival = 1.0
    cif_improvement = 0.0
    cif_deterioration = 0.0
    rows = []
    for month in FOLLOWUP_MONTHS:
        frame = person_period[person_period["interval_end_month"].eq(month)]
        weight = frame["ipcw_weight"].to_numpy(dtype=float)
        n_risk = float(weight.sum())
        if n_risk <= 0:
            continue
        d_improve = float(
            np.sum(weight * frame["event_improvement"].to_numpy(dtype=float))
        )
        d_deteriorate = float(
            np.sum(weight * frame["event_deterioration"].to_numpy(dtype=float))
        )
        cif_improvement += survival * d_improve / n_risk
        cif_deterioration += survival * d_deteriorate / n_risk
        survival *= 1.0 - (d_improve + d_deteriorate) / n_risk
        rows.append(
            {
                "month": month,
                "weighted_risk_sum": n_risk,
                "weighted_improvement_events": d_improve,
                "weighted_deterioration_events": d_deteriorate,
                "survival_no_reliable_change": survival,
                "cif_improvement": cif_improvement,
                "cif_deterioration": cif_deterioration,
            }
        )
    return pd.DataFrame(rows)


def write_report(
    outdir: Path,
    summary: dict,
    missing: pd.DataFrame,
    primary_cif: pd.DataFrame,
    ipcw_cif: pd.DataFrame,
    mi: pd.DataFrame,
) -> None:
    mar12 = mi[
        mi["delta_points_added_to_missing_phq9"].eq(0)
        & mi["month"].eq(12)
        & mi["estimand"].isin(["cif_improvement", "cif_deterioration"])
    ]
    delta12 = mi[
        mi["month"].eq(12)
        & mi["estimand"].eq("cif_difference_improvement_minus_deterioration")
    ]
    report = f"""# v0.10 Missing follow-up: IPCW, MAR multiple imputation and MNAR delta sensitivity

## Why this analysis exists

v0.9 estimated time to first observed reliable PHQ-9 improvement or deterioration while censoring at the first missing scheduled assessment. In that analysis **{summary['v09_first_missing_visit_censor_n']:,}** participants were censored at a first missing follow-up. v0.10 asks how strongly the competing-risk conclusions depend on that censoring assumption.

## Observed score availability in the v0.9 baseline cohort

{missing.to_markdown(index=False, floatfmt='.4f')}

Absence in PSYCHE-D is not identified as questionnaire non-response: it can also reflect attrition or release preprocessing. The analyses below therefore describe assumption-based sensitivity, not recovery of known unobserved outcomes.

## IPCW censoring sensitivity

A pooled logistic model predicts remaining observed at the next scheduled visit among the current event-free risk set using scheduled month, baseline PHQ-9, last observed PHQ-9 and change from baseline. Stabilised cumulative weights are truncated at empirical 1st/99th percentiles with a hard 0.1-10 range.

Observation-model ROC-AUC: **{summary['ipcw']['roc_auc']:.3f}**; Brier score: **{summary['ipcw']['brier']:.3f}**. Raw IPCW 99th percentile: **{summary['ipcw']['raw_weight_q99']:.3f}**; maximum: **{summary['ipcw']['raw_weight_max']:.3f}**.

Unweighted v0.9 CIF:

{primary_cif.to_markdown(index=False, floatfmt='.4f')}

IPCW CIF:

{ipcw_cif.to_markdown(index=False, floatfmt='.4f')}

## MAR multiple imputation

The MAR analysis uses **{summary['n_imputations']}** stochastic chained-equation imputations implemented with Bayesian-regression IterativeImputer. The imputation model includes the full scheduled PHQ-9 vector and available baseline categorical indicators. Observed scores are restored exactly after each imputation. Estimates are pooled with Rubin's rules.

Month-12 MAR results:

{mar12[['estimand','estimate','se','ci95_low','ci95_high','fraction_missing_information']].to_markdown(index=False, floatfmt='.4f')}

## MNAR delta adjustment

For each imputation, only originally missing follow-up scores receive a prespecified additive delta before event reconstruction. Positive delta means missing PHQ-9 values are systematically **worse** than their MAR predictions; negative delta means systematically better. Values are clipped to the valid 0-27 score range.

Month-12 improvement-minus-deterioration sensitivity:

{delta12[['delta_points_added_to_missing_phq9','estimate','se','ci95_low','ci95_high','fraction_missing_information']].to_markdown(index=False, floatfmt='.4f')}

Tipping-point result within the prespecified grid: **{summary['mnar_tipping_point_statement']}**

## Interpretation boundary

IPCW and MI both rely on observed-data models; delta adjustment deliberately explores departures from MAR rather than claiming to estimate the true MNAR mechanism. The point is to show where the clinical conclusion is stable and where it becomes assumption-sensitive. A governed service dataset with explicit non-response, discharge and attrition reason codes would support a better missingness model.
"""
    (outdir / "V10_MISSINGNESS_MNAR_REPORT.md").write_text(report)


def run_analysis(
    data_path: Path,
    outdir: Path,
    n_imputations: int = 20,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    df = parse_index(pd.read_parquet(data_path))
    measurements, conflicts = build_all_score_measurements(df)
    wide = build_score_wide(measurements)
    missing = missingness_summary(wide)
    design, missing_followup = imputation_design_matrix(wide, df)
    imputations = generate_mar_imputations(
        wide,
        design,
        n_imputations=n_imputations,
    )
    mi = pooled_mi_sensitivity(wide, imputations)

    raw_measurements = wide.reset_index().melt(
        id_vars="participant_id",
        value_vars=SCORE_COLUMNS,
        var_name="score_month",
        value_name="score",
    )
    raw_measurements["measurement_month"] = raw_measurements["score_month"].str.replace("phq", "", regex=False).astype(int)
    raw_measurements = raw_measurements.dropna(subset=["score"])[
        ["participant_id", "measurement_month", "score"]
    ]
    primary_pp, primary_participant = build_first_change_person_period(raw_measurements)
    primary_cif = cumulative_incidence(primary_pp)

    risk_rows = build_observation_risk_rows(wide)
    weights, ipcw_diagnostics = fit_ipcw_observation_model(risk_rows)
    weighted_pp = primary_pp.merge(
        weights,
        on=["participant_id", "interval_end_month"],
        how="left",
        validate="one_to_one",
    )
    if weighted_pp["ipcw_weight"].isna().any():
        raise AssertionError("IPCW weights missing for observed person-period rows")
    ipcw_cif = time_varying_weighted_cif(weighted_pp)

    delta12 = mi[
        mi["month"].eq(12)
        & mi["estimand"].eq("cif_difference_improvement_minus_deterioration")
        & mi["delta_points_added_to_missing_phq9"].ge(0)
    ].sort_values("delta_points_added_to_missing_phq9")
    tipped = delta12[delta12["estimate"] <= 0]
    if len(tipped):
        tipping_delta = float(tipped.iloc[0]["delta_points_added_to_missing_phq9"])
        tipping_statement = (
            f"imputed month-12 deterioration reaches/exceeds improvement at delta={tipping_delta:g} PHQ-9 points"
        )
    else:
        tipping_delta = None
        tipping_statement = (
            f"no reversal of improvement-minus-deterioration through delta={max(DELTA_GRID):g} PHQ-9 points"
        )

    primary12 = primary_cif[primary_cif["month"].eq(12)].iloc[0]
    ipcw12 = ipcw_cif[ipcw_cif["month"].eq(12)].iloc[0]
    mar12 = mi[
        mi["delta_points_added_to_missing_phq9"].eq(0)
        & mi["month"].eq(12)
    ]
    mar_improvement = float(
        mar12.loc[mar12["estimand"].eq("cif_improvement"), "estimate"].iloc[0]
    )
    mar_deterioration = float(
        mar12.loc[mar12["estimand"].eq("cif_deterioration"), "estimate"].iloc[0]
    )

    summary = {
        "version": "0.10",
        "dataset": "PSYCHE-D public longitudinal release",
        "source_rows": int(len(df)),
        "baseline_cohort_n": int(len(wide)),
        "measurement_conflicts": int(len(conflicts)),
        "n_imputations": int(n_imputations),
        "delta_grid": list(DELTA_GRID),
        "v09_first_missing_visit_censor_n": int(
            primary_participant["censor_reason"].eq("first_missing_scheduled_measurement").sum()
        ),
        "primary_month12": {
            "cif_improvement": float(primary12["cif_improvement"]),
            "cif_deterioration": float(primary12["cif_deterioration"]),
        },
        "ipcw_month12": {
            "cif_improvement": float(ipcw12["cif_improvement"]),
            "cif_deterioration": float(ipcw12["cif_deterioration"]),
        },
        "mar_mi_month12": {
            "cif_improvement": mar_improvement,
            "cif_deterioration": mar_deterioration,
        },
        "ipcw": ipcw_diagnostics,
        "mnar_tipping_delta": tipping_delta,
        "mnar_tipping_point_statement": tipping_statement,
        "interpretation_boundary": (
            "Missing PSYCHE-D follow-up is not identified as questionnaire non-response. IPCW and MAR MI are observed-data "
            "assumption models; delta adjustment is a controlled MNAR sensitivity analysis."
        ),
    }

    missing.to_csv(outdir / "v10_missingness_by_month.csv", index=False)
    risk_rows.to_csv(outdir / "v10_observation_risk_rows.csv", index=False)
    weights.to_csv(outdir / "v10_ipcw_weights.csv", index=False)
    primary_cif.to_csv(outdir / "v10_primary_cif.csv", index=False)
    ipcw_cif.to_csv(outdir / "v10_ipcw_cif.csv", index=False)
    mi.to_csv(outdir / "v10_mi_mnar_sensitivity.csv", index=False)
    (outdir / "v10_missingness_mnar_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    write_report(outdir, summary, missing, primary_cif, ipcw_cif, mi)
    print("V10_MISSINGNESS_MNAR:", json.dumps(summary))
    print("V10_MISSINGNESS:\n", missing.to_string(index=False))
    print("V10_IPCW_CIF:\n", ipcw_cif.to_string(index=False))
    print("V10_DELTA_MONTH12:\n", mi[mi["month"].eq(12)].to_string(index=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-imputations", type=int, default=20)
    args = parser.parse_args()
    run_analysis(args.data, args.out, n_imputations=args.n_imputations)

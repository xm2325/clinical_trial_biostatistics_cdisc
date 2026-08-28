from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2

from analysis import parse_index
from v02_score_longitudinal import PHQ_RELIABLE_CHANGE_POINTS, SCHEDULED_MONTHS

BASELINE_MONTH = 0
FOLLOWUP_MONTHS = tuple(SCHEDULED_MONTHS)


def build_all_score_measurements(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconstruct every observed PHQ-9 score without requiring a complete interval."""

    required = {"participant_id", "study_month", "phq9_score_start", "phq9_score_end"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"PSYCHE-D score columns missing: {missing}")

    start = df.loc[df["phq9_score_start"].notna(), ["participant_id", "study_month", "phq9_score_start"]].copy()
    start["measurement_month"] = start["study_month"].astype(int) - 3
    start["score"] = pd.to_numeric(start["phq9_score_start"], errors="raise")
    start["source"] = "interval_start"

    end = df.loc[df["phq9_score_end"].notna(), ["participant_id", "study_month", "phq9_score_end"]].copy()
    end["measurement_month"] = end["study_month"].astype(int)
    end["score"] = pd.to_numeric(end["phq9_score_end"], errors="raise")
    end["source"] = "interval_end"

    stacked = pd.concat(
        [
            start[["participant_id", "measurement_month", "score", "source"]],
            end[["participant_id", "measurement_month", "score", "source"]],
        ],
        ignore_index=True,
    )
    stacked = stacked[
        stacked["measurement_month"].isin([BASELINE_MONTH, *FOLLOWUP_MONTHS])
    ].copy()
    if not stacked["score"].between(0, 27).all():
        raise ValueError("Observed PHQ-9 scores outside the valid 0-27 range")

    audit = (
        stacked.groupby(["participant_id", "measurement_month"], as_index=False)
        .agg(
            n_source_rows=("score", "size"),
            score_min=("score", "min"),
            score_max=("score", "max"),
            score=("score", "mean"),
        )
    )
    audit["score_range"] = audit["score_max"] - audit["score_min"]
    conflicts = audit[audit["score_range"] > 1e-9].copy()
    measurements = audit[["participant_id", "measurement_month", "score"]].copy()
    measurements = measurements.sort_values(["participant_id", "measurement_month"]).reset_index(drop=True)
    return measurements, conflicts


def baseline_covariates(df: pd.DataFrame, baseline_ids: set) -> pd.DataFrame:
    ordered = df.sort_values(["participant_id", "study_month"])
    first = ordered.groupby("participant_id", as_index=False).first()
    keep = ["participant_id"]
    for candidate in ("sex", "insurance", "trauma"):
        if candidate in first.columns:
            keep.append(candidate)
    result = first[keep].copy()
    result = result[result["participant_id"].isin(baseline_ids)].copy()
    return result


def build_first_change_person_period(
    measurements: pd.DataFrame,
    covariates: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a discrete-time first-event competing-risks cohort.

    The event is the first *observed* scheduled PHQ-9 score at least six points
    below (improvement) or above (deterioration) the month-0 score. Primary
    follow-up censors at the first missing scheduled assessment; later visits
    after that gap are not used. This deliberately makes the censoring
    assumption visible for v0.10 missing-data sensitivity analysis.
    """

    pivot = measurements.pivot(
        index="participant_id", columns="measurement_month", values="score"
    )
    if BASELINE_MONTH not in pivot.columns:
        raise ValueError("No month-0 PHQ-9 measurements available")
    baseline_ids = pivot.index[pivot[BASELINE_MONTH].notna()]
    pivot = pivot.loc[baseline_ids].copy()

    rows: list[dict] = []
    participants: list[dict] = []
    for participant_id, row in pivot.iterrows():
        baseline = float(row[BASELINE_MONTH])
        event_type = "none"
        event_month: int | None = None
        censor_month = FOLLOWUP_MONTHS[-1]
        censor_reason = "administrative_12_month"
        observed_followups = 0

        for month in FOLLOWUP_MONTHS:
            score = row.get(month, np.nan)
            if pd.isna(score):
                censor_month = month - 3
                censor_reason = "first_missing_scheduled_measurement"
                break

            observed_followups += 1
            score = float(score)
            change = score - baseline
            improvement = change <= -PHQ_RELIABLE_CHANGE_POINTS
            deterioration = change >= PHQ_RELIABLE_CHANGE_POINTS
            if improvement and deterioration:
                raise AssertionError("Improvement and deterioration cannot co-occur")

            rows.append(
                {
                    "participant_id": participant_id,
                    "interval_end_month": int(month),
                    "baseline_phq9": baseline,
                    "current_phq9": score,
                    "change_from_baseline": change,
                    "event_improvement": int(improvement),
                    "event_deterioration": int(deterioration),
                    "event_any": int(improvement or deterioration),
                }
            )
            if improvement or deterioration:
                event_type = "improvement" if improvement else "deterioration"
                event_month = int(month)
                censor_month = int(month)
                censor_reason = "event"
                break

        participants.append(
            {
                "participant_id": participant_id,
                "baseline_phq9": baseline,
                "observed_followups_before_event_or_censor": observed_followups,
                "event_type": event_type,
                "event_month": event_month,
                "censor_month": int(censor_month),
                "censor_reason": censor_reason,
            }
        )

    person_period = pd.DataFrame(rows)
    participant = pd.DataFrame(participants)
    participant["event_improvement"] = participant["event_type"].eq("improvement").astype(int)
    participant["event_deterioration"] = participant["event_type"].eq("deterioration").astype(int)

    if covariates is not None and len(covariates):
        person_period = person_period.merge(covariates, on="participant_id", how="left")
        participant = participant.merge(covariates, on="participant_id", how="left")

    if len(person_period):
        mean = float(person_period["baseline_phq9"].mean())
        sd = float(person_period["baseline_phq9"].std(ddof=0))
        if sd <= 0:
            raise ValueError("Baseline PHQ-9 has zero variance")
        person_period["baseline_phq9_z"] = (person_period["baseline_phq9"] - mean) / sd
        participant["baseline_phq9_z"] = (participant["baseline_phq9"] - mean) / sd

    return person_period, participant


def cumulative_incidence(
    person_period: pd.DataFrame,
    participant_weights: dict | None = None,
) -> pd.DataFrame:
    """Discrete Aalen-Johansen cumulative incidence on scheduled visits."""

    if participant_weights is None:
        participant_weights = {}

    survival = 1.0
    cif_improvement = 0.0
    cif_deterioration = 0.0
    rows: list[dict] = []
    for month in FOLLOWUP_MONTHS:
        frame = person_period[person_period["interval_end_month"].eq(month)].copy()
        if participant_weights:
            weight = frame["participant_id"].map(participant_weights).fillna(0).to_numpy(dtype=float)
        else:
            weight = np.ones(len(frame), dtype=float)
        n_risk = float(weight.sum())
        if n_risk <= 0:
            rows.append(
                {
                    "month": month,
                    "n_risk": 0.0,
                    "events_improvement": 0.0,
                    "events_deterioration": 0.0,
                    "survival_no_reliable_change": survival,
                    "cif_improvement": cif_improvement,
                    "cif_deterioration": cif_deterioration,
                }
            )
            continue
        d_improvement = float(np.sum(weight * frame["event_improvement"].to_numpy(dtype=float)))
        d_deterioration = float(np.sum(weight * frame["event_deterioration"].to_numpy(dtype=float)))
        cif_improvement += survival * d_improvement / n_risk
        cif_deterioration += survival * d_deterioration / n_risk
        survival *= 1.0 - (d_improvement + d_deterioration) / n_risk
        rows.append(
            {
                "month": month,
                "n_risk": n_risk,
                "events_improvement": d_improvement,
                "events_deterioration": d_deterioration,
                "survival_no_reliable_change": survival,
                "cif_improvement": cif_improvement,
                "cif_deterioration": cif_deterioration,
            }
        )
    return pd.DataFrame(rows)


def participant_bootstrap_cif(
    person_period: pd.DataFrame,
    participant: pd.DataFrame,
    replicates: int = 400,
    seed: int = 20260828,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ids = participant["participant_id"].to_numpy()
    if len(ids) < 100:
        raise ValueError("Too few participants for cluster bootstrap")
    records: list[dict] = []
    for replicate in range(replicates):
        sampled = rng.choice(ids, size=len(ids), replace=True)
        unique, counts = np.unique(sampled, return_counts=True)
        weights = dict(zip(unique.tolist(), counts.astype(float).tolist()))
        cif = cumulative_incidence(person_period, weights)
        for row in cif.itertuples(index=False):
            records.append(
                {
                    "replicate": replicate,
                    "month": int(row.month),
                    "cif_improvement": float(row.cif_improvement),
                    "cif_deterioration": float(row.cif_deterioration),
                    "survival_no_reliable_change": float(row.survival_no_reliable_change),
                }
            )
    draws = pd.DataFrame(records)
    summaries = []
    for month, frame in draws.groupby("month", sort=True):
        for estimand in (
            "cif_improvement",
            "cif_deterioration",
            "survival_no_reliable_change",
        ):
            values = frame[estimand].to_numpy(dtype=float)
            q025, q50, q975 = np.quantile(values, [0.025, 0.5, 0.975])
            summaries.append(
                {
                    "month": int(month),
                    "estimand": estimand,
                    "bootstrap_mean": float(values.mean()),
                    "bootstrap_q025": float(q025),
                    "bootstrap_q50": float(q50),
                    "bootstrap_q975": float(q975),
                    "finite_replicates": int(np.isfinite(values).sum()),
                }
            )
    return pd.DataFrame(summaries)


def fit_cause_specific_cloglog(
    person_period: pd.DataFrame,
    outcome: str,
) -> dict:
    """Fit a discrete-time cause-specific complementary-log-log model."""

    if outcome not in {"event_improvement", "event_deterioration"}:
        raise ValueError(outcome)
    model_df = person_period.copy()
    if model_df[outcome].sum() < 20:
        raise ValueError(f"Too few {outcome} events")

    formula = f"{outcome} ~ C(interval_end_month) + baseline_phq9_z"
    covariates = ["baseline_phq9_z"]
    if "sex" in model_df.columns:
        nonmissing = model_df["sex"].dropna()
        if nonmissing.nunique() >= 2 and len(nonmissing) >= 0.7 * len(model_df):
            formula += " + C(sex)"

    family = sm.families.Binomial(link=sm.families.links.CLogLog())
    base = smf.glm(formula, data=model_df, family=family).fit(
        cov_type="cluster",
        cov_kwds={"groups": model_df["participant_id"]},
    )
    expanded_formula = (
        f"{outcome} ~ C(interval_end_month) + baseline_phq9_z "
        "+ baseline_phq9_z:C(interval_end_month)"
    )
    if "+ C(sex)" in formula:
        expanded_formula += " + C(sex)"
    expanded = smf.glm(expanded_formula, data=model_df, family=family).fit()
    base_ml = smf.glm(formula, data=model_df, family=family).fit()
    lr = max(0.0, 2.0 * (expanded.llf - base_ml.llf))
    df_diff = max(1, int(expanded.df_model - base_ml.df_model))
    interaction_p = float(chi2.sf(lr, df_diff))

    coefficient = float(base.params["baseline_phq9_z"])
    se = float(base.bse["baseline_phq9_z"])
    low = coefficient - 1.96 * se
    high = coefficient + 1.96 * se
    return {
        "outcome": outcome,
        "formula": formula,
        "n_person_period_rows": int(base.nobs),
        "n_participants": int(model_df.loc[base.model.data.row_labels, "participant_id"].nunique())
        if hasattr(base.model.data, "row_labels")
        else int(model_df["participant_id"].nunique()),
        "events": int(model_df[outcome].sum()),
        "converged": bool(base.converged),
        "baseline_phq9_z_log_hazard_coefficient": coefficient,
        "baseline_phq9_z_hazard_ratio": float(np.exp(coefficient)),
        "baseline_phq9_z_hr_ci95_low": float(np.exp(low)),
        "baseline_phq9_z_hr_ci95_high": float(np.exp(high)),
        "time_interaction_lr_chi2": float(lr),
        "time_interaction_df": df_diff,
        "time_interaction_p": interaction_p,
        "interpretation": (
            "Cause-specific discrete-time hazard association with cluster-robust participant SEs. "
            "This is prognostic/descriptive, not a treatment-effect estimate."
        ),
    }


def write_report(
    outdir: Path,
    summary: dict,
    cif: pd.DataFrame,
    bootstrap: pd.DataFrame,
    improvement_model: dict,
    deterioration_model: dict,
) -> None:
    month12 = cif[cif["month"].eq(12)].iloc[0]
    boot12 = bootstrap[bootstrap["month"].eq(12)].copy()
    report = f"""# v0.9 Competing-risks time to first reliable PHQ-9 change

## Research question

Among PSYCHE-D participants with an observed month-0 PHQ-9 score, what is the time to the first **observed reliable change** relative to baseline, distinguishing reliable improvement from reliable deterioration?

## Event definition

At scheduled months 3, 6, 9 and 12, PHQ-9 is compared with the participant's month-0 score:

- reliable improvement: change <= -{PHQ_RELIABLE_CHANGE_POINTS:.0f} points;
- reliable deterioration: change >= +{PHQ_RELIABLE_CHANGE_POINTS:.0f} points;
- otherwise: no reliable change yet.

Only the first observed event is retained, so improvement and deterioration are mutually exclusive competing first events. The primary analysis censors at the first missing scheduled PHQ-9 assessment; it does **not** skip a missing visit and use a later visit as though the risk process had been continuously observed.

## Cohort

- Source participants: **{summary['source_participants']:,}**
- Participants with month-0 PHQ-9: **{summary['baseline_cohort_n']:,}**
- Participants censored before the first three-month event assessment because month 3 is missing: **{summary['censored_at_month0_n']:,}**
- First reliable improvements observed: **{summary['first_improvement_events']:,}**
- First reliable deteriorations observed: **{summary['first_deterioration_events']:,}**

## Non-parametric cumulative incidence

{cif.to_markdown(index=False, floatfmt='.4f')}

At month 12, the primary discrete Aalen-Johansen estimate is **{100*month12.cif_improvement:.2f}%** for first reliable improvement and **{100*month12.cif_deterioration:.2f}%** for first reliable deterioration. Participant-cluster bootstrap uncertainty is stored in `v09_cif_cluster_bootstrap.csv`.

Month-12 bootstrap intervals:

{boot12.to_markdown(index=False, floatfmt='.4f')}

## Cause-specific discrete-time hazard models

The complementary-log-log models use a separate baseline hazard for scheduled month and cluster-robust participant standard errors. A one-SD higher baseline PHQ-9 is associated with:

- improvement cause-specific hazard ratio **{improvement_model['baseline_phq9_z_hazard_ratio']:.3f}** (95% CI {improvement_model['baseline_phq9_z_hr_ci95_low']:.3f}-{improvement_model['baseline_phq9_z_hr_ci95_high']:.3f});
- deterioration cause-specific hazard ratio **{deterioration_model['baseline_phq9_z_hazard_ratio']:.3f}** (95% CI {deterioration_model['baseline_phq9_z_hr_ci95_low']:.3f}-{deterioration_model['baseline_phq9_z_hr_ci95_high']:.3f}).

The time-interaction checks test whether the baseline-severity association is constant across the four discrete follow-up intervals. They are specification diagnostics, not causal-effect tests.

## Missingness boundary

This is **time to first observed reliable change under censoring at the first missing scheduled visit**. PSYCHE-D does not identify every absence as questionnaire non-response rather than attrition or release preprocessing. Therefore independent censoring is an explicit working assumption, not a fact established by the data. v0.10 is reserved for IPCW/MAR/MNAR sensitivity to this assumption.
"""
    (outdir / "V09_COMPETING_RISKS_SURVIVAL_REPORT.md").write_text(report)


def run_analysis(
    data_path: Path,
    outdir: Path,
    bootstrap_replicates: int = 400,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    df = parse_index(pd.read_parquet(data_path))
    measurements, conflicts = build_all_score_measurements(df)
    baseline_ids = set(
        measurements.loc[
            measurements["measurement_month"].eq(BASELINE_MONTH), "participant_id"
        ].tolist()
    )
    covariates = baseline_covariates(df, baseline_ids)
    person_period, participant = build_first_change_person_period(
        measurements, covariates
    )

    conflicts.to_csv(outdir / "v09_score_measurement_conflicts.csv", index=False)
    person_period.to_csv(outdir / "v09_first_change_person_period.csv", index=False)
    participant.to_csv(outdir / "v09_first_change_participant_summary.csv", index=False)

    cif = cumulative_incidence(person_period)
    bootstrap = participant_bootstrap_cif(
        person_period,
        participant,
        replicates=bootstrap_replicates,
    )
    improvement_model = fit_cause_specific_cloglog(
        person_period, "event_improvement"
    )
    deterioration_model = fit_cause_specific_cloglog(
        person_period, "event_deterioration"
    )

    cif.to_csv(outdir / "v09_cumulative_incidence.csv", index=False)
    bootstrap.to_csv(outdir / "v09_cif_cluster_bootstrap.csv", index=False)
    (outdir / "v09_improvement_cloglog.json").write_text(
        json.dumps(improvement_model, indent=2) + "\n"
    )
    (outdir / "v09_deterioration_cloglog.json").write_text(
        json.dumps(deterioration_model, indent=2) + "\n"
    )

    summary = {
        "version": "0.9",
        "dataset": "PSYCHE-D public longitudinal release",
        "source_rows": int(len(df)),
        "source_participants": int(df["participant_id"].nunique()),
        "baseline_cohort_n": int(len(participant)),
        "person_period_rows": int(len(person_period)),
        "participants_with_any_observed_followup_before_event_or_censor": int(
            (participant["observed_followups_before_event_or_censor"] > 0).sum()
        ),
        "censored_at_month0_n": int(
            (
                participant["censor_reason"].eq("first_missing_scheduled_measurement")
                & participant["censor_month"].eq(0)
            ).sum()
        ),
        "first_improvement_events": int(participant["event_improvement"].sum()),
        "first_deterioration_events": int(participant["event_deterioration"].sum()),
        "administratively_censored_at_12_n": int(
            participant["censor_reason"].eq("administrative_12_month").sum()
        ),
        "first_missing_visit_censor_n": int(
            participant["censor_reason"].eq("first_missing_scheduled_measurement").sum()
        ),
        "measurement_conflicts": int(len(conflicts)),
        "bootstrap_replicates": int(bootstrap_replicates),
        "month12_cif_improvement": float(
            cif.loc[cif["month"].eq(12), "cif_improvement"].iloc[0]
        ),
        "month12_cif_deterioration": float(
            cif.loc[cif["month"].eq(12), "cif_deterioration"].iloc[0]
        ),
        "improvement_model": improvement_model,
        "deterioration_model": deterioration_model,
        "censoring_boundary": (
            "Primary analysis censors at the first missing scheduled PHQ-9 visit. Absence may reflect non-response, "
            "attrition or source preprocessing; independent censoring is therefore a working assumption to be "
            "challenged by v0.10 IPCW/MI/MNAR sensitivity."
        ),
    }
    (outdir / "v09_competing_risks_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    write_report(
        outdir,
        summary,
        cif,
        bootstrap,
        improvement_model,
        deterioration_model,
    )
    print("V09_COMPETING_RISKS:", json.dumps(summary))
    print("V09_CIF:\n", cif.to_string(index=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=400)
    args = parser.parse_args()
    run_analysis(
        args.data,
        args.out,
        bootstrap_replicates=args.bootstrap_replicates,
    )

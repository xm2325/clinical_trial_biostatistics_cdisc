from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

EXPECTED_ARMS = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
VISIT_DAYS = {"Week 8": 56, "Week 16": 112, "Week 24": 168}
ICH_STRATEGIES = {
    "treatment_policy",
    "hypothetical",
    "composite",
    "while_on_treatment",
    "principal_stratum",
}
REQUIRED_ESTIMAND_ATTRIBUTES = [
    "treatment",
    "population",
    "variable",
    "intercurrent_events",
    "summary_measure",
]


def _require(df: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


def _norm_visit(series: pd.Series) -> pd.Series:
    mapping = {k.upper(): k for k in VISIT_DAYS}
    return series.fillna("").astype(str).str.strip().str.upper().map(mapping)


def validate_estimand_spec(spec: dict) -> pd.DataFrame:
    """Return required checks for an ICH E9(R1)-style estimand specification."""
    rows: list[dict[str, object]] = []

    def add(check: str, passed: bool, detail: str, required: bool = True) -> None:
        rows.append({"check": check, "passed": bool(passed), "required": bool(required), "detail": detail, "area": "estimand_spec"})

    estimands = spec.get("estimands", [])
    add("Estimand specification contains at least one estimand", bool(estimands), f"estimands={len(estimands)}")
    ids = [str(x.get("id", "")).strip() for x in estimands]
    add("Estimand identifiers are non-empty and unique", bool(ids) and all(ids) and len(ids) == len(set(ids)), f"ids={ids}")

    for estimand in estimands:
        eid = str(estimand.get("id", "<missing>"))
        missing_attrs = [a for a in REQUIRED_ESTIMAND_ATTRIBUTES if not estimand.get(a)]
        add(f"{eid} has the five estimand attributes", not missing_attrs, f"missing={missing_attrs}")

        treatment = estimand.get("treatment", {})
        conditions = treatment.get("conditions", []) if isinstance(treatment, dict) else []
        add(
            f"{eid} treatment conditions match portfolio arms",
            set(conditions) == set(EXPECTED_ARMS),
            f"conditions={conditions}",
        )

        variable = estimand.get("variable", {}) if isinstance(estimand.get("variable", {}), dict) else {}
        add(f"{eid} variable identifies ACTOT", variable.get("parameter") == "ACTOT", f"parameter={variable.get('parameter')}")
        add(f"{eid} variable identifies Week 24", variable.get("visit") == "Week 24", f"visit={variable.get('visit')}")
        add(
            f"{eid} variable is change from baseline",
            variable.get("measure") == "change_from_baseline",
            f"measure={variable.get('measure')}",
        )

        ices = estimand.get("intercurrent_events", [])
        disc = [x for x in ices if isinstance(x, dict) and x.get("event") == "treatment_discontinuation"]
        strategies = [x.get("strategy") for x in ices if isinstance(x, dict)]
        add(f"{eid} intercurrent-event strategies use ICH categories", bool(strategies) and all(s in ICH_STRATEGIES for s in strategies), f"strategies={strategies}")
        add(f"{eid} specifies treatment discontinuation", len(disc) == 1, f"matches={len(disc)}")
        if disc:
            add(
                f"{eid} treatment discontinuation uses treatment-policy strategy",
                disc[0].get("strategy") == "treatment_policy",
                f"strategy={disc[0].get('strategy')}",
            )

        estimator = estimand.get("estimator", {})
        primary = estimator.get("primary", {}) if isinstance(estimator, dict) else {}
        add(f"{eid} primary estimator is MMRM", primary.get("method") == "MMRM", f"method={primary.get('method')}")
        add(f"{eid} primary estimator does not use LOCF", primary.get("uses_locf") is False, f"uses_locf={primary.get('uses_locf')}")
        add(f"{eid} primary missing-data assumption is MAR", primary.get("missing_data_assumption") == "MAR", f"assumption={primary.get('missing_data_assumption')}")

    return pd.DataFrame(rows)


def _target_population(adsl: pd.DataFrame, adqs: pd.DataFrame) -> pd.DataFrame:
    _require(adsl, ["STUDYID", "USUBJID", "TRT01A", "RANDFL", "DCSFL", "EOSDECOD", "EOSDT", "TRTSDT"], "ADSL-style")
    _require(adqs, ["STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "ABLFL", "EFFFL", "ADT"], "ADQS-style")

    rand = adsl.loc[adsl["RANDFL"].eq("Y") & adsl["TRT01A"].isin(EXPECTED_ARMS)].copy()
    base = adqs.loc[
        adqs["ABLFL"].eq("Y") & pd.to_numeric(adqs["AVAL"], errors="coerce").notna(),
        ["STUDYID", "USUBJID", "TRT01A", "AVAL"],
    ].copy()
    base = base.sort_values(["STUDYID", "USUBJID"]).drop_duplicates(["STUDYID", "USUBJID"], keep="last")
    base = base.rename(columns={"AVAL": "BASE_ACTOT", "TRT01A": "TRT01A_ADQS"})
    target = rand.merge(base, on=["STUDYID", "USUBJID"], how="inner", validate="one_to_one")
    mismatch = target["TRT01A"].astype(str) != target["TRT01A_ADQS"].astype(str)
    if bool(mismatch.any()):
        raise ValueError(f"Treatment mismatch between ADSL-style and baseline ACTOT for {int(mismatch.sum())} subjects")
    target["EOSDT"] = pd.to_datetime(target["EOSDT"], errors="coerce").dt.normalize()
    target["TRTSDT"] = pd.to_datetime(target["TRTSDT"], errors="coerce").dt.normalize()
    target["DISCDY"] = (target["EOSDT"] - target["TRTSDT"]).dt.days + 1
    return target


def derive_actot_missingness(adsl: pd.DataFrame, adqs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create visit missingness, subject patterns and Week-24 disposition summaries.

    Denominators are randomised subjects with an observed baseline ACTOT score.
    Missingness is descriptive and does not assert that MAR holds.
    """
    target = _target_population(adsl, adqs)
    obs = adqs.copy()
    obs["AVISIT_N"] = _norm_visit(obs["AVISIT"])
    obs["AVAL_N"] = pd.to_numeric(obs["AVAL"], errors="coerce")
    obs["ADT_N"] = pd.to_datetime(obs["ADT"], errors="coerce").dt.normalize()
    obs = obs.loc[
        obs["ABLFL"].ne("Y")
        & obs["AVISIT_N"].notna()
        & obs["AVAL_N"].notna()
        & obs["BASE"].notna()
    ].copy()
    obs = obs.sort_values(["STUDYID", "USUBJID", "AVISIT_N", "ADT_N"]).drop_duplicates(
        ["STUDYID", "USUBJID", "AVISIT_N"], keep="last"
    )

    subject_rows: list[dict[str, object]] = []
    visit_rows: list[dict[str, object]] = []
    reason_rows: list[dict[str, object]] = []

    obs_keys = set(zip(obs["STUDYID"], obs["USUBJID"], obs["AVISIT_N"]))
    obs_date = {(r.STUDYID, r.USUBJID, r.AVISIT_N): r.ADT_N for r in obs.itertuples()}

    for row in target.itertuples():
        rec: dict[str, object] = {
            "STUDYID": row.STUDYID,
            "USUBJID": row.USUBJID,
            "TRT01A": row.TRT01A,
            "DCSFL": row.DCSFL,
            "EOSDECOD": row.EOSDECOD,
            "DISCDY": row.DISCDY,
        }
        pattern = []
        for visit in VISIT_DAYS:
            key = (row.STUDYID, row.USUBJID, visit)
            observed = key in obs_keys
            rec[visit.replace(" ", "_").upper()] = "O" if observed else "M"
            pattern.append("O" if observed else "M")
        rec["PATTERN"] = "".join(pattern)
        subject_rows.append(rec)

    patterns = pd.DataFrame(subject_rows)

    for arm in EXPECTED_ARMS:
        arm_target = target.loc[target["TRT01A"].eq(arm)].copy()
        target_n = int(len(arm_target))
        arm_keys = set(zip(arm_target["STUDYID"], arm_target["USUBJID"]))
        for visit, nominal_day in VISIT_DAYS.items():
            observed_subjects = {
                (study, subj)
                for study, subj, v in obs_keys
                if v == visit and (study, subj) in arm_keys
            }
            observed_n = len(observed_subjects)
            missing_n = target_n - observed_n
            due_by_visit = arm_target["DCSFL"].eq("Y") & arm_target["DISCDY"].notna() & arm_target["DISCDY"].le(nominal_day)
            discontinued_before_n = int(due_by_visit.sum())
            prior_disc_keys = set(zip(arm_target.loc[due_by_visit, "STUDYID"], arm_target.loc[due_by_visit, "USUBJID"]))
            missing_keys = arm_keys - observed_subjects
            missing_prior_n = len(missing_keys & prior_disc_keys)
            observed_after_disc_n = 0
            for study, subj in observed_subjects:
                subj_row = arm_target.loc[(arm_target["STUDYID"].eq(study)) & (arm_target["USUBJID"].eq(subj))].iloc[0]
                adt = obs_date.get((study, subj, visit), pd.NaT)
                if subj_row["DCSFL"] == "Y" and pd.notna(subj_row["EOSDT"]) and pd.notna(adt) and adt > subj_row["EOSDT"]:
                    observed_after_disc_n += 1
            visit_rows.append(
                {
                    "TRT01A": arm,
                    "AVISIT": visit,
                    "nominal_day": nominal_day,
                    "target_n": target_n,
                    "observed_n": observed_n,
                    "missing_n": missing_n,
                    "missing_pct": 100.0 * missing_n / target_n if target_n else np.nan,
                    "discontinued_before_or_on_visit_n": discontinued_before_n,
                    "missing_with_prior_discontinuation_n": missing_prior_n,
                    "missing_without_prior_discontinuation_n": missing_n - missing_prior_n,
                    "observed_after_discontinuation_n": observed_after_disc_n,
                }
            )

        wk24_obs = {
            (study, subj)
            for study, subj, v in obs_keys
            if v == "Week 24" and (study, subj) in arm_keys
        }
        wk24_missing = arm_target.loc[
            ~arm_target.apply(lambda r: (r["STUDYID"], r["USUBJID"]) in wk24_obs, axis=1)
        ].copy()
        wk24_missing["missingness_category"] = np.where(
            wk24_missing["DCSFL"].eq("Y"),
            wk24_missing["EOSDECOD"].fillna("").astype(str).str.strip().replace("", "DISCONTINUED_REASON_UNAVAILABLE"),
            "NO_RECORDED_DISCONTINUATION",
        )
        denom = int(len(wk24_missing))
        counts = wk24_missing.groupby("missingness_category", dropna=False).size().sort_values(ascending=False)
        for category, n in counts.items():
            reason_rows.append(
                {
                    "TRT01A": arm,
                    "category": str(category),
                    "n": int(n),
                    "denominator_missing_week24": denom,
                    "pct_of_missing": 100.0 * int(n) / denom if denom else np.nan,
                }
            )

    return pd.DataFrame(visit_rows), patterns, pd.DataFrame(reason_rows)


def review_estimand_consistency(
    spec: dict,
    adsl: pd.DataFrame,
    adqs: pd.DataFrame,
    mmrm: pd.DataFrame,
    missingness: pd.DataFrame,
    reasons: pd.DataFrame,
) -> pd.DataFrame:
    """Review estimand, estimator and missingness consistency against outputs."""
    checks = [validate_estimand_spec(spec)]
    rows: list[dict[str, object]] = []

    def add(check: str, passed: bool, detail: str, area: str) -> None:
        rows.append({"check": check, "passed": bool(passed), "required": True, "detail": detail, "area": area})

    target = _target_population(adsl, adqs)
    expected_rows = len(EXPECTED_ARMS) * len(VISIT_DAYS)
    add("Missingness table has every arm-by-visit cell", len(missingness) == expected_rows, f"rows={len(missingness)}; expected={expected_rows}", "missingness")
    reconcile = (missingness["observed_n"] + missingness["missing_n"] == missingness["target_n"]).all()
    add("Observed plus missing equals target denominator", bool(reconcile), f"cells={len(missingness)}", "missingness")
    split = (
        missingness["missing_with_prior_discontinuation_n"] + missingness["missing_without_prior_discontinuation_n"] == missingness["missing_n"]
    ).all()
    add("Missingness discontinuation split reconciles", bool(split), f"cells={len(missingness)}", "missingness")

    expected_target = target.groupby("TRT01A").size().to_dict()
    target_ok = all(int(r.target_n) == int(expected_target.get(r.TRT01A, -1)) for r in missingness.itertuples())
    add("Missingness denominators match randomised baseline-ACTOT population", target_ok, f"target_by_arm={expected_target}", "population")

    wk24 = missingness.loc[missingness["AVISIT"].eq("Week 24")].set_index("TRT01A")
    reason_ok = True
    for arm in EXPECTED_ARMS:
        expected = int(wk24.loc[arm, "missing_n"]) if arm in wk24.index else -1
        actual = int(reasons.loc[reasons["TRT01A"].eq(arm), "n"].sum()) if not reasons.empty else 0
        reason_ok = reason_ok and expected == actual
    add("Week 24 missingness reasons reconcile to missing counts", reason_ok, "reason counts compared with Week 24 missing_n", "missingness")

    _require(mmrm, ["STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "CHG"], "MMRM analysis dataset")
    mm = mmrm.copy()
    mm["AVISIT_N"] = _norm_visit(mm["AVISIT"])
    mm_keys = set(zip(mm["STUDYID"], mm["USUBJID"], mm["AVISIT_N"]))

    aq = adqs.copy()
    aq["AVISIT_N"] = _norm_visit(aq["AVISIT"])
    aq["AVAL_N"] = pd.to_numeric(aq["AVAL"], errors="coerce")
    aq["BASE_N"] = pd.to_numeric(aq["BASE"], errors="coerce")
    aq["CHG_N"] = pd.to_numeric(aq["CHG"], errors="coerce")
    expected_mm = aq.loc[
        aq["EFFFL"].eq("Y")
        & aq["ABLFL"].ne("Y")
        & aq["TRT01A"].isin(EXPECTED_ARMS)
        & aq["AVISIT_N"].notna()
        & aq[["AVAL_N", "BASE_N", "CHG_N"]].notna().all(axis=1)
    ].copy()
    expected_mm_keys = set(zip(expected_mm["STUDYID"], expected_mm["USUBJID"], expected_mm["AVISIT_N"]))
    add("MMRM uses exactly observed eligible ACTOT visit records", mm_keys == expected_mm_keys, f"mmrm={len(mm_keys)}; expected={len(expected_mm_keys)}", "estimator")

    adsl_disc = adsl[["STUDYID", "USUBJID", "DCSFL", "EOSDT"]].copy()
    adsl_disc["EOSDT"] = pd.to_datetime(adsl_disc["EOSDT"], errors="coerce").dt.normalize()
    post = expected_mm.merge(adsl_disc, on=["STUDYID", "USUBJID"], how="left", validate="many_to_one")
    post["ADT_N"] = pd.to_datetime(post["ADT"], errors="coerce").dt.normalize()
    post = post.loc[post["DCSFL"].eq("Y") & post["EOSDT"].notna() & post["ADT_N"].notna() & (post["ADT_N"] > post["EOSDT"])]
    post_keys = set(zip(post["STUDYID"], post["USUBJID"], post["AVISIT_N"]))
    add("Observed post-discontinuation ACTOT records are retained", post_keys.issubset(mm_keys), f"post-discontinuation observed records={len(post_keys)}", "intercurrent_event")

    no_locf = "DTYPE" not in mm.columns or not mm.get("DTYPE", pd.Series(dtype=str)).fillna("").astype(str).str.upper().eq("LOCF").any()
    add("MMRM contains no imputed LOCF rows", bool(no_locf), "primary estimator is observed-data MMRM", "estimator")

    return pd.concat(checks + [pd.DataFrame(rows)], ignore_index=True)

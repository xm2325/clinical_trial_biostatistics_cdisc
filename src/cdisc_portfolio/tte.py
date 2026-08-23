from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TTEResult:
    dataset: pd.DataFrame
    qc: pd.DataFrame
    metrics: dict[str, Any]


def _qc(check: str, passed: bool, detail: str, required: bool = True) -> dict[str, Any]:
    return {
        "check": check,
        "passed": bool(passed),
        "required": bool(required),
        "detail": str(detail),
    }


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in dict.fromkeys(columns) if column not in frame.columns]
    if missing:
        raise ValueError(f"ADSL-style input missing required columns: {', '.join(missing)}")


def _clean(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def derive_retention_adtte(adsl: pd.DataFrame, spec: dict[str, Any]) -> TTEResult:
    if spec.get("version") != "0.17.0":
        raise ValueError("Retention TTE specification version must be 0.17.0")

    parameter = spec.get("parameter", {})
    population = spec.get("population", {})
    event_rule = spec.get("event_rule", {})
    censor_rule = spec.get("censor_rule", {})

    param = str(parameter.get("PARAM", "")).strip()
    paramcd = str(parameter.get("PARAMCD", "")).strip()
    origin_var = str(parameter.get("origin_variable", "")).strip()
    end_var = str(parameter.get("event_or_censor_variable", "")).strip()

    randomised_flag = str(population.get("randomised_flag", "")).strip()
    randomised_value = str(population.get("required_value", "")).strip()
    analysis_trt_var = str(population.get("analysis_treatment_variable", "")).strip()
    actual_trt_var = str(population.get("actual_treatment_context_variable", "")).strip()
    arms = [str(value) for value in population.get("treatment_arms", [])]

    event_var = str(event_rule.get("condition_variable", "")).strip()
    event_value = str(event_rule.get("condition_value", "")).strip().upper()
    censor_var = str(censor_rule.get("condition_variable", "")).strip()
    censor_value = str(censor_rule.get("condition_value", "")).strip().upper()
    event_desc_var = str(event_rule.get("description_source", "")).strip()
    event_desc_fallback = str(event_rule.get("description_fallback_source", "")).strip()
    censor_desc = str(censor_rule.get("EVNTDESC", "")).strip()

    if not param or paramcd != "TTDISC":
        raise ValueError("Retention TTE parameter must define PARAM and PARAMCD=TTDISC")
    if not all([origin_var, end_var, randomised_flag, randomised_value]):
        raise ValueError("Retention TTE population/date specification is incomplete")
    if not analysis_trt_var or not actual_trt_var:
        raise ValueError("Retention TTE treatment-variable specification is incomplete")
    if analysis_trt_var == actual_trt_var:
        raise ValueError("Retention TTE must distinguish planned analysis treatment from actual-treatment context")
    if not all([event_var, event_value, censor_var, censor_value]):
        raise ValueError("Retention TTE event/censor condition specification is incomplete")
    if not event_desc_var or not event_desc_fallback:
        raise ValueError("Retention TTE event description specification is incomplete")
    if not censor_desc:
        raise ValueError("Retention TTE censor EVNTDESC must be non-empty")
    if len(arms) != 3 or len(set(arms)) != 3:
        raise ValueError("Retention TTE specification must define three unique treatment arms")
    if int(event_rule.get("CNSR", -1)) != 0 or int(censor_rule.get("CNSR", -1)) != 1:
        raise ValueError("Retention TTE uses CNSR=0 for events and CNSR=1 for censoring")

    _require_columns(
        adsl,
        [
            "STUDYID",
            "USUBJID",
            analysis_trt_var,
            actual_trt_var,
            "SAFFL",
            randomised_flag,
            origin_var,
            end_var,
            event_var,
            censor_var,
            event_desc_var,
            event_desc_fallback,
        ],
    )

    analysis_arm_all = _clean(adsl[analysis_trt_var])
    d = adsl[
        (_clean(adsl[randomised_flag]) == randomised_value)
        & analysis_arm_all.isin(arms)
    ].copy()
    if d.empty:
        raise ValueError("Retention TTE population is empty")

    planned = _clean(d[analysis_trt_var])
    actual = _clean(d[actual_trt_var])
    treatment_diff = planned.ne(actual)
    event_status = _clean(d[event_var]).str.upper()
    censor_status = _clean(d[censor_var]).str.upper()
    event = event_status.eq(event_value)
    censored = censor_status.eq(censor_value)
    partition_ok = event ^ censored

    start = pd.to_datetime(d[origin_var], errors="coerce")
    end = pd.to_datetime(d[end_var], errors="coerce")
    aval = (end - start).dt.days + 1

    event_desc = _clean(d[event_desc_var])
    fallback_desc = _clean(d[event_desc_fallback])
    event_desc = event_desc.where(event_desc.ne(""), fallback_desc)

    out = pd.DataFrame(
        {
            "STUDYID": _clean(d["STUDYID"]),
            "USUBJID": _clean(d["USUBJID"]),
            "TRT01P": _clean(d["TRT01P"]) if "TRT01P" in d.columns else planned,
            "TRT01A": _clean(d["TRT01A"]) if "TRT01A" in d.columns else actual,
            "ANLTRT": planned,
            "ANLTRTSRC": f"ADSL.{analysis_trt_var}",
            "TRTDIFFL": np.where(treatment_diff.to_numpy(), "Y", "N"),
            "SAFFL": _clean(d["SAFFL"]),
            "PARAM": param,
            "PARAMCD": paramcd,
            "STARTDT": start.dt.strftime("%Y-%m-%d"),
            "ADT": end.dt.strftime("%Y-%m-%d"),
            "AVAL": aval,
            "CNSR": np.where(event.to_numpy(), 0, 1),
            "EVNTDESC": np.where(event.to_numpy(), event_desc.to_numpy(), censor_desc),
            "DCSREAS": np.where(event.to_numpy(), event_desc.to_numpy(), ""),
            "ANL01FL": "Y",
            "SRCDOM": "ADSL",
            "SRCVAR": end_var,
            "STARTSRC": f"ADSL.{origin_var}",
            "ADTSRC": f"ADSL.{end_var}",
            "CNSRSRC": np.where(
                event.to_numpy(), f"ADSL.{event_var}", f"ADSL.{censor_var}"
            ),
            "EVNTSRC": np.where(
                event.to_numpy(), f"ADSL.{event_desc_var}", "SPEC.CENSOR_RULE"
            ),
        }
    ).reset_index(drop=True)

    recomputed_aval = (
        pd.to_datetime(out["ADT"], errors="coerce")
        - pd.to_datetime(out["STARTDT"], errors="coerce")
    ).dt.days + 1
    aval_formula_ok = bool(
        np.array_equal(
            pd.to_numeric(out["AVAL"], errors="coerce").to_numpy(),
            pd.to_numeric(recomputed_aval, errors="coerce").to_numpy(),
            equal_nan=True,
        )
    )
    analysis_treatment_ok = bool(
        np.array_equal(out["ANLTRT"].to_numpy(), planned.to_numpy())
    )
    treatment_diff_flag_ok = bool(
        np.array_equal(
            out["TRTDIFFL"].to_numpy(),
            np.where(treatment_diff.to_numpy(), "Y", "N"),
        )
    )
    event_source_ok = bool(
        (out.loc[event.to_numpy(), "CNSRSRC"] == f"ADSL.{event_var}").all()
        and (out.loc[event.to_numpy(), "EVNTSRC"] == f"ADSL.{event_desc_var}").all()
    )
    censor_source_ok = bool(
        (out.loc[censored.to_numpy(), "CNSRSRC"] == f"ADSL.{censor_var}").all()
        and (out.loc[censored.to_numpy(), "EVNTSRC"] == "SPEC.CENSOR_RULE").all()
    )

    qc_rows = [
        _qc("Retention population is non-empty", len(out) > 0, f"rows={len(out)}"),
        _qc(
            "Retention population has all three randomised treatment arms",
            set(out["ANLTRT"]) == set(arms),
            ", ".join(sorted(out["ANLTRT"].unique().tolist())),
        ),
        _qc(
            "Retention population has one row per subject",
            not out["USUBJID"].duplicated().any(),
            f"duplicate_subjects={int(out['USUBJID'].duplicated().sum())}",
        ),
        _qc(
            "Analysis treatment follows planned randomised assignment",
            analysis_treatment_ok,
            f"source={analysis_trt_var}; rows={len(out)}",
        ),
        _qc(
            "Planned-versus-actual treatment difference flag is exact",
            treatment_diff_flag_ok,
            f"mismatch_subjects={int(treatment_diff.sum())}",
        ),
        _qc(
            "Retention origin dates are complete",
            not start.isna().any(),
            f"missing={int(start.isna().sum())}",
        ),
        _qc(
            "Retention event/censor dates are complete",
            not end.isna().any(),
            f"missing={int(end.isna().sum())}",
        ),
        _qc(
            "Discontinuation and completion flags form an exact partition",
            bool(partition_ok.all()),
            f"invalid_rows={int((~partition_ok).sum())}",
        ),
        _qc(
            "Retention analysis dates are on or after origin dates",
            bool((aval.notna() & aval.ge(1)).all()),
            f"invalid_rows={int((~(aval.notna() & aval.ge(1))).sum())}",
        ),
        _qc("ADTTE AVAL equals ADT-STARTDT+1", aval_formula_ok, f"rows={len(out)}"),
        _qc(
            "ADTTE CNSR contains only event=0 and censor=1",
            set(pd.to_numeric(out["CNSR"], errors="coerce").dropna().astype(int)) <= {0, 1},
            f"codes={sorted(out['CNSR'].unique().tolist())}",
        ),
        _qc(
            "Discontinued subjects map to CNSR=0",
            bool((out.loc[event.to_numpy(), "CNSR"] == 0).all()),
            f"events={int(event.sum())}; source={event_var}={event_value}",
        ),
        _qc(
            "Completed subjects map to CNSR=1",
            bool((out.loc[censored.to_numpy(), "CNSR"] == 1).all()),
            f"censored={int(censored.sum())}; source={censor_var}={censor_value}",
        ),
        _qc(
            "Event and censor descriptions are populated",
            bool(_clean(out["EVNTDESC"]).ne("").all()),
            f"blank={int(_clean(out['EVNTDESC']).eq('').sum())}",
        ),
        _qc(
            "Event source trace follows specification",
            event_source_ok,
            f"status={event_var}; description={event_desc_var}",
        ),
        _qc(
            "Censor source trace follows specification",
            censor_source_ok,
            f"status={censor_var}; description=SPEC.CENSOR_RULE",
        ),
    ]

    arm_order = {arm: index for index, arm in enumerate(arms)}
    out["_arm_order"] = out["ANLTRT"].map(arm_order)
    out = (
        out.sort_values(["_arm_order", "USUBJID"])
        .drop(columns="_arm_order")
        .reset_index(drop=True)
    )

    qc = pd.DataFrame(qc_rows)
    required = qc.loc[qc["required"]]
    all_required = len(required) > 0 and bool(required["passed"].all())

    arm_counts: dict[str, dict[str, int]] = {}
    for arm in arms:
        arm_frame = out[out["ANLTRT"] == arm]
        arm_counts[arm] = {
            "subjects": int(len(arm_frame)),
            "events": int((arm_frame["CNSR"] == 0).sum()),
            "censored": int((arm_frame["CNSR"] == 1).sum()),
        }

    transition_counts = (
        pd.DataFrame({"planned": planned, "actual": actual})
        .groupby(["planned", "actual"], dropna=False)
        .size()
        .reset_index(name="subjects")
        .sort_values(["planned", "actual"])
        .to_dict(orient="records")
    )
    event_reasons = (
        out.loc[out["CNSR"] == 0, "EVNTDESC"]
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict()
    )
    metrics: dict[str, Any] = {
        "analysis_version": "0.17.0",
        "parameter": paramcd,
        "subjects": int(len(out)),
        "events": int((out["CNSR"] == 0).sum()),
        "censored": int((out["CNSR"] == 1).sum()),
        "min_aval_days": int(pd.to_numeric(out["AVAL"]).min()),
        "max_aval_days": int(pd.to_numeric(out["AVAL"]).max()),
        "analysis_treatment_variable": analysis_trt_var,
        "actual_treatment_context_variable": actual_trt_var,
        "planned_actual_mismatch_subjects": int(treatment_diff.sum()),
        "treatment_transition_counts": transition_counts,
        "event_condition": f"{event_var}={event_value}",
        "censor_condition": f"{censor_var}={censor_value}",
        "event_description_source": event_desc_var,
        "event_description_fallback_source": event_desc_fallback,
        "arm_counts": arm_counts,
        "event_reasons": event_reasons,
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_required,
    }
    return TTEResult(dataset=out, qc=qc, metrics=metrics)

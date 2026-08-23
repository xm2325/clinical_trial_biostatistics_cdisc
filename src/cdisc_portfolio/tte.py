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


def _qc_row(check: str, passed: bool, detail: str, required: bool = True) -> dict[str, Any]:
    return {
        "check": check,
        "passed": bool(passed),
        "required": bool(required),
        "detail": str(detail),
    }


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"ADSL-style input missing required columns: {', '.join(missing)}")


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
    arms = [str(x) for x in population.get("treatment_arms", [])]

    if not param or paramcd != "TTDISC":
        raise ValueError("Retention TTE parameter must define PARAM and PARAMCD=TTDISC")
    if not origin_var or not end_var or not randomised_flag or not randomised_value:
        raise ValueError("Retention TTE population/date specification is incomplete")
    if len(arms) != 3 or len(set(arms)) != 3:
        raise ValueError("Retention TTE specification must define three unique treatment arms")
    if int(event_rule.get("CNSR", -1)) != 0 or int(censor_rule.get("CNSR", -1)) != 1:
        raise ValueError("Retention TTE uses CNSR=0 for events and CNSR=1 for censoring")

    required_columns = [
        "STUDYID",
        "USUBJID",
        "TRT01P",
        "TRT01A",
        "SAFFL",
        randomised_flag,
        origin_var,
        end_var,
        "DCSFL",
        "COMPLFL",
        "EOSDECOD",
        "EOSTERM",
    ]
    _require_columns(adsl, required_columns)

    d = adsl[
        (adsl[randomised_flag].astype(str).str.strip() == randomised_value)
        & adsl["TRT01A"].astype(str).isin(arms)
    ].copy()
    d["STARTDT_PARSED"] = pd.to_datetime(d[origin_var], errors="coerce")
    d["ADT_PARSED"] = pd.to_datetime(d[end_var], errors="coerce")
    d["DCSFL_N"] = d["DCSFL"].fillna("").astype(str).str.strip().str.upper()
    d["COMPLFL_N"] = d["COMPLFL"].fillna("").astype(str).str.strip().str.upper()

    event = d["DCSFL_N"].eq(str(event_rule.get("condition_value", "Y")).upper())
    censored = d["COMPLFL_N"].eq(str(censor_rule.get("condition_value", "Y")).upper())
    partition_ok = event ^ censored

    elapsed = (d["ADT_PARSED"] - d["STARTDT_PARSED"]).dt.days + 1
    event_desc = d["EOSDECOD"].fillna("").astype(str).str.strip()
    fallback = d["EOSTERM"].fillna("").astype(str).str.strip()
    event_desc = event_desc.where(event_desc.ne(""), fallback)
    censor_desc = str(censor_rule.get("EVNTDESC", "STUDY COMPLETED"))

    out = pd.DataFrame(
        {
            "STUDYID": d["STUDYID"].astype(str),
            "USUBJID": d["USUBJID"].astype(str),
            "TRT01P": d["TRT01P"].astype(str),
            "TRT01A": d["TRT01A"].astype(str),
            "SAFFL": d["SAFFL"].astype(str),
            "PARAM": param,
            "PARAMCD": paramcd,
            "STARTDT": d["STARTDT_PARSED"].dt.strftime("%Y-%m-%d"),
            "ADT": d["ADT_PARSED"].dt.strftime("%Y-%m-%d"),
            "AVAL": elapsed,
            "CNSR": np.where(event, 0, 1),
            "EVNTDESC": np.where(event, event_desc, censor_desc),
            "DCSREAS": np.where(event, event_desc, ""),
            "ANL01FL": "Y",
            "SRCDOM": "ADSL",
            "SRCVAR": end_var,
            "STARTSRC": f"ADSL.{origin_var}",
            "ADTSRC": f"ADSL.{end_var}",
        }
    )

    # Evaluate row-wise source/derivation identities before presentation sorting so
    # the QC is invariant to treatment-arm or subject ordering.
    derived_from_output = (
        pd.to_datetime(out["ADT"], errors="coerce")
        - pd.to_datetime(out["STARTDT"], errors="coerce")
    ).dt.days + 1
    aval_formula_ok = bool(
        np.allclose(
            pd.to_numeric(out["AVAL"], errors="coerce").to_numpy(dtype=float),
            pd.to_numeric(derived_from_output, errors="coerce").to_numpy(dtype=float),
            rtol=0.0,
            atol=0.0,
            equal_nan=False,
        )
    )
    event_map_ok = bool((out.loc[event.to_numpy(), "CNSR"] == 0).all())
    censor_map_ok = bool((out.loc[censored.to_numpy(), "CNSR"] == 1).all())

    arm_order = {arm: index for index, arm in enumerate(arms)}
    out["_arm_order"] = out["TRT01A"].map(arm_order)
    out = out.sort_values(["_arm_order", "USUBJID"]).drop(columns="_arm_order").reset_index(drop=True)

    qc_rows: list[dict[str, Any]] = []
    qc_rows.append(_qc_row("Retention population is non-empty", len(out) > 0, f"rows={len(out)}"))
    qc_rows.append(
        _qc_row(
            "Retention population has all three treatment arms",
            set(out["TRT01A"]) == set(arms),
            ", ".join(sorted(out["TRT01A"].unique().tolist())),
        )
    )
    qc_rows.append(
        _qc_row(
            "Retention population has one row per subject",
            not out["USUBJID"].duplicated().any(),
            f"duplicate_subjects={int(out['USUBJID'].duplicated().sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Retention origin dates are complete",
            not d["STARTDT_PARSED"].isna().any(),
            f"missing={int(d['STARTDT_PARSED'].isna().sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Retention event/censor dates are complete",
            not d["ADT_PARSED"].isna().any(),
            f"missing={int(d['ADT_PARSED'].isna().sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Discontinuation and completion flags form an exact partition",
            bool(partition_ok.all()),
            f"invalid_rows={int((~partition_ok).sum())}",
        )
    )
    valid_elapsed = elapsed.notna() & elapsed.ge(1)
    qc_rows.append(
        _qc_row(
            "Retention analysis dates are on or after origin dates",
            bool(valid_elapsed.all()),
            f"invalid_rows={int((~valid_elapsed).sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "ADTTE AVAL equals ADT-STARTDT+1",
            aval_formula_ok,
            f"rows={len(out)}",
        )
    )
    qc_rows.append(
        _qc_row(
            "ADTTE CNSR contains only event=0 and censor=1",
            set(pd.to_numeric(out["CNSR"], errors="coerce").dropna().astype(int)) <= {0, 1},
            f"codes={sorted(out['CNSR'].unique().tolist())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Discontinued subjects map to CNSR=0",
            event_map_ok,
            f"events={int(event.sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Completed subjects map to CNSR=1",
            censor_map_ok,
            f"censored={int(censored.sum())}",
        )
    )
    qc_rows.append(
        _qc_row(
            "Event and censor descriptions are populated",
            bool(out["EVNTDESC"].fillna("").astype(str).str.strip().ne("").all()),
            f"blank={int(out['EVNTDESC'].fillna('').astype(str).str.strip().eq('').sum())}",
        )
    )

    qc = pd.DataFrame(qc_rows)
    required = qc.loc[qc["required"]]
    all_required = len(required) > 0 and bool(required["passed"].all())

    arm_counts: dict[str, dict[str, int]] = {}
    for arm in arms:
        arm_frame = out[out["TRT01A"] == arm]
        arm_counts[arm] = {
            "subjects": int(len(arm_frame)),
            "events": int((arm_frame["CNSR"] == 0).sum()),
            "censored": int((arm_frame["CNSR"] == 1).sum()),
        }

    event_reasons = (
        out.loc[out["CNSR"] == 0, "EVNTDESC"].value_counts().sort_index().astype(int).to_dict()
    )
    metrics: dict[str, Any] = {
        "analysis_version": "0.17.0",
        "parameter": paramcd,
        "subjects": int(len(out)),
        "events": int((out["CNSR"] == 0).sum()),
        "censored": int((out["CNSR"] == 1).sum()),
        "min_aval_days": int(pd.to_numeric(out["AVAL"]).min()),
        "max_aval_days": int(pd.to_numeric(out["AVAL"]).max()),
        "arm_counts": arm_counts,
        "event_reasons": event_reasons,
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_required,
    }
    return TTEResult(dataset=out, qc=qc, metrics=metrics)

from __future__ import annotations

import numpy as np
import pandas as pd


def _to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def _require(df: pd.DataFrame, columns: set[str], domain: str) -> None:
    missing = columns.difference(df.columns)
    if missing:
        raise ValueError(f"{domain} missing required columns: {sorted(missing)}")


def _exposure_subject_summary(ex: pd.DataFrame) -> pd.DataFrame:
    _require(ex, {"STUDYID", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXSTDTC", "EXENDTC"}, "EX")
    x = ex.copy()
    x["EXSTDT"] = _to_date(x["EXSTDTC"])
    x["EXENDT"] = _to_date(x["EXENDTC"])
    x["EXDOSE_NUM"] = pd.to_numeric(x["EXDOSE"], errors="coerce")

    rows: list[dict[str, object]] = []
    for (studyid, usubjid), g in x.groupby(["STUDYID", "USUBJID"], sort=False, dropna=False):
        start = g["EXSTDT"].min()
        end = g["EXENDT"].max()
        duration = (end - start).days + 1 if pd.notna(start) and pd.notna(end) else np.nan
        trts = sorted(g["EXTRT"].dropna().astype(str).str.strip().unique().tolist())
        doses = pd.to_numeric(g["EXDOSE_NUM"], errors="coerce")
        rows.append({
            "STUDYID": studyid,
            "USUBJID": usubjid,
            "TRTSDT_EX": start,
            "TRTEDT_EX": end,
            "EXDURN_RAW": duration,
            "EXN": int(len(g)),
            "EXTRTS": " | ".join(trts),
            "EXDOSE_MAX": float(doses.max()) if doses.notna().any() else np.nan,
            "EXDOSE_MEAN": float(doses.mean()) if doses.notna().any() else np.nan,
        })
    return pd.DataFrame(rows)


def _disposition_subject_summary(ds: pd.DataFrame) -> pd.DataFrame:
    _require(ds, {"STUDYID", "USUBJID", "DSSEQ", "DSDECOD", "DSCAT", "DSSTDTC"}, "DS")
    x = ds.copy()
    x["DSDT"] = _to_date(x["DSSTDTC"])
    x["DSSEQ_NUM"] = pd.to_numeric(x["DSSEQ"], errors="coerce")

    rows: list[dict[str, object]] = []
    for (studyid, usubjid), g in x.groupby(["STUDYID", "USUBJID"], sort=False, dropna=False):
        decod = g["DSDECOD"].fillna("").astype(str).str.strip().str.upper()
        randomized = bool(decod.eq("RANDOMIZED").any())
        completed = bool(decod.eq("COMPLETED").any())

        disp = g.loc[g["DSCAT"].fillna("").astype(str).str.upper().eq("DISPOSITION EVENT")].copy()
        if not disp.empty:
            disp = disp.sort_values(["DSDT", "DSSEQ_NUM"], na_position="first")
            final = disp.iloc[-1]
            eos_decod = str(final.get("DSDECOD", ""))
            eos_term = str(final.get("DSTERM", ""))
            eos_date = final.get("DSDT", pd.NaT)
        else:
            eos_decod = ""
            eos_term = ""
            eos_date = pd.NaT

        rows.append({
            "STUDYID": studyid,
            "USUBJID": usubjid,
            "RAND_DSFL": "Y" if randomized else "N",
            "COMPLFL": "Y" if completed else "N",
            "EOSDECOD": eos_decod,
            "EOSTERM": eos_term,
            "EOSDT": eos_date,
        })
    return pd.DataFrame(rows)


def derive_adsl_style(dm: pd.DataFrame, ex: pd.DataFrame, ds: pd.DataFrame) -> pd.DataFrame:
    """Derive an ADSL-style subject dataset using DM plus observed EX and DS records.

    This is deliberately labelled ADSL-style rather than CDISC-conformant ADaM.
    Safety population is operationally defined as at least one observed EX record.
    """
    _require(
        dm,
        {"STUDYID", "USUBJID", "AGE", "SEX", "RACE", "ARM", "ACTARM", "RFXSTDTC", "RFXENDTC"},
        "DM",
    )
    exposure = _exposure_subject_summary(ex)
    disposition = _disposition_subject_summary(ds)

    adsl = dm.copy()
    adsl["TRT01P"] = adsl["ARM"]
    adsl["TRT01A"] = adsl["ACTARM"]
    adsl["TRTSDT_DM"] = _to_date(adsl["RFXSTDTC"])
    adsl["TRTEDT_DM"] = _to_date(adsl["RFXENDTC"])
    adsl = adsl.merge(exposure, on=["STUDYID", "USUBJID"], how="left", validate="one_to_one")
    adsl = adsl.merge(disposition, on=["STUDYID", "USUBJID"], how="left", validate="one_to_one")

    # EX is used as the source of actual exposure dates when available; DM dates are kept
    # for traceability and QC comparisons. A final DS disposition date is an explicit
    # portfolio fallback when both EX and DM exposure-end dates are unavailable.
    adsl["TRTSDT"] = adsl["TRTSDT_EX"].combine_first(adsl["TRTSDT_DM"])
    adsl["TRTEDT"] = adsl["TRTEDT_EX"].combine_first(adsl["TRTEDT_DM"]).combine_first(adsl["EOSDT"])
    adsl["TRTSDTSRC"] = np.select(
        [adsl["TRTSDT_EX"].notna(), adsl["TRTSDT_DM"].notna()],
        ["EX", "DM_FALLBACK"],
        default="MISSING",
    )
    adsl["TRTEDTSRC"] = np.select(
        [adsl["TRTEDT_EX"].notna(), adsl["TRTEDT_DM"].notna(), adsl["EOSDT"].notna()],
        ["EX", "DM_FALLBACK", "DS_DISPOSITION_FALLBACK"],
        default="MISSING",
    )
    valid_window = adsl["TRTSDT"].notna() & adsl["TRTEDT"].notna() & (adsl["TRTEDT"] >= adsl["TRTSDT"])
    adsl["TRTDURN"] = np.where(valid_window, (adsl["TRTEDT"] - adsl["TRTSDT"]).dt.days + 1, np.nan)
    adsl["RANDFL"] = np.where(adsl["RAND_DSFL"].eq("Y"), "Y", "N")
    adsl["SAFFL"] = np.where(adsl["EXN"].fillna(0).gt(0), "Y", "N")
    adsl["DCSFL"] = np.where(adsl["RANDFL"].eq("Y") & adsl["COMPLFL"].fillna("N").ne("Y"), "Y", "N")

    keep = [
        "STUDYID", "USUBJID", "AGE", "SEX", "RACE", "COUNTRY",
        "TRT01P", "TRT01A", "TRTSDT", "TRTEDT", "TRTSDTSRC", "TRTEDTSRC", "TRTSDT_DM", "TRTEDT_DM",
        "EXDURN_RAW", "TRTDURN", "EXN", "EXTRTS", "EXDOSE_MAX", "EXDOSE_MEAN",
        "RANDFL", "SAFFL", "COMPLFL", "DCSFL", "EOSDECOD", "EOSTERM", "EOSDT",
    ]
    keep = [c for c in keep if c in adsl.columns]
    return adsl[keep].sort_values(["STUDYID", "USUBJID"]).reset_index(drop=True)


def derive_adae_style(ae: pd.DataFrame, adsl: pd.DataFrame, followup_days: int = 30) -> pd.DataFrame:
    _require(ae, {"STUDYID", "USUBJID", "AESEQ", "AEDECOD", "AESTDTC", "AESER"}, "AE")
    subject_cols = ["STUDYID", "USUBJID", "TRT01A", "TRTSDT", "TRTEDT", "SAFFL"]
    out = ae.merge(adsl[subject_cols], on=["STUDYID", "USUBJID"], how="left", validate="many_to_one")
    out["ASTDT"] = _to_date(out["AESTDTC"])
    out["AENDT"] = _to_date(out["AEENDTC"]) if "AEENDTC" in out.columns else pd.NaT

    lower_ok = out["ASTDT"].notna() & out["TRTSDT"].notna() & (out["ASTDT"] >= out["TRTSDT"])
    upper_bound = out["TRTEDT"] + pd.to_timedelta(followup_days, unit="D")
    upper_ok = out["TRTEDT"].isna() | (out["ASTDT"] <= upper_bound)
    # ADaM single-value analysis flags are populated with Y for qualifying records
    # and left blank otherwise. This preserves an unambiguous TEAE subset while
    # avoiding a non-standard explicit N value for TRTEMFL.
    out["TRTEMFL"] = np.where(lower_ok & upper_ok & out["SAFFL"].eq("Y"), "Y", "")

    if "AESTDY" in out.columns:
        out["ASTDY"] = pd.to_numeric(out["AESTDY"], errors="coerce")
    else:
        delta = (out["ASTDT"] - out["TRTSDT"]).dt.days
        out["ASTDY"] = np.where(delta >= 0, delta + 1, delta)

    rel = out.get("AEREL", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    out["RELFL"] = np.where(rel.isin({"POSSIBLE", "PROBABLE", "DEFINITE", "RELATED"}), "Y", "N")
    sev = out.get("AESEV", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    out["MODSEVFL"] = np.where(sev.isin({"MODERATE", "SEVERE"}), "Y", "N")

    keep = [
        "STUDYID", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AEBODSYS",
        "AESEV", "AESER", "AEREL", "AEOUT", "ASTDT", "AENDT", "ASTDY",
        "TRT01A", "TRTSDT", "TRTEDT", "SAFFL", "TRTEMFL", "RELFL", "MODSEVFL",
    ]
    keep = [c for c in keep if c in out.columns]
    return out[keep].sort_values(["STUDYID", "USUBJID", "AESEQ"]).reset_index(drop=True)

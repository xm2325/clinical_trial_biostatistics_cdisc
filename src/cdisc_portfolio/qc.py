from __future__ import annotations

import pandas as pd


def run_qc(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    def add(name: str, passed: bool, detail: str, required: bool = True) -> None:
        checks.append({"check": name, "passed": bool(passed), "required": bool(required), "detail": detail})

    adsl_dups = int(adsl.duplicated(["STUDYID", "USUBJID"]).sum())
    add("ADSL-style subject key unique", adsl_dups == 0, f"duplicate keys={adsl_dups}")

    ae_dups = int(adae.duplicated(["STUDYID", "USUBJID", "AESEQ"]).sum())
    add("ADAE-style AE key unique", ae_dups == 0, f"duplicate keys={ae_dups}")

    adsl_ids = set(adsl["USUBJID"].astype(str))
    ae_ids = set(adae["USUBJID"].astype(str))
    missing_ids = ae_ids.difference(adsl_ids)
    add("All AE subjects present in subject analysis dataset", not missing_ids, f"missing subject ids={len(missing_ids)}")

    bad_saf = sorted(set(adsl["SAFFL"].dropna()) - {"Y", "N"})
    add("SAFFL valid values", not bad_saf, f"invalid={bad_saf}")

    bad_te = sorted(set(adae["TRTEMFL"].dropna()) - {"Y", "N"})
    add("TRTEMFL valid values", not bad_te, f"invalid={bad_te}")

    safety_without_ex = int((adsl["SAFFL"].eq("Y") & adsl["EXN"].fillna(0).le(0)).sum())
    add("Safety population has observed exposure", safety_without_ex == 0, f"subjects={safety_without_ex}")

    bad_ex_dates = int((adsl["SAFFL"].eq("Y") & (adsl["TRTSDT"].isna() | adsl["TRTEDT"].isna())).sum())
    add("Safety subjects have exposure start/end dates", bad_ex_dates == 0, f"subjects={bad_ex_dates}")

    reverse_dates = int((adsl["TRTSDT"].notna() & adsl["TRTEDT"].notna() & (adsl["TRTEDT"] < adsl["TRTSDT"])).sum())
    add("Exposure end is not before exposure start", reverse_dates == 0, f"subjects={reverse_dates}")

    rand_missing_ds = int((adsl["RANDFL"].eq("Y") & adsl["EOSDECOD"].fillna("").eq("")).sum())
    add("Randomised subjects have a disposition event", rand_missing_ds == 0, f"subjects={rand_missing_ds}")

    completed_but_dc = int((adsl["COMPLFL"].eq("Y") & adsl["DCSFL"].eq("Y")).sum())
    add("Completed and discontinued flags are mutually exclusive", completed_but_dc == 0, f"subjects={completed_but_dc}")

    missing_start = int(adae["ASTDT"].isna().sum())
    add("AE missing start dates quantified", True, f"missing ASTDT={missing_start}", required=False)

    teae_without_safety = int(((adae["TRTEMFL"] == "Y") & (adae["SAFFL"] != "Y")).sum())
    add("No TEAE outside safety population", teae_without_safety == 0, f"records={teae_without_safety}")

    pre_exposure_teae = int(((adae["TRTEMFL"] == "Y") & (adae["ASTDT"] < adae["TRTSDT"])).sum())
    add("No TEAE before first exposure", pre_exposure_teae == 0, f"records={pre_exposure_teae}")

    beyond_followup = int(((adae["TRTEMFL"] == "Y") & adae["TRTEDT"].notna() & (adae["ASTDT"] > adae["TRTEDT"] + pd.Timedelta(days=30))).sum())
    add("No TEAE after 30-day follow-up window", beyond_followup == 0, f"records={beyond_followup}")

    return pd.DataFrame(checks)

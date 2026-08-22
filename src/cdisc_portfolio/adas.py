from __future__ import annotations

import numpy as np
import pandas as pd

ADAS11_ITEM_CODES = [
    "ACITM01", "ACITM02", "ACITM04", "ACITM05", "ACITM06", "ACITM07",
    "ACITM08", "ACITM11", "ACITM12", "ACITM13", "ACITM14",
]
ADAS_WINDOWS = [
    ("Week 8", 8, 56, 2, 84),
    ("Week 16", 16, 112, 85, 140),
    ("Week 24", 24, 168, 141, None),
]


def _require(df: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns.difference(df.columns)
    if missing:
        raise ValueError(f"{name} missing required columns: {sorted(missing)}")


def _recomputed_actot_source(qs: pd.DataFrame) -> pd.DataFrame:
    """Recalculate ADAS-Cog(11) total from its 11 item records at each source visit.

    The official SDTM QS domain contains an ACTOT record, but the portfolio
    reconstruction recalculates the total from the 11 component items so the
    total derivation is independently checkable.
    """
    required = {
        "STUDYID", "USUBJID", "QSSEQ", "QSTESTCD", "QSSTRESN", "QSBLFL",
        "VISITNUM", "VISIT", "QSDY", "QSDTC",
    }
    _require(qs, required, "QS")

    x = qs.copy()
    x["QSTESTCD_U"] = x["QSTESTCD"].fillna("").astype(str).str.upper()
    x["QSSTRESN_NUM"] = pd.to_numeric(x["QSSTRESN"], errors="coerce")
    x["QSDY_NUM"] = pd.to_numeric(x["QSDY"], errors="coerce")
    x["VISITNUM_NUM"] = pd.to_numeric(x["VISITNUM"], errors="coerce")

    items = x.loc[x["QSTESTCD_U"].isin(ADAS11_ITEM_CODES)].copy()
    group = ["STUDYID", "USUBJID", "VISITNUM_NUM", "VISIT", "QSDY_NUM", "QSDTC"]
    item_summary = (
        items.groupby(group, dropna=False)
        .agg(
            ITEM_N=("QSTESTCD_U", "nunique"),
            AVAL_RECALC=("QSSTRESN_NUM", lambda s: s.sum(min_count=1)),
        )
        .reset_index()
    )
    item_summary.loc[item_summary["ITEM_N"].ne(len(ADAS11_ITEM_CODES)), "AVAL_RECALC"] = np.nan

    actot = x.loc[x["QSTESTCD_U"].eq("ACTOT")].copy()
    actot = actot.rename(columns={
        "QSSEQ": "QSSEQ_ACTOT",
        "QSSTRESN_NUM": "AVAL_SDTM_ACTOT",
        "QSBLFL": "QSBLFL_ACTOT",
    })
    keep = group + ["QSSEQ_ACTOT", "AVAL_SDTM_ACTOT", "QSBLFL_ACTOT"]
    source = actot[keep].merge(item_summary, on=group, how="left", validate="one_to_one")
    source["AVAL"] = source["AVAL_RECALC"].combine_first(source["AVAL_SDTM_ACTOT"])
    source["ADT"] = pd.to_datetime(source["QSDTC"], errors="coerce").dt.normalize()
    return source.sort_values(["STUDYID", "USUBJID", "QSDY_NUM", "QSSEQ_ACTOT"]).reset_index(drop=True)


def derive_adqsadas_actot_analysis_style(qs: pd.DataFrame, adsl: pd.DataFrame) -> pd.DataFrame:
    """Derive the selected ACTOT analysis records used for reference validation.

    One baseline and one selected record for Week 8, Week 16 and Week 24 are
    generated per subject. Observed records are selected by analysis windows and
    distance to target day. If a window has no observation, the latest prior
    record is carried forward and marked DTYPE=LOCF.
    """
    _require(adsl, {"STUDYID", "USUBJID", "TRT01P", "RANDFL"}, "ADSL-style")
    source = _recomputed_actot_source(qs)
    subj = adsl[["STUDYID", "USUBJID", "TRT01P", "RANDFL"]].drop_duplicates()
    source = source.merge(subj, on=["STUDYID", "USUBJID"], how="inner", validate="many_to_one")
    source = source.loc[source["RANDFL"].eq("Y")].copy()

    post_subjects = set(
        source.loc[source["QSDY_NUM"].gt(1) & source["AVAL"].notna(), ["STUDYID", "USUBJID"]]
        .drop_duplicates().itertuples(index=False, name=None)
    )
    rows: list[dict[str, object]] = []
    for (studyid, usubjid), g in source.groupby(["STUDYID", "USUBJID"], sort=False):
        g = g.sort_values(["QSDY_NUM", "QSSEQ_ACTOT"])
        trtp = str(g["TRT01P"].iloc[0])
        efffl = "Y" if (studyid, usubjid) in post_subjects else "N"
        baseline = g.loc[
            g["QSBLFL_ACTOT"].fillna("").astype(str).str.upper().eq("Y") & g["AVAL"].notna()
        ].copy()
        if baseline.empty:
            baseline = g.loc[g["QSDY_NUM"].le(1) & g["AVAL"].notna()].copy()
        if baseline.empty:
            continue
        b = baseline.sort_values(["QSDY_NUM", "QSSEQ_ACTOT"]).iloc[-1]
        base = float(b["AVAL"])

        def make_row(chosen: pd.Series, avisit: str, avisitn: int, target: int, lo, hi, dtype: str, ablfl: str = ""):
            aval = float(chosen["AVAL"])
            chg = np.nan if ablfl == "Y" else aval - base
            pchg = np.nan if ablfl == "Y" or base == 0 else 100.0 * chg / base
            if avisit == "Baseline":
                awrange, awlo, awhi = "<=1", np.nan, 1
            else:
                awrange = f">{lo - 1}" if hi is None else f"{lo}-{hi}"
                awlo, awhi = lo, hi
            return {
                "STUDYID": studyid,
                "USUBJID": usubjid,
                "TRTP": trtp,
                "EFFFL": efffl,
                "AVISIT": avisit,
                "AVISITN": avisitn,
                "VISIT": chosen["VISIT"],
                "VISITNUM": chosen["VISITNUM_NUM"],
                "ADY": chosen["QSDY_NUM"],
                "ADT": chosen["ADT"],
                "PARAMCD": "ACTOT",
                "PARAM": "Adas-Cog(11) Subscore",
                "AVAL": aval,
                "BASE": base,
                "CHG": chg,
                "PCHG": pchg,
                "ABLFL": ablfl,
                "ANL01FL": "Y",
                "DTYPE": dtype,
                "AWRANGE": awrange,
                "AWTARGET": target,
                "AWTDIFF": abs(float(chosen["QSDY_NUM"]) - target),
                "AWLO": awlo,
                "AWHI": awhi,
                "AWU": "DAYS",
                "QSSEQ": chosen["QSSEQ_ACTOT"],
                "ITEM_N": chosen["ITEM_N"],
                "AVAL_SDTM_ACTOT": chosen["AVAL_SDTM_ACTOT"],
                "AVAL_RECALC": chosen["AVAL_RECALC"],
            }

        rows.append(make_row(b, "Baseline", 0, 1, None, 1, "", "Y"))
        for avisit, avisitn, target, lo, hi in ADAS_WINDOWS:
            post = g.loc[g["QSDY_NUM"].gt(1) & g["AVAL"].notna()].copy()
            if hi is None:
                candidates = post.loc[post["QSDY_NUM"].ge(lo)].copy()
            else:
                candidates = post.loc[post["QSDY_NUM"].between(lo, hi, inclusive="both")].copy()
            dtype = ""
            if not candidates.empty:
                candidates["DIST"] = (candidates["QSDY_NUM"] - target).abs()
                chosen = candidates.sort_values(["DIST", "QSDY_NUM", "QSSEQ_ACTOT"]).iloc[0]
            else:
                prior = g.loc[g["QSDY_NUM"].lt(lo) & g["AVAL"].notna()].copy()
                if prior.empty:
                    continue
                chosen = prior.sort_values(["QSDY_NUM", "QSSEQ_ACTOT"]).iloc[-1]
                dtype = "LOCF"
            rows.append(make_row(chosen, avisit, avisitn, target, lo, hi, dtype))

    return pd.DataFrame(rows).sort_values(["STUDYID", "USUBJID", "AVISITN"]).reset_index(drop=True)


def compare_actot_analysis_reference(derived: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare selected source-derived ACTOT records with official ADQSADAS ANL01FL=Y rows."""
    r = reference.loc[
        reference["PARAMCD"].fillna("").astype(str).str.upper().eq("ACTOT")
        & reference["ANL01FL"].fillna("").astype(str).str.upper().eq("Y")
    ].copy()
    key = ["USUBJID", "AVISIT"]
    cols = ["AVAL", "BASE", "CHG", "DTYPE", "QSSEQ"]
    d2 = derived[key + cols].rename(columns={c: f"{c}_DER" for c in cols})
    r2 = r[key + cols].rename(columns={c: f"{c}_REF" for c in cols})
    detail = r2.merge(d2, on=key, how="outer", indicator=True)
    overlap = detail["_merge"].eq("both")
    for c in ["DTYPE_DER", "DTYPE_REF"]:
        detail[c] = detail[c].fillna("").astype(str)
    for c in ["AVAL", "BASE", "CHG"]:
        detail[f"{c}_MATCH"] = overlap & np.isclose(
            pd.to_numeric(detail[f"{c}_DER"], errors="coerce"),
            pd.to_numeric(detail[f"{c}_REF"], errors="coerce"),
            equal_nan=True,
        )
    detail["DTYPE_MATCH"] = overlap & detail["DTYPE_DER"].eq(detail["DTYPE_REF"])
    detail["QSSEQ_MATCH"] = overlap & (
        pd.to_numeric(detail["QSSEQ_DER"], errors="coerce")
        == pd.to_numeric(detail["QSSEQ_REF"], errors="coerce")
    )
    n_ref = len(r2)
    n_overlap = int(overlap.sum())
    denom = max(n_overlap, 1)
    metrics = {
        "reference_rows": int(n_ref),
        "derived_rows": int(len(d2)),
        "overlap_rows": n_overlap,
        "reference_key_coverage": n_overlap / n_ref if n_ref else np.nan,
        "derived_extra_rows": int(detail["_merge"].eq("right_only").sum()),
        "reference_missing_rows": int(detail["_merge"].eq("left_only").sum()),
    }
    for c in ["AVAL", "BASE", "CHG"]:
        metrics[f"{c.lower()}_match_rate_on_overlap"] = float(detail.loc[overlap, f"{c}_MATCH"].sum()) / denom
    metrics["dtype_match_rate_on_overlap"] = float(detail.loc[overlap, "DTYPE_MATCH"].sum()) / denom
    metrics["qsseq_match_rate_on_overlap"] = float(detail.loc[overlap, "QSSEQ_MATCH"].sum()) / denom
    return pd.DataFrame([metrics]), detail

from __future__ import annotations

import json
import numpy as np
import pandas as pd


def compare_adqscibc_reference(derived: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare portfolio ADQSCIBC-style rows with the public CDISC reference ADaM."""
    required = {"USUBJID", "AVISIT", "AVAL", "DTYPE", "QSSEQ"}
    for name, df in [("derived ADQSCIBC-style", derived), ("reference ADQSCIBC", reference)]:
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"{name} missing columns: {sorted(missing)}")

    d = derived.copy()
    r = reference.copy()
    if "ANL01FL" in r.columns:
        r = r.loc[r["ANL01FL"].fillna("").astype(str).str.upper().eq("Y")].copy()

    key = ["USUBJID", "AVISIT"]
    d = d.sort_values(key).drop_duplicates(key, keep="first")
    r = r.sort_values(key).drop_duplicates(key, keep="first")
    d2 = d[key + ["AVAL", "DTYPE", "QSSEQ"]].rename(
        columns={"AVAL": "AVAL_DER", "DTYPE": "DTYPE_DER", "QSSEQ": "QSSEQ_DER"}
    )
    r2 = r[key + ["AVAL", "DTYPE", "QSSEQ"]].rename(
        columns={"AVAL": "AVAL_REF", "DTYPE": "DTYPE_REF", "QSSEQ": "QSSEQ_REF"}
    )
    detail = r2.merge(d2, on=key, how="outer", indicator=True)
    overlap = detail["_merge"].eq("both")
    for col in ["DTYPE_DER", "DTYPE_REF"]:
        detail[col] = detail[col].fillna("").astype(str)
    detail["AVAL_MATCH"] = overlap & np.isclose(
        pd.to_numeric(detail["AVAL_DER"], errors="coerce"),
        pd.to_numeric(detail["AVAL_REF"], errors="coerce"),
        equal_nan=True,
    )
    detail["DTYPE_MATCH"] = overlap & detail["DTYPE_DER"].eq(detail["DTYPE_REF"])
    detail["QSSEQ_MATCH"] = overlap & (
        pd.to_numeric(detail["QSSEQ_DER"], errors="coerce")
        == pd.to_numeric(detail["QSSEQ_REF"], errors="coerce")
    )

    n_ref = int(len(r2))
    n_der = int(len(d2))
    n_overlap = int(overlap.sum())
    denom = max(n_overlap, 1)
    metrics = pd.DataFrame([{
        "reference_rows": n_ref,
        "derived_rows": n_der,
        "overlap_rows": n_overlap,
        "reference_key_coverage": n_overlap / n_ref if n_ref else np.nan,
        "derived_extra_rows": int(detail["_merge"].eq("right_only").sum()),
        "reference_missing_rows": int(detail["_merge"].eq("left_only").sum()),
        "aval_match_rate_on_overlap": float(detail.loc[overlap, "AVAL_MATCH"].sum()) / denom,
        "dtype_match_rate_on_overlap": float(detail.loc[overlap, "DTYPE_MATCH"].sum()) / denom,
        "qsseq_match_rate_on_overlap": float(detail.loc[overlap, "QSSEQ_MATCH"].sum()) / denom,
    }])
    return metrics, detail


def trace_adqscibc_value_mismatches(qs: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    """Trace every reference AVAL mismatch back to the selected official SDTM QS row."""
    required_qs = {"USUBJID", "QSSEQ", "QSTESTCD", "QSSTRESN"}
    missing = required_qs.difference(qs.columns)
    if missing:
        raise ValueError(f"QS missing columns for CIBIC source trace: {sorted(missing)}")

    mism = detail.loc[detail["_merge"].eq("both") & ~detail["AVAL_MATCH"]].copy()
    if mism.empty:
        return mism

    source_cols = [
        "USUBJID", "QSSEQ", "QSTESTCD", "QSTEST", "QSCAT", "QSORRES",
        "QSSTRESC", "QSSTRESN", "VISIT", "VISITNUM", "QSDY", "QSDTC",
    ]
    source_cols = [c for c in source_cols if c in qs.columns]
    src = qs.loc[
        qs["QSTESTCD"].fillna("").astype(str).str.upper().eq("CIBIC"), source_cols
    ].copy()
    src["QSSEQ_JOIN"] = pd.to_numeric(src["QSSEQ"], errors="coerce")
    mism["QSSEQ_JOIN"] = pd.to_numeric(mism["QSSEQ_DER"], errors="coerce")
    out = mism.merge(
        src.drop(columns=["QSSEQ"]).drop_duplicates(["USUBJID", "QSSEQ_JOIN"]),
        on=["USUBJID", "QSSEQ_JOIN"],
        how="left",
        validate="many_to_one",
    )
    src_val = pd.to_numeric(out.get("QSSTRESN"), errors="coerce")
    der_val = pd.to_numeric(out["AVAL_DER"], errors="coerce")
    ref_val = pd.to_numeric(out["AVAL_REF"], errors="coerce")
    out["DERIVED_EQUALS_SOURCE"] = np.isclose(der_val, src_val, equal_nan=True)
    out["REFERENCE_EQUALS_SOURCE"] = np.isclose(ref_val, src_val, equal_nan=True)
    return out.sort_values(["USUBJID", "AVISIT"]).reset_index(drop=True)


def profile_adqsadas_reference(reference: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create compact, inspectable summaries of the official ADQSADAS reference dataset."""
    profile: dict[str, object] = {
        "rows": int(len(reference)),
        "columns": reference.columns.tolist(),
        "unique_subjects": int(reference["USUBJID"].nunique()) if "USUBJID" in reference else None,
    }
    for col in ["EFFFL", "ANL01FL", "ABLFL", "DTYPE"]:
        if col in reference.columns:
            counts = reference[col].fillna("<MISSING>").astype(str).value_counts(dropna=False)
            profile[f"{col}_counts"] = {str(k): int(v) for k, v in counts.items()}

    param_cols = [c for c in ["PARAMCD", "PARAM"] if c in reference.columns]
    if param_cols:
        param_counts = (
            reference.groupby(param_cols, dropna=False).size().reset_index(name="records")
            .sort_values("records", ascending=False).reset_index(drop=True)
        )
    else:
        param_counts = pd.DataFrame(columns=["PARAMCD", "PARAM", "records"])

    visit_cols = [c for c in ["PARAMCD", "AVISIT", "AVISITN", "DTYPE"] if c in reference.columns]
    if visit_cols:
        visit_counts = (
            reference.groupby(visit_cols, dropna=False).size().reset_index(name="records")
            .sort_values([c for c in ["PARAMCD", "AVISITN", "AVISIT"] if c in visit_cols])
            .reset_index(drop=True)
        )
    else:
        visit_counts = pd.DataFrame(columns=["records"])

    sample_cols = [
        c for c in [
            "USUBJID", "TRTP", "EFFFL", "PARAMCD", "PARAM", "AVISIT", "AVISITN",
            "ABLFL", "BASE", "AVAL", "CHG", "ANL01FL", "DTYPE", "QSSEQ", "ADY", "ADT",
        ] if c in reference.columns
    ]
    if "PARAMCD" in reference.columns:
        samples = reference[sample_cols].groupby("PARAMCD", group_keys=False).head(4).reset_index(drop=True)
    else:
        samples = reference[sample_cols].head(20).reset_index(drop=True)
    return profile, param_counts, visit_counts, samples

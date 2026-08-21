from __future__ import annotations

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

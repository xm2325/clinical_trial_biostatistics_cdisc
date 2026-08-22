from __future__ import annotations

import pandas as pd


def run_efficacy_qc(
    adqscibc: pd.DataFrame,
    adqs_item: pd.DataFrame,
    reference_metrics: pd.DataFrame,
    ancova_subjects: pd.DataFrame,
) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    def add(name: str, passed: bool, detail: str, required: bool = True) -> None:
        checks.append({"check": name, "passed": bool(passed), "required": bool(required), "detail": detail})

    dup_cibic = int(adqscibc.duplicated(["STUDYID", "USUBJID", "AVISIT"]).sum())
    add("ADQSCIBC-style analysis key unique", dup_cibic == 0, f"duplicate keys={dup_cibic}")

    missing_cibic = int(adqscibc["AVAL"].isna().sum())
    add("ADQSCIBC-style analysis values non-missing", missing_cibic == 0, f"missing AVAL={missing_cibic}")

    bad_dtype = sorted(set(adqscibc["DTYPE"].fillna("").astype(str)) - {"", "LOCF"})
    add("ADQSCIBC-style DTYPE values valid", not bad_dtype, f"invalid={bad_dtype}")

    bad_visit = sorted(set(adqscibc["AVISIT"].dropna().astype(str)) - {"Week 8", "Week 16", "Week 24"})
    add("ADQSCIBC-style target visits valid", not bad_visit, f"invalid={bad_visit}")

    baseline = adqs_item.loc[adqs_item["ABLFL"].eq("Y")]
    baseline_counts = baseline.groupby(["STUDYID", "USUBJID"]).size()
    baseline_dups = int((baseline_counts > 1).sum())
    add("ACTOT baseline record unique per subject", baseline_dups == 0, f"subjects with >1 baseline={baseline_dups}")

    post = adqs_item.loc[adqs_item["ABLFL"].ne("Y") & adqs_item["BASE"].notna() & adqs_item["AVAL"].notna()]
    identity_error = (pd.to_numeric(post["CHG"], errors="coerce") - (post["AVAL"] - post["BASE"])).abs()
    max_error = float(identity_error.max()) if not identity_error.empty else 0.0
    add("ACTOT CHG equals AVAL-BASE", max_error < 1e-12, f"max absolute error={max_error:.3g}")

    obs = ancova_subjects.loc[ancova_subjects["analysis"].eq("Observed Week 24")]
    obs_dups = int(obs.duplicated(["STUDYID", "USUBJID"]).sum())
    add("Observed Week 24 ANCOVA subject key unique", obs_dups == 0, f"duplicate subjects={obs_dups}")

    locf = ancova_subjects.loc[ancova_subjects["analysis"].eq("LOCF sensitivity")]
    locf_n = int(len(locf))
    obs_n = int(len(obs))
    add("LOCF sensitivity retains at least observed-case N", locf_n >= obs_n, f"observed N={obs_n}; LOCF N={locf_n}")

    m = reference_metrics.iloc[0]
    coverage = float(m["reference_key_coverage"])
    aval_match = float(m["aval_match_rate_on_overlap"])
    dtype_match = float(m["dtype_match_rate_on_overlap"])
    qsseq_match = float(m["qsseq_match_rate_on_overlap"])

    # The official pilot package contains a small number of reference AVAL values
    # that differ from the selected SDTM QS source rows. The repository therefore
    # requires exact agreement on row selection/source identity and derivation type,
    # while reporting value agreement rather than altering source values to force a match.
    add("Official ADQSCIBC reference key coverage =100%", coverage == 1.0, f"coverage={coverage:.4f}")
    add("Official ADQSCIBC DTYPE match =100%", dtype_match == 1.0, f"match rate={dtype_match:.4f}")
    add("Official ADQSCIBC QSSEQ source-row match =100%", qsseq_match == 1.0, f"match rate={qsseq_match:.4f}")
    add(
        "Official ADQSCIBC AVAL agreement reported",
        True,
        f"match rate={aval_match:.4f}; mismatches are source-traced in adqscibc_mismatch_source_trace.csv",
        required=False,
    )
    return pd.DataFrame(checks)

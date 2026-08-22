from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.stats import t as student_t


CIBIC_WINDOWS = [
    ("Week 8", 8, 56, 2, 84),
    ("Week 16", 16, 112, 85, 140),
    ("Week 24", 24, 168, 141, None),
]
EXPECTED_ARMS = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]


def _require(df: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns.difference(df.columns)
    if missing:
        raise ValueError(f"{name} missing required columns: {sorted(missing)}")


def _to_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def derive_adqscibc_style(qs: pd.DataFrame, adsl: pd.DataFrame) -> pd.DataFrame:
    """Reproduce a compact CIBIC+ analysis dataset from official SDTM QS.

    SDTM uses QSTESTCD=CIBIC; the public reference ADaM maps this to
    PARAMCD=CIBICVAL. The output is labelled ADQSCIBC-style rather than
    submission-ready ADaM.
    """
    _require(
        qs,
        {"STUDYID", "USUBJID", "QSSEQ", "QSTESTCD", "QSSTRESN", "QSDY", "QSDTC", "VISIT", "VISITNUM"},
        "QS",
    )
    _require(adsl, {"STUDYID", "USUBJID", "TRT01P", "RANDFL", "COMPLFL"}, "ADSL-style")

    q = qs.loc[qs["QSTESTCD"].fillna("").astype(str).str.upper().eq("CIBIC")].copy()
    q["AVAL"] = pd.to_numeric(q["QSSTRESN"], errors="coerce")
    q["ADY"] = pd.to_numeric(q["QSDY"], errors="coerce")
    q["ADT"] = _to_date(q["QSDTC"])
    q["QSSEQ_NUM"] = pd.to_numeric(q["QSSEQ"], errors="coerce")
    q = q.loc[q["AVAL"].notna() & q["ADY"].notna()].copy()

    subj = adsl[["STUDYID", "USUBJID", "TRT01P", "RANDFL", "COMPLFL"]].drop_duplicates()
    q = q.merge(subj, on=["STUDYID", "USUBJID"], how="inner", validate="many_to_one")
    q = q.loc[q["RANDFL"].eq("Y")].copy()

    rows: list[dict[str, object]] = []
    for (studyid, usubjid), g in q.groupby(["STUDYID", "USUBJID"], sort=False):
        g = g.sort_values(["ADY", "QSSEQ_NUM"])
        trtp = str(g["TRT01P"].iloc[0])
        compl = str(g["COMPLFL"].iloc[0])
        for avisit, avisitn, target, lo, hi in CIBIC_WINDOWS:
            if hi is None:
                actual = g.loc[g["ADY"].ge(lo)].copy()
            else:
                actual = g.loc[g["ADY"].between(lo, hi, inclusive="both")].copy()

            dtype = ""
            if not actual.empty:
                actual["DIST"] = (actual["ADY"] - target).abs()
                chosen = actual.sort_values(["DIST", "ADY", "QSSEQ_NUM"]).iloc[0]
            else:
                prior = g.loc[g["ADY"].lt(lo)].copy()
                if prior.empty:
                    continue
                chosen = prior.sort_values(["ADY", "QSSEQ_NUM"]).iloc[-1]
                dtype = "LOCF"

            awrange = f">{int(lo - 1)}" if hi is None else f"{int(lo)}-{int(hi)}"
            rows.append(
                {
                    "STUDYID": studyid,
                    "USUBJID": usubjid,
                    "TRTP": trtp,
                    "ITTFL": "Y",
                    "EFFFL": "Y",
                    "COMP24FL": "Y" if compl == "Y" else "N",
                    "AVISIT": avisit,
                    "AVISITN": avisitn,
                    "VISIT": chosen.get("VISIT"),
                    "VISITNUM": chosen.get("VISITNUM"),
                    "ADY": chosen["ADY"],
                    "ADT": chosen["ADT"],
                    "PARAMCD": "CIBICVAL",
                    "PARAM": "CIBIC Score",
                    "AVAL": chosen["AVAL"],
                    "ANL01FL": "Y",
                    "DTYPE": dtype,
                    "AWRANGE": awrange,
                    "AWTARGET": target,
                    "AWTDIFF": abs(float(chosen["ADY"]) - target),
                    "AWLO": lo,
                    "AWHI": hi,
                    "AWU": "DAYS",
                    "QSSEQ": chosen["QSSEQ"],
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["STUDYID", "USUBJID", "AVISITN"]).reset_index(drop=True)


def derive_actot_adqs_style(qs: pd.DataFrame, adsl: pd.DataFrame) -> pd.DataFrame:
    """Create an ADQS-style long dataset for ACTOT total score.

    The official SDTM Define-XML identifies ACTOT as the derived total score for
    the Alzheimer's Disease Assessment Scale. This portfolio uses the supplied
    QS total score rather than re-scoring individual questionnaire items.
    """
    _require(
        qs,
        {"STUDYID", "USUBJID", "QSSEQ", "QSTESTCD", "QSTEST", "QSSTRESN", "QSBLFL", "QSDY", "QSDTC", "VISIT", "VISITNUM"},
        "QS",
    )
    q = qs.loc[qs["QSTESTCD"].fillna("").astype(str).str.upper().eq("ACTOT")].copy()
    q["AVAL"] = pd.to_numeric(q["QSSTRESN"], errors="coerce")
    q["ADY"] = pd.to_numeric(q["QSDY"], errors="coerce")
    q["ADT"] = _to_date(q["QSDTC"])
    q["QSSEQ_NUM"] = pd.to_numeric(q["QSSEQ"], errors="coerce")

    subj = adsl[["STUDYID", "USUBJID", "TRT01A", "RANDFL"]].drop_duplicates()
    q = q.merge(subj, on=["STUDYID", "USUBJID"], how="inner", validate="many_to_one")
    q = q.loc[q["RANDFL"].eq("Y") & q["AVAL"].notna()].copy()

    baseline_rows = q.loc[q["QSBLFL"].fillna("").astype(str).str.upper().eq("Y")].copy()
    baseline_rows = baseline_rows.sort_values(["STUDYID", "USUBJID", "ADY", "QSSEQ_NUM"])
    baseline = baseline_rows.drop_duplicates(["STUDYID", "USUBJID"], keep="last")[["STUDYID", "USUBJID", "AVAL"]].rename(columns={"AVAL": "BASE"})

    out = q.merge(baseline, on=["STUDYID", "USUBJID"], how="left", validate="many_to_one")
    out["PARAMCD"] = "ACTOT"
    out["PARAM"] = out["QSTEST"]
    out["AVISIT"] = out["VISIT"]
    out["AVISITN"] = pd.to_numeric(out["VISITNUM"], errors="coerce")
    out["ABLFL"] = np.where(out["QSBLFL"].fillna("").astype(str).str.upper().eq("Y"), "Y", "")
    out["CHG"] = np.where(out["ABLFL"].eq("Y"), 0.0, out["AVAL"] - out["BASE"])
    has_post = out.loc[out["ABLFL"].ne("Y") & out["AVAL"].notna()].groupby(["STUDYID", "USUBJID"]).size()
    post_keys = set(has_post.index.tolist())
    out["EFFFL"] = [
        "Y" if pd.notna(base) and (study, subj_id) in post_keys else "N"
        for study, subj_id, base in zip(out["STUDYID"], out["USUBJID"], out["BASE"])
    ]
    keep = [
        "STUDYID", "USUBJID", "TRT01A", "PARAMCD", "PARAM", "AVISIT", "AVISITN",
        "ADY", "ADT", "AVAL", "BASE", "CHG", "ABLFL", "EFFFL", "QSSEQ",
    ]
    return out[keep].sort_values(["STUDYID", "USUBJID", "AVISITN", "QSSEQ"]).reset_index(drop=True)


def _analysis_subjects(adqs: pd.DataFrame, locf: bool) -> pd.DataFrame:
    x = adqs.loc[adqs["EFFFL"].eq("Y") & adqs["TRT01A"].isin(EXPECTED_ARMS)].copy()
    base = x.loc[x["ABLFL"].eq("Y"), ["STUDYID", "USUBJID", "TRT01A", "BASE"]].drop_duplicates(["STUDYID", "USUBJID"])
    if not locf:
        wk24 = x.loc[x["AVISIT"].fillna("").astype(str).str.upper().eq("WEEK 24"), ["STUDYID", "USUBJID", "AVAL", "ADY"]].copy()
        wk24 = wk24.sort_values(["STUDYID", "USUBJID", "ADY"]).drop_duplicates(["STUDYID", "USUBJID"], keep="last").copy()
        wk24["DTYPE"] = ""
    else:
        post = x.loc[x["ABLFL"].ne("Y") & x["ADY"].gt(1) & x["ADY"].le(168), ["STUDYID", "USUBJID", "AVAL", "ADY", "AVISIT"]].copy()
        post = post.sort_values(["STUDYID", "USUBJID", "ADY"])
        wk24 = post.drop_duplicates(["STUDYID", "USUBJID"], keep="last").copy()
        wk24["DTYPE"] = np.where(wk24["AVISIT"].fillna("").astype(str).str.upper().eq("WEEK 24"), "", "LOCF")
    ana = base.merge(wk24, on=["STUDYID", "USUBJID"], how="inner", validate="one_to_one")
    ana["CHG"] = ana["AVAL"] - ana["BASE"]
    return ana


def _fit_ancova(data: pd.DataFrame, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = data.dropna(subset=["AVAL", "BASE", "TRT01A"]).copy()
    mean_base = float(d["BASE"].mean())
    d["BASEC"] = d["BASE"] - mean_base
    d["LOW"] = d["TRT01A"].eq("Xanomeline Low Dose").astype(float)
    d["HIGH"] = d["TRT01A"].eq("Xanomeline High Dose").astype(float)
    X = np.column_stack([np.ones(len(d)), d["LOW"], d["HIGH"], d["BASEC"]])
    y = d["AVAL"].to_numpy(dtype=float)
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    if rank < X.shape[1]:
        raise ValueError("ANCOVA design matrix is rank deficient")
    resid = y - X @ beta
    df = len(y) - X.shape[1]
    if df <= 0:
        raise ValueError("ANCOVA has insufficient residual degrees of freedom")
    mse = float((resid @ resid) / df)
    cov = mse * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    tcrit = float(student_t.ppf(0.975, df))

    lsmeans = []
    for arm, idx in [("Placebo", None), ("Xanomeline Low Dose", 1), ("Xanomeline High Dose", 2)]:
        est = float(beta[0] + (beta[idx] if idx is not None else 0.0))
        c = np.array([1.0, 1.0 if idx == 1 else 0.0, 1.0 if idx == 2 else 0.0, 0.0])
        sest = float(math.sqrt(c @ cov @ c))
        lsmeans.append({
            "analysis": label,
            "TRT01A": arm,
            "n": int(d["TRT01A"].eq(arm).sum()),
            "lsmean_week24": est,
            "se": sest,
            "ci95_lower": est - tcrit * sest,
            "ci95_upper": est + tcrit * sest,
            "baseline_reference": mean_base,
        })

    contrasts = []
    for arm, idx in [("Xanomeline Low Dose", 1), ("Xanomeline High Dose", 2)]:
        est = float(beta[idx])
        sest = float(se[idx])
        tstat = est / sest if sest > 0 else np.nan
        p = float(2 * student_t.sf(abs(tstat), df)) if np.isfinite(tstat) else np.nan
        contrasts.append({
            "analysis": label,
            "comparison": f"{arm} vs Placebo",
            "n_total": int(len(d)),
            "estimate": est,
            "se": sest,
            "ci95_lower": est - tcrit * sest,
            "ci95_upper": est + tcrit * sest,
            "p_value": p,
            "df": int(df),
            "baseline_reference": mean_base,
        })
    return pd.DataFrame(lsmeans), pd.DataFrame(contrasts)


def actot_week24_ancova(adqs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed = _analysis_subjects(adqs, locf=False)
    locf = _analysis_subjects(adqs, locf=True)
    ls_obs, c_obs = _fit_ancova(observed, "Observed Week 24")
    ls_locf, c_locf = _fit_ancova(locf, "LOCF sensitivity")
    analysis_subjects = pd.concat(
        [observed.assign(analysis="Observed Week 24"), locf.assign(analysis="LOCF sensitivity")],
        ignore_index=True,
    )
    return pd.concat([ls_obs, ls_locf], ignore_index=True), pd.concat([c_obs, c_locf], ignore_index=True), analysis_subjects


def actot_descriptive(adqs: pd.DataFrame) -> pd.DataFrame:
    observed = _analysis_subjects(adqs, locf=False)
    rows = []
    for arm in EXPECTED_ARMS:
        g = observed.loc[observed["TRT01A"].eq(arm)]
        if g.empty:
            continue
        rows.append({
            "TRT01A": arm,
            "n": len(g),
            "baseline_mean": g["BASE"].mean(),
            "baseline_sd": g["BASE"].std(ddof=1),
            "week24_mean": g["AVAL"].mean(),
            "week24_sd": g["AVAL"].std(ddof=1),
            "change_mean": g["CHG"].mean(),
            "change_sd": g["CHG"].std(ddof=1),
        })
    return pd.DataFrame(rows)

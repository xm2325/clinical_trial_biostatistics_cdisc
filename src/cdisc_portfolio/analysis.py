from __future__ import annotations

import math
import pandas as pd
from scipy.stats import fisher_exact, norm


def _fmt_n_pct(n: int, denom: int) -> str:
    pct = 100.0 * n / denom if denom else 0.0
    return f"{n} ({pct:.1f}%)"


def _arm_order(values: pd.Series) -> list[str]:
    unique = [str(x) for x in values.dropna().unique()]
    preferred = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
    return [x for x in preferred if x in unique] + sorted(x for x in unique if x not in preferred)


def demographics_summary(adsl: pd.DataFrame) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y")].copy()
    rows: list[dict[str, object]] = []
    for arm in _arm_order(safety["TRT01A"]):
        g = safety.loc[safety["TRT01A"].eq(arm)]
        n = len(g)
        rows.append({"TRT01A": arm, "Statistic": "N", "Value": str(n)})
        age = pd.to_numeric(g["AGE"], errors="coerce")
        rows.append({"TRT01A": arm, "Statistic": "Age, mean (SD)", "Value": f"{age.mean():.1f} ({age.std(ddof=1):.1f})"})
        rows.append({"TRT01A": arm, "Statistic": "Age, median [Q1, Q3]", "Value": f"{age.median():.1f} [{age.quantile(.25):.1f}, {age.quantile(.75):.1f}]"})
        for sex in sorted(g["SEX"].dropna().astype(str).unique()):
            count = int(g["SEX"].eq(sex).sum())
            rows.append({"TRT01A": arm, "Statistic": f"Sex={sex}, n (%)", "Value": _fmt_n_pct(count, n)})
        for race in sorted(g["RACE"].dropna().astype(str).unique()):
            count = int(g["RACE"].eq(race).sum())
            rows.append({"TRT01A": arm, "Statistic": f"Race={race}, n (%)", "Value": _fmt_n_pct(count, n)})
    return pd.DataFrame(rows)


def disposition_summary(adsl: pd.DataFrame) -> pd.DataFrame:
    rand = adsl.loc[adsl["RANDFL"].eq("Y")].copy()
    rows: list[dict[str, object]] = []
    for arm in _arm_order(rand["TRT01A"]):
        g = rand.loc[rand["TRT01A"].eq(arm)]
        n = len(g)
        rows.extend([
            {"TRT01A": arm, "Statistic": "Randomised N", "Value": str(n)},
            {"TRT01A": arm, "Statistic": "Safety population, n (%)", "Value": _fmt_n_pct(int(g["SAFFL"].eq("Y").sum()), n)},
            {"TRT01A": arm, "Statistic": "Completed, n (%)", "Value": _fmt_n_pct(int(g["COMPLFL"].eq("Y").sum()), n)},
            {"TRT01A": arm, "Statistic": "Discontinued, n (%)", "Value": _fmt_n_pct(int(g["DCSFL"].eq("Y").sum()), n)},
        ])
        dc = g.loc[g["DCSFL"].eq("Y")]
        for reason, count in dc["EOSDECOD"].fillna("Missing").value_counts().sort_index().items():
            rows.append({"TRT01A": arm, "Statistic": f"Discontinuation reason: {reason}, n (%)", "Value": _fmt_n_pct(int(count), n)})
    return pd.DataFrame(rows)


def exposure_summary(adsl: pd.DataFrame) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y")].copy()
    rows: list[dict[str, object]] = []
    for arm in _arm_order(safety["TRT01A"]):
        g = safety.loc[safety["TRT01A"].eq(arm)]
        dur = pd.to_numeric(g["TRTDURN"], errors="coerce")
        maxdose = pd.to_numeric(g["EXDOSE_MAX"], errors="coerce")
        rows.extend([
            {"TRT01A": arm, "Statistic": "Exposure duration, mean (SD), days", "Value": f"{dur.mean():.1f} ({dur.std(ddof=1):.1f})"},
            {"TRT01A": arm, "Statistic": "Exposure duration, median [Q1, Q3], days", "Value": f"{dur.median():.1f} [{dur.quantile(.25):.1f}, {dur.quantile(.75):.1f}]"},
            {"TRT01A": arm, "Statistic": "Observed exposure records, median [Q1, Q3]", "Value": f"{g['EXN'].median():.1f} [{g['EXN'].quantile(.25):.1f}, {g['EXN'].quantile(.75):.1f}]"},
            {"TRT01A": arm, "Statistic": "Maximum recorded dose, median [Q1, Q3]", "Value": f"{maxdose.median():.1f} [{maxdose.quantile(.25):.1f}, {maxdose.quantile(.75):.1f}]"},
        ])
    return pd.DataFrame(rows)


def teae_overview(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y"), ["USUBJID", "TRT01A", "DCSFL", "EOSDECOD"]].copy()
    teae = adae.loc[adae["TRTEMFL"].eq("Y")].copy()
    rows: list[dict[str, object]] = []
    for arm in _arm_order(safety["TRT01A"]):
        gsub = safety.loc[safety["TRT01A"].eq(arm)]
        denom = gsub["USUBJID"].nunique()
        arm_ae = teae.loc[teae["TRT01A"].eq(arm)]
        metrics = {
            "Subjects with >=1 TEAE, n (%)": arm_ae["USUBJID"].nunique(),
            "Subjects with >=1 serious TEAE, n (%)": arm_ae.loc[arm_ae["AESER"].astype(str).str.upper().eq("Y"), "USUBJID"].nunique(),
            "Subjects with >=1 related TEAE, n (%)": arm_ae.loc[arm_ae["RELFL"].eq("Y"), "USUBJID"].nunique(),
            "Subjects with >=1 moderate/severe TEAE, n (%)": arm_ae.loc[arm_ae["MODSEVFL"].eq("Y"), "USUBJID"].nunique(),
            "Subjects discontinued due to AE, n (%)": gsub.loc[gsub["EOSDECOD"].fillna("").astype(str).str.upper().eq("ADVERSE EVENT"), "USUBJID"].nunique(),
        }
        rows.append({"TRT01A": arm, "Statistic": "Safety N", "Value": str(denom)})
        rows.extend({"TRT01A": arm, "Statistic": name, "Value": _fmt_n_pct(int(n), denom)} for name, n in metrics.items())
        rows.append({"TRT01A": arm, "Statistic": "Total TEAE events", "Value": str(len(arm_ae))})
    return pd.DataFrame(rows)


def teae_by_soc_pt(adsl: pd.DataFrame, adae: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y")].copy()
    denom = safety.groupby("TRT01A")["USUBJID"].nunique().to_dict()
    teae = adae.loc[adae["TRTEMFL"].eq("Y") & adae["AEDECOD"].notna()].copy()
    overall = teae.groupby("AEDECOD")["USUBJID"].nunique().sort_values(ascending=False)
    preferred_terms = overall.head(top_n).index.tolist()
    rows: list[dict[str, object]] = []
    for term in preferred_terms:
        term_rows = teae.loc[teae["AEDECOD"].eq(term)]
        soc = term_rows["AEBODSYS"].dropna().astype(str).mode()
        soc_value = soc.iloc[0] if not soc.empty else ""
        for arm in _arm_order(safety["TRT01A"]):
            n = term_rows.loc[term_rows["TRT01A"].eq(arm), "USUBJID"].nunique()
            rows.append({"AEBODSYS": soc_value, "AEDECOD": term, "TRT01A": arm, "n": int(n), "denom": int(denom[arm]), "n_pct": _fmt_n_pct(int(n), int(denom[arm]))})
    return pd.DataFrame(rows)


def teae_by_severity(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y")].copy()
    denom = safety.groupby("TRT01A")["USUBJID"].nunique().to_dict()
    teae = adae.loc[adae["TRTEMFL"].eq("Y")].copy()
    rows: list[dict[str, object]] = []
    for arm in _arm_order(safety["TRT01A"]):
        arm_ae = teae.loc[teae["TRT01A"].eq(arm)]
        for sev in ["MILD", "MODERATE", "SEVERE"]:
            n = arm_ae.loc[arm_ae["AESEV"].fillna("").astype(str).str.upper().eq(sev), "USUBJID"].nunique()
            rows.append({"TRT01A": arm, "Severity": sev.title(), "n": int(n), "denom": int(denom[arm]), "n_pct": _fmt_n_pct(int(n), int(denom[arm]))})
    return pd.DataFrame(rows)


def teae_risk_differences(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    """Unadjusted subject-level any-TEAE risk differences vs placebo."""
    safety = adsl.loc[adsl["SAFFL"].eq("Y"), ["USUBJID", "TRT01A"]].drop_duplicates()
    teae_ids = set(adae.loc[adae["TRTEMFL"].eq("Y"), "USUBJID"].astype(str))
    safety["ANY_TEAE"] = safety["USUBJID"].astype(str).isin(teae_ids).astype(int)
    placebo = safety.loc[safety["TRT01A"].eq("Placebo")]
    if placebo.empty:
        return pd.DataFrame(columns=["comparison", "n_arm", "n_placebo", "risk_arm", "risk_placebo", "risk_difference", "ci95_lower", "ci95_upper", "fisher_p"])

    n0 = len(placebo)
    e0 = int(placebo["ANY_TEAE"].sum())
    p0 = e0 / n0
    z = norm.ppf(0.975)
    rows: list[dict[str, object]] = []
    for arm in _arm_order(safety["TRT01A"]):
        if arm == "Placebo":
            continue
        g = safety.loc[safety["TRT01A"].eq(arm)]
        if g.empty:
            continue
        n1 = len(g)
        e1 = int(g["ANY_TEAE"].sum())
        p1 = e1 / n1
        rd = p1 - p0
        se = math.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
        lo, hi = rd - z * se, rd + z * se
        _, fisher_p = fisher_exact([[e1, n1 - e1], [e0, n0 - e0]], alternative="two-sided")
        rows.append({
            "comparison": f"{arm} vs Placebo",
            "n_arm": n1,
            "n_placebo": n0,
            "risk_arm": round(p1, 4),
            "risk_placebo": round(p0, 4),
            "risk_difference": round(rd, 4),
            "ci95_lower": round(lo, 4),
            "ci95_upper": round(hi, 4),
            "fisher_p": round(float(fisher_p), 6),
        })
    return pd.DataFrame(rows)

"""Build the real-data examples used by the CDISC / ADaM / TLF learning handbook.

All inputs are public files pulled from GitHub at pinned commits:

* SDTM: pharmaverse/pharmaversesdtm (CDISC pilot-style test data, CSV)
* ADaM: cdisc-org/sdtm-adam-pilot-project (CDISCPILOT01 ADaM, Dataset-JSON)

Outputs (committed so the handbook can be read without running anything):

* docs/learning/generated/real_data_examples.md
* docs/learning/generated/real_data_metrics.json
* docs/learning/generated/km_ttde.svg

Usage::

    python scripts/build_cdisc_learning_examples.py [--cache cache/learning]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "learning" / "generated"

PHARMAVERSESDTM_COMMIT = "7ec53ea88dfe1c168f9efbef59233c4426813b89"
CDISC_PILOT_COMMIT = "667511d4b183871d74392ba691c935c38d431d39"

SDTM_BASE = (
    "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/"
    f"{PHARMAVERSESDTM_COMMIT}/inst/extdata"
)
ADAM_BASE = (
    "https://raw.githubusercontent.com/cdisc-org/sdtm-adam-pilot-project/"
    f"{CDISC_PILOT_COMMIT}/updated-pilot-submission-package/900172/m5/datasets/"
    "cdiscpilot01/analysis/adam/datasets"
)
SOURCES = {
    "dm": ("SDTM", f"{SDTM_BASE}/dm.csv"),
    "ex": ("SDTM", f"{SDTM_BASE}/ex.csv"),
    "ds": ("SDTM", f"{SDTM_BASE}/ds.csv"),
    "ae": ("SDTM", f"{SDTM_BASE}/ae.csv"),
    "adsl": ("ADaM", f"{ADAM_BASE}/adsl.json"),
    "adae": ("ADaM", f"{ADAM_BASE}/adae.json"),
    "adqsadas": ("ADaM", f"{ADAM_BASE}/adqsadas.json"),
    "adtte": ("ADaM", f"{ADAM_BASE}/adtte.json"),
}

ARMS = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
ARM_SHORT = {"Placebo": "Placebo", "Xanomeline Low Dose": "Xan Low", "Xanomeline High Dose": "Xan High"}
TRACE_SUBJECT = "01-701-1015"


# --------------------------------------------------------------------------- io
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(cache: Path) -> dict[str, Path]:
    cache.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, (_, url) in SOURCES.items():
        path = cache / Path(url).name
        if not path.exists():
            req = Request(url, headers={"User-Agent": "cdisc-learning-handbook/1.0"})
            with urlopen(req, timeout=120) as r:
                path.write_bytes(r.read())
        paths[name] = path
    return paths


def load(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    data = {}
    for name, path in paths.items():
        if path.suffix == ".csv":
            data[name] = pd.read_csv(path, na_values=["NA", ""], keep_default_na=True)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cols = [c["name"] for c in payload["columns"]]
            data[name] = pd.DataFrame(payload["rows"], columns=cols)
    return data


# ------------------------------------------------------------------- formatting
def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        cells = ["" if (isinstance(v, float) and math.isnan(v)) else str(v) for v in row]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(lines)


def npct(n: int, d: int) -> str:
    return f"{n} ({100 * n / d:.1f}%)" if d else "0"


# ---------------------------------------------------------------------- sections
def source_inventory(paths, data) -> pd.DataFrame:
    rows = []
    for name, (std, url) in SOURCES.items():
        df = data[name]
        rows.append({
            "数据集": name.upper(),
            "标准": std,
            "行数": len(df),
            "变量数": df.shape[1],
            "SHA256(前12位)": sha256(paths[name])[:12],
            "来源": url.split("githubusercontent.com/")[1].split("/")[0] + "/" + url.split("/")[4],
        })
    return pd.DataFrame(rows)


def rederive_adsl(dm: pd.DataFrame, ex: pd.DataFrame, adsl: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Independent (teaching) re-derivation of a few ADSL variables from SDTM."""
    d = dm[dm["ARMCD"] != "Scrnfail"].copy()
    d = d[d["ARM"] != "Screen Failure"]

    exd = ex.copy()
    exd["start"] = pd.to_datetime(exd["EXSTDTC"].str[:10], errors="coerce")
    exd["end"] = pd.to_datetime(exd["EXENDTC"].str[:10], errors="coerce")
    exs = exd.groupby("USUBJID").agg(TRTSDT=("start", "min"), TRTEDT=("end", "max")).reset_index()
    # did the subject's last exposure record have a missing end date?
    last = exd.sort_values(["USUBJID", "start"]).groupby("USUBJID").tail(1)
    exs = exs.merge(last[["USUBJID", "end"]].rename(columns={"end": "last_end"}), on="USUBJID")
    d = d.merge(exs, on="USUBJID", how="left")

    d["AGEGR1"] = np.select([d["AGE"] < 65, d["AGE"] <= 80], ["<65", "65-80"], ">80")
    d["SAFFL"] = np.where(d["TRTSDT"].notna(), "Y", "N")
    d["TRTDUR"] = (d["TRTEDT"] - d["TRTSDT"]).dt.days + 1
    # v2 rule: if the last EX record is still open (EXENDTC missing), impute
    # TRTEDT with the reference end date DM.RFENDTC, as the pilot ADSL does.
    rfend = pd.to_datetime(d["RFENDTC"].str[:10], errors="coerce")
    d["TRTEDT_V2"] = d["TRTEDT"].where(d["last_end"].notna(), rfend)
    d["TRTDUR_V2"] = (d["TRTEDT_V2"] - d["TRTSDT"]).dt.days + 1
    imputed = d.loc[d["last_end"].isna(), "USUBJID"].tolist()

    ref = adsl.copy()
    ref["TRTSDT"] = pd.to_datetime(ref["TRTSDT"], errors="coerce")
    ref["TRTEDT"] = pd.to_datetime(ref["TRTEDT"], errors="coerce")
    ref["TRTDUR"] = pd.to_numeric(ref["TRTDUR"], errors="coerce")
    m = d.merge(ref, on="USUBJID", suffixes=("_ours", "_ref"), how="outer", indicator=True)

    rows = []
    stats_out = {"subjects_ours": int(len(d)), "subjects_ref": int(len(ref)),
                 "subjects_both": int((m["_merge"] == "both").sum())}
    both = m[m["_merge"] == "both"]
    checks = [("AGEGR1", "AGEGR1_ours", "v1"), ("SAFFL", "SAFFL_ours", "v1"), ("TRTSDT", "TRTSDT_ours", "v1"),
              ("TRTEDT", "TRTEDT_ours", "v1 = max(EXENDTC)"), ("TRTDUR", "TRTDUR_ours", "v1"),
              ("TRTEDT", "TRTEDT_V2", "v2 = 末次EXENDTC缺失时用RFENDTC"), ("TRTDUR", "TRTDUR_V2", "v2")]
    for var, ours, rule in checks:
        a, b = both[ours], both[f"{var}_ref"]
        eq = (a == b) | (a.isna() & b.isna())
        rows.append({"变量": var, "推导规则": rule, "比较受试者数": len(both), "一致": int(eq.sum()),
                     "不一致": int((~eq).sum()), "一致率": f"{100 * eq.mean():.1f}%"})
        stats_out[f"match_{var}_{rule.split()[0]}"] = int(eq.sum())
    stats_out["open_last_exposure_subjects"] = imputed
    return pd.DataFrame(rows), stats_out


def population_table(adsl) -> pd.DataFrame:
    rows = []
    for label, flag in [("随机化/ITT (ITTFL)", "ITTFL"), ("安全性 (SAFFL)", "SAFFL"),
                        ("疗效 (EFFFL)", "EFFFL"), ("完成第24周 (COMP24FL)", "COMP24FL")]:
        row = {"人群": label}
        for arm in ARMS:
            row[ARM_SHORT[arm]] = int(((adsl["TRT01P"] == arm) & (adsl[flag] == "Y")).sum())
        row["合计"] = int((adsl[flag] == "Y").sum())
        rows.append(row)
    return pd.DataFrame(rows)


def demographics_table(adsl) -> pd.DataFrame:
    itt = adsl[adsl["ITTFL"] == "Y"].copy()
    itt["AGE"] = pd.to_numeric(itt["AGE"])
    groups = {ARM_SHORT[a]: itt[itt["TRT01P"] == a] for a in ARMS}
    groups["合计"] = itt
    rows = []

    def add(label, fn):
        rows.append({"项目": label, **{k: fn(g) for k, g in groups.items()}})

    add("N", lambda g: str(len(g)))
    add("年龄 Mean (SD)", lambda g: f"{g['AGE'].mean():.1f} ({g['AGE'].std():.2f})")
    add("年龄 Median", lambda g: f"{g['AGE'].median():.1f}")
    add("年龄 Min, Max", lambda g: f"{g['AGE'].min():.0f}, {g['AGE'].max():.0f}")
    for grp in ["<65", "65-80", ">80"]:
        add(f"  年龄组 {grp}", lambda g, grp=grp: npct(int((g["AGEGR1"] == grp).sum()), len(g)))
    for sex, lab in [("F", "女"), ("M", "男")]:
        add(f"  性别 {lab}", lambda g, sex=sex: npct(int((g["SEX"] == sex).sum()), len(g)))
    for race in ["WHITE", "BLACK OR AFRICAN AMERICAN", "AMERICAN INDIAN OR ALASKA NATIVE"]:
        add(f"  种族 {race}", lambda g, race=race: npct(int((g["RACE"] == race).sum()), len(g)))
    return pd.DataFrame(rows)


def ae_tables(adsl, adae):
    saf = adsl[adsl["SAFFL"] == "Y"]
    denom = {a: int((saf["TRT01A"] == a).sum()) for a in ARMS}
    te = adae[(adae["SAFFL"] == "Y") & (adae["TRTEMFL"] == "Y")]

    def subj(df, arm):
        return df.loc[df["TRTA"] == arm, "USUBJID"].nunique()

    overview = []
    for label, sub in [
        ("至少1个TEAE的受试者", te),
        ("至少1个严重TEAE (AESER=Y)", te[te["AESER"] == "Y"]),
        ("至少1个重度TEAE (AESEV=SEVERE)", te[te["AESEV"] == "SEVERE"]),
    ]:
        overview.append({"类别": label, **{f"{ARM_SHORT[a]} (N={denom[a]})": npct(subj(sub, a), denom[a]) for a in ARMS}})
    # AEACN is blank in the pilot ADAE; AE-driven discontinuation lives in ADSL.DSRAEFL
    overview.append({"类别": "因AE停止研究 (ADSL.DSRAEFL=Y)",
                     **{f"{ARM_SHORT[a]} (N={denom[a]})": npct(int(((saf["TRT01A"] == a) & (saf["DSRAEFL"] == "Y")).sum()), denom[a]) for a in ARMS}})
    overview.append({"类别": "TEAE 事件数 (records)", **{f"{ARM_SHORT[a]} (N={denom[a]})": str(int((te["TRTA"] == a).sum())) for a in ARMS}})

    pt_n = te.groupby("AEDECOD")["USUBJID"].nunique().sort_values(ascending=False)
    top = []
    for pt in pt_n.index[:10]:
        sub = te[te["AEDECOD"] == pt]
        soc = sub["AEBODSYS"].iloc[0]
        top.append({"SOC": soc, "PT (AEDECOD)": pt,
                    **{f"{ARM_SHORT[a]} (N={denom[a]})": npct(subj(sub, a), denom[a]) for a in ARMS}})
    return pd.DataFrame(overview), pd.DataFrame(top), denom, te


def adas_ancova(adqs):
    """Week 24 ACTOT change from baseline, LOCF, efficacy population.

    Mirrors the CDISC pilot primary efficacy table: ANCOVA with treatment,
    site group and baseline score.
    """
    df = adqs[(adqs["PARAMCD"] == "ACTOT") & (adqs["AVISIT"] == "Week 24")
              & (adqs["EFFFL"] == "Y") & (adqs["ANL01FL"] == "Y")].copy()
    for c in ["AVAL", "BASE", "CHG"]:
        df[c] = pd.to_numeric(df[c])
    desc = []
    for arm in ARMS:
        g = df[df["TRTP"] == arm]
        desc.append({"组别": ARM_SHORT[arm], "n": len(g), "基线 Mean (SD)": f"{g['BASE'].mean():.1f} ({g['BASE'].std():.2f})",
                     "第24周 Mean (SD)": f"{g['AVAL'].mean():.1f} ({g['AVAL'].std():.2f})",
                     "变化值 CHG Mean (SD)": f"{g['CHG'].mean():.1f} ({g['CHG'].std():.2f})",
                     "其中 LOCF 填补行": int((g["DTYPE"] == "LOCF").sum())})

    sites = sorted(df["SITEGR1"].unique())
    X_cols = {"Intercept": np.ones(len(df))}
    X_cols["Xan Low"] = (df["TRTP"] == ARMS[1]).astype(float).to_numpy()
    X_cols["Xan High"] = (df["TRTP"] == ARMS[2]).astype(float).to_numpy()
    for s in sites[1:]:
        X_cols[f"site_{s}"] = (df["SITEGR1"] == s).astype(float).to_numpy()
    X_cols["BASE"] = df["BASE"].to_numpy()
    X = np.column_stack(list(X_cols.values()))
    y = df["CHG"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.inv(X.T @ X)
    tcrit = stats.t.ppf(0.975, dof)
    contrast = []
    for i, name in [(1, "Xan Low"), (2, "Xan High")]:
        est, se = beta[i], math.sqrt(cov[i, i])
        p = 2 * stats.t.sf(abs(est / se), dof)
        contrast.append({"比较": f"{name} vs Placebo", "LS均值差": f"{est:.2f}", "SE": f"{se:.2f}",
                         "95% CI": f"({est - tcrit * se:.2f}, {est + tcrit * se:.2f})", "p值": f"{p:.4f}"})
    # dose-response test (TRTPN as continuous 0/54/81), pilot's primary contrast
    dose = pd.to_numeric(df["TRTPN"]).to_numpy()
    Xd = np.column_stack([np.ones(len(df)), dose] + [X_cols[k] for k in X_cols if k.startswith("site_")] + [X_cols["BASE"]])
    bd, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    rd = y - Xd @ bd
    dofd = len(y) - Xd.shape[1]
    covd = (rd @ rd / dofd) * np.linalg.inv(Xd.T @ Xd)
    p_dose = 2 * stats.t.sf(abs(bd[1] / math.sqrt(covd[1, 1])), dofd)
    return pd.DataFrame(desc), pd.DataFrame(contrast), {"n": int(len(df)), "dof": int(dof), "p_dose_response": float(p_dose)}


def kaplan_meier(time: np.ndarray, event: np.ndarray):
    order = np.argsort(time, kind="stable")
    t, e = time[order], event[order]
    times, surv = [0.0], [1.0]
    s = 1.0
    n_at_risk = len(t)
    for ut in np.unique(t):
        d = int(e[t == ut].sum())
        c = int((t == ut).sum())
        if d:
            s *= 1 - d / n_at_risk
            times.append(float(ut))
            surv.append(s)
        n_at_risk -= c
    median = next((tt for tt, ss in zip(times, surv) if ss <= 0.5), None)
    return np.array(times), np.array(surv), median


def logrank(time, event, group):
    groups = np.unique(group)
    obs = np.zeros(len(groups))
    exp = np.zeros(len(groups))
    var = np.zeros((len(groups), len(groups)))
    for ut in np.unique(time[event == 1]):
        at = time >= ut
        n = at.sum()
        d = ((time == ut) & (event == 1)).sum()
        ni = np.array([(at & (group == g)).sum() for g in groups])
        di = np.array([((time == ut) & (event == 1) & (group == g)).sum() for g in groups])
        obs += di
        exp += d * ni / n
        if n > 1:
            for i in range(len(groups)):
                for j in range(len(groups)):
                    var[i, j] += d * (n - d) / (n - 1) * (ni[i] / n) * ((i == j) - ni[j] / n)
    oe = (obs - exp)[:-1]
    chi2 = float(oe @ np.linalg.inv(var[:-1, :-1]) @ oe)
    return chi2, float(stats.chi2.sf(chi2, len(groups) - 1))


def tte_section(adtte):
    df = adtte[adtte["SAFFL"] == "Y"].copy()
    df["AVAL"] = pd.to_numeric(df["AVAL"])
    df["EVENT"] = 1 - pd.to_numeric(df["CNSR"])
    rows, curves = [], {}
    for arm in ARMS:
        g = df[df["TRTA"] == arm]
        t, s, med = kaplan_meier(g["AVAL"].to_numpy(float), g["EVENT"].to_numpy(int))
        curves[arm] = (t, s)
        rows.append({"组别": ARM_SHORT[arm], "N": len(g), "事件数 (CNSR=0)": int(g["EVENT"].sum()),
                     "删失数 (CNSR=1)": int((g["EVENT"] == 0).sum()),
                     "KM中位时间(天)": "未达到" if med is None else f"{med:.0f}"})
    chi2, p = logrank(df["AVAL"].to_numpy(float), df["EVENT"].to_numpy(int), df["TRTA"].to_numpy())
    return pd.DataFrame(rows), curves, {"logrank_chi2": chi2, "logrank_p": p}


def km_svg(curves, path: Path) -> None:
    W, H, L, R, T, B = 640, 400, 60, 20, 30, 50
    tmax = max(c[0].max() for c in curves.values())
    tmax = math.ceil(tmax / 30) * 30
    sx = lambda t: L + (W - L - R) * t / tmax  # noqa: E731
    sy = lambda s: T + (H - T - B) * (1 - s)  # noqa: E731
    colors = {"Placebo": "#4C72B0", "Xanomeline Low Dose": "#DD8452", "Xanomeline High Dose": "#C44E52"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial, sans-serif" font-size="12">',
             f'<rect width="{W}" height="{H}" fill="white"/>',
             f'<text x="{W / 2}" y="18" text-anchor="middle" font-size="14">Figure: Kaplan-Meier, Time to First Dermatologic Event (ADTTE, SAFFL=Y)</text>']
    for k in range(0, 11, 2):
        y = sy(k / 10)
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#eee"/>')
        parts.append(f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end">{k / 10:.1f}</text>')
    for t in range(0, tmax + 1, 30):
        x = sx(t)
        parts.append(f'<text x="{x:.1f}" y="{H - B + 16}" text-anchor="middle">{t}</text>')
    parts.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(0)}" y2="{sy(0)}" stroke="#333"/>')
    parts.append(f'<line x1="{L}" x2="{L}" y1="{sy(1)}" y2="{sy(0)}" stroke="#333"/>')
    parts.append(f'<text x="{(L + W - R) / 2}" y="{H - 10}" text-anchor="middle">Days since first dose (AVAL)</text>')
    parts.append(f'<text x="16" y="{(T + H - B) / 2}" text-anchor="middle" transform="rotate(-90 16 {(T + H - B) / 2})">Event-free probability</text>')
    for i, (arm, (t, s)) in enumerate(curves.items()):
        pts = [f"{sx(t[0]):.1f},{sy(s[0]):.1f}"]
        for j in range(1, len(t)):
            pts.append(f"{sx(t[j]):.1f},{sy(s[j - 1]):.1f}")
            pts.append(f"{sx(t[j]):.1f},{sy(s[j]):.1f}")
        pts.append(f"{sx(tmax):.1f},{sy(s[-1]):.1f}")
        parts.append(f'<polyline fill="none" stroke="{colors[arm]}" stroke-width="2" points="{" ".join(pts)}"/>')
        ly = T + 20 + 18 * i
        parts.append(f'<line x1="{W - 200}" x2="{W - 175}" y1="{ly}" y2="{ly}" stroke="{colors[arm]}" stroke-width="3"/>')
        parts.append(f'<text x="{W - 170}" y="{ly + 4}">{arm}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def subject_trace(data) -> str:
    s = TRACE_SUBJECT
    out = []
    dm = data["dm"][data["dm"]["USUBJID"] == s][["USUBJID", "ARM", "ACTARM", "RFSTDTC", "RFENDTC", "BRTHDTC", "AGE", "SEX", "RACE", "SITEID"]]
    out += ["**① SDTM.DM（一人一行，原始“收集到的”事实）**", "", md_table(dm), ""]
    ex = data["ex"][data["ex"]["USUBJID"] == s][["USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXSTDTC", "EXENDTC", "VISIT"]]
    out += ["**② SDTM.EX（给药记录，一人多行）**", "", md_table(ex), ""]
    adsl = data["adsl"][data["adsl"]["USUBJID"] == s][["USUBJID", "TRT01P", "TRT01A", "TRTSDT", "TRTEDT", "TRTDUR", "AGEGR1", "SAFFL", "ITTFL", "EFFFL", "COMP24FL", "MMSETOT"]]
    out += ["**③ ADaM.ADSL（一人一行，加上了治疗日期、人群标志、分组等“分析用”变量）**", "", md_table(adsl), ""]
    ae = data["ae"][data["ae"]["USUBJID"] == s][["USUBJID", "AESEQ", "AETERM", "AEDECOD", "AEBODSYS", "AESTDTC", "AESEV", "AESER"]]
    out += ["**④ SDTM.AE（不良事件原始记录）**", "", md_table(ae), ""]
    adae = data["adae"][data["adae"]["USUBJID"] == s][["USUBJID", "AESEQ", "TRTA", "AEDECOD", "ASTDT", "ASTDY", "TRTEMFL", "AOCCPFL", "SAFFL"]]
    out += ["**⑤ ADaM.ADAE（加上 TRTA、ASTDY、TRTEMFL 等分析变量）**", "", md_table(adae), ""]
    q = data["adqsadas"]
    q = q[(q["USUBJID"] == s) & (q["PARAMCD"] == "ACTOT")][["USUBJID", "PARAMCD", "AVISIT", "ADY", "AVAL", "BASE", "CHG", "ABLFL", "ANL01FL", "DTYPE"]]
    out += ["**⑥ ADaM.ADQSADAS（BDS 结构：一人 × 参数 × 访视 一行）**", "", md_table(q), ""]
    t = data["adtte"][data["adtte"]["USUBJID"] == s][["USUBJID", "PARAMCD", "STARTDT", "ADT", "AVAL", "CNSR", "EVNTDESC", "SRCDOM", "SRCVAR", "SRCSEQ"]]
    out += ["**⑦ ADaM.ADTTE（时间-事件：AVAL=天数，CNSR=0 表示事件发生）**", "", md_table(t), ""]
    return "\n".join(out)


def sae_listing(data) -> pd.DataFrame:
    a = data["adae"]
    a = a[(a["AESER"] == "Y") & (a["SAFFL"] == "Y")].sort_values(["TRTA", "USUBJID", "ASTDT"])
    return a[["TRTA", "USUBJID", "AGE", "SEX", "AEDECOD", "ASTDT", "ASTDY", "AESEV", "AEOUT", "AEREL"]].head(10)


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "cache" / "learning"))
    args = ap.parse_args()

    paths = fetch(Path(args.cache))
    data = load(paths)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    inv = source_inventory(paths, data)
    dm_arm = data["dm"]["ARM"].value_counts().rename_axis("DM.ARM").reset_index(name="受试者数")
    qc_tab, qc_stats = rederive_adsl(data["dm"], data["ex"], data["adsl"])
    pop = population_table(data["adsl"])
    demo = demographics_table(data["adsl"])
    ae_over, ae_top, denom, te = ae_tables(data["adsl"], data["adae"])
    adas_desc, adas_contrast, adas_stats = adas_ancova(data["adqsadas"])
    tte_tab, curves, tte_stats = tte_section(data["adtte"])
    km_svg(curves, OUT_DIR / "km_ttde.svg")
    listing = sae_listing(data)

    md = [
        "# CDISC Pilot 真实数据示例（自动生成）",
        "",
        "> 本文件由 `python scripts/build_cdisc_learning_examples.py` 生成，请勿手工修改。",
        "> 数据全部来自 GitHub 公开仓库（固定 commit），用于学习手册 `docs/learning/` 中的讲解。",
        f"> SDTM: `pharmaverse/pharmaversesdtm@{PHARMAVERSESDTM_COMMIT[:7]}`；ADaM: `cdisc-org/sdtm-adam-pilot-project@{CDISC_PILOT_COMMIT[:7]}`（CDISCPILOT01）。",
        "",
        "## 1. 数据清单", "", md_table(inv), "",
        "## 2. 为什么 DM 有 306 人而 ADSL 只有 254 人？", "",
        md_table(dm_arm), "",
        "DM 收录了所有签署知情同意的人（含筛选失败 Screen Failure），而 CDISC Pilot 的 ADSL 只保留进入随机化的受试者。",
        "",
        f"## 3. 一名受试者（{TRACE_SUBJECT}）从 SDTM 到 ADaM 的完整追溯", "",
        subject_trace(data), "",
        "## 4. 独立复算 QC：用 SDTM 重新推导 ADSL 关键变量，再与官方 ADSL 比对", "",
        f"我方推导受试者 {qc_stats['subjects_ours']} 人，官方 ADSL {qc_stats['subjects_ref']} 人，匹配上 {qc_stats['subjects_both']} 人。", "",
        md_table(qc_tab), "",
        "规则（教学版）：TRTSDT=min(EX.EXSTDTC)，TRTDUR=TRTEDT−TRTSDT+1，AGEGR1: <65 / 65-80 / >80，SAFFL=有任何给药记录。", "",
        f"v1 的 6 个不一致受试者（{', '.join(qc_stats['open_last_exposure_subjects'])}）末次 EX 记录 EXENDTC 为空："
        "简单取 max 会拿到更早那条记录的结束日期。官方 ADSL 用 DM.RFENDTC 补齐——把这条规则写进 spec 后（v2）即 100% 一致。"
        "这正是双人独立编程（double programming）发现 spec 歧义的典型过程，见手册第 6 章。", "",
        "## 5. Table：分析人群汇总（ADSL，按 TRT01P）", "", md_table(pop), "",
        "## 6. Table 14-2.01 风格：人口学与基线特征（ITT，按 TRT01P）", "", md_table(demo), "",
        "## 7. Table 14-5.01 风格：TEAE 总览（安全性人群，按实际治疗 TRTA）", "", md_table(ae_over), "",
        "### 按 PT 发生率前 10（受试者数，非事件数）", "", md_table(ae_top), "",
        "## 8. Table 14-3.01 风格：ADAS-Cog(11) 第 24 周较基线变化（LOCF，疗效人群）", "",
        md_table(adas_desc), "",
        f"ANCOVA：CHG ~ 治疗 + 中心组(SITEGR1) + 基线(BASE)，n={adas_stats['n']}，残差自由度={adas_stats['dof']}。", "",
        md_table(adas_contrast), "",
        f"剂量-反应检验（TRTPN 作为连续变量 0/54/81）p = {adas_stats['p_dose_response']:.4f}。", "",
        "## 9. Figure：首次皮肤类不良事件时间（ADTTE，KM）", "",
        md_table(tte_tab), "",
        f"Log-rank 检验（3 组）：χ² = {tte_stats['logrank_chi2']:.2f}，df = 2，p = {tte_stats['logrank_p']:.2g}。", "",
        "![KM curve](km_ttde.svg)", "",
        "## 10. Listing：严重不良事件列表（前 10 行）", "", md_table(listing), "",
    ]
    (OUT_DIR / "real_data_examples.md").write_text("\n".join(md), encoding="utf-8")

    metrics = {
        "sources": {k: {"standard": v[0], "url": v[1], "sha256": sha256(paths[k]), "rows": int(len(data[k]))} for k, v in SOURCES.items()},
        "adsl_rederivation_qc": qc_stats,
        "population": pop.to_dict(orient="records"),
        "safety_denominators": denom,
        "teae_subjects_total": int(te["USUBJID"].nunique()),
        "teae_records_total": int(len(te)),
        "adas_week24": {**adas_stats, "contrasts": adas_contrast.to_dict(orient="records")},
        "ttde": {**tte_stats, "by_arm": tte_tab.to_dict(orient="records")},
    }
    (OUT_DIR / "real_data_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ["adsl_rederivation_qc", "teae_subjects_total", "adas_week24", "ttde"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

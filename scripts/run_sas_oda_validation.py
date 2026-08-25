from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import saspy
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
CACHE = ROOT / "cache"
OUT.mkdir(parents=True, exist_ok=True)

CONTROLLED_CLAIM = "PORTFOLIO_SAS_ODA_EXECUTION_RECONCILED"
EVIDENCE_BOUNDARY = (
    "SAS executed remotely in SAS OnDemand for Academics from a GitHub-hosted runner. "
    "Independent public-data portfolio evidence only; not sponsor/CRO production, "
    "not a validated GxP environment, not formal second-programmer sign-off, "
    "not formal ADaM conformance, and not a regulatory submission package."
)


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, na_values=["NA", ""], keep_default_na=True)


def _norm_str(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _norm_date(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        dates = pd.Timestamp("1960-01-01") + pd.to_timedelta(numeric, unit="D")
        return dates.dt.strftime("%Y-%m-%d").fillna("")
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d").fillna("")


def _program_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _submit(sas: saspy.SASsession, path: Path) -> str:
    result = sas.submit(_program_text(path), results="text")
    log = str(result.get("LOG", ""))
    errors = [
        line.strip()
        for line in log.splitlines()
        if re.match(r"^\s*ERROR(?:\s+\d+-\d+)?:", line, flags=re.IGNORECASE)
    ]
    if errors:
        (OUT / f"{path.stem}_sas_error.log").write_text(log, encoding="utf-8")
        raise RuntimeError(f"SAS execution failed for {path.name}: {errors[:3]}")
    return log


def _to_work(sas: saspy.SASsession, frame: pd.DataFrame, table: str) -> None:
    sas.df2sd(frame, table=table, libref="work")
    if not sas.exist(table, "work"):
        raise RuntimeError(f"WORK.{table} was not created on SAS ODA")


def _from_work(sas: saspy.SASsession, table: str) -> pd.DataFrame:
    if not sas.exist(table, "work"):
        raise RuntimeError(f"Expected SAS output WORK.{table} does not exist")
    return sas.sasdata(table, "work").to_df()


def _compare_keys(area: str, sas_df: pd.DataFrame, ref_df: pd.DataFrame, keys: list[str], rows: list[dict[str, object]]) -> bool:
    sas_keys = set(map(tuple, sas_df[keys].fillna("").astype(str).to_numpy()))
    ref_keys = set(map(tuple, ref_df[keys].fillna("").astype(str).to_numpy()))
    passed = sas_keys == ref_keys and not sas_df.duplicated(keys).any()
    rows.append({"area":area,"check":"unique_key_set","passed":passed,"sas_value":len(sas_keys),"reference_value":len(ref_keys),"detail":f"keys={','.join(keys)}; sas_only={len(sas_keys-ref_keys)}; ref_only={len(ref_keys-sas_keys)}"})
    return passed


def _compare_columns(area: str, sas_df: pd.DataFrame, ref_df: pd.DataFrame, keys: list[str], string_cols: Iterable[str], numeric_cols: Iterable[str], date_cols: Iterable[str], rows: list[dict[str, object]], numeric_tol: float = 1e-10) -> bool:
    s = sas_df.copy(); r = ref_df.copy()
    for key in keys:
        s[key] = _norm_str(s[key]); r[key] = _norm_str(r[key])
    merged = s.merge(r, on=keys, how="outer", suffixes=("_sas", "_ref"), indicator=True)
    all_pass = bool((merged["_merge"] == "both").all())
    for col in string_cols:
        a = _norm_str(merged[f"{col}_sas"]); b = _norm_str(merged[f"{col}_ref"])
        mism = int((a != b).sum()); passed = mism == 0; all_pass &= passed
        rows.append({"area":area,"check":f"{col}_exact","passed":passed,"sas_value":len(merged)-mism,"reference_value":len(merged),"detail":f"mismatches={mism}"})
    for col in numeric_cols:
        a = pd.to_numeric(merged[f"{col}_sas"], errors="coerce"); b = pd.to_numeric(merged[f"{col}_ref"], errors="coerce")
        both_missing = a.isna() & b.isna(); diff = (a-b).abs(); bad = ~(both_missing | (diff <= numeric_tol))
        mism = int(bad.sum()); max_diff = float(diff[~both_missing].max()) if (~both_missing).any() else 0.0
        passed = mism == 0; all_pass &= passed
        rows.append({"area":area,"check":f"{col}_numeric","passed":passed,"sas_value":max_diff,"reference_value":numeric_tol,"detail":f"mismatches={mism}; max_abs_diff={max_diff:.12g}"})
    for col in date_cols:
        a = _norm_date(merged[f"{col}_sas"]); b = _norm_date(merged[f"{col}_ref"])
        mism = int((a != b).sum()); passed = mism == 0; all_pass &= passed
        rows.append({"area":area,"check":f"{col}_date","passed":passed,"sas_value":len(merged)-mism,"reference_value":len(merged),"detail":f"mismatches={mism}"})
    return all_pass


def _teae_reconcile(sas_subjects: pd.DataFrame, ref_table: pd.DataFrame, rows: list[dict[str, object]]) -> bool:
    s = sas_subjects.copy(); s["TRT01A"] = _norm_str(s["TRT01A"]); s["ANY_TEAE"] = pd.to_numeric(s["ANY_TEAE"], errors="coerce").fillna(0).astype(int)
    placebo = s.loc[s["TRT01A"].eq("Placebo")]; n0 = len(placebo); e0 = int(placebo["ANY_TEAE"].sum()); all_pass = True
    for arm in ["Xanomeline Low Dose", "Xanomeline High Dose"]:
        g = s.loc[s["TRT01A"].eq(arm)]; n1 = len(g); e1 = int(g["ANY_TEAE"].sum()); p1 = e1/n1; p0 = e0/n0; rd = p1-p0
        _, fp = fisher_exact([[e1,n1-e1],[e0,n0-e0]], alternative="two-sided")
        ref = ref_table.loc[ref_table["comparison"].eq(f"{arm} vs Placebo")].iloc[0]
        checks = {
            f"{arm}_n_arm":(n1,int(ref["n_arm"]),n1==int(ref["n_arm"])),
            f"{arm}_n_placebo":(n0,int(ref["n_placebo"]),n0==int(ref["n_placebo"])),
            f"{arm}_risk_arm":(round(p1,4),float(ref["risk_arm"]),round(p1,4)==float(ref["risk_arm"])),
            f"{arm}_risk_placebo":(round(p0,4),float(ref["risk_placebo"]),round(p0,4)==float(ref["risk_placebo"])),
            f"{arm}_risk_difference":(round(rd,4),float(ref["risk_difference"]),round(rd,4)==float(ref["risk_difference"])),
            f"{arm}_fisher_p":(round(float(fp),6),float(ref["fisher_p"]),abs(round(float(fp),6)-float(ref["fisher_p"]))<=1e-6),
        }
        for name,(got,expected,passed) in checks.items():
            all_pass &= bool(passed)
            rows.append({"area":"TEAE_TFL","check":name,"passed":bool(passed),"sas_value":got,"reference_value":expected,"detail":"Derived from SAS-created subject-level ANY_TEAE population; PROC FREQ ODS outputs retained separately."})
    return all_pass


def _find_mmrm_contrasts(diffs: pd.DataFrame, reference: pd.DataFrame, rows: list[dict[str, object]]) -> bool:
    if diffs.empty:
        rows.append({"area":"MMRM_TFL","check":"ods_diffs_nonempty","passed":False,"sas_value":0,"reference_value":">0","detail":""}); return False
    cols = list(diffs.columns)
    estimate_col = next((c for c in cols if c.lower()=="estimate"), None)
    se_col = next((c for c in cols if c.lower() in {"stderr","standarderror","std_err","se"}), None)
    trt_cols = [c for c in cols if "trt01a" in c.lower()]
    visit_cols = [c for c in cols if "avisitn" in c.lower()]
    if estimate_col is None or se_col is None or len(trt_cols)<2 or len(visit_cols)<2:
        rows.append({"area":"MMRM_TFL","check":"ods_schema_recognised","passed":False,"sas_value":"|".join(cols),"reference_value":"Estimate+StdErr+paired TRT01A/AVISITN","detail":"Raw ODS Diffs is uploaded for inspection."}); return False
    all_pass=True; tol=0.0005
    for arm in ["Xanomeline Low Dose","Xanomeline High Dose"]:
        ref = reference.loc[reference["contrast"].eq(f"{arm} vs Placebo") & reference["AVISIT"].eq("Week 24")].iloc[0]
        candidate=None; direction=1.0
        for _,rr in diffs.iterrows():
            trt_values=[str(rr[c]).strip() for c in trt_cols]
            visit_values=[pd.to_numeric(pd.Series([rr[c]]),errors="coerce").iloc[0] for c in visit_cols]
            if arm in trt_values and "Placebo" in trt_values and all(v==24 for v in visit_values if pd.notna(v)):
                candidate=rr; direction=1.0 if str(rr[trt_cols[0]]).strip()==arm else -1.0; break
        if candidate is None:
            rows.append({"area":"MMRM_TFL","check":f"{arm}_week24_row","passed":False,"sas_value":"missing","reference_value":"present","detail":f"trt_cols={trt_cols}; visit_cols={visit_cols}"}); all_pass=False; continue
        est=direction*float(candidate[estimate_col]); se=float(candidate[se_col]); est_diff=abs(est-float(ref["estimate"])); se_diff=abs(se-float(ref["SE"])); passed=est_diff<=tol and se_diff<=tol and np.sign(est)==np.sign(float(ref["estimate"]))
        all_pass &= passed
        rows.append({"area":"MMRM_TFL","check":f"{arm}_week24_estimate_se","passed":passed,"sas_value":f"estimate={est:.9g}; SE={se:.9g}","reference_value":f"estimate={float(ref['estimate']):.9g}; SE={float(ref['SE']):.9g}","detail":f"estimate_abs_diff={est_diff:.6g}; se_abs_diff={se_diff:.6g}; tolerance={tol}"})
    return all_pass


def main() -> None:
    cfgfile=os.environ.get("SASPY_CFGFILE")
    if not cfgfile: raise SystemExit("SASPY_CFGFILE is not set")
    required=[CACHE/"dm.csv",CACHE/"ae.csv",CACHE/"ds.csv",CACHE/"ex.csv",OUT/"adsl_style.csv",OUT/"adae_style.csv",OUT/"adqs_actot_style.csv",OUT/"table7_teae_risk_difference.csv",OUT/"mmrm_treatment_contrasts.csv",OUT/"mmrm_analysis_dataset.csv"]
    missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing: raise SystemExit(f"Local validated references missing before SAS ODA run: {missing}")
    qc_rows=[]; sas=saspy.SASsession(cfgname="oda",cfgfile=cfgfile,results="TEXT")
    try:
        _submit(sas,ROOT/"sas"/"macros"/"qc_contract.sas")
        for domain in ["dm","ex","ds","ae"]: _to_work(sas,_read(CACHE/f"{domain}.csv"),domain)
        _submit(sas,ROOT/"sas"/"oda"/"derive_adsl_adae.sas")
        sas_adsl=_from_work(sas,"adsl"); sas_adae=_from_work(sas,"adae"); sas_adsl.to_csv(OUT/"sas_oda_adsl_style.csv",index=False); sas_adae.to_csv(OUT/"sas_oda_adae_style.csv",index=False)
        ref_adsl=_read(OUT/"adsl_style.csv"); ref_adae=_read(OUT/"adae_style.csv")
        adsl_ok=_compare_keys("ADSL",sas_adsl,ref_adsl,["STUDYID","USUBJID"],qc_rows)
        adsl_ok &= _compare_columns("ADSL",sas_adsl,ref_adsl,["STUDYID","USUBJID"],["TRT01P","TRT01A","TRTSDTSRC","TRTEDTSRC","RANDFL","SAFFL","COMPLFL","DCSFL"],["TRTDURN","EXN","EXDOSE_MAX","EXDOSE_MEAN"],["TRTSDT","TRTEDT"],qc_rows,1e-8)
        adae_ok=_compare_keys("ADAE",sas_adae,ref_adae,["STUDYID","USUBJID","AESEQ"],qc_rows)
        adae_ok &= _compare_columns("ADAE",sas_adae,ref_adae,["STUDYID","USUBJID","AESEQ"],["TRT01A","SAFFL","TRTEMFL","RELFL","MODSEVFL"],["ASTDY"],["ASTDT","AENDT"],qc_rows,1e-8)
        _submit(sas,ROOT/"sas"/"oda"/"teae_risk_difference.sas")
        safety_teae=_from_work(sas,"safety_teae"); safety_teae.to_csv(OUT/"sas_oda_teae_subjects.csv",index=False)
        ods_names=["rd0_low","rd1_low","fisher_low","rd0_high","rd1_high","fisher_high"]; ods_nonempty=True; nonempty_count=0
        for name in ods_names:
            frame=_from_work(sas,name); frame.to_csv(OUT/f"sas_oda_{name}.csv",index=False); nonempty_count += int(not frame.empty); ods_nonempty &= not frame.empty
        qc_rows.append({"area":"TEAE_TFL","check":"proc_freq_ods_outputs_nonempty","passed":ods_nonempty,"sas_value":nonempty_count,"reference_value":len(ods_names),"detail":"RiskDiffCol1/2 and FishersExact captured for both active-vs-placebo comparisons."})
        teae_ok=ods_nonempty and _teae_reconcile(safety_teae,_read(OUT/"table7_teae_risk_difference.csv"),qc_rows)
        _to_work(sas,_read(OUT/"adqs_actot_style.csv"),"adqs_actot")
        _submit(sas,ROOT/"sas"/"oda"/"actot_mmrm_primary.sas")
        sas_mmrm_analysis=_from_work(sas,"mmrm_analysis"); sas_mmrm_diffs=_from_work(sas,"mmrm_diffs"); sas_mmrm_lsmeans=_from_work(sas,"mmrm_lsmeans")
        sas_mmrm_analysis.to_csv(OUT/"sas_oda_mmrm_analysis_dataset.csv",index=False); sas_mmrm_diffs.to_csv(OUT/"sas_oda_mmrm_diffs.csv",index=False); sas_mmrm_lsmeans.to_csv(OUT/"sas_oda_mmrm_lsmeans.csv",index=False)
        ref_mmrm=_read(OUT/"mmrm_analysis_dataset.csv")
        mmrm_rows_ok=_compare_keys("MMRM_ANALYSIS_ROWS",sas_mmrm_analysis,ref_mmrm,["STUDYID","USUBJID","AVISIT"],qc_rows)
        mmrm_rows_ok &= _compare_columns("MMRM_ANALYSIS_ROWS",sas_mmrm_analysis,ref_mmrm,["STUDYID","USUBJID","AVISIT"],["TRT01A"],["QSSEQ","AVAL","BASE","CHG"],[],qc_rows,1e-12)
        mmrm_est_ok=_find_mmrm_contrasts(sas_mmrm_diffs,_read(OUT/"mmrm_treatment_contrasts.csv"),qc_rows); mmrm_ok=mmrm_rows_ok and mmrm_est_ok
    finally:
        try: sas.endsas()
        except Exception: pass
    qc=pd.DataFrame(qc_rows); qc["required"]=True; qc.to_csv(OUT/"sas_oda_execution_qc.csv",index=False); all_passed=bool(qc["passed"].all())
    metrics={"version":"0.26.1","sas_runtime":"SAS OnDemand for Academics via SASPy Remote IOM","sas_runtime_executed":True,"analysis_dataset_programs_executed":1,"tfl_programs_executed":2,"adsl_rows":int(len(sas_adsl)),"adae_rows":int(len(sas_adae)),"teae_subject_rows":int(len(safety_teae)),"mmrm_analysis_rows":int(len(sas_mmrm_analysis)),"mmrm_ods_diff_rows":int(len(sas_mmrm_diffs)),"required_checks":int(len(qc)),"required_passed":int(qc["passed"].sum()),"all_required_passed":all_passed,"controlled_claim":CONTROLLED_CLAIM if all_passed else None,"evidence_boundary":EVIDENCE_BOUNDARY}
    (OUT/"sas_oda_validation_metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    summary=("# SAS ODA execution validation\n\n"+f"- Runtime executed: **{metrics['sas_runtime_executed']}**\n"+f"- SAS analysis-dataset programs executed: **{metrics['analysis_dataset_programs_executed']}**\n"+f"- SAS TFL/statistical programs executed: **{metrics['tfl_programs_executed']}**\n"+f"- ADSL rows: **{metrics['adsl_rows']}**; ADAE rows: **{metrics['adae_rows']}**\n"+f"- MMRM analysis rows: **{metrics['mmrm_analysis_rows']}**; ODS Diffs rows: **{metrics['mmrm_ods_diff_rows']}**\n"+f"- Required reconciliation checks: **{metrics['required_passed']}/{metrics['required_checks']}**\n"+f"- Controlled claim: `{metrics['controlled_claim']}`\n\n"+f"Evidence boundary: {EVIDENCE_BOUNDARY}\n")
    (OUT/"sas_oda_validation_summary.md").write_text(summary,encoding="utf-8"); print(json.dumps(metrics,indent=2,sort_keys=True))
    if not all_passed: raise SystemExit("SAS ODA execution completed but reconciliation gate failed; inspect outputs/sas_oda_execution_qc.csv")


if __name__ == "__main__": main()

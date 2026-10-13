#!/usr/bin/env python3
"""Independent re-derivation from synthetic DM/EX/PC/VS, with auditable pass/fail."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import hashlib
import math
from pathlib import Path

ROOT = Path("case_studies/nonmem_dataflow_demo/advanced")
COLS = ("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT",
        "WT","AGE","SEX","BLQ","LLOQ","CENS")

def read(path: Path) -> list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def parsedate(value: str) -> datetime:
    parsed = datetime.strptime(value,"%Y-%m-%dT%H:%M:%S")
    if parsed.strftime("%Y-%m-%dT%H:%M:%S") != value:
        raise ValueError(f"Noncanonical/partial date: {value!r}")
    return parsed

def hours(a: datetime,b: datetime)->float:
    return (a-b).total_seconds()/3600

def check_qc(source:Path,output:Path)->list[dict[str,str]]:
    dm,ex,pc,vs=(read(source/f"{domain}.csv") for domain in ("dm","ex","pc","vs"))
    mode=(output/"metadata/blq_mode.txt").read_text(encoding="utf-8").strip()
    if mode not in {"m1","m3"}: raise ValueError("Unknown BLQ mode")
    review=read(output/"data/nonmem_input_review.csv")
    cw=read(output/"metadata/subject_crosswalk.csv")
    results=[]
    def ck(subject,name,ok,found="",action="Review source and regenerate"):
        results.append(dict(subject=subject,check=name,result="PASS" if ok else "FAIL",
            finding="" if ok else found,follow_up="" if ok else action,
            qc_script="advanced/scripts/20_independent_qc.py"))
    schema_ok=bool(review) and tuple(review[0].keys())==COLS+("SOURCE_KEY",)
    ck("ALL","schema",schema_ok,"Column order and SOURCE_KEY mismatch")
    dm_subjects=[d["USUBJID"] for d in dm]
    ids={r["USUBJID"]:int(r["ID"]) for r in cw}
    ck("ALL","crosswalk",len(ids)==len(dm_subjects)==len(set(dm_subjects)) and
       set(dm_subjects)==set(ids) and len(set(ids.values()))==len(ids),
       "Missing or duplicate subject ID")
    exkeys=[(r["USUBJID"],r["EXSEQ"]) for r in ex]
    pckeys=[(r["USUBJID"],r["PCSEQ"]) for r in pc]
    ck("ALL","source_keys",len(exkeys)==len(set(exkeys)) and len(pckeys)==len(set(pckeys)),
       "Duplicate EXSEQ/PCSEQ")
    if not (schema_ok and set(dm_subjects)==set(ids)): return results
    check_fields=COLS
    expected_all=[]
    for d in dm:
        s=d["USUBJID"]; ident=ids[s]
        ee=[z for z in ex if z["USUBJID"]==s]
        pp=[z for z in pc if z["USUBJID"]==s]
        ww=[z for z in vs if z["USUBJID"]==s and z["VSTESTCD"]=="WEIGHT"]
        if not ee or not pp or len(ww)!=1:
            ck(s,"source_cardinality",False,"Missing EX, PC or exactly one baseline weight");continue
        first=min(parsedate(z["EXSTDTC"]) for z in ee)
        wt=float(ww[0]["VSSTRESN"])*(0.001 if ww[0]["VSSTRESU"]=="g" else 1.0)
        if parsedate(ww[0]["VSDTC"])>first:
            ck(s,"weight_timing",False,"Post-dose weight not allowed");continue
        sex=1 if d["SEX"]=="M" else 0
        age=float(d["AGE"])
        exp=[]
        for e in ee:
            route=e["EXROUTE"];dur=float(e["EXDURH"])
            amount=float(e["EXDOSE"])*(0.001 if e["EXDOSU"]=="ug" else 1)
            if route not in {"ORAL","IV_INFUSION"} or ((route=="ORAL")!=(dur==0)):
                ck(s,"route_duration",False,"Route/duration mismatch");continue
            rate=amount/dur if route=="IV_INFUSION" else 0
            t=hours(parsedate(e["EXSTDTC"]),first)
            exp.append((dict(zip(check_fields,(ident,t,0,1,1,0,amount,rate,
                   2 if route=="IV_INFUSION" else 1,wt,age,sex,0,0,0))),
                   "EX:"+s+":"+e["EXSEQ"]))
        for p in pp:
            t=parsedate(p["PCDTC"])
            prior=[parsedate(e["EXSTDTC"]) for e in ee if parsedate(e["EXSTDTC"])<=t]
            if not prior:
                ck(s,"sample_timing",False,"Pre-dose PC sample");continue
            blq=int(p["BLQ_FLAG"]=="Y")
            ll=float(p["LLOQ_NG_ML"])
            if blq:
                if p["PCSTRESN"]: ck(s,"blq_value",False,"BLQ record has numeric observation")
                dv=ll if mode=="m3" else 0
            else:
                if not p["PCSTRESN"]:
                    ck(s,"observed_value",False,"Unflagged sample has no DV");continue
                dv=float(p["PCSTRESN"])*(1000 if p["PCSTRESU"]=="mg/L" else 1)
                if dv<ll: ck(s,"lower_limit",False,"Unflagged DV below LLOQ")
            exp.append((dict(zip(check_fields,(ident,hours(t,first),hours(t,max(prior)),
                  0,int(bool(blq) and mode=="m1"),dv,0,0,2,wt,age,sex,blq,ll,blq))),
                  "PC:"+s+":"+p["PCSEQ"]))
        exp.sort(key=lambda pair:(pair[0]["ID"],pair[0]["TIME"],-pair[0]["EVID"],pair[1]))
        actual=[r for r in review if int(r["ID"])==ident]
        ck(s,"event_count",len(actual)==len(exp),
           f"Generated {len(actual)} records; source expects {len(exp)}")
        if len(actual)!=len(exp):continue
        for n,((want,key),got) in enumerate(zip(exp,actual),1):
            same_key=got["SOURCE_KEY"]==key
            matches=all(math.isclose(float(got[field]),float(want[field]),
                       abs_tol=1e-8,rel_tol=1e-9) for field in check_fields)
            ck(s,f"event_{n:03d}",same_key and matches,
               f"Source mismatch: {key}; keys_match={same_key}, values_match={matches}",
               "Raise source query; resolve mapping and review EVID/MDV/CMT/DV/RATE")
        expected_all.extend(exp)
    ck("ALL","total_event_count",len(review)==len(ex)+len(pc),
       "Unmatched exposure or concentration event")
    data=(output/"data/nonmem_input.csv").read_text(encoding="utf-8").splitlines()
    ck("ALL","headerless_row_count",len(data)==len(review),"Input file record count incorrect")
    for n,(line,row) in enumerate(zip(data,review),1):
        parts=line.split(",")
        ok=len(parts)==len(COLS) and all(math.isclose(float(actual),float(row[k]),
                   rel_tol=1e-9,abs_tol=1e-8) for actual,k in zip(parts,COLS))
        ck("ALL",f"numeric_export_{n:03d}",ok,"Model CSV not equal to reviewed fields",
           "Re-export NONMEM model input using controlled input order")
    ctl=output/"model"/f"one_compartment_{mode}_unexecuted.ctl"
    model=ctl.read_text(encoding="utf-8")
    ck("ALL","model_data_link","$DATA ../data/nonmem_input.csv" in model,
       "Model does not point to relative packaged input")
    ck("ALL","model_input_order",
       "$INPUT "+" ".join(COLS) in model,"Control-file input order differs")
    ck("ALL","blq_mode_rules",
       (mode=="m3" and all(int(float(r["MDV"]))==0 and int(float(r["CENS"]))==1
          for r in review if r["SOURCE_KEY"].startswith("PC:") and int(float(r["BLQ"]))==1))
       or (mode=="m1" and all(int(float(r["MDV"]))==1
          for r in review if r["SOURCE_KEY"].startswith("PC:") and int(float(r["BLQ"]))==1)),
       "BLQ data representation does not match selected M1/M3")
    ck("ALL","no_unexpected_files",set(r["SOURCE_KEY"] for r in review)==set(k for _,k in expected_all),
       "Input includes untraced or missing source event")
    return results

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--output-dir",type=Path,default=Path("outputs/nonmem_advanced/m3"))
    arg=parser.parse_args()
    dest=arg.output_dir/"qc";dest.mkdir(parents=True,exist_ok=True)
    try:checks=check_qc(arg.source_dir,arg.output_dir)
    except (ValueError,KeyError,TypeError,OSError,ZeroDivisionError,OverflowError) as error:
        checks=[dict(subject="ALL",check="fatal_qc_error",result="FAIL",
            finding=f"{type(error).__name__}: {error}", follow_up="Investigate input/derivation",
            qc_script="advanced/scripts/20_independent_qc.py")]
    with (dest/"qc_log.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=("subject","check","result","finding","follow_up","qc_script"))
        writer.writeheader();writer.writerows(checks)
    failed=sum(c["result"]=="FAIL" for c in checks)
    (dest/"qc_summary.md").write_text(
        f"# Advanced synthetic PK dataflow independent QC\n\n"
        f"PASS {len(checks)-failed}/{len(checks)}; FAIL {failed}.\n\n"
        "This independent source reconstruction is not sponsor second-programmer sign-off.\n",
        encoding="utf-8")
    print(f"Advanced independent QC: {len(checks)-failed}/{len(checks)} PASS")
    return 1 if failed else 0

if __name__=="__main__":raise SystemExit(main())

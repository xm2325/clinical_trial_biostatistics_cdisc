#!/usr/bin/env python3
"""Independent source-to-dataset QC + public-data pooled PK least squares.

This fit is scipy nonlinear least squares, NOT NONMEM or population NLME. No
ETAs, IIV, BLQ likelihood, confidence intervals or sponsor validation claimed.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares

ROOT=Path("outputs/nonmem_theoph_public")
COLS=("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT",
      "WT","AGE","SEX","BLQ","LLOQ","CENS")

def read(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def run(output:Path)->int:
    src=read(output/"data/public_theoph_source_export.csv")
    review=read(output/"data/nonmem_input_review.csv")
    mapping=read(output/"metadata/subject_crosswalk.csv")
    ids={r["USUBJID"].split("_",1)[1]:int(r["ID"]) for r in mapping}
    if len(ids)!=12 or len(src)!=132 or len(review)!=144:raise ValueError("unexpected Theoph cardinality")
    if tuple(review[0])!=COLS+("SOURCE_KEY",):raise ValueError("unexpected schema")
    assert all(int(float(r["EVID"])) in (0,1) for r in review)
    records=[]
    for sub in sorted(ids):
        sources=[r for r in src if r["SUBJECT"]==sub]
        data=[r for r in review if int(float(r["ID"]))==ids[sub]]
        doses=[r for r in data if int(float(r["EVID"]))==1]
        samples=[r for r in data if int(float(r["EVID"]))==0]
        if len(doses)!=1 or len(sources)!=len(samples):raise ValueError("event cardinality mismatch")
        expected_amount=float(sources[0]["DOSE_MG_KG"])*float(sources[0]["WT_KG"])
        if not math.isclose(float(doses[0]["AMT"]),expected_amount,rel_tol=1e-11):
            raise ValueError("incorrect mg/kg->mg dose")
        for n,(source,row) in enumerate(zip(sources,samples),1):
            if row["SOURCE_KEY"] != f"THEOPH:{sub}:{n}":
                raise ValueError(f"mismatched subject/source row identity {sub}:{n}")
            pair=(("TIME","TIME_H",1),("DV","CONC_MG_L",1000),("WT","WT_KG",1))
            if not all(math.isclose(float(row[dst]),float(source[src_col])*scale,
               rel_tol=1e-11,abs_tol=1e-10) for dst,src_col,scale in pair):
                raise ValueError("published PK value or unit mismatch")
            if float(row["AGE"])!=-99 or float(row["SEX"])!=-1 or float(row["LLOQ"])!=0:
                raise ValueError("undocumented demographics/assay limit were fabricated")
            records.append((ids[sub],float(row["TIME"]),expected_amount,float(row["DV"])/1000))
    headerless=(output/"data/nonmem_input.csv").read_text(encoding="utf-8").splitlines()
    if len(headerless)!=len(review):raise ValueError("headerless row count mismatch")
    for line,row in zip(headerless,review):
        fields=line.split(",")
        if len(fields)!=len(COLS) or not all(math.isclose(float(fields[i]),float(row[c]),
                   rel_tol=1e-10,abs_tol=1e-8) for i,c in enumerate(COLS)):
            raise ValueError("headerless model input differs from review data")

    ids_arr=np.array([r[0] for r in records],dtype=int)
    times=np.array([r[1] for r in records])
    doses=np.array([r[2] for r in records])
    obs=np.array([r[3] for r in records]) # mg/L, not ng/mL
    train=ids_arr<=8;test=ids_arr>8
    def calc(par,t,d):
        cl,v,ka=par;k=cl/v
        if abs(ka-k)<1e-5:
            contribution=d*ka*t*np.exp(-k*t)
        else:
            contribution=d*ka/(ka-k)*(np.exp(-k*t)-np.exp(-ka*t))
        return contribution/v
    def err(par):return calc(par,times[train],doses[train])-obs[train]
    fit=least_squares(err,x0=np.array([4.,40.,1.]),
       bounds=(np.array([0.01,1.,0.01]),np.array([50.,500.,10.])),
       max_nfev=2500,ftol=1e-11,xtol=1e-11,gtol=1e-11)
    if not fit.success or not np.all(np.isfinite(fit.x)):
        raise ValueError(f"scipy fitting failed: {fit.message}")
    fitted=calc(fit.x,times,doses)
    rmse=lambda a:float(np.sqrt(np.mean((fitted[a]-obs[a])**2)))
    result={"source":"R datasets::Theoph","subjects":12,"samples":132,
        "observations_used_train":int(sum(train)),"observations_heldout":int(sum(test)),
        "model":"fixed-effect pooled oral one-compartment, nonlinear least squares; not population NLME",
        "parameters":{"CL_L_h":float(fit.x[0]),"V_L":float(fit.x[1]),"KA_per_h":float(fit.x[2])},
        "train_RMSE_mg_L":rmse(train),"heldout_RMSE_mg_L":rmse(test),
        "model_fitted":True,"NONMEM_executed":False,
        "patient_demographics_reported":False,"SDTM_qualified":False}
    folder=output/"validation";folder.mkdir(parents=True,exist_ok=True)
    (folder/"theoph_public_fit.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    with (folder/"theoph_public_fit_predictions.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(("ID","TIME_H","OBS_MG_L","FITTED_MG_L","SPLIT"))
        for id,t,y,p in zip(ids_arr,times,obs,fitted):
            w.writerow((id,t,y,p,"train" if id<=8 else "heldout"))
    (folder/"theoph_qc_summary.md").write_text(
       "# Public Theoph data QC\n\n"
       "PASS: 12 subject keys, 132 source concentration values, 12 source "
       "dose conversions, 144 headerless NONMEM-style events, absent "
       "age/sex flagged rather than invented.\n\n"
       "This is an independent Python reconstruction of the R package source export. "
       "The scipy fit is pooled fixed-effect least squares, not NONMEM "
       "nor a population PK random-effects analysis.\n",encoding="utf-8")
    print(f"Public Theoph source QC PASS; train RMSE={rmse(train):.5f} mg/L, heldout RMSE={rmse(test):.5f} mg/L")
    return 0

if __name__=="__main__":
    raise SystemExit(run(ROOT))

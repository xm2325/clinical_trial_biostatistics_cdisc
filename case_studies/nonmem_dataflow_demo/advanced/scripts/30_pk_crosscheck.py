#!/usr/bin/env python3
"""Oral + IV infusion reference predictions checked against independent ODE integration.

Only structural simulation at fixed illustrative parameters. Not NONMEM execution,
parameter estimation, external validation, pharmacometric qualification or fit.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import log_ndtr

@dataclass(frozen=True)
class Dose:
    t: float
    amt: float
    rate: float
    cmt: int

def load(path:Path)->list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def model_source(data:list[dict[str,str]])->dict[int,list[Dose]]:
    result={}
    for row in data:
        if int(float(row["EVID"]))==1:
            id=int(float(row["ID"]))
            result.setdefault(id,[]).append(Dose(float(row["TIME"]),float(row["AMT"]),
                              float(row["RATE"]),int(float(row["CMT"]))))
    return result

def analytic(t:float,doses:list[Dose],cl:float,v:float,ka:float)->float:
    """Closed-form solution for linear one-compartment with oral absorption/IV infusion."""
    k=cl/v
    a=0.0
    for d in doses:
        delta=t-d.t
        if delta < 0: continue
        if d.cmt==1 and d.rate==0:
            a+=d.amt*ka/(ka-k)*(math.exp(-k*delta)-math.exp(-ka*delta))
        elif d.cmt==2 and d.rate>0:
            dur=d.amt/d.rate
            if delta<=dur:
                a+=(d.rate/k)*(-math.expm1(-k*delta))
            else:
                a+=(d.rate/k)*(-math.expm1(-k*dur))*math.exp(-k*(delta-dur))
        else: raise ValueError("unsupported dose/route in analytic model")
    return 1000*a/v

def numeric(t:float,doses:list[Dose],cl:float,v:float,ka:float)->float:
    k=cl/v
    intervals={0.,t}
    for d in doses:
        if d.t<=t:
            intervals.add(d.t)
            if d.rate>0 and d.t+d.amt/d.rate<=t:intervals.add(d.t+d.amt/d.rate)
    boundaries=sorted(intervals)
    state=np.array([0.,0.]) # depot and central mg
    for index,left in enumerate(boundaries):
        state[0]+=sum(d.amt for d in doses if d.cmt==1 and d.rate==0
                       and math.isclose(d.t,left,abs_tol=1e-9))
        if index==len(boundaries)-1:break
        right=boundaries[index+1]
        mid=(left+right)/2
        rate=sum(d.rate for d in doses if d.cmt==2 and d.rate>0 and
                 d.t<=mid<d.t+d.amt/d.rate)
        def rhs(_t,y):
            return [-ka*y[0],ka*y[0]-k*y[1]+rate]
        sol=solve_ivp(rhs,(left,right),state,rtol=1e-10,atol=1e-11,method="DOP853")
        if not sol.success: raise RuntimeError(sol.message)
        state=sol.y[:,-1]
    return 1000*state[1]/v

def run(output:Path)->int:
    review=load(output/"data/nonmem_input_review.csv")
    doses=model_source(review)
    cl,v,ka=5.,40.,1.2
    rows=[]
    failed=[]
    for row in review:
        if int(float(row["EVID"]))!=0:continue
        id=int(float(row["ID"]));t=float(row["TIME"])
        closed=analytic(t,doses[id],cl,v,ka)
        ode=numeric(t,doses[id],cl,v,ka)
        err=abs(closed-ode)
        threshold=1e-5+1e-7*max(abs(closed),abs(ode))
        if err>threshold:failed.append((id,t,err))
        cens=int(float(row["CENS"]))
        ll=float(row["LLOQ"])
        logp=float(log_ndtr((ll-closed)/100.)) if cens else ""
        rows.append(dict(ID=id,TIME=t,SOURCE_KEY=row["SOURCE_KEY"],CENS=cens,
            MODEL_NG_ML=f"{closed:.10f}",ODE_NG_ML=f"{ode:.10f}",
            ABS_ERROR_NG_ML=f"{err:.10g}",M3_LOGCDF_DEMO=logp))
    dest=output/"validation"
    dest.mkdir(parents=True,exist_ok=True)
    with (dest/"pk_crosscheck.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else [])
        writer.writeheader();writer.writerows(rows)
    valid=bool(rows) and not failed
    (dest/"pk_crosscheck_summary.md").write_text(
        f"# Synthetic PK structural cross-check\n\n"
        f"Oral and intravenous infusion dosing, fixed CL={cl} L/h, V={v} L, "
        f"KA={ka} h^-1.\n\n"
        f"Analytic-versus-ODE checks: {len(rows)-len(failed)}/{len(rows)} PASS.\n\n"
        f"Maximum absolute error: {max(float(x['ABS_ERROR_NG_ML']) for x in rows) if rows else 'NA'} ng/mL.\n\n"
        "M3_LOGCDF_DEMO uses illustrative additive residual SD=100 ng/mL for "
        "censored records only. No PK parameter fitting or NONMEM execution was performed.\n",
        encoding="utf-8")
    print(f"Fixed-parameter analytic vs solve_ivp checks: {len(rows)-len(failed)}/{len(rows)} PASS")
    return 0 if valid else 1

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("outputs/nonmem_advanced/m3"))
    return run(p.parse_args().output_dir)

if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""Descriptive NCA of public R datasets::Theoph samples; no NONMEM required.

Computed on original mg/L concentration and hour values. Terminal phase uses
ONLY final three strictly positive samples (no adaptive window search).
Sparse data may make lambda_z not estimable; report that explicitly.
"""
import csv
import math
from pathlib import Path
import numpy as np
from scipy.integrate import trapezoid

root=Path("outputs/nonmem_theoph_public")
source=root/"data/public_theoph_source_export.csv"
with source.open(newline="",encoding="utf-8") as stream:
    original=list(csv.DictReader(stream))
subjects=sorted(set(r["SUBJECT"] for r in original))
if len(subjects)!=12 or len(original)!=132:
    raise ValueError("public source cardinality mismatch")
output=[]
for subject in subjects:
    d=[x for x in original if x["SUBJECT"]==subject]
    points=sorted([(float(x["TIME_H"]),float(x["CONC_MG_L"])) for x in d])
    t=np.array([x[0] for x in points],dtype=float)
    c=np.array([x[1] for x in points],dtype=float)
    if len(points)<3 or np.any(~np.isfinite(t)) or np.any(~np.isfinite(c)):
        raise ValueError("invalid PK samples")
    if np.any(np.diff(t)<=0) or np.any(t<0) or np.any(c<0):
        raise ValueError("nonascending time / negative concentration")
    auc=float(sum((float(c[i])+float(c[i+1]))/2*
                  (float(t[i+1])-float(t[i])) for i in range(len(t)-1)))
    scipy_auc=float(trapezoid(c,t))
    if not math.isclose(auc,scipy_auc,rel_tol=1e-12,abs_tol=1e-12):
        raise AssertionError("manual and scipy trapezoid mismatch")
    cmax=float(np.max(c))
    tmax=float(t[int(np.argmax(c))])
    pos=[i for i in range(len(c)) if c[i]>0 and t[i]>=tmax]
    kel=None;r2=None;t_half=None;aucinf=None
    if len(pos)>=3:
        terminal=pos[-3:]
        tx=t[terminal]; cy=np.log(c[terminal])
        beta=np.polyfit(tx,cy,1)
        pred=np.polyval(beta,tx)
        ss_tot=float(np.sum((cy-np.mean(cy))**2))
        r2=1-float(np.sum((cy-pred)**2))/ss_tot if ss_tot>0 else None
        if beta[0]<0:
            kel=-float(beta[0])
            t_half=float(math.log(2)/kel)
            aucinf=auc+float(c[-1])/kel
    output.append(dict(SUBJECT=subject,N_SAMPLES=len(d),
      CMAX_MG_L=round(cmax,9),TMAX_H=round(tmax,9),
      AUC_0_LAST_MG_H_L=round(auc,9),
      TERMINAL_LAMBDA_H_INV=round(kel,9) if kel is not None else "",
      TERMINAL_R2=round(r2,9) if r2 is not None else "",
      TERMINAL_HALF_LIFE_H=round(t_half,9) if t_half is not None else "",
      AUC_INF_MG_H_L=round(aucinf,9) if aucinf is not None else "",
      TERMINAL_METHOD="last 3 post-CMAX positive samples; descriptive only"))
dest=root/"validation"
dest.mkdir(parents=True,exist_ok=True)
with (dest/"theoph_nca_descriptive.csv").open("w",newline="",encoding="utf-8") as stream:
    writer=csv.DictWriter(stream,fieldnames=list(output[0]))
    writer.writeheader();writer.writerows(output)
estimable=sum(bool(o["TERMINAL_LAMBDA_H_INV"]) for o in output)
(dest/"theoph_nca_summary.md").write_text(
    f"# Descriptive NCA on published Theoph PK data\n\n"
    f"Source: R datasets::Theoph, {len(subjects)} subjects, {len(original)} observations.\n\n"
    "Independent manual linear trapezoid agrees with scipy.integrate.trapezoid "
    "for every subject. No extrapolation is used in AUC0-last.\n\n"
    f"Terminal slope estimated using a predeclared last-three-samples rule "
    f"for {estimable}/{len(subjects)} subjects. In other cases report not estimable.\n\n"
    "This is a simple teaching summary; it is not validated pharmacometric NCA, "
    "does not address BLQ because assay limits are absent, and is not NONMEM execution.\n",
    encoding="utf-8")
print(f"Public Theoph descriptive NCA: {len(subjects)}/{len(subjects)} AUC checks PASS; "
      f"terminal slope available for {estimable}/{len(subjects)}")

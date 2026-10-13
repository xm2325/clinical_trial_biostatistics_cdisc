#!/usr/bin/env python3
"""Executable reference for M1 omission versus M3 censored-normal likelihood.

SYNTHETIC one-compartment oral PK with fixed V and KA, fitting CL and additive SD.
This is scipy likelihood estimation, NOT NONMEM, NLME, IIV or GxP model validation.
The generated output NEVER includes the hidden true BLQ concentration.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr

SEED = 20261013
N_SUBJECTS = 40
TIME_H = np.array([0.15, 0.35, 0.75, 1.5, 3., 6., 10., 16., 24., 32.])
DOSE_MG = 100.
V_L = 40.
KA_H = 1.2
TRUE_CL_L_H = 5.
TRUE_SD_NG_ML = 170.
LLOQ_NG_ML = 550.


def predicted(t: np.ndarray, clearance: float) -> np.ndarray:
    k = clearance / V_L
    # stable neighbourhood of ka==k
    if math.isclose(k, KA_H, rel_tol=1e-6):
        central = DOSE_MG * KA_H * t * np.exp(-k*t)
    else:
        central = (DOSE_MG * KA_H / (KA_H-k)) * (
            np.exp(-k*t)-np.exp(-KA_H*t))
    return 1000. * central / V_L


def make_source() -> tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray,np.ndarray]:
    rng = np.random.default_rng(SEED)
    subjects=np.repeat(np.arange(1,N_SUBJECTS+1), len(TIME_H))
    times=np.tile(TIME_H,N_SUBJECTS)
    concentration=predicted(times,TRUE_CL_L_H)+rng.normal(
        0,TRUE_SD_NG_ML,size=times.size)
    censored=concentration<LLOQ_NG_ML
    # Replace hidden BLQ observations with a threshold placeholder.
    reported=np.where(censored,LLOQ_NG_ML,concentration)
    return subjects,times,reported,censored,concentration


def negative_log_likelihood(params, time, observed, censored, strategy):
    cl,sd=(float(params[0]),float(params[1]))
    if cl<=0 or sd<=0: return 1e100
    pred=predicted(time,cl)
    uncensored=~censored
    residual=(observed[uncensored]-pred[uncensored])/sd
    # constants kept for comparable calculation, despite M1 vs M3 sample scopes
    normal_ll=-0.5*residual**2-np.log(sd)-0.5*np.log(2*np.pi)
    total=float(np.sum(normal_ll))
    if strategy=="M3":
        z=(LLOQ_NG_ML-pred[censored])/sd
        total+=float(np.sum(log_ndtr(z)))
    elif strategy!="M1":
        raise ValueError("strategy must be M1 or M3")
    return -total


def fit(time, observed, censored, strategy):
    fun=lambda par:negative_log_likelihood(par,time,observed,censored,strategy)
    result=minimize(fun, x0=[7.0,230.0],method="L-BFGS-B",
                    bounds=[(0.2,30.),(20.,1500.)],
                    options={"maxiter":3000,"ftol":1e-11})
    if not result.success or not np.all(np.isfinite(result.x)):
        raise ValueError(f"{strategy} optimisation failed: {result.message}")
    return dict(CL_L_h=float(result.x[0]),
                additive_SD_ng_mL=float(result.x[1]),
                negative_log_likelihood=float(result.fun),
                converged=True, iterations=int(result.nit))


def likelihood_math_checks():
    # Independent error-function check at ordinary z values, and
    # underflow-safe censored tail at z=-25.
    for z in (-4.,-2.,-0.1,0.,1.,3.,5.):
        expected=math.log(0.5*math.erfc(-z/math.sqrt(2.)))
        if abs(float(log_ndtr(z))-expected)>1e-10:
            raise AssertionError(f"logcdf numerical mismatch at z={z}")
    if not math.isfinite(float(log_ndtr(-25.))):
        raise AssertionError("Censored log CDF underflow")
    t=np.array([0.5,2.])
    dv=np.array([LLOQ_NG_ML,1200.])
    cens=np.array([True,False])
    expected=(math.log(0.5*math.erfc(-(
        (LLOQ_NG_ML-predicted(t[:1],5.)[0])/170.)/math.sqrt(2.)))-
              0.5*((dv[1]-predicted(t[1:],5.)[0])/170.)**2-
              math.log(170.)-0.5*math.log(2*math.pi))
    observed_ll=-negative_log_likelihood([5.,170.],t,dv,cens,"M3")
    if not math.isclose(expected,observed_ll,abs_tol=1e-8):
        raise AssertionError("Manual M3 likelihood comparison failed")


def run(out_dir:Path):
    likelihood_math_checks()
    subjects,times,observed,censored,true_values=make_source()
    if censored.sum()<30 or censored.sum()>350:
        raise AssertionError("Simulation BLQ fraction outside planned stress range")
    m1=fit(times,observed,censored,"M1")
    m3=fit(times,observed,censored,"M3")
    # To prove the reported data never leak hidden BLQ observations:
    if not np.all(observed[censored]==LLOQ_NG_ML):
        raise AssertionError("Censored observations leaked from hidden measurement")
    out_dir.mkdir(parents=True,exist_ok=True)
    rows=[dict(SUBJECT=int(s),TIME_H=float(t),
               DV_NG_ML="" if cens else f"{float(y):.10f}",
               LLOQ_NG_ML=LLOQ_NG_ML,
               CENS=int(cens),MDV_M1=int(cens),MDV_M3=0)
          for s,t,y,cens in zip(subjects,times,observed,censored)]
    with (out_dir/"synthetic_pk_censored_source.csv").open("w",newline="",
           encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    summary={
      "dataset":"SYNTHETIC generated with seed",
      "seed":SEED,"n_subjects":N_SUBJECTS,"n_observations":len(observed),
      "n_blq":int(np.sum(censored)),"blq_fraction":float(np.mean(censored)),
      "true_parameters_used_only_for_simulation":{
        "CL_L_h":TRUE_CL_L_H,"V_L":V_L,"KA_h_inverse":KA_H,
        "additive_SD_ng_mL":TRUE_SD_NG_ML,
        "LLOQ_ng_mL":LLOQ_NG_ML},
      "estimated_parameters":{"M1_exclude_BLQ":m1,"M3_censored_likelihood":m3},
      "M1_absolute_CL_error":abs(m1["CL_L_h"]-TRUE_CL_L_H),
      "M3_absolute_CL_error":abs(m3["CL_L_h"]-TRUE_CL_L_H),
      "real_NONMEM_run":False,
      "NLME_or_random_effects_estimated":False,
      "interpretation":"one seeded illustration; does not establish superiority in general"
    }
    (out_dir/"m1_vs_m3_results.json").write_text(
        json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    (out_dir/"m1_vs_m3_review.md").write_text(
        "# Executable M1 vs M3 censored-likelihood exercise\n\n"
        f"Observations: {len(observed)}, censored: {int(sum(censored))} "
        f"({np.mean(censored)*100:.1f}%).\n\n"
        f"M1 CL={m1['CL_L_h']:.5f} L/h, SD={m1['additive_SD_ng_mL']:.2f} ng/mL.\n\n"
        f"M3 CL={m3['CL_L_h']:.5f} L/h, SD={m3['additive_SD_ng_mL']:.2f} ng/mL.\n\n"
        "M1 fits only observed samples. M3 includes log Phi((LLOQ-f)/SD) "
        "for censored observations. Simulation truth is known, but censored "
        "individual values are not supplied to either estimator.\n\n"
        "Numerical checks include independent erfc calculation and extreme-tail "
        "logCDF stability. This is a fixed-effect Python model and is NOT "
        "a licensed NONMEM execution, mixed-effects estimation, or validation "
        "of the illustrative NONMEM control stream.\n",encoding="utf-8")
    print(f"M1/M3 numerical checks PASS; {int(censored.sum())}/{len(censored)} censored; "
          f"CL M1={m1['CL_L_h']:.5f}, M3={m3['CL_L_h']:.5f} L/h")
    return 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",type=Path,
                   default=Path("outputs/nonmem_m3_likelihood"))
    return run(p.parse_args().out_dir)


if __name__=="__main__":
    raise SystemExit(main())

/*
  Portfolio translation of the validated ACTOT primary MMRM contract.
  EXECUTION STATUS: NOT_EXECUTED_NO_SAS_RUNTIME
  Translation basis: R/mmrm_analysis.R and its validated public-data outputs.
  Observed post-baseline rows only; no single-imputation carry-forward rows are introduced.
  This source is not claimed as executed, validated production SAS or sponsor/CRO code.
*/

%include "sas/macros/qc_contract.sas";

filename actot "outputs/adqs_actot_style.csv";

proc import datafile=actot
    out=work.adqs_actot
    dbms=csv
    replace;
  guessingrows=max;
  getnames=yes;
run;

%assert_vars(
  ds=work.adqs_actot,
  vars=STUDYID USUBJID TRT01A AVISIT AVAL BASE CHG ABLFL EFFFL QSSEQ
);

data work.mmrm_analysis;
  set work.adqs_actot;
  length AVISITN 8;

  if EFFFL="Y" and ABLFL ne "Y";
  if not missing(AVAL) and not missing(BASE) and not missing(CHG);

  select (upcase(strip(AVISIT)));
    when ("WEEK 8")  AVISITN=8;
    when ("WEEK 16") AVISITN=16;
    when ("WEEK 24") AVISITN=24;
    otherwise delete;
  end;

  if TRT01A not in (
    "Placebo",
    "Xanomeline Low Dose",
    "Xanomeline High Dose"
  ) then delete;

  keep STUDYID USUBJID TRT01A AVISIT AVISITN AVAL BASE CHG QSSEQ;
run;

proc sort data=work.mmrm_analysis;
  by USUBJID AVISITN QSSEQ;
run;

ods output
  LSMeans=work.mmrm_lsmeans
  Diffs=work.mmrm_diffs;

proc mixed data=work.mmrm_analysis method=reml;
  class USUBJID TRT01A AVISITN;
  model CHG = TRT01A AVISITN TRT01A*AVISITN BASE BASE*AVISITN
    / solution ddfm=satterth;
  repeated AVISITN / subject=USUBJID type=un;
  lsmeans TRT01A*AVISITN / diff cl;
run;

ods output close;

/*
  The validated R implementation remains the executed primary analysis.
  Any future SAS runtime validation must compare population, Week 24 contrasts,
  covariance contract and inference settings before changing execution status.
*/

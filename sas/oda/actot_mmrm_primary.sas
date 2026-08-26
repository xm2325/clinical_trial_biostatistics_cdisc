/*
  v0.26.1 ODA execution companion for the validated ACTOT primary MMRM
  contract. Assumes WORK.ADQS_ACTOT was transferred through SASPy.
*/
%assert_vars(
  ds=work.adqs_actot,
  vars=STUDYID USUBJID TRT01A AVISIT AVAL BASE CHG ABLFL EFFFL QSSEQ
);

data work.mmrm_analysis;
  set work.adqs_actot;
  length AVISITN_MODEL 8;

  if EFFFL="Y" and ABLFL ne "Y";
  if not missing(AVAL) and not missing(BASE) and not missing(CHG);

  select (upcase(strip(AVISIT)));
    when ("WEEK 8")  AVISITN_MODEL=8;
    when ("WEEK 16") AVISITN_MODEL=16;
    when ("WEEK 24") AVISITN_MODEL=24;
    otherwise delete;
  end;

  if TRT01A not in (
    "Placebo",
    "Xanomeline Low Dose",
    "Xanomeline High Dose"
  ) then delete;

  keep STUDYID USUBJID TRT01A AVISIT AVISITN_MODEL AVAL BASE CHG QSSEQ;
run;

proc sort data=work.mmrm_analysis;
  by USUBJID AVISITN_MODEL QSSEQ;
run;

ods output
  LSMeans=work.mmrm_lsmeans
  Diffs=work.mmrm_diffs;

proc mixed data=work.mmrm_analysis method=reml;
  class USUBJID TRT01A AVISITN_MODEL;
  model CHG = TRT01A AVISITN_MODEL TRT01A*AVISITN_MODEL BASE BASE*AVISITN_MODEL
    / solution ddfm=satterth;
  repeated AVISITN_MODEL / subject=USUBJID type=un;
  lsmeans TRT01A*AVISITN_MODEL / diff cl;
run;

ods output close;

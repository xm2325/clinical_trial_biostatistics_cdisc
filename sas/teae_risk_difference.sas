/*
  v0.26 portfolio translation of the validated subject-level any-TEAE
  risk-difference TFL.
  EXECUTION STATUS: NOT_EXECUTED_NO_SAS_RUNTIME
  Translation basis: src/cdisc_portfolio/analysis.py
*/

%include "sas/macros/qc_contract.sas";

filename adslcsv "outputs/adsl_style.csv";
filename adaecsv "outputs/adae_style.csv";

proc import datafile=adslcsv out=work.adsl dbms=csv replace;
  guessingrows=max;
  getnames=yes;
run;

proc import datafile=adaecsv out=work.adae dbms=csv replace;
  guessingrows=max;
  getnames=yes;
run;

%assert_vars(ds=work.adsl, vars=USUBJID TRT01A SAFFL);
%assert_vars(ds=work.adae, vars=USUBJID TRT01A TRTEMFL);

proc sort data=work.adsl(where=(SAFFL="Y"))
    out=work.safety(keep=USUBJID TRT01A)
    nodupkey;
  by USUBJID;
run;

proc sort data=work.adae(where=(TRTEMFL="Y"))
    out=work.teae_subjects(keep=USUBJID)
    nodupkey;
  by USUBJID;
run;

data work.safety_teae;
  merge work.safety(in=in_safety)
        work.teae_subjects(in=in_teae);
  by USUBJID;
  if in_safety;
  ANY_TEAE=in_teae;
run;

%macro teae_rd(active=, label=);
  data work.pair_&label.;
    set work.safety_teae;
    if TRT01A in ("Placebo", "&active.");
    ACTIVE=(TRT01A="&active.");
  run;

  ods output
    RiskDiffCol1=work.rd_&label.
    FishersExact=work.fisher_&label.;

  proc freq data=work.pair_&label.;
    tables ACTIVE*ANY_TEAE / riskdiff(cl=wald);
    exact fisher;
  run;

  ods output close;
%mend teae_rd;

%teae_rd(active=Xanomeline Low Dose, label=low);
%teae_rd(active=Xanomeline High Dose, label=high);

proc export data=work.rd_low
  outfile="outputs/sas_external_teae_rd_low.csv"
  dbms=csv replace;
run;
proc export data=work.rd_high
  outfile="outputs/sas_external_teae_rd_high.csv"
  dbms=csv replace;
run;
proc export data=work.fisher_low
  outfile="outputs/sas_external_teae_fisher_low.csv"
  dbms=csv replace;
run;
proc export data=work.fisher_high
  outfile="outputs/sas_external_teae_fisher_high.csv"
  dbms=csv replace;
run;

/*
  The executed Python/R evidence remains authoritative in this CI. External SAS
  execution must reconcile arm denominators, subject events, active-minus-placebo
  risk differences, confidence limits and Fisher p-values before execution status
  changes.
*/

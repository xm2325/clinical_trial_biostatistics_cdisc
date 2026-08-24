/*
  Portfolio translation of the validated subject-level any-TEAE risk-difference analysis.
  EXECUTION STATUS: NOT_EXECUTED_NO_SAS_RUNTIME
  Translation basis: src/cdisc_portfolio/analysis.py and validated Table 7 evidence.
  This source is not claimed as executed, validated production SAS or sponsor/CRO code.
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
  ANY_TEAE = in_teae;
run;

%macro teae_rd(active=, label=);
  data work.pair_&label.;
    set work.safety_teae;
    if TRT01A in ("Placebo", "&active.");
    ACTIVE = (TRT01A="&active.");
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

/*
  The executed Python/R evidence remains authoritative for reported values.
  A future SAS-enabled validation must reconcile arm denominators, event counts,
  active-minus-placebo risk differences, confidence limits and Fisher p-values.
*/

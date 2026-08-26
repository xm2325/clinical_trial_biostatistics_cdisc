/*
  v0.26.1 ODA execution companion for the subject-level any-TEAE risk-
  difference TFL. Assumes WORK.ADSL and WORK.ADAE were SAS-derived in the
  current ODA session.
*/
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
    RiskDiffCol1=work.rd0_&label.
    RiskDiffCol2=work.rd1_&label.
    FishersExact=work.fisher_&label.;

  proc freq data=work.pair_&label.;
    tables ACTIVE*ANY_TEAE / riskdiff(cl=wald);
    exact fisher;
  run;

  ods output close;
%mend teae_rd;

%teae_rd(active=Xanomeline Low Dose, label=low);
%teae_rd(active=Xanomeline High Dose, label=high);

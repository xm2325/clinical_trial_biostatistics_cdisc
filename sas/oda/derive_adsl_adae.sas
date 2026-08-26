/*
  v0.26.1 ODA execution companion for ADSL-style / ADAE-style derivation.
  Assumes public DM/EX/DS/AE have already been transferred into session-scoped
  WORK tables through the authenticated SASPy connection. This program performs
  the derivations in SAS; it does not read GitHub-runner file paths.
*/

%assert_vars(ds=work.dm, vars=STUDYID USUBJID AGE SEX RACE ARM ACTARM RFXSTDTC RFXENDTC);
%assert_vars(ds=work.ex, vars=STUDYID USUBJID EXSEQ EXTRT EXDOSE EXSTDTC EXENDTC);
%assert_vars(ds=work.ds, vars=STUDYID USUBJID DSSEQ DSDECOD DSCAT DSSTDTC);
%assert_vars(ds=work.ae, vars=STUDYID USUBJID AESEQ AEDECOD AESTDTC AESER);

data work.ex_clean;
  set work.ex;
  TRTSDT_EX=input(scan(EXSTDTC,1,'T'), yymmdd10.);
  TRTEDT_EX=input(scan(EXENDTC,1,'T'), yymmdd10.);
  EXDOSE_NUM=input(strip(vvalue(EXDOSE)), best32.);
  format TRTSDT_EX TRTEDT_EX yymmdd10.;
run;

proc sql;
  create table work.ex_summary as
  select STUDYID,
         USUBJID,
         min(TRTSDT_EX) as TRTSDT_EX format=yymmdd10.,
         max(TRTEDT_EX) as TRTEDT_EX format=yymmdd10.,
         count(*) as EXN,
         max(EXDOSE_NUM) as EXDOSE_MAX,
         mean(EXDOSE_NUM) as EXDOSE_MEAN
  from work.ex_clean
  group by STUDYID, USUBJID;
quit;

data work.ds_clean;
  set work.ds;
  DSDT=input(scan(DSSTDTC,1,'T'), yymmdd10.);
  format DSDT yymmdd10.;
  RAND_REC=(upcase(strip(DSDECOD))="RANDOMIZED");
  COMPL_REC=(upcase(strip(DSDECOD))="COMPLETED");
  DISP_REC=(upcase(strip(DSCAT))="DISPOSITION EVENT");
run;

proc sql;
  create table work.ds_summary as
  select STUDYID,
         USUBJID,
         max(RAND_REC) as RAND_REC,
         max(COMPL_REC) as COMPL_REC,
         max(case when DISP_REC then DSDT else . end) as EOSDT format=yymmdd10.
  from work.ds_clean
  group by STUDYID, USUBJID;
quit;

proc sort data=work.dm; by STUDYID USUBJID; run;
proc sort data=work.ex_summary; by STUDYID USUBJID; run;
proc sort data=work.ds_summary; by STUDYID USUBJID; run;

data work.adsl;
  merge work.dm(in=in_dm)
        work.ex_summary
        work.ds_summary;
  by STUDYID USUBJID;
  if in_dm;

  length TRT01P TRT01A $200 RANDFL SAFFL COMPLFL DCSFL $1;
  length TRTSDTSRC TRTEDTSRC $30;

  TRT01P=ARM;
  TRT01A=ACTARM;
  TRTSDT_DM=input(scan(RFXSTDTC,1,'T'), yymmdd10.);
  TRTEDT_DM=input(scan(RFXENDTC,1,'T'), yymmdd10.);

  if not missing(TRTSDT_EX) then do;
    TRTSDT=TRTSDT_EX; TRTSDTSRC="EX";
  end;
  else if not missing(TRTSDT_DM) then do;
    TRTSDT=TRTSDT_DM; TRTSDTSRC="DM_FALLBACK";
  end;
  else TRTSDTSRC="MISSING";

  if not missing(TRTEDT_EX) then do;
    TRTEDT=TRTEDT_EX; TRTEDTSRC="EX";
  end;
  else if not missing(TRTEDT_DM) then do;
    TRTEDT=TRTEDT_DM; TRTEDTSRC="DM_FALLBACK";
  end;
  else if not missing(EOSDT) then do;
    TRTEDT=EOSDT; TRTEDTSRC="DS_DISPOSITION_FALLBACK";
  end;
  else TRTEDTSRC="MISSING";

  if not missing(TRTSDT) and not missing(TRTEDT) and TRTEDT>=TRTSDT
    then TRTDURN=TRTEDT-TRTSDT+1;

  RANDFL=ifc(RAND_REC=1,"Y","N");
  SAFFL=ifc(coalesce(EXN,0)>0,"Y","N");
  COMPLFL=ifc(COMPL_REC=1,"Y","N");
  DCSFL=ifc(RANDFL="Y" and COMPLFL ne "Y","Y","N");

  format TRTSDT TRTEDT TRTSDT_DM TRTEDT_DM EOSDT yymmdd10.;
run;

proc sort data=work.adsl; by STUDYID USUBJID; run;
proc sort data=work.ae; by STUDYID USUBJID; run;

data work.adae;
  merge work.ae(in=in_ae)
        work.adsl(keep=STUDYID USUBJID TRT01A TRTSDT TRTEDT SAFFL);
  by STUDYID USUBJID;
  if in_ae;

  length TRTEMFL RELFL MODSEVFL $1;
  ASTDT=input(scan(AESTDTC,1,'T'), yymmdd10.);
  if not missing(AEENDTC) then AENDT=input(scan(AEENDTC,1,'T'), yymmdd10.);
  format ASTDT AENDT yymmdd10.;

  if not missing(ASTDT) and not missing(TRTSDT)
     and ASTDT>=TRTSDT
     and (missing(TRTEDT) or ASTDT<=TRTEDT+30)
     and SAFFL="Y"
    then TRTEMFL="Y";
  else TRTEMFL="N";

  if not missing(AESTDY) then ASTDY=input(strip(vvalue(AESTDY)), best32.);
  else if not missing(ASTDT) and not missing(TRTSDT) then do;
    ASTDY=ASTDT-TRTSDT;
    if ASTDY>=0 then ASTDY=ASTDY+1;
  end;

  if upcase(strip(AEREL)) in ("POSSIBLE","PROBABLE","DEFINITE","RELATED")
    then RELFL="Y";
  else RELFL="N";

  if upcase(strip(AESEV)) in ("MODERATE","SEVERE")
    then MODSEVFL="Y";
  else MODSEVFL="N";
run;

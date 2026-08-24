/*
  Portfolio SAS translation evidence.
  EXECUTION STATUS: NOT_EXECUTED_NO_SAS_RUNTIME
  This macro is source-review evidence only. It is not claimed as executed,
  validated production SAS, sponsor/CRO code or submission-ready programming.
*/

%macro assert_vars(ds=, vars=);
  %local dsid rc i var varnum;
  %let dsid=%sysfunc(open(&ds,i));

  %if &dsid=0 %then %do;
    %put ERROR: Unable to open required data set &ds.;
    %abort cancel;
  %end;

  %let i=1;
  %let var=%scan(&vars,&i,%str( ));
  %do %while(%length(&var));
    %let varnum=%sysfunc(varnum(&dsid,&var));
    %if &varnum=0 %then %do;
      %put ERROR: Required variable &var. is missing from &ds.;
      %let rc=%sysfunc(close(&dsid));
      %abort cancel;
    %end;
    %let i=%eval(&i+1);
    %let var=%scan(&vars,&i,%str( ));
  %end;

  %let rc=%sysfunc(close(&dsid));
%mend assert_vars;

; ILLUSTRATION ONLY - NONMEM NOT EXECUTED OR VALIDATED.
; Run from output's model/ directory if a licensed NONMEM executable is available.
; M1: BLQ flagged MDV=1, excluded, NOT censored likelihood.
$PROBLEM Synthetic mixed oral and IV infusion one-compartment teaching example M1
$INPUT ID TIME TAD EVID MDV DV AMT RATE CMT WT AGE SEX BLQ LLOQ CENS
$DATA ../data/nonmem_input.csv
$SUBROUTINES ADVAN2 TRANS2
$PK
  CL=THETA(1)*EXP(ETA(1))
  V=THETA(2)*EXP(ETA(2))
  KA=THETA(3)
  S2=V/1000
$ERROR
  Y=F+THETA(4)*ERR(1)
$THETA (0,5) (0,40) (0,1) (0,100)
$OMEGA 0.1 0.1
$SIGMA 1 FIX
$ESTIMATION METHOD=COND INTERACTION MAXEVAL=999
$TABLE ID TIME DV PRED CMT EVID BLQ NOPRINT ONEHEADER FILE=sdtab001

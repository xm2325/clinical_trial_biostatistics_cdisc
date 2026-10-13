; ILLUSTRATION ONLY - NONMEM NOT EXECUTED OR VALIDATED.
; Run from output's model/ directory if a licensed NONMEM executable is available.
; Units: AMT mg; concentration ng/mL; V L; CL L/h; TIME hour.
; S2=V/1000 converts mg/L -> ng/mL.
$PROBLEM Synthetic mixed oral and IV infusion one-compartment teaching example M3
$INPUT ID TIME TAD EVID MDV DV AMT RATE CMT WT AGE SEX BLQ LLOQ CENS
$DATA ../data/nonmem_input.csv
$SUBROUTINES ADVAN2 TRANS2
$PK
  TVCL=THETA(1)
  TVV=THETA(2)
  TVKA=THETA(3)
  CL=TVCL*EXP(ETA(1))
  V=TVV*EXP(ETA(2))
  KA=TVKA
  S2=V/1000
$ERROR
  W=THETA(4)
  F_FLAG=0
  IF (CENS.EQ.1) THEN
    F_FLAG=1
    Y=PHI((LLOQ-F)/W)
    MDVRES=1
  ELSE
    Y=F+W*ERR(1)
  ENDIF
$THETA (0,5) (0,40) (0,1) (0,100)
$OMEGA 0.1 0.1
$SIGMA 1 FIX
; M3 likelihood typically requires LAPLACIAN: illustrative, not run.
$ESTIMATION METHOD=COND INTERACTION LAPLACIAN MAXEVAL=999
$TABLE ID TIME DV PRED CMT EVID BLQ NOPRINT ONEHEADER FILE=sdtab001

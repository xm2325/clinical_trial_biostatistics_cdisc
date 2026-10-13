; ILLUSTRATIVE ONLY: NOT executed or validated against NONMEM.
; Oral depot (CMT=1) -> central (CMT=2) with concentration observations.
; BLQ records use an EXCLUSION / M1 teaching strategy: MDV=1, DV=0.
; This is NOT appropriate as a general BLQ likelihood model or clinical analysis.
$PROBLEM Synthetic one-compartment oral PK teaching example
$INPUT ID TIME TAD EVID MDV DV AMT RATE CMT WT AGE SEX BLQ LLOQ
$DATA nonmem_input.csv
$SUBROUTINES ADVAN2 TRANS2
$PK
TVCL=THETA(1)
TVV=THETA(2)
TVKA=THETA(3)
CL=TVCL*EXP(ETA(1))
V=TVV*EXP(ETA(2))
KA=TVKA
S2=V
$ERROR
Y=F*(1+ERR(1))
$THETA (0,5) (0,40) (0,1)
$OMEGA 0.1 0.1
$SIGMA 0.04
$ESTIMATION METHOD=1 INTERACTION MAXEVAL=999

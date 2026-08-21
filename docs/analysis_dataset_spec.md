# Analysis dataset specification

This document records the main source-to-derived-variable mappings used by v0.3. It is a compact portfolio analogue of an analysis dataset specification, not a formal CDISC metadata package.

## ADSL-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID | DM | copied |
| USUBJID | DM | copied |
| AGE / SEX / RACE / COUNTRY | DM | copied |
| TRT01P | DM.ARM | copied |
| TRT01A | DM.ACTARM | copied |
| TRTSDT_DM / TRTEDT_DM | DM.RFXSTDTC / RFXENDTC | parsed to date; traceability only |
| TRTSDT | EX.EXSTDTC | minimum non-missing subject date; DM fallback if unavailable |
| TRTEDT | EX.EXENDTC / DM.RFXENDTC / DS | maximum non-missing EX end date; then DM end date; then final DS disposition date |
| TRTSDTSRC / TRTEDTSRC | derivation metadata | records the source used for final treatment dates |
| EXDURN_RAW | EX.EXSTDTC / EX.EXENDTC | inclusive duration using EX dates only |
| TRTDURN | TRTSDT / TRTEDT | final inclusive treatment-window duration after documented fallbacks |
| EXN | EX | number of subject EX records |
| EXTRTS | EX.EXTRT | sorted distinct treatment strings |
| EXDOSE_MAX / EXDOSE_MEAN | EX.EXDOSE | subject-level numeric dose summaries |
| RANDFL | DS.DSDECOD | `Y` if `RANDOMIZED` exists |
| SAFFL | EX | `Y` if at least one EX record exists |
| COMPLFL | DS.DSDECOD | `Y` if `COMPLETED` exists |
| EOSDECOD / EOSTERM / EOSDT | DS | last `DISPOSITION EVENT` by date / DS sequence |
| DCSFL | RANDFL / COMPLFL | `Y` if randomised and not completed |

## ADAE-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID / AESEQ | AE | copied key |
| AETERM / AEDECOD / AEBODSYS | AE | copied |
| AESEV / AESER / AEREL / AEOUT | AE | copied |
| TRT01A / TRTSDT / TRTEDT / SAFFL | ADSL-style | merge by STUDYID + USUBJID |
| ASTDT / AENDT | AE.AESTDTC / AE.AEENDTC | parsed dates |
| ASTDY | AE.AESTDY | numeric when supplied; otherwise relative-day derivation |
| TRTEMFL | AE + ADSL-style | `Y` when ASTDT is within `[TRTSDT, TRTEDT + 30 days]` and SAFFL=`Y` |
| RELFL | AE.AEREL | `Y` for POSSIBLE / PROBABLE / DEFINITE / RELATED |
| MODSEVFL | AE.AESEV | `Y` for MODERATE / SEVERE |

## ADQSCIBC-style

Source: official CDISC pilot `QS` Dataset-JSON, filtered to `QSTESTCD=CIBICVAL` and linked to ADSL-style.

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID | QS | copied key |
| TRTP | ADSL-style.TRT01P | planned treatment |
| ITTFL | ADSL-style.RANDFL | `Y` for retained randomised subjects |
| EFFFL | QS + RANDFL | `Y` for retained randomised subjects with numeric CIBIC+ data |
| COMP24FL | ADSL-style.COMPLFL | portfolio completion flag |
| AVISIT / AVISITN | analysis windows | Week 8/8, Week 16/16, Week 24/24 |
| VISIT / VISITNUM | QS | source visit of selected/carried record |
| ADY / ADT | QS.QSDY / QSDTC | source analysis day/date |
| PARAMCD / PARAM | constant | CIBICVAL / CIBIC Score |
| AVAL | QS.QSSTRESN | numeric selected or carried-forward value |
| ANL01FL | derivation | `Y` for selected analysis record |
| DTYPE | derivation | blank for in-window observation; `LOCF` for carried-forward observation |
| AWTARGET | reference metadata | 56 / 112 / 168 days |
| AWLO / AWHI | reference metadata | 2–84 / 85–140 / 141+ |
| AWTDIFF | ADY / AWTARGET | absolute distance to target day |
| QSSEQ | QS.QSSEQ | source-record traceability |

The output is compared row-by-row with the public CDISC `ADQSCIBC` reference ADaM on `USUBJID + AVISIT`.

## ADQS-style ACITM01

Source: official CDISC pilot `QS` Dataset-JSON, filtered to `QSTESTCD=ACITM01`.

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID | QS | copied key |
| TRT01A | ADSL-style | actual treatment |
| PARAMCD | QS.QSTESTCD | `ACITM01` |
| PARAM | QS.QSTEST | Word Recall Task label |
| AVISIT / AVISITN | QS.VISIT / VISITNUM | source visit |
| ADY / ADT | QS.QSDY / QSDTC | numeric day and parsed date |
| AVAL | QS.QSSTRESN | numeric standard result |
| BASE | QS.QSBLFL | subject baseline value from the baseline-flagged record |
| CHG | AVAL / BASE | `AVAL - BASE` for post-baseline records; 0 at baseline |
| ABLFL | QS.QSBLFL | `Y` for baseline record |
| EFFFL | baseline + post-baseline availability | `Y` when randomised subject has both baseline and post-baseline numeric data |
| QSSEQ | QS.QSSEQ | source-record traceability |

## ANCOVA analysis-subject datasets

Observed Week 24 uses an observed `WEEK 24` ACITM01 record. LOCF sensitivity uses the latest numeric post-baseline observation on or before day 168. Each analysis dataset contains one row per subject with treatment, BASE, Week 24/sensitivity AVAL, CHG, source day and `DTYPE`.

# Analysis dataset specification

This document records the main source-to-derived-variable mappings used by v0.3. It is a compact portfolio analysis specification, not a formal CDISC metadata package.

## ADSL-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID | DM | copied |
| AGE / SEX / RACE / COUNTRY | DM | copied |
| TRT01P / TRT01A | DM.ARM / DM.ACTARM | planned / actual treatment labels |
| TRTSDT_DM / TRTEDT_DM | DM.RFXSTDTC / RFXENDTC | parsed dates retained for traceability |
| TRTSDT | EX.EXSTDTC / DM | first EX start; DM fallback if unavailable |
| TRTEDT | EX.EXENDTC / DM / DS | last EX end; DM fallback; final DS disposition fallback |
| TRTSDTSRC / TRTEDTSRC | derivation metadata | source used for final treatment dates |
| EXDURN_RAW | EX dates | inclusive EX-only duration |
| TRTDURN | TRTSDT / TRTEDT | final inclusive treatment-window duration |
| EXN / EXTRTS | EX | record count / distinct treatment strings |
| EXDOSE_MAX / EXDOSE_MEAN | EX.EXDOSE | subject-level numeric summaries |
| RANDFL | DS.DSDECOD | `Y` when `RANDOMIZED` is present |
| SAFFL | EX | `Y` when at least one EX record is present |
| COMPLFL | DS.DSDECOD | `Y` when `COMPLETED` is present |
| EOSDECOD / EOSTERM / EOSDT | DS | final disposition event |
| DCSFL | RANDFL / COMPLFL | randomised but not completed |

## ADAE-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID / AESEQ | AE | copied key |
| AETERM / AEDECOD / AEBODSYS | AE | copied |
| AESEV / AESER / AEREL / AEOUT | AE | copied |
| TRT01A / TRTSDT / TRTEDT / SAFFL | ADSL-style | subject merge |
| ASTDT / AENDT | AE dates | parsed dates |
| ASTDY | AE.AESTDY or date calculation | analysis start day |
| TRTEMFL | AE + subject dates | start within treatment through 30-day follow-up |
| RELFL | AE.AEREL | relationship flag |
| MODSEVFL | AE.AESEV | moderate/severe flag |

## ADQSCIBC-style

Source: official CDISC pilot QS Dataset-JSON, `QSTESTCD=CIBIC`, linked to ADSL-style. The analysis output uses `PARAMCD=CIBICVAL`, as in the official reference ADaM.

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID | QS | copied |
| TRTP | ADSL-style.TRT01P | planned treatment |
| ITTFL | ADSL-style.RANDFL | retained randomised subject |
| AVISIT / AVISITN | analysis windows | Week 8/8, Week 16/16, Week 24/24 |
| VISIT / VISITNUM | QS | selected source visit |
| ADY / ADT | QS.QSDY / QSDTC | selected source day/date |
| PARAMCD / PARAM | derivation | `CIBICVAL` / `CIBIC Score` |
| AVAL | QS.QSSTRESN | selected source numeric value |
| ANL01FL | derivation | `Y` for selected analysis row |
| DTYPE | derivation | blank for in-window record; `LOCF` for carried record |
| AWTARGET | analysis rule | 56 / 112 / 168 |
| AWLO / AWHI | analysis rule | 2–84 / 85–140 / 141+ |
| AWTDIFF | ADY / AWTARGET | absolute difference from target day |
| QSSEQ | QS.QSSEQ | exact source-record identifier |

Official-reference comparison uses `USUBJID + AVISIT`. The verified run covers 705/705 reference analysis keys and matches `QSSEQ` and `DTYPE` for every row. Ten reference `AVAL` values differ from the selected official QS source; these rows are retained in `adqscibc_mismatch_source_trace.csv`.

## ADQS-style ACTOT for portfolio analysis

Source: official CDISC pilot QS Dataset-JSON, `QSTESTCD=ACTOT`.

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID | QS | copied |
| TRT01A | ADSL-style | actual treatment |
| PARAMCD / PARAM | QS | `ACTOT` and source label |
| AVISIT / AVISITN | QS.VISIT / VISITNUM | source visit |
| ADY / ADT | QS.QSDY / QSDTC | numeric day / parsed date |
| AVAL | QS.QSSTRESN | official source total-score value |
| BASE | baseline-flagged ACTOT | subject baseline value |
| CHG | AVAL / BASE | `AVAL - BASE` after baseline |
| ABLFL | QS.QSBLFL | baseline flag |
| EFFFL | baseline + post-baseline availability | portfolio efficacy flag |
| QSSEQ | QS.QSSEQ | source traceability |

The main ANCOVA uses this source-derived ACTOT dataset. It does not substitute official reference ADaM values when those values differ from the source QS.

## Official ADQSADAS selected ACTOT reconstruction

The official `ADQSADAS` reference has 12,463 rows and 15 parameters. `ACTOT` has 1,040 rows. The selected reference set is defined by `PARAMCD=ACTOT` and `ANL01FL=Y`, giving 1,016 rows.

The portfolio reconstructs one selected row for Baseline, Week 8, Week 16 and Week 24 for each of 254 subjects. Analysis windows and LOCF rules determine the source row. Validation uses:

| Field | Validation role |
|---|---|
| USUBJID + AVISIT | analysis-row key |
| QSSEQ | selected source record |
| DTYPE | observed versus LOCF classification |
| AVAL / BASE / CHG | reported value comparison |

The verified live run has 100% key, `QSSEQ` and `DTYPE` agreement. Value agreement is reported separately because the public source and public reference differ for a subset of rows.

## ADAS-Cog(11) item-recalculation diagnostic

A separate diagnostic recalculates `ACTOT` from 11 component codes: `ACITM01`, `ACITM02`, `ACITM04`, `ACITM05`, `ACITM06`, `ACITM07`, `ACITM08`, `ACITM11`, `ACITM12`, `ACITM13`, and `ACITM14`.

This diagnostic is not used to replace the official source `ACTOT` in the main analysis. It is retained to show whether discrepancies can be explained by a simple item sum and to make that assumption testable.

## ANCOVA analysis-subject datasets

Observed Week 24 uses an observed `WEEK 24` ACTOT record. LOCF sensitivity uses the latest numeric post-baseline ACTOT observation on or before day 168. Each analysis set contains one row per subject with treatment, `BASE`, analysis `AVAL`, `CHG`, source day and `DTYPE`.

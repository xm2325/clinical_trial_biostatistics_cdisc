# Statistical Analysis Plan — portfolio version 0.4

## 1. Scope

This Statistical Analysis Plan (SAP) specifies independent portfolio safety and questionnaire-efficacy analyses using public CDISC pilot data. It is not sponsor-approved and is not a regulatory-submission SAP.

Version 0.3 added two official-reference workflows. The first derives an `ADQSCIBC-style` CIBIC+ analysis dataset from official CDISC QS and compares it with the public `ADQSCIBC` reference ADaM. The second profiles the official `ADQSADAS` reference, validates selected ADAS-Cog `ACTOT` analysis rows, and runs an independent Week 24 continuous-endpoint analysis using baseline adjustment and LOCF sensitivity.

Version 0.4 adds a separate R implementation for selected programming QC. The R program independently reconstructs safety populations, TEAE results, CIBIC record selection, ACTOT baseline/change records and Week 24/LOCF ANCOVA from the same public source data. Python outputs are read only for the final R/Python comparison.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised if DS contains a record with `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population if at least one EX record is observed.

### 2.3 CIBIC+ analysis population

Subjects must be randomised and have numeric official QS records with `QSTESTCD == "CIBIC"`. The output parameter code is `CIBICVAL`, matching the official reference ADaM.

### 2.4 ACTOT efficacy population

The independent portfolio efficacy analysis uses randomised subjects with a numeric `ACTOT` baseline and at least one numeric post-baseline value. The observed Week 24 analysis requires an observed Week 24 value. The LOCF sensitivity analysis uses the latest eligible post-baseline value through analysis day 168.

## 3. Treatment and exposure

Planned and actual treatment labels are taken from DM and carried to `TRT01P` and `TRT01A`.

Actual exposure dates are derived from EX:

- `TRTSDT`: minimum parsed `EXSTDTC`;
- `TRTEDT`: maximum parsed `EXENDTC`; if unavailable, DM `RFXENDTC`, then the final DS disposition date;
- `EXDURN_RAW`: inclusive duration based only on non-missing EX start/end dates;
- `TRTDURN`: final inclusive treatment-window duration after documented date fallbacks;
- `EXN`: number of observed EX records;
- `EXDOSE_MAX` and `EXDOSE_MEAN`: subject-level numeric dose summaries.

`TRTSDTSRC` and `TRTEDTSRC` preserve the selected source for final treatment dates.

## 4. Disposition

`RANDFL` is based on a DS randomisation record. `COMPLFL` is `Y` if DS contains `DSDECOD == "COMPLETED"`. The final disposition event is the last record with `DSCAT == "DISPOSITION EVENT"` ordered by date and sequence. A randomised subject without completion is flagged `DCSFL == "Y"`.

## 5. Adverse-event derivations

AE records are linked to ADSL-style by `STUDYID` and `USUBJID`.

- `ASTDT`: parsed from `AESTDTC`.
- `AENDT`: parsed from `AEENDTC` when available.
- `TRTEMFL`: `Y` when `ASTDT >= TRTSDT` and `ASTDT <= TRTEDT + 30 days`.
- `RELFL`: `Y` for `AEREL` in `POSSIBLE`, `PROBABLE`, `DEFINITE`, or `RELATED`.
- `MODSEVFL`: `Y` for `AESEV` in `MODERATE` or `SEVERE`.
- Serious TEAE: `AESER == "Y"` and `TRTEMFL == "Y"`.

No partial-date imputation is performed for AE start dates.

## 6. CIBIC+ analysis-window derivation

Official QS is filtered to `QSTESTCD == "CIBIC"`. Numeric `QSSTRESN` is mapped to `AVAL`. The output uses `PARAMCD=CIBICVAL`.

| Analysis visit | Target day | Observation window |
|---|---:|---|
| Week 8 | 56 | days 2–84 |
| Week 16 | 112 | days 85–140 |
| Week 24 | 168 | day 141 onward |

Within a window, the record nearest the target day is selected. If no record is present, the latest prior record is carried forward and `DTYPE=LOCF`. `AWTARGET`, `AWLO`, `AWHI`, `AWTDIFF`, source visit/date and `QSSEQ` are retained.

The live validation compares derived rows with official `ADQSCIBC` analysis records. The verified result is 705/705 analysis keys covered, 100% `QSSEQ` agreement and 100% `DTYPE` agreement. `AVAL` agreement is 695/705 (98.58%). For each of the ten differences, the derived value equals the selected official SDTM QS `QSSTRESN`, while the official reference ADaM value differs from that source row. These differences are written to `adqscibc_mismatch_source_trace.csv` and are not overwritten.

## 7. Official ADQSADAS reference validation

The official `ADQSADAS` Dataset-JSON contains 12,463 rows for 254 subjects and 15 ADAS-Cog parameters. `ACTOT` (`Adas-Cog(11) Subscore`) contains 1,040 rows.

For structural validation, official `ACTOT` records with `ANL01FL=Y` are treated as the selected analysis set. This gives 1,016 records: one baseline plus Week 8, Week 16 and Week 24 records for 254 subjects. The portfolio reconstructs the same `USUBJID + AVISIT` keys and validates selected source `QSSEQ` and `DTYPE` against the reference. The verified live run gives 100% key coverage, 100% `QSSEQ` agreement and 100% `DTYPE` agreement.

An additional diagnostic recomputes ADAS-Cog(11) totals from the 11 component items. This diagnostic is kept separate from the main source-value analysis because the public reference and public SDTM source contain value differences for a subset of selected rows. Reference-value agreement is therefore reported, not used to alter source values.

## 8. ACTOT baseline and change from baseline

The main portfolio continuous-endpoint dataset uses official QS `ACTOT` records. `AVAL` is numeric `QSSTRESN`. `BASE` is taken from the baseline-flagged `ACTOT` record. For post-baseline records:

`CHG = AVAL - BASE`.

The dataset retains source visit, day/date and `QSSEQ` for traceability.

## 9. Week 24 ANCOVA

The observed-case model is:

`AVAL_Week24 = intercept + treatment + centred BASE + error`.

Placebo is the reference treatment. Least-squares means are evaluated at the analysis-set mean baseline. Active-versus-placebo contrasts are reported with standard errors, two-sided 95% t-based confidence intervals and two-sided p-values.

The verified observed Week 24 analysis contains 116 subjects. Estimated active-versus-placebo differences are -2.028 for Xanomeline Low Dose and -0.923 for Xanomeline High Dose.

These are independent portfolio analyses and are not presented as the original trial's confirmatory results.

## 10. Missing-data sensitivity

A separate LOCF sensitivity analysis uses the latest numeric post-baseline ACTOT observation on or before analysis day 168. It contains 235 subjects and fits the same ANCOVA specification. Observed-case and LOCF outputs are reported separately.

## 11. Descriptive statistics

Age is summarised with mean, standard deviation, median, Q1 and Q3. Categorical variables are summarised as counts and percentages. Safety incidence uses subject-level denominators. ACTOT outputs report baseline, Week 24 and change-from-baseline summaries by treatment.

## 12. Exploratory any-TEAE treatment comparison

For each Xanomeline arm versus placebo, the workflow reports subject-level TEAE risk, unadjusted risk difference, Wald 95% confidence interval and Fisher exact-test p-value.

## 13. Multiplicity

No confirmatory hypothesis family is defined. TEAE and ACTOT p-values are exploratory and are not multiplicity-adjusted.

## 14. QC and acceptance

The live workflow separates three types of checks: Python internal QC, official-reference validation, and R/Python cross-language programming QC.

Required official-reference checks are:

- 100% official ADQSCIBC analysis-key coverage;
- 100% ADQSCIBC `DTYPE` agreement;
- 100% ADQSCIBC `QSSEQ` source-row agreement;
- every ADQSCIBC value discrepancy must trace to the selected official QS source row, with the portfolio value equal to that source;
- 100% selected ACTOT reference-key coverage;
- 100% selected ACTOT `DTYPE` agreement;
- 100% selected ACTOT `QSSEQ` agreement.

Reference `AVAL` agreement is reported as an informational metric when the official source and reference differ. The workflow does not change a source-derived value merely to make the reference match.

### 14.1 Independent R/Python programming QC

`R/independent_qc.R` reimplements selected analysis rules from the same raw public inputs. It does not call Python derivation code. The final comparison requires exact agreement for discrete derivations and an absolute difference no greater than `1e-8` for ANCOVA numerical outputs.

The required cross-language comparisons cover:

- randomised, safety and completed subject counts;
- TEAE subject and event counts;
- DS treatment-end fallback count;
- any-TEAE risk-difference table;
- CIBIC analysis keys, `QSSEQ`, `DTYPE` and source-derived `AVAL`;
- ACTOT source-row keys, `AVAL`, `BASE`, `CHG` and flags;
- ANCOVA contrast keys, N, residual df, estimates, standard errors, confidence limits, p-values and baseline reference values.

The verified v0.4 run passes **16/16 required R/Python checks**. The maximum ANCOVA numeric difference is `7.11e-15`, below the `1e-8` acceptance tolerance. The same run retains **10/10 Python unit tests** and **24/24 required Python pipeline QC checks**.

This cross-language check is a separate implementation by the same portfolio author. It is not described as independent review by a second programmer.

The live scripts exit non-zero if a required QC condition fails, while GitHub Actions retains diagnostic outputs.

## 15. Sample-size demonstration

A separate utility provides equal-allocation normal-approximation sample-size calculations for two-arm continuous and binary endpoints. These examples are not tied to the public pilot study.

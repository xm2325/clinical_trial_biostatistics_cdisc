# Statistical Analysis Plan — portfolio version 0.3

## 1. Scope

This Statistical Analysis Plan (SAP) specifies independent portfolio safety and questionnaire-efficacy analyses using public CDISC pilot data. It is not sponsor-approved and is not a regulatory-submission SAP.

Version 0.3 adds two questionnaire workflows. First, it derives an `ADQSCIBC-style` CIBIC+ analysis dataset from the official CDISC QS Dataset-JSON and compares the result with the public CDISC `ADQSCIBC` reference ADaM. Second, it uses `ACITM01` (Word Recall Task) as a portfolio continuous-endpoint example with baseline, change from baseline, Week 24 ANCOVA and a LOCF sensitivity analysis. The ACITM01 analysis is not presented as the source trial's primary or confirmatory endpoint.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised if DS contains a record with `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population if at least one EX record is observed.

### 2.3 CIBIC+ reference-reproduction population

Subjects must be randomised and have at least one numeric QS record with `QSTESTCD == "CIBICVAL"`. One analysis record is selected or carried forward for each available target analysis visit.

### 2.4 ACITM01 efficacy population

Subjects must be randomised, have a numeric `ACITM01` baseline record flagged by `QSBLFL == "Y"`, and have at least one numeric post-baseline ACITM01 value. The observed-case Week 24 ANCOVA further requires an observed `WEEK 24` value.

## 3. Treatment and exposure

Planned and actual treatment labels are taken from DM and carried to `TRT01P` and `TRT01A`.

Actual exposure dates are derived from EX:

- `TRTSDT`: minimum parsed `EXSTDTC`;
- `TRTEDT`: maximum parsed `EXENDTC`; if unavailable, use DM `RFXENDTC`, then the final DS disposition date as a documented fallback;
- `EXDURN_RAW`: inclusive duration from non-missing EX start/end dates only;
- `TRTDURN`: final inclusive treatment-window duration from `TRTSDT`/`TRTEDT`, after documented fallbacks;
- `EXN`: number of observed EX records;
- `EXDOSE_MAX` and `EXDOSE_MEAN`: subject-level summaries of numeric `EXDOSE`.

DM `RFXSTDTC` and `RFXENDTC` are retained as `TRTSDT_DM` and `TRTEDT_DM`. `TRTSDTSRC` and `TRTEDTSRC` record the source used for the final analysis dates.

## 4. Disposition

`RANDFL` is based on a DS randomisation milestone. `COMPLFL` is `Y` if a DS record has `DSDECOD == "COMPLETED"`. The final disposition event is the last record with `DSCAT == "DISPOSITION EVENT"` ordered by disposition date and sequence. A randomised subject without completion is flagged `DCSFL == "Y"`.

## 5. Adverse-event derivations

AE records are linked to ADSL-style by `STUDYID` and `USUBJID`.

- `ASTDT`: parsed from `AESTDTC`.
- `AENDT`: parsed from `AEENDTC` when available.
- `TRTEMFL`: `Y` if `ASTDT >= TRTSDT` and `ASTDT <= TRTEDT + 30 days`; otherwise `N`.
- `RELFL`: `Y` for `AEREL` in `POSSIBLE`, `PROBABLE`, `DEFINITE`, or `RELATED`.
- `MODSEVFL`: `Y` for `AESEV` in `MODERATE` or `SEVERE`.
- Serious TEAE: `AESER == "Y"` and `TRTEMFL == "Y"`.

No partial-date imputation is performed for AE start dates.

## 6. CIBIC+ analysis-window reproduction

The official CDISC QS Dataset-JSON is filtered to `QSTESTCD == "CIBICVAL"`. Numeric standard results are mapped to `AVAL`. The following portfolio implementation follows the public `ADQSCIBC` reference metadata:

| Analysis visit | Target day | Actual-observation window |
|---|---:|---|
| Week 8 | 56 | days 2–84 |
| Week 16 | 112 | days 85–140 |
| Week 24 | 168 | day 141 onward |

Within an analysis window, the record nearest the target day is selected. If no record exists in a window, the latest prior post-baseline CIBIC+ record is carried forward and `DTYPE=LOCF`. `AWTARGET`, `AWLO`, `AWHI`, `AWTDIFF`, `QSSEQ`, source visit and source date are retained for traceability.

The derived records are compared with the official CDISC `ADQSCIBC` reference using `USUBJID + AVISIT`. Validation metrics include reference-key coverage and exact-match rates for `AVAL`, `DTYPE` and `QSSEQ`.

## 7. ACITM01 ADQS-style derivation

`ACITM01` is the QS Word Recall Task. `AVAL` is the numeric standard result. Baseline is the subject's record with `QSBLFL == "Y"`; this value is carried as `BASE`. For post-baseline records:

`CHG = AVAL - BASE`.

The long-form ADQS-style dataset retains the subject, actual treatment, source visit, analysis day/date, `AVAL`, `BASE`, `CHG`, baseline flag and source `QSSEQ`.

## 8. Week 24 ANCOVA

The observed-case portfolio analysis models the Week 24 ACITM01 value as:

`AVAL_Week24 = intercept + treatment + centred BASE + error`.

Placebo is the reference treatment. Least-squares means are evaluated at the analysis-set mean baseline. Two active-versus-placebo contrasts are reported with standard errors, two-sided 95% t-based confidence intervals and two-sided p-values.

This is an exploratory portfolio model. No claim is made that ACITM01 is the original trial's confirmatory endpoint.

## 9. Missing-data sensitivity

The observed-case Week 24 ANCOVA uses only observed Week 24 values. A separate LOCF sensitivity dataset uses the latest numeric post-baseline ACITM01 observation on or before analysis day 168 for each efficacy subject. The same ANCOVA specification is then fitted to the LOCF sensitivity dataset. Observed-case and LOCF results are reported separately.

## 10. Descriptive statistics

Safety descriptive statistics are unchanged from v0.2. For ACITM01, the observed Week 24 analysis set is summarised by treatment arm using N, baseline mean/SD, Week 24 mean/SD and change-from-baseline mean/SD.

## 11. Exploratory any-TEAE treatment comparison

For each Xanomeline arm versus placebo, the workflow reports subject-level TEAE risk, unadjusted risk difference, a Wald 95% confidence interval and Fisher's exact-test p-value. These comparisons remain exploratory.

## 12. Multiplicity

No confirmatory hypothesis family is defined. P-values from the TEAE analysis and ACITM01 ANCOVA are exploratory and are not multiplicity-adjusted.

## 13. QC and acceptance

Required QC covers safety derivations, efficacy keys, baseline/change identities, ANCOVA subject uniqueness, LOCF sample retention and official-reference validation. The v0.3 acceptance thresholds initially require at least 95% official `ADQSCIBC` reference-key coverage and at least 99% `AVAL` agreement on overlapping keys. `DTYPE` and `QSSEQ` agreement are also reported.

The live script exits non-zero when any required QC check fails. Outputs are still uploaded by GitHub Actions so the failing derivation can be diagnosed.

## 14. Sample-size demonstration

A separate utility provides equal-allocation normal-approximation sample-size calculations for two-arm continuous and binary endpoints. These examples are not tied to the public pilot study.

# Statistical Analysis Plan — portfolio version 0.5

## 1. Scope

This Statistical Analysis Plan (SAP) specifies independent portfolio safety and questionnaire-efficacy analyses using public CDISC pilot data. It is not sponsor-approved and is not a regulatory-submission SAP.

Version 0.3 added official-reference validation against public `ADQSCIBC` and `ADQSADAS` reference ADaM datasets. Version 0.4 added a separate R implementation for selected programming QC. Version 0.5 adds an observed-data longitudinal mixed model for repeated measures (MMRM) for ACTOT Week 8, Week 16 and Week 24 change from baseline, with a pre-specified covariance sensitivity analysis.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised if DS contains a record with `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population if at least one EX record is observed.

### 2.3 CIBIC+ analysis population

Subjects must be randomised and have numeric official QS records with `QSTESTCD == "CIBIC"`. The output parameter code is `CIBICVAL`, matching the public reference ADaM.

### 2.4 ACTOT efficacy population

The independent portfolio efficacy analysis uses randomised subjects with a numeric ACTOT baseline and at least one numeric post-baseline ACTOT value.

The Week 24 observed-case ANCOVA requires an observed Week 24 ACTOT value. The LOCF sensitivity uses the latest eligible post-baseline ACTOT value through analysis day 168.

The MMRM analysis uses observed ACTOT values at Week 8, Week 16 and Week 24 only. A subject can contribute one, two or three post-baseline observations. LOCF records are not introduced into the MMRM.

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

AE records are linked to the ADSL-style subject dataset by `STUDYID` and `USUBJID`.

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

The verified live run covers 705/705 public ADQSCIBC analysis keys with 100% `QSSEQ` and 100% `DTYPE` agreement. `AVAL` agreement is 695/705 (98.58%). For all ten value differences, the portfolio value equals the selected public SDTM QS `QSSTRESN`; the public reference ADaM value differs from that source record. These differences remain visible in `adqscibc_mismatch_source_trace.csv`.

## 7. Official ADQSADAS reference validation

The public `ADQSADAS` Dataset-JSON contains 12,463 rows for 254 subjects and 15 ADAS-Cog parameters. `ACTOT` (`Adas-Cog(11) Subscore`) contains 1,040 rows.

The official selected ACTOT structure contains 1,016 `ANL01FL=Y` records. The portfolio reconstructs the same `USUBJID + AVISIT` keys and validates source `QSSEQ` and `DTYPE` against the public reference. Verified key, `QSSEQ` and `DTYPE` agreement are all 100%.

A separate diagnostic recomputes ADAS-Cog(11) totals from component items. This diagnostic does not replace the source ACTOT values when public source and public reference values differ.

## 8. ACTOT baseline and change from baseline

The portfolio ACTOT analysis dataset uses public QS `ACTOT` records. `AVAL` is numeric `QSSTRESN`. `BASE` is taken from the baseline-flagged ACTOT record. For post-baseline records:

```text
CHG = AVAL - BASE
```

Source visit, analysis day/date and `QSSEQ` are retained for traceability.

## 9. Week 24 observed-case ANCOVA

The observed-case model is:

```text
AVAL_Week24 = intercept + treatment + centred BASE + error
```

Placebo is the reference treatment. Least-squares means are evaluated at the analysis-set mean baseline. Active-versus-placebo contrasts are reported with standard errors, two-sided 95% t-based confidence intervals and two-sided p-values.

The verified analysis contains 116 subjects. Estimates are -2.0283 for Xanomeline Low Dose versus Placebo and -0.9234 for Xanomeline High Dose versus Placebo.

## 10. LOCF sensitivity analysis

A separate LOCF sensitivity uses the latest numeric post-baseline ACTOT observation on or before analysis day 168 and fits the same Week 24 ANCOVA specification. It contains 235 subjects.

LOCF is retained as a separate sensitivity analysis and is not used as input to the MMRM in Section 11.

## 11. ACTOT longitudinal MMRM

### 11.1 Objective

The longitudinal analysis estimates treatment differences in ACTOT change from baseline at Week 8, Week 16 and Week 24 while using all observed data at those scheduled visits under the model assumptions.

### 11.2 Analysis records

Only observed post-baseline ACTOT records at Week 8, Week 16 and Week 24 enter the model. Each subject contributes at most one record per analysis visit. The verified dataset contains 451 observations from 189 subjects: Week 8=189, Week 16=146 and Week 24=116.

### 11.3 Primary model

The response is `CHG`. Treatment and visit are categorical. The fixed-effects model is:

```text
CHG ~ TRT01A * AVISIT + BASE * AVISIT
```

The primary within-subject covariance matrix is unstructured. Estimation uses restricted maximum likelihood (REML). Degrees of freedom for treatment contrasts use the Satterthwaite method.

Visit-specific treatment least-squares means and two active-versus-placebo contrasts are reported at each visit. No multiplicity adjustment is applied because these portfolio analyses are exploratory.

The verified primary Week 24 contrasts are:

| Contrast | Estimate | SE | 95% CI | df | p-value |
|---|---:|---:|---:|---:|---:|
| Xanomeline Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 142.05 | 0.1693 |
| Xanomeline High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 139.44 | 0.4220 |

### 11.4 Covariance sensitivity

The same fixed-effects model is refit using heterogeneous AR(1) covariance. Week 8, Week 16 and Week 24 are treated as equally spaced ordered analysis visits for this covariance structure.

Verified diagnostics are:

| Covariance | logLik | AIC | BIC |
|---|---:|---:|---:|
| Unstructured | -1299.3136 | 2610.6272 | 2630.0777 |
| Heterogeneous AR(1) | -1309.7404 | 2627.4809 | 2640.4479 |

The unstructured model has lower AIC/BIC in this dataset. Model-selection criteria are reported descriptively; they are not treated as proof that the same covariance choice is optimal for other trials.

### 11.5 Comparison with observed Week 24 ANCOVA

The MMRM and observed-case Week 24 ANCOVA are reported side by side rather than required to match. The MMRM uses longitudinal Week 8/16/24 observations and a repeated-measures covariance model, while the ANCOVA uses Week 24 observations only.

At Week 24:

- High Dose: MMRM -0.9271 versus observed ANCOVA -0.9234;
- Low Dose: MMRM -1.6131 versus observed ANCOVA -2.0283.

## 12. Descriptive statistics

Age is summarised using mean, standard deviation, median, Q1 and Q3. Categorical variables are summarised as counts and percentages. Safety incidence uses subject-level denominators. ACTOT outputs report baseline, post-baseline and change-from-baseline summaries by treatment where applicable.

## 13. Exploratory any-TEAE treatment comparison

For each Xanomeline arm versus placebo, the workflow reports subject-level TEAE risk, unadjusted risk difference, Wald 95% confidence interval and Fisher exact-test p-value.

## 14. Multiplicity

No confirmatory hypothesis family is defined. TEAE, ANCOVA and MMRM p-values are exploratory and are not multiplicity-adjusted.

## 15. QC and acceptance

The live workflow separates Python internal QC, official-reference validation, R/Python cross-language programming QC and MMRM model/data QC.

Required official-reference checks include 100% ADQSCIBC key coverage, 100% ADQSCIBC `DTYPE` agreement, 100% ADQSCIBC `QSSEQ` agreement, complete traceability of value discrepancies to the selected source row, and 100% selected ACTOT key/`DTYPE`/`QSSEQ` agreement.

Reference `AVAL` agreement is informational when the public source and public reference differ. The workflow does not alter source-derived values merely to make a reference match.

### 15.1 Independent R/Python programming QC

`R/independent_qc.R` reimplements selected analysis rules from the same public raw inputs. It does not call Python derivation code. Discrete derivations require exact agreement; ANCOVA numerical outputs require absolute difference no greater than `1e-8`.

The verified v0.5 run retains **16/16 required cross-language checks**, **10/10 Python unit tests** and **24/24 required Python pipeline QC checks**. The maximum R/Python ANCOVA numerical difference is `7.11e-15`.

This is a separate implementation by the same portfolio author, not independent review by a second programmer.

### 15.2 MMRM QC

Required MMRM checks are:

1. all three planned treatment arms are present;
2. Week 8, Week 16 and Week 24 are present;
3. the covariance visit variable is a factor;
4. `USUBJID + AVISIT` is unique;
5. `CHG = AVAL - BASE` exactly within numerical tolerance;
6. `BASE` is constant within subject;
7. the unstructured model returns a finite likelihood;
8. the heterogeneous AR(1) sensitivity model returns a finite likelihood;
9. six primary active-versus-placebo visit contrasts are produced;
10. primary contrast estimates, standard errors, df, confidence limits and p-values are finite;
11. two Week 24 primary contrasts are produced.

The verified v0.5 live run passes **11/11 required MMRM checks**. A required failure causes the R analysis step to exit non-zero; GitHub Actions still retains diagnostic outputs where available.

## 16. Sample-size demonstration

A separate utility provides equal-allocation normal-approximation sample-size calculations for two-arm continuous and binary endpoints. These examples demonstrate the calculation workflow and are not presented as the original pilot study's design assumptions.

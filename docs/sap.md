# Statistical Analysis Plan — portfolio version 0.7

## 1. Scope

This Statistical Analysis Plan (SAP) specifies independent portfolio safety and questionnaire-efficacy analyses using public CDISC pilot data. It is not sponsor-approved and is not a regulatory-submission SAP.

Version 0.3 added public-reference validation against `ADQSCIBC` and `ADQSADAS`. Version 0.4 added a separate R implementation for selected programming QC. Version 0.5 added longitudinal ACTOT MMRM. Version 0.6 added executable SAP-to-TLF structural traceability. Version 0.7 adds a separate, machine-readable protocol-design and sample-size exercise with multiplicity, dropout inflation, achieved-power back-checking and design QC.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised if DS contains a record with `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population if at least one EX record is observed.

### 2.3 CIBIC+ analysis population

Subjects must be randomised and have numeric public QS records with `QSTESTCD == "CIBIC"`. The output parameter code is `CIBICVAL`, matching the public reference ADaM.

### 2.4 ACTOT efficacy population

The portfolio efficacy analysis uses randomised subjects with a numeric ACTOT baseline and at least one numeric post-baseline ACTOT value.

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

- `ASTDT`: parsed from `AESTDTC`;
- `AENDT`: parsed from `AEENDTC` when available;
- `TRTEMFL`: `Y` when `ASTDT >= TRTSDT` and `ASTDT <= TRTEDT + 30 days`;
- `RELFL`: `Y` for `AEREL` in `POSSIBLE`, `PROBABLE`, `DEFINITE`, or `RELATED`;
- `MODSEVFL`: `Y` for `AESEV` in `MODERATE` or `SEVERE`;
- serious TEAE: `AESER == "Y"` and `TRTEMFL == "Y"`.

No partial-date imputation is performed for AE start dates.

## 6. CIBIC+ analysis-window derivation

Public QS is filtered to `QSTESTCD == "CIBIC"`. Numeric `QSSTRESN` is mapped to `AVAL`. The output uses `PARAMCD=CIBICVAL`.

| Analysis visit | Target day | Observation window |
|---|---:|---|
| Week 8 | 56 | days 2–84 |
| Week 16 | 112 | days 85–140 |
| Week 24 | 168 | day 141 onward |

Within a window, the record nearest the target day is selected. If no record is present, the latest prior record is carried forward and `DTYPE=LOCF`. `AWTARGET`, `AWLO`, `AWHI`, `AWTDIFF`, source visit/date and `QSSEQ` are retained.

The verified live run covers 705/705 public ADQSCIBC analysis keys with 100% `QSSEQ` and 100% `DTYPE` agreement. `AVAL` agreement is 695/705 (98.58%). For all ten value differences, the portfolio value equals the selected public SDTM QS `QSSTRESN`; the public reference ADaM value differs from that selected source record. These differences remain visible in `outputs/adqscibc_mismatch_source_trace.csv`.

## 7. Public ADQSADAS reference validation

The public `ADQSADAS` Dataset-JSON contains 12,463 rows for 254 subjects and 15 ADAS-Cog parameters. `ACTOT` (`Adas-Cog(11) Subscore`) contains 1,040 rows.

The public selected ACTOT structure contains 1,016 `ANL01FL=Y` records. The portfolio reconstructs the same `USUBJID + AVISIT` keys and validates source `QSSEQ` and `DTYPE` against the public reference. Verified key, `QSSEQ` and `DTYPE` agreement are all 100%.

A separate diagnostic recomputes ADAS-Cog(11) totals from component items. This diagnostic does not replace source ACTOT values when public source and reference values differ.

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

Visit-specific treatment least-squares means and two active-versus-placebo contrasts are reported at each visit. No multiplicity adjustment is applied because these observed-data portfolio analyses are exploratory.

The verified primary Week 24 contrasts are:

| Contrast | Estimate | SE | 95% CI | df | p-value |
|---|---:|---:|---:|---:|---:|
| Xanomeline Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 142.05 | 0.1693 |
| Xanomeline High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 139.44 | 0.4220 |

### 11.4 Covariance sensitivity

The same fixed-effects model is refit using heterogeneous AR(1) covariance. Week 8, Week 16 and Week 24 are treated as equally spaced ordered analysis visits for this covariance structure.

| Covariance | logLik | AIC | BIC |
|---|---:|---:|---:|
| Unstructured | -1299.3136 | 2610.6272 | 2630.0777 |
| Heterogeneous AR(1) | -1309.7404 | 2627.4809 | 2640.4479 |

The unstructured model has lower AIC/BIC in this dataset. These are fit diagnostics, not a general covariance-selection rule.

### 11.5 Comparison with observed Week 24 ANCOVA

The MMRM and observed-case Week 24 ANCOVA are reported side by side rather than required to match. At Week 24:

- High Dose: MMRM -0.9271 versus observed ANCOVA -0.9234;
- Low Dose: MMRM -1.6131 versus observed ANCOVA -2.0283.

## 12. Descriptive statistics

Age is summarised using mean, standard deviation, median, Q1 and Q3. Categorical variables are summarised as counts and percentages. Safety incidence uses subject-level denominators. ACTOT outputs report baseline, post-baseline and change-from-baseline summaries by treatment where applicable.

## 13. Exploratory any-TEAE treatment comparison

For each Xanomeline arm versus placebo, the workflow reports subject-level TEAE risk, unadjusted risk difference, Wald 95% confidence interval and Fisher exact-test p-value.

## 14. Multiplicity for analysed public data

No confirmatory hypothesis family is defined for the portfolio analyses of the public study data. TEAE, ANCOVA and MMRM p-values are exploratory and are not multiplicity-adjusted.

The separate protocol-design exercise in Section 17 does define a planning hypothesis family and applies Bonferroni control. That design exercise is not retroactively applied to the exploratory analyses above.

## 15. QC and acceptance

The live workflow separates Python internal QC, public-reference validation, R/Python cross-language programming QC, MMRM model/data QC, structural SAP-to-TLF traceability and protocol-design QC.

The verified v0.7 live run has:

| QC layer | Result |
|---|---:|
| Python unit tests | **19/19 passed** |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| Complete SAP-to-TLF structural traceability | **15/15 TLFs** |
| Required protocol-design QC | **7/7 passed** |

The latest maximum R/Python ANCOVA numerical difference is `4e-14`.

### 15.1 R/Python programming QC

`R/independent_qc.R` reimplements selected analysis rules from the same public raw inputs. It does not call Python derivation code. Discrete derivations require exact agreement; ANCOVA numerical outputs require absolute difference no greater than `1e-8`.

This is a separate implementation by the same portfolio author, not independent review by a second programmer.

### 15.2 MMRM QC

Required MMRM checks cover treatment/visit completeness, factor-coded covariance visit, unique subject-visit keys, exact `CHG=AVAL-BASE`, constant subject baseline, finite likelihoods, finite contrast inference, six active-versus-placebo visit contrasts and two Week 24 primary contrasts. The verified run passes **11/11**.

### 15.3 SAP-to-TLF structural traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` define the expected relationship between objectives, populations, endpoints, methods, source/analysis datasets, generated outputs and QC evidence.

For each of 15 planned TLFs, CI requires:

- the output file to exist;
- minimum row count and required columns to match its contract;
- linked analysis dataset(s) to resolve;
- linked QC evidence to resolve;
- a SHA256 digest of the generated output to be recorded.

The verified run passes **15/15** TLFs on all structural checks. This gate supplements rather than replaces analysis-specific statistical QC.

## 16. TLF outputs

The planned output set is documented in `docs/tlf_shells.md`. It covers demographics, disposition, exposure, TEAE summaries, Week 24 ACTOT descriptives and ANCOVA, MMRM least-squares means and contrasts, covariance sensitivity, model diagnostics and the Week 24 MMRM-versus-ANCOVA comparison.

## 17. Protocol-design and sample-size exercise

### 17.1 Status and objective

Version 0.7 adds a separate illustrative planning exercise for a three-arm parallel-group study with Placebo, Xanomeline Low Dose and Xanomeline High Dose allocated 1:1:1. The planned continuous endpoint is Week 24 ACTOT change from baseline, with each active dose compared with placebo.

This is not the original source trial's sample-size calculation and does not claim that its assumptions are clinically justified.

### 17.2 Multiplicity and assumptions

The machine-readable specification in `spec/protocol_design.json` uses:

| Assumption | Value |
|---|---:|
| Family-wise two-sided alpha | 0.05 |
| Active-versus-placebo comparisons | 2 |
| Bonferroni alpha per comparison | 0.025 |
| Common planning SD | 6.0 |
| Anticipated dropout | 15% |
| Target power | 80% or 90% |
| Mean-difference scenarios | 2.0, 2.5 or 3.0 |

For a continuous two-arm comparison within the three-arm design:

```text
n_evaluable_per_arm = ceil(
    2 * SD^2 * (z_(1-alpha/2) + z_power)^2 / effect^2
)

n_randomised_per_arm = ceil(
    n_evaluable_per_arm / (1 - dropout_rate)
)

total_randomised = 3 * n_randomised_per_arm
```

### 17.3 Verified planning scenarios

| Scenario | Effect | Target power | Evaluable N/arm | Randomised N/arm | Total randomised | Achieved power |
|---|---:|---:|---:|---:|---:|---:|
| E2.0_P80 | 2.0 | 80% | 172 | 203 | 609 | 0.802 |
| E2.0_P90 | 2.0 | 90% | 224 | 264 | 792 | 0.901 |
| E2.5_P80 | 2.5 | 80% | 110 | 130 | 390 | 0.802 |
| E2.5_P90 | 2.5 | 90% | 143 | 169 | 507 | 0.900 |
| E3.0_P80 | 3.0 | 80% | 77 | 91 | 273 | 0.805 |
| E3.0_P90 | 3.0 | 90% | 100 | 118 | 354 | 0.902 |

The code back-calculates achieved power after integer rounding rather than assuming the requested power was preserved.

### 17.4 Design QC

The design run must pass all seven required checks:

1. Bonferroni per-comparison alpha reconciles exactly to family alpha divided by the number of comparisons;
2. dropout inflation does not reduce per-arm sample size;
3. achieved power at rounded evaluable N meets each target;
4. scenario identifiers are unique;
5. total randomised N equals randomised N per arm multiplied by three arms;
6. required N does not increase when the assumed treatment effect increases at fixed target power;
7. required N does not decrease when target power increases at fixed effect.

The verified v0.7 run passes **7/7**. `outputs/protocol_design_metrics.json` also records a SHA256 digest of the exact machine-readable design specification used for the run.

## 18. Statistical protocol review

`docs/protocol_statistical_review_checklist.md` records the statistical questions that should be resolved before a protocol is considered ready for SAP and programming work, including design, objectives/endpoints, estimand components, multiplicity, sample-size assumptions, analysis populations, missing data, model details, safety windows, programming implications and DSMB/interim-analysis boundaries.

The checklist is a portfolio review aid. It does not represent sponsor protocol sign-off, DSMB work or regulatory-submission ownership.

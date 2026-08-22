# Statistical Analysis Plan — consolidated portfolio version 0.13

## 1. Scope and evidence boundary

This SAP specifies an independent clinical-trial biostatistics portfolio built from public CDISC pilot and pharmaverse SDTM test data. It consolidates the current analysis plan through v0.13 while versioned addenda remain in the repository as change history.

This is **not** a sponsor-approved SAP, regulatory-submission document or production clinical-trial programming record. `*-style` datasets are not claimed to be submission-ready ADaM.

The current portfolio includes:

- ADSL-/ADAE-style safety derivations;
- CIBIC+/ACTOT efficacy derivations and public-reference checks;
- observed Week 24 ANCOVA and LOCF supportive analysis;
- observed-data ACTOT longitudinal MMRM;
- separate R/Python programming QC;
- an ICH E9(R1)-style ACTOT estimand specification;
- arm/visit missingness and disposition review;
- deterministic fixed-delta missing-data sensitivity and directional tipping points;
- v0.13 subject-level multiple-imputation (MI) sensitivity with independent Monte Carlo precision QC;
- TLF-style outputs T01-T21;
- protocol-design/sample-size and randomisation/initial-kit portfolio exercises;
- analysis-dataset/TLF reviewer and statistical change-impact gates.

The controlled analysis sequence is:

```text
estimand
  -> missingness review
  -> primary MMRM
  -> deterministic fixed-delta sensitivity
  -> subject-level MI sensitivity
  -> MCSE precision QC
  -> TLF contracts
  -> change impact
  -> executable traceability
```

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised when DS contains `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population when at least one EX record is observed.

### 2.3 CIBIC+ analysis population

Subjects must be randomised and have numeric public QS records with `QSTESTCD == "CIBIC"`. The analysis parameter code is `CIBICVAL`.

### 2.4 ACTOT estimand target population

The ACTOT estimand target population is randomised subjects with an observed numeric baseline ACTOT value. Verified public-data target N: **254**.

### 2.5 Week 24 observed ANCOVA population

Subjects in the ACTOT target population with an observed Week 24 ACTOT value. Verified N: **116**.

### 2.6 LOCF supportive population

Subjects with baseline ACTOT and an eligible post-baseline ACTOT value through analysis day 168. The latest eligible value is carried forward for the supportive Week 24 ANCOVA. Verified N: **235**.

### 2.7 MMRM population

Subjects with baseline ACTOT and at least one observed numeric ACTOT value at Week 8, Week 16 or Week 24. LOCF rows do not enter the MMRM. Verified input: **451 observed post-baseline records from 189 subjects**.

### 2.8 v0.13 MI pairwise populations

The target population is the same 254 randomised subjects with observed baseline ACTOT. MI is run separately for:

- Xanomeline Low Dose versus Placebo;
- Xanomeline High Dose versus Placebo.

Within each pairwise analysis, every included subject is expanded to the controlled Week 8, Week 16 and Week 24 visit grid. Observed ACTOT change-from-baseline values are retained; unobserved scheduled outcomes remain missing before imputation.

## 3. Treatment, exposure and disposition

Treatment labels are carried from DM into planned/actual treatment variables.

Exposure summaries use EX:

- `TRTSDT`: earliest parsed exposure start;
- `TRTEDT`: latest parsed exposure end, with documented DM/DS fallback when required;
- `EXDURN_RAW`: duration based only on observed EX dates;
- `TRTDURN`: final treatment-window duration after controlled fallback;
- `EXN`: observed EX-record count;
- dose summaries from numeric EX dose values.

Disposition uses DS. `COMPLFL` identifies completed subjects; final disposition and discontinuation context are derived from the last disposition event by date/sequence.

## 4. Safety analysis

AE records are linked to subject treatment/population context.

Portfolio TEAE definition:

```text
ASTDT >= TRTSDT
and
ASTDT <= TRTEDT + 30 days
```

No partial-date imputation is applied to missing AE start dates.

Safety TLFs include demographics, disposition, exposure, TEAE overview, SOC/PT, severity and exploratory any-TEAE risk differences. Exploratory risk-difference comparisons are not multiplicity-adjusted.

## 5. CIBIC+ derivation

Public QS is filtered to `QSTESTCD == "CIBIC"`; `QSSTRESN` maps to analysis `AVAL`.

| Analysis visit | Target day | Window |
|---|---:|---|
| Week 8 | 56 | days 2-84 |
| Week 16 | 112 | days 85-140 |
| Week 24 | 168 | day 141 onward |

Within each window, the observed record nearest target day is selected. If no record exists, the latest prior post-baseline record is carried forward with `DTYPE=LOCF`.

Verified public-reference checks include 705/705 selected CIBIC keys, 100% `QSSEQ`, 100% `DTYPE`, and 695/705 (98.58%) `AVAL` agreement. The ten source/reference value differences remain visible and trace to the exact selected public QS source row.

## 6. ACTOT source derivation and public-reference review

ACTOT records are derived from public QS with baseline, post-baseline analysis visit, source sequence, `BASE` and `CHG = AVAL - BASE` retained.

Official `ADQSADAS` contains 12,463 rows for 254 subjects across 15 ADAS-Cog parameters. The portfolio reconstructs all **1,016/1,016** selected ACTOT analysis keys with exact selected `QSSEQ` and `DTYPE` agreement.

An 11-item ADAS-Cog total recalculation is retained only as a diagnostic. It does not replace the public source ACTOT value.

## 7. Week 24 ANCOVA

Model:

```text
Week 24 AVAL = intercept + treatment + centred BASE + error
```

Two analysis sets are reported: observed Week 24 and LOCF supportive sensitivity. Treatment LS means and active-versus-placebo contrasts include estimate, SE, two-sided 95% CI, residual df and p-value. LOCF is not the primary estimator for the ACTOT estimand.

## 8. Primary longitudinal MMRM

The primary longitudinal ACTOT model uses observed Week 8, Week 16 and Week 24 change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit uses REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. A heterogeneous AR(1) fit with the same fixed-effects structure is retained as covariance sensitivity.

Verified Week 24 primary contrasts:

| Contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not source-trial confirmatory efficacy results.

## 9. ACTOT estimand

Machine-readable estimand: `EST-ACTOT-W24-TP`.

| Attribute | Portfolio specification |
|---|---|
| Treatment | Placebo, Low Dose, High Dose; each active arm versus placebo |
| Population | Randomised subjects with observed baseline ACTOT |
| Variable | Week 24 ACTOT change from baseline |
| Intercurrent event | Treatment discontinuation |
| Strategy | Treatment policy |
| Population summary | Active-minus-placebo adjusted mean change |

The primary observed-data MMRM is interpreted under a working MAR missing-data assumption. MAR is an estimator assumption, not an estimand attribute.

The current public run contains **0 observed ACTOT arm-visit records after recorded treatment discontinuation**. The treatment-policy retention rule is executable and unit-tested but has no positive post-discontinuation live-data example in this dataset.

## 10. Missingness review

T16 reports arm × Week 8/16/24 observed/missing ACTOT counts in the estimand target population. T17 reports recorded final-disposition context among subjects missing Week 24.

Verified Week 24 missingness:

| Arm | Target N | Observed | Missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Low Dose | 96 | 27 | 69 | 71.9% |
| High Dose | 72 | 30 | 42 | 58.3% |
| **Overall** | **254** | **116** | **138** | **54.3%** |

Recorded final disposition is adverse event for 8/27 placebo, 49/69 Low Dose and 34/42 High Dose subjects missing Week 24. These descriptive counts do not establish the truth of MAR or MNAR.

## 11. Deterministic fixed-delta missing-data sensitivity

The v0.12 fixed-delta analysis remains a controlled deterministic pattern-mixture mean-shift diagnostic. It is not subject-level MI and is not reference-based imputation.

For each primary Week 24 active-versus-placebo contrast:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

The controlled grid is `0.0, 0.5, ..., 6.0` ACTOT points under common worsening, active-only worsening and divergent worsening. Both primary Week 24 MMRM contrasts are already non-significant at delta=0, so the primary threshold is the positive delta at which the shifted point estimate reaches zero.

Verified thresholds:

| Scenario | Low vs Placebo | High vs Placebo |
|---|---:|---:|
| Common worsening | 3.985 | 3.442 |
| Active-only worsening | 2.244 | 1.589 |
| Divergent worsening | 1.562 | 1.033 |

T18 fixed-delta CI/p-value columns reuse primary MMRM SE/df after deterministic shift. They do not include imputation-model or delta uncertainty and are not Rubin-pooling inference.

## 12. v0.13 subject-level MI sensitivity

The controlled specification is `spec/mi_sensitivity.json`.

Imputation model:

- R package: `rbmi` 1.6.1;
- method: approximate-Bayesian MI;
- covariance: unstructured and common across the two treatment groups within each pairwise analysis;
- estimation: REML;
- history: Week 8, Week 16 and Week 24 ACTOT change from baseline;
- model terms: baseline-by-visit and treatment-by-visit;
- imputations: **200**;
- maximum allowed bootstrap-fit failure fraction: **10%**;
- fixed random seeds separately for the two active-versus-placebo comparisons.

Each imputed data set is analysed by Week 24 ANCOVA with treatment and baseline ACTOT. Active-minus-placebo estimates are combined using Rubin pooling. Reported inference includes estimate, SE, 95% CI, two-sided p-value and Monte Carlo standard errors.

The MAR pairwise MI estimates are compared with the existing three-arm Week 24 MMRM only as a diagnostic. Equality is not required because the estimators are different.

### 12.1 Controlled departures from MAR

The same imputation draws are reused for four scenarios:

1. `MAR`: no delta adjustment;
2. `ACTIVE_PLUS_1`: +1 ACTOT point for originally missing Week 24 outcomes in the active arm;
3. `ACTIVE_PLUS_2`: +2 ACTOT points for originally missing Week 24 outcomes in the active arm;
4. `DIVERGENT_1`: +1 in the active arm and -1 in placebo for originally missing Week 24 outcomes.

Because lower ACTOT is favourable, positive active-arm deltas represent an adverse departure. Delta is permitted only for outcomes that were originally missing at Week 24. Observed Week 24 outcomes and non-Week-24 outcomes must not be shifted.

### 12.2 Monte Carlo precision gate

A separate QC gate calculates:

```text
MCSE(estimate) / pooled SE
```

for each MAR pairwise comparison. The controlled maximum is **7.5%**. Model convergence and Monte Carlo precision are separate acceptance questions: zero fit failures does not make a run acceptable if the finite-imputation MCSE ratio exceeds the threshold.

A sensitivity result that fails this precision gate is not accepted as QC-complete until it is rerun or the controlled MI assumptions are changed through change control.

### 12.3 MI outputs

- T20: `outputs/table20_rbmi_mar_pairwise.csv`;
- T21: `outputs/table21_rbmi_delta_sensitivity.csv`;
- `outputs/rbmi_draw_diagnostics.csv`;
- `outputs/rbmi_delta_audit.csv`;
- `outputs/rbmi_mi_qc.csv`;
- `outputs/rbmi_mcse_diagnostics.csv`;
- `outputs/rbmi_mcse_qc.csv`;
- `outputs/rbmi_vs_mmrm_week24.csv`.

## 13. Programming QC

A separate R implementation reconstructs selected safety/efficacy derivations from the same raw public sources and is compared with Python only after its own results are generated. This is same-author cross-language replication, not independent second-programmer review.

## 14. TLF plan

Current effective TLF scope is **T01-T21**.

- T01-T07: safety/demographics;
- T08-T10: Week 24 ACTOT descriptives/ANCOVA;
- T11-T15: longitudinal MMRM and diagnostics;
- T16-T17: missingness/disposition context;
- T18: 78-row deterministic fixed-delta sensitivity grid;
- T19: six analytic directional tipping points;
- T20: MAR subject-level MI pairwise analysis, minimum 2 rows;
- T21: delta-adjusted MI sensitivity, minimum 8 rows.

`spec/analysis_traceability.csv` and `spec/output_contracts.json` are executable specifications for these outputs. T20/T21 require their dedicated MI/MCSE/draw/delta QC evidence, not only final CSV structure.

## 15. Required QC gates

The v0.13 workflow retains separate blocking layers for:

- Python derivation/pipeline QC;
- public CDISC reference validation;
- separate R/Python programming checks;
- MMRM data/model/inference QC;
- estimand/missing-data review;
- deterministic fixed-delta sensitivity QC;
- subject-level MI model/pooling/delta-application QC;
- independent MCSE precision QC;
- analysis-dataset/TLF reviewer;
- protocol-design and randomisation/initial-kit QC;
- statistical change-impact assessment;
- **21-TLF** structural traceability.

Required failures exit non-zero. Aggregate unit-test totals are intentionally not hard-coded into this SAP because the test suite can grow without changing the statistical plan.

## 16. Statistical change control

`spec/change_impact_graph.json` and `spec/change_requests.json` define the current controlled dependency model. There are **seven** simulated change requests.

CR-006 controls the deterministic fixed-delta sensitivity assumptions for T18/T19. CR-007 controls v0.13 MI assumptions including imputation count, longitudinal imputation model, MCSE threshold and delta scenarios for T20/T21.

Upstream changes must propagate rather than leave stale sensitivity analyses. In particular:

- CR-003 primary ACTOT visit changes propagate to T20/T21;
- CR-005 treatment-discontinuation/intercurrent-event strategy changes propagate to T20/T21;
- CR-007 directly requires review/regeneration of MI analysis, MCSE QC, T20/T21, relevant specifications and controlled documents.

These requests are portfolio simulations and do not themselves change the analysed results.

## 17. Protocol-design and randomisation exercises

A separate portfolio planning specification evaluates a three-arm Week 24 ACTOT design under two active-versus-placebo comparisons, Bonferroni family-wise alpha control, common SD assumptions, dropout inflation and target-power scenarios.

The selected illustrative `E2.5_P80` scenario drives a deterministic 390-subject stratified permuted-block randomisation and initial-kit coding exercise. This is not an IRT/IWRS production schedule and does not model drug-supply operations, resupply, expiry, replacement or emergency unblinding.

## 18. Controlled supporting documents

- `docs/sap_v0_9_review_addendum.md`
- `docs/sap_v0_10_change_control_addendum.md`
- `docs/sap_v0_11_estimand_addendum.md`
- `docs/sap_v0_12_mnar_addendum.md`
- `docs/sap_v0_13_rbmi_addendum.md`
- `docs/estimand_missing_data_review.md`
- `docs/mnar_sensitivity.md`
- `docs/qc_plan.md`
- `docs/tlf_shells.md`
- `docs/tlf_shells_v0_13_addendum.md`
- `docs/analysis_traceability.md`
- `docs/change_control_impact_assessment.md`

Earlier addenda remain as portfolio change history; this consolidated document states the current effective **v0.13** analysis plan.
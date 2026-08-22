# Statistical Analysis Plan — consolidated portfolio version 0.12

## 1. Scope and evidence boundary

This SAP specifies an independent clinical-trial biostatistics portfolio built from public CDISC pilot and pharmaverse SDTM test data. It consolidates the current analysis plan through v0.12 while the versioned addenda remain in the repository as change history.

This is **not** a sponsor-approved SAP, regulatory-submission document or production clinical-trial programming record. `*-style` datasets are not claimed to be submission-ready ADaM.

The current portfolio includes:

- ADSL-/ADAE-style safety derivations;
- CIBIC+/ACTOT efficacy derivations and public-reference checks;
- observed Week 24 ANCOVA and LOCF supportive analysis;
- observed-data ACTOT longitudinal MMRM;
- separate R/Python programming QC;
- an ICH E9(R1)-style ACTOT estimand specification;
- arm/visit missingness and disposition review;
- v0.12 fixed-delta missing-data sensitivity and directional tipping points;
- TLF-style outputs T01–T19;
- protocol-design/sample-size and randomisation/initial-kit portfolio exercises;
- analysis-dataset/TLF reviewer and statistical change-impact gates.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised when DS contains `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population when at least one EX record is observed.

### 2.3 CIBIC+ analysis population

Subjects must be randomised and have numeric public QS records with `QSTESTCD == "CIBIC"`. The analysis parameter code is `CIBICVAL`.

### 2.4 ACTOT estimand target population

The v0.11+ estimand target population is randomised subjects with an observed numeric baseline ACTOT value. The verified public-data target N is **254**.

### 2.5 Week 24 observed ANCOVA population

Subjects in the ACTOT target population with an observed Week 24 ACTOT value. Verified N: **116**.

### 2.6 LOCF supportive population

Subjects with baseline ACTOT and an eligible post-baseline ACTOT value through analysis day 168. The latest eligible value is carried forward for the supportive Week 24 ANCOVA. Verified N: **235**.

### 2.7 MMRM population

Subjects with baseline ACTOT and at least one observed numeric ACTOT value at Week 8, Week 16 or Week 24. LOCF rows do not enter the MMRM. Verified input: **451 observed post-baseline records from 189 subjects**.

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
| Week 8 | 56 | days 2–84 |
| Week 16 | 112 | days 85–140 |
| Week 24 | 168 | day 141 onward |

Within each window, the observed record nearest target day is selected. If no record exists, the latest prior post-baseline record is carried forward with `DTYPE=LOCF`.

Source visit/date, analysis-window variables and `QSSEQ` are retained.

Verified public-reference checks:

- selected CIBIC keys: **705/705**;
- `QSSEQ`: **100%** agreement;
- `DTYPE`: **100%** agreement;
- `AVAL`: 695/705 (98.58%) agreement.

For all ten `AVAL` differences, the portfolio value matches the selected public QS source value. The reference/source disagreement is retained in an auditable trace and is not overwritten.

## 6. ACTOT source derivation and public-reference review

ACTOT records are derived from public QS with baseline, post-baseline analysis visit, source sequence, `BASE` and `CHG = AVAL - BASE` retained.

Official `ADQSADAS` contains 12,463 rows for 254 subjects across 15 ADAS-Cog parameters. The portfolio reconstructs all **1,016/1,016** selected ACTOT analysis keys with exact selected `QSSEQ` and `DTYPE` agreement.

An 11-item ADAS-Cog total recalculation is retained only as a diagnostic. It does not replace the public source ACTOT value.

## 7. Week 24 ANCOVA

Model:

```text
Week 24 AVAL = intercept + treatment + centred BASE + error
```

Two analysis sets are reported:

1. observed Week 24;
2. LOCF supportive sensitivity.

Treatment LS means and active-versus-placebo contrasts include estimate, SE, two-sided 95% CI, residual df and p-value.

The LOCF analysis is not the primary estimator for the v0.11+ estimand.

## 8. Primary longitudinal MMRM

The primary longitudinal ACTOT model uses observed Week 8, Week 16 and Week 24 change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit:

- REML;
- unstructured within-subject covariance;
- Satterthwaite degrees of freedom;
- visit-specific estimated marginal means;
- Low Dose vs Placebo and High Dose vs Placebo contrasts at each visit.

A heterogeneous AR(1) fit using the same fixed-effects structure is retained as a covariance sensitivity analysis.

Verified Week 24 primary contrasts:

| Contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not source-trial confirmatory efficacy results.

## 9. ACTOT estimand

Machine-readable estimand: `EST-ACTOT-W24-TP`.

### 9.1 Treatment

Placebo, Xanomeline Low Dose and Xanomeline High Dose, with each active arm compared with placebo.

### 9.2 Population

Randomised subjects with observed baseline ACTOT.

### 9.3 Variable

ACTOT change from baseline at Week 24.

### 9.4 Intercurrent event and strategy

Recorded treatment discontinuation is handled with a **treatment-policy** strategy: observed outcomes after discontinuation would be retained.

The current public run contains **0 observed ACTOT arm-visit records after recorded treatment discontinuation**. The retention rule is therefore executable and unit-tested but has no positive post-discontinuation live-data example in this dataset.

### 9.5 Population-level summary

Active-minus-placebo difference in adjusted mean Week 24 change.

### 9.6 Estimator assumption

The primary observed-data MMRM is interpreted under a working **MAR** missing-data assumption. MAR is an estimator assumption, not an estimand attribute.

## 10. Missingness review

T16 reports arm × Week 8/16/24 observed/missing ACTOT counts in the estimand target population. T17 reports recorded final-disposition context among subjects missing Week 24.

Verified Week 24 missingness:

| Arm | Target N | Observed | Missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Low Dose | 96 | 27 | 69 | 71.9% |
| High Dose | 72 | 30 | 42 | 58.3% |
| **Overall** | **254** | **116** | **138** | **54.3%** |

Recorded final disposition is adverse event for 8/27 placebo, 49/69 Low Dose and 34/42 High Dose subjects missing Week 24.

These descriptive counts do not establish the truth of MAR or MNAR.

## 11. v0.12 fixed-delta missing-data sensitivity

The v0.12 sensitivity is a transparent fixed-delta pattern-mixture **mean-shift diagnostic**, not production MNAR multiple imputation or reference-based imputation.

For each primary Week 24 active-versus-placebo contrast:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

where `m_active` and `m_placebo` are observed Week 24 missing proportions.

ACTOT is treated as lower-is-better. Positive delta therefore represents a worse assumed missing outcome.

### 11.1 Controlled grid

```text
delta = 0.0, 0.5, ..., 6.0 ACTOT points
```

### 11.2 Scenarios

| Scenario | Active multiplier | Placebo multiplier |
|---|---:|---:|
| Common worsening | +1 | +1 |
| Active-only worsening | +1 | 0 |
| Divergent worsening | +1 | -1 |

### 11.3 Primary sensitivity threshold

Both primary Week 24 MMRM contrasts are already non-significant at delta=0. Therefore “loss of statistical significance” is not used as a tipping criterion.

The v0.12 primary threshold is the positive delta at which the shifted active-minus-placebo point estimate reaches zero:

```text
delta* = -theta_MAR / contrast_shift_per_delta
```

Verified thresholds:

| Scenario | Low vs Placebo | High vs Placebo |
|---|---:|---:|
| Common worsening | 3.985 | 3.442 |
| Active-only worsening | 2.244 | 1.589 |
| Divergent worsening | 1.562 | 1.033 |

All six analytic thresholds lie inside the controlled 0–6 grid.

T18 fixed-delta CI/p-value columns reuse the primary MMRM SE/df after deterministic shift. They do not include imputation-model/delta uncertainty and are not Rubin's-rules MI inference.

## 12. Programming QC

A separate R implementation reconstructs selected safety/efficacy derivations from the same raw public sources and is compared with Python only after its own results are generated.

Verified cross-language checks: **16/16 passed**. Maximum current ANCOVA numeric difference: **4e-14** against `1e-8` tolerance.

This remains same-author cross-language replication, not independent second-programmer review.

## 13. TLF plan

Current TLF scope is T01–T19.

- T01–T07: safety/demographics;
- T08–T10: Week 24 ACTOT descriptives/ANCOVA;
- T11–T15: longitudinal MMRM and diagnostics;
- T16–T17: missingness/disposition context;
- T18: 78-row fixed-delta sensitivity grid;
- T19: six analytic directional tipping points.

`spec/analysis_traceability.csv` and `spec/output_contracts.json` are executable specifications for these outputs. Verified structural traceability: **19/19**.

## 14. Required QC gates

Verified v0.12 live workflow:

| QC layer | Result |
|---|---:|
| Unit tests | 57/57 |
| Python pipeline | 24/24 |
| R/Python programming QC | 16/16 |
| MMRM | 11/11 |
| Estimand/missingness | 21/21 |
| Fixed-delta sensitivity | 19/19 |
| Dataset/TLF reviewer | 24/24 |
| Protocol design | 7/7 |
| Randomisation/kit | 10/10 |
| TLF traceability | 19/19 |
| Change-impact relationships | 118/118 |

Required failures exit non-zero and diagnostic outputs are retained where possible.

## 15. Statistical change control

`spec/change_impact_graph.json` and `spec/change_requests.json` are both version `0.12.0`.

Six simulated changes test transitive downstream review. New v0.12 propagation ensures that changes to the primary ACTOT visit, primary MMRM covariance, treatment-discontinuation strategy or fixed-delta sensitivity assumptions reach T18/T19 and dedicated sensitivity QC.

Verified live result: **118/118 required impact relationships declared and 118/118 required resources resolved**.

These requests are portfolio simulations and do not change the analysed results.

## 16. Protocol-design and randomisation exercises

A separate portfolio planning specification evaluates a three-arm Week 24 ACTOT design under two active-versus-placebo comparisons, Bonferroni family-wise alpha control, common SD assumptions, dropout inflation and target-power scenarios.

The selected illustrative `E2.5_P80` scenario drives a deterministic 390-subject stratified permuted-block randomisation and initial-kit coding exercise.

This is not an IRT/IWRS production schedule and does not model drug-supply operations, resupply, expiry, replacement or emergency unblinding.

## 17. Controlled supporting documents

- `docs/sap_v0_9_review_addendum.md`
- `docs/sap_v0_10_change_control_addendum.md`
- `docs/sap_v0_11_estimand_addendum.md`
- `docs/sap_v0_12_mnar_addendum.md`
- `docs/estimand_missing_data_review.md`
- `docs/mnar_sensitivity.md`
- `docs/qc_plan.md`
- `docs/tlf_shells.md`
- `docs/analysis_traceability.md`
- `docs/change_control_impact_assessment.md`

The earlier addenda remain as portfolio change history; this consolidated document states the current v0.12 analysis plan.

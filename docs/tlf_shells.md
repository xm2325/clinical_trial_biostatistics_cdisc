# TLF shells — portfolio version 0.5

These shells define the intended table structure for the portfolio analyses. They are planning documents, not sponsor-approved shells. Treatment columns use actual treatment (`TRT01A`) unless stated otherwise.

## Table 1. Demographics — Safety population

Treatment columns and Total.

Rows:
- N;
- age: mean (SD), median [Q1, Q3];
- sex: n (%);
- race: n (%).

Produced by: `outputs/table1_demographics.csv`.

## Table 2. Subject disposition — Randomised population

Treatment columns and Total.

Rows:
- randomised N;
- safety-population n (%);
- completed n (%);
- discontinued n (%);
- discontinuation reasons n (%).

Produced by: `outputs/table2_disposition.csv`.

## Table 3. Exposure — Safety population

Treatment columns.

Rows:
- treatment duration: mean (SD), median [Q1, Q3];
- observed EX-record count: median [Q1, Q3];
- maximum recorded dose: median [Q1, Q3].

Produced by: `outputs/table3_exposure.csv`.

## Table 4. Treatment-emergent adverse-event overview — Safety population

Treatment columns and Total.

Rows:
- Safety N;
- subjects with >=1 TEAE, n (%);
- subjects with >=1 serious TEAE, n (%);
- subjects with >=1 related TEAE, n (%);
- subjects with >=1 moderate/severe TEAE, n (%);
- discontinuation due to AE, n (%);
- total TEAE event count.

Produced by: `outputs/table4_teae_overview.csv`.

## Table 5. TEAEs by system organ class / preferred term — Safety population

Treatment columns.

Rows are system organ class and preferred term. Arm cells show unique-subject n (%). Preferred terms are ranked by overall subject incidence within the portfolio output. System organ class is carried from `AEBODSYS`.

Produced by: `outputs/table5_teae_soc_pt.csv`.

## Table 6. TEAEs by severity — Safety population

Treatment columns.

Rows:
- mild;
- moderate;
- severe.

Cells contain unique-subject n (%). A subject can contribute to more than one severity row.

Produced by: `outputs/table6_teae_severity.csv`.

## Table 7. Exploratory any-TEAE risk difference versus placebo — Safety population

One row per active arm versus placebo.

Columns:
- comparison;
- active-arm N;
- placebo N;
- active-arm risk;
- placebo risk;
- risk difference;
- 95% Wald confidence interval;
- Fisher exact-test p-value.

Produced by: `outputs/table7_teae_risk_difference.csv`.

## Table 8. ACTOT observed Week 24 descriptive statistics — Efficacy population

One row per treatment arm.

Columns:
- treatment;
- N;
- baseline mean and SD;
- observed Week 24 mean and SD;
- change-from-baseline mean and SD.

Produced by: `outputs/table8_actot_descriptive.csv`.

## Table 9. ACTOT Week 24 ANCOVA least-squares means

Separate blocks for:
1. observed Week 24;
2. LOCF sensitivity.

One row per treatment arm.

Columns:
- analysis;
- treatment;
- N;
- least-squares mean at the analysis-set mean baseline;
- standard error;
- two-sided 95% confidence interval;
- baseline reference value.

Produced by: `outputs/table9_actot_lsmeans.csv`.

## Table 10. ACTOT Week 24 ANCOVA active-versus-placebo contrasts

Separate blocks for observed Week 24 and LOCF sensitivity.

One row per active arm versus placebo.

Columns:
- analysis;
- comparison;
- total analysis N;
- estimate;
- standard error;
- two-sided 95% confidence interval;
- residual degrees of freedom;
- two-sided p-value;
- baseline reference value.

Produced by: `outputs/table10_actot_ancova_contrasts.csv`.

## Table 11. ACTOT MMRM least-squares means by visit — Primary unstructured covariance

Rows are treatment within Week 8, Week 16 and Week 24.

Columns:
- analysis visit;
- treatment;
- estimated marginal mean of ACTOT change from baseline;
- standard error;
- Satterthwaite degrees of freedom;
- two-sided 95% confidence interval.

Produced by: `outputs/mmrm_lsmeans.csv`.

## Table 12. ACTOT MMRM active-versus-placebo contrasts by visit — Primary unstructured covariance

Two rows per visit: Low Dose versus Placebo and High Dose versus Placebo.

Columns:
- analysis visit;
- comparison;
- treatment difference in change from baseline;
- standard error;
- Satterthwaite degrees of freedom;
- two-sided 95% confidence interval;
- t statistic;
- two-sided p-value;
- covariance label.

Expected primary rows: **6**.

Produced by: `outputs/mmrm_treatment_contrasts.csv`.

## Table 13. ACTOT MMRM covariance sensitivity

The same six visit-specific active-versus-placebo contrasts are reported under:
- primary unstructured covariance;
- heterogeneous AR(1) covariance.

Columns follow Table 12 and include the covariance label.

Expected rows: **12**.

Produced by: `outputs/mmrm_covariance_sensitivity.csv`.

## Table 14. MMRM model diagnostics

One row per covariance specification.

Columns:
- covariance model;
- estimation method;
- degrees-of-freedom method;
- observations;
- subjects;
- log likelihood;
- AIC;
- BIC;
- optimiser;
- fit-returned flag.

Produced by: `outputs/mmrm_model_diagnostics.csv`.

## Table 15. Week 24 MMRM versus observed-case ANCOVA

One row per active arm versus placebo.

Columns:
- comparison;
- MMRM estimate, SE, 95% CI and p-value;
- observed-case ANCOVA estimate, SE, 95% CI and p-value;
- MMRM minus ANCOVA estimate difference.

This table is diagnostic. Equality of the two estimates is not an acceptance criterion because the analyses use different information sets.

Produced by: `outputs/mmrm_vs_week24_ancova.csv`.

## Figure shells

No confirmatory figure is required by this portfolio SAP. Any future longitudinal profile or forest plot must identify the analysis population, estimand/statistic, confidence interval definition and source table; it must not replace the tabular numerical output used for QC.

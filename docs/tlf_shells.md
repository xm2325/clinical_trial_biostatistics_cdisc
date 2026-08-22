# TLF shells — portfolio version 0.13

These shells define the intended table structure for the portfolio analyses. They are planning documents, not sponsor-approved shells. Treatment columns use actual treatment (`TRT01A`) unless stated otherwise. The current effective registry is T01-T21; the v0.13 addendum is retained as change history.

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

Treatment columns. Rows are system organ class and preferred term. Arm cells show unique-subject n (%). Preferred terms are ranked by overall subject incidence within the portfolio output.

Produced by: `outputs/table5_teae_soc_pt.csv`.

## Table 6. TEAEs by severity — Safety population

Rows: mild, moderate and severe. Cells contain unique-subject n (%). A subject can contribute to more than one severity row.

Produced by: `outputs/table6_teae_severity.csv`.

## Table 7. Exploratory any-TEAE risk difference versus placebo — Safety population

One row per active arm versus placebo with arm N, placebo N, risks, risk difference, 95% Wald confidence interval and Fisher exact-test p-value.

Produced by: `outputs/table7_teae_risk_difference.csv`.

## Table 8. ACTOT observed Week 24 descriptive statistics — Efficacy population

One row per treatment arm with N, baseline mean/SD, observed Week 24 mean/SD and change-from-baseline mean/SD.

Produced by: `outputs/table8_actot_descriptive.csv`.

## Table 9. ACTOT Week 24 ANCOVA least-squares means

Separate blocks for observed Week 24 and LOCF sensitivity. One row per treatment arm with N, adjusted mean, SE, 95% CI and baseline reference.

Produced by: `outputs/table9_actot_lsmeans.csv`.

## Table 10. ACTOT Week 24 ANCOVA active-versus-placebo contrasts

Separate blocks for observed Week 24 and LOCF sensitivity. One row per active arm versus placebo with total N, estimate, SE, 95% CI, residual df, p-value and baseline reference.

Produced by: `outputs/table10_actot_ancova_contrasts.csv`.

## Table 11. ACTOT MMRM least-squares means by visit — Primary unstructured covariance

Rows are treatment within Week 8, Week 16 and Week 24, reporting estimated marginal mean of ACTOT change, SE, Satterthwaite df and 95% CI.

Produced by: `outputs/mmrm_lsmeans.csv`.

## Table 12. ACTOT MMRM active-versus-placebo contrasts by visit — Primary unstructured covariance

Two rows per visit: Low Dose versus Placebo and High Dose versus Placebo. Expected primary rows: **6**.

Produced by: `outputs/mmrm_treatment_contrasts.csv`.

## Table 13. ACTOT MMRM covariance sensitivity

The same six visit-specific active-versus-placebo contrasts are reported under primary unstructured and heterogeneous AR(1) covariance. Expected rows: **12**.

Produced by: `outputs/mmrm_covariance_sensitivity.csv`.

## Table 14. MMRM model diagnostics

One row per covariance specification with estimation method, df method, observations, subjects, log likelihood, AIC, BIC, optimiser and fit-returned flag.

Produced by: `outputs/mmrm_model_diagnostics.csv`.

## Table 15. Week 24 MMRM versus observed-case ANCOVA

One row per active arm versus placebo with MMRM and observed-case ANCOVA estimate, SE, 95% CI and p-value, plus their estimate difference. This table is diagnostic; equality is not an acceptance criterion because the analyses use different information sets.

Produced by: `outputs/mmrm_vs_week24_ancova.csv`.

## Table 16. ACTOT missingness by treatment and visit — Estimand target population

One row per treatment arm at Week 8, Week 16 and Week 24. The denominator is randomised subjects with an observed baseline ACTOT value.

Columns:
- treatment and analysis visit;
- nominal visit day;
- target N;
- observed N;
- missing N and missing percentage;
- subjects discontinued before/on the nominal visit;
- missing subjects with and without recorded discontinuation before/on the visit;
- observed records occurring after recorded treatment discontinuation.

Produced by: `outputs/table16_actot_missingness_by_visit.csv`.

## Table 17. Week 24 ACTOT missingness by recorded disposition context

Among target-population subjects missing Week 24 ACTOT, rows report the recorded final disposition category within treatment arm.

Columns:
- treatment;
- disposition/missingness category;
- n;
- arm-specific number missing Week 24;
- percentage of arm-specific missing subjects.

This is descriptive missingness context. It does not establish an MAR or MNAR mechanism and does not infer unrecorded intercurrent events.

Produced by: `outputs/table17_week24_missingness_by_disposition.csv`.

## Table 18. ACTOT fixed-delta missing-data sensitivity grid

Rows are sensitivity scenario × active-versus-placebo Week 24 contrast × delta value. The controlled delta grid is 0 to 6 ACTOT points in 0.5-point steps, giving **78 expected rows** for three scenarios and two contrasts.

Columns include:
- scenario and comparison;
- active and placebo Week 24 missing proportions;
- scenario multipliers and contrast shift per delta;
- primary MMRM estimate;
- shifted estimate;
- reused primary MMRM SE and df;
- fixed-delta 95% CI and p-value;
- direction of the shifted point estimate.

`delta=0` must reproduce the primary MMRM estimate exactly. The fixed-delta CI/p-value columns are diagnostic and do not represent multiple-imputation uncertainty.

Produced by: `outputs/table18_actot_delta_sensitivity.csv`.

## Table 19. ACTOT direction-of-effect tipping points

Six rows are expected: three fixed-delta scenarios × two active-versus-placebo Week 24 contrasts.

Columns include:
- scenario and comparison;
- contrast shift per delta;
- primary estimate and p-value;
- analytic delta at which the point estimate reaches zero;
- whether that threshold lies within the controlled grid;
- first grid delta whose shifted estimate is non-negative;
- significance-tipping status.

The primary threshold is the direction-of-effect crossing, not loss of statistical significance, because both primary Week 24 MMRM contrasts are already non-significant at delta zero.

Produced by: `outputs/table19_actot_directional_tipping_points.csv`.

## Table 20. ACTOT Week 24 MAR pairwise multiple-imputation sensitivity

Population: randomised subjects with observed baseline ACTOT, analysed separately as Low Dose versus Placebo and High Dose versus Placebo.

One row per active-versus-placebo comparison. Minimum rows: **2**.

Required columns include:

- comparison ID and label;
- active and reference arm;
- pooled active-minus-placebo estimate;
- pooled standard error;
- 95% confidence interval;
- two-sided p-value;
- Monte Carlo standard error of the estimate and standard error;
- pooling method;
- number of imputations.

Method: approximate-Bayesian `rbmi` multiple imputation using Week 8/16/24 longitudinal ACTOT history, followed by Week 24 ANCOVA adjusted for baseline and Rubin pooling. The controlled number of imputations is **200**.

Produced by: `outputs/table20_rbmi_mar_pairwise.csv`.

Required linked QC evidence includes `outputs/rbmi_mi_qc.csv`, `outputs/rbmi_mcse_qc.csv` and `outputs/rbmi_draw_diagnostics.csv`.

## Table 21. ACTOT Week 24 delta-adjusted multiple-imputation sensitivity

Rows are pairwise comparison × controlled sensitivity scenario. Expected and minimum rows: **8** (2 comparisons × 4 scenarios).

Required columns include all T20 inferential fields plus:

- scenario ID and label;
- active-arm delta;
- placebo delta;
- change in pooled estimate from the MAR scenario.

Controlled scenarios:

- MAR;
- active missing Week 24 outcomes +1 ACTOT point;
- active missing Week 24 outcomes +2 ACTOT points;
- active +1 and placebo -1 ACTOT point for originally missing Week 24 outcomes.

Observed Week 24 outcomes and non-Week-24 outcomes must not receive a delta shift. The same controlled imputation draws are reused across the four scenarios.

Produced by: `outputs/table21_rbmi_delta_sensitivity.csv`.

Required linked QC evidence includes `outputs/rbmi_mi_qc.csv`, `outputs/rbmi_mcse_qc.csv` and `outputs/rbmi_delta_audit.csv`.

## T20/T21 Monte Carlo precision requirement

T20/T21 are not accepted from table structure alone. For both MAR active-versus-placebo comparisons, the controlled criterion is:

```text
MCSE(estimate) / pooled SE <= 7.5%
```

This precision gate is separate from imputation-model fit/convergence.

## Figure shells

No confirmatory figure is required by this portfolio SAP. Any future longitudinal profile or forest plot must identify the analysis population, estimand/statistic, confidence interval definition and source table; it must not replace the tabular numerical output used for QC.
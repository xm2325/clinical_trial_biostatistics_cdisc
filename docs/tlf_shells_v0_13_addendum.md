# TLF shell addendum v0.13 — subject-level MI sensitivity

This addendum extends the v0.12 TLF shell document with T20 and T21. It is a portfolio planning document, not a sponsor-approved shell.

## Table 20. ACTOT Week 24 MAR pairwise multiple-imputation sensitivity

Population: randomised subjects with observed baseline ACTOT, analysed separately as Low Dose versus Placebo and High Dose versus Placebo.

One row per active-versus-placebo comparison.

Required columns:

- comparison ID and label;
- active and reference arm;
- pooled active-minus-placebo estimate;
- pooled standard error;
- 95% confidence interval;
- two-sided p-value;
- Monte Carlo standard error of the estimate and standard error;
- pooling method;
- number of imputations.

Method: approximate-Bayesian `rbmi` multiple imputation using Week 8/16/24 longitudinal ACTOT history, followed by Week 24 ANCOVA adjusted for baseline and Rubin pooling.

Produced by: `outputs/table20_rbmi_mar_pairwise.csv`.

## Table 21. ACTOT Week 24 delta-adjusted multiple-imputation sensitivity

Rows are pairwise comparison × controlled sensitivity scenario. Expected rows: **8** (2 comparisons × 4 scenarios).

Required columns include all T20 inferential fields plus:

- scenario ID and label;
- active-arm delta;
- placebo delta;
- change in the pooled estimate from the MAR scenario.

Controlled scenarios:

- MAR;
- active missing Week 24 outcomes +1 ACTOT point;
- active missing Week 24 outcomes +2 ACTOT points;
- active +1 and placebo -1 ACTOT point for originally missing Week 24 outcomes.

Observed Week 24 outcomes and non-Week-24 outcomes must not receive a delta shift.

Produced by: `outputs/table21_rbmi_delta_sensitivity.csv`.

## Required QC linkage

T20/T21 are not accepted from table structure alone. The traceability gate also requires:

- `outputs/rbmi_mi_qc.csv`;
- `outputs/rbmi_mcse_qc.csv`;
- `outputs/rbmi_draw_diagnostics.csv` for T20;
- `outputs/rbmi_delta_audit.csv` for T21.

The controlled MAR Monte Carlo precision criterion is `MCSE(estimate) / pooled SE <= 7.5%` for both active-versus-placebo comparisons.

# TLF shell addendum v0.14 — reference-based MI sensitivity

This addendum extends the controlled TLF plan with T22. It is a portfolio planning document, not a sponsor-approved shell.

## Table 22. ACTOT Week 24 reference-based multiple-imputation sensitivity

Population: randomised subjects with observed baseline ACTOT, analysed separately as Low Dose versus Placebo and High Dose versus Placebo.

Rows are active-versus-placebo comparison × reference-based strategy. Expected minimum rows: **8** (2 comparisons × 4 strategies).

Controlled strategies:

- MAR;
- Jump to Reference (`JR`);
- Copy Reference (`CR`);
- Copy Increments in Reference (`CIR`).

Required columns include:

- comparison ID and label;
- active and reference arm;
- strategy ID and label;
- active discontinuers and active subjects with an affected scheduled visit;
- pooled active-minus-placebo estimate and standard error;
- 95% confidence interval and two-sided p-value;
- Monte Carlo standard error of the estimate and standard error;
- pooling method and number of imputations;
- change in estimate from MAR;
- `MCSE(estimate) / pooled SE` and precision-pass flag.

Produced by: `outputs/table22_rbmi_reference_based.csv`.

## Required QC linkage

T22 is not accepted from table structure alone. Structural traceability also requires:

- `outputs/estimand_review.csv`;
- `outputs/rbmi_reference_ice_audit.csv` as analysis evidence;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`.

The controlled Monte Carlo precision criterion is `MCSE(estimate) / pooled SE <= 7.5%` for every comparison × strategy row.

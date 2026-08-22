# SAP addendum v0.13 — subject-level multiple-imputation sensitivity

## Purpose

This portfolio addendum extends the Week 24 ACTOT missing-data review with subject-level multiple imputation (MI). It is a sensitivity analysis alongside the existing observed-data MMRM and fixed-delta diagnostic; it does not replace the primary MMRM specification.

## Analysis population and comparisons

The target population is the 254 randomised subjects with an observed baseline ACTOT value. MI analyses are run separately for:

- Xanomeline Low Dose versus Placebo;
- Xanomeline High Dose versus Placebo.

Each pairwise analysis expands every included subject to the controlled Week 8, Week 16 and Week 24 visit grid. Observed ACTOT change-from-baseline values are retained and unobserved scheduled outcomes remain missing before imputation.

## Imputation model

The controlled specification is `spec/mi_sensitivity.json`.

- R package: `rbmi` 1.6.1;
- method: approximate-Bayesian MI;
- covariance: unstructured, common across the two treatment groups within each pairwise analysis;
- estimation: REML;
- longitudinal history: Week 8, Week 16 and Week 24 ACTOT change from baseline;
- model terms: baseline-by-visit and treatment-by-visit;
- imputations: 200;
- maximum allowed bootstrap-fit failure fraction: 10%.

Random seeds are fixed separately for the two active-versus-placebo comparisons.

## Week 24 analysis and pooling

Each imputed data set is analysed by Week 24 ANCOVA with treatment and baseline ACTOT. Active-minus-placebo estimates are combined using Rubin pooling. The analysis records estimate, standard error, 95% confidence interval, p-value and Monte Carlo standard errors.

The MAR pairwise MI estimates are compared with the existing three-arm Week 24 MMRM estimates only as a diagnostic. The estimators are different and are not required to be numerically equal.

## Controlled departures from MAR

The same imputation draws are reused for four scenarios:

1. `MAR`: no delta adjustment;
2. `ACTIVE_PLUS_1`: +1 ACTOT point for originally missing Week 24 outcomes in the active arm;
3. `ACTIVE_PLUS_2`: +2 ACTOT points for originally missing Week 24 outcomes in the active arm;
4. `DIVERGENT_1`: +1 in the active arm and -1 in placebo for originally missing Week 24 outcomes.

Because lower ACTOT is favourable, positive active-arm deltas represent an adverse departure. Delta is permitted only for outcomes that were originally missing at Week 24; observed values and non-Week-24 outcomes must not be shifted.

## Monte Carlo precision gate

A separate CI gate calculates `MCSE(estimate) / pooled SE` for each MAR comparison. The controlled maximum is 7.5%. This requirement is intentionally separate from model-fit convergence: a run can have zero model failures yet still be rejected if the finite-imputation Monte Carlo error is too large.

## Outputs

- T20: `outputs/table20_rbmi_mar_pairwise.csv`;
- T21: `outputs/table21_rbmi_delta_sensitivity.csv`;
- `outputs/rbmi_draw_diagnostics.csv`;
- `outputs/rbmi_delta_audit.csv`;
- `outputs/rbmi_mi_qc.csv`;
- `outputs/rbmi_mcse_diagnostics.csv`;
- `outputs/rbmi_mcse_qc.csv`;
- `outputs/rbmi_vs_mmrm_week24.csv`.

## Evidence boundary

This is an independent analysis of public pilot data for a portfolio. It demonstrates a controlled MI implementation, sensitivity-analysis specification, automated QC and traceability. It is not a sponsor-approved missing-data strategy, validated production program, regulatory analysis, or a claim of reference-based imputation. No J2R analysis is claimed in v0.13.

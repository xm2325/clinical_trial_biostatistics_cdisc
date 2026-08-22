# SAP addendum v0.14 — reference-based multiple-imputation sensitivity

## Purpose

This portfolio addendum adds a reference-based MI sensitivity analysis for Week 24 ACTOT. It is a sensitivity analysis alongside the primary observed-data MMRM, the v0.12 deterministic fixed-delta diagnostic and the v0.13 MAR/delta-adjusted subject-level MI analyses.

It does not change the primary estimand or primary estimator.

## Population and comparisons

The target population remains randomised subjects with observed baseline ACTOT. Analyses are performed separately for:

- Xanomeline Low Dose versus Placebo;
- Xanomeline High Dose versus Placebo.

## Intercurrent event and operational timing

Recorded treatment discontinuation is identified by `DCSFL=Y`. The discontinuation date used for this sensitivity analysis is `EOSDT`, consistent with the existing ACTOT estimand review.

Observed scheduled ACTOT values with `ADT <= EOSDT` are retained. The first affected scheduled visit is the first Week 8/16/24 visit after discontinuation and after all observed pre-discontinuation scheduled outcomes.

Reference-based strategy switching is permitted only when both of the following live-data checks are satisfied:

- zero observed scheduled ACTOT values with `ADT > EOSDT`;
- zero observed ACTOT values on or after the derived first affected visit supplied to `rbmi`.

## Imputation strategies

The controlled specification is `spec/reference_based_mi.json`.

The v0.13 approximate-Bayesian pairwise imputation model is reused with 200 imputations. Placebo remains MAR and supplies the reference distribution. Active-arm discontinuers with an affected scheduled visit are evaluated under:

1. `MAR` — Missing at Random;
2. `JR` — Jump to Reference;
3. `CR` — Copy Reference;
4. `CIR` — Copy Increments in Reference.

Parameter draws and ICE timing are held fixed across strategies within each pairwise analysis so strategy comparisons do not mix changes in random draws with changes in the missing-data assumption.

## Analysis and pooling

Each imputed data set is analysed by Week 24 ANCOVA with treatment and baseline ACTOT. Active-minus-placebo estimates are combined using Rubin pooling.

The reference-based analysis reports estimate, standard error, 95% confidence interval, two-sided p-value, Monte Carlo standard errors, number of imputations and change in estimate from the MAR strategy.

## Monte Carlo precision

Every comparison × strategy row must satisfy:

```text
MCSE(estimate) / pooled SE <= 7.5%
```

This is a blocking criterion separate from model-fit success.

## Planned output

T22: `outputs/table22_rbmi_reference_based.csv`, expected minimum 8 rows (2 comparisons × 4 strategies).

Required linked evidence includes:

- `outputs/estimand_review.csv`;
- `outputs/rbmi_reference_ice_audit.csv`;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`.

## Core live-run results used for formalisation

The successful core v0.14 run included 68 Low Dose and 39 High Dose active subjects with an affected scheduled visit. It produced all 8 planned rows, passed 27/27 reference-based MI checks, had zero model-fit failures and a maximum MCSE-to-SE ratio of 5.381%.

The JR/CR/CIR point estimates were closer to zero than MAR for both active comparisons in this data set. This observation is descriptive of the controlled public-data sensitivity analysis and is not assumed to hold for other trials.

## Evidence boundary

This is independent public-data portfolio work. It is not a sponsor-approved reference-based imputation strategy, validated production program, regulatory analysis or change to the source trial estimand.

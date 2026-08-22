# SAP addendum — portfolio v0.12 fixed-delta missing-data sensitivity

## Status and scope

This document is a portfolio addendum to the existing ACTOT analysis plan. It does not replace the primary observed-data MMRM, change the treatment-policy estimand, or claim sponsor approval.

## Reference estimand and estimator

The scientific estimand remains `EST-ACTOT-W24-TP`: active treatment versus placebo in Week 24 ACTOT change from baseline, with treatment discontinuation addressed using a treatment-policy strategy.

The primary estimator remains the observed-data REML MMRM with treatment-by-visit and baseline-by-visit fixed effects, unstructured within-subject covariance and Satterthwaite degrees of freedom. MAR remains the recorded working missing-data assumption for that estimator.

## Added sensitivity diagnostic

Version 0.12 adds a fixed-delta pattern-mixture mean-shift diagnostic after the primary MMRM and v0.11 missingness review have passed.

For each active-versus-placebo Week 24 MMRM contrast, the analysis applies the pre-specified scenario formula

```text
shifted contrast = primary MMRM contrast
                 + delta * (active missing proportion * active multiplier
                            - placebo missing proportion * placebo multiplier)
```

The delta grid is 0 to 6 ACTOT points by 0.5. The three scenario multiplier pairs are `(1,1)`, `(1,0)` and `(1,-1)` for common worsening, active-only worsening and divergent worsening respectively.

No observed ACTOT value is modified. Delta is a sensitivity parameter applied to the assumed mean of outcomes that are missing at Week 24 relative to the MAR reference.

## Primary sensitivity output

The primary v0.12 sensitivity diagnostic is the **direction-of-effect tipping delta**, defined as the smallest analytic positive delta at which the shifted active-minus-placebo point estimate reaches zero.

A loss-of-statistical-significance tipping point is not used because both current primary Week 24 MMRM contrasts are already non-significant at delta zero.

## TLFs

- **T18** — fixed-delta sensitivity grid by scenario, contrast and delta;
- **T19** — analytic direction-of-effect tipping points with the first non-negative grid point used as a bracketing check.

## QC and change control

The sensitivity gate is blocking in CI. Delta-zero reproduction, denominator reconciliation, adverse-direction monotonicity and analytic/grid tipping agreement are required checks.

The v0.12 change-impact graph also treats the sensitivity as downstream of the primary ACTOT visit and primary MMRM fit. A treatment-discontinuation estimand-strategy change requires review of the v0.12 sensitivity assumption. CR-006 separately tests a direct change to the delta range or scenario multipliers.

## Interpretation boundary

T18 fixed-delta confidence intervals reuse the primary MMRM standard error and degrees of freedom after a deterministic shift. They do not include imputation-model uncertainty and must not be described as multiple-imputation inference.

This addendum is an independent public-data portfolio exercise, not a sponsor-approved SAP amendment, regulatory analysis or production programming record.

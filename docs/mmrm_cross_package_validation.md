# MMRM cross-package validation — v0.16

## Purpose

v0.16 adds a distinct-package re-programming check for the primary observed-data ACTOT MMRM. The primary analysis remains `mmrm::mmrm` with REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. The validation program independently reconstructs the observed Week 8/16/24 analysis rows from `outputs/adqs_actot_style.csv` and fits the same fixed-effects mean model with `nlme::gls`.

The independent covariance is represented by `corSymm` plus visit-specific `varIdent` residual variances, which together form a general unstructured marginal covariance across the three scheduled post-baseline visits.

## What is compared

The controlled target is exactly the two Week 24 active-versus-placebo contrasts:

- Xanomeline Low Dose vs Placebo;
- Xanomeline High Dose vs Placebo.

The independent program constructs the Week 24 contrast vectors directly from the fitted fixed-effect design matrix rather than reusing the primary `emmeans` contrast output.

The blocking comparison is limited to quantities that should agree across equivalent REML marginal-model implementations:

- treatment-effect point estimate;
- model-based standard error;
- treatment-effect sign.

The pre-specified absolute tolerances are **0.0005** for the estimate and **0.0005** for the standard error. A failure is blocking.

## What is deliberately not compared

Degrees of freedom and p-values are not cross-validated in this layer. The primary `mmrm` model uses Satterthwaite inference; the `nlme` fit is being used as an independent point-estimate/model-based-SE reconstruction, not as a replacement inferential engine. Treating package-specific denominator-df calculations as if they must be identical would create a false validation requirement.

Multiplicity decisions continue to use the controlled primary `mmrm` p-values and the separate v0.15 Bonferroni decision layer.

## Live public-data agreement

The first complete live implementation run used **451 observed post-baseline ACTOT records from 189 subjects**. All **12/12** required cross-package checks passed without changing the pre-specified tolerances.

| Week 24 contrast | Primary `mmrm` estimate | Independent `nlme` estimate | Estimate abs diff | Primary SE | Independent SE | SE abs diff |
|---|---:|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131494994 | -1.6131364979 | 0.0000130015 | 1.1677899331 | 1.1677873008 | 0.0000026323 |
| High Dose vs Placebo | -0.9271379405 | -0.9271340803 | 0.0000038602 | 1.1511769515 | 1.1511759590 | 0.0000009925 |

Maximum absolute estimate difference: **1.3002e-05**. Maximum absolute SE difference: **2.6323e-06**. Both are far below the locked **0.0005** thresholds, and both treatment-effect signs agree.

These values are generated from the CI artifact; they are not hard-coded into the validation gate.

## Executable evidence

The CI sequence is:

```text
R/mmrm_analysis.R
  -> outputs/mmrm_treatment_contrasts.csv

R/mmrm_cross_package_qc.R
  -> outputs/mmrm_cross_package_contrasts.csv
  -> outputs/mmrm_cross_package_metrics.json

scripts/run_mmrm_cross_validation.py
  -> outputs/mmrm_cross_package_validation.csv
  -> outputs/mmrm_cross_package_qc.csv
  -> outputs/mmrm_cross_package_validation_metrics.json
  -> outputs/mmrm_cross_package_validation_summary.md
```

`spec/mmrm_cross_package_validation.json` locks the visit, hypothesis set, package-specific covariance labels, numerical tolerances and the deliberate exclusion of df/p-value comparison.

## Change control

The v0.16 change-impact extension makes this validation downstream of the primary ACTOT visit and covariance assumptions. Estimand-alignment changes also propagate to the independently reconstructed analysis rows and validation output. CR-010 simulates a change to the independent package, validation scope, controlled hypotheses or numerical tolerance and requires review of all validation inputs, outputs, specification and documentation.

## Evidence boundary

This is a distinct-package re-programming exercise performed by the portfolio author. It demonstrates an executable validation pattern, but it is **not** formal independent second-programmer validation, sponsor/CRO validated production programming, or regulatory submission QC.

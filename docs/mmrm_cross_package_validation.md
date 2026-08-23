# MMRM cross-package validation — v0.16

## Purpose

v0.16 adds a distinct-package re-programming check for the primary observed-data ACTOT MMRM. The primary analysis remains `mmrm::mmrm` with REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. The validation program independently reconstructs the observed Week 8/16/24 analysis rows from `outputs/adqs_actot_style.csv` and fits the same fixed-effects mean model with `nlme::gls`.

The independent covariance is represented by `corSymm` plus visit-specific `varIdent` residual variances, which together form a general unstructured marginal covariance across the three scheduled post-baseline visits.

## Analysis-population identity gate

The independent program does not consume `outputs/mmrm_analysis_dataset.csv` for fitting. It rebuilds the eligible rows from the source-derived ACTOT file and writes `outputs/mmrm_cross_package_analysis_dataset.csv`.

Before model estimates are compared, the blocking gate requires:

- unique `STUDYID × USUBJID × AVISIT` keys in both datasets;
- identical key sets;
- exact treatment agreement;
- `QSSEQ`, `AVAL`, `BASE` and `CHG` agreement within **1e-12**.

The validated public-data run contains **451/451 rows** and **189/189 subjects** in the primary and independent datasets. There are **0 missing/extra keys**, **0 treatment mismatches** and **0 numeric mismatch rows**; the maximum numeric row difference reported by the executable gate is **0** after CSV materialisation.

## Week 24 contrast validation

The controlled target is exactly the two Week 24 active-versus-placebo contrasts:

- Xanomeline Low Dose vs Placebo;
- Xanomeline High Dose vs Placebo.

The independent program constructs the Week 24 contrast vectors directly from the fitted fixed-effect design matrix rather than reusing the primary `emmeans` contrast output.

The blocking comparison requires:

- treatment-effect point-estimate absolute difference <= **0.0005**;
- model-based SE absolute difference <= **0.0005**;
- treatment-effect sign agreement.

| Week 24 contrast | Primary `mmrm` estimate | Independent `nlme` estimate | Estimate abs diff | Primary SE | Independent SE | SE abs diff |
|---|---:|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131494994 | -1.6131364979 | 0.0000130015 | 1.1677899331 | 1.1677873008 | 0.0000026323 |
| High Dose vs Placebo | -0.9271379405 | -0.9271340803 | 0.0000038602 | 1.1511769515 | 1.1511759590 | 0.0000009925 |

Maximum absolute estimate difference: **1.30015e-05**. Maximum absolute SE difference: **2.63230e-06**. Both are well below the locked thresholds and both signs agree.

Together with the six analysis-row checks, the final v0.16 gate passes **18/18 required checks**.

## What is deliberately not compared

Degrees of freedom and p-values are not cross-validated in this layer. The primary `mmrm` model uses Satterthwaite inference; the `nlme` fit is used for analysis-population, point-estimate and model-based-SE validation, not as a replacement inferential engine. Treating package-specific denominator-df calculations as if they must be identical would create a false validation requirement.

Multiplicity decisions continue to use the controlled primary `mmrm` p-values and the separate v0.15 Bonferroni decision layer.

## Executable evidence and provenance

The CI sequence is:

```text
R/mmrm_analysis.R
  -> outputs/mmrm_analysis_dataset.csv
  -> outputs/mmrm_treatment_contrasts.csv

R/mmrm_cross_package_qc.R
  -> outputs/mmrm_cross_package_analysis_dataset.csv
  -> outputs/mmrm_cross_package_contrasts.csv
  -> outputs/mmrm_cross_package_metrics.json

scripts/run_mmrm_cross_validation.py
  -> outputs/mmrm_cross_package_validation.csv
  -> outputs/mmrm_cross_package_qc.csv
  -> outputs/mmrm_cross_package_validation_metrics.json
  -> outputs/mmrm_cross_package_validation_summary.md
```

`spec/mmrm_cross_package_validation.json` locks the row-identity columns/tolerance, visit, hypothesis set, package-specific covariance labels, estimate/SE tolerances and the deliberate exclusion of df/p-value comparison.

`mmrm_cross_package_validation_metrics.json` records SHA256 fingerprints for the validation specification, both contrast sources and both analysis datasets so later numerical changes can be traced to changed inputs/specification rather than silently accepted.

## Change control

The v0.16 change-impact extension makes this validation downstream of the primary ACTOT visit and covariance assumptions. Estimand-alignment changes also propagate to the independently reconstructed analysis rows and validation output. CR-010 simulates a change to the independent package, row-identity rule, validation scope, controlled hypotheses or numerical tolerances and requires review of all validation inputs, outputs, specification and documentation.

The validated merged graph assesses **10 change requests**, **73 propagated component links** and **254/254 required impact relationships/resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources.

## Evidence boundary

This is a distinct-package re-programming exercise performed by the portfolio author. It demonstrates an executable validation pattern, but it is **not** formal independent second-programmer validation, sponsor/CRO validated production programming, or regulatory submission QC.

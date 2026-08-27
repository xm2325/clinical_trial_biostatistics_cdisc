# Method-to-role evidence matrix

This file separates implemented evidence from planned extensions. A method is marked implemented only when the repository contains runnable code and a real-data output for it.

| Scientific capability | Real-data evidence | Status | Next evidence |
|---|---|---|---|
| Longitudinal clinical outcomes | 15,261 unique participant-month PHQ-9 measurements reconstructed from 10,866 three-month intervals | Implemented | Nonlinear time and prespecified cohort sensitivity analyses |
| Mixed-effects modelling | PHQ-9 random-intercept mixed model across 4,036 participants; converged real-data fit | Implemented | Random-slope comparison and model diagnostics |
| Clinically meaningful score change | PHQ-specific 6-point reliable-improvement/deterioration flags; caseness crossing at 10 kept separate | Implemented | Add paired anxiety outcomes on a dataset that supports the full NHS service definition |
| MCID sensitivity | 20% relative reduction reported as a sensitivity analysis rather than a universal threshold | Implemented with boundary | Baseline-severity-stratified analysis |
| Deterioration classification | Participant-held-out category-deterioration model | Implemented | Freeze features at a defined prospective prediction timestamp before calling it risk forecasting |
| Calibration | Unweighted vs class-weight-balanced AUC/Brier/intercept/slope comparison | Implemented | Bootstrap uncertainty and temporal recalibration |
| Outcome availability / missingness | 19,792 expected participant-quarter opportunities; availability declines from 65.6% at month 3 to 41.6% at month 12; held-out availability AUC 0.623 | Implemented diagnostic | Distinguish questionnaire nonresponse, attrition and preprocessing if source-level reason codes become available |
| Subgroup review | Sex, race-indicator and insurance performance where sample size permits | Implemented baseline | Confidence intervals and subgroup calibration |
| Reproducibility | Zenodo source, published MD5 checks, CI, unit tests, zero participant overlap, uploaded real-data artifact | Implemented | Freeze a versioned result snapshot in a release |
| Trajectory phenotyping | Not yet claimed | Planned | Growth-mixture / latent-class comparison with minimum class-size and stability checks |
| Bayesian hierarchical modelling | Participant-level frequentist mixed model currently implemented | Planned extension | Bayesian partial pooling when service/clinician hierarchy is available |
| Causal inference | No treatment or pathway association is called causal | Correctly withheld | Separate target-trial-style module with explicit exposure, time zero, estimand and identification assumptions |
| Service benchmarking | Not part of PSYCHE-D | Planned | NHS Talking Therapies provider-level waiting-time, improvement, recovery and deterioration module |
| Clinical NLP | Not part of PSYCHE-D | Planned only if useful | Negation, temporality and section-aware extraction on a suitable public clinical-text dataset |

## Real-data interview case

**Question:** You have repeated clinical outcome data and want to identify patients at risk of deterioration. What would you do before selecting a complex model?

**Evidence-backed answer from this repository:**

1. define the outcome and clinically meaningful change rules from source-supported scores;
2. reconstruct the repeated-measure structure and verify shared time-point consistency;
3. split by patient so repeated records cannot leak across train and test;
4. fit a transparent repeated-measures baseline before adding more complex trajectory models;
5. report calibration and Brier score as well as discrimination;
6. audit whether outcome availability changes over follow-up and whether it is predictable;
7. inspect subgroup performance with minimum sample-size rules and uncertainty in mind;
8. fix the prediction timestamp before making a prospective risk claim;
9. keep descriptive trends, prediction and causal effects as separate targets.

## Critical appraisal link to Paul Wallang's prior work

The DBT service evaluation by Webb, Girardi, Fox and Wallang used routinely collected clinical records with baseline, 6-month and 12-month outcomes and ANOVA/non-parametric comparisons. The published paper also states that outcome data were not available for the whole sample and that improvements could not be attributed directly to DBT. Its patient-level data are confidential.

The useful interview position is therefore not that this older service evaluation is incorrect. It is that a modern analysis of the same class of routine-care question can add explicit repeated-measures models, outcome-availability analysis, clinically meaningful individual change, calibration, patient-level validation and clearly separated causal claims. This repository demonstrates several of those additions on an open longitudinal dataset without claiming access to private Clinical Partners or St Andrew's Healthcare records.

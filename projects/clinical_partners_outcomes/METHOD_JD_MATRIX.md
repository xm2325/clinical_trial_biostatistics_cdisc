# Method-to-role evidence matrix

This file separates implemented evidence from planned extensions. It is intentionally conservative: a method is marked implemented only when the repository contains runnable code and a real-data output for it.

| Scientific capability | v0.1 evidence | Status | Next evidence |
|---|---|---|---|
| Longitudinal clinical outcomes | PHQ-9 category start/end transitions over repeated participant observations; explicit participant/month parsing | Implemented baseline | Add score-level mixed-effects trajectories only if raw scores are available in a licensed dataset |
| Predictive deterioration | Participant-held-out deterioration model | Implemented | Compare prespecified baseline model with a nonlinear benchmark without changing the held-out cohort |
| Calibration | Brier score, calibration intercept, calibration slope, calibration curve | Implemented | Bootstrap uncertainty and temporal calibration review |
| Missing data | Endpoint-observation rates by study month plus prediction of endpoint availability | Implemented diagnostic | Multiple imputation and MNAR sensitivity require a score-level analysis dataset and a defined estimand |
| Subgroup review | Sex, race-indicator and insurance subgroup performance where sample size permits | Implemented | Confidence intervals and calibration-by-subgroup; avoid unsupported fairness claims |
| Reproducibility | Pinned source record, MD5 verification, CI run, unit tests, participant-overlap invariant, uploaded outputs | Implemented | Add machine-readable provenance manifest and frozen result snapshot |
| Reliable change / MCID | No category-to-score conversion is invented | Correctly withheld | Use open item/score-level PHQ-9/GAD-7 data with a prespecified reliability/MCID definition |
| Mixed-effects / hierarchical modelling | Not yet claimed from category-only endpoint | Planned | Patient random intercept/slope; service/clinician partial pooling when a suitable data hierarchy exists |
| Trajectory phenotyping | Not yet claimed | Planned | Growth mixture / latent class model with stability and class-size checks on score-level longitudinal data |
| Causal inference | No causal interpretation of PSYCHE-D observational associations | Correctly withheld | Separate target-trial-style module for a modifiable pathway exposure using an appropriate observational dataset |
| Service benchmarking | Not part of PSYCHE-D | Planned | NHS Talking Therapies provider-level waiting-time, improvement, recovery and deterioration module |

## Interview case supported by v0.1

**Question:** You have repeated clinical outcome data and want to identify patients at risk of deterioration. What would you do before selecting a complex model?

**Evidence-backed answer from this repository:**

1. define the outcome using the source data rather than an invented label;
2. inspect the longitudinal sampling structure and observation process;
3. split by patient so repeated records cannot leak across train and test;
4. establish a transparent baseline model;
5. report calibration and Brier score in addition to discrimination;
6. test whether outcome availability is systematically predictable;
7. inspect subgroup performance subject to minimum sample-size rules;
8. separate prediction from causal claims and from clinically meaningful-change claims.

## Critical appraisal link to the existing literature

A useful interview position is not that older routine-care studies are 'wrong', but that modern clinical data science can add stronger handling of repeated measures, missing outcome collection, calibration, patient-level validation and explicit estimands. This repository is constructed to demonstrate those additions on open data rather than to claim access to private Clinical Partners records.

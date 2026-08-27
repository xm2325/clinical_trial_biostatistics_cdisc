# Method-to-role evidence matrix

This file separates implemented real-data evidence from planned work. A method is marked implemented only when the repository contains runnable code, CI checks and a real-data output for it.

| Scientific capability | Real-data evidence | Status | Next evidence |
|---|---|---|---|
| Longitudinal clinical outcomes | 15,261 unique participant-month PHQ-9 measurements reconstructed from 10,866 three-month intervals | Implemented | Nonlinear time and prespecified cohort sensitivity analyses |
| Mixed-effects modelling | PHQ-9 random-intercept mixed model across 4,036 participants; converged real-data fit | Implemented | Random-slope comparison and residual/model diagnostics |
| Clinically meaningful score change | PHQ-specific 6-point reliable-improvement/deterioration flags; caseness crossing at 10 kept separate | Implemented | Add paired anxiety outcomes on a dataset supporting the full NHS service definition |
| MCID sensitivity | 20% relative reduction reported as a sensitivity analysis rather than a universal threshold | Implemented with boundary | Baseline-severity-stratified analysis |
| Prospective prediction-time design | Strict model freezes features at interval start: PHQ-9 start score plus participant baseline/screener variables; zero patient overlap | Implemented v0.3 | Temporal validation on a later cohort and threshold/workload analysis |
| Prospective reliable deterioration model | 3-month PHQ-9 increase >=6 points; strict t0 AUC 0.620, AP 0.107, Brier 0.062, calibration slope 0.827 | Implemented baseline | Bootstrap uncertainty, recalibration and external/temporal validation before clinical use |
| Leakage sensitivity | Broader interval-feature reference AUC 0.628 vs strict t0 AUC 0.620; broader model explicitly not treated as deployment-safe | Implemented v0.3 | Feature-level availability timestamps in a clinical source system |
| Calibration | Brier score, calibration intercept/slope, and class-weight sensitivity analyses | Implemented | Bootstrap uncertainty and temporal recalibration |
| Outcome availability / missingness | 19,792 expected participant-quarter opportunities; availability declines from 65.6% at month 3 to 41.6% at month 12; held-out availability AUC 0.623 | Implemented diagnostic | Distinguish questionnaire nonresponse, attrition and preprocessing if reason codes become available |
| Subgroup review | Sex, race-indicator and insurance performance where sample size permits | Implemented baseline | Confidence intervals and subgroup calibration |
| Trajectory phenotyping | 3,107 participants with >=3 PHQ-9 measures; GMM selects 3 classes using BIC and >=5% class-size rule; repeated-initialisation mean ARI 0.819 | Implemented exploratory v0.3 | External stability and clinical validation; compare with richer growth-mixture approaches |
| Service benchmarking | Latest official NHS Talking Therapies key-measures file parsed at Provider level; 6/18-week access, reliable deterioration/improvement, recovery and reliable recovery distributions | Implemented v0.3 | Case-mix-adjusted benchmarking requires patient-level covariates unavailable in the aggregate release |
| Service trend monitoring | Provider first-to-latest changes and England aggregate time series across June 2025-June 2026 | Implemented v0.3 | Longer historical series and formal control-chart specification |
| Access-outcome association | Provider-level Spearman summaries between 6-week access and outcome measures | Implemented as ecological description only | Patient-level causal analysis with explicit time zero, confounding control and identification assumptions |
| Reproducibility | Zenodo MD5 checks, latest published NHS source, CI, unit tests, zero participant overlap and uploaded real-data artifact | Implemented | Freeze a versioned release snapshot |
| Bayesian hierarchical modelling | Participant-level frequentist mixed model currently implemented | Planned extension | Bayesian service/clinician partial pooling when an appropriate hierarchy is available |
| Causal inference | No treatment, waiting-time or pathway association is called causal | Correctly withheld | Target-trial-style study with explicit exposure, time zero, estimand and assumptions |
| Clinical NLP | Not part of the available open structured data | Planned only if useful | Negation, temporality and section-aware extraction on a suitable public clinical-text dataset |

## v0.3 interview case

**Question:** You want a clinical deterioration model from routinely collected longitudinal data. What do you do before choosing a complex algorithm?

**Evidence-backed answer from this repository:**

1. define a clinically interpretable endpoint and separate it from diagnosis or treatment effect;
2. fix the prediction timestamp before feature engineering;
3. quarantine features whose source timing can extend beyond the prediction timestamp;
4. split by patient so repeated records cannot leak across train and test;
5. compare the strict prediction-time model with the broader feature model as a leakage sensitivity analysis rather than silently using future information;
6. report calibration and Brier score as well as AUC and average precision;
7. audit outcome availability over follow-up;
8. analyse longitudinal trajectories separately from prospective prediction;
9. treat model-based trajectory classes as exploratory until externally and clinically validated;
10. use national aggregate service data for benchmarking, not as a substitute for patient-level causal evidence.

## Link to the Clinical Partners research context

The DBT service evaluation by Webb, Girardi, Fox and Wallang used routine clinical records with baseline, 6-month and 12-month outcomes and ANOVA/non-parametric comparisons. The published paper states that outcome data were not available for the whole sample and that observed improvements could not be attributed directly to DBT; patient-level data are confidential.

The useful comparison is therefore methodological. A modern analysis of the same class of routine-care question can add explicit repeated-measures models, outcome-availability analysis, clinically meaningful individual change, calibrated patient-level validation, fixed prediction timestamps and clearly separated causal claims. v0.3 demonstrates those additions on open PSYCHE-D data and adds an external NHS Talking Therapies service benchmark without claiming access to private Clinical Partners records.

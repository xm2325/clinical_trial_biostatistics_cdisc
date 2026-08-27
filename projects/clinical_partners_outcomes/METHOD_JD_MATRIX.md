# Method-to-role evidence matrix

This file separates implemented evidence from planned work. A method is marked implemented only when the repository contains runnable code and a real-data output for it. v0.4 also records when an implemented method fails a robustness or causal-readiness gate.

| Scientific capability | Real-data evidence | Status | Interpretation / next evidence |
|---|---|---|---|
| Longitudinal clinical outcomes | 15,261 unique participant-month PHQ-9 measurements reconstructed from 10,866 three-month intervals | Implemented | Repeated score structure is explicit and checked for shared-boundary conflicts |
| Mixed-effects modelling | PHQ-9 random-intercept mixed model across 4,036 participants; converged fit | Implemented descriptive | Random slopes or nonlinear time are secondary to obtaining a service-linked hierarchy |
| Clinically meaningful score change | PHQ-specific 6-point reliable improvement/deterioration; caseness crossing at 10 kept separate | Implemented | Full NHS Talking Therapies reliable improvement/recovery requires the paired anxiety measure |
| MCID sensitivity | 20% relative reduction reported only as a sensitivity analysis | Implemented with boundary | No universal MCID claim |
| Prediction-time control | Strict model uses interval-start PHQ-9 plus baseline/screener variables; dynamic interval summaries excluded | Implemented v0.3 | Broad feature model kept only as leakage-risk reference |
| Participant-held-out prediction | Strict t0 AUC 0.620, AP 0.107, Brier 0.0621; zero participant overlap | Implemented v0.3 | Internal random participant hold-out only |
| Forward-time validation | Train endpoint months 3/6 and test endpoint months 9/12 on different participants; AUC 0.593 on 1,183 test rows / 748 participants | Implemented v0.4 | Shows weaker later-window performance; still internal to one study |
| Calibration | v0.4 temporal calibration intercept -0.693 and slope 0.762 | Implemented | Point calibration is not enough without uncertainty |
| Calibration/discrimination uncertainty | 300 participant-cluster bootstrap replicates; AUC 95% CI 0.527-0.658, calibration slope 0.283-1.243 | Implemented v0.4 | Quantifies held-out sampling uncertainty; does not measure external transportability |
| Decision-curve analysis | Net benefit evaluated over thresholds 0.02-0.20 against treat-all and treat-none | Implemented exploratory v0.4 | Point-estimate analysis only; no clinical threshold recommendation and no current net-benefit CI |
| Outcome availability / missingness | 19,792 expected participant-quarter opportunities; availability falls from 65.6% at month 3 to 41.6% at month 12; held-out availability AUC 0.623 | Implemented diagnostic | Cannot distinguish non-response, attrition and source preprocessing without reason codes |
| Subgroup review | Sex, race-indicator and insurance performance where sample size permits | Implemented baseline | Confidence intervals and subgroup calibration remain useful extensions |
| Trajectory phenotyping | v0.3 selected 3 classes among 3,107 participants; repeated-initialisation mean ARI 0.819 | Implemented exploratory | Not enough by itself for subtype validity |
| Trajectory specification sensitivity | Add residual SD ARI 0.389; diagonal covariance ARI 0.567; leave-last-out ARI 0.668 | Implemented v0.4; **fails strong stability gate** | Three-class solution is too specification-sensitive for a clinical-subtype claim |
| NHS service benchmarking | 182,512-row official key-measures file; 145 provider codes; June 2026 access/outcome distributions and ecological correlations | Implemented v0.3 | Aggregate provider statistics support benchmarking/hypothesis generation, not patient-level causal effects |
| Target-trial specification | Eligibility, strategies, time zero, follow-up, outcome, contrast and identification assumptions written for medication initiation | Implemented v0.4 | Protocol can be specified even when estimation is not justified |
| Exposure-timing causal gate | `med_start` and related variables are Dynamic / past-month features and cannot be aligned safely to the three-month interval start | Implemented v0.4; **causal estimate withheld** | Requires treatment and outcome timestamps plus pre-treatment confounding data before estimation |
| Bayesian hierarchical modelling | No real clinician/service hierarchy in PSYCHE-D | Planned | Add partial pooling only when a genuine provider/clinician hierarchy is available |
| Patient-level causal effect estimation | No effect estimate reported from timing-ambiguous treatment features | Correctly withheld | Use a dataset with well-defined treatment assignment time zero and confounding information |
| Reproducibility | Zenodo source, MD5 checks, official NHS download, CI, unit tests, real-data invariants, uploaded artifact | Implemented | v0.4 CI has 14 tests plus source and scientific-boundary checks |
| Clinical NLP | Not required for the current core scientific question | Optional only | Add only if a suitable clinical-text question and dataset materially improve the application |

## Real-data interview case

**Question:** You have repeated clinical outcome data and want to identify patients at risk of deterioration. What should happen before claiming clinical usefulness?

**Evidence-backed answer from this repository:**

1. define the outcome and clinically meaningful change rule from source-supported scores;
2. reconstruct repeated measures and check shared-time-point consistency;
3. freeze a prediction timestamp and exclude features collected after it;
4. split by patient so repeated records do not cross train/test;
5. move beyond a random hold-out to a forward-time test on different patients;
6. report calibration, Brier score and average precision as well as ROC-AUC;
7. quantify uncertainty with participant-level resampling rather than row-level resampling;
8. examine whether outcome availability changes over follow-up;
9. assess whether any phenotype or cluster survives reasonable specification changes;
10. use decision curves only as threshold-value analysis unless a real intervention and harm/benefit trade-off are defined;
11. define treatment, time zero and causal contrast before any causal model;
12. refuse causal estimation when exposure timing cannot be ordered safely before the outcome window.

## What v0.4 adds to the interview story

The strongest v0.4 evidence is not a higher score. The stricter forward-time test reduces AUC from 0.620 to 0.593, trajectory agreement falls as low as ARI 0.389 under reasonable specification changes, and the medication target-trial estimate is withheld because treatment timing is not established at time zero.

Those negative/limiting findings show the difference between running statistical methods and deciding whether the resulting evidence is strong enough for a clinical claim.

## Critical appraisal link to Paul Wallang's prior work

The DBT service evaluation by Webb, Girardi, Fox and Wallang used routinely collected clinical records with baseline, 6-month and 12-month outcomes and ANOVA/non-parametric comparisons. The published paper states that outcome data were not available for the whole sample and that improvements could not be attributed directly to DBT. Its patient-level data are confidential.

The useful interview position is not that the earlier service evaluation is incorrect. It is that a modern analysis of the same class of routine-care question can add explicit repeated-measures models, outcome-availability analysis, clinically meaningful individual change, prediction-time control, forward-time validation, calibration uncertainty, phenotype stability tests and a target-trial time-zero gate. This repository demonstrates those additions on open data without claiming access to private Clinical Partners or St Andrew's Healthcare records.

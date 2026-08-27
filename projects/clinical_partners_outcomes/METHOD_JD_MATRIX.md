# Method-to-role evidence matrix

This file separates implemented evidence from planned work. A method is marked implemented only when the repository contains runnable code and a real-data output for it. v0.4 records when an implemented method fails a robustness or causal-readiness gate; v0.5 adds a real NHS provider-level hierarchical Bayesian analysis and posterior predictive checks; v0.6 adds a real public item-level PHQ-9 psychometric analysis using NHANES 2021-2023.

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
| NHS service benchmarking | Official June 2025-June 2026 key-measures panel plus June 2026 Monthly Activity counts; 130 provider codes in the activity file | Implemented v0.3-v0.5 | Aggregate provider statistics support benchmarking and model demonstrations, not patient-level causal effects |
| Bayesian hierarchical modelling | June 2026 NHS provider reliable-improvement counts: 123 complete provider count pairs; Beta-Binomial hierarchy with posterior partial pooling | Implemented v0.5; **simple hierarchy fails one PPC gate** | Provider-population mean 68.35% (95% CrI 67.40%-69.10%); median absolute shrinkage 0.68 pp and p90 5.72 pp; useful partial-pooling demonstration but not an adequate final service model |
| Bayesian prior sensitivity | Primary versus broader hyperprior changes provider posterior means by median 0.010 pp and maximum 0.103 pp | Implemented v0.5 | Provider posterior means are not materially driven by the tested hyperprior choice |
| Bayesian posterior predictive checks | 2,000 replicated provider panels using the observed denominators; 95% population-predictive interval coverage 94.3% | Implemented v0.5; **model-adequacy gate FAIL** | Overall SD/IQR are plausible, but observed providers at or below 50% = 7 versus predictive 97.5% upper bound = 4; two-sided Bayesian p=0.000. Investigate case mix/provider type/time structure rather than tuning this aggregate model only to pass |
| Target-trial specification | Eligibility, strategies, time zero, follow-up, outcome, contrast and identification assumptions written for medication initiation | Implemented v0.4 | Protocol can be specified even when estimation is not justified |
| Exposure-timing causal gate | `med_start` and related variables are Dynamic / past-month features and cannot be aligned safely to the three-month interval start | Implemented v0.4; **causal estimate withheld** | Requires treatment and outcome timestamps plus pre-treatment confounding data before estimation |
| Patient-level causal effect estimation | No effect estimate reported from timing-ambiguous treatment features | Correctly withheld | Use a dataset with well-defined treatment assignment time zero and confounding information |
| Ordinal psychometric factor structure | NHANES 2021-2023 public PHQ-9 item data; 5,455 complete nine-item adults; survey-weighted polychoric matrix; first eigenvalue 5.699, first/second ratio 7.87, first-eigenvalue fraction 63.3%, one-factor off-diagonal residual RMS 0.066 | Implemented v0.6 | Strong dominant-factor signal in this public sample, but factor diagnostics do not by themselves establish target-population validity or strict unidimensionality |
| Item response theory | Four-category PHQ-9 graded-response model fitted by marginal maximum likelihood on 1,616 observed response patterns; all 9 discriminations positive and ordered thresholds enforced; fit converged in 53 iterations | Implemented v0.6 | Item discrimination ranges from 1.53 to 3.41; this is a public-population item model rather than a Clinical Partners instrument calibration |
| Measurement invariance / DIF | Anchored male-versus-female multi-group GRM allows latent mean/scale differences, then frees one item's discrimination and three thresholds at a time; BH-FDR 0.05 flags DPQ010, DPQ030, DPQ040, DPQ050, DPQ060 and DPQ090 | Implemented screening v0.6; **non-invariance signal** | Six of nine items are flagged under this screen. A flagged item is a possible DIF signal, not proof of bias; anchor sensitivity, item-content review, full survey-design inference and replication are required |
| Conditional measurement precision | GRM test information and conditional SEM reported over latent theta = -2,-1,0,1,2; SEM falls from 1.882 at theta=-2 to 0.271 at theta=2 | Implemented v0.6 | The public item set is much less informative at the very low-symptom end; do not treat total-score precision as constant across severity |
| Reliable-change psychometric readiness | Two-independent-measurement 95% latent-change threshold derived from conditional information: 1.10 at theta=0, 0.85 at theta=1 and 0.75 at theta=2 | Implemented readiness only | NHANES is cross-sectional, so no observed within-person reliable-change estimate is claimed. Repeated item administrations are required for longitudinal reliable change and time invariance |
| Pathway survival / competing risks | Current public sources used here do not provide Clinical Partners patient-level referral-to-assessment/treatment event times | Planned with explicit boundary | A production analysis would define time zero, censoring and competing exits before fitting Cox/flexible-parametric or cause-specific/subdistribution models |
| Reproducibility | Zenodo source, MD5 checks, official NHS downloads, official CDC NHANES XPT downloads, CI, unit tests, real-data invariants and uploaded evidence artifacts | Implemented | v0.6 adds 5/5 psychometric unit tests, XPORT-zero normalization, exact CDC item-frequency checks, GRM/DIF convergence checks and real-data evidence upload; scientific limitations remain separate from software CI |
| Clinical NLP | Not required for the current core scientific question | Optional only | Add only if a suitable clinical-text question and dataset materially improves the application |

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
12. refuse causal estimation when exposure timing cannot be ordered safely before the outcome window;
13. when comparing services with different denominators, model the count likelihood and use partial pooling rather than ranking raw percentages as if their precision were equal;
14. run posterior predictive checks and retain a model-adequacy failure when the assumed service distribution does not reproduce an important part of the observed data;
15. when the outcome instrument is ordinal, test the item-level measurement model rather than assuming a total score has equal precision everywhere;
16. test measurement invariance before treating group differences in a total or latent score as fully comparable.

## What v0.6 adds to the interview story

v0.6 turns the psychometrics part of the role into a real-data analysis. It uses the public NHANES August 2021-August 2023 PHQ-9 item responses rather than total scores or synthetic questionnaire data. A SAS XPORT reader issue initially decoded response code 0 as a tiny positive floating-point value; the workflow detected the resulting implausible 117-person complete-case cohort, restored the near-zero representation to exact zero, and now checks every item's published CDC zero and valid-response counts before accepting a run. The corrected complete nine-item cohort contains 5,455 adults.

The ordinal factor audit shows a dominant first dimension: weighted Cronbach alpha is 0.857, the first polychoric eigenvalue is 5.699, the first/second eigenvalue ratio is 7.87 and the first dimension accounts for 63.3% of the polychoric variance. The project does not convert those diagnostics into a claim of strict unidimensionality.

The next layer is a four-category graded-response model. It converges on 1,616 observed response patterns; discrimination parameters range from 1.53 to 3.41. Test information is strongly severity-dependent: conditional SEM is 1.882 at theta=-2, 0.398 at theta=0, 0.306 at theta=1 and 0.271 at theta=2. This makes the measurement point concrete: the same questionnaire does not estimate the latent construct with equal precision at every point on the severity scale.

The sex invariance screen gives a useful limiting result rather than a clean pass. A multi-group GRM allows the female latent mean and variance to differ from the male reference distribution, then frees one item's discrimination and three thresholds while the other eight items act as anchors. After BH-FDR correction, six items are flagged: DPQ010, DPQ030, DPQ040, DPQ050, DPQ060 and DPQ090. The repository labels these as possible DIF signals, not proof that the items are biased. The next scientific checks would be anchor purification/sensitivity, item-content review, full survey-design inference and replication in the target clinical population.

NHANES is cross-sectional in this release, so v0.6 does not claim observed longitudinal reliable change. It uses test information only to show a measurement-error readiness calculation: a two-independent-measurement 95% latent-score difference is about 1.10 at theta=0, 0.85 at theta=1 and 0.75 at theta=2. Repeated item administrations would be needed to estimate actual within-person reliable change and longitudinal invariance.

## What v0.5 adds to the interview story

v0.5 turns the JD phrase "partial pooling across services, clinicians and cohorts" into a real-data service-level example without claiming access to Clinical Partners data. The June 2026 NHS Monthly Activity file gives both the number finishing treatment and the number showing reliable improvement, so the analysis uses a Binomial likelihood rather than treating published percentages as equally precise observations.

For provider j,

`y_j ~ Binomial(n_j, theta_j)`

and

`theta_j ~ Beta(alpha, beta)`.

The population mean and concentration are estimated jointly from all providers. Small-denominator observations therefore receive stronger shrinkage and wider posterior intervals. In the real run, a 5/5 provider has a raw rate of 100% but a posterior mean of about 69.6%, while large samples remain much closer to their observed rates. The tested broader hyperprior changes provider posterior means by at most about 0.10 percentage points.

The next check changes the conclusion. In 2,000 posterior predictive provider panels, the model reproduces the broad spread reasonably but does not reproduce the lower tail: the observed data contain 7 providers at or below 50% reliable improvement, while the model's 97.5% predictive upper bound is 4. The model-adequacy gate therefore fails. The correct next step is to investigate service composition, case mix, time effects or a richer hierarchy, not to present the simple Beta-Binomial model as a final service model.

That negative result strengthens the interview story: the model demonstrates why partial pooling matters, while the PPC demonstrates why partial pooling alone is not enough.

## What v0.4 added to the interview story

The strongest v0.4 evidence is not a higher score. The stricter forward-time test reduces AUC from 0.620 to 0.593, trajectory agreement falls as low as ARI 0.389 under reasonable specification changes, and the medication target-trial estimate is withheld because treatment timing is not established at time zero.

Those limiting findings show the difference between running statistical methods and deciding whether the resulting evidence is strong enough for a clinical claim.

## Clinical Partners-specific public study design

`CLINICAL_PARTNERS_PUBLIC_RESEARCH_AGENDA.md` uses only current public Clinical Partners service information to define candidate studies for interview discussion: patient-clinician-service partial pooling, pathway survival/competing risks, psychometrics, service-capacity quasi-experimental design and clinical NLP. It explicitly separates public pathway facts from analyses that would require governed patient-level data.

## Critical appraisal link to Paul Wallang's prior work

The DBT service evaluation by Webb, Girardi, Fox and Wallang used routinely collected clinical records with baseline, 6-month and 12-month outcomes and ANOVA/non-parametric comparisons. The published paper states that outcome data were not available for the whole sample and that improvements could not be attributed directly to DBT. Its patient-level data are confidential.

The useful interview position is not that the earlier service evaluation is incorrect. It is that a modern analysis of the same class of routine-care question can add explicit repeated-measures models, outcome-availability analysis, clinically meaningful individual change, prediction-time control, forward-time validation, calibration uncertainty, phenotype stability tests, a target-trial time-zero gate, denominator-aware Bayesian partial pooling, posterior predictive model checks and item-level psychometric measurement checks. This repository demonstrates those additions on open data without claiming access to private Clinical Partners or St Andrew's Healthcare records.

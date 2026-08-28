# Method-to-role evidence matrix

Current evidence level: **v0.10**.

This matrix distinguishes four states:

- **Implemented** — runnable code plus a real-data result in this repository;
- **Implemented with limiting result** — the method runs, but robustness/model-adequacy checks prevent a stronger claim;
- **Designed only** — a defensible study design exists but the public data used here do not support estimation;
- **Not covered here** — no claim is made from this subproject.

The aim is not to maximise the number of methods marked green. A method is counted only when the available data support the scientific question.

| JD / scientific capability | Real-data evidence in current project | Status | Boundary / next evidence |
|---|---|---|---|
| Longitudinal real-world outcomes | PSYCHE-D 35,694 rows / 4,948 participants; 15,261 reconstructed participant-month PHQ-9 measurements | **Implemented** | Public observational release, not a service EHR |
| Mixed-effects modelling | Participant random-intercept PHQ-9 model across 4,036 participants | **Implemented descriptive** | Patient random slopes / nonlinear time are possible extensions; clinician/service hierarchy requires real IDs |
| Clinically meaningful change | PHQ-9 ±6-point reliable improvement/deterioration; caseness crossing kept separate | **Implemented** | Clinical importance and statistical reliability are not treated as identical |
| MCID sensitivity | 20% relative reduction retained only as sensitivity analysis | **Implemented with boundary** | No universal MCID claim |
| Prediction-time control | Strict t0 model excludes dynamic interval features whose timing can overlap outcome window | **Implemented** | Broad feature model retained only as leakage-risk reference |
| Participant-held-out prediction | AUC 0.620, AP 0.107, Brier 0.0621 | **Implemented** | Internal validation |
| Forward-time validation | Different participants; later endpoint months; AUC 0.593, AP 0.119, Brier 0.0632 | **Implemented with limiting result** | Performance weakens later; retained rather than tuned away |
| Calibration | Temporal intercept -0.693, slope 0.762 | **Implemented** | External calibration still needed for transportability |
| Prediction uncertainty | 300 participant-cluster bootstraps; AUC 95% CI 0.527-0.658 | **Implemented** | Sampling uncertainty, not external transport uncertainty |
| Decision-curve analysis | Thresholds 0.02-0.20 vs treat-all/treat-none | **Implemented exploratory** | No real intervention/harm threshold is claimed |
| Trajectory / latent phenotyping | Three-class GMM on repeated PHQ-9 summaries | **Implemented exploratory** | Model-based phenotype, not validated subtype |
| Trajectory robustness | ARI 0.389 / 0.567 / 0.668 under specification changes | **Implemented; strong stability gate FAIL** | Current three-class phenotype is not robust enough for clinical subtype claims |
| Bayesian hierarchical modelling | v0.5 Beta-Binomial provider hierarchy; v0.8 repeated provider×month logit hierarchy | **Implemented** | Public aggregate providers, not patient→clinician→service |
| Partial pooling across sparse services | v0.5 median absolute shrinkage 0.68pp; p90 5.72pp; v0.8 median provider-month shrinkage 1.61pp, p90 6.73pp | **Implemented** | Demonstrates denominator-aware service shrinkage |
| Bayesian prior sensitivity | v0.5 broader hyperprior max provider-mean change 0.103pp; v0.8 monthly means nearly unchanged | **Implemented** | Tested priors do not materially drive reported service means |
| Posterior predictive checks | v0.5 and v0.8/v0.8.1 provider-panel replications | **Implemented; model-adequacy failures retained** | Persistent provider effect reproduces broad Jan→Jun persistence but not extreme tails/dispersion |
| Dynamic service hierarchy | Jan-Jun 2026, 703 provider-month rows, 119 providers; `logit(p_jt)=mu_t+u_j` | **Implemented v0.8** | Provider persistence captured; tail lack of fit remains |
| Robust random-effect sensitivity | Normal vs variance-standardised Student-t df 10/5/3 | **Implemented v0.8.1** | Best t5 only reduces PPC failures 11/18→10/18; no candidate adequate; stop tail tuning |
| Patient→clinician→service hierarchy | No real clinician assignment in current public sources | **Designed only** | Do not synthesize clinician IDs; require governed patient-level service data |
| Ordinal psychometric factor structure | NHANES 5,455 complete PHQ-9 adults; weighted polychoric audit; first/second eigenvalue ratio 7.87 | **Implemented** | Dominant dimension does not prove strict unidimensionality or target-population validity |
| Item response theory | Four-category graded-response model; 1,616 response patterns; converged fit | **Implemented** | Public NHANES calibration, not Clinical Partners calibration |
| Conditional measurement precision | Test information / SEM by latent severity | **Implemented** | Precision is not constant across severity |
| Measurement invariance / DIF | Multi-group GRM with latent mean/scale differences | **Implemented** | DIF signal is not proof of item bias |
| Anchor purification | v0.7 converges in three rounds to DPQ030/040/050 | **Implemented v0.7** | Six final anchors; stable signals remain under sensitivity |
| Anchor-set sensitivity | Stable DIF items flagged 6/6 leave-one-anchor-out runs; other items 0/6 | **Implemented v0.7** | DPQ090 appears under equal weighting and is labelled weighting-sensitive |
| Reliable-change psychometric readiness | Conditional SEM translated to two-measurement latent-score thresholds | **Implemented readiness only** | NHANES is cross-sectional; no longitudinal item-level invariance claim |
| Survival / time-to-event | Time to first observed reliable PHQ-9 change on 3/6/9/12 month grid | **Implemented v0.9** | Discrete observation process, not exact event time |
| Competing risks | First reliable improvement vs first reliable deterioration, mutually exclusive first events; discrete cumulative incidence | **Implemented v0.9** | Primary analysis censors at first missing scheduled visit |
| Cause-specific hazard modelling | Complementary-log-log models with month-specific baseline hazards and participant-cluster robust SEs | **Implemented v0.9** | Prognostic/descriptive, not causal |
| Proportional/time-constant effect checking | Baseline severity × follow-up month diagnostic | **Implemented v0.9** | Deterioration interaction p=0.0156; pooled baseline-severity HR should not be treated as constant |
| Referral→assessment / treatment survival | No patient-level referral timestamps in current open datasets | **Designed only** | Requires MHSDS/Talking Therapies patient-level governed data / TRE-SDE access |
| Outcome availability / missingness diagnosis | PSYCHE-D month-12 PHQ-9 missing 49.7% in v0.9 baseline cohort | **Implemented** | Absence reason cannot be separated into non-response, attrition or release preprocessing |
| IPCW for censoring | Pooled logistic next-visit observation model; stabilised/truncated time-varying weights; weighted competing CIF | **Implemented v0.10** | Observation model AUC 0.617; weights mild; relies on observed-history censoring model |
| Multiple imputation under MAR | 20 stochastic chained-equation imputations with Bayesian regression; observed scores restored; Rubin pooling | **Implemented v0.10** | MAR is an assumption, not established by the release |
| MNAR sensitivity | Delta adjustment -3 to +6 PHQ-9 points only on originally missing follow-up values | **Implemented v0.10** | Point-estimate improvement/deterioration ordering reverses at +1; +2 yields CI for I-D entirely below 0; does not identify true MNAR mechanism |
| Tipping-point analysis | Month-12 improvement-minus-deterioration tracked over delta grid | **Implemented v0.10** | Controlled sensitivity statement, not estimate of real unobserved outcomes |
| Target-trial specification | Eligibility, strategies, time zero, follow-up, outcome and assumptions written for medication initiation | **Implemented design** | Estimation deliberately withheld when exposure cannot be ordered before outcome window |
| Propensity score matching / weighting | No patient-level treatment effect estimate from current timing-ambiguous PSYCHE-D treatment variables | **Not implemented here** | Use a dataset with defensible treatment assignment time zero and pre-treatment confounders |
| Difference-in-differences / ITS | Service-capacity use cases specified in Clinical Partners public research agenda | **Designed only** | Requires credible intervention date, comparator / pre-trend structure and outcome series |
| Instrumental variables | No credible public instrument identified | **Not covered here** | Do not create an IV example without a defensible instrument/exclusion restriction |
| Uplift / heterogeneous treatment effects | No treatment assignment suitable for an HTE claim in current core data | **Not covered here** | Prefer real randomised/quasi-randomised treatment data before adding HTE |
| Clinical NLP: NER / negation / temporality | Research pipeline specified, but no clinical-text dataset in this subproject | **Designed only here** | Add only with a real clinical-text question; do not duplicate weaker generic NLP for checkbox coverage |
| Explainability / SHAP | Current core deterioration model emphasises timing/calibration rather than SHAP | **Partial gap** | Can add feature-attribution/subgroup stability if it improves a decision-relevant prediction question |
| Fairness / subgroup performance | Baseline sex/race/insurance reviews; psychometric DIF by sex plus exploratory age/race screens | **Partially implemented** | Prediction subgroup calibration/uncertainty could be strengthened |
| SQL | Not central to this public-file subproject | **Not evidenced here** | Demonstrate elsewhere in application / governed-data workflow rather than fabricate SQL need |
| Reproducibility | Zenodo MD5, official NHS downloads, CDC XPT source-frequency gates, unit tests, CI, model invariants, evidence artifacts | **Implemented strongly** | Scientific failures are kept separate from software failures |

## Current strongest Clinical Data Scientist story

The repository now supports a coherent answer to a research-oriented mental-health JD:

1. **Measurement:** validate ordinal questionnaire structure, IRT precision and group comparability before treating a total score as interchangeable across severity/groups.
2. **Longitudinal outcomes:** define clinically meaningful repeated outcomes and separate description, prediction and causal questions.
3. **Prediction:** freeze time zero, separate participants, validate later in time, report calibration and uncertainty, and retain deterioration in performance.
4. **Service estimation:** use count likelihoods and partial pooling for sparse providers, then reject an apparently plausible hierarchy when PPCs miss clinically relevant tails.
5. **Survival:** treat improvement and deterioration as competing first events on the observed schedule rather than as unrelated binary endpoints.
6. **Missing follow-up:** show how IPCW, MAR MI and MNAR delta assumptions alter the competing-risk result instead of assuming censoring is harmless.
7. **Causal discipline:** specify target trials but refuse treatment-effect estimation when the data cannot establish time zero.

## Highest-value remaining gaps

### 1. Actual causal estimation on defensible assignment data

The current project demonstrates causal **discipline**, not a fitted patient-level treatment effect. The next useful addition should use real randomised or credible quasi-experimental mental-health/service data so that treatment assignment, time zero and pre-treatment variables are defensible. One well-designed causal study is higher value than separate PSM/IV/DiD checkbox demos.

### 2. Patient-clinician-service multilevel structure

Current public NHS files support provider-level partial pooling but not patient-to-clinician assignment. A real nested longitudinal hierarchy requires governed patient-level service data. Synthetic clinician identifiers should not be used to claim this capability.

### 3. Real referral-pathway event data

Clinical Partners-style referral→triage→assessment→treatment time requires patient-level operational timestamps. Public MHSDS/Talking Therapies catalogues show that these concepts exist, but patient-level records are normally accessed through governed NHS environments rather than direct download.

### 4. Prediction fairness / interpretability

If application evidence still needs strengthening after causal work, extend the existing strict t0 model with subgroup calibration/bootstrapped differences and feature-attribution stability rather than adding a disconnected explainability demo.

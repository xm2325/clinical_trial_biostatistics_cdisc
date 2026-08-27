# Clinical Outcomes & Longitudinal Methods Workbench

Current version: **v0.5**.

This subproject uses the public PSYCHE-D release plus official NHS Talking Therapies aggregate statistics to demonstrate clinical-data-science reasoning for research-oriented mental-health work: longitudinal outcomes, clinically meaningful change, prediction-time control, forward-time validation, calibration and uncertainty, trajectory analysis, service benchmarking, causal-readiness checks and denominator-aware Bayesian partial pooling.

The project is designed as public-data evidence for a Clinical Data Scientist application. It does **not** use Clinical Partners patient data and does **not** claim that any model here is currently used by Clinical Partners.

## Data and source boundaries

- PSYCHE-D dataset: Makhmutova et al., Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Published paper: Makhmutova M, Kainkaryam R, Ferreira M, Min J, Jaggi M, Clay I. *Predicting Changes in Depression Severity Using the PSYCHE-D (Prediction of Severity Change-Depression) Model Involving Person-Generated Health Data: Longitudinal Case-Control Observational Study.* JMIR mHealth and uHealth. 2022;10(3):e34148. DOI `10.2196/34148`.
- Original code: `evidation-opensource/PSYCHE-D`.
- Released dataset licence: CC BY-NC 4.0.
- NHS time-series service benchmark: NHS Talking Therapies Monthly Time Series for Key Measures, June 2025-June 2026, publication dated 13 August 2026.
- NHS count-level service benchmark for v0.5: NHS Talking Therapies June 2026 Monthly Activity Data File.

Raw source files are downloaded at run time and are not committed to this repository. The real-data PSYCHE-D run contains 35,694 rows and 4,948 participants; 10,866 three-month intervals from 4,036 participants have paired start/end PHQ-9 scores.

## v0.2: score-level longitudinal analysis

v0.2 reconstructs 15,261 unique participant-month PHQ-9 measurements from the interval representation and adds score-scale analysis rather than relying only on severity categories.

Real-data findings:

- 10,866 paired three-month intervals from 4,036 participants;
- PHQ-9 reliable improvement, defined here as a decrease of at least 6 points: 8.72%;
- PHQ-9 reliable deterioration, defined here as an increase of at least 6 points: 7.24%;
- among intervals beginning at PHQ-9 >=10, 30.13% cross below 10;
- 15.47% both improve by at least 6 points and end below 10;
- a 20% relative reduction occurs in 42.32% of baseline-case intervals and is retained only as an MCID sensitivity analysis;
- a participant-random-intercept mixed model converges, with a descriptive month coefficient of -0.055 PHQ-9 points per study month (95% CI -0.068 to -0.042).

The mixed model is descriptive and is not interpreted as a treatment effect.

### Outcome availability

v0.2 constructs the four expected quarterly PHQ assessment opportunities for every participant: 19,792 participant-quarter opportunities.

Availability in the released analytical file is:

- month 3: 65.6%;
- month 6: 57.2%;
- month 9: 55.2%;
- month 12: 41.6%.

A participant-held-out model of analytical-file endpoint availability has ROC-AUC 0.623. This shows structured availability, but absence from the released analytical file cannot be assigned specifically to questionnaire non-response because attrition and source preprocessing may also contribute.

## v0.3: strict prediction time, trajectory phenotyping and NHS benchmarking

### Strict t0 deterioration prediction

The v0.3 prediction endpoint is:

```text
PHQ-9 increase >= 6 points over the next three-month interval
```

The strict model uses only interval-start PHQ-9 plus baseline/screener variables frozen per participant. Dynamic medication, lifestyle and wearable summaries are excluded because their source timing can fall within the future interval.

Participant-held-out results:

| Metric | Strict t0 model | Broad interval reference |
|---|---:|---:|
| ROC-AUC | 0.620 | 0.628 |
| Average precision | 0.107 | -- |
| Brier score | 0.0621 | 0.0619 |
| Calibration intercept | -0.530 | -- |
| Calibration slope | 0.827 | -- |

The broad interval model improves AUC by only about 0.008 while accepting a weaker timing boundary. It is retained only as a leakage-risk reference.

### Exploratory trajectory phenotyping

Among 3,107 participants with at least three reconstructed PHQ-9 measurements, v0.3 compares Gaussian mixture models with 2-5 classes using baseline PHQ-9 and participant-specific linear slope. The selected solution has 3 classes, every class exceeds 5% of participants, and repeated initialisation gives mean ARI 0.819 and minimum ARI 0.688.

These are exploratory model-based phenotypes, not validated clinical subtypes. v0.4 below tests whether this solution survives specification changes.

### NHS Talking Therapies provider benchmark

The official June 2025-June 2026 key-measures file contains 182,512 long-format rows across 13 months, 5 aggregation levels and 11 measures. The provider panel contains 18,909 rows and 145 provider codes appearing in at least one month.

For June 2026, the provider distribution is:

| Measure | Providers observed | Provider median | England aggregate |
|---|---:|---:|---:|
| Access within 6 weeks | 123 | 90.0% | 85.2% |
| Access within 18 weeks | 123 | 100.0% | 97.7% |
| Reliable deterioration | 108 | 6.0% | 5.8% |
| Reliable improvement | 123 | 69.0% | 68.5% |
| Recovery | 120 | 51.0% | 50.6% |
| Reliable recovery | 120 | 49.0% | 48.1% |

Provider medians and England aggregates answer different questions and are not expected to be equal. Provider-level access/outcome correlations are labelled ecological associations only and are not patient-level causal effects.

## v0.4: forward-time validation, uncertainty, decision value and causal-readiness gates

### 1. Forward-time + participant-disjoint validation

v0.4 makes the evaluation harder in two ways at the same time.

Training uses held-in participants with interval endpoints at months 3 and 6, corresponding to prediction times 0 and 3 months. Testing uses different participants with interval endpoints at months 9 and 12, corresponding to prediction times 6 and 9 months.

Real-data result:

| Quantity | v0.4 result |
|---|---:|
| Train rows | 4,581 |
| Test rows | 1,183 |
| Train participants | 2,747 |
| Test participants | 748 |
| Participant overlap | 0 |
| Test deterioration prevalence | 6.85% |
| ROC-AUC | **0.593** |
| Average precision | **0.119** |
| Brier score | **0.0632** |
| Calibration intercept | **-0.693** |
| Calibration slope | **0.762** |

Performance is weaker than the v0.3 random participant hold-out AUC of 0.620. This is retained as evidence of limited temporal robustness rather than tuned away.

By endpoint month:

| Endpoint month | Prediction time | N | ROC-AUC | AP | Calibration slope |
|---|---:|---:|---:|---:|---:|
| 9 | 6 | 669 | 0.601 | 0.119 | 0.787 |
| 12 | 9 | 514 | 0.583 | 0.127 | 0.728 |

The month-12 discrimination is lower than month 9, which is consistent with possible temporal weakening, but these two internal windows are not enough to establish a general drift process.

### 2. Participant-cluster bootstrap uncertainty

The temporal hold-out is resampled by participant, not by interval row, for 300 bootstrap replicates.

| Metric | Point estimate | 95% cluster-bootstrap interval |
|---|---:|---:|
| ROC-AUC | 0.593 | 0.527-0.658 |
| Average precision | 0.119 | 0.080-0.186 |
| Brier | 0.0632 | 0.0520-0.0748 |
| Calibration intercept | -0.693 | -2.002 to 0.455 |
| Calibration slope | 0.762 | 0.283-1.243 |

The intervals show that discrimination is modest and calibration parameters are uncertain. The result is not presented as an externally validated clinical risk score.

### 3. Decision-curve analysis

Decision-curve net benefit is evaluated over risk thresholds 0.02-0.20 against treat-all and treat-none references. The model has higher point-estimate net benefit than both references at 18 of 19 tested thresholds.

This is intentionally not converted into a clinical recommendation. The analysis does not specify a real intervention, patient harm model or acceptable false-positive trade-off, and the current decision-curve output does not attach uncertainty intervals to net benefit. It is evidence about potential decision value under hypothetical thresholds only.

A fixed 0.5 threshold is inappropriate for this low-prevalence risk task and flags nobody in the temporal test set. The repository therefore reports probability quality and threshold curves instead of treating 0.5 classification accuracy as a useful clinical target.

### 4. Trajectory specification sensitivity

v0.4 directly tests whether the v0.3 three-class phenotype solution survives reasonable modelling changes.

| Sensitivity analysis | N | ARI vs v0.3 primary |
|---|---:|---:|
| Add residual SD to baseline + slope | 3,107 | **0.389** |
| Diagonal rather than full GMM covariance | 3,107 | **0.567** |
| Leave final PHQ-9 measurement out before estimating slope | 2,516 | **0.668** |

Mean ARI is 0.541 and minimum ARI is 0.389. Therefore the trajectory result does **not** pass a strong specification-stability test. The correct conclusion is that the three classes are useful exploratory summaries but are not stable enough to support a clinical-subtype claim.

### 5. Target-trial causal-readiness gate

v0.4 writes a target-trial specification for the question:

```text
What is the effect of starting a new medication at the beginning of a three-month interval
on PHQ-9 reliable deterioration over the following three months?
```

The requested causal estimate is deliberately **withheld**.

The released feature dictionary describes `med_start` as:

```text
Dynamic — Started a new medication, past month
```

The same timing problem applies to `med_stop`, `med_dose`, `nonmed_start`, `nonmed_stop`, `life_meditation` and `life_activity_eating`. The release does not establish that these values are measured before the three-month outcome interval begins. Treating them as time-zero exposures could reverse treatment and outcome timing and create immortal-time/reverse-timing bias.

The target-trial module therefore records the desired eligibility criteria, strategies, time zero, follow-up, outcome, causal contrast and identification assumptions, then fails the exposure-timing gate rather than reporting a causal estimate.

A real emulation would require treatment start timestamps, PHQ-9 measurement timestamps, pre-treatment confounders, indication information, censoring/follow-up data and a prespecified rule for treatment changes after time zero.

## v0.5: hierarchical Bayesian partial pooling for sparse service outcomes

v0.5 adds a service-level Bayesian model using the official NHS Talking Therapies June 2026 Monthly Activity Data File. This file is used because it contains count numerators and denominators rather than only percentages.

The real source audit finds:

- 290,472 rows and 228 measure names;
- 130 provider codes;
- 123 providers with complete `Count_FinishedCourseTreatment` and `Count_ReliableImprovement` pairs usable in the model;
- 7 provider rows excluded because the count pair is suppressed or missing;
- England `39,769 / 58,029 = 68.53%`, consistent with the published rounded reliable-improvement percentage of 68.5%.

### Model

For provider j:

```text
y_j ~ Binomial(n_j, theta_j)
theta_j ~ Beta(alpha, beta)
alpha = m * kappa
beta  = (1 - m) * kappa
```

The hyperparameters `m` and `kappa` are estimated jointly from the provider count pairs on a numerical posterior grid. The primary prior is specified on `logit(m)` and `log(kappa)`, and a broader prior is run as a sensitivity analysis.

Primary posterior result:

| Quantity | Result |
|---|---:|
| Provider-population mean `m` | **68.35%** |
| 95% credible interval for `m` | **67.40%-69.10%** |
| Posterior mean `kappa` | **127.7** |
| 95% credible interval for `kappa` | **86.0-183.7** |
| Median absolute provider shrinkage | **0.68 percentage points** |
| 90th percentile absolute shrinkage | **5.72 percentage points** |
| Maximum posterior-mean change under broader prior | **0.103 percentage points** |
| Median posterior-mean change under broader prior | **0.010 percentage points** |

The denominator effect is visible in the real data. A provider with `5/5` reliable improvements has a raw rate of 100%, but its posterior mean is about 69.6% with a much wider posterior interval. A provider with `10/10` is similarly pulled toward the provider population. The model therefore does not treat a 100% rate based on 5 people as equally precise to a rate based on hundreds or thousands of people.

This is the service-level analogue of the Clinical Partners JD requirement for partial pooling across services, clinicians and cohorts. It is **not** a provider quality ranking and it is **not** a Clinical Partners model. The public NHS aggregate data do not contain patient-level case mix, clinician hierarchy, treatment assignment or repeated item-level outcomes. A production implementation would extend the hierarchy to patients, clinicians and services, with prespecified case-mix adjustment and clinically reviewed endpoints.

### Prior sensitivity

The broader hyperprior changes provider posterior means by at most 0.103 percentage points and by a median of 0.010 percentage points. The main provider posterior means are therefore not materially driven by the two tested hyperprior specifications. Prior sensitivity does not establish model adequacy.

### Posterior predictive model-adequacy gate

v0.5 next generates 2,000 replicated provider panels from the fitted hierarchy while preserving every observed provider denominator. The aim is to test whether the simple exchangeable Beta population can reproduce features of the real provider distribution.

| Discrepancy | Observed | Predictive mean | 95% predictive interval | Two-sided Bayesian p |
|---|---:|---:|---:|---:|
| Provider rate SD | 0.0762 | 0.0623 | 0.0505-0.0782 | 0.070 |
| Provider rate IQR | 0.0574 | 0.0697 | 0.0534-0.0881 | 0.153 |
| Providers <=50% | **7** | **1.36** | **0-4** | **0.000** |
| Providers >=85% | 2 | 1.24 | 0-4 | 0.717 |
| Maximum absolute deviation from provider median | 0.3077 | 0.2721 | 0.1510-0.4870 | 0.574 |

The 95% provider population-predictive interval coverage is 94.3%, but the lower-tail check fails strongly: the observed data contain 7 providers at or below 50% reliable improvement, while the replicated 97.5% upper bound is 4.

**Model-adequacy gate: FAIL.**

This is treated as a scientific result, not a software failure. The simple Beta-Binomial hierarchy is useful for demonstrating denominator-aware partial pooling, but it is not an adequate final service model. The next analysis should investigate provider/service composition, patient case mix, time effects, suppression and a richer hierarchy. The model is not made more complex merely to force the PPC to pass on aggregate data.

## What v0.5 changes scientifically

The project now separates six questions that are often mixed together:

1. **Description:** how PHQ-9 changes over observed follow-up.
2. **Prediction:** who has higher probability of reliable deterioration at a defined prediction time.
3. **Validation:** whether that probability model survives a later study-time window and different participants.
4. **Phenotyping:** whether repeated outcome patterns support stable exploratory groups.
5. **Causal inference:** whether treatment timing and confounding data are sufficient to define and estimate a target-trial contrast.
6. **Service estimation:** whether service-level outcome rates should be pooled according to their count information and uncertainty rather than compared as equally precise percentages.

The useful results include limitations rather than higher headline scores: forward-time AUC falls to 0.593, calibration is uncertain, trajectory classes are sensitive to modelling choices, the medication causal estimate is withheld, and the first Bayesian service hierarchy fails a lower-tail posterior predictive check.

## Clinical Partners-specific public research agenda

`CLINICAL_PARTNERS_PUBLIC_RESEARCH_AGENDA.md` maps current public Clinical Partners pathway information to candidate studies without claiming access to private data. It covers:

- patient-clinician-service hierarchical outcome models;
- referral-to-assessment/treatment survival and multi-state analysis;
- psychometric and IRT questions around instruments publicly listed in the pathways;
- quasi-experimental evaluation of service-capacity changes, with explicit causal assumptions;
- clinical NLP with negation, temporality and clinician review;
- a proposed first-90-day scientific sequence.

## Reproducibility and CI

GitHub Actions downloads the real PSYCHE-D files and official NHS data, verifies the published PSYCHE-D MD5 hashes, runs unit tests, executes the longitudinal/prediction/validation analyses, checks participant separation and source-scale invariants, verifies that the target-trial timing gate withholds the unsupported causal estimate, and uploads real-data evidence packages.

v0.5 adds a dedicated Bayesian CI workflow that:

1. downloads the official June 2026 Monthly Activity Data File;
2. audits the real schema and required outcome count measures;
3. runs **4/4 v0.5 unit tests**;
4. reproduces the England count ratio before modelling;
5. fits the hierarchical Beta-Binomial model;
6. runs the broader-prior sensitivity analysis;
7. runs 2,000 posterior predictive provider panels and records the model-adequacy gate; and
8. uploads the model and diagnostic evidence.

The software workflow passes when the code and data checks execute correctly even when a scientific gate fails. This keeps computational correctness separate from evidence strength.

Key v0.5 outputs include:

```text
v05_nhs_activity_schema_summary.json
v05_nhs_activity_measure_names.csv
v05_nhs_activity_target_row_sample.csv
v05_provider_partial_pooling.csv
v05_prior_sensitivity.csv
v05_bayesian_partial_pooling_summary.json
V05_BAYESIAN_PARTIAL_POOLING_REPORT.md
v05_posterior_predictive_discrepancies.csv
v05_provider_population_predictive_intervals.csv
v05_posterior_predictive_summary.json
V05_POSTERIOR_PREDICTIVE_CHECKS.md
```

## Interview use

A concise evidence-based explanation of v0.1-v0.4 is:

> I treated the project as a sequence of clinical research questions rather than one prediction benchmark. I reconstructed repeated PHQ-9 outcomes, separated reliable score change from caseness crossing, froze predictors at a defined time zero, and then moved from random participant hold-out to a forward-time participant-disjoint test. The stricter test reduced AUC from about 0.62 to 0.59, so I reported the temporal weakness and participant-bootstrap uncertainty instead of tuning it away. I also stress-tested the trajectory clusters and found that they were not stable enough for a clinical-subtype claim. Finally, I wrote a target-trial specification for medication initiation but refused to estimate the effect because the released medication-change variable is only labelled as occurring in the past month and cannot be aligned safely to time zero.

A concise explanation of the Bayesian component is:

> I used the NHS count-level activity file to study unequal service denominators. A Beta-Binomial hierarchy gives small services stronger partial pooling and wider uncertainty than large services; the provider-population posterior mean was about 68.35% and the tested prior sensitivity was small. I then ran posterior predictive checks rather than stopping at a plausible posterior. The simple hierarchy under-predicted the lower tail: seven observed providers were at or below 50% reliable improvement, while the 97.5% replicated upper bound was four. I therefore marked the model-adequacy gate as failed. For a production Clinical Partners model, I would next investigate case mix, service type, time and a genuine patient-clinician-service hierarchy rather than presenting one exchangeable provider distribution as final.

## Next evidence after v0.5

The next additions should remain data-driven rather than adding methods for keyword coverage. The highest-value extensions are:

- patient-level service/clinician hierarchical longitudinal modelling when a genuine hierarchy is available;
- item-level psychometric modelling, measurement invariance or IRT only with a suitable public item-level mental-health dataset;
- referral-to-assessment/treatment survival and competing-risk analysis only with valid event timestamps;
- external temporal validation on another patient-level mental-health dataset;
- causal estimation only when treatment assignment time zero and pre-treatment confounding data are defensible;
- for the NHS service model, investigate whether provider type, case mix or temporal structure explains the lower-tail PPC failure before considering a richer random-effect distribution.

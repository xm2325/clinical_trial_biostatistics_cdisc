# Clinical Outcomes & Longitudinal Methods Workbench

Current version: **v0.6**.

This subproject uses public PSYCHE-D data, official NHS Talking Therapies statistics and public CDC/NCHS NHANES PHQ-9 item responses to demonstrate clinical-data-science reasoning for research-oriented mental-health work. The current evidence chain covers longitudinal outcomes, clinically meaningful change, prediction-time control, forward-time validation, calibration and uncertainty, trajectory analysis, service benchmarking, causal-readiness checks, denominator-aware Bayesian partial pooling, posterior predictive model checks, ordinal psychometrics, graded-response IRT and DIF screening.

The project is public-data evidence for a Clinical Data Scientist application. It does **not** use Clinical Partners patient data and does **not** claim that any model here is currently used by Clinical Partners.

## Data and source boundaries

- PSYCHE-D dataset: Makhmutova et al., Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Published PSYCHE-D paper: Makhmutova M, Kainkaryam R, Ferreira M, Min J, Jaggi M, Clay I. *Predicting Changes in Depression Severity Using the PSYCHE-D (Prediction of Severity Change-Depression) Model Involving Person-Generated Health Data: Longitudinal Case-Control Observational Study.* JMIR mHealth and uHealth. 2022;10(3):e34148. DOI `10.2196/34148`.
- Original PSYCHE-D code: `evidation-opensource/PSYCHE-D`.
- Released PSYCHE-D dataset licence: CC BY-NC 4.0.
- NHS time-series service benchmark: NHS Talking Therapies Monthly Time Series for Key Measures, June 2025-June 2026, publication dated 13 August 2026.
- NHS count-level service benchmark for v0.5: NHS Talking Therapies June 2026 Monthly Activity Data File.
- Item-level psychometric source for v0.6: CDC/NCHS NHANES August 2021-August 2023 `DPQ_L` Depression Screener and `DEMO_L` demographics/sample-weight files.

Raw source files are downloaded at run time and are not committed to this repository.

The PSYCHE-D real-data run contains 35,694 rows and 4,948 participants; 10,866 three-month intervals from 4,036 participants have paired start/end PHQ-9 scores. The corrected NHANES v0.6 item-level analysis contains 5,455 adults with all nine PHQ-9 symptom items observed.

## v0.2: score-level longitudinal analysis

v0.2 reconstructs 15,261 unique participant-month PHQ-9 measurements from the PSYCHE-D interval representation and adds score-scale analysis rather than relying only on severity categories.

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

| Scheduled month | Endpoint available |
|---:|---:|
| 3 | 65.6% |
| 6 | 57.2% |
| 9 | 55.2% |
| 12 | 41.6% |

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

For June 2026:

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

### Forward-time + participant-disjoint validation

Training uses held-in participants with interval endpoints at months 3 and 6, corresponding to prediction times 0 and 3 months. Testing uses different participants with interval endpoints at months 9 and 12, corresponding to prediction times 6 and 9 months.

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

The month-12 discrimination is lower than month 9, but two internal windows are not enough to establish a general drift process.

### Participant-cluster bootstrap uncertainty

The temporal hold-out is resampled by participant, not by interval row, for 300 bootstrap replicates.

| Metric | Point estimate | 95% cluster-bootstrap interval |
|---|---:|---:|
| ROC-AUC | 0.593 | 0.527-0.658 |
| Average precision | 0.119 | 0.080-0.186 |
| Brier | 0.0632 | 0.0520-0.0748 |
| Calibration intercept | -0.693 | -2.002 to 0.455 |
| Calibration slope | 0.762 | 0.283-1.243 |

The intervals show that discrimination is modest and calibration parameters are uncertain. The result is not presented as an externally validated clinical risk score.

### Decision-curve analysis

Decision-curve net benefit is evaluated over risk thresholds 0.02-0.20 against treat-all and treat-none references. The model has higher point-estimate net benefit than both references at 18 of 19 tested thresholds.

This is not converted into a clinical recommendation. The analysis does not specify a real intervention, patient harm model or acceptable false-positive trade-off, and the current decision-curve output does not attach uncertainty intervals to net benefit.

### Trajectory specification sensitivity

| Sensitivity analysis | N | ARI vs v0.3 primary |
|---|---:|---:|
| Add residual SD to baseline + slope | 3,107 | **0.389** |
| Diagonal rather than full GMM covariance | 3,107 | **0.567** |
| Leave final PHQ-9 measurement out before estimating slope | 2,516 | **0.668** |

Mean ARI is 0.541 and minimum ARI is 0.389. The three classes therefore remain exploratory summaries and are not stable enough for a clinical-subtype claim.

### Target-trial causal-readiness gate

v0.4 writes a target-trial specification for:

```text
What is the effect of starting a new medication at the beginning of a three-month interval
on PHQ-9 reliable deterioration over the following three months?
```

The requested causal estimate is deliberately **withheld**. The released feature dictionary describes `med_start` as `Dynamic — Started a new medication, past month`, so the release does not establish that exposure occurs before the three-month outcome interval begins. The same issue applies to related medication/non-medication change variables.

A real emulation would require treatment start timestamps, PHQ-9 measurement timestamps, pre-treatment confounders, indication information, censoring/follow-up data and a prespecified rule for treatment changes after time zero.

## v0.5: hierarchical Bayesian partial pooling for sparse service outcomes

v0.5 uses the official NHS Talking Therapies June 2026 Monthly Activity Data File because it contains count numerators and denominators rather than only percentages.

The source audit finds:

- 290,472 rows and 228 measure names;
- 130 provider codes;
- 123 providers with complete `Count_FinishedCourseTreatment` and `Count_ReliableImprovement` pairs;
- 7 provider rows excluded because the count pair is suppressed or missing;
- England `39,769 / 58,029 = 68.53%`, consistent with the published rounded reliable-improvement percentage of 68.5%.

### Beta-Binomial hierarchy

For provider j:

```text
y_j ~ Binomial(n_j, theta_j)
theta_j ~ Beta(alpha, beta)
alpha = m * kappa
beta  = (1 - m) * kappa
```

The hyperparameters `m` and `kappa` are estimated jointly from provider count pairs on a numerical posterior grid. A broader hyperprior is run as a sensitivity analysis.

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

A provider with `5/5` reliable improvements has a raw rate of 100%, but its posterior mean is about 69.6% with much wider uncertainty. The model therefore does not treat 100% based on five people as equally precise to a rate based on hundreds or thousands of people.

This is a service-level demonstration of denominator-aware partial pooling. It is not a provider quality ranking and it is not a Clinical Partners model.

### Posterior predictive model-adequacy gate

v0.5 generates 2,000 replicated provider panels while preserving every observed denominator.

| Discrepancy | Observed | Predictive mean | 95% predictive interval | Two-sided Bayesian p |
|---|---:|---:|---:|---:|
| Provider rate SD | 0.0762 | 0.0623 | 0.0505-0.0782 | 0.070 |
| Provider rate IQR | 0.0574 | 0.0697 | 0.0534-0.0881 | 0.153 |
| Providers <=50% | **7** | **1.36** | **0-4** | **0.000** |
| Providers >=85% | 2 | 1.24 | 0-4 | 0.717 |
| Maximum absolute deviation from provider median | 0.3077 | 0.2721 | 0.1510-0.4870 | 0.574 |

The 95% provider population-predictive interval coverage is 94.3%, but the lower-tail check fails strongly: seven observed providers are at or below 50% reliable improvement while the replicated 97.5% upper bound is four.

**Model-adequacy gate: FAIL.**

This is a scientific result, not a software failure. The simple hierarchy demonstrates partial pooling but is not accepted as a final service model. A next model would test whether service composition, patient case mix, time effects or a richer hierarchy explain the lower tail.

## v0.6: real item-level PHQ-9 psychometrics

v0.6 addresses a different question: before comparing questionnaire scores across patients or groups, what does the item-level measurement model look like, where is the scale informative, and is item functioning stable across groups?

The analysis uses the public NHANES August 2021-August 2023 `DPQ_L` PHQ-9 item file joined to `DEMO_L` by `SEQN`. `DPQ010`-`DPQ090` are treated as the nine ordinal symptom items, each with response categories 0-3. `DPQ100` is functional impairment and is not treated as a tenth PHQ-9 symptom item. The MEC examination weight `WTMEC2YR` is normalised to mean one for weighted pseudo-likelihood estimation.

### Source-format validation: a real data-pipeline failure that is now gated

The first v0.6 run exposed a source-reading problem. For this XPT file, `pandas.read_sas(..., format="xport")` represented SAS numeric zero as the tiny positive floating-point value `5.397605346934028e-79`. A naive `.isin([0,1,2,3])` check therefore removed most `0 = Not at all` responses and produced an impossible complete-case sample of only 117 people.

The fix does **not** lower the sample-size gate. The loader now restores values with absolute magnitude below `1e-12` to exact zero before validating PHQ-9 response codes. CI then checks the source frequencies against the published CDC counts. For example:

| Item | Published/validated zero count | Valid 0-3 count |
|---|---:|---:|
| DPQ010 | 3,703 | 5,498 |
| DPQ020 | 3,674 | 5,508 |
| DPQ030 | 2,772 | 5,509 |
| DPQ040 | 2,348 | 5,506 |
| DPQ050 | 3,710 | 5,510 |
| DPQ060 | 3,971 | 5,505 |
| DPQ070 | 4,036 | 5,505 |
| DPQ080 | 4,748 | 5,496 |
| DPQ090 | 5,207 | 5,501 |

After correction, the complete nine-item cohort is **5,455 adults**: 2,968 female and 2,487 male, age 18-80.

### Ordinal factor audit

The nine ordinal items are analysed with a survey-weighted polychoric correlation matrix rather than a Pearson correlation matrix on treated-as-continuous item scores.

| Quantity | v0.6 result |
|---|---:|
| Weighted Cronbach alpha | **0.857** |
| First polychoric eigenvalue | **5.699** |
| Second eigenvalue | **0.724** |
| First / second eigenvalue ratio | **7.87** |
| First-eigenvalue variance fraction | **63.3%** |
| One-factor off-diagonal residual RMS | **0.066** |

One-factor loading estimates range from 0.711 to 0.884. These diagnostics show a strong dominant first dimension in this public sample, but the project does not convert that into a claim of strict unidimensionality or target-population validity.

### Four-category graded-response model

v0.6 fits a graded-response model (GRM) by marginal maximum likelihood with 15-point Gaussian-Hermite quadrature. Each item has one positive discrimination parameter and three ordered thresholds. Observed response vectors are collapsed to unique response patterns before likelihood evaluation.

The real-data fit uses **1,616 unique response patterns** and converges in **53 iterations**.

| Item | Discrimination `a` |
|---|---:|
| DPQ010 | 2.652 |
| DPQ020 | **3.410** |
| DPQ030 | **1.525** |
| DPQ040 | 2.024 |
| DPQ050 | 1.707 |
| DPQ060 | 2.586 |
| DPQ070 | 1.863 |
| DPQ080 | 1.648 |
| DPQ090 | 2.494 |

The strongest discrimination in this fit is DPQ020 and the weakest is DPQ030. The complete item threshold table is written to `v06_grm_item_parameters.csv`.

These are population/sample-specific item parameters. They are not presented as a Clinical Partners calibration.

### Test information and conditional measurement error

The GRM makes questionnaire precision conditional on latent severity rather than assuming one constant reliability value.

| Latent `theta` | Test information | Conditional SEM | Two-independent-measurement 95% change threshold |
|---:|---:|---:|---:|
| -2 | 0.282 | 1.882 | 5.216 |
| -1 | 1.504 | 0.815 | 2.260 |
| 0 | 6.323 | 0.398 | 1.102 |
| 1 | 10.670 | 0.306 | 0.849 |
| 2 | 13.610 | 0.271 | 0.751 |

The scale is much less informative at the very low-symptom end than around moderate/high latent severity. This matters for clinical interpretation: a single global alpha does not imply equal measurement precision across severity.

The last column is a **measurement-error readiness calculation**, not an observed reliable-change result. It is `1.96 * sqrt(2) * SEM(theta)` under a two-independent-measurement approximation.

NHANES is cross-sectional in this release. v0.6 therefore does **not** claim observed within-person reliable change or longitudinal measurement invariance. Repeated item-level administrations are required for those questions.

### Sex DIF / measurement-invariance screen

The v0.6 screening model uses male participants as the reference group and female participants as the comparison group. The shared-item baseline allows the comparison latent mean and latent standard deviation to differ, so an overall difference in latent symptom level is not automatically labelled item DIF.

The baseline fit estimates:

```text
female latent mean relative to male reference = 0.291
female latent SD relative to male reference   = 0.922
```

For each item, one alternative model frees its discrimination and three thresholds in the female group while the other eight items remain anchors. A likelihood-ratio statistic with 4 degrees of freedom is then corrected across nine item tests using Benjamini-Hochberg FDR.

| Item | LRT chi-square (df=4) | BH q | FDR 0.05 flag |
|---|---:|---:|---|
| DPQ010 | 29.42 | 0.000019 | **yes** |
| DPQ020 | 9.78 | 0.0569 | no |
| DPQ030 | 48.75 | 2.96e-9 | **yes** |
| DPQ040 | 54.72 | 3.35e-10 | **yes** |
| DPQ050 | 24.40 | 0.000149 | **yes** |
| DPQ060 | 12.38 | 0.0221 | **yes** |
| DPQ070 | 7.59 | 0.1077 | no |
| DPQ080 | 8.95 | 0.0702 | no |
| DPQ090 | 16.71 | 0.00396 | **yes** |

Thus the first anchored screen flags **6/9 items: DPQ010, DPQ030, DPQ040, DPQ050, DPQ060 and DPQ090**.

This is deliberately labelled a **non-invariance signal**, not proof that six items are biased. When several items are flagged, the assumption that the other eight items form a stable anchor set becomes questionable. The next psychometric checks would include anchor purification/sensitivity, item-content review, full NHANES survey-design inference, replication in another sample and, for a target service, invariance across clinically relevant groups, service settings, assessment modes and time.

## What v0.6 changes scientifically

The project now separates seven questions that are often mixed together:

1. **Description:** how PHQ-9 changes over observed follow-up.
2. **Prediction:** who has higher probability of reliable deterioration at a defined prediction time.
3. **Validation:** whether that probability model survives a later study-time window and different participants.
4. **Phenotyping:** whether repeated outcome patterns support stable exploratory groups.
5. **Causal inference:** whether treatment timing and confounding data are sufficient to define and estimate a target-trial contrast.
6. **Service estimation:** whether service-level outcome rates should be pooled according to count information and uncertainty rather than compared as equally precise percentages.
7. **Measurement:** whether an ordinal questionnaire behaves like a coherent latent measure, where it is precise, and whether item functioning is comparable across groups.

The strongest project evidence is not a collection of high scores. Forward-time AUC falls to 0.593; calibration is uncertain; trajectory classes are specification-sensitive; the medication causal estimate is withheld; the first Bayesian service hierarchy fails a lower-tail posterior predictive check; and the first item-level sex invariance screen flags six of nine PHQ-9 items for follow-up.

## Clinical Partners-specific public research agenda

`CLINICAL_PARTNERS_PUBLIC_RESEARCH_AGENDA.md` maps current public Clinical Partners pathway information to candidate studies without claiming access to private data. It covers:

- patient-clinician-service hierarchical outcome models;
- referral-to-assessment/treatment survival and multi-state analysis;
- psychometric and IRT questions around instruments publicly listed in the pathways;
- quasi-experimental evaluation of service-capacity changes, with explicit causal assumptions;
- clinical NLP with negation, temporality and clinician review;
- a proposed first-90-day scientific sequence.

The v0.6 NHANES analysis is a public-data implementation of the psychometric methods, not validation of Clinical Partners' own patient instruments.

## Reproducibility and CI

GitHub Actions downloads real source files rather than relying on committed result tables.

The PSYCHE-D/NHS workflows verify source/schema properties, run unit tests, execute longitudinal/prediction/validation analyses, check participant separation and source-scale invariants, verify that the target-trial timing gate withholds the unsupported causal estimate, run the Bayesian service analysis and upload real-data evidence packages.

The dedicated v0.6 workflow:

1. downloads official CDC/NCHS `DPQ_L.xpt` and `DEMO_L.xpt`;
2. runs **5/5 v0.6 unit tests**, including a regression test for the SAS-XPORT near-zero representation;
3. restores the XPORT near-zero representation to response code 0 before PHQ-9 validation;
4. checks all nine CDC zero counts and valid 0-3 counts exactly;
5. requires more than 5,000 complete nine-item observations;
6. fits the weighted polychoric factor audit and marginal-likelihood GRM;
7. checks positive discriminations and ordered thresholds;
8. fits the shared-item and nine item-freed multi-group GRM models and checks optimiser success;
9. computes test information, conditional SEM and measurement-error thresholds;
10. uploads the real-data psychometric evidence package.

The source-reading incident is intentionally retained in the project history because it illustrates why apparently simple questionnaire coding must be checked against the source specification before clinical modelling.

Key v0.6 outputs are:

```text
v06_phq9_polychoric.csv
v06_one_factor_loadings.csv
v06_grm_item_parameters.csv
v06_test_information_reliable_change_readiness.csv
v06_sex_dif_anchor_lrt.csv
v06_psychometrics_summary.json
V06_PSYCHOMETRICS_REPORT.md
```

## Interview use

A concise explanation of the longitudinal/validation component is:

> I treated the project as a sequence of clinical research questions rather than one prediction benchmark. I reconstructed repeated PHQ-9 outcomes, separated reliable score change from caseness crossing, froze predictors at a defined time zero, and moved from random participant hold-out to a forward-time participant-disjoint test. The stricter test reduced AUC from about 0.62 to 0.59, so I reported the temporal weakness and participant-bootstrap uncertainty rather than tuning it away. I also stress-tested trajectory clusters and found that they were not stable enough for a clinical-subtype claim. Finally, I wrote a target-trial specification for medication initiation but withheld the effect estimate because the public treatment-change variable cannot be aligned safely to time zero.

A concise explanation of the Bayesian component is:

> I used the NHS count-level activity file to study unequal service denominators. A Beta-Binomial hierarchy gives small services stronger partial pooling and wider uncertainty than large services. I then ran posterior predictive checks rather than stopping at a plausible posterior. The simple hierarchy under-predicted the lower tail, so I marked model adequacy as failed and would next test case mix, service type and time structure rather than present one exchangeable provider distribution as final.

A concise explanation of the v0.6 psychometric component is:

> I added a separate measurement layer using real NHANES PHQ-9 item responses. First, the source audit caught a SAS-XPORT parsing issue that had converted code zero into a tiny floating-point value; I fixed it by tying the loader to the published item frequencies rather than lowering a sample-size check. On 5,455 complete adults, the polychoric structure has a dominant first dimension and a four-category graded-response model converges. I then used the model's test information to show that measurement precision changes strongly across severity. Finally, I ran an anchored male-versus-female multi-group GRM screen. Six of nine items were flagged after FDR correction, so I would not claim measurement invariance. I would next run anchor-sensitivity and survey-design-aware analyses and then replicate in the target clinical population.

## Next evidence after v0.6

Further work should remain driven by data that can support the scientific question. High-value additions are:

- anchor purification and sensitivity for the v0.6 DIF result, plus full NHANES survey-design uncertainty;
- replication of PHQ-9 item parameters and DIF in an independent public sample;
- longitudinal item-level data for observed reliable change and time invariance;
- patient-level service/clinician hierarchical longitudinal modelling when a genuine hierarchy is available;
- referral-to-assessment/treatment survival and competing-risk analysis only with valid event timestamps;
- external temporal validation on another patient-level mental-health dataset;
- causal estimation only when treatment assignment time zero and pre-treatment confounding data are defensible;
- for the NHS service model, test whether provider type, case mix or temporal structure explains the lower-tail PPC failure before selecting a richer random-effect distribution.

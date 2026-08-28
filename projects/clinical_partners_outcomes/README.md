# Clinical Outcomes & Longitudinal Methods Workbench

Current version: **v0.10**.

This subproject is a public-data clinical-data-science portfolio built around research questions that are relevant to a mental-health service organisation. It uses real public data from PSYCHE-D, NHS Talking Therapies and CDC/NCHS NHANES. It does **not** use Clinical Partners patient data and does not claim that any model here is used by Clinical Partners.

The project is deliberately organised as a scientific evidence chain rather than a collection of isolated modelling demos:

1. define clinically meaningful longitudinal outcomes;
2. control prediction time and validate later in study time;
3. test whether trajectory phenotypes survive specification changes;
4. refuse causal estimation when treatment time zero is not defensible;
5. use hierarchical partial pooling for sparse service outcomes and criticise the model with posterior predictive checks;
6. model questionnaire measurement at item level with ordinal factor methods, graded-response IRT and DIF analysis;
7. purify and stress-test DIF anchors rather than treating a first screen as final;
8. model time to first clinically meaningful change as competing first events;
9. challenge censoring assumptions with IPCW, MAR multiple imputation and controlled MNAR sensitivity.

## Data and source boundaries

### PSYCHE-D

- Public longitudinal depression dataset from Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Released file licence: CC BY-NC 4.0.
- Source file is downloaded during CI and checked against MD5 `a6b21ffbb5fba0600ed494c6ab299cc4`.
- 35,694 source rows and 4,948 participants.
- Used for repeated PHQ-9 outcomes, prediction, temporal validation, trajectory analysis, survival/competing first events and missing-data sensitivity.

### NHS Talking Therapies

- Official NHS England public monthly statistics and Monthly Activity Data Files.
- Used only at aggregate provider level.
- v0.5 uses June 2026 provider counts.
- v0.8-v0.8.1 use six monthly activity files from January-June 2026.
- Public aggregate data do not expose patient-to-clinician assignment, patient-level case mix or referral-to-assessment event histories.

### NHANES PHQ-9 item data

- CDC/NCHS NHANES August 2021-August 2023 `DPQ_L` Depression Screener joined to `DEMO_L`.
- 5,455 adults with all nine PHQ-9 symptom items observed after source-format validation.
- Used for ordinal factor structure, graded-response IRT, test information and measurement-invariance/DIF analysis.

## Evidence map

| Version | Scientific question | Real-data evidence | Main limiting result |
|---|---|---|---|
| v0.2 | How do repeated PHQ-9 scores change? | 15,261 reconstructed participant-month measurements; mixed-effects description | Repeated outcome availability declines over follow-up |
| v0.3 | Can deterioration be predicted at a defensible time zero? | Strict t0 participant-held-out AUC 0.620; AP 0.107; Brier 0.0621 | Broad interval features add little and weaken timing integrity |
| v0.4 | Does prediction/phenotyping survive stricter validation? | Forward-time participant-disjoint AUC 0.593; cluster bootstrap; decision curve | Later-window performance weakens; trajectory stability falls to ARI 0.389 under one specification; medication causal estimate withheld |
| v0.5 | How should sparse service percentages be pooled? | 123 NHS providers; Beta-Binomial partial pooling; prior sensitivity; 2,000 PPC panels | Simple exchangeable hierarchy under-predicts the lower provider tail |
| v0.6 | Does PHQ-9 behave as a coherent ordinal latent measure? | Polychoric factor audit; four-category GRM; conditional test information; first sex-DIF screen | Initial anchored screen flags 6/9 items; invariance cannot be claimed |
| v0.7 | Does the DIF signal survive anchor purification? | Iterative purification; leave-one-anchor-out sensitivity; weighting sensitivity | Stable signal contracts to DPQ030, DPQ040 and DPQ050; DPQ090 is weighting-sensitive |
| v0.8 | Does repeated provider structure explain v0.5 lack of fit? | 703 provider-month rows, 119 providers; dynamic logit-Normal hierarchy; persistence PPC | Persistence is reproduced but extreme provider tails/dispersion remain under-predicted |
| v0.8.1 | Are Normal provider-effect tails the problem? | Prespecified Normal vs Student-t df 10/5/3 comparison | Student-t df=5 improves only marginally; no candidate passes all PPCs |
| v0.9 | What is time to first reliable PHQ-9 change? | 3,244 baseline participants; 8,115 person-period rows; competing first events; discrete CIF; 400 participant bootstraps; cause-specific cloglog | 1,176 first-missing-visit censorings; deterioration baseline-severity association varies over time |
| v0.10 | How sensitive is the v0.9 conclusion to missing follow-up? | IPCW; 20-fold stochastic MAR MI; Rubin pooling; MNAR delta grid | Month-12 improvement-vs-deterioration ordering is sensitive to small MNAR departures |

## Longitudinal outcomes and prediction: v0.2-v0.4

The score-level analysis reconstructs 15,261 unique participant-month PHQ-9 measurements and distinguishes:

- reliable improvement: PHQ-9 decrease of at least 6 points;
- reliable deterioration: PHQ-9 increase of at least 6 points;
- caseness crossing below PHQ-9 10;
- a 20% relative reduction retained only as an MCID sensitivity analysis.

A participant-random-intercept mixed model is descriptive rather than causal.

The strict deterioration predictor uses only interval-start PHQ-9 and baseline/screener information available at prediction time. Dynamic interval summaries are excluded because their source timing can overlap the future outcome window.

### Prediction results

| Evaluation | ROC-AUC | AP | Brier |
|---|---:|---:|---:|
| participant-held-out strict t0 | 0.620 | 0.107 | 0.0621 |
| forward-time + different participants | 0.593 | 0.119 | 0.0632 |

Forward-time calibration intercept is -0.693 and slope 0.762. A 300-replicate participant-cluster bootstrap gives AUC 95% interval 0.527-0.658. The weaker temporal result is retained rather than tuned away.

### Trajectory phenotyping

The initial three-class Gaussian-mixture trajectory solution has repeated-initialisation mean ARI 0.819, but specification checks produce ARI 0.389, 0.567 and 0.668. The classes are therefore exploratory summaries, not validated clinical subtypes.

### Causal-readiness gate

A target-trial protocol is written for medication initiation, including eligibility, strategies, time zero, follow-up and outcome. The effect estimate is deliberately **withheld** because the public `med_start` feature is a past-month dynamic variable and cannot be ordered safely before the three-month outcome interval. The project treats a defensible causal question as more important than forcing a propensity-score estimate from timing-ambiguous exposure data.

## Bayesian service modelling: v0.5-v0.8.1

### v0.5 single-month partial pooling

For provider `j`:

```text
y_j ~ Binomial(n_j, theta_j)
theta_j ~ Beta(alpha, beta)
```

June 2026 provides 123 complete provider count pairs. Posterior provider-population mean reliable improvement is 68.35% (95% CrI 67.40%-69.10%). Median absolute shrinkage is 0.68 percentage points and the 90th percentile is 5.72 points. A broader hyperprior changes provider posterior means by at most 0.103 points.

The critical result is a posterior predictive failure: seven observed providers are at or below 50% reliable improvement, while the model predicts a mean of 1.36 and a 97.5% upper bound of four. This is retained as model criticism.

### v0.8 dynamic provider-by-month hierarchy

Six official Monthly Activity files are joined into a real panel:

- January-June 2026;
- 703 provider-month observations after requiring at least four observed months;
- 119 providers;
- 110 observed in all six months.

The model is:

```text
y_jt ~ Binomial(n_jt, p_jt)
logit(p_jt) = mu_t + u_j
u_j ~ Normal(0, tau^2)
```

Consecutive month population logits receive a first-order Gaussian smoothing prior. Provider effects are integrated with Gaussian-Hermite quadrature and posterior uncertainty is approximated by a Laplace expansion around the posterior mode.

Posterior mean provider heterogeneity is `tau = 0.185` on the log-odds scale. Median absolute provider-month shrinkage is 1.61 percentage points and p90 is 6.73 points. Prior sensitivity is negligible for monthly population means.

The model reproduces broad provider persistence: January-to-June observed provider-rate correlation is 0.559 versus predictive mean 0.506, with posterior predictive p=0.737. It still fails the June lower tail: observed providers at or below 50% = 7 versus predictive mean about 1.0 and 97.5% upper bound 3.

### v0.8.1 robust provider-effect sensitivity

The same model is refitted with prespecified, variance-standardised provider-effect distributions:

- Normal;
- Student-t df=10;
- Student-t df=5;
- Student-t df=3.

Student-t df=5 gives the best diagnostic ordering but only reduces failures from 11/18 prespecified PPC checks under Normal to 10/18. In June it predicts about 1.46 providers at or below 50%, with a 97.5% upper bound of 4, while 7 are observed. No candidate passes all prespecified PPCs.

**Scientific conclusion:** stop tuning the random-effect tail. The next service model should test observed provider/service structure, case-mix proxies where public data support them, or richer time-varying heterogeneity. Heavy tails alone do not explain the data.

## Item-level psychometrics: v0.6-v0.7

### Source validation

A real ingestion error was caught in the NHANES XPT reader: SAS numeric zero was represented as the tiny positive float `5.397605346934028e-79`, causing naive response-code validation to discard most `0 = Not at all` values. The loader now normalises near-zero XPORT numerics before validation, and CI checks published CDC item frequencies exactly.

### Ordinal factor / IRT evidence

On 5,455 complete adults:

- survey-weighted Cronbach alpha: 0.857;
- first polychoric eigenvalue: 5.699;
- first/second eigenvalue ratio: 7.87;
- first dimension: 63.3% of polychoric variance;
- one-factor off-diagonal residual RMS: 0.066.

A four-category graded-response model fits 1,616 observed response patterns and converges. Item discrimination ranges from about 1.53 to 3.41. Conditional SEM falls from 1.882 at latent theta=-2 to 0.271 at theta=2, showing that measurement precision is severity-dependent.

### v0.7 anchor purification

The v0.6 one-item-at-a-time sex-DIF screen initially flags six of nine items. Because that makes the assumption that all other items are clean anchors doubtful, v0.7 allows previously flagged items to remain free and iterates until the flag set stabilises.

Purification converges in three rounds. Final stable sex-DIF signals are:

- `DPQ030`;
- `DPQ040`;
- `DPQ050`.

Final anchors are `DPQ010`, `DPQ020`, `DPQ060`, `DPQ070`, `DPQ080`, `DPQ090`. Each of the three stable signals remains flagged in all 6/6 leave-one-anchor-out analyses; the other six items are flagged in 0/6. Under equal weighting, `DPQ090` also appears, so it is labelled weighting-sensitive rather than a stable primary finding.

These are non-invariance signals in this public NHANES sample, not proof of item bias and not a Clinical Partners calibration.

## Competing first events: v0.9

v0.9 reframes longitudinal change as a discrete time-to-first-event question. Relative to month-0 PHQ-9, the first observed scheduled score with change <= -6 is reliable improvement and the first with change >= +6 is reliable deterioration. Only the first event is retained, making these mutually exclusive competing first events.

The primary analysis censors at the first missing scheduled PHQ-9 rather than skipping a gap and treating a later score as continuously observed.

Real-data cohort:

- 3,244 participants with reconstructed month-0 PHQ-9;
- 8,115 person-period rows;
- 597 first reliable improvements;
- 487 first reliable deteriorations;
- 1,176 participants censored at a first missing scheduled follow-up;
- zero conflicting duplicated PHQ-9 measurement values.

Discrete cumulative incidence:

| Month | CIF improvement | CIF deterioration | No reliable change survival |
|---:|---:|---:|---:|
| 3 | 0.1048 | 0.0706 | 0.8246 |
| 6 | 0.1584 | 0.1196 | 0.7220 |
| 9 | 0.1956 | 0.1542 | 0.6502 |
| 12 | **0.2151** | **0.1852** | **0.5997** |

Cause-specific complementary-log-log models use month-specific baseline hazards and participant-cluster robust standard errors. A one-SD higher baseline PHQ-9 has an improvement cause-specific HR 2.79 (95% CI 2.60-2.99), with no detected time interaction (`p=0.608`). For deterioration, the pooled baseline-severity HR is about 1.00, but the baseline-severity × time interaction is significant (`p=0.0156`), so the pooled HR is not interpreted as a stable effect across follow-up.

This is prognosis/description, not a treatment-effect analysis.

## Missing follow-up sensitivity: v0.10

The v0.9 censoring assumption is challenged three ways.

### Observed availability in the v0.9 baseline cohort

| Month | Observed | Missing | Missing rate |
|---:|---:|---:|---:|
| 0 | 3,244 | 0 | 0.0% |
| 3 | 3,244 | 0 | 0.0% |
| 6 | 2,612 | 632 | 19.5% |
| 9 | 2,338 | 906 | 27.9% |
| 12 | 1,632 | 1,612 | 49.7% |

### IPCW

A pooled logistic observation model predicts remaining observed at the next scheduled visit among the current event-free risk set using month, baseline PHQ-9, last observed PHQ-9 and change from baseline. Observation-model AUC is 0.617 and Brier score 0.152. Stabilised weights are mild: median 1.00, raw p99 1.216, raw maximum 1.647; 2.0% are truncated by the prespecified rule.

Month-12 weighted cumulative incidence becomes:

- improvement: **0.2227**;
- deterioration: **0.1869**.

Thus the observed-history IPCW correction does not materially reverse the primary ordering.

### MAR multiple imputation

Twenty stochastic chained-equation imputations use Bayesian regression with the scheduled PHQ-9 vector and available baseline categorical indicators. Observed PHQ-9 scores are restored exactly after every imputation. Estimates are pooled with Rubin's rules.

At month 12 under MAR:

- improvement: **0.2153** (95% CI 0.2004-0.2301);
- deterioration: **0.1942** (95% CI 0.1787-0.2097);
- improvement minus deterioration: **0.0211** (95% CI -0.0024 to 0.0445).

The point estimate still favours improvement, but uncertainty spans zero.

### MNAR delta sensitivity

Only originally missing follow-up scores receive an additive delta after each MAR imputation. Positive delta means missing PHQ-9 values are systematically worse than MAR predictions.

At month 12:

| Delta added to missing PHQ-9 | Improvement | Deterioration | Difference (I-D) |
|---:|---:|---:|---:|
| -1 | 0.2310 | 0.1780 | +0.0530 |
| 0 | 0.2153 | 0.1942 | +0.0211 |
| +1 | 0.2052 | 0.2152 | -0.0100 |
| +2 | 0.1977 | 0.2436 | -0.0459 |
| +3 | 0.1932 | 0.2775 | -0.0843 |
| +6 | 0.1878 | 0.3893 | -0.2015 |

The **point-estimate ordering reverses at +1 PHQ-9 point** among originally missing follow-up scores. At +2 points the 95% interval for improvement-minus-deterioration is entirely below zero (-0.0710 to -0.0208).

This does not prove that follow-up is MNAR by +1 or +2 points. It quantifies how little unobserved deterioration would be required to change the clinical interpretation. PSYCHE-D does not identify missingness reason as questionnaire non-response versus attrition or release preprocessing.

## What the project now demonstrates

### Strongly implemented on real data

- longitudinal outcome reconstruction;
- mixed-effects description;
- clinically meaningful change rules;
- prediction-time control and participant-held-out validation;
- forward-time validation and calibration;
- participant-cluster bootstrap uncertainty;
- trajectory clustering with specification-stability checks;
- Bayesian hierarchical partial pooling;
- Bayesian prior sensitivity and posterior predictive model criticism;
- repeated provider-by-month hierarchical modelling;
- robust random-effect distribution sensitivity;
- ordinal psychometric factor structure;
- graded-response IRT;
- conditional test information / measurement precision;
- measurement invariance / DIF screening and anchor purification;
- competing first-event cumulative incidence;
- cause-specific discrete-time hazards;
- IPCW for incomplete follow-up;
- stochastic MAR multiple imputation and Rubin pooling;
- controlled MNAR delta / tipping-point sensitivity;
- reproducible public-source validation and CI.

### Deliberately not claimed

- patient-to-clinician-to-service hierarchy from public aggregate NHS files;
- referral-to-assessment survival from data that do not contain referral events;
- causal medication effects from PSYCHE-D timing-ambiguous exposure fields;
- full Clinical Partners patient-population validation;
- longitudinal PHQ-9 item-level measurement invariance from cross-sectional NHANES;
- proof that a DIF signal means an item is biased.

## Reproducibility

Dedicated GitHub Actions workflows download real public source files, run unit tests, execute the analysis, validate source/model invariants and upload evidence artifacts. Important source/data checks include:

- PSYCHE-D MD5 verification;
- exact NHS count extraction and denominator checks;
- direct official NHS monthly activity-file provenance;
- NHANES XPT near-zero regression test plus exact CDC response-frequency checks;
- optimiser convergence checks;
- probability / cumulative-incidence accounting invariants;
- observed-data v0.9 estimand reproduced exactly before v0.10 corrections;
- MI and IPCW numerical bounds.

Key generated reports include:

```text
V05_BAYESIAN_PARTIAL_POOLING_REPORT.md
V06_PSYCHOMETRICS_REPORT.md
V08_DYNAMIC_BAYESIAN_SERVICE_REPORT.md
V081_ROBUST_PROVIDER_EFFECTS_REPORT.md
V09_COMPETING_RISKS_SURVIVAL_REPORT.md
V10_MISSINGNESS_MNAR_REPORT.md
```

## Interview framing

A concise project explanation is:

> I built the portfolio as a sequence of clinical research decisions rather than a method checklist. I first defined repeated PHQ-9 outcomes and a strict prediction time, then showed that performance weakened under a later participant-disjoint validation window and that trajectory clusters were not robust enough for a subtype claim. At service level, I used real NHS provider counts for Bayesian partial pooling, but posterior predictive checks exposed a lower-tail lack of fit. Adding six months of persistent provider effects reproduced cross-month provider persistence, while Normal and prespecified heavy-tailed random effects still failed to explain the extremes, so I stopped distributional tuning rather than selecting the nicest model. At measurement level, I fitted an ordinal PHQ-9 factor/IRT model and used iterative anchor purification to separate stable from anchor-sensitive DIF signals. Finally, I modelled time to first reliable improvement or deterioration as competing events and challenged the first-missing-visit censoring assumption with IPCW, twenty MAR imputations and MNAR delta sensitivity. Under MAR the month-12 improvement-deterioration difference is small and uncertain, and a +1-point MNAR shift in missing PHQ-9 values reverses the point-estimate ordering. The common theme is deciding what the data can support, checking robustness, and keeping negative findings rather than forcing a clinical claim.

## Next high-value evidence

Further work should be driven by data that can support the question:

1. **Service hierarchy:** add observed service/provider structure or public case-mix proxies before trying more random-effect distributions; the v0.8.1 heavy-tail sensitivity shows that tail tuning alone is insufficient.
2. **Time-varying hazards:** characterise the v0.9 deterioration baseline-severity × time interaction rather than reporting one constant hazard ratio.
3. **Causal estimation:** use a real dataset with defensible assignment/time zero for an actual treatment or service-effect estimand; retain the PSYCHE-D medication causal gate.
4. **Referral pathway survival:** require real patient-level referral/assessment/treatment timestamps, normally available only through governed NHS/TRE access rather than public aggregate files.
5. **Patient-clinician-service partial pooling:** require a genuine patient-to-clinician hierarchy rather than synthesising clinician identifiers.

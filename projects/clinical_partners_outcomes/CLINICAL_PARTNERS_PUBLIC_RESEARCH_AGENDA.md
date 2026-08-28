# Clinical Partners public-data research agenda

This note translates public Clinical Partners service information into candidate statistical studies and states which parts of the methodology are already demonstrated on real public substitute data. It is **not** an analysis of Clinical Partners patient data. No private Clinical Partners data are used or inferred.

Public Clinical Partners pages reviewed in August 2026 describe NHS pathways that include referral/triage, booking, pre-assessment questionnaires, diagnostic assessment, feedback/reporting and, where commissioned, medication initiation/titration. Publicly listed instruments include HADS and ASRS for adults and R-CADS, SDQ and Conners measures for children. These pathway facts motivate the study designs below; exact internal states, timestamps, instruments, clinician assignment rules and governance would require confirmation inside the organisation.

## What the public-data portfolio already demonstrates

The repository deliberately separates method evidence from target-population claims.

| Clinical Partners-style question | Public substitute data | Implemented evidence |
|---|---|---|
| Repeated outcome change / deterioration | PSYCHE-D | longitudinal PHQ-9, mixed-effects description, strict t0 prediction, temporal validation, competing first-event analysis |
| Incomplete follow-up | PSYCHE-D | IPCW, 20-fold MAR multiple imputation, Rubin pooling, MNAR delta/tipping-point sensitivity |
| Sparse service outcome estimates | NHS Talking Therapies aggregate provider counts | Bayesian partial pooling, dynamic provider×month hierarchy, prior sensitivity, posterior predictive checks |
| Questionnaire measurement | NHANES PHQ-9 item responses | polychoric factor audit, graded-response IRT, test information, sex DIF, iterative anchor purification/sensitivity |
| Causal study design | PSYCHE-D + public service scenarios | target-trial specification and explicit refusal to estimate when treatment time zero is unsafe |

The portfolio does **not** claim that these substitute datasets reproduce Clinical Partners patient mix or operational data.

# Study 1 — referral-to-assessment / treatment pathway

## Question

Where does waiting time accumulate, which transitions are slow, and which patients are at risk of remaining unassessed or untreated for a long period?

A useful starting state structure is:

```text
referral received
  -> triage decision
  -> booking
  -> pre-assessment complete
  -> diagnostic assessment
  -> feedback/report
  -> medication initiation, if relevant
  -> repeated titration
  -> stabilised / ongoing management
```

The actual state set must be derived from internal operational data rather than forced to match a public website.

## Minimum internal/TRE data

- patient identifier;
- referral received timestamp;
- triage and booking timestamps;
- assessment / feedback / treatment timestamps;
- pathway/service/team;
- closure, rejection, transfer, withdrawal and discharge reason codes;
- baseline patient characteristics measured before time zero;
- censoring/data-cut date.

## Analysis

For a first endpoint, time zero would be accepted referral and event time first diagnostic assessment. Patients still waiting at data cut are right-censored. If mutually exclusive pathway exits exist, those exits should be modelled as competing risks or as a multi-state process rather than automatically treated as non-informative censoring.

Candidate methods:

- Kaplan-Meier only when one event/censoring process is appropriate;
- cause-specific discrete/continuous-time hazards;
- cumulative incidence for competing exits;
- flexible parametric survival where appropriate;
- multi-state models for pathway transitions;
- hierarchical survival models when service/team clustering matters.

### Existing transferable evidence

v0.9 already implements a discrete competing-first-event analysis on real longitudinal mental-health data: first reliable PHQ-9 improvement versus first reliable deterioration, with cumulative incidence, participant bootstrap and cause-specific complementary-log-log models. That demonstrates the survival/competing-risk mechanics without pretending that PSYCHE-D contains referral events.

# Study 2 — incomplete follow-up and outcome availability

## Question

How sensitive are conclusions about clinical outcomes to patients whose later questionnaires are not observed?

Internal data should distinguish, where possible:

- questionnaire non-response;
- disengagement;
- discharge after improvement;
- transfer;
- pathway closure;
- administrative data loss.

These mechanisms should not be collapsed automatically into one generic missingness process.

## Analysis sequence

1. describe availability by time, service and patient characteristics;
2. model observed follow-up / censoring using variables measured before the missing visit;
3. use IPCW if the target estimand is a time-to-event or longitudinal observed-history analysis;
4. run MAR multiple imputation using outcomes and auxiliary predictors;
5. add controlled MNAR sensitivity, for example delta-adjusted pattern-mixture assumptions;
6. state the point or interval where a clinical conclusion changes.

### Existing transferable evidence

v0.10 demonstrates this sequence on PSYCHE-D. In its month-0 cohort, PHQ-9 missingness reaches 49.7% by month 12. IPCW changes month-12 competing cumulative incidence only modestly, while 20-fold MAR MI leaves a small uncertain improvement-minus-deterioration difference. A +1 PHQ-9-point MNAR shift among originally missing follow-up values reverses the point-estimate ordering; at +2 points the pooled interval for improvement-minus-deterioration is entirely below zero. This is reported as assumption sensitivity, not as the true missing-data mechanism.

# Study 3 — patient, clinician and service variation

## Question

How much does outcome vary across patients, clinicians and services after accounting for baseline case mix, and how uncertain are estimates for small groups?

With genuine internal hierarchy, a repeated continuous outcome could be modelled as:

```text
y_ijst = alpha + f(t) + X_i beta + b_i + u_j + v_s + epsilon_ijst

b_i ~ Normal(0, tau_patient)
u_j ~ Normal(0, tau_clinician)
v_s ~ Normal(0, tau_service)
```

For binary/reliable-change outcomes, use an appropriate GLMM or Bayesian likelihood rather than treating percentages as Gaussian observations.

## Checks before interpretation

- verify clinician/service assignment dates;
- inspect denominator distribution and switching between clinicians/services;
- prespecify case-mix adjustment;
- use posterior intervals / shrinkage rather than raw league tables;
- run prior sensitivity and posterior predictive checks;
- do not interpret random effects as causal clinician quality effects.

### Existing transferable evidence

v0.5 demonstrates denominator-aware Bayesian partial pooling on real NHS provider counts. v0.8 extends this to January-June 2026 provider×month data with a persistent provider effect. The dynamic model captures broad January-to-June provider persistence but still under-predicts extreme provider outcomes. v0.8.1 compares Normal and prespecified Student-t provider-effect distributions; heavy tails improve fit only marginally and do not resolve the lower-tail failure. The correct next step is measured service/case-mix structure, not further tail tuning.

A **patient→clinician→service** model is intentionally not faked because public NHS aggregate files do not contain the required assignment hierarchy.

# Study 4 — psychometric validity and clinically meaningful change

## Questions

- Do items support the intended latent construct in the local service population?
- Where along severity is the instrument precise or imprecise?
- Are item thresholds/discriminations comparable across relevant groups?
- Is score change larger than expected measurement error?
- Is measurement behaviour stable across time, modality and pathway stage?

For ordered responses a graded-response model is one option:

```text
logit P(Y_iq >= k) = a_q * (theta_i - b_qk)
```

Measurement invariance / DIF should be assessed before assuming latent or total-score group comparisons are directly comparable.

### Existing transferable evidence

v0.6-v0.7 now implement the item-level component on real NHANES PHQ-9 responses:

- source-format / item-frequency validation;
- weighted polychoric factor diagnostics;
- four-category graded-response IRT;
- conditional test information and SEM;
- multi-group sex-DIF screen;
- iterative anchor purification;
- leave-one-anchor-out sensitivity;
- weighting sensitivity.

The purified sex-DIF signal is limited to DPQ030, DPQ040 and DPQ050, each stable in all leave-one-anchor-out runs. This is a public-population non-invariance signal, not a claim about Clinical Partners instruments or proof of item bias.

Longitudinal item-level reliable change and time invariance still require repeated item administrations.

# Study 5 — treatment or pathway-change causal evaluation

## Question

Does a specific treatment, pathway redesign, booking process, commissioning change or capacity intervention improve clinical outcomes, time to treatment, completion or disengagement relative to the relevant counterfactual?

## Target-trial first

Before choosing propensity scores, DiD, IV or heterogeneous-treatment-effect methods, specify:

- eligibility;
- strategies/intervention;
- assignment or exposure mechanism;
- time zero;
- follow-up;
- outcome;
- causal contrast;
- pre-treatment confounders;
- censoring/intercurrent events;
- analysis population.

The PSYCHE-D medication example deliberately withholds an effect estimate because the public `med_start` feature cannot be aligned safely to interval time zero. That is a study-validity result, not a missing software feature.

## Possible service-level quasi-experimental designs

A clearly timed rollout or commissioning change could support:

- interrupted time series with level/slope changes and seasonality checks;
- difference-in-differences only with a credible comparator and pre-trends;
- event-study coefficients for pre/post dynamics;
- survival models with time-varying capacity exposure;
- target-trial emulation if patient-level treatment assignment/confounding data are available.

A method should not be called causal merely because it includes a treatment indicator or propensity score.

### Remaining portfolio gap

The next useful causal portfolio addition should use **real data with defensible assignment and time zero**. One credible treatment-effect study is more valuable than separate PSM, IV, DiD and uplift checkbox demonstrations.

# Study 6 — free-text clinical information

A Clinical Partners free-text pipeline should start with a narrow clinical question, not generic embeddings:

```text
assessment / report text
  -> entity extraction
  -> negation
  -> temporality
  -> experiencer / source
  -> clinician-reviewed structured variables
  -> downstream study
```

Past, negated or family-history statements must not become current positive patient events merely because a keyword is present. Annotation guidance, clinician review, inter-rater agreement, error analysis and subgroup performance should precede production use.

This subproject keeps NLP as a designed component unless a suitable clinical-text dataset is added; the core public-data evidence here focuses on statistical outcome research rather than duplicating a disconnected generic NLP demo.

# First 90-day scientific sequence

## 1. Reconstruct and audit the pathway

Create patient-level event and repeated-outcome tables with explicit timestamps, provenance, reason codes, state-transition validity and instrument completion.

## 2. Choose one decision-relevant primary study

A defensible first study could be referral-to-assessment time or repeated clinical outcome change. Write the estimand and analysis plan before subgroup fishing.

## 3. Make missingness part of the primary analysis

Quantify observation/closure mechanisms and prespecify IPCW/MI/MNAR sensitivity where follow-up is incomplete.

## 4. Add multilevel uncertainty

Estimate service/clinician variation with partial pooling only when the hierarchy and case-mix variables are genuine. Use posterior predictive checks to decide whether the hierarchy is adequate.

## 5. Separate prediction from causal evaluation

A deterioration-risk model and an effect of a pathway redesign answer different questions. Prediction requires calibration/transport validation; causal inference requires counterfactual identification and defensible time zero.

## 6. Validate the measurement layer

Where questionnaires drive endpoints or decisions, check item structure, precision and invariance before treating score differences as directly comparable.

## 7. Build reusable scientific components

Version cohort construction, endpoint derivation, survival/risk-set logic, missingness summaries, hierarchical models, calibration, psychometrics, subgroup reviews and reproducible reports.

## Interview boundary statement

> I used public Clinical Partners pathway information to decide which research questions would be useful, and real public mental-health/NHS datasets to demonstrate the statistical methods. I would not claim that those datasets reproduce Clinical Partners case mix or operations. Where the open data support a method, I implemented it and stress-tested it; where referral timestamps, clinician assignments or treatment time zero are unavailable, I keep the work at the study-design level rather than synthesising the missing structure.

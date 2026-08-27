# Clinical Partners public-data research agenda

This note converts public Clinical Partners service information into candidate statistical studies for interview discussion. It is a study-design document, not an analysis of Clinical Partners patient data. No private Clinical Partners data are used or inferred.

Public source pages checked in August 2026:

- NHS service pathways: https://www.clinical-partners.co.uk/working-with-the-nhs/what-we-can-offer/current-nhs-pathways/
- NHS working-with-us resources: https://www.clinical-partners.co.uk/working-with-the-nhs/
- Right to Choose waiting-time/service updates: https://www.clinical-partners.co.uk/nhs-right-to-choose-assessments-and-medication/nhs-right-to-choose-wait-times-and-updates/
- Healthcare Director Dr Paul Wallang: https://www.clinical-partners.co.uk/about-us/leadership-team/dr-paul-wallang/

The public pathway page documents a sequence from referral/triage through booking, pre-assessment questionnaires, diagnostic assessment, feedback/reporting and, where commissioned, medication initiation and repeated titration. It also lists instruments including HADS and ASRS for adults and R-CADS, SDQ and Conners measures for children. These observations motivate the study designs below; the actual data model, endpoints and governance rules would need confirmation with Clinical Informatics and clinical leadership.

## Study 1: stable outcome estimates across clinicians and services

### Question

How much does patient outcome vary across services or clinicians after accounting for baseline case mix, and how uncertain are estimates for small groups?

### Minimum data

- patient identifier;
- service and clinician identifiers with valid assignment dates;
- outcome instrument and item/total score;
- assessment date;
- baseline severity and major prespecified case-mix variables;
- treatment/pathway stage;
- completion/censoring reason where available.

### Model

For a repeated continuous outcome `y_ijst` for patient `i`, clinician `j`, service `s` and time `t`:

```text
y_ijst ~ Normal(mu_ijst, sigma)
mu_ijst = alpha + f(t) + X_i beta + b_i + u_j + v_s
b_i ~ Normal(0, tau_patient)
u_j ~ Normal(0, tau_clinician)
v_s ~ Normal(0, tau_service)
```

The service and clinician effects use partial pooling. Small groups therefore receive more shrinkage and wider posterior uncertainty than large groups. The public NHS Beta-Binomial analysis in `v05_bayesian_partial_pooling.py` is a count-level demonstration of this same statistical principle; it is not a substitute for the patient-level model above.

### Checks before interpretation

- inspect clinician/service sample sizes and assignment rules;
- adjust only for prespecified case-mix variables measured before the outcome window;
- test whether residual variance and trajectories differ materially by service;
- report posterior intervals rather than a raw league table;
- run prior sensitivity and posterior predictive checks;
- do not interpret clinician effects causally unless assignment and confounding assumptions support that claim.

## Study 2: referral-to-assessment and referral-to-treatment time

### Question

Where does waiting time accumulate, which pathway transitions are slow, and which patients are at higher risk of remaining unassessed or untreated for a long period?

### Public pathway state structure

A useful starting multi-state representation is:

```text
referral received
  -> triage decision
  -> booking
  -> pre-assessment complete
  -> diagnostic assessment
  -> feedback/report
  -> medication initiation, if relevant
  -> repeated titration
  -> stabilised/ongoing management
```

The actual state set should be defined from operational data rather than forced to match the public web page.

### Analysis

For a simple first endpoint, define time zero as an accepted referral and event time as first diagnostic assessment. Patients still waiting at the data cut are right-censored. If there are several mutually exclusive pathway exits, define those exits from real reason codes and use a competing-risk or multi-state analysis rather than treating every exit as non-informative censoring.

Possible models include cause-specific Cox models, flexible parametric survival models, or Bayesian multilevel survival models with service-level effects. The model choice comes after checking the event-time process, ties, proportional-hazards assumptions and service structure.

### Capacity changes as time-varying context

Clinical Partners publicly reported on 14 May 2026 that Greater Manchester ICB had reached the funded appointment volume for that financial year, so new booking dates and new ADHD medication titration appointments could not be scheduled until further funding, while referrals could still be accepted onto the waiting list.

This creates a useful research question about service capacity, but it is **not automatically a random natural experiment**. If patient-level and ICB-level timestamps were available, possible designs include:

- interrupted time-series analysis around a clearly dated capacity change;
- difference-in-differences only if a credible comparison ICB and pre-trend support exist;
- survival models with time-varying capacity indicators;
- queue/pathway analyses separating referral inflow from appointment capacity.

Any causal interpretation would require checking concurrent policy changes, referral composition, spillovers between ICBs, seasonality and changes in data recording.

## Study 3: psychometric validity and clinically meaningful change

### Public measurement context

The Clinical Partners public pathway page lists several instruments, including:

- adult ADHD: AQ-10 self-report, ASRS-18 self-report/informant and HADS;
- child/adolescent ADHD: Conners measures, SDQ and R-CADS;
- child/adolescent autism: AQ-10, Conners-4PS, SDQ and R-CADS;
- adult autism: AQ-10, ASRS-6 and HADS.

### Questions

- Do items support the intended latent construct in this service population?
- Are item thresholds/discrimination similar across relevant patient groups?
- Is longitudinal score change comparable over time, or does measurement behaviour itself change?
- What level of change is larger than expected measurement error?
- Does a threshold used for clinical decision support retain acceptable sensitivity/specificity in the local population?

### Candidate models

For ordered item responses, a graded-response item response theory model is one option:

```text
logit P(Y_iq >= k) = a_q * (theta_i - b_qk)
```

where `theta_i` is latent severity, `a_q` is item discrimination and `b_qk` are ordered item thresholds.

Before reporting group comparisons, test measurement invariance or differential item functioning where sample sizes permit. Reliable change and minimal clinically important difference should be treated as separate questions: statistical reliability of change does not by itself establish clinical importance.

### Data boundary

The current repository has PHQ-9 total-score longitudinal evidence but does not yet claim an item-level IRT analysis. A real IRT extension requires item-level responses from a suitable public dataset or governed Clinical Partners data.

## Study 4: treatment or pathway-change causal evaluation

### Question

Does a specific pathway or treatment change improve clinical outcome, time to treatment, completion or disengagement compared with the relevant counterfactual?

### Target-trial first

Before selecting propensity scores, difference-in-differences, instrumental variables or heterogeneous treatment-effect models, specify:

- eligibility;
- treatment strategies;
- time zero;
- follow-up;
- outcome;
- causal contrast;
- pre-treatment confounders;
- censoring/intercurrent events;
- analysis population.

The v0.4 PSYCHE-D example in this repository deliberately withholds a medication effect because the public treatment-change variable cannot be aligned safely to time zero. The same standard should apply to service data.

### Possible service-level quasi-experimental work

A staged operational rollout, commissioning change or capacity intervention could support an interrupted time-series or difference-in-differences design if timing, comparison groups and pre-trends are credible. A model should not be called causal just because it includes a propensity score or a treatment indicator.

## Study 5: free-text clinical information

The job description refers to assessment letters and clinical free text. A useful pipeline would begin with a narrow clinical question rather than generic embedding generation.

For example:

```text
assessment/report text
  -> entity extraction
  -> negation
  -> temporality
  -> experiencer/source
  -> clinically reviewed structured variables
  -> downstream study
```

A statement such as a past or negated risk event must not be converted into a current positive event merely because a keyword is present. Annotation guidance, clinician review, inter-rater agreement, error analysis and subgroup performance should come before production use.

## First 90-day scientific sequence I would propose in interview

### 1. Reconstruct and audit the pathway

Create a patient-level event table and repeated-outcome table with explicit timestamps, provenance and reason codes. Quantify missingness, duplicate/inconsistent events, state-transition validity and instrument completion.

### 2. Choose one decision-relevant outcome study

Start with a question that has a defensible endpoint and enough data, such as referral-to-assessment time or repeated outcome change. Write a short statistical analysis plan before inspecting subgroup results.

### 3. Add multilevel uncertainty

Estimate service/clinician variation with partial pooling and case-mix adjustment where the hierarchy and sample sizes support it. Use posterior predictive checks and sensitivity analyses.

### 4. Separate prediction from causal inference

A risk model for disengagement and a causal estimate of a pathway change answer different questions. Define time zero and counterfactual logic before causal estimation.

### 5. Build reusable scientific components

Turn the validated pieces into version-controlled functions for cohort construction, endpoint derivation, missingness summaries, multilevel models, calibration, subgroup review and reproducible reports.

## Interview boundary statement

A safe concise statement is:

> I used public Clinical Partners pathway information to decide which research questions would be useful, and official NHS/public patient-level datasets to demonstrate the statistical methods. I would not claim that the public data reproduce Clinical Partners case mix or that these are the organisation's current models. The value of the exercise is the study design: clear time zero, clinically defined outcomes, multilevel uncertainty, explicit missing-data limits and a separation between prediction and causal claims.

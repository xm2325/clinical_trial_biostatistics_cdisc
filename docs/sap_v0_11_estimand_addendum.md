# SAP addendum — v0.11 ACTOT estimand and missing-data review

## Status

Controlled portfolio addendum. This document does not amend the source study protocol and is not sponsor-approved.

## Estimand

The portfolio primary ACTOT estimand is `EST-ACTOT-W24-TP` in `spec/estimands.json`.

- Treatment conditions: Placebo, Xanomeline Low Dose, Xanomeline High Dose.
- Population: randomised subjects with an observed baseline ACTOT score.
- Variable: ACTOT change from baseline at Week 24.
- Intercurrent event: treatment discontinuation.
- Strategy for discontinuation: treatment policy; observed ACTOT values after discontinuation remain eligible for the primary longitudinal analysis.
- Population-level summary: each active treatment versus placebo difference in adjusted mean change at Week 24.

## Primary estimator

The current primary longitudinal estimator remains the v0.5+ REML MMRM with treatment-by-visit and baseline-by-visit fixed effects, unstructured within-subject covariance and Satterthwaite degrees of freedom. Week 8, Week 16 and Week 24 observed ACTOT records enter the model. No LOCF rows are created for the primary MMRM.

The working missing-data assumption is MAR conditional on the variables represented in the fitted model. This assumption belongs to the estimator, not to the five estimand attributes. The portfolio missingness review reports the observed data pattern and discontinuation context but does not claim that MAR has been verified.

## Supportive sensitivity

The existing Week 24 LOCF ANCOVA remains a supportive legacy-style sensitivity/stress test. It is not the primary estimator and is not used to define the treatment-policy estimand.

## New review outputs

- T16: ACTOT missingness by treatment arm and scheduled visit.
- T17: Week 24 missingness by recorded disposition context.
- Subject-level Week 8/16/24 observed/missing patterns.
- Blocking estimand/estimator/missingness consistency review.

## Change control

A hypothetical change from treatment-policy handling of discontinuation to a hypothetical strategy is represented as a v0.11 portfolio change-control scenario. Such a change is required to trigger review of the estimand specification, MMRM analysis path, related longitudinal TLFs, T16/T17, QC evidence and controlled statistical documentation.

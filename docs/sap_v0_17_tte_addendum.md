# SAP addendum — v0.17 exploratory retention TTE

## Analysis objective

Describe time to study discontinuation as an exploratory trial-retention endpoint. This addendum does not modify the ACTOT primary estimand, MMRM, missing-data strategy or multiplicity family.

## Analysis population

Randomised subjects with an actual treatment arm in Placebo, Xanomeline Low Dose or Xanomeline High Dose and complete first-treatment/study-end dates.

## Endpoint derivation

Parameter: `TTDISC` — Time to Study Discontinuation (days).

- Origin: first treatment date (`TRTSDT`).
- Analysis date: study end/discontinuation date (`EOSDT`).
- Analysis value: `EOSDT - TRTSDT + 1` days.
- Event: `DCSFL=Y`, `CNSR=0`.
- Censor: protocol completion (`COMPLFL=Y`) at `EOSDT`, `CNSR=1`.

The discontinuation/completion flags must form an exact partition for the controlled population.

## Statistical methods

Kaplan–Meier estimates of remaining free from study discontinuation are reported by arm at days 56, 112, 168 and 182 with log-log 95% confidence intervals.

For exploratory active-versus-placebo comparisons, report:

- unadjusted log-rank test;
- Cox proportional-hazards model with Efron ties;
- hazard ratio and 95% confidence interval;
- `cox.zph` proportional-hazards diagnostic.

No multiplicity adjustment is applied. A PH diagnostic signal is reported and limits interpretation of the Cox hazard ratio rather than causing the analysis to be replaced or the threshold to be changed.

## Interpretation boundary

Higher hazard ratio indicates higher study-discontinuation hazard relative to placebo. Results describe retention in the public-data exercise; they are not efficacy or confirmatory clinical conclusions.

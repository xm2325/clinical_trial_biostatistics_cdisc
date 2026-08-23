# Exploratory time-to-study-discontinuation analysis — v0.17

## Purpose

v0.17 adds an ADTTE-style BDS exercise for trial retention using the public portfolio data. The endpoint is **time from first treatment date to study discontinuation**. It is an exploratory operational/retention endpoint, not an efficacy endpoint and not part of the ACTOT primary multiplicity family.

## Derivation

One `TTDISC` record is created per randomised subject in Placebo, Xanomeline Low Dose and Xanomeline High Dose.

- `STARTDT`: ADSL-style `TRTSDT`;
- `ADT`: ADSL-style `EOSDT`;
- `AVAL = ADT - STARTDT + 1` days;
- `DCSFL=Y`: study-discontinuation event, `CNSR=0`;
- `COMPLFL=Y`: censored at protocol completion date, `CNSR=1`;
- `EVNTDESC`: discontinuation reason for events, `STUDY COMPLETED` for censored completions.

The derivation requires complete origin/end dates, one row per subject, a mutually exclusive and exhaustive discontinuation/completion partition, positive duration and exact event/censor mapping.

## Survival analysis

`R/tte_retention_analysis.R` uses the R `survival` package.

- Kaplan–Meier retention probabilities are reported at days 56, 112, 168 and 182 with log-log 95% confidence intervals.
- T24 is the treatment-arm KM table.
- T25 contains exploratory Low Dose vs Placebo and High Dose vs Placebo log-rank and Cox model summaries.
- Cox models use Efron ties.
- `cox.zph` is reported for proportional-hazards diagnostics.

A proportional-hazards diagnostic signal does not itself fail the pipeline. If present, it limits interpretation of the Cox hazard ratio; KM estimates and log-rank evidence remain visible rather than forcing the model assumption to pass.

No multiplicity adjustment is applied to T25 because it is explicitly exploratory. T24/T25 are not incorporated into the controlled ACTOT Week 24 Bonferroni family.

## Traceability

Controlled sources and outputs:

```text
outputs/adsl_style.csv
  -> outputs/adtte_retention_style.csv
  -> outputs/adtte_retention_qc.csv
  -> R survival analysis
  -> outputs/table24_retention_km.csv
  -> outputs/table25_retention_pairwise.csv
  -> outputs/tte_retention_survival_qc.csv
```

`spec/tte_retention.json` locks the population, dates, censoring/event rules, KM timepoints and exploratory Cox settings.

## Evidence boundary

This is independent public-data portfolio work. `adtte_retention_style.csv` is an ADTTE-style exercise and is not claimed to be sponsor-approved, formally ADaM-conformant/submission-ready, independently validated production programming, an efficacy endpoint or a regulatory conclusion.

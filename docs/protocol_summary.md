# Portfolio protocol summary

## Objective

Demonstrate a reproducible clinical-trial safety-analysis workflow on public SDTM test data with explicit analysis assumptions and traceability from DM/EX/DS/AE to analysis-ready datasets and TLF-style outputs.

## Source domains

- **DM**: demographics and planned/actual treatment labels.
- **EX**: observed exposure records used to derive the portfolio treatment window.
- **DS**: randomisation, completion and discontinuation status.
- **AE**: adverse events.

## Analysis populations

- **Randomised population:** at least one DS record with `DSDECOD == RANDOMIZED`.
- **Safety population:** at least one observed EX record.

These are portfolio definitions selected for this exercise.

## Safety endpoints

1. Any treatment-emergent adverse event (TEAE).
2. Serious TEAE.
3. Related TEAE using the pre-specified portfolio relationship rule.
4. Moderate/severe TEAE.
5. Discontinuation due to an adverse event.
6. TEAE incidence by system organ class / preferred term and severity.

## TEAE window

AE start date from first observed `EXSTDTC` through 30 days after last observed `EXENDTC`, inclusive.

## Exploratory treatment comparison

For each active arm versus placebo, the workflow estimates the subject-level risk of any TEAE, the unadjusted risk difference, a two-sided 95% Wald confidence interval and Fisher's exact-test p-value.

This comparison is exploratory. It is not described as a confirmatory estimand for the source study.

## Important limitation

This document is not the source protocol for the CDISC pilot study. It defines a transparent independent portfolio analysis using public test data.

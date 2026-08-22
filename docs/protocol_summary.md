# Portfolio protocol summary

## Objective

Demonstrate a reproducible clinical-trial biostatistics workflow on public CDISC pilot data, with explicit analysis assumptions and traceability from source domains through analysis-ready datasets, statistical models, TLF-style outputs, QC evidence and a separate protocol-design/sample-size exercise.

This is an independent portfolio specification. It is not the source protocol and is not sponsor-approved.

## Source domains

- **DM**: demographics and planned/actual treatment labels.
- **EX**: observed exposure records used to derive the portfolio treatment window.
- **DS**: randomisation, completion and discontinuation status.
- **AE**: adverse events.
- **QS**: questionnaire data used for CIBIC+ and ACTOT efficacy analyses.

## Analysis populations

- **Randomised population:** at least one DS record with `DSDECOD == RANDOMIZED`.
- **Safety population:** at least one observed EX record.
- **ACTOT efficacy population:** randomised subjects with numeric ACTOT baseline and at least one numeric post-baseline ACTOT value.
- **MMRM population:** ACTOT efficacy subjects with at least one observed Week 8, Week 16 or Week 24 ACTOT record.

These are portfolio definitions selected for this exercise.

## Safety endpoints

1. Any treatment-emergent adverse event (TEAE).
2. Serious TEAE.
3. Related TEAE using the pre-specified portfolio relationship rule.
4. Moderate/severe TEAE.
5. Discontinuation due to an adverse event.
6. TEAE incidence by system organ class / preferred term and severity.

## TEAE window

AE start date from first observed `EXSTDTC` through 30 days after treatment end, inclusive. Documented disposition-date fallback is used when an exposure end date is unavailable.

## Efficacy endpoints and analyses

The efficacy work sample uses public ACTOT questionnaire records.

- Week 24 observed-case ANCOVA: Week 24 value adjusted for treatment and baseline.
- LOCF sensitivity: latest eligible post-baseline value through analysis day 168, fitted with the same ANCOVA form.
- Longitudinal MMRM: observed Week 8/16/24 change from baseline with treatment-by-visit and baseline-by-visit fixed effects, unstructured covariance as primary and heterogeneous AR(1) as covariance sensitivity.

All efficacy p-values are exploratory. No confirmatory hypothesis family is claimed for the source study.

## Exploratory safety treatment comparison

For each active arm versus placebo, the workflow estimates subject-level risk of any TEAE, the unadjusted risk difference, a two-sided 95% Wald confidence interval and Fisher's exact-test p-value.

## Portfolio protocol-design exercise

Version 0.7 adds a separate planning exercise for a three-arm parallel design with two active-versus-placebo comparisons on Week 24 ACTOT change from baseline. The machine-readable assumptions live in `spec/protocol_design.json` and are analysed by `scripts/run_protocol_design.py`.

The illustrative design uses family-wise two-sided alpha 0.05, Bonferroni alpha 0.025 per active-versus-placebo comparison, common SD 6.0, 15% anticipated dropout, 80%/90% target power and treatment-difference scenarios of 2.0, 2.5 and 3.0 points.

These are portfolio planning scenarios only. They are not presented as the source trial's assumptions or as clinically justified values.

## Reproducibility and QC

The workflow separates:

1. Python derivation and analysis QC;
2. public CDISC reference validation;
3. independent R/Python programming comparison;
4. MMRM data/model QC;
5. executable SAP-to-TLF structural traceability;
6. protocol-design/sample-size QC.

Required failures exit non-zero in GitHub Actions and diagnostic outputs are retained where possible.

## Important limitation

The repository demonstrates statistical programming, design reasoning and traceable analysis on public data. It does not claim sponsor/CRO production experience, SAS programming, DSMB responsibility, regulatory-submission ownership or independent validation by a second programmer.

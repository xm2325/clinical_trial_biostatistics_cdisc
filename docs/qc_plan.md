# QC plan — portfolio version 0.11

The workflow separates required validation layers for Python derivation, official-reference checks, independent R/Python programming QC, MMRM data/model QC, ACTOT estimand/missing-data review, analysis-dataset/TLF review, statistical change-impact assessment and SAP-to-TLF traceability. Required failures exit non-zero. Informational discrepancies remain visible rather than being converted into pass/fail rules without justification.

## Python safety and efficacy pipeline

The core Python pipeline retains **24 required checks** covering ADSL-/ADAE-style keys and population flags, exposure dates, disposition, TEAE timing, ADQSCIBC/ACTOT derivations, Week 24 analysis sets and official-reference key/source-row agreement.

Key hard conditions include:
- all safety subjects have observed exposure and usable treatment dates;
- no portfolio-defined TEAE occurs outside the safety population or outside the 30-day treatment-emergent window;
- ACTOT `CHG = AVAL - BASE`;
- observed Week 24 ANCOVA has one row per subject;
- official ADQSCIBC key, `DTYPE` and selected `QSSEQ` agreement are each 100%.

The v0.11 first-pass live run retained **24/24 required Python pipeline checks**.

## Unit tests and negative controls

Version 0.11 adds tests for the estimand and missing-data layer as well as a regression test for matching change-control specification versions. The final-head target is **49 unit tests**.

Negative controls include deliberately:
- using LOCF as the primary estimand estimator;
- removing an observed post-discontinuation ACTOT record from an MMRM fixture;
- corrupting a missingness denominator;
- omitting a graph-required TLF from a change request;
- supplying unknown or cyclic change-impact dependencies;
- mismatching graph/request specification versions;
- corrupting analysis-dataset treatment, derivation, metadata or TLF denominators.

Each injected defect is required to fail its corresponding validator.

## Independent R/Python programming QC

`R/independent_qc.R` starts from the same cached public DM, EX, DS, AE and QS inputs and does not call Python derivation functions. Python outputs are read only for the final comparison.

The **16 required checks** cover population counts, TEAE counts/risk differences, CIBIC selection and values, ACTOT source rows/baseline/change, and Week 24/LOCF ANCOVA estimates. The v0.11 first-pass live run retained **16/16** checks, with maximum R/Python ANCOVA numerical difference `4e-14`, below the pre-specified `1e-8` tolerance.

This is a second implementation by the same portfolio author, not independent validation by a second human programmer.

## MMRM required checks

`R/mmrm_analysis.R` uses observed Week 8, Week 16 and Week 24 ACTOT records; LOCF values do not enter the primary model. Eleven hard checks cover planned treatment/visit levels, subject-visit uniqueness, `CHG`/`BASE` consistency, finite likelihood for unstructured and heterogeneous AR(1) covariance models, expected contrast cardinality and finite inference.

The v0.11 first-pass live run retained **11/11** checks on 451 observed post-baseline records from 189 subjects (Week 8=189, Week 16=146, Week 24=116).

## ACTOT estimand and missing-data review

The v0.11 gate is driven by `spec/estimands.json` and executes after MMRM generation. It separates the five ICH E9(R1)-style estimand attributes from estimator assumptions.

Portfolio estimand `EST-ACTOT-W24-TP` specifies:
- treatment: three portfolio arms, each active arm compared with placebo;
- population: randomised subjects with an observed baseline ACTOT score;
- variable: ACTOT change from baseline at Week 24;
- intercurrent event: treatment discontinuation, handled with a treatment-policy strategy;
- population-level summary: active-versus-placebo difference in adjusted mean change.

The primary estimator remains observed-data REML MMRM with unstructured covariance and Satterthwaite df. `MAR` is recorded as a working estimator assumption, not an estimand attribute. The existing LOCF Week 24 ANCOVA remains a supportive legacy-style stress test only.

The v0.11 first-pass live run passed **21/21 required estimand/missing-data checks**. In the public data, the target population is 254 subjects; Week 24 has 116 observed and 138 missing ACTOT values (**54.3% missing**). No observed arm-visit ACTOT records were identified after recorded treatment discontinuation in this public run (`0`). Therefore the treatment-policy retention rule is executable and negative-control tested, but the live dataset does not provide a positive post-discontinuation retention example.

T16 and T17 add descriptive evidence:
- T16 reconciles observed/missing counts for all 3 arms × 3 visits and decomposes missingness by whether recorded discontinuation occurred before/on the nominal visit;
- T17 reports the recorded disposition context among target-population subjects missing Week 24 ACTOT.

These tables describe the observed dataset. They do not establish that MAR is true or identify an unobserved MNAR mechanism.

## Analysis-dataset and TLF reviewer gate

The v0.9+ reviewer remains separate from the derivation programs and checks generated analysis datasets and TLF denominators. The v0.11 first-pass run retained **24/24 required reviewer checks** across ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM outputs, with SHA256 identities for reviewed files.

## Statistical change-control impact gate

Version 0.11 extends the dependency graph to estimand/missingness governance. The graph and change-request specifications must now declare the same version; a mismatch is a hard failure.

Five illustrative portfolio scenarios are assessed:

| Change | Propagated components | Required impacts | TLF scope |
|---|---:|---:|---|
| CR-001 safety population definition | 4 | 18 | T01–T07 |
| CR-002 TEAE follow-up window | 3 | 14 | T04–T07 |
| CR-003 primary ACTOT visit | 6 | 27 | T08–T12, T15 |
| CR-004 primary MMRM covariance | 3 | 11 | T11–T15 |
| CR-005 treatment-discontinuation strategy | 4 | 18 | T11–T17 |

The v0.11 first-pass live run covered **88/88 graph-required impact declarations** and resolved **88/88 required resources**, with zero missing and zero extra declarations.

CR-005 is hypothetical: it tests the impact of changing treatment discontinuation from treatment-policy to hypothetical strategy. It does **not** change the current analysed estimand or MMRM.

## SAP-to-TLF traceability

The machine-readable registry now contains **17 planned TLFs**. T16 and T17 are linked to the v0.11 estimand review evidence. The v0.11 first-pass live run passed **17/17** output existence, output-contract, analysis-dataset-link and QC-evidence checks.

Structural traceability supplements rather than replaces analysis-specific statistical QC.

## Official-reference profiler

Required hard gates retain 100% selected-key/`DTYPE`/`QSSEQ` agreement for the official CIBIC/ACTOT reference comparisons where specified. Reference-value mismatches are retained with source-row traces rather than overwritten.

Verified public reference results retained in v0.11 include 705 CIBIC selected rows and 1,016 selected ACTOT analysis keys.

## Informational diagnostics

Informational evidence includes AE missing start dates, treatment-end fallbacks, official-reference value mismatch traces, model fit diagnostics, covariance sensitivity, MMRM-versus-ANCOVA differences, missingness patterns/disposition context and conservative extra change-impact declarations if present.

## CI evidence retention

GitHub Actions prints Python, R, MMRM, estimand/missingness, reviewer, change-control and traceability summaries and uploads `outputs/` even when a downstream analysis step fails where possible. This keeps the evidence needed to investigate a failed gate rather than hiding it behind a single pass/fail status.

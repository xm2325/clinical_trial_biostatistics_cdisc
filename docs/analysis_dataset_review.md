# Analysis-dataset and TLF review — portfolio v0.9

## Purpose

This layer simulates a statistical-programming review step after analysis datasets and TLF-style outputs have been generated. It is intentionally separate from the derivation code that creates those outputs.

The objective is to detect inconsistencies that can survive within-dataset QC but become visible when a statistician reviews analysis populations, treatment attributes, source traceability, metadata expectations and output denominators across datasets.

> **Evidence boundary:** this is an independent portfolio reviewer gate written by the same author as the analysis pipeline. It is not sponsor/CRO production review, independent second-programmer validation, formal ADaM conformance assessment, or regulatory-submission sign-off.

## Verified live result

The v0.9 GitHub Actions run passes **24/24 required reviewer checks**. The reviewer covers **17 generated files** and records a SHA256 digest for every reviewed file.

The 24 required checks comprise:

- **19 cross-dataset / derivation / TLF reconciliation checks**; and
- **5 machine-readable dataset-contract checks** for ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM datasets.

The six review areas are `analysis_dataset`, `derivation`, `metadata_contract`, `population`, `tlf_denominator` and `tlf_structure`.

## Machine-readable dataset contracts

`spec/analysis_dataset_contracts.json` defines portfolio contracts for five generated analysis datasets. Each contract specifies:

- expected file identity;
- dataset key;
- required columns;
- required non-missing fields;
- controlled values and whether blank is allowed.

The contract specification itself is hashed in `outputs/analysis_dataset_review_metrics.json` so the reviewer evidence is tied to the exact metadata rules used in the run.

These are portfolio QC contracts, not formal Define-XML, CDISC conformance rules or sponsor-approved ADaM metadata.

## Analysis-dataset parentage and subject attributes

Required checks include:

- ADSL-style `STUDYID + USUBJID` uniqueness;
- safety population as a subset of randomised subjects;
- every ADAE-style row resolving to one ADSL-style subject;
- ADAE treatment, safety-population flag and treatment dates reconciling to ADSL-style values;
- ACTOT analysis rows resolving to randomised ADSL-style subjects with matching treatment;
- ANCOVA analysis-subject treatment reconciling to ADSL-style treatment.

## Derivation and source-record review

The reviewer requires:

- a unique ACTOT baseline for efficacy subjects;
- `BASE` to equal the selected baseline-row `AVAL`;
- ACTOT and ANCOVA `CHG` to equal `AVAL - BASE`;
- every MMRM row to trace to the exact ACTOT source row through `STUDYID + USUBJID + QSSEQ`;
- MMRM treatment, `AVAL`, `BASE` and `CHG` to match that source row;
- unique MMRM subject-visit keys and visits restricted to Week 8, Week 16 and Week 24.

## TLF denominator reconciliation

The review reconstructs denominators from generated analysis datasets instead of trusting displayed table values. It checks:

- demographics N versus ADSL randomised population by treatment;
- disposition randomised and safety denominators versus ADSL flags;
- TEAE safety N, subjects with TEAE and total TEAE events versus ADAE-style records;
- SOC/PT and severity denominators versus ADSL safety population;
- any-TEAE risk-difference arm denominators and displayed risks versus subject-level TEAE incidence;
- Week 24 descriptive N versus observed ANCOVA analysis subjects;
- ANCOVA least-squares-mean N and contrast total N versus analysis-subject sets;
- MMRM visit-count output versus the MMRM analysis dataset;
- MMRM LS-mean and active-versus-placebo contrast coverage across all planned visits.

In the verified run, the reviewer reconstructs randomised/safety arm Ns of **Placebo=86, Xanomeline High Dose=96, Xanomeline Low Dose=72**. Observed Week 24 Ns are **Placebo=30, High Dose=59, Low Dose=27**. All linked TLF denominators/counts reconcile.

## Negative-control tests

Unit tests deliberately introduce defects and require the reviewer to reject them:

1. change an ADAE treatment value so it no longer agrees with ADSL;
2. change a safety-table denominator;
3. change an MMRM `CHG` value while retaining its source `QSSEQ`;
4. remove a required dataset-contract column;
5. insert an invalid controlled-value flag.

The verified v0.9 run contains **34/34 passing unit tests**, including these failure-mode tests. They show that the reviewer can reject deliberately inconsistent inputs rather than only reporting conditions that happen to be true in the current public-data run.

## CI acceptance

`scripts/run_dataset_review.py` writes:

- `outputs/analysis_dataset_review.csv` — check-level result and diagnostic detail;
- `outputs/analysis_dataset_review_metrics.json` — pass counts, review areas, dataset-contract hash and SHA256 digests of reviewed files;
- `outputs/analysis_dataset_review_summary.md` — concise reviewer summary.

The script exits non-zero if any required reviewer check fails. GitHub Actions runs the reviewer after the R MMRM step and before final SAP-to-TLF traceability validation, so a cross-dataset, metadata-contract or denominator inconsistency blocks the build.

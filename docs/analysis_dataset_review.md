# Analysis-dataset and TLF review — portfolio v0.9

## Purpose

This layer simulates a statistical-programming review step after analysis datasets and TLF-style outputs have been generated. It is intentionally separate from the derivation code that creates those outputs.

The objective is to detect inconsistencies that can survive within-dataset QC but become visible when a statistician reviews analysis populations, treatment attributes, source traceability and output denominators across datasets.

> **Evidence boundary:** this is an independent portfolio reviewer gate written by the same author as the analysis pipeline. It is not sponsor/CRO production review, independent second-programmer validation, formal ADaM conformance assessment, or regulatory-submission sign-off.

## Reviewed generated files

The executable review reads generated ADSL-style, ADAE-style, ACTOT analysis, ANCOVA and MMRM datasets plus the main safety and efficacy TLF-style outputs. Every reviewed file receives a SHA256 digest in `analysis_dataset_review_metrics.json`.

## Required review areas

### Analysis-dataset parentage and subject attributes

- ADSL-style `STUDYID + USUBJID` must be unique.
- Safety subjects must be a subset of randomised subjects.
- Every ADAE-style row must resolve to one ADSL-style subject.
- ADAE treatment, safety-population flag and treatment dates must reconcile to ADSL-style values.
- ACTOT analysis rows must resolve to randomised ADSL-style subjects with matching treatment.
- ANCOVA analysis-subject treatment must reconcile to ADSL-style treatment.

### Derivation review

- ACTOT efficacy subjects must have a unique baseline record.
- `BASE` must equal the selected baseline-row `AVAL`.
- ACTOT and ANCOVA `CHG` must equal `AVAL - BASE`.
- Every MMRM record must trace to the exact ACTOT source row through `STUDYID + USUBJID + QSSEQ`.
- MMRM treatment, `AVAL`, `BASE` and `CHG` must match that source row.
- MMRM subject-visit keys must be unique and visits restricted to Week 8, Week 16 and Week 24.

### TLF denominator reconciliation

The review recomputes denominators from the generated analysis datasets instead of trusting the displayed table values.

- demographics N versus ADSL randomised population by treatment;
- disposition randomised and safety denominators versus ADSL flags;
- TEAE safety N, subjects with TEAE and total TEAE events versus ADAE-style records;
- SOC/PT and severity denominators versus ADSL safety population;
- any-TEAE risk-difference arm denominators and displayed risks versus subject-level TEAE incidence;
- Week 24 descriptive N versus observed ANCOVA analysis subjects;
- ANCOVA least-squares-mean N and contrast total N versus analysis-subject sets;
- MMRM visit-count output versus the MMRM analysis dataset;
- MMRM LS-mean and active-versus-placebo contrast coverage across all planned visits.

## Negative-control tests

Unit tests deliberately introduce three review defects and require the reviewer to reject them:

1. an ADAE treatment value is changed so that it no longer agrees with ADSL;
2. a safety-table denominator is deliberately changed;
3. an MMRM `CHG` value is changed while retaining its source `QSSEQ`.

These tests are evidence that the review checks are capable of failing rather than only documenting conditions that happen to be true in the current public dataset.

## CI acceptance

`scripts/run_dataset_review.py` writes:

- `outputs/analysis_dataset_review.csv` — check-level result and diagnostic detail;
- `outputs/analysis_dataset_review_metrics.json` — pass counts, review areas and SHA256 digests of reviewed files;
- `outputs/analysis_dataset_review_summary.md` — concise reviewer summary.

The script exits non-zero if any required reviewer check fails. GitHub Actions therefore treats a cross-dataset or denominator inconsistency as a failed build.

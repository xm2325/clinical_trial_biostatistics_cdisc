# v0.25 Clinical Programming Workflow

## Objective

v0.25 reframes the existing public-data clinical-trial portfolio as an executable clinical-programming release package. It does not add a new statistical model. The controlled path is:

```text
public SDTM/source data
  -> declared programming specification
  -> analysis-dataset derivation
  -> TLF production
  -> QC / re-programming evidence
  -> SAP-to-TLF traceability
  -> statistical change-control evidence
  -> SHA256 release manifest
```

The workflow is implemented by `spec/clinical_programming_workflow_v0_25.csv`,
`src/cdisc_portfolio/clinical_programming_workflow.py`, and
`scripts/run_clinical_programming_workflow.py`.

## Controlled packages

The v0.25 programming specification registers seven representative packages:

- CP-001: DM/EX/DS -> ADSL-style subject-level analysis dataset.
- CP-002: AE + ADSL-style -> ADAE-style adverse-event analysis dataset.
- CP-003: QS + ADSL-style -> ADQS-style ACTOT efficacy analysis dataset.
- CP-004: ADSL-style -> ADTTE-style retention analysis dataset.
- CP-005: ADSL-style + ADAE-style -> T07 TEAE risk-difference table.
- CP-006: ADQS-style + ANCOVA analysis subjects -> T10 Week 24 ANCOVA contrast table.
- CP-007: MMRM analysis dataset -> T12 MMRM treatment-contrast table.

The registry is deliberately representative rather than a duplicate of the existing T01-T25 SAP-to-TLF registry. Its purpose is to show the programming chain at the program/package level.

## Executable checks

The v0.25 gate blocks release when any required condition fails. It checks:

1. program IDs, deliverable types and QC modes are controlled;
2. production-program and specification files exist;
3. declared SDTM/source domains are present in the run manifest;
4. declared upstream analysis inputs exist;
5. deliverable outputs exist;
6. required columns are present and declared keys are unique;
7. linked QC evidence exists and all required QC rows pass;
8. the existing statistical change-control gate reports `all_passed=true`;
9. the existing SAP-to-TLF traceability gate reports `all_passed=true`;
10. at least one controlled package has cross-language reconstruction evidence.

For every registered package, the release manifest records SHA256 identities for
upstream analysis inputs, production programs, specifications, deliverables and
QC evidence.

## Validation strategy

The portfolio already contains two useful forms of re-programming evidence.

`R/independent_qc.R` reconstructs important safety and efficacy results in R from
the public source data and compares them with the Python implementation. This is
used by CP-001, CP-002, CP-003, CP-005 and CP-006.

The primary MMRM uses `mmrm::mmrm`; the independent reconstruction uses
`nlme::gls` with a separately implemented covariance structure. CP-007 links the
resulting cross-package QC evidence.

CP-004 uses derivation-specific QC for the ADTTE-style endpoint. It is not
described as independent second-programmer validation.

## Generated evidence

A successful run writes:

- `outputs/clinical_programming_workflow_qc.csv`
- `outputs/clinical_programming_release_manifest.csv`
- `outputs/clinical_programming_workflow_metrics.json`
- `outputs/clinical_programming_workflow_summary.md`

The controlled portfolio claim is:

```text
PORTFOLIO_CLINICAL_PROGRAMMING_WORKFLOW_READY
```

The claim is issued only when all required checks pass.

## Evidence boundary

This remains independent portfolio work using public CDISC/pharmaverse data.
The v0.25 gate does not claim sponsor/CRO production experience, formal
second-programmer sign-off, formal ADaM conformance, a validated GxP production
environment, database lock approval, or regulatory submission readiness.

The purpose is narrower: provide reproducible evidence that the portfolio can be
run and reviewed as a controlled clinical-programming workflow rather than only
as a collection of statistical analyses.

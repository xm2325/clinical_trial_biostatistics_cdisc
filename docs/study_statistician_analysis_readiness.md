# v0.20 Study-statistician analysis-readiness and evidence-closure pack

## Purpose

v0.20 adds a study-statistician review layer over the already validated statistical programming and CDISC evidence. It does not add another statistical model or another TLF. The purpose is to show a controlled transition from generated analysis data and TLFs to an analysis-package review decision with explicit data-cutoff checks, known-issue disposition and final evidence closure.

This remains public-data portfolio work. It is not a sponsor database lock, formal blinded data review meeting, sponsor/CRO sign-off, validated production release or regulatory-submission readiness decision.

## Controlled sequence

The clean workflow uses four distinct stages:

```text
validated analysis data / metadata / standards evidence
  -> pre-closure analysis readiness
  -> statistical change-control impact assessment
  -> SAP-to-TLF traceability validation
  -> evidence closure
```

The separation is deliberate. Pre-closure readiness asks whether the analysis package is internally ready for statistician review. Change control and traceability are then run as independent governance gates. Evidence closure succeeds only when all three results come from the same clean workflow run.

## Analysis data cutoff

`spec/analysis_readiness_v0_20.json` fixes the portfolio analysis data cutoff at **2015-03-05**. The readiness program checks date values used by the ADSL-, ADAE-, ADQS- and ADTTE-style analysis data and blocks the gate if any analysed date exceeds that cutoff.

The cutoff is a portfolio control derived from the public test-data package. It is not represented as a sponsor database-lock date.

## Treatment-blind aggregate review

The blinded review artifact is intentionally limited to aggregate checks:

- total subject count;
- randomized subject count;
- end-of-study date completeness;
- randomized ACTOT baseline coverage;
- dates beyond the configured analysis cutoff.

The generated `outputs/blinded_analysis_readiness_review.csv` is blocked from containing the treatment-assignment field names `TRT01P`, `TRT01A` or `ANLTRT`, either as columns or literal tokens. Treatment-specific statistical results remain outside this artifact.

## Known issues are retained, not hidden

The final analysis-readiness review carries three known public-data issues with expected counts and explicit dispositions.

### AR-001 — planned versus actual treatment mismatch

Expected count: **12 randomized subjects**.

Disposition: `ACCEPTED_FOR_ANALYSIS`.

The randomized-retention analysis uses planned randomized assignment and retains actual treatment as auditable context. A count change is blocking because it would mean the reviewed data no longer match the controlled issue record.

### AR-002 — Week 24 ACTOT missingness

Expected count: **138 randomized subjects** without observed Week 24 ACTOT under the configured analysis flag.

Disposition: `ADDRESSED_BY_SENSITIVITY`.

The observed-data MMRM remains the primary estimator. Missing-data risk is reviewed through the existing fixed-delta, subject-level MI and reference-based MI evidence. The issue is therefore not removed from the readiness record merely because sensitivity analyses exist.

### AR-003 — public ADQSCIBC reference-value differences

Expected count: **10 values**.

Disposition: `SOURCE_TRACE_ACCEPTED`.

The portfolio-derived selected values retain source-row traceability to the public QS input. Differences from the public ADQSCIBC reference remain visible rather than being overwritten to make a comparison appear exact.

## Readiness prerequisites

The pre-closure readiness gate depends on four earlier evidence layers:

```text
dataset_review
metadata_lineage
dataset_json
core_standards_state
```

Change control and TLF traceability are deliberately excluded from this prerequisite list. They execute after readiness and are required by the separate closure gate.

The controlled readiness claim is:

```text
PORTFOLIO_ANALYSIS_PACKAGE_READY_FOR_REVIEW
```

Tests reject attempts to replace it with a regulatory or submission-ready claim.

## Evidence closure

After readiness, the workflow runs the v0.20 statistical change-control assessment and SAP-to-TLF traceability validation. The separate closure runner then requires:

```text
analysis_readiness
change_control
traceability
```

The controlled closure claim is:

```text
PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE
```

A failed change-control or traceability gate does not retroactively rewrite the pre-closure readiness result; it blocks closure. This makes the dependency direction explicit and avoids a circular gate definition.

## CR-014

CR-014 controls changes to the v0.20 analysis-readiness definition or known-issue disposition. Its dependency chain covers:

```text
analysis_readiness_configuration
  -> blinded_analysis_readiness_review
  -> final_analysis_readiness_review
  -> analysis_evidence_closure
```

CR-014 has **0 impacted TLFs** by design. A change to cutoff, readiness checks or issue disposition requires review of the v0.20 spec, readiness evidence and review documentation, but it does not automatically alter the MMRM, multiplicity, missing-data sensitivity, survival analysis or TLF content.

## Generated evidence

Pre-closure readiness writes:

```text
outputs/blinded_analysis_readiness_review.csv
outputs/analysis_readiness_review.csv
outputs/analysis_readiness_metrics.json
outputs/analysis_readiness_summary.md
```

Post-governance closure writes:

```text
outputs/analysis_closure_review.csv
outputs/analysis_closure_metrics.json
outputs/analysis_closure_summary.md
```

The GitHub Actions artifact retains these files together with the statistical analyses, metadata/standards evidence, change-control assessment and TLF traceability evidence from the same clean run.

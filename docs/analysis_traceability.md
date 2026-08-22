# Analysis traceability — portfolio version 0.14

## Purpose

The executable traceability layer links each planned TLF to generated analysis data, required output structure and QC evidence. It is structural portfolio traceability, not sponsor-approved submission metadata or independent second-programmer sign-off.

## Versioned registry

`spec/analysis_traceability.csv` now contains `registry_version`. All rows must declare one identical non-empty version. The controlled v0.14 registry version is `0.14.0`.

The validator writes that registry version into `outputs/traceability_metrics.json`; the analysis version is no longer hard-coded in Python.

## Traceability chain

Each TLF row links:

```text
TLF ID + registry version
  -> objective / population / endpoint / method
  -> source domains
  -> analysis dataset(s)
  -> generated output
  -> QC evidence
  -> required output contract
  -> SHA256 output identity
```

`spec/output_contracts.json` defines the output path, required columns and minimum rows. `scripts/validate_traceability.py` validates the generated artifacts after all upstream analysis/QC gates.

## Required rules

For every TLF, CI requires:

1. a unique TLF ID;
2. one common non-empty registry version across all planned TLF rows;
3. a matching output contract;
4. complete planning metadata;
5. identical registry/contract output paths;
6. an existing generated output;
7. all required columns;
8. at least the minimum row count;
9. all linked analysis datasets to exist;
10. all linked QC files to exist;
11. a SHA256 digest for the output that passed validation.

## v0.14 registry

The registry contains **22 planned TLFs (T01-T22)**. The verified v0.14 formalisation run passed:

- output files: **22/22**;
- output contracts: **22/22**;
- analysis-data links: **22/22**;
- QC-evidence links: **22/22**;
- complete structural traceability: **22/22**.

T18/T19 are deterministic fixed-delta outputs. T20/T21 are v0.13 subject-level MI outputs. T22 is the v0.14 reference-based MI output.

## T22 trace

T22 reports two active-versus-placebo comparisons under four controlled strategies: MAR, JR, CR and CIR. Minimum rows: **8**.

Analysis evidence includes:

- `outputs/adsl_style.csv`;
- `outputs/adqs_actot_style.csv`;
- `outputs/rbmi_reference_ice_audit.csv`.

Required QC evidence includes:

- `outputs/estimand_review.csv`;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`.

The T22 contract requires strategy identifiers, ICE subject counts, pooled Week 24 inference, Monte Carlo errors, number of imputations, change from MAR, MCSE-to-SE ratio and a precision-pass flag.

## QC layers

Structural traceability is the final link in this chain:

```text
Python derivation/reference QC
  -> R/Python programming comparison
  -> MMRM QC
  -> estimand/missing-data review
  -> deterministic sensitivity QC
  -> subject-level MI and MCSE QC
  -> reference-based MI and MCSE QC
  -> analysis-dataset/TLF reviewer
  -> statistical change-control gate
  -> 22-TLF structural traceability
```

Structural output validity does not prove a numerical estimate is correct, and numerical QC does not prove that every planned output has the required data/QC links. The checks remain separate.

## Generated evidence

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

The output SHA256 is an audit aid tied to the exact generated file in a run.

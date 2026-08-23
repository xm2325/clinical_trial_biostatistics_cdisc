# Analysis traceability — portfolio version 0.15

## Purpose

The executable traceability layer links every planned TLF to generated analysis data, required output structure and QC evidence. It is structural portfolio traceability, not sponsor-approved submission metadata or independent second-programmer sign-off.

## Versioned registry

`spec/analysis_traceability.csv` contains `registry_version`. All rows must declare one identical non-empty value. The controlled v0.15 registry version is `0.15.0`.

The validator writes that value into `outputs/traceability_metrics.json`; analysis version is not hard-coded in Python.

## Traceability chain

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

`spec/output_contracts.json` defines output paths, required columns and minimum rows. `scripts/validate_traceability.py` validates generated artifacts after all upstream analysis/QC gates.

## Required rules

For every TLF, CI requires:

1. a unique TLF ID;
2. one common non-empty registry version;
3. a matching output contract;
4. complete planning metadata;
5. identical registry/contract output paths;
6. an existing generated output;
7. all required columns;
8. at least the minimum row count;
9. all linked analysis datasets to exist;
10. all linked QC files to exist;
11. a SHA256 digest for the output that passed validation.

## v0.15 registry

The registry contains **23 planned TLFs (T01–T23)**. The verified v0.15 run passes:

- output files: **23/23**;
- output contracts: **23/23**;
- analysis-data links: **23/23**;
- QC-evidence links: **23/23**;
- complete structural traceability: **23/23**.

T18/T19 are deterministic fixed-delta outputs. T20/T21 are subject-level MI outputs. T22 is the reference-based MI output. T23 is the v0.15 primary multiplicity decision output.

## T23 trace

T23 contains exactly two rows, corresponding to `H_LOW` and `H_HIGH` at Week 24 from the primary `Unstructured` MMRM.

Analysis evidence:

- `outputs/mmrm_analysis_dataset.csv`;
- `outputs/mmrm_treatment_contrasts.csv`.

Required QC evidence:

- `outputs/mmrm_qc.csv`;
- `outputs/multiplicity_qc.csv`.

The T23 contract requires:

- family and hypothesis IDs;
- contrast, endpoint, visit and covariance;
- estimate, SE and df;
- raw p-value;
- adjustment method;
- family alpha, comparison count and local alpha;
- adjusted p-value;
- family-wise reject flag.

The live public-data values are raw/adjusted p=0.169334/0.338669 for H_LOW and 0.421970/0.843940 for H_HIGH; neither is rejected under family-wise alpha 0.05.

## QC layers

```text
Python derivation/reference QC
  -> R/Python programming comparison
  -> MMRM QC
  -> primary multiplicity QC
  -> estimand/missing-data review
  -> deterministic sensitivity QC
  -> subject-level MI and MCSE QC
  -> reference-based MI and MCSE QC
  -> analysis-dataset/TLF reviewer
  -> versioned statistical change-control gate
  -> 23-TLF structural traceability
```

Structural output validity does not prove a numerical estimate is scientifically correct, and numerical QC does not prove every planned output has the required structural links. The checks remain separate.

## Generated evidence

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

The output SHA256 is an audit aid tied to the exact generated file in a run.

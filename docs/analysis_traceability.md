# Analysis traceability — portfolio version 0.12

## Purpose

The executable traceability layer links planned statistical outputs to generated analysis data and QC evidence. It is structural portfolio traceability, not sponsor-approved SAP/TLF metadata, submission validation or independent second-programmer sign-off.

## Traceability chain

Each planned TLF is registered in `spec/analysis_traceability.csv`:

```text
TLF ID
  -> objective / population / endpoint / method
  -> source domains
  -> analysis dataset(s)
  -> generated output
  -> QC evidence
  -> SHA256 output identity
```

`spec/output_contracts.json` defines the exact output path, required columns and minimum row count. `scripts/validate_traceability.py` validates the live generated artifacts after all upstream analysis/QC gates.

## Required rules

For every TLF, CI requires:

1. a unique TLF ID;
2. a matching output contract;
3. non-empty objective/population/endpoint/method/source/analysis/QC metadata;
4. identical registry and contract output paths;
5. an existing generated output;
6. all required columns;
7. at least the minimum row count;
8. all linked analysis datasets to exist;
9. all linked QC files to exist;
10. a SHA256 digest for the output that passed validation.

A required failure exits non-zero.

## Verified v0.12 registry

The registry now contains **19 planned TLFs**. The verified live run passes **19/19** for output existence, output contracts, analysis-data links and QC-evidence links.

| TLF | Output | Minimum rows |
|---|---|---:|
| T01 | Demographics | 1 |
| T02 | Subject disposition | 1 |
| T03 | Exposure | 1 |
| T04 | TEAE overview | 1 |
| T05 | TEAE by SOC/PT | 1 |
| T06 | TEAE by severity | 9 |
| T07 | Any-TEAE risk difference | 2 |
| T08 | ACTOT Week 24 descriptives | 3 |
| T09 | ACTOT Week 24 ANCOVA LS means | 6 |
| T10 | ACTOT Week 24 ANCOVA contrasts | 4 |
| T11 | ACTOT MMRM LS means | 9 |
| T12 | ACTOT MMRM contrasts | 6 |
| T13 | MMRM covariance sensitivity | 12 |
| T14 | MMRM model diagnostics | 2 |
| T15 | Week 24 MMRM versus ANCOVA | 2 |
| T16 | ACTOT missingness by arm/visit | 9 |
| T17 | Week 24 missingness by disposition | 1 |
| T18 | Fixed-delta sensitivity grid | **78** |
| T19 | Directional tipping points | **6** |

T18 and T19 depend on `outputs/mnar_sensitivity_inputs.csv` and `outputs/mnar_sensitivity_qc.csv`. Structural traceability therefore cannot pass merely because the final CSVs exist: the input evidence and dedicated sensitivity QC must also exist in the same live run.

## T18 trace example

```text
Objective
  Stress the primary Week 24 MMRM contrast under fixed mean shifts
  for outcomes that are missing at Week 24

Population
  Randomised subjects with observed baseline ACTOT

Endpoint
  Week 24 ACTOT change from baseline

Method
  Fixed-delta pattern-mixture mean-shift diagnostic
  Delta 0–6 by 0.5 under three pre-specified scenarios

Analysis evidence
  outputs/mnar_sensitivity_inputs.csv

TLF
  outputs/table18_actot_delta_sensitivity.csv
  rows >= 78

QC evidence
  outputs/mnar_sensitivity_qc.csv

Artifact identity
  SHA256 recorded by the traceability validator
```

## T19 trace example

T19 uses the same controlled inputs/QC but reports the analytic positive delta at which each active-minus-placebo point estimate reaches zero. Six rows are expected: three scenarios × two active-versus-placebo contrasts. The first non-negative 0.5-point grid value is retained as an independent bracketing check of the analytic threshold.

## Relationship to other QC layers

```text
Python derivation / pipeline QC
        |
Official CDISC reference validation
        |
Separate R/Python programming comparison
        |
MMRM model/data QC
        |
Estimand and missing-data review
        |
Fixed-delta sensitivity QC
        |
Analysis-dataset / TLF reviewer
        |
Statistical change-control impact gate
        |
19-TLF structural traceability
```

These checks answer different questions. Structural output validity does not prove a numerical estimate is correct, and numerical QC does not prove the planned output has the required metadata/links. The layers therefore remain separate.

## Generated traceability evidence

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

The SHA256 value identifies the exact output file that passed a given run. It is an audit aid, not a substitute for statistical-programming QC or source-data provenance.

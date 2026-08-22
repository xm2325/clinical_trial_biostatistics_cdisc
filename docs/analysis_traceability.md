# Analysis traceability — portfolio version 0.11

## Purpose

The executable traceability layer links planned statistical output to generated evidence. It makes the route from analysis intent through analysis data, final TLF and QC evidence inspectable rather than relying only on prose documentation.

This is structural traceability for an independent portfolio project. It does not claim sponsor-approved SAP/TLF specifications, regulatory-submission validation, SAS programming or independent review by a second human programmer.

## Traceability chain

Each planned TLF is registered in `spec/analysis_traceability.csv`:

```text
TLF ID
  -> title / objective
  -> analysis population
  -> endpoint
  -> statistical method
  -> source domains
  -> analysis dataset(s)
  -> output file
  -> QC evidence file(s)
```

`spec/output_contracts.json` adds an executable contract for the exact output path, required columns and minimum row count. `scripts/validate_traceability.py` validates those contracts against generated artifacts after all required upstream analysis/QC gates have run.

## Required validation rules

For every TLF, the validator requires:

1. a unique TLF ID;
2. a corresponding output contract;
3. non-empty objective, population, endpoint, method, source, analysis-dataset, output and QC metadata;
4. identical registry/contract output paths;
5. an existing generated output;
6. all required output columns;
7. at least the minimum row count;
8. all linked analysis datasets to exist;
9. all linked QC-evidence files to exist;
10. SHA256 identity for the generated output.

A required failure exits non-zero. The gate therefore validates actual generated evidence rather than static documentation alone.

## v0.11 registry

The registry contains **17 planned TLFs**:

| TLF | Output | Expected minimum rows |
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
| T13 | ACTOT MMRM covariance sensitivity | 12 |
| T14 | MMRM model diagnostics | 2 |
| T15 | Week 24 MMRM versus ANCOVA | 2 |
| T16 | ACTOT missingness by arm/visit | 9 |
| T17 | Week 24 missingness by disposition context | 1 |

T16/T17 are linked to ADSL-/ACTOT analysis data and `outputs/estimand_review.csv`, so structural traceability cannot pass if the new missingness outputs are present but their analysis/QC evidence is absent.

The v0.11 first-pass live run passes **17/17** for output existence, output contracts, analysis-dataset links and QC-evidence links.

## Machine-readable evidence

The validation step writes:

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

`traceability_validation.csv` records output existence, row-count and column-contract acceptance, linked-analysis-data acceptance, linked-QC acceptance, SHA256, read errors and final status for each TLF.

The output SHA256 identifies the exact file that passed structural checks in a given run. It does not replace dataset provenance or statistical-programming QC.

## Relationship to other QC layers

```text
Python derivation / pipeline QC
        |
Official CDISC reference validation
        |
Independent R/Python programming comparison
        |
MMRM model/data QC
        |
Estimand and missing-data review
        |
Analysis-dataset / TLF reviewer
        |
Statistical change-control impact gate
        |
SAP-to-TLF structural traceability
```

These layers answer different questions. Correct columns and links do not prove a numerical estimate is correct, which is why structural traceability supplements rather than replaces statistical QC.

## Example: T16 ACTOT missingness by visit

```text
Objective
  Describe observed and missing ACTOT by treatment and scheduled visit

Population
  Randomised subjects with observed baseline ACTOT

Endpoint
  ACTOT observation status

Method
  Arm-by-visit counts/percentages and discontinuation-linked decomposition

Source domains
  DM / DS / EX / QS

Analysis datasets
  outputs/adsl_style.csv
  outputs/adqs_actot_style.csv

TLF
  outputs/table16_actot_missingness_by_visit.csv
  expected rows >= 9

QC evidence
  outputs/estimand_review.csv

Artifact identity
  SHA256 recorded by the live traceability validator
```

This makes the missing-data review inspectable from its planned population and method through the generated evidence without implying production submission validation.

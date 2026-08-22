# Analysis traceability — portfolio version 0.6

## Purpose

Version 0.6 adds an executable link from planned statistical output to generated evidence. The aim is to make the route from analysis intent to final table inspectable rather than relying only on prose documentation.

This is structural traceability for an independent portfolio project. It does not claim sponsor-approved SAP/TLF specifications, regulatory-submission validation, SAS programming, or independent review by a second human programmer.

## Traceability chain

Each planned TLF is registered in `spec/analysis_traceability.csv` with the following fields:

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

`spec/output_contracts.json` adds an executable contract for each registered TLF. The contract defines:

- the exact output path;
- required output columns;
- a minimum expected row count.

After the Python, independent R and MMRM analyses have completed, `scripts/validate_traceability.py` validates the registry against the generated artifacts.

## Required validation rules

For every TLF, the validator requires all of the following:

1. the TLF ID exists exactly once in the registry;
2. the TLF ID has a corresponding output contract;
3. objective, population, endpoint, method, source, analysis dataset, output and QC metadata are non-empty;
4. the contract output path is identical to the registry output path;
5. the generated output file exists;
6. every required output column exists;
7. the output contains at least the contract minimum number of rows;
8. every linked analysis dataset exists;
9. every linked QC-evidence file exists;
10. the generated output receives a SHA256 content hash.

A required failure exits non-zero in GitHub Actions. The traceability gate therefore runs against the actual generated outputs, not only against static specifications.

## Verified live-run result

The verified v0.6 GitHub Actions run produced the following result:

| Validation measure | Result |
|---|---:|
| Planned TLFs | 15 |
| TLFs passing complete structural traceability | **15 / 15** |
| Output files found | **15 / 15** |
| Output contracts passed | **15 / 15** |
| Analysis-dataset links resolved | **15 / 15** |
| QC-evidence links resolved | **15 / 15** |
| Output SHA256 hashes recorded | **15 / 15** |

The generated TLF row counts were:

| TLF | Output | Rows |
|---|---|---:|
| T01 | Demographics | 22 |
| T02 | Subject disposition | 33 |
| T03 | Exposure | 12 |
| T04 | TEAE overview | 21 |
| T05 | TEAE by SOC/PT | 60 |
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

## Machine-readable evidence

The validation step writes:

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

`traceability_validation.csv` contains one record per TLF and records output existence, row-count acceptance, required-column acceptance, linked-analysis-data acceptance, linked-QC acceptance, SHA256, any read error and final pass/fail status.

The output SHA256 is an audit aid: it identifies the exact file that passed the structural contract in a given run. It is not a replacement for dataset provenance hashes or statistical programming QC.

## Relationship to the other QC layers

The repository now keeps four checks separate:

```text
1. Python derivation / pipeline QC
2. Official CDISC reference validation
3. Independent R/Python programming comparison
4. SAP-to-TLF structural traceability
```

The ACTOT MMRM also has its own data/model/inference QC gate.

These layers answer different questions. For example, an output can have the correct columns and traceability links while containing a wrong estimate; that is why structural traceability does not replace the statistical QC in `qc_report.csv`, `r_independent_qc.csv` or `mmrm_qc.csv`.

## Example: T12 ACTOT MMRM contrasts

The T12 trace is:

```text
Objective
  Compare active treatment with placebo by visit

Population
  Observed longitudinal ACTOT population

Endpoint
  ACTOT change from baseline

Method
  Visit-specific MMRM active-versus-placebo contrasts
  Primary covariance = unstructured

Source domains
  DM / DS / EX / QS

Analysis dataset
  outputs/mmrm_analysis_dataset.csv

TLF
  outputs/mmrm_treatment_contrasts.csv
  expected rows >= 6
  required columns include estimate, SE, df, CI, t statistic, p-value

QC evidence
  outputs/mmrm_qc.csv

Artifact identity
  SHA256 recorded by the live traceability validator
```

This makes the statistical work sample easier to audit from the planned method through the final numerical artifact without claiming a production submission process that the portfolio has not performed.

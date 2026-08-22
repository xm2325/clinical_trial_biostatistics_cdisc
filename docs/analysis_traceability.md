# Analysis traceability — portfolio version 0.13

## Purpose

The executable traceability layer links planned statistical outputs to generated analysis data and QC evidence. It is structural portfolio traceability, not sponsor-approved SAP/TLF metadata, submission validation or independent second-programmer sign-off.

The current effective registry contains **21 planned TLFs (T01-T21)**.

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

`spec/output_contracts.json` defines the output path, required columns and minimum row count. `scripts/validate_traceability.py` validates live generated artifacts after all upstream analysis/QC gates.

The v0.13 analysis chain represented by these links is:

```text
estimand
  -> missingness review
  -> primary MMRM
  -> deterministic fixed-delta sensitivity
  -> subject-level MI sensitivity
  -> MCSE precision QC
  -> TLF contracts
  -> change impact
  -> structural traceability
```

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

A required failure exits non-zero. A final TLF CSV cannot pass structural traceability when its linked analysis or QC evidence is missing.

## Current v0.13 registry

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
| T18 | Deterministic fixed-delta sensitivity grid | **78** |
| T19 | Directional tipping points | **6** |
| T20 | MAR subject-level MI pairwise sensitivity | **2** |
| T21 | Delta-adjusted subject-level MI sensitivity | **8** |

T18/T19 depend on the deterministic sensitivity inputs/QC. T20/T21 have additional MI and MCSE evidence requirements.

## T18/T19 deterministic sensitivity linkage

T18 and T19 depend on:

```text
outputs/mnar_sensitivity_inputs.csv
outputs/mnar_sensitivity_qc.csv
```

T18 reports the controlled 78-row scenario × contrast × delta grid. T19 reports six analytic positive deltas at which the active-minus-placebo point estimate reaches zero, with a grid-bracketing check.

The deterministic fixed-delta analysis reuses primary MMRM SE/df after mean shift and must not be interpreted as Rubin-pooling MI inference.

## T20 trace example

```text
Objective
  Evaluate Week 24 ACTOT under pairwise MAR subject-level MI

Population
  Randomised subjects with observed baseline ACTOT,
  analysed as Low Dose vs Placebo and High Dose vs Placebo

Endpoint
  Week 24 ACTOT change from baseline

Method
  Approximate-Bayesian rbmi longitudinal MI using Week 8/16/24 history
  -> Week 24 baseline-adjusted ANCOVA within each imputed data set
  -> Rubin pooling across 200 imputations

TLF
  outputs/table20_rbmi_mar_pairwise.csv
  rows >= 2

Required QC evidence
  outputs/rbmi_mi_qc.csv
  outputs/rbmi_mcse_qc.csv
  outputs/rbmi_draw_diagnostics.csv

Monte Carlo criterion
  MCSE(estimate) / pooled SE <= 7.5%

Artifact identity
  SHA256 recorded by the traceability validator
```

T20 therefore cannot pass merely because two pairwise rows exist. The MI QC, MCSE QC and draw diagnostics must all resolve in the same live run.

## T21 trace example

```text
Objective
  Stress the Week 24 pairwise MI result under controlled delta departures

Population
  Same pairwise ACTOT target populations as T20

Endpoint
  Week 24 ACTOT change from baseline

Method
  Reuse controlled MI draws and apply delta only to outcomes
  originally missing at Week 24

Scenarios
  MAR
  ACTIVE_PLUS_1
  ACTIVE_PLUS_2
  DIVERGENT_1

TLF
  outputs/table21_rbmi_delta_sensitivity.csv
  rows >= 8

Required QC evidence
  outputs/rbmi_mi_qc.csv
  outputs/rbmi_mcse_qc.csv
  outputs/rbmi_delta_audit.csv

Artifact identity
  SHA256 recorded by the traceability validator
```

The delta audit is required so that observed Week 24 outcomes and non-Week-24 outcomes cannot be shifted without failing the evidence chain.

## Statistical change-control linkage

Traceability is also connected to `spec/change_requests.json`. The current request set contains seven simulated changes.

CR-003 (primary ACTOT visit) and CR-005 (treatment-discontinuation/intercurrent-event strategy) explicitly propagate to T20/T21 and the MI review path. CR-007 directly controls the MI assumptions, including imputation count, longitudinal imputation model, MCSE threshold and delta scenarios.

This prevents T20/T21 from remaining structurally valid but scientifically stale after an upstream assumption change.

## Relationship to other QC layers

```text
Python derivation / pipeline QC
        |
Public CDISC reference validation
        |
Separate R/Python programming comparison
        |
MMRM model/data QC
        |
Estimand and missing-data review
        |
Deterministic fixed-delta sensitivity QC
        |
Subject-level MI QC
        |
Independent MCSE precision QC
        |
Analysis-dataset / TLF reviewer
        |
Statistical change-control impact gate
        |
21-TLF structural traceability
```

These layers answer different questions. Structural output validity does not prove a numerical estimate is correct, and numerical QC does not prove that a planned output has the required metadata, analysis links and QC links. They remain separate blocking checks.

## Generated traceability evidence

```text
outputs/traceability_validation.csv
outputs/traceability_metrics.json
outputs/traceability_summary.md
```

The SHA256 value identifies the exact output file that passed a given run. It is an audit aid, not a substitute for statistical-programming QC or source-data provenance.
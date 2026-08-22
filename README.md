# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, TLF-style outputs, public-reference validation, separate R/Python programming QC, longitudinal MMRM, executable SAP-to-TLF traceability, protocol-design/sample-size calculations, a controlled portfolio randomisation/initial-kit schedule, and an executable analysis-dataset/TLF reviewer gate.

> **Evidence boundary:** this is an independent portfolio project. Outputs are labelled `*-style` where they are not claimed to be submission-ready ADaM. The repository does **not** claim sponsor/CRO production, strong SAS production, DSMB, regulatory-submission, formal ADaM conformance, IRT/IWRS production, or independent second-programmer validation experience.

## Verified v0.9 live run

The full workflow has been executed in GitHub Actions against downloaded public source data and pinned public CDISC reference files.

| Verification layer | Verified result |
|---|---:|
| Python unit tests | **34/34 passed** |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| SAP-to-TLF structural traceability | **15/15 TLFs passed** |
| Protocol-design/sample-size QC | **7/7 passed** |
| Randomisation/initial-kit schedule QC | **10/10 passed** |
| Analysis-dataset/TLF reviewer QC | **24/24 passed** |
| Reviewed generated files with SHA256 | **17/17** |
| Randomised / safety subjects in public analysis | 254 / 254 |
| Official CDISC QS rows | 121,749 |
| Portfolio-defined TEAE events | 1,116 |
| ACTOT observed Week 24 ANCOVA subjects | 116 |
| ACTOT LOCF sensitivity subjects | 235 |
| MMRM observed records / subjects | 451 / 189 |

The verified R runtime uses **R 4.6.1**, **mmrm 0.3.18** and **emmeans 2.0.4**.

## Analysis and validation flow

```text
Public DM / EX / DS / AE / QS
        |
        +--> Python derivations --> ADSL-style / ADAE-style / questionnaire analysis data
        |                           |
        |                           +--> safety TLFs
        |                           +--> Week 24 ANCOVA + LOCF sensitivity
        |                           +--> Python QC
        |
        +--> Public CDISC ADaM references --> key / source-row / DTYPE validation
        |
        +--> Separate R reconstruction --> R/Python programming comparison
        |
        +--> Observed ACTOT Week 8/16/24 --> longitudinal MMRM + covariance sensitivity
        |
        +--> Dataset contracts + cross-dataset reviewer --> TLF denominator reconciliation
        |
        +--> SAP/TLF registry --> output contracts --> QC evidence --> SHA256 output identity

Machine-readable protocol-design assumptions
        |
        +--> multiplicity + sample size + dropout inflation + achieved-power back-check
        |
        +--> selected E2.5_P80 scenario (390 randomisations)
                |
                +--> stratified permuted-block randomisation
                +--> blinded / unblinded schedule separation
                +--> treatment-coded initial-kit allocation
                +--> schedule QC + output hashes
```

## Public-reference validation

### CIBIC+

The portfolio derives 705 `ADQSCIBC-style` analysis records from public SDTM `QS` records with `QSTESTCD=CIBIC`.

| Check | Verified result |
|---|---:|
| Analysis-key coverage | **100% (705/705)** |
| `QSSEQ` source-row agreement | **100%** |
| `DTYPE` agreement | **100%** |
| `AVAL` agreement | 98.58% (695/705) |

The ten `AVAL` differences are not overwritten. In all ten cases the portfolio value equals the selected public SDTM QS `QSSTRESN`, while the public reference ADaM value differs from that selected source row. The discrepancy trace is retained in `outputs/adqscibc_mismatch_source_trace.csv`.

### ADQSADAS / ACTOT

The public `ADQSADAS` reference contains 12,463 rows for 254 subjects across 15 ADAS-Cog parameters. The portfolio validates selected ACTOT analysis keys, source `QSSEQ` and `DTYPE` against the public reference while keeping source-derived values visible when source and reference differ.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public raw inputs and does not call the Python derivation code. Python outputs are read only for the final cross-language comparison.

The verified run passes **16/16 required checks**. Safety population counts, TEAE counts, risk-difference outputs, CIBIC selected records, ACTOT derivations and Week 24/LOCF ANCOVA outputs reconcile across the two implementations. The latest maximum R/Python ANCOVA numerical difference is **7.11e-15**.

This remains a separate implementation by the same portfolio author, not review by a second independent programmer.

## ACTOT efficacy analyses

### Week 24 ANCOVA and LOCF sensitivity

```text
Week 24 AVAL = intercept + treatment + centred baseline + error
```

| Analysis | Contrast | Estimate | 95% CI | p-value |
|---|---|---:|---:|---:|
| Observed Week 24 | Low Dose vs Placebo | -2.028 | [-4.596, 0.539] | 0.1204 |
| Observed Week 24 | High Dose vs Placebo | -0.923 | [-3.411, 1.564] | 0.4635 |
| LOCF sensitivity | Low Dose vs Placebo | -1.218 | [-2.830, 0.394] | 0.1378 |
| LOCF sensitivity | High Dose vs Placebo | -1.191 | [-2.921, 0.538] | 0.1760 |

Observed Week 24 uses 116 subjects; the separate LOCF sensitivity uses 235 subjects.

### Longitudinal MMRM

The longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline. LOCF records are not used in the MMRM.

```text
CHG ~ treatment * visit + baseline * visit
```

The primary fit uses REML, unstructured within-subject covariance and Satterthwaite degrees of freedom; heterogeneous AR(1) is a covariance sensitivity analysis. The verified MMRM contains **451 observations from 189 subjects** and passes **11/11 required MMRM QC checks**.

| Week 24 contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are independent portfolio analyses, not the source trial's confirmatory efficacy results.

## Analysis-dataset and TLF reviewer gate

Version 0.9 adds a blocking reviewer layer after the analysis datasets and R MMRM are generated. It is deliberately separate from the derivation code and checks whether generated datasets and TLF-style outputs agree with each other.

The verified run passes **24/24 required reviewer checks** across six review areas: analysis-dataset parentage, derivation consistency, metadata contracts, population consistency, TLF denominator reconciliation and TLF structure. It reviews 17 generated files and records a SHA256 digest for each.

Five machine-readable contracts cover ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM datasets. Each contract specifies keys, required columns, non-missing fields and controlled values. The reviewer additionally requires:

- ADAE treatment, safety flag and treatment dates to reconcile to ADSL-style values;
- ACTOT analysis records to resolve to randomised ADSL-style subjects with matching treatment;
- ACTOT baseline and `CHG = AVAL - BASE` derivations to reconcile;
- every MMRM row to trace to the exact ACTOT source row using `STUDYID + USUBJID + QSSEQ`;
- demographics, disposition and safety TLF denominators to reconcile to ADSL/ADAE populations;
- Week 24 ANCOVA and MMRM output Ns to reconstruct from their analysis datasets;
- MMRM LS-means and active-versus-placebo contrasts to cover the complete planned visit set.

The live reviewer reconstructed randomised/safety arm denominators of **86 Placebo, 96 High Dose and 72 Low Dose**, and observed Week 24 Ns of **30 Placebo, 59 High Dose and 27 Low Dose**, with all linked TLF values reconciling.

Negative-control unit tests deliberately corrupt an ADAE treatment assignment, a safety-table denominator, an MMRM source-derived `CHG`, a required dataset column and a controlled flag. The reviewer/contract validators are required to reject those defects. This is evidence that the checks can fail rather than only reporting conditions that happen to be true in the current outputs.

This layer is same-author portfolio review, not formal ADaM conformance assessment, sponsor programming review or independent second-programmer sign-off.

## Executable SAP-to-TLF traceability

The machine-readable registry covers **15 planned TLFs**. CI requires each TLF to have a planned objective/population/endpoint/method, resolvable source and analysis-dataset links, an actual output file, required columns/minimum rows, linked QC evidence and a SHA256 output identity. The verified v0.9 run retains **15/15** passing structural traceability.

## Protocol design and sample-size exercise

Version 0.7 introduced a machine-readable three-arm planning exercise for Week 24 ACTOT change from baseline. It is explicitly a portfolio scenario rather than the original study design.

Planning assumptions are 1:1:1 allocation, two active-versus-placebo comparisons, two-sided family-wise alpha 0.05, Bonferroni alpha 0.025 per comparison, common planning SD 6.0, 15% anticipated dropout, target power 80%/90% and mean-difference scenarios 2.0/2.5/3.0.

| Scenario | Effect | Power | Evaluable N/arm | Randomised N/arm | Total randomised | Back-checked power |
|---|---:|---:|---:|---:|---:|---:|
| E2.0_P80 | 2.0 | 80% | 172 | 203 | 609 | 0.802 |
| E2.0_P90 | 2.0 | 90% | 224 | 264 | 792 | 0.901 |
| E2.5_P80 | 2.5 | 80% | 110 | 130 | 390 | 0.802 |
| E2.5_P90 | 2.5 | 90% | 143 | 169 | 507 | 0.900 |
| E3.0_P80 | 3.0 | 80% | 77 | 91 | 273 | 0.805 |
| E3.0_P90 | 3.0 | 90% | 100 | 118 | 354 | 0.902 |

The design gate passes **7/7 required checks** including alpha reconciliation, dropout inflation, achieved-power back-checking and effect/power monotonicity.

## Randomisation and initial-kit schedule

Version 0.8 links the illustrative `E2.5_P80` scenario to a reproducible 390-subject stratified permuted-block randomisation and initial-kit schedule. This is a training simulation, not an IRT/IWRS production schedule.

| Schedule property | Verified result |
|---|---:|
| Randomisation numbers | **390** |
| Unique initial-kit codes | **390** |
| Treatment allocation | **130 / 130 / 130** |
| Strata | **5** |
| Allocation within each stratum | **26 / 26 / 26** |
| Permuted blocks | **87** |
| Block-size 3 / block-size 6 | **44 / 43** |
| Required schedule QC | **10/10 passed** |
| Kit-to-treatment mismatches | **0** |

The blinded schedule exposes only `randomisation_id`, `stratum` and `kit_id`; treatment, blind code and block structure remain in unblinded portfolio outputs. Production seed/list access, independent verification, IRT/vendor validation, emergency unblinding and drug-supply operations are outside the claimed scope.

## Safety analysis

The safety population requires at least one observed EX record. The portfolio-defined TEAE window is treatment start through 30 days after treatment end, with documented disposition-date fallback where exposure end is unavailable.

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

These comparisons are exploratory and not multiplicity-adjusted.

## Key reviewer documents

- `docs/protocol_summary.md` — portfolio protocol scope and analysis populations.
- `docs/sap.md` — portfolio SAP through v0.8 analysis/randomisation scope.
- `docs/sap_v0_9_review_addendum.md` — v0.9 controlled addendum for dataset/TLF review.
- `docs/tlf_shells.md` — TLF definitions and output structure.
- `docs/analysis_traceability.md` — executable SAP-to-TLF traceability design.
- `docs/analysis_dataset_spec.md` — source-to-analysis mappings plus v0.9 machine-readable contracts.
- `docs/analysis_dataset_review.md` — v0.9 reviewer rules, negative controls and CI evidence.
- `docs/protocol_statistical_design.md` — protocol-design and sample-size rationale.
- `docs/protocol_statistical_review_checklist.md` — statistical protocol review checklist.
- `docs/randomisation_kit_schedule.md` — randomisation, blinding boundary and initial-kit schedule design/QC.
- `docs/qc_plan.md` — required and informational QC.
- `docs/independent_programming_qc.md` — cross-language QC design.

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript -e 'install.packages(c("jsonlite", "mmrm", "emmeans"))'
Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
python scripts/run_dataset_review.py
python scripts/validate_traceability.py
```

Analysis scripts cache public inputs under `cache/`. GitHub Actions runs the same calculation and QC chain and uploads generated `outputs/` as an artifact, including reviewer diagnostics when available.

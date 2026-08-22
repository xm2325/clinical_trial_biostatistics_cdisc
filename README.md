# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, TLF-style outputs, public-reference validation, separate R/Python programming QC, longitudinal MMRM, executable SAP-to-TLF traceability, and a reproducible protocol-design/sample-size exercise.

> **Evidence boundary:** this is an independent portfolio project. Outputs are labelled `*-style` where they are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS, DSMB, regulatory-submission experience, or validation by an independent second programmer.

## Verified v0.7 live run

The full workflow has been executed in GitHub Actions against downloaded public source data and pinned public CDISC reference files.

| Verification layer | Verified result |
|---|---:|
| Python unit tests | **19/19 passed** |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| SAP-to-TLF structural traceability | **15/15 TLFs passed** |
| Protocol-design/sample-size QC | **7/7 passed** |
| Randomised / safety subjects | 254 / 254 |
| Official CDISC QS rows | 121,749 |
| Portfolio-defined TEAE events | 1,116 |
| ACTOT observed Week 24 ANCOVA subjects | 116 |
| ACTOT LOCF sensitivity subjects | 235 |
| MMRM observed records / subjects | 451 / 189 |

The latest verified R runtime uses **R 4.6.1**, **mmrm 0.3.18** and **emmeans 2.0.4**.

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
        +--> SAP/TLF registry --> output contracts --> QC evidence --> SHA256 output identity

Machine-readable protocol-design assumptions
        |
        +--> family alpha / multiplicity
        +--> sample size / dropout inflation
        +--> achieved-power back-check
        +--> design QC
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

`R/independent_qc.R` begins from the same cached public raw inputs and does not call the Python derivation code. Python outputs are read only for the final cross-language comparison.

The verified run passes **16/16 required checks**. Safety population counts, TEAE counts, risk-difference outputs, CIBIC selected records, ACTOT derivations and Week 24/LOCF ANCOVA outputs reconcile across the two implementations. The latest maximum R/Python ANCOVA numerical difference is **4e-14**.

This remains a separate implementation by the same portfolio author, not review by a second independent programmer.

## ACTOT efficacy analyses

### Week 24 ANCOVA and LOCF sensitivity

The observed-case model is:

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

The primary fit uses REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. Heterogeneous AR(1) is a covariance sensitivity analysis.

The verified MMRM contains **451 observations from 189 subjects** and passes **11/11 required MMRM QC checks**.

| Week 24 contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

| Covariance | AIC | BIC |
|---|---:|---:|
| Unstructured | 2610.627 | 2630.078 |
| Heterogeneous AR(1) | 2627.481 | 2640.448 |

These are independent portfolio analyses, not the source trial's confirmatory efficacy results.

## Executable SAP-to-TLF traceability

Version 0.6 introduced a machine-readable registry covering **15 planned TLFs**. CI verifies, for every TLF:

- planned objective, population, endpoint and statistical method;
- source and analysis-dataset links;
- actual output file existence;
- minimum rows and required output columns;
- linked QC evidence;
- SHA256 identity of the generated output.

The verified v0.7 run retains **15/15** passing output contracts, **15/15** analysis-dataset links and **15/15** QC-evidence links.

## Protocol design and sample-size exercise

Version 0.7 adds a machine-readable three-arm planning exercise for Week 24 ACTOT change from baseline. It is explicitly a portfolio scenario rather than the original study design.

Planning assumptions:

- allocation 1:1:1 across placebo, low dose and high dose;
- two active-versus-placebo comparisons;
- two-sided family-wise alpha 0.05;
- Bonferroni per-comparison alpha 0.025;
- common planning SD 6.0;
- anticipated dropout 15%;
- target power 80% or 90%;
- mean-difference scenarios 2.0, 2.5 or 3.0 points.

Verified calculations are:

| Scenario | Effect | Power | Evaluable N/arm | Randomised N/arm | Total randomised | Back-checked power |
|---|---:|---:|---:|---:|---:|---:|
| E2.0_P80 | 2.0 | 80% | 172 | 203 | 609 | 0.802 |
| E2.0_P90 | 2.0 | 90% | 224 | 264 | 792 | 0.901 |
| E2.5_P80 | 2.5 | 80% | 110 | 130 | 390 | 0.802 |
| E2.5_P90 | 2.5 | 90% | 143 | 169 | 507 | 0.900 |
| E3.0_P80 | 3.0 | 80% | 77 | 91 | 273 | 0.805 |
| E3.0_P90 | 3.0 | 90% | 100 | 118 | 354 | 0.902 |

The design gate passes **7/7 required checks**, including alpha reconciliation, dropout inflation, achieved-power back-checking and monotonicity of required N as effect size or target power changes. The run also records the SHA256 of the exact design specification.

## Safety analysis

The safety population requires at least one observed EX record. The portfolio-defined TEAE window is treatment start through 30 days after treatment end, with documented disposition-date fallback where exposure end is unavailable.

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

These comparisons are exploratory and not multiplicity-adjusted.

## Key reviewer documents

- `docs/protocol_summary.md` — portfolio protocol scope and analysis populations.
- `docs/sap.md` — detailed Statistical Analysis Plan.
- `docs/tlf_shells.md` — TLF definitions and output structure.
- `docs/analysis_traceability.md` — executable SAP-to-TLF traceability design.
- `docs/protocol_statistical_design.md` — protocol-design and sample-size rationale.
- `docs/protocol_statistical_review_checklist.md` — statistical protocol review/sign-off checklist.
- `docs/analysis_dataset_spec.md` — source-to-analysis variable mapping.
- `docs/qc_plan.md` — required and informational QC.
- `docs/independent_programming_qc.md` — cross-language QC design.

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_protocol_design.py

Rscript -e 'install.packages(c("jsonlite", "mmrm", "emmeans"))'
Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
python scripts/validate_traceability.py
```

Analysis scripts cache public inputs under `cache/`. GitHub Actions runs the same calculation and QC chain and uploads generated `outputs/` as an artifact, including diagnostic files when available.

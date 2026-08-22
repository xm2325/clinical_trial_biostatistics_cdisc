# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial statistics work sample using public CDISC pilot data and public pharmaverse SDTM test data.

The project demonstrates source-to-analysis traceability, analysis populations, safety and questionnaire efficacy derivations, statistical analysis, TLF-style outputs, QC, provenance tracking, comparison with official CDISC reference ADaM datasets, and a separate R implementation used for cross-language programming QC.

> **Evidence boundary:** this is an independent portfolio project. Portfolio outputs are labelled `*-style` where they are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS, DSMB, regulatory-submission experience, or independent validation by a second programmer.

## Verified v0.4 live run

The complete workflow has been run in GitHub Actions against downloaded public source data and pinned official CDISC reference files.

| Item | Verified result |
|---|---:|
| DM rows | 306 |
| AE rows | 1,191 |
| DS rows | 850 |
| EX rows | 591 |
| Official CDISC QS rows | 121,749 |
| Official ADQSCIBC rows | 730 |
| Official ADQSADAS rows | 12,463 |
| Official ADQSADAS subjects | 254 |
| ADQSADAS parameters | 15 |
| ACTOT reference rows | 1,040 |
| ACTOT selected `ANL01FL=Y` rows | 1,016 |
| Randomised subjects | 254 |
| Safety subjects | 254 |
| Subjects with >=1 portfolio-defined TEAE | 217 |
| Portfolio-defined TEAE events | 1,116 |
| Required Python pipeline QC | **24 / 24 passed** |
| Python unit tests | **10 / 10 passed** |
| Required R/Python cross-language checks | **16 / 16 passed** |
| Maximum R/Python ANCOVA numeric difference | **7.11e-15** |

## Independent R programming QC

Version 0.4 adds `R/independent_qc.R`. The R program starts from the same cached public DM, EX, DS, AE and official QS inputs, but does not call Python derivation functions. It independently rebuilds the selected safety and efficacy results and reads Python outputs only for the final comparison.

The verified GitHub Actions run uses **R 4.6.1** and **jsonlite 2.0.0**. All 16 required cross-language checks pass:

| Independent R check | Verified result |
|---|---:|
| Randomised subjects | 254 = Python 254 |
| Safety subjects | 254 = Python 254 |
| Completed subjects | 110 = Python 110 |
| Subjects with TEAE | 217 = Python 217 |
| TEAE events | 1,116 = Python 1,116 |
| DS exposure-end fallbacks | 2 = Python 2 |
| Any-TEAE risk-difference table | exact; max numeric difference 0 |
| CIBIC selected analysis keys | 705 = Python 705 |
| CIBIC `QSSEQ` | exact |
| CIBIC `DTYPE` | exact |
| CIBIC source-derived `AVAL` | exact |
| ACTOT source-row keys | 818 = Python 818 |
| ACTOT `AVAL` / `BASE` / `CHG` | exact |
| ACTOT baseline / efficacy flags | exact |
| ANCOVA contrast keys / N / df | exact |
| ANCOVA estimates / SE / CI / p | max numeric difference **7.11e-15** |

The CI also performs an R syntax parse before package installation and analysis. Any required cross-language discrepancy makes the R QC step fail. `r_session_info.txt`, `r_metrics.json`, the R-derived statistical outputs and the complete check table are retained in the workflow artifact.

This is a separate implementation in a second language, not a claim that a second human programmer independently reviewed the work. The exact derivation rules and acceptance criteria are documented in `docs/independent_programming_qc.md`.

### Official-reference validation

For CIBIC+, the portfolio derives 705 `ADQSCIBC-style` analysis rows from official SDTM `QS` records with `QSTESTCD=CIBIC`. Against the official CDISC `ADQSCIBC` analysis records, the live run obtains:

| Check | Result |
|---|---:|
| Analysis-key coverage | **100% (705/705)** |
| `QSSEQ` source-row agreement | **100%** |
| `DTYPE` agreement | **100%** |
| `AVAL` agreement | 98.58% (695/705) |

The ten `AVAL` differences are not hidden or overwritten. For all ten, the portfolio value equals the selected official SDTM QS `QSSTRESN`, while the official reference ADaM value differs from that source row. `outputs/adqscibc_mismatch_source_trace.csv` records subject, analysis visit, source `QSSEQ`, source text/value, derived value and reference value.

This distinction matters for QC: exact agreement is required on which source record was selected and how the analysis record was classified, while reference-value agreement is reported separately when the public source and public reference disagree.

The official `ADQSADAS` dataset is used as a second validation source. It contains 12,463 rows across 15 ADAS-Cog parameters, including 1,040 `ACTOT` records. The selected `ACTOT` analysis structure contains 1,016 `ANL01FL=Y` rows: baseline plus Week 8, Week 16 and Week 24 analysis records for 254 subjects. The portfolio reproduces those selected keys, `QSSEQ` source rows and `DTYPE` classifications at 100%; value differences are retained as diagnostic evidence rather than changed to match the reference.

## Analysis flow

```text
Public source data

DM + EX + DS ───────────────> Python ADSL-style ──┐
AE ─────────────────────────> Python ADAE-style ──┼─> safety TLFs + TEAE analyses
                                                    │
Official QS ── CIBIC ───────> Python ADQSCIBC-style│
            └─ ACTOT ───────> baseline/change ─────┼─> Week 24 ANCOVA + LOCF
                                                    │
                                                    └─> Python QC + reference validation

Same raw DM / EX / DS / AE / QS
            └────────────────> independent R reconstruction
                                  ├─ populations / TEAE / risk differences
                                  ├─ CIBIC selected records
                                  ├─ ACTOT baseline/change
                                  └─ Week 24 + LOCF ANCOVA
                                             │
                                             └─> final R/Python comparison
```

## Efficacy analysis

The main continuous portfolio endpoint is `ACTOT`, labelled by the official reference as **Adas-Cog(11) Subscore**. The source QS baseline flag defines `BASE`; post-baseline change is `CHG = AVAL - BASE`.

The observed Week 24 model is:

```text
Week24 AVAL = intercept + treatment + centred baseline + error
```

Placebo is the reference arm. The live run includes 116 subjects with an observed Week 24 value. A separate LOCF sensitivity analysis includes 235 subjects.

| Analysis | Contrast | Estimate | 95% CI | p-value |
|---|---|---:|---:|---:|
| Observed Week 24 | Xanomeline Low Dose vs Placebo | -2.028 | [-4.596, 0.539] | 0.1204 |
| Observed Week 24 | Xanomeline High Dose vs Placebo | -0.923 | [-3.411, 1.564] | 0.4635 |
| LOCF sensitivity | Xanomeline Low Dose vs Placebo | -1.218 | [-2.830, 0.394] | 0.1378 |
| LOCF sensitivity | Xanomeline High Dose vs Placebo | -1.191 | [-2.921, 0.538] | 0.1760 |

The R implementation reproduces all four contrasts, their sample sizes and residual degrees of freedom exactly; the largest numeric difference across estimates, standard errors, confidence limits, p-values and baseline reference values is `7.11e-15`.

These are independent portfolio analyses. They are not presented as the original trial's confirmatory efficacy results.

## Safety analysis

The portfolio safety definition uses at least one observed EX record for the safety population and a TEAE window from treatment start through 30 days after treatment end. Two safety subjects require a documented DS disposition-date fallback for treatment end; this remains visible through `TRTEDTSRC=DS_DISPOSITION_FALLBACK`.

Exploratory subject-level any-TEAE comparisons are:

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Xanomeline Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| Xanomeline High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

The independent R implementation reproduces every value in this table exactly at the reported precision. No multiplicity correction is applied to these exploratory comparisons.

## Key outputs

```text
outputs/
  adsl_style.csv
  adae_style.csv
  adqscibc_style.csv
  adqs_actot_style.csv
  adqscibc_reference_metrics.csv
  adqscibc_reference_detail.csv
  adqscibc_mismatch_source_trace.csv
  adqsadas_reference_profile.json
  adqsadas_param_counts.csv
  adqsadas_actot_reference_counts.csv
  adqsadas_actot_analysis_style.csv
  adqsadas_actot_comparison_metrics.csv
  table1_demographics.csv
  ...
  table7_teae_risk_difference.csv
  table8_actot_descriptive.csv
  table9_actot_lsmeans.csv
  table10_actot_ancova_contrasts.csv
  r_independent_qc.csv
  r_metrics.json
  r_session_info.txt
  r_independent_qc_summary.md
  r_teae_risk_difference.csv
  r_actot_ancova_contrasts.csv
  qc_report.csv
  metrics.json
  manifest.json
  analysis_run_note.md
```

`manifest.json` records pinned source URLs and SHA256 hashes. Reference diagnostic outputs are created before the main analysis, so a failed analysis still leaves enough evidence to locate the discrepancy.

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
Rscript -e 'install.packages("jsonlite")'
Rscript R/independent_qc.R
```

The Python unit tests do not require network access. The analysis scripts download public inputs on first use and cache them in `cache/`. The R QC program then uses those cached raw inputs.

## Repository structure

```text
docs/
  protocol_summary.md
  sap.md
  tlf_shells.md
  data_provenance.md
  analysis_dataset_spec.md
  qc_plan.md
  independent_programming_qc.md
R/
  independent_qc.R
src/cdisc_portfolio/
  io.py
  derive.py
  analysis.py
  efficacy.py
  adas.py
  reference.py
  qc.py
  efficacy_qc.py
  sample_size.py
  pipeline.py
scripts/
  profile_official_references.py
  run_all.py
tests/
.github/workflows/run.yml
```

See `docs/sap.md` for analysis rules, `docs/analysis_dataset_spec.md` for source-to-derived-variable mapping, `docs/qc_plan.md` for required and informational QC checks, and `docs/independent_programming_qc.md` for the cross-language validation design.

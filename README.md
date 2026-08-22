# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial statistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The project demonstrates source-to-analysis traceability, analysis-population derivation, safety and questionnaire-efficacy analyses, TLF-style outputs, official-reference validation, independent R/Python programming QC, and longitudinal repeated-measures modelling.

> **Evidence boundary:** this is an independent portfolio project. Portfolio outputs are labelled `*-style` where they are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS, DSMB, regulatory-submission experience, or independent validation by a second programmer.

## Verified v0.5 live run

The complete workflow has been executed in GitHub Actions against downloaded public source data and pinned official CDISC reference files.

| Item | Verified result |
|---|---:|
| DM rows | 306 |
| AE rows | 1,191 |
| DS rows | 850 |
| EX rows | 591 |
| Official CDISC QS rows | 121,749 |
| Official ADQSCIBC rows | 730 |
| Official ADQSADAS rows | 12,463 |
| Randomised / safety subjects | 254 / 254 |
| Subjects with >=1 portfolio-defined TEAE | 217 |
| Portfolio-defined TEAE events | 1,116 |
| Python unit tests | **10 / 10 passed** |
| Required Python pipeline QC | **24 / 24 passed** |
| Required R/Python cross-language QC | **16 / 16 passed** |
| Maximum R/Python ANCOVA numeric difference | **7.11e-15** |
| MMRM observed post-baseline records | 451 |
| MMRM subjects | 189 |
| MMRM visit records | Week 8=189; Week 16=146; Week 24=116 |
| Required MMRM QC | **11 / 11 passed** |

The verified R runtime is **R 4.6.1** with **mmrm 0.3.18** and **emmeans 2.0.4**.

## Analysis flow

```text
Public source data

DM + EX + DS ───────────────> Python ADSL-style ──┐
AE ─────────────────────────> Python ADAE-style ──┼─> safety TLFs + TEAE analyses
                                                    │
Official QS ── CIBIC ───────> Python ADQSCIBC-style│
            └─ ACTOT ───────> baseline/change ─────┼─> Week 24 ANCOVA + LOCF sensitivity
                                                    │
                                                    └─> Python QC + official-reference validation

Same raw DM / EX / DS / AE / QS
            └────────────────> independent R reconstruction
                                  ├─ populations / TEAE / risk differences
                                  ├─ CIBIC selected records
                                  ├─ ACTOT baseline/change
                                  └─ Week 24 + LOCF ANCOVA
                                             │
                                             └─> final R/Python comparison

Observed ACTOT Week 8 / 16 / 24
            └────────────────> R MMRM
                                  ├─ unstructured covariance (primary)
                                  ├─ heterogeneous AR(1) covariance sensitivity
                                  ├─ visit-specific LS means / contrasts
                                  └─ MMRM QC + Week 24 ANCOVA comparison
```

## Official CDISC reference validation

### CIBIC+

The portfolio derives 705 `ADQSCIBC-style` analysis records from official SDTM `QS` records with `QSTESTCD=CIBIC`.

| Check | Verified result |
|---|---:|
| Analysis-key coverage | **100% (705/705)** |
| `QSSEQ` source-row agreement | **100%** |
| `DTYPE` agreement | **100%** |
| `AVAL` agreement | 98.58% (695/705) |

The ten `AVAL` differences are retained rather than overwritten. For all ten, the portfolio value equals the selected official SDTM QS `QSSTRESN`, while the public reference ADaM value differs from that selected source record. `outputs/adqscibc_mismatch_source_trace.csv` preserves the complete source trace.

### ADQSADAS / ACTOT

The official `ADQSADAS` reference contains 12,463 rows for 254 subjects across 15 ADAS-Cog parameters. `ACTOT` contains 1,040 rows. The official selected structure contains 1,016 `ANL01FL=Y` ACTOT rows. The portfolio reproduces selected analysis keys, source `QSSEQ` and `DTYPE` at 100% agreement. Value differences remain diagnostic evidence and are not changed simply to force a reference match.

## Independent R programming QC

`R/independent_qc.R` begins from the same cached public DM, EX, DS, AE and official QS inputs but does not call Python derivation functions. Python outputs are read only at the final comparison step.

The verified run passes **16/16 required cross-language checks**. It independently reproduces:

| Check | Verified result |
|---|---:|
| Randomised subjects | 254 = Python 254 |
| Safety subjects | 254 = Python 254 |
| Completed subjects | 110 = Python 110 |
| Subjects with TEAE | 217 = Python 217 |
| TEAE events | 1,116 = Python 1,116 |
| DS exposure-end fallbacks | 2 = Python 2 |
| Any-TEAE risk-difference table | exact; maximum numeric difference 0 |
| CIBIC selected rows | 705 = Python 705 |
| CIBIC key / `QSSEQ` / `DTYPE` / source-derived `AVAL` | exact |
| ACTOT source rows | 818 = Python 818 |
| ACTOT `AVAL` / `BASE` / `CHG` / flags | exact |
| Week 24 / LOCF ANCOVA N and df | exact |
| ANCOVA estimates / SE / CI / p-values | maximum numeric difference **7.11e-15** |

This is a separate implementation by the same portfolio author, not independent review by a second programmer.

## ACTOT efficacy analyses

`ACTOT` is labelled in the public reference as **Adas-Cog(11) Subscore**. `BASE` is taken from the baseline-flagged source ACTOT record and post-baseline `CHG = AVAL - BASE`.

### Week 24 ANCOVA and LOCF sensitivity

The observed-case ANCOVA uses:

```text
Week 24 AVAL = intercept + treatment + centred baseline + error
```

| Analysis | Contrast | Estimate | 95% CI | p-value |
|---|---|---:|---:|---:|
| Observed Week 24 | Xanomeline Low Dose vs Placebo | -2.028 | [-4.596, 0.539] | 0.1204 |
| Observed Week 24 | Xanomeline High Dose vs Placebo | -0.923 | [-3.411, 1.564] | 0.4635 |
| LOCF sensitivity | Xanomeline Low Dose vs Placebo | -1.218 | [-2.830, 0.394] | 0.1378 |
| LOCF sensitivity | Xanomeline High Dose vs Placebo | -1.191 | [-2.921, 0.538] | 0.1760 |

Observed Week 24 uses 116 subjects. The separate LOCF sensitivity uses 235 subjects.

### Longitudinal MMRM

Version 0.5 adds an observed-data MMRM for Week 8, Week 16 and Week 24 ACTOT change from baseline. **LOCF rows do not enter this model.**

The fixed-effects specification is:

```text
CHG ~ treatment * visit + baseline * visit
```

The primary fit uses REML, an unstructured within-subject covariance matrix and Satterthwaite degrees of freedom. A heterogeneous AR(1) fit with the same fixed-effects model is reported as covariance sensitivity.

The live run contains **451 observations from 189 subjects**: Week 8=189, Week 16=146 and Week 24=116. All **11/11 required MMRM QC checks pass**, including unique subject-visit keys, exact `CHG=AVAL-BASE`, constant subject baseline, finite model likelihoods, finite inference and the expected six active-versus-placebo visit contrasts.

Primary unstructured-covariance contrasts are:

| Visit | Contrast | Estimate | SE | 95% CI | df | p-value |
|---|---|---:|---:|---:|---:|---:|
| Week 8 | Low Dose vs Placebo | 1.2143 | 0.7294 | [-0.2247, 2.6532] | 185.00 | 0.0976 |
| Week 8 | High Dose vs Placebo | 0.1978 | 0.7480 | [-1.2780, 1.6736] | 185.00 | 0.7917 |
| Week 16 | Low Dose vs Placebo | -0.4412 | 1.0105 | [-2.4370, 1.5546] | 159.38 | 0.6630 |
| Week 16 | High Dose vs Placebo | -0.4551 | 1.0457 | [-2.5202, 1.6100] | 160.01 | 0.6640 |
| Week 24 | Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 142.05 | 0.1693 |
| Week 24 | High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 139.44 | 0.4220 |

Model diagnostics are:

| Covariance | logLik | AIC | BIC |
|---|---:|---:|---:|
| Unstructured | -1299.314 | 2610.627 | 2630.078 |
| Heterogeneous AR(1) | -1309.740 | 2627.481 | 2640.448 |

For this dataset the unstructured fit has lower AIC/BIC. That is reported as a fit diagnostic, not as a general claim that it is the correct covariance model for other studies.

At Week 24, the longitudinal MMRM estimates are close to the observed-case ANCOVA for High Dose (-0.9271 vs -0.9234) and differ more for Low Dose (-1.6131 vs -2.0283), reflecting the additional longitudinal information used by the MMRM. The two analyses are kept separate rather than forced to agree.

These are independent portfolio analyses and are not presented as the original trial's confirmatory efficacy results.

## Safety analysis

The safety population requires at least one observed EX record. The portfolio-defined TEAE window is treatment start through 30 days after treatment end. Two safety subjects require a documented DS disposition-date fallback for treatment end; this remains visible in `TRTEDTSRC`.

Exploratory any-TEAE comparisons are:

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Xanomeline Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| Xanomeline High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

No multiplicity correction is applied to these exploratory comparisons.

## Key outputs

```text
outputs/
  adsl_style.csv
  adae_style.csv
  adqscibc_style.csv
  adqs_actot_style.csv
  adqscibc_reference_metrics.csv
  adqscibc_mismatch_source_trace.csv
  adqsadas_reference_profile.json
  table1_demographics.csv
  ...
  table10_actot_ancova_contrasts.csv
  r_independent_qc.csv
  r_metrics.json
  r_session_info.txt
  r_actot_ancova_contrasts.csv
  mmrm_analysis_dataset.csv
  mmrm_visit_counts.csv
  mmrm_model_diagnostics.csv
  mmrm_lsmeans.csv
  mmrm_treatment_contrasts.csv
  mmrm_covariance_sensitivity.csv
  mmrm_vs_week24_ancova.csv
  mmrm_qc.csv
  mmrm_metrics.json
  mmrm_model_summary.txt
  mmrm_run_summary.md
  qc_report.csv
  metrics.json
  manifest.json
  analysis_run_note.md
```

`manifest.json` records pinned source URLs and SHA256 hashes. Diagnostic outputs are retained even when a required downstream step fails, so source/reference or model failures remain inspectable.

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py

Rscript -e 'install.packages(c("jsonlite", "mmrm", "emmeans"))'
Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
```

The Python unit tests do not require network access. Analysis scripts download public inputs on first use and cache them in `cache/`; R then uses the cached inputs and Python analysis products as documented above.

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
  mmrm_analysis.R
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

See `docs/sap.md` for analysis rules, `docs/analysis_dataset_spec.md` for source-to-derived-variable mapping, `docs/tlf_shells.md` for planned output structure, `docs/qc_plan.md` for required and informational checks, and `docs/independent_programming_qc.md` for the cross-language validation design.

# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial statistics workflow built on public SDTM test data from `pharmaverse/pharmaversesdtm`.

The project is designed as a **work sample for clinical biostatistics / statistical programming roles**. It demonstrates traceability from SDTM source domains through analysis-ready datasets, pre-specified safety analyses, TLF-style outputs, inferential summaries, QC and provenance tracking.

> **Evidence boundary:** this is an independent portfolio project. The derived datasets are labelled **ADSL-style** and **ADAE-style** because they are not claimed to be fully CDISC-conformant ADaM submission datasets. The repository does not claim sponsor/CRO production, SAS, DSMB or regulatory-submission experience.

## Verified v0.2 live run

The full workflow has been run in GitHub Actions against the public source CSVs, not only against local fixtures.

| Item | Verified result |
|---|---:|
| DM rows | 306 |
| AE rows | 1,191 |
| DS rows | 850 |
| EX rows | 591 |
| Randomised subjects | 254 |
| Safety-population subjects | 254 |
| Completed subjects | 110 |
| Subjects with >=1 portfolio-defined TEAE | 217 |
| Portfolio-defined TEAE events | 1,116 |
| Exposure-end fallbacks | 2 / 254 |
| Required QC checks | **13 / 13 passed** |
| Unit tests | **6 / 6 passed** |

Two safety subjects had observed EX records but no usable EX/DM exposure-end date. v0.2 therefore uses the final DS disposition date as a documented fallback for those two subjects and records `TRTEDTSRC=DS_DISPOSITION_FALLBACK`. Raw EX duration remains separate from the final treatment-window duration so the source-data limitation stays visible.

### Exploratory any-TEAE comparisons

These are **unadjusted portfolio analyses**, not confirmatory results for the source trial.

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Xanomeline Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| Xanomeline High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

The confidence interval and Fisher p-value use different inferential procedures, so their threshold behaviour does not have to match exactly. No multiplicity correction is applied.

## What v0.2 adds

v0.2 moves beyond the initial DM/AE-only workflow:

- uses **EX** records to define observed exposure and the safety population;
- uses **DS** records to derive randomisation, completion and discontinuation status;
- retains DM dates and explicit treatment-date source flags for traceability;
- separates raw EX duration (`EXDURN_RAW`) from final treatment-window duration (`TRTDURN`);
- derives ADSL-style and ADAE-style datasets with treatment-emergent, related and moderate/severe flags;
- produces demographics, disposition, exposure and safety TLF-style tables;
- adds subject-level any-TEAE **risk differences vs placebo with 95% confidence intervals and Fisher exact p-values** as an exploratory analysis;
- runs required QC checks on keys, populations, dates, referential integrity and the TEAE window;
- writes SHA256 hashes for downloaded inputs and generated core outputs;
- runs the complete public-data workflow in GitHub Actions and uploads all outputs as a workflow artifact.

## Analysis flow

```text
Public SDTM test data
  DM ───────────────┐
  EX ── exposure ───┼──> ADSL-style ───────────────┐
  DS ─ disposition ─┘                               │
                                                   ├──> TLF-style outputs
  AE ───────────────────────> ADAE-style ──────────┤
                                                   ├──> exploratory TEAE risk differences
                                                   └──> QC + provenance manifest
```

## Pre-specified portfolio definitions

**Randomised population:** `DSDECOD == RANDOMIZED` is observed in DS.

**Safety population:** at least one EX record is observed for the subject.

**Treatment start:** first non-missing `EXSTDTC`, with DM `RFXSTDTC` retained as a documented fallback.

**Treatment end:** last non-missing `EXENDTC`; if unavailable, DM `RFXENDTC`; if both are unavailable, final DS disposition date. `TRTSDTSRC` and `TRTEDTSRC` preserve the selected source.

**Treatment-emergent adverse event (TEAE):** AE start date on/after treatment start and no later than 30 days after treatment end, inclusive.

**Related TEAE:** portfolio flag for `AEREL` in `POSSIBLE`, `PROBABLE`, `DEFINITE`, or `RELATED`.

These are explicit portfolio assumptions and are not presented as the original pilot protocol's rules.

## Outputs

Running the workflow creates:

```text
outputs/
  adsl_style.csv
  adae_style.csv
  table1_demographics.csv
  table2_disposition.csv
  table3_exposure.csv
  table4_teae_overview.csv
  table5_teae_soc_pt.csv
  table6_teae_severity.csv
  table7_teae_risk_difference.csv
  qc_report.csv
  sample_size_examples.json
  metrics.json
  manifest.json
  analysis_run_note.md
```

`metrics.json` contains machine-readable run counts and QC status. `manifest.json` records source URLs, SHA256 input/output hashes and analysis version.

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/run_all.py
```

The unit-test suite does not require network access. The analysis run downloads the four public CSV inputs on first use and caches them in `cache/`.

## Repository structure

```text
docs/
  protocol_summary.md
  sap.md
  tlf_shells.md
  data_provenance.md
  analysis_dataset_spec.md
  qc_plan.md
src/cdisc_portfolio/
  io.py
  derive.py
  analysis.py
  qc.py
  sample_size.py
  pipeline.py
scripts/run_all.py
tests/
.github/workflows/run.yml
```

## Why this is a biostatistics work sample

The statistical model is intentionally simple. The work sample focuses on tasks that matter in a clinical-trial workflow: converting an analysis rule into explicit derivations, keeping source-to-analysis traceability, defining analysis populations, producing reproducible tables, quantifying uncertainty, separating descriptive from inferential outputs, and checking derived results against pre-specified QC rules.

See `docs/sap.md` for the analysis specification, `docs/analysis_dataset_spec.md` for source-to-derived-variable traceability, and `docs/qc_plan.md` for required versus informational checks.

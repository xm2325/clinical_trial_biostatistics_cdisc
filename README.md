# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial statistics workflow built on public SDTM test data from `pharmaverse/pharmaversesdtm`.

The project is designed as a **work sample for clinical biostatistics / statistical programming roles**. It demonstrates traceability from SDTM source domains through analysis-ready datasets, pre-specified safety analyses, TLF-style outputs, inferential summaries, QC and provenance tracking.

> **Evidence boundary:** this is an independent portfolio project. The derived datasets are labelled **ADSL-style** and **ADAE-style** because they are not claimed to be fully CDISC-conformant ADaM submission datasets. The repository does not claim sponsor/CRO production, SAS, DSMB or regulatory-submission experience.

## What v0.2 adds

v0.2 moves beyond the initial DM/AE-only workflow:

- uses **EX** records to define observed exposure and the safety population;
- uses **DS** records to derive randomisation, completion and discontinuation status;
- keeps DM exposure dates alongside EX-derived dates for traceability and QC;
- derives ADSL-style and ADAE-style datasets with explicit treatment-emergent, related and moderate/severe flags;
- produces demographics, disposition, exposure and safety TLF-style tables;
- adds subject-level any-TEAE **risk differences vs placebo with 95% confidence intervals and Fisher exact p-values** as an exploratory analysis;
- runs required QC checks on keys, populations, dates, referential integrity and the TEAE window;
- writes SHA256 hashes for all downloaded inputs and analysis outputs;
- runs the complete public-data workflow in GitHub Actions and uploads all outputs as a workflow artifact.

## Analysis flow

```text
Public SDTM test data
  DM ───────────────┐
  EX ── exposure ───┼──> ADSL-style ───────────────┐
  DS ─ disposition ─┘                               │
                                                   ├──> TLF-style outputs
  AE ───────────────────────> ADAE-style ──────────┤
                                                   ├──> TEAE risk differences
                                                   └──> QC + provenance manifest
```

## Pre-specified portfolio definitions

**Randomised population:** `DSDECOD == RANDOMIZED` is observed in DS.

**Safety population:** at least one EX record is observed for the subject.

**Actual exposure window:** first `EXSTDTC` through last `EXENDTC`. DM `RFXSTDTC/RFXENDTC` are retained for comparison but EX drives the portfolio safety window when available.

**Treatment-emergent adverse event (TEAE):** AE start date on/after first observed exposure and no later than 30 days after last observed exposure, inclusive.

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

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/run_all.py
```

The local unit-test suite does not require network access. The analysis run downloads the four public CSV inputs on first use and caches them in `cache/`.

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

The statistical model is intentionally simple. The work sample focuses on tasks that matter in a clinical-trial workflow: converting a protocol-level rule into explicit derivations, keeping source-to-analysis traceability, defining analysis populations, producing reproducible tables, quantifying uncertainty, separating descriptive from inferential outputs, and checking every derived result against pre-specified QC rules.

See `docs/sap.md` for the analysis specification and `docs/analysis_dataset_spec.md` for source-to-derived-variable traceability.

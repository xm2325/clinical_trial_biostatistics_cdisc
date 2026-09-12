# Real-data medical-device RCT analysis in R

A focused statistical work sample for a short-cycle medical-device study: **patient-level data -> data quality review -> statistical analysis in R -> sensitivity analysis -> figures/tables -> internal study brief -> optional dashboard**.

## Question

Can a clinical team turn a patient-level randomized medical-device dataset into a reproducible, reviewable analysis package without silently changing source data or overstating what the data support?

This case study uses a **real randomized comparison of two laryngoscopes**: the Pentax AWS video laryngoscope versus the standard Macintosh #4 laryngoscope in adults requiring elective orotracheal intubation. The public teaching release contains **99 patients and 22 study variables**. The original publication reports 105 randomized patients, so this repository treats the 99-row teaching release as its own analysis source and does **not** claim an exact reproduction of the published trial.

## Why this dataset

The work sample is intentionally close to the delivery pattern of a medical-device Statistical Data Scientist role:

- organize and validate patient-level study data;
- program the analysis in **R**;
- compare randomized device groups using binary and continuous clinical outcomes;
- make missingness, structural missing values and source-definition questions explicit;
- create analysis-ready tables and figures;
- produce a short report for internal stakeholders;
- expose the same outputs in a small **Shiny** dashboard.

It is not a machine-learning prediction exercise.

## Data source and evidence boundary

The data are redistributed through the `medicaldata` / Rdatasets teaching collection and originate from the TSHS Resources Portal dataset contributed by Amy S. Nowacki, Cleveland Clinic.

Original study:

> Abdallah R, Galway U, You J, Kurz A, Sessler DI, Doyle DJ. *A Randomized Comparison Between the Pentax AWS Video Laryngoscope and the Macintosh Laryngoscope in Morbidly Obese Patients.* Anesthesia & Analgesia. 2011;113(5):1082-1087. DOI: 10.1213/ANE.0b013e31822cf47d.

Public CSV used by the pipeline:

`https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/medicaldata/laryngoscope.csv`

Documentation:

`https://search.r-project.org/CRAN/refmans/medicaldata/html/laryngoscope.html`

TSHS data-use statement:

`https://www.causeweb.org/tshs/`

**Boundary:** TSHS states that its datasets may have been modified for de-identification, that inferences beyond the original study purpose should not be presented as valid estimates, and that publication use requires permission from the source. This repository is therefore an **educational/portfolio re-analysis**, not new clinical evidence, a regulatory analysis, or a publication-ready claim about device effectiveness.

The raw CSV is downloaded at run time and is not committed to this repository. The pipeline records source URL, retrieval time and MD5 checksum.

## Analysis contract

The analysis is specified before model output is inspected in `spec/analysis_plan.md`.

Main comparisons use randomized device assignment:

1. **First-attempt intubation success**: absolute risk difference, risk ratio and Fisher exact test.
2. **Total intubation time**: group medians, median difference with seeded bootstrap 95% interval, and Wilcoxon rank-sum test.
3. Supportive outcomes: overall success, repeated attempts, bleeding, postoperative sore throat and ease of intubation.

Baseline variables are summarized descriptively. Because this is a randomized comparison, baseline significance testing is not used as a gate for whether the treatment comparison is allowed.

A covariate-adjusted log-time model is included only as a **sensitivity analysis**. With the available sample size and small number of first-attempt failures, a large adjusted logistic model for success would be unstable and is not used as the main result.

## Data-quality decisions that are deliberately visible

The pipeline separates ordinary missingness from structural missingness. Attempt-2 and attempt-3 fields are expected to be empty when no later attempt was needed.

Two source issues are not silently repaired:

- the public data dictionary describes the `view` coding in a way that is internally hard to reconcile with the usual clinical interpretation of Cormack-Lehane grades. The variable is retained as a raw source code but excluded from clinically labelled inferential conclusions;
- the pipeline checks whether any first-attempt time exceeds the supplied total-intubation-time value. Such rows are surfaced for source clarification rather than overwritten.

This is intentional: a short contract should still leave an auditable trail of what was changed, what was not changed and why.

## Repository layout

```text
medical_device_rct_real_data/
├── README.md
├── run_all.R
├── .gitignore
├── R/
│   ├── 00_config.R
│   ├── 01_prepare_data.R
│   ├── 02_analysis.R
│   └── 03_outputs.R
├── spec/
│   └── analysis_plan.md
├── tests/
│   └── check_outputs.R
├── dashboard/
│   └── app.R
├── data/                 # created locally; raw data are ignored by git
└── outputs/              # generated tables, figures and reports
```

## Run

From this folder:

```bash
Rscript run_all.R
Rscript tests/check_outputs.R
```

The analysis itself uses base R so that the core pipeline has no external R-package dependency.

For the optional dashboard:

```r
install.packages("shiny")
shiny::runApp("dashboard")
```

Run `Rscript run_all.R` first so the dashboard can read the generated outputs.

## Generated outputs

The pipeline creates:

- `outputs/data_provenance.csv`
- `outputs/missingness.csv`
- `outputs/qc_findings.csv`
- `outputs/baseline_table.csv`
- `outputs/binary_outcomes.csv`
- `outputs/continuous_outcomes.csv`
- `outputs/sensitivity_analysis.csv`
- `outputs/analysis_summary.md`
- `outputs/stakeholder_brief.md`
- `outputs/figures/first_attempt_success.png`
- `outputs/figures/total_intubation_time.png`
- `outputs/figures/missingness.png`

The GitHub Actions workflow reruns the analysis from the public source, executes output checks, prints the study summary and uploads the generated outputs as an artifact.

## What this work sample demonstrates

The important result is not whether one device wins. The work sample demonstrates that I can take a real patient-level device study, define the analysis boundary, check the source data, write reproducible R code, quantify uncertainty, preserve questionable source fields rather than silently fixing them, and produce outputs that a clinical/statistical team can review quickly.

# Real-data medical-device RCT analysis in R

A focused statistical work sample for a short-cycle medical-device study: **patient-level data -> data quality review -> statistical analysis in R -> sensitivity analysis -> figures/tables -> internal study brief -> reproducible handoff**.

## Start here: 2-minute review

For a short review, open [`CASE_STUDY_ONE_PAGER.md`](CASE_STUDY_ONE_PAGER.md). It gives the study -> data -> QC -> analysis -> decision path, the main estimates, the open source questions and the evidence boundary on one page.

For the practical contract-delivery view, open [`DAY5_HANDOFF.md`](DAY5_HANDOFF.md). It shows what would be handed to a clinical/statistical study team at the end of the first five working days.

## Question

Can a clinical team turn a patient-level randomized medical-device dataset into a reproducible, reviewable analysis package without silently changing source data or overstating what the data support?

This case study uses a **real randomized comparison of two laryngoscopes**: the Pentax AWS video laryngoscope versus the standard Macintosh #4 laryngoscope in adults requiring elective orotracheal intubation. The public teaching release contains **99 patients and 22 study variables**. The original publication reports 105 randomized patients, so this repository treats the 99-row teaching release as its own analysis source and does **not** claim an exact reproduction of the published trial.

## What the current run shows

| Outcome | Pentax AWS | Macintosh #4 | Contrast |
| --- | ---: | ---: | --- |
| First-attempt success | 43/50 (86.0%) | 45/49 (91.8%) | risk difference -5.8 percentage points; 95% Newcombe interval -19.0 to 7.2; Fisher p=0.5246 |
| Overall success | 46/50 (92.0%) | 49/49 (100.0%) | Fisher p=0.1175 |
| More than one attempt | 6/50 (12.0%) | 4/49 (8.2%) | Fisher p=0.7407 |
| Total intubation time | median 38.1 s [31.0, 50.1] | median 26.0 s [21.9, 29.4] | median difference +12.1 s; bootstrap 95% interval 7.0 to 22.5; Wilcoxon p=2.61e-7 |
| Ease score (0 easy, 100 difficult) | median 52.5 | median 35.0 | median difference +17.5; bootstrap 95% interval -10.0 to 40.0 |

The first-attempt-success interval is wide, so the released data do not establish an AWS advantage and do not rule out clinically relevant differences in either direction. Total intubation time is longer with AWS in this released dataset. The planned source-time sensitivity check gives a median difference of **+12.0 s** with bootstrap 95% interval **7.0 to 22.0**, and the supportive adjusted log-time model on **96 complete cases** gives an AWS/Macintosh time ratio of **1.555** with 95% CI **1.297 to 1.865**.

These are results from the redistributed teaching release, not a replacement for the source publication.

## Why this dataset

The work sample is close to the delivery pattern of a medical-device Statistical Data Scientist role:

- organize and validate patient-level study data;
- program the analysis in **R**;
- compare randomized device groups using binary and continuous clinical outcomes;
- make missingness, structural missing values and source-definition questions explicit;
- create analysis-ready tables and review-ready figures;
- produce short technical and stakeholder reports;
- keep the full workflow reproducible in CI;
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

## Data-quality decisions kept visible

The pipeline separates ordinary missingness from structural missingness. Attempt-2 and attempt-3 fields are expected to be empty when no later attempt was needed.

The automated review produces **22 checks: 17 PASS, 5 REVIEW, 0 FAIL**. REVIEW is used for source questions that should reach a statistician/data manager rather than be silently changed. The five review items are:

- one BMI value just outside the rounded range stated in the teaching documentation;
- one total-intubation-time value just outside the rounded documented range;
- four missing cells across three core variables, with available-case denominators made explicit;
- one patient whose first-attempt time is greater than the supplied total-intubation-time value;
- the public data dictionary describes the `view` coding in a way that is internally hard to reconcile with the usual clinical interpretation of Cormack-Lehane grades. The variable is retained as a raw source code but excluded from clinically labelled inferential conclusions.

No source value is silently repaired. The source-timing row is retained in the main analysis and handled separately in a bounded sensitivity analysis.

## Repository layout

```text
medical_device_rct_real_data/
├── README.md
├── CASE_STUDY_ONE_PAGER.md
├── DAY5_HANDOFF.md
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

The analysis uses base R so the core pipeline has no external R-package dependency.

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
- `outputs/day5_handoff.md`
- `outputs/figures/first_attempt_success.png`
- `outputs/figures/total_intubation_time.png`
- `outputs/figures/missingness.png`
- `outputs/figures/study_to_decision.png`

The figure set now uses direct result annotations and includes a one-page **Study -> Data -> QC -> Analysis -> Decision Support** view. The GitHub Actions workflow reruns the analysis from the public source, executes output checks, prints the study summary and uploads the generated outputs as an artifact.

## What this work sample demonstrates

The important result is not whether one device wins. The work sample shows that I can take real patient-level device-study data, define the analysis boundary, check source data, write reproducible R code, quantify uncertainty, preserve questionable source fields rather than silently fixing them, and produce outputs that a clinical/statistical team can review quickly.

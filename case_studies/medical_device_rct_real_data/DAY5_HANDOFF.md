# Day-5 study-team handoff

This page shows what I would hand to a clinical/statistical study team at the end of the first five working days of a short medical-device analysis contract.

## Day 1 — analysis boundary and plan

Confirm the study question, randomized treatment variable, main outcomes, analysis population, missing-data handling, sensitivity analyses and reporting boundary before reviewing model output. Record the public-data limitation: this repository uses the 99-patient teaching release rather than the 105-patient source publication dataset.

**Handoff:** `spec/analysis_plan.md` plus the data-source and evidence-boundary section of `README.md`.

## Day 2 — source-data review

Run reproducible import, provenance recording, type/range checks, treatment-count checks, missingness review and structural-missingness rules. Separate true source questions from values that can be handled by predefined analysis rules.

**Handoff:** `data_provenance.csv`, `missingness.csv`, `qc_findings.csv`, and a short list of source questions for the statistician/data manager.

## Day 3 — main randomized analysis

Produce the baseline descriptive table and the prespecified randomized device comparisons. Report effect estimates and uncertainty, not only p-values. Keep the small sample size and event counts visible.

**Handoff:** `baseline_table.csv`, `binary_outcomes.csv`, `continuous_outcomes.csv`, and the main figures.

## Day 4 — sensitivity and interpretation review

Run the bounded source-timing exclusion check and the supportive adjusted log-time model. Check whether the direction and practical size of the result change. Review wording so that statistical statements do not exceed what the teaching release can support.

**Handoff:** `sensitivity_analysis.csv` and `analysis_summary.md`.

## Day 5 — decision package

The study team receives one compact package:

1. **Decision brief:** the main result in plain statistical language, with the open source questions listed separately.
2. **Analysis summary:** methods, estimates, confidence intervals, sensitivity results and evidence boundary.
3. **Tables and figures:** review-ready outputs generated from the same analysis run.
4. **QC record:** PASS/REVIEW status for every automated check; no silent repair of the source data.
5. **Reproducible code and tests:** one-command analysis plus executable checks in CI.

The current teaching-release result is: first-attempt success does not show an AWS advantage, while total intubation time is longer for AWS in both the main and sensitivity analyses. This is a portfolio re-analysis, not a new clinical or regulatory conclusion.

## Open items before external use

The source-timing review row should be checked against the original study definition, the public `view` coding should be clarified before a clinical label is assigned, and any use outside this educational work sample should follow the source data-use terms and study-team review.

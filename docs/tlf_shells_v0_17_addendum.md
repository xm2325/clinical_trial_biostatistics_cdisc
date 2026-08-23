# TLF shell addendum — v0.17 retention TTE

## T24 — Study-discontinuation Kaplan–Meier retention

Population: randomised treated subjects in the three study arms.

Columns:

| Treatment | Day | Number at risk | Retention probability | Standard error | 95% CI lower | 95% CI upper |
|---|---:|---:|---:|---:|---:|---:|

Controlled timepoints: days 56, 112, 168 and 182. Confidence intervals use the log-log transformation.

## T25 — Study-discontinuation pairwise survival diagnostics

Exploratory comparisons only: Low Dose vs Placebo and High Dose vs Placebo.

Columns:

| Comparison | Hazard ratio | 95% CI lower | 95% CI upper | Cox p-value | Log-rank chi-square | Log-rank p-value | PH diagnostic p-value | PH interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---|

Cox models use Efron ties. `HR > 1` denotes a higher study-discontinuation hazard for the active arm than placebo. `cox.zph` is diagnostic evidence; a signal is reported rather than hidden or treated as a reason to change the pre-specified analysis.

T24 and T25 are explicitly outside the ACTOT primary confirmatory multiplicity family.

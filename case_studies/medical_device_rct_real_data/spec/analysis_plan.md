# Analysis plan: real-data medical-device RCT case study

Version: 1.0  
Date: 2026-09-12

## 1. Purpose

This plan defines a reproducible educational re-analysis of the public 99-patient teaching release derived from the randomized comparison of the Pentax AWS video laryngoscope and the Macintosh #4 laryngoscope.

The purpose is to demonstrate short-cycle clinical statistical delivery in R. It is not a substitute for the original study protocol/statistical analysis plan, source database, publication analysis or regulatory analysis.

## 2. Analysis population

All records in the 99-row public teaching release with a valid randomized-device code are included in the main analysis. The randomized groups are:

- `Randomization = 0`: Macintosh #4;
- `Randomization = 1`: Pentax AWS video.

No patient is excluded because of a post-randomization outcome.

The original publication reports 105 randomized patients. Because the redistributed teaching release contains 99, all denominators in this case study come from the teaching release and are reported explicitly.

## 3. Data handling

The raw CSV is downloaded at run time from the public Rdatasets mirror. It is not edited manually and is not committed to this repository.

The pipeline records source URL, retrieval timestamp and MD5 checksum. Patient identifier uniqueness, randomized-arm coding, ranges, missingness and attempt-level consistency are checked before analysis.

Missing later-attempt variables are structural when a later attempt was not required and are not counted as ordinary missing outcomes.

No source value is silently corrected. A source-definition question is recorded when `attempt1_time > total_intubation_time`. The main analysis retains the source value; an exclusion sensitivity analysis is reported separately.

The `view` variable is not assigned a clinical interpretation in the main report because the public dictionary's wording for the binary code and Cormack-Lehane grades is internally hard to reconcile. Raw code is retained.

## 4. Baseline description

Baseline variables are summarized by randomized device:

- age;
- sex;
- body mass index;
- ASA physical status;
- Mallampati class.

Continuous variables use mean, standard deviation, median and quartiles. Selected binary summaries use n/N and percentage. Standardized mean differences are reported descriptively.

No baseline p-values are used to decide whether randomized outcome comparisons are valid.

## 5. Main outcomes

### 5.1 First-attempt intubation success

Variable: `attempt1_S_F`.

Reported by randomized device as events/N and percentage.

Effect measures:

- absolute risk difference, Pentax AWS minus Macintosh;
- 95% Newcombe interval based on Wilson score intervals;
- risk ratio, Pentax AWS divided by Macintosh;
- 95% log-scale interval, with half-cell correction only if a 2x2 cell is zero;
- two-sided Fisher exact p-value.

### 5.2 Total intubation time

Variable: `total_intubation_time` in seconds.

Reported by randomized device as N, median and quartiles.

Effect measures:

- median difference, Pentax AWS minus Macintosh;
- 10,000-resample seeded nonparametric bootstrap 95% percentile interval;
- two-sided Wilcoxon rank-sum p-value.

The nonparametric main analysis avoids relying on a normal distribution for procedure times.

## 6. Supportive outcomes

The same randomized grouping is used for:

- overall successful intubation (`intubation_overall_S_F`);
- more than one intubation attempt (`attempts > 1`);
- trace bleeding (`bleeding`);
- any postoperative sore throat (`sore_throat > 0`);
- ease of intubation (`ease`, 0 extremely easy to 100 extremely difficult).

Binary outcomes use event proportions, risk difference/risk ratio and Fisher exact testing. Ease uses the same median/bootstrap/Wilcoxon approach as total time.

These supportive analyses are descriptive/inferential aids and are not presented as a new multiplicity-controlled confirmatory family.

## 7. Missing data

The pipeline reports available-case denominators for every outcome.

No imputation is used because the main randomized outcome fields are nearly complete and the portfolio goal is transparent re-analysis of the released source. Missing BMI, Mallampati or sore-throat values are surfaced in QC and reflected in the relevant denominators.

No missing value is converted to a negative outcome.

## 8. Sensitivity analyses

### S1: source-time review exclusion

Repeat the total-time median comparison after excluding rows where first-attempt time exceeds the supplied total-intubation-time value. This does not replace the main analysis because the reason for the source value is not known.

### S2: covariate-adjusted log-time model

Fit an ordinary least-squares model to log(total intubation time) with randomized device plus age, BMI, gender, ASA and Mallampati among complete cases.

Exponentiating the randomized-device coefficient gives a multiplicative time ratio, Pentax AWS divided by Macintosh.

This model is supportive only. The unadjusted randomized comparison remains the main result.

A large adjusted logistic model for first-attempt success is intentionally not specified because the dataset contains few failures relative to the number of possible covariates and would be at high risk of unstable estimation.

## 9. Reporting

Generated outputs include:

- provenance and checksum;
- missingness and QC tables;
- baseline summary;
- binary and continuous outcome tables;
- sensitivity-analysis table;
- first-attempt success, total-time and missingness figures;
- technical analysis summary;
- short internal stakeholder brief.

All effect directions are labelled explicitly. Statistical uncertainty is reported with point estimates rather than replacing them with significance labels.

## 10. Evidence boundary

The TSHS Resources Portal states that its datasets may be modified for de-identification and should not be used to claim valid inferences beyond the original study purpose. It also states that publication use requires permission from the source.

Accordingly:

- results are described as results from the 99-patient teaching release;
- the original publication remains the clinical source;
- differences from published denominators or estimates are not treated as errors in the publication;
- no new device-effectiveness, safety, regulatory or clinical-practice claim is made from this portfolio re-analysis.

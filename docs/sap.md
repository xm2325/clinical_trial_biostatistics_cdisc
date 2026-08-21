# Statistical Analysis Plan — portfolio version 0.2

## 1. Scope

This Statistical Analysis Plan (SAP) specifies a limited safety analysis for an independent portfolio project using public SDTM test data. It is not sponsor-approved and is not a regulatory-submission SAP.

## 2. Analysis populations

### 2.1 Randomised population

A subject is randomised if DS contains a record with `DSDECOD == "RANDOMIZED"`.

### 2.2 Safety population

A subject is in the safety population if at least one EX record is observed. This operational definition makes the population depend on observed exposure rather than only DM treatment labels.

## 3. Treatment and exposure

Planned and actual treatment labels are taken from DM and carried to `TRT01P` and `TRT01A`.

Actual exposure dates are derived from EX:

- `TRTSDT`: minimum parsed `EXSTDTC`;
- `TRTEDT`: maximum parsed `EXENDTC`; if unavailable, use DM `RFXENDTC`, then the final DS disposition date as a pre-specified fallback;
- `EXDURN_RAW`: inclusive duration from non-missing EX start/end dates only;
- `TRTDURN`: final inclusive treatment-window duration from `TRTSDT`/`TRTEDT`, after documented fallbacks;
- `EXN`: number of observed EX records;
- `EXDOSE_MAX` and `EXDOSE_MEAN`: subject-level summaries of numeric `EXDOSE`.

DM `RFXSTDTC` and `RFXENDTC` are retained as `TRTSDT_DM` and `TRTEDT_DM` for traceability. `TRTSDTSRC` and `TRTEDTSRC` record whether the final analysis date came from EX or a fallback. Fallback use is quantified in QC and run metrics.

## 4. Disposition

`RANDFL` is based on a DS randomisation milestone. `COMPLFL` is `Y` if a DS record has `DSDECOD == "COMPLETED"`. The final disposition event is the last record with `DSCAT == "DISPOSITION EVENT"` ordered by disposition date and sequence. A randomised subject without completion is flagged `DCSFL == "Y"`.

## 5. Adverse-event derivations

AE records are linked to ADSL-style by `STUDYID` and `USUBJID`.

- `ASTDT`: parsed from `AESTDTC`.
- `AENDT`: parsed from `AEENDTC` when available.
- `TRTEMFL`: `Y` if `ASTDT >= TRTSDT` and `ASTDT <= TRTEDT + 30 days`; otherwise `N`.
- `RELFL`: `Y` for `AEREL` in `POSSIBLE`, `PROBABLE`, `DEFINITE`, or `RELATED`.
- `MODSEVFL`: `Y` for `AESEV` in `MODERATE` or `SEVERE`.
- Serious TEAE: `AESER == "Y"` and `TRTEMFL == "Y"`.

No partial-date imputation is performed. An AE with missing start date cannot meet the portfolio TEAE rule; the missingness count is reported by QC.

## 6. Descriptive statistics

Age is summarised using mean, standard deviation, median, Q1 and Q3. Categorical variables are summarised as counts and percentages. Exposure duration and exposure-record counts are summarised by actual treatment.

TEAE incidence is subject-level: each subject contributes at most once to an incidence count for a given endpoint or preferred term. Percentages use the corresponding safety-population treatment-arm N as denominator.

## 7. Exploratory any-TEAE treatment comparison

For each Xanomeline arm versus placebo:

- risk in the active arm: `p1 = e1 / n1`;
- risk in placebo: `p0 = e0 / n0`;
- risk difference: `RD = p1 - p0`;
- 95% CI: `RD +/- 1.96 * sqrt[p1(1-p1)/n1 + p0(1-p0)/n0]`;
- Fisher's exact-test p-value from the 2x2 subject-level table.

These comparisons are unadjusted and exploratory. No multiplicity correction is applied. The workflow does not present them as confirmatory efficacy or safety conclusions.

## 8. Missing data

No model-based missing-data imputation is used. Missing dates and other derivation-impacting fields are quantified in the QC output.

## 9. Multiplicity

No confirmatory hypothesis family is defined. P-values in Table 7 are exploratory and are reported without multiplicity adjustment.

## 10. QC

Required checks cover:

- unique ADSL-style and ADAE-style keys;
- AE-to-subject referential integrity;
- valid analysis flags;
- observed exposure for safety subjects;
- usable exposure dates and valid exposure start/end ordering;
- disposition availability for randomised subjects;
- mutually exclusive completion/discontinuation flags;
- no treatment-emergent event outside the safety population;
- no TEAE before first exposure;
- no TEAE after the pre-specified 30-day follow-up window.

Exposure-date fallback use and AE records with missing start dates are reported as informational QC items. The pipeline fails the work-sample acceptance condition if any required QC check fails, although it still writes the QC report for diagnosis.

## 11. Sample-size demonstration

A separate utility provides equal-allocation normal-approximation sample-size calculations for two-arm continuous and binary endpoints. These examples are not tied to the public pilot study.

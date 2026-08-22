# Independent programming QC — R/Python cross-language implementation

## Purpose

Version 0.4 adds a second implementation of selected analysis derivations in R. Its purpose is to test whether the analysis rules can be reproduced from the same public source data without using the Python derivation code.

This is a portfolio analogue of double programming. It is deliberately described as **cross-language implementation QC**, not as independent validation by a second human programmer.

## Independence boundary

`R/independent_qc.R` reads the same cached public inputs used by the Python workflow:

- DM;
- EX;
- DS;
- AE;
- official CDISC QS Dataset-JSON.

The R program does not import, call or translate Python derivation functions. It independently implements the analysis rules in R. Python-generated CSV/JSON outputs are read only at the final comparison stage.

The two implementations therefore share:

- source data;
- written analysis definitions;
- the repository owner;
- target outputs and acceptance criteria.

They do not share executable derivation code.

## R reconstruction scope

### Safety

R independently derives:

- randomised population from DS `DSDECOD=RANDOMIZED`;
- safety population from observed EX;
- completed-subject count from DS;
- treatment start and end dates, including the documented DS disposition fallback;
- TEAE flags using the `[TRTSDT, TRTEDT + 30 days]` window;
- subject-level any-TEAE risks;
- active-versus-placebo risk differences, Wald confidence intervals and Fisher exact-test p-values.

### CIBIC

R independently applies the same analysis windows to official QS `QSTESTCD=CIBIC` records:

| Analysis visit | Target day | Observation window |
|---|---:|---|
| Week 8 | 56 | 2–84 |
| Week 16 | 112 | 85–140 |
| Week 24 | 168 | 141 onward |

Within each window, the observation closest to the target day is selected. If no observation is available, the latest prior eligible record is carried forward and marked `DTYPE=LOCF`.

The final comparison checks selected analysis keys, `QSSEQ`, `DTYPE` and source-derived `AVAL`.

### ACTOT

R independently rebuilds the 818 official QS `ACTOT` source records retained by the Python portfolio analysis, including:

- baseline identification from `QSBLFL`;
- `BASE`;
- `CHG = AVAL - BASE`;
- baseline and efficacy flags;
- source-row keys.

### Week 24 ANCOVA

R independently forms the observed Week 24 and LOCF analysis sets and fits:

`AVAL = intercept + LOW + HIGH + centred BASE + error`.

The comparison covers:

- contrast names;
- analysis sample size;
- residual degrees of freedom;
- treatment estimates;
- standard errors;
- two-sided 95% t confidence intervals;
- two-sided p-values;
- analysis-set mean baseline used as the centring reference.

## Acceptance rules

Discrete derivations must match exactly. The any-TEAE risk-difference output must match at the reported precision. ANCOVA numeric outputs must agree within `1e-8`.

The GitHub Actions workflow fails if any required check fails. An R syntax parse is run before the R analysis. R version, dependency version and full `sessionInfo()` are retained in the artifact.

## Verified v0.4 result

The verified GitHub Actions run used:

- R 4.6.1 (2026-06-24);
- jsonlite 2.0.0.

All **16/16 required cross-language checks passed**.

| Area | Verified result |
|---|---:|
| Randomised subjects | R 254 = Python 254 |
| Safety subjects | R 254 = Python 254 |
| Completed subjects | R 110 = Python 110 |
| Subjects with TEAE | R 217 = Python 217 |
| TEAE events | R 1,116 = Python 1,116 |
| DS treatment-end fallbacks | R 2 = Python 2 |
| Any-TEAE risk table | max numeric difference 0 |
| CIBIC selected rows | R 705 = Python 705 |
| CIBIC selected keys | exact |
| CIBIC `QSSEQ` | exact |
| CIBIC `DTYPE` | exact |
| CIBIC source-derived `AVAL` | exact |
| ACTOT source rows | R 818 = Python 818 |
| ACTOT `AVAL` / `BASE` / `CHG` | exact |
| ACTOT flags | exact |
| Observed Week 24 N | R 116 = Python 116 |
| LOCF N | R 235 = Python 235 |
| ANCOVA N / df | exact |
| ANCOVA numerical outputs | maximum difference `7.11e-15` |

The measured ANCOVA difference is several orders of magnitude below the pre-specified `1e-8` tolerance.

## Relation to official-reference QC

Cross-language QC and official-reference QC answer different questions.

The R/Python checks ask whether two separate implementations of the written portfolio rules give the same result from the same source data.

The official-reference checks ask whether selected records and analysis metadata align with public CDISC reference ADaM files. For ADQSCIBC, the public QS source and public reference ADaM differ in `AVAL` for ten selected records. Those ten cases remain explicit source/reference discrepancies even though the R and Python source-derived values agree exactly.

Keeping these checks separate prevents a public reference inconsistency from being misreported as a cross-language programming failure.

## Artifact outputs

The v0.4 workflow adds:

- `r_independent_qc.csv` — one row per required cross-language check;
- `r_metrics.json` — machine-readable R run metadata and counts;
- `r_session_info.txt` — R runtime and package/session information;
- `r_independent_qc_summary.md` — compact run summary;
- `r_teae_risk_difference.csv` — independently generated R safety comparison;
- `r_actot_ancova_contrasts.csv` — independently generated R ANCOVA contrasts.

# QC plan — portfolio version 0.10

The workflow separates required validation layers for Python derivation, official-reference checks, R/Python cross-language programming QC, MMRM data/model QC, analysis-dataset/TLF review, statistical change-impact assessment and SAP-to-TLF traceability. Required failures exit non-zero. Informational discrepancies remain visible rather than being converted into pass/fail rules without justification.

## Python safety required checks

1. ADSL-style `STUDYID + USUBJID` is unique.
2. ADAE-style `STUDYID + USUBJID + AESEQ` is unique.
3. Every AE subject maps to ADSL-style.
4. `SAFFL` and `TRTEMFL` contain only `Y/N`.
5. Every safety subject has observed EX records.
6. Safety subjects have usable first/last exposure dates.
7. Exposure end is not before exposure start.
8. Randomised subjects have a final disposition event.
9. Completion and discontinuation flags are mutually exclusive.
10. No TEAE occurs outside the safety population.
11. No TEAE starts before first exposure.
12. No TEAE starts after the 30-day post-exposure window.

## Python efficacy required checks

13. ADQSCIBC-style `STUDYID + USUBJID + AVISIT` is unique.
14. ADQSCIBC-style `AVAL` is non-missing.
15. ADQSCIBC-style `DTYPE` is blank or `LOCF`.
16. ADQSCIBC-style analysis visits are Week 8, Week 16 or Week 24.
17. ACTOT has at most one baseline-flagged record per subject.
18. ACTOT `CHG` exactly equals `AVAL - BASE` for eligible post-baseline records.
19. Observed Week 24 ANCOVA has one row per subject.
20. LOCF sensitivity retains at least as many subjects as the observed-case analysis.
21. Official ADQSCIBC analysis-key coverage is exactly 100%.
22. Official ADQSCIBC `DTYPE` agreement is exactly 100%.
23. Official ADQSCIBC `QSSEQ` source-row agreement is exactly 100%.
24. The pipeline records ADQSCIBC reference-value agreement and its mismatch trace without changing source-derived values.

The verified v0.10 live run retains **24/24 required Python pipeline checks** and **40/40 Python unit tests** across the full portfolio codebase.

## Independent R/Python required checks

`R/independent_qc.R` starts from the same cached public DM, EX, DS, AE and QS inputs. It does not call Python derivation functions. Python outputs are read only after the R results have been reconstructed, for the final comparison.

The following 16 checks are required:

1. R randomised-subject count equals Python.
2. R safety-subject count equals Python.
3. R completed-subject count equals Python.
4. R subject-with-TEAE count equals Python.
5. R TEAE event count equals Python.
6. R DS exposure-end fallback count equals Python.
7. R any-TEAE risk-difference table matches Python at the reported precision.
8. R CIBIC selected `STUDYID + USUBJID + AVISIT` keys equal Python.
9. R CIBIC selected `QSSEQ` values equal Python.
10. R CIBIC `DTYPE` values equal Python.
11. R CIBIC source-derived `AVAL` values equal Python.
12. R ACTOT source-row keys equal Python.
13. R ACTOT `AVAL`, `BASE` and `CHG` equal Python.
14. R ACTOT baseline and efficacy flags equal Python.
15. R ANCOVA contrast keys, analysis N and residual df equal Python.
16. R ANCOVA estimates, standard errors, 95% confidence limits, p-values and baseline reference values agree with Python within `1e-8`.

The verified v0.10 run passes **16/16**. Measured results include R/Python equality for 254 randomised subjects, 254 safety subjects, 110 completed subjects, 217 subjects with TEAE, 1,116 TEAE events, 705 CIBIC selected rows and 818 ACTOT source rows. The latest maximum ANCOVA numerical difference is `4e-14`, below the pre-specified tolerance.

This is a second implementation by the same portfolio author, not independent validation by a second human programmer.

## MMRM required checks

`R/mmrm_analysis.R` fits the ACTOT longitudinal analysis after the Python derivation and independent R QC steps. MMRM inputs are observed Week 8, Week 16 and Week 24 ACTOT records only; LOCF values do not enter the model.

The following 11 checks are required:

1. all three planned treatment arms are present;
2. Week 8, Week 16 and Week 24 are present;
3. the covariance visit variable is an R factor;
4. `USUBJID + AVISIT` is unique;
5. `CHG = AVAL - BASE` within `1e-12`;
6. `BASE` is constant within subject within `1e-12`;
7. the primary unstructured MMRM returns a finite log likelihood;
8. the heterogeneous AR(1) sensitivity MMRM returns a finite log likelihood;
9. the primary fit produces exactly six active-versus-placebo visit contrasts;
10. primary estimates, standard errors, df, confidence limits and p-values are finite;
11. the primary fit produces exactly two Week 24 active-versus-placebo contrasts.

The verified v0.10 run passes **11/11**. The checked input contains 451 observed post-baseline records from 189 subjects, with Week 8=189, Week 16=146 and Week 24=116.

A model fit is not accepted merely because an R object is returned: the workflow separately checks finite likelihood, expected contrast cardinality and finite inferential quantities.

## Analysis-dataset and TLF reviewer required checks

The v0.9+ reviewer runs after the R MMRM and before change-control/traceability gates. It is separate from the derivation programs and checks consistency across generated files.

The verified v0.10 run retains **24/24 required reviewer checks**: 19 cross-dataset, derivation, population, TLF-denominator and TLF-structure checks plus five machine-readable dataset contracts. The reviewer covers ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM analysis data and records SHA256 for 17 reviewed generated files.

Required review includes exact MMRM source-row traceability through `STUDYID + USUBJID + QSSEQ`, treatment/population reconciliation across datasets, ACTOT baseline/change checks and independent reconstruction of safety/efficacy TLF denominators.

Negative-control tests deliberately corrupt treatment consistency, a safety-table denominator, MMRM `CHG`, a required dataset column and a controlled-value flag; the corresponding validators must fail.

## Statistical change-control impact gate

The v0.10 gate uses `spec/change_impact_graph.json` to derive downstream review requirements from the changed statistical component and compares those graph-derived requirements with `spec/change_requests.json`.

Five impact categories are controlled:

1. generated analysis datasets;
2. TLF IDs resolved through `spec/analysis_traceability.csv`;
3. generated QC evidence;
4. statistical/reviewer documents;
5. machine-readable design or randomisation specifications.

The verified v0.10 live run evaluates four portfolio change scenarios and covers **67/67 required impact declarations** with **67/67 required resources resolved**. No required declaration is missing and no extra declaration is present in the verified specifications.

| Change | Propagated components | Required impacts | TLF scope |
|---|---:|---:|---|
| CR-001 safety population definition | 4 | 18 | T01–T07 |
| CR-002 TEAE follow-up window | 3 | 14 | T04–T07 |
| CR-003 primary ACTOT visit | 6 | 24 | T08–T12, T15 |
| CR-004 primary MMRM covariance | 3 | 11 | T11–T15 |

Required failure conditions include an omitted graph-required impact, an unknown changed component, a cyclic dependency graph, an unresolved static resource, an unmapped TLF ID or a required generated resource that does not exist in the live run. Conservative extra review declarations are permitted but reported.

These four change requests are simulations. They do not change the current 30-day TEAE window, Week 24 analysis focus or unstructured primary MMRM.

## Official-reference profiler hard gates

`scripts/profile_official_references.py` runs before the main analysis in CI.

### ADQSCIBC

Required:
- reference analysis-key coverage = 100%;
- `DTYPE` agreement = 100%;
- `QSSEQ` agreement = 100%;
- when `AVAL` differs from the public reference, the portfolio `AVAL` must equal `QSSTRESN` from the selected official QS source row.

Verified: 705/705 analysis keys, 100% `DTYPE`, 100% `QSSEQ`, 98.58% `AVAL` agreement. All ten value differences satisfy the source-trace requirement.

### ADQSADAS / ACTOT

For official `ACTOT` rows with `ANL01FL=Y`, selected `USUBJID + AVISIT` key coverage, `DTYPE` and selected `QSSEQ` must each agree at 100%.

Verified: all 1,016 selected ACTOT analysis keys are reconstructed with exact `DTYPE` and `QSSEQ` agreement.

## Informational checks and retained diagnostics

Informational items include:
- AE records with missing start dates;
- treatment-end fallback use and DS disposition fallback count;
- ADQSCIBC `AVAL` agreement rate and full mismatch source trace;
- ADQSADAS `AVAL`, `BASE` and `CHG` agreement rates;
- item-recomputed ADAS-Cog(11) total comparison with official selected ACTOT rows;
- R/package/session information;
- MMRM log likelihood, AIC and BIC for both covariance structures;
- MMRM-versus-observed-Week-24-ANCOVA estimate differences;
- conservative extra change-impact declarations, if any.

A reference-value mismatch is not automatically a derivation failure when the selected source row is identical and the portfolio value matches that source. Likewise, a difference between MMRM and Week 24 ANCOVA estimates is not automatically a failure because the analyses use different data structures. Both types of difference are preserved in audit outputs.

## CI evidence retention

GitHub Actions prints the main Python, R, MMRM, reviewer, change-control and traceability summaries and uploads the `outputs/` directory even when a downstream analysis step fails where possible. This keeps source-reference traces, QC tables, model diagnostics, reviewer evidence and change-impact diagnostics available for investigation.

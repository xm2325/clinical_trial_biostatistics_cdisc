# QC plan

The workflow distinguishes **required** QC checks from informational checks. `metrics.json` reports required Python-pipeline status, while `manifest.json` records `qc_all_passed`. `scripts/run_all.py` exits non-zero when required pipeline QC fails. The official-reference profiler has separate structural/source gates. Version 0.4 adds a second-language R implementation with its own required cross-language checks.

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

The verified v0.4 live run retains **24/24 required Python pipeline checks**.

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

The verified live run passes **16/16**. Key measured results are:

- randomised subjects: R 254, Python 254;
- safety subjects: R 254, Python 254;
- completed subjects: R 110, Python 110;
- subjects with TEAE: R 217, Python 217;
- TEAE events: R 1,116, Python 1,116;
- DS exposure-end fallback subjects: R 2, Python 2;
- risk-difference table maximum numeric difference: 0;
- CIBIC selected rows: R 705, Python 705, with exact key/`QSSEQ`/`DTYPE`/source-value agreement;
- ACTOT source rows: R 818, Python 818, with exact key/`AVAL`/`BASE`/`CHG`/flag agreement;
- observed Week 24 ANCOVA N: R 116, Python 116;
- LOCF ANCOVA N: R 235, Python 235;
- maximum ANCOVA numeric difference: `7.11e-15`.

The R step also records R version, package version and `sessionInfo()`. GitHub Actions parses the R program before running it. Any failed required R check causes the workflow to fail.

This provides cross-language implementation evidence, but it is not labelled as independent validation by a second human programmer.

## Official-reference profiler hard gates

`scripts/profile_official_references.py` runs before the main analysis in CI and checks two reference workflows.

### ADQSCIBC

- reference analysis-key coverage must be 100%;
- `DTYPE` agreement must be 100%;
- `QSSEQ` agreement must be 100%;
- if `AVAL` differs from the public reference, the portfolio `AVAL` must equal `QSSTRESN` from the selected official QS source row.

The verified run has 705/705 reference analysis keys, 100% `DTYPE`, 100% `QSSEQ` and 98.58% `AVAL` agreement. The ten value differences all satisfy the source-trace requirement.

### ADQSADAS / ACTOT

For official `ACTOT` rows with `ANL01FL=Y`:

- selected `USUBJID + AVISIT` key coverage must be 100%;
- `DTYPE` agreement must be 100%;
- selected `QSSEQ` agreement must be 100%.

The official reference contains 1,016 selected ACTOT analysis records and the portfolio reconstructs all 1,016 keys with exact `DTYPE` and `QSSEQ` agreement.

## Informational checks and metrics

- AE records with missing start dates;
- treatment-end fallback use and DS disposition fallback count;
- ADQSCIBC `AVAL` agreement rate and full mismatch source trace;
- ADQSADAS `AVAL`, `BASE` and `CHG` agreement rates;
- item-recomputed ADAS-Cog(11) total comparison with official selected ACTOT rows;
- R version, `jsonlite` version and complete R session information.

A reference-value mismatch is not automatically a derivation failure when the selected source row is identical and the portfolio value matches the official source. In that case the discrepancy is kept in an audit output instead of being silently changed.

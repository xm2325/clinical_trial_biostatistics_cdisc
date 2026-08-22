# QC plan

The workflow distinguishes **required** QC checks from informational checks. `metrics.json` reports required-check status, while `manifest.json` records the overall `qc_all_passed` flag. `scripts/run_all.py` exits non-zero when required pipeline QC fails. The official-reference profiler has separate hard structural/source gates.

## Safety required checks

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

## Efficacy required checks in the main pipeline

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

The verified v0.3 live run passes **24/24 required pipeline checks**.

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
- item-recomputed ADAS-Cog(11) total comparison with official selected ACTOT rows.

A reference-value mismatch is not automatically a derivation failure when the selected source row is identical and the portfolio value matches the official source. In that case the discrepancy is kept in an audit output instead of being silently changed.

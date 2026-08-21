# QC plan

The workflow distinguishes **required** QC checks from informational checks. `metrics.json` reports how many required checks pass, and `manifest.json` carries an overall `qc_all_passed` flag. From v0.3, `scripts/run_all.py` exits non-zero when required QC fails; GitHub Actions still uploads any generated diagnostic outputs.

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

## Efficacy / reference required checks

13. ADQSCIBC-style `STUDYID + USUBJID + AVISIT` is unique.
14. ADQSCIBC-style `AVAL` is non-missing.
15. ADQSCIBC-style `DTYPE` is blank or `LOCF`.
16. ADQSCIBC-style analysis visits are Week 8, Week 16 or Week 24.
17. ACITM01 has at most one baseline-flagged record per subject.
18. ACITM01 `CHG` exactly equals `AVAL - BASE` for post-baseline records.
19. Observed Week 24 ANCOVA has one row per subject.
20. LOCF sensitivity retains at least as many subjects as the observed-case analysis.
21. Portfolio ADQSCIBC-style records cover at least 95% of official reference keys.
22. `AVAL` matches the official CDISC ADQSCIBC reference for at least 99% of overlapping keys.

## Informational checks

- number of AE records with missing start dates;
- number of subjects whose exposure end required DM or DS fallback;
- official ADQSCIBC `DTYPE` match rate;
- official ADQSCIBC `QSSEQ` source-record match rate.

The reference thresholds are intentionally strict. If the first live run fails them, the mismatch detail output is used to identify the exact subjects/visits and the derivation rule is corrected rather than weakening the threshold without evidence.

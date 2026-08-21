# QC plan

The workflow distinguishes **required** QC checks from informational checks. `metrics.json` reports how many required checks pass, and `manifest.json` carries an overall `qc_all_passed` flag.

## Required checks

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

## Informational checks

- Number of AE records with missing start dates.
- Number of subjects whose exposure end required DM or DS fallback; DS disposition fallbacks are counted separately.

Informational checks are retained in the QC report but do not make the overall required-QC flag fail.

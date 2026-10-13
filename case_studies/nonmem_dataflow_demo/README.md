# NONMEM dataflow teaching module (synthetic source records)

This is an additive **portfolio training exercise**, not pharmaceutical production work, a
validated NONMEM dataset, a GxP/Part 11 system, or a regulatory e-submission. All
subjects, doses and concentrations in data/ are invented. Do not merge these records
with real public clinical datasets in the rest of the repository.

## Run from the repository root

```bash
Rscript case_studies/nonmem_dataflow_demo/R/01_build_nonmem_dataset.R
python case_studies/nonmem_dataflow_demo/scripts/02_independent_qc.py
```

The first command writes outputs/nonmem_demo/{data,metadata,model}; the second
adds qc/qc_log.csv and qc/qc_summary.md. Outputs are generated, not committed.

## Input fields

- DM: USUBJID, AGE, SEX; EX: USUBJID, EXSTDTC, EXDOSE, EXDOSU, EXROUTE.
- PC: USUBJID, PCDTC, PCSTRESN, PCSTRESU, BLQ_FLAG, LLOQ_NG_ML.
- VS: USUBJID, VSDTC, VSTESTCD, VSSTRESN, VSSTRESU.

These are deliberately **SDTM-like CSVs**, not certified SDTM domains; BLQ_FLAG
and LLOQ_NG_ML are exercise-specific source fields, not asserted to be SDTM
standard variable names. Source timestamps are complete ISO datetimes treated
as UTC. No partial datetimes, time zones, infusions, titration, duration, carry-forward
covariates, simultaneous repeated measurements or unclean interim data are supported.

## Derivation / model context

- IDs are deterministic by sorted USUBJID and documented in subject_crosswalk.csv.
- TIME = hours from first EX; TAD = hours since latest EX.
- Dose event: EVID=1, MDV=1, AMT in mg, CMT=1 (oral depot).
- Concentration event: EVID=0, CMT=2 (central), DV in ng/mL, AMT=0.
- BLQ is **M1 exclusion for illustration only**: BLQ=1, MDV=1, DV=0;
  the true observed concentration is not invented. This is NOT an M3 censored
  likelihood analysis; such modelling requires a different model specification.
- WT is the single pre-dose weight (kg); SEX uses F=0, M=1. Dose events
  precede observations at tied times. Exact dose/sample timestamps are used.
- nonmem_input.csv has **no header** in the declared $INPUT order;
  nonmem_input_review.csv has named columns for inspection/QC.
- The illustrative control file is not executed, tested or qualified for real
  NONMEM. No PK parameter estimation, parameter output or simulation claimed.

## QC and simulated submission hand-off

Python QC independently derives expected events from source files and checks
each synthetic subject's values, dose/PC counts, time since dose,
MDV/EVID/CMT/BLQ, unit conversions, exposure and covariates. It also checks
manifest MD5s and the headerless NONMEM export shape. Each check records
subject, QC script, pass/fail, issue and proposed follow-up. An output marked
PASS is a **bounded synthetic work sample**, not formal second-programmer sign-off.

The generated directory is submission-**style** training material only:
data/, model/, metadata/variable_definitions.csv, metadata/manifest.csv,
qc/. It does not contain a validated define.xml, real run outputs,
EPOD hand-off evidence, or a regulatory submission.

### Interview explanation

The PM/CPP modelling lead determines the analysis specification and
population PK assumptions. This module focuses on source mapping, event
construction, derivations, independent checks, traceability and packaging,
which are programmer support activities.

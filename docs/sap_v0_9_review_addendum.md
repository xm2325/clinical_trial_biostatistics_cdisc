# Statistical Analysis Plan addendum — portfolio v0.9

## 1. Status

This addendum extends `docs/sap.md` (portfolio v0.8) with the analysis-dataset and TLF reviewer controls introduced in v0.9. It does not alter the statistical models, analysis populations, estimands, safety window, multiplicity statements, protocol-design exercise or randomisation method specified in the base portfolio SAP.

This is an independent portfolio document. It is not sponsor-approved, is not a regulatory-submission SAP amendment and does not represent formal change control for a real clinical trial.

## 2. Reason for addendum

Version 0.9 adds a separate post-generation statistical-programming review layer. Existing derivation QC can show that a dataset is internally consistent; the v0.9 reviewer additionally checks whether analysis datasets and TLF-style outputs remain consistent **across** files.

The reviewer is run after the R MMRM analysis and before final SAP-to-TLF structural traceability validation.

## 3. Machine-readable analysis-dataset contracts

`spec/analysis_dataset_contracts.json` defines portfolio contracts for:

- ADSL-style subject analysis data;
- ADAE-style adverse-event analysis data;
- source-derived ACTOT analysis data;
- Week 24 / LOCF ANCOVA analysis-subject data;
- longitudinal MMRM analysis data.

Each contract defines a key, required columns, non-missing fields and controlled values. The contract specification is hashed in the reviewer metrics to tie the evidence to the exact rules used.

These contracts are portfolio QC metadata. They are not formal ADaM conformance assessment, Define-XML or sponsor-approved metadata.

## 4. Required cross-dataset review

The reviewer requires subject parentage and treatment/population attributes to reconcile across ADSL-style, ADAE-style, ACTOT and ANCOVA datasets. ACTOT `BASE` and `CHG` are independently checked, and every MMRM row must trace to the exact ACTOT source record through `STUDYID + USUBJID + QSSEQ`, with treatment, `AVAL`, `BASE` and `CHG` matching the source row.

MMRM subject-visit keys must be unique and the allowed visit set remains Week 8, Week 16 and Week 24.

## 5. Required TLF denominator review

The reviewer reconstructs displayed Ns/denominators from analysis datasets rather than trusting the output tables. Required reconciliation covers demographics, disposition, TEAE overview, TEAE SOC/PT, TEAE severity, any-TEAE risk differences, Week 24 descriptives, ANCOVA least-squares means/contrasts and MMRM visit counts/coverage.

In the verified v0.9 run, reconstructed randomised/safety arm Ns are Placebo=86, Xanomeline High Dose=96 and Xanomeline Low Dose=72. Observed Week 24 Ns are Placebo=30, High Dose=59 and Low Dose=27. All required linked TLF checks reconcile.

## 6. QC acceptance

The verified v0.9 GitHub Actions run has:

| QC layer | Result |
|---|---:|
| Python unit tests | **34/34 passed** |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| SAP-to-TLF structural traceability | **15/15 TLFs passed** |
| Required protocol-design QC | **7/7 passed** |
| Required randomisation/initial-kit QC | **10/10 passed** |
| Required analysis-dataset/TLF reviewer QC | **24/24 passed** |
| Reviewed generated files with SHA256 | **17/17** |

The 24 reviewer checks contain 19 cross-dataset/derivation/TLF checks plus five dataset-contract checks.

## 7. Failure-mode testing

Unit tests deliberately corrupt treatment consistency, a safety-table denominator, an MMRM source-derived change value, a required contract column and a controlled flag. The relevant reviewer/contract validation must fail on these defects.

This is same-author automated portfolio review and does not claim independent second-programmer validation.

## 8. Outputs

The reviewer writes:

- `outputs/analysis_dataset_review.csv`;
- `outputs/analysis_dataset_review_metrics.json`;
- `outputs/analysis_dataset_review_summary.md`.

A required review failure exits non-zero and blocks GitHub Actions.

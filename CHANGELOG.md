# Changelog

## 0.7.0 — 2026-08-22

- Add a machine-readable three-arm protocol-design specification for a portfolio Week 24 ACTOT change-from-baseline planning scenario.
- Define two active-versus-placebo comparisons with two-sided family-wise alpha 0.05 and Bonferroni per-comparison alpha 0.025.
- Add continuous-endpoint sample-size utilities, dropout inflation and achieved-power back-calculation after integer rounding.
- Evaluate six effect/power scenarios using common planning SD 6.0 and 15% anticipated dropout.
- Verify scenario totals from 273 to 792 randomised subjects across the six illustrative scenarios; assumptions are explicitly not claimed as the source trial design.
- Add seven required protocol-design QC checks covering alpha reconciliation, dropout inflation, achieved power, unique scenarios, total-N reconciliation and effect/power monotonicity; verified run passes 7/7.
- Record SHA256 of the exact machine-readable design specification used by the calculation.
- Add `docs/protocol_statistical_design.md` and a protocol statistical-review checklist covering design, endpoints, estimand components, multiplicity, sample size, populations, models, safety, programming implications and DSMB/interim-analysis boundaries.
- Update the SAP and README to portfolio version 0.7 with the verified protocol-design outputs and current analysis/QC evidence.
- Expand Python unit tests to 19 while retaining 24/24 Python pipeline QC, 16/16 R/Python programming QC, 11/11 MMRM QC and 15/15 SAP-to-TLF structural traceability.

## 0.6.0 — 2026-08-22

- Add a machine-readable SAP-to-TLF registry for 15 planned outputs spanning safety, ANCOVA and longitudinal MMRM analyses.
- Add executable output contracts checking required files, minimum row counts and required columns.
- Require every planned TLF to resolve to its analysis dataset(s) and QC evidence.
- Record SHA256 identity for every generated TLF output.
- Add an independent CI gate that validates the final generated artifacts rather than only checking static specifications.
- Detect and correct a real T08 specification mismatch (`chg_mean` versus the generated `change_mean`) without weakening the validation rule; the final T08 contract also requires baseline, Week 24 and change mean/SD fields.
- Verify 15/15 planned TLFs, 15/15 output files, 15/15 output contracts, 15/15 analysis-dataset links and 15/15 QC-evidence links.
- Add `docs/analysis_traceability.md` and extend the CI artifact summary with traceability detail.

## 0.5.0 — 2026-08-22

- Add an observed-data ACTOT longitudinal MMRM using Week 8, Week 16 and Week 24 change from baseline; LOCF values are not used in the repeated-measures model.
- Pre-specify `CHG ~ treatment * visit + baseline * visit` with REML, unstructured within-subject covariance and Satterthwaite degrees of freedom.
- Add a heterogeneous AR(1) covariance sensitivity fit using the same fixed-effects model.
- Add visit-specific estimated marginal means and six active-versus-placebo primary contrasts.
- Verify the MMRM input as 451 observed post-baseline records from 189 subjects: Week 8=189, Week 16=146 and Week 24=116.
- Add 11 required MMRM data/model/inference checks; the verified GitHub Actions run passes 11/11.
- Verify finite primary and sensitivity fits. Unstructured: logLik -1299.3136, AIC 2610.6272, BIC 2630.0777. Heterogeneous AR(1): logLik -1309.7404, AIC 2627.4809, BIC 2640.4479.
- Verify primary Week 24 treatment contrasts: Low Dose vs Placebo -1.6131 (95% CI -3.9216 to 0.6953, p=0.1693); High Dose vs Placebo -0.9271 (95% CI -3.2032 to 1.3489, p=0.4220).
- Add a diagnostic comparison of Week 24 MMRM and the existing observed-case ANCOVA without requiring the estimands to match numerically.
- Add machine-readable MMRM dataset, visit-count, LS-mean, contrast, covariance-sensitivity, model-diagnostic, QC and metrics outputs.
- Extend GitHub Actions with R syntax parsing, `mmrm`/`emmeans` installation, the MMRM analysis gate and retained diagnostic artifacts.
- Expand the SAP and TLF planning documents so efficacy outputs are specified through Table 15, including MMRM and covariance sensitivity.
- Preserve the existing 10/10 Python unit tests, 24/24 required Python pipeline QC checks and 16/16 R/Python cross-language programming checks.

## 0.4.0 — 2026-08-22

- Add an independent R implementation of selected safety and efficacy derivations using the same public DM, EX, DS, AE and official QS inputs.
- Keep executable derivation code separate: R does not call Python derivation functions and reads Python outputs only for the final comparison.
- Independently reproduce randomised, safety and completed populations, TEAE counts and DS treatment-end fallback counts in R.
- Independently reproduce the any-TEAE risk-difference table in R with zero difference at the reported precision.
- Independently reconstruct all 705 CIBIC analysis records with exact R/Python key, `QSSEQ`, `DTYPE` and source-derived `AVAL` agreement.
- Independently reconstruct all 818 ACTOT source rows with exact R/Python key, `AVAL`, `BASE`, `CHG`, baseline-flag and efficacy-flag agreement.
- Refit observed Week 24 and LOCF ANCOVA models in R with the same N and residual df as Python.
- Verify R/Python ANCOVA estimates, standard errors, confidence limits, p-values and baseline references with a maximum numeric difference of `7.11e-15` against a pre-specified `1e-8` tolerance.
- Add 16 required cross-language QC checks; the verified live run passes 16/16 while retaining the existing 10/10 Python unit tests and 24/24 Python pipeline QC checks.
- Pin the CI R runtime to R 4.6.1 and record `jsonlite` 2.0.0 plus full R session information.
- Add an R syntax parse gate before the independent R analysis.
- Add machine-readable R QC, R metrics, R safety/ANCOVA outputs and a dedicated cross-language QC design document.

## 0.3.0 — 2026-08-22

- Add pinned public CDISC QS Dataset-JSON input with 121,749 records.
- Add public `ADQSCIBC` and `ADQSADAS` Dataset-JSON reference inputs.
- Derive 705 CIBIC+ analysis records with Week 8/16/24 analysis windows and LOCF.
- Reproduce 100% of public ADQSCIBC analysis keys, source `QSSEQ` values and `DTYPE` classifications.
- Add source tracing for ten ADQSCIBC reference-value differences; all ten portfolio values match their selected public QS source records.
- Profile public ADQSADAS: 12,463 rows, 254 subjects and 15 ADAS-Cog parameters.
- Add ACTOT baseline/change derivation, descriptive outputs, Week 24 ANCOVA and LOCF sensitivity analysis.
- Reconstruct all 1,016 public selected ACTOT (`ANL01FL=Y`) keys with 100% `QSSEQ` and `DTYPE` agreement.
- Add a separate 11-item ADAS-Cog total recalculation diagnostic without replacing the public source ACTOT values.
- Split structural/source reference checks from informational value-agreement metrics when the public source and public reference disagree.
- Expand unit tests to 10 and required pipeline QC to 24 checks.
- Add a pre-analysis reference profiler to GitHub Actions so discrepancies remain inspectable even when the main workflow fails.
- Verify the complete v0.3 workflow in GitHub Actions with 10/10 unit tests and 24/24 required pipeline QC checks passing.

## 0.2.0 — 2026-08-21

- Use EX to define observed exposure and safety population.
- Add explicit exposure-date source flags and DS-disposition fallback when EX/DM end dates are both missing.
- Separate raw EX duration (`EXDURN_RAW`) from final treatment-window duration (`TRTDURN`) so fallback dates do not hide source-data incompleteness.
- Use DS to derive randomisation, completion and discontinuation.
- Add subject-level exposure summaries and source-date traceability.
- Add related and moderate/severe TEAE flags.
- Add disposition, exposure, severity and any-TEAE risk-difference outputs.
- Expand required QC plan and machine-readable run metrics.
- Expand tests from derivation/QC smoke tests to analysis and sample-size checks.
- Update GitHub Actions to print measurable live-run results and upload outputs.

## 0.1.0

- Initial DM/AE safety workflow with ADSL-style / ADAE-style derivation, TEAE summaries, sample-size utilities and provenance hashing.

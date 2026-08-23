# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, public-reference validation, separate R/Python programming QC, longitudinal MMRM, distinct-package MMRM re-programming, analysis-population identity checks, estimand and missing-data review, deterministic and multiple-imputation sensitivity analyses, Monte Carlo precision QC, protocol-design calculations, randomisation exercises, multiplicity control, executable TLF contracts, structural traceability and statistical change-impact assessment.

> **Evidence boundary:** this is independent public-data portfolio work. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP/multiplicity decisions, validated production programming or formal independent second-programmer validation.

## Current milestone: v0.16

The controlled analysis chain is:

```text
public CDISC data
  -> source-to-analysis derivation and R/Python QC
  -> primary observed-data ACTOT MMRM (mmrm)
  -> independently reconstructed ACTOT analysis rows
  -> distinct-package MMRM reconstruction (nlme)
  -> row-identity + Week 24 estimate/SE validation gate
  -> Week 24 Bonferroni family-wise decision layer
  -> estimand and missingness review
  -> deterministic fixed-delta diagnostic
  -> subject-level MAR/delta MI + MCSE QC
  -> reference-based MI (MAR / JR / CR / CIR) + MCSE QC
  -> analysis-dataset/TLF reviewer
  -> versioned statistical change-impact assessment
  -> executable 23-TLF structural traceability
```

The validated v0.16 formal run verifies:

- **451/451** primary/independent MMRM analysis rows and **189/189** subjects;
- zero missing/extra subject-visit keys, zero treatment mismatches and zero numeric mismatch rows;
- **18/18** blocking cross-package MMRM checks passed;
- maximum Week 24 estimate absolute difference **1.30015e-05** versus tolerance **0.0005**;
- maximum model-based SE absolute difference **2.63230e-06** versus tolerance **0.0005**;
- **23/23** TLF outputs found and contracts passed;
- **23/23** analysis-data links and QC-evidence links resolved;
- **12/12** primary multiplicity QC checks passed;
- family-wise alpha **0.05**, two controlled hypotheses and Bonferroni local alpha **0.025**;
- **0/2** primary hypotheses rejected after multiplicity control;
- **10** simulated change requests assessed across **73** propagated component links;
- **254/254** graph-required impact relationships declared;
- **254/254** required resources resolved;
- zero missing, extra or unresolved required change-control resources.

The v0.16 change-control layer is implemented as a controlled extension over the byte-preserved v0.14 base and v0.15 multiplicity extension. Large previously validated JSON specifications are not rewritten merely to add the new validation dependency layer.

## Public CDISC evidence

The workflow downloads pinned public CDISC efficacy inputs in CI. Key inputs include:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects and 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with exact selected `QSSEQ`/`DTYPE`. `AVAL` agreement is 695/705; the ten source/reference differences remain visible and trace to the selected public QS source row.

For selected ACTOT (`ANL01FL=Y`), **1,016/1,016** selected analysis keys have exact selected `QSSEQ`/`DTYPE` agreement.

## Primary ACTOT MMRM

The target population contains 254 randomised subjects with observed baseline ACTOT. The longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit: `mmrm::mmrm`, REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. Heterogeneous AR(1) is retained as a covariance sensitivity analysis.

| Week 24 contrast | Estimate | SE | 95% CI | Raw p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not source-trial confirmatory results.

## v0.16 cross-package MMRM validation

The validation program does **not** fit from the primary `outputs/mmrm_analysis_dataset.csv`. `R/mmrm_cross_package_qc.R` independently rebuilds the observed Week 8/16/24 ACTOT rows from `outputs/adqs_actot_style.csv`, writes `outputs/mmrm_cross_package_analysis_dataset.csv`, and fits the same fixed-effects mean model with `nlme::gls`.

`corSymm + varIdent` provides a separate implementation of a general unstructured marginal covariance. Week 24 active-versus-placebo contrast vectors are constructed directly from the fitted `nlme` design matrix rather than reusing the primary `emmeans` output.

### Analysis-row identity

The blocking gate first requires unique and identical `STUDYID × USUBJID × AVISIT` key sets, exact treatment agreement and `QSSEQ`/`AVAL`/`BASE`/`CHG` agreement within **1e-12**.

The validated run has:

- primary rows: **451**;
- independent rows: **451**;
- primary subjects: **189**;
- independent subjects: **189**;
- missing keys: **0**;
- extra keys: **0**;
- exact-field mismatch rows: **0**;
- numeric mismatch rows: **0**.

### Cross-package Week 24 agreement

| Contrast | Primary `mmrm` estimate | Independent `nlme` estimate | Estimate abs diff | Primary SE | Independent SE | SE abs diff |
|---|---:|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131494994 | -1.6131364979 | 0.0000130015 | 1.1677899331 | 1.1677873008 | 0.0000026323 |
| High Dose vs Placebo | -0.9271379405 | -0.9271340803 | 0.0000038602 | 1.1511769515 | 1.1511759590 | 0.0000009925 |

The locked absolute tolerances are **0.0005** for both estimates and model-based SEs; treatment-effect signs must also agree. Together with the analysis-row checks, the gate passes **18/18** required checks.

Degrees of freedom and p-values are deliberately **not** compared: the primary `mmrm` model uses Satterthwaite inference, while `nlme` is used here to validate the analysis population, point estimates and model-based SEs rather than to replace the primary inferential engine.

`outputs/mmrm_cross_package_validation_metrics.json` records SHA256 fingerprints for the validation specification, both contrast sources and both analysis datasets.

This is distinct-package re-programming by the same portfolio author, not formal independent second-programmer validation.

## v0.15 multiplicity control

`spec/multiplicity.json` connects the illustrative protocol-design rule to analysis-side decisions. The controlled family contains exactly two Week 24 primary unstructured-MMRM hypotheses:

- `H_LOW`: Low Dose vs Placebo;
- `H_HIGH`: High Dose vs Placebo.

The two-sided family-wise alpha is 0.05. Bonferroni gives local alpha 0.025 and adjusted p-value `min(2 * raw_p, 1)`.

| Hypothesis | Raw p-value | Bonferroni adjusted p-value | Family-wise reject |
|---|---:|---:|---|
| H_LOW | 0.169334 | 0.338669 | No |
| H_HIGH | 0.421970 | 0.843940 | No |

Sensitivity analyses, alternative covariance structures, ANCOVA, fixed-delta analyses and MI sensitivity results are explicitly excluded from this primary family. The non-significant result is retained rather than changing the family or procedure to manufacture significance.

T23 is `outputs/table23_actot_multiplicity.csv`; its executable contract locks the hypothesis identifiers, raw and adjusted p-values, family/local alpha and reject flag structure.

## Estimand and missingness

`spec/estimands.json` defines portfolio estimand `EST-ACTOT-W24-TP`, with treatment discontinuation handled using a treatment-policy strategy. MAR is a working estimator assumption rather than an estimand attribute.

Week 24 has 116 observed and 138 missing outcomes (**54.3% missing**):

| Arm | Target N | Observed | Missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Low Dose | 96 | 27 | 69 | 71.9% |
| High Dose | 72 | 30 | 42 | 58.3% |

The current public run contains zero scheduled ACTOT observations with actual `ADT > EOSDT` among recorded discontinuers under the project estimand timing definition.

## Missing-data sensitivity layers

### v0.12 deterministic fixed-delta

T18 reports a controlled 0-to-6-point fixed-delta grid and T19 reports analytic direction-of-effect tipping points. This is a deterministic mean-shift diagnostic, not subject-level MI.

### v0.13 subject-level MI

Pairwise approximate-Bayesian `rbmi` analyses use Week 8/16/24 ACTOT history, unstructured covariance, REML, **200 imputations**, Week 24 baseline-adjusted ANCOVA and Rubin pooling. An independent gate requires `MCSE(estimate) / pooled SE <= 7.5%`.

T20 is MAR MI; T21 is controlled delta-adjusted MI sensitivity.

### v0.14 reference-based MI

`spec/reference_based_mi.json` evaluates MAR, Jump to Reference (`JR`), Copy Reference (`CR`) and Copy Increments in Reference (`CIR`) using a placebo reference distribution. Recorded discontinuation is anchored to `EOSDT`, and two independent guards block invalid post-ICE strategy switching.

The live analysis identified 68 Low Dose and 39 High Dose subjects with an affected scheduled visit. T22 contains 8 comparison × strategy rows; **27/27** required reference-based checks passed and the maximum `MCSE(estimate) / pooled SE` ratio was **5.381%**.

## Statistical change control

The validated base files remain byte-preserved:

```text
spec/change_impact_graph.json
spec/change_requests.json
```

v0.15 adds multiplicity dependencies through:

```text
spec/change_impact_graph_v0_15_extension.json
spec/change_requests_v0_15_extension.json
```

v0.16 adds cross-package analysis-row/model validation through:

```text
spec/change_impact_graph_v0_16_extension.json
spec/change_requests_v0_16_extension.json
```

The merged logical graph is version `0.16.0` and contains **10 simulated change requests (CR-001–CR-010)**.

Important v0.16 propagation includes:

- CR-003 primary ACTOT visit -> independent row reconstruction, cross-package gate and T23 through existing primary/multiplicity dependencies;
- CR-004 primary MMRM covariance -> cross-package validation and T23;
- CR-005 treatment-discontinuation strategy / MMRM-estimand alignment -> independent row reconstruction, validation outputs and T23;
- CR-009 multiplicity-rule change -> multiplicity spec, primary MMRM input/QC and T23;
- CR-010 cross-package validation-rule change -> row-reconstruction inputs/outputs, validation QC, specification and documentation, with **no invented TLF**.

The validated assessment covers **73 propagated component links**, **254/254 required impact relationships** and **254/254 required resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register **T01–T23** at registry version `0.16.0`. The structural gate requires:

- one common non-empty registry version;
- exact registry/contract ID and output-path agreement;
- generated output existence;
- required columns and minimum rows;
- linked analysis datasets;
- linked QC evidence;
- SHA256 identity for every validated output.

The validated run passes all four **23/23** structural counts. T12 now explicitly requires `outputs/mmrm_cross_package_qc.csv` in addition to the primary MMRM QC. T23 deliberately does not use the cross-package file as multiplicity evidence because the v0.16 layer does not reproduce Satterthwaite df/p-values.

## CI execution control

The GitHub Actions workflow uses branch/event-level concurrency with `cancel-in-progress: true`. A newer commit on the same upgrade branch cancels its superseded long-running run instead of spending a full MI/reference-based-MI cycle validating an obsolete head.

## Key files

```text
R/mmrm_analysis.R                                  primary longitudinal ACTOT MMRM
R/mmrm_cross_package_qc.R                          v0.16 independent rows + nlme MMRM
R/rbmi_sensitivity.R                              v0.13 subject-level MI
R/rbmi_mcse_qc.R                                  independent MI precision gate
R/rbmi_reference_based.R                          v0.14 MAR/JR/CR/CIR sensitivity
src/cdisc_portfolio/mmrm_validation.py             v0.16 row/model comparison gate
src/cdisc_portfolio/multiplicity.py                v0.15 family-wise decision logic
src/cdisc_portfolio/change_control_v016.py         layered v0.16 change-control merger
spec/mmrm_cross_package_validation.json            v0.16 validation scope/tolerances
spec/multiplicity.json                             controlled multiplicity specification
spec/analysis_traceability.csv                     versioned T01-T23 registry
spec/output_contracts.json                         executable TLF contracts
spec/change_impact_graph_v0_16_extension.json      v0.16 dependency extension
spec/change_requests_v0_16_extension.json          CR-010 and v0.16 impact additions
docs/mmrm_cross_package_validation.md              method, live evidence and boundary
docs/qc_plan.md                                    blocking QC stack
```

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
Rscript R/mmrm_cross_package_qc.R
python scripts/run_mmrm_cross_validation.py
python scripts/run_multiplicity.py
python scripts/run_estimand_review.py
python scripts/run_mnar_sensitivity.py
Rscript R/rbmi_sensitivity.R
Rscript R/rbmi_mcse_qc.R
Rscript R/rbmi_reference_based.R
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

Generated evidence is written under `outputs/`; CI uploads the output directory so the exact statistical and governance evidence can be inspected.

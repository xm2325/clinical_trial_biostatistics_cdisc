# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository covers source-to-analysis derivation, safety and efficacy analysis, public-reference validation, separate R/Python programming QC, longitudinal MMRM, estimand and missing-data review, deterministic sensitivity analysis, subject-level multiple imputation (MI), reference-based MI, Monte Carlo precision QC, TLF-style outputs, executable SAP-to-TLF traceability, protocol-design/sample-size calculations, randomisation/initial-kit exercises, analysis-dataset/TLF review and statistical change-control impact assessment.

> **Evidence boundary:** this is independent public-data portfolio work. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP decisions, validated production programming or independent second-programmer validation. Reference-based MI is implemented as a controlled portfolio sensitivity analysis, not as a sponsor-approved or regulatory strategy.

## Current milestone: v0.14

The controlled analysis chain is:

```text
estimand
  -> missingness review
  -> primary observed-data MMRM
  -> deterministic fixed-delta diagnostic
  -> subject-level MAR/delta MI
  -> independent MI Monte Carlo precision QC
  -> reference-based MI (MAR / JR / CR / CIR)
  -> reference-based ICE and MCSE QC
  -> TLF output contracts
  -> statistical change impact
  -> executable structural traceability
```

The machine-readable registry contains **22 planned TLFs (T01-T22)**. The change-control specification contains **8 simulated change requests (CR-001-CR-008)**.

A successful live v0.14 formalisation run verified:

- **22/22** TLFs passed output, contract, analysis-data and QC-evidence traceability;
- **195/195** graph-required change-impact relationships were declared;
- **195/195** required change-impact resources resolved;
- reference-based MI produced the expected 8 comparison × strategy rows;
- all reference-based rows used 200 imputations and Rubin pooling;
- all reference-based rows passed `MCSE(estimate) / pooled SE <= 7.5%`;
- the maximum observed reference-based MCSE ratio was **5.381%**;
- both pairwise reference-based models had zero model-fit failures.

## Public CDISC evidence

The workflow downloads pinned public CDISC efficacy inputs in CI.

Key inputs include:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects and 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with exact selected `QSSEQ` and `DTYPE`. `AVAL` agreement is 695/705 (98.58%); the ten source/reference value differences remain visible and trace to the exact selected public QS source row.

For selected ACTOT (`ANL01FL=Y`), the portfolio reconstructs **1,016/1,016** selected analysis keys with exact selected `QSSEQ` and `DTYPE` agreement.

## Primary ACTOT analysis

The ACTOT target population is 254 randomised subjects with observed baseline ACTOT. Week 24 contains 116 observed and 138 missing outcomes.

The primary longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit: REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. Heterogeneous AR(1) is retained as a covariance sensitivity analysis.

Verified Week 24 primary MMRM contrasts:

| Contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not source-trial confirmatory results.

## Estimand and missingness

`spec/estimands.json` defines portfolio estimand `EST-ACTOT-W24-TP` with treatment discontinuation handled by a treatment-policy strategy. MAR is recorded as a working estimator assumption, not an estimand attribute.

Week 24 missingness is:

| Arm | Target N | Observed | Missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Xanomeline Low Dose | 96 | 27 | 69 | 71.9% |
| Xanomeline High Dose | 72 | 30 | 42 | 58.3% |
| **Overall** | **254** | **116** | **138** | **54.3%** |

The live data contain zero scheduled ACTOT observations with actual `ADT > EOSDT` among recorded discontinuers under the project estimand timing definition.

## v0.12 deterministic fixed-delta analysis

The v0.12 layer is a deterministic pattern-mixture mean-shift diagnostic based on the primary Week 24 MMRM estimate and observed missing proportions. It is not subject-level MI and is not reference-based imputation.

The controlled grid is 0 to 6 ACTOT points by 0.5 under common worsening, active-only worsening and divergent worsening. T18 reports the 78-row grid and T19 reports six analytic direction-of-effect tipping points.

## v0.13 subject-level MI

`spec/mi_sensitivity.json` controls pairwise approximate-Bayesian `rbmi` MI:

- Low Dose versus Placebo and High Dose versus Placebo;
- Week 8/16/24 ACTOT change history;
- unstructured covariance with REML;
- baseline-by-visit and treatment-by-visit terms;
- **200 imputations** per pairwise analysis;
- Week 24 baseline-adjusted ANCOVA;
- Rubin pooling;
- MAR, active +1, active +2 and divergent active +1/placebo -1 scenarios.

An independent precision gate requires `MCSE(estimate) / pooled SE <= 7.5%` for each MAR comparison.

T20 is the pairwise MAR MI output. T21 is the delta-adjusted MI sensitivity output.

## v0.14 reference-based MI

`spec/reference_based_mi.json` adds a controlled reference-based sensitivity analysis while reusing the v0.13 pairwise imputation model and 200-imputation setting.

Recorded treatment discontinuation is aligned with the existing estimand review:

- `DCSFL=Y` identifies recorded discontinuers;
- `EOSDT` is the recorded discontinuation date;
- observed scheduled ACTOT with `ADT <= EOSDT` is retained;
- the first affected visit is the first Week 8/16/24 visit after discontinuation and after all observed pre-discontinuation scheduled outcomes.

Two blocking guards must pass before changing MAR/non-MAR strategy:

1. zero observed scheduled ACTOT records with `ADT > EOSDT`;
2. zero observed ACTOT values on or after the first affected visit supplied to `rbmi`.

The first v0.14 live implementation used `TRTEDT` as the ICE date and was rejected because observed scheduled ACTOT data existed after that date. The definition was corrected to the `EOSDT` timing already used by the estimand review; the guards were retained, not weakened.

Placebo remains MAR and provides the reference distribution. Active-arm discontinuers with an affected scheduled visit are evaluated under:

- `MAR` — Missing at Random;
- `JR` — Jump to Reference;
- `CR` — Copy Reference;
- `CIR` — Copy Increments in Reference.

The successful live run identified 71 Low Dose and 45 High Dose active discontinuers. Of these, 68 and 39 respectively had an affected scheduled visit and entered the reference-based strategy update.

| Comparison | Strategy | Estimate | SE | 95% CI | p-value | Change from MAR |
|---|---|---:|---:|---|---:|---:|
| Low Dose vs Placebo | MAR | -1.4966 | 1.3268 | [-4.1459, 1.1526] | 0.2634 | 0.0000 |
| Low Dose vs Placebo | JR | -0.5353 | 1.0686 | [-2.6536, 1.5830] | 0.6174 | 0.9614 |
| Low Dose vs Placebo | CR | -0.2239 | 1.0601 | [-2.3248, 1.8769] | 0.8331 | 1.2727 |
| Low Dose vs Placebo | CIR | -0.3529 | 1.0785 | [-2.4909, 1.7852] | 0.7442 | 1.1438 |
| High Dose vs Placebo | MAR | -0.6874 | 1.0769 | [-2.8265, 1.4517] | 0.5249 | 0.0000 |
| High Dose vs Placebo | JR | -0.3389 | 1.0359 | [-2.3940, 1.7162] | 0.7442 | 0.3485 |
| High Dose vs Placebo | CR | -0.3195 | 1.0101 | [-2.3220, 1.6829] | 0.7524 | 0.3679 |
| High Dose vs Placebo | CIR | -0.2790 | 1.0201 | [-2.3019, 1.7439] | 0.7850 | 0.4084 |

In this public-data analysis, JR/CR/CIR move both active-minus-placebo point estimates toward zero relative to MAR. This is descriptive of this controlled sensitivity analysis and should not be assumed for other trials.

T22 is `outputs/table22_rbmi_reference_based.csv` and has an executable minimum-row/required-column contract plus linked estimand, ICE, draw and MCSE QC evidence.

## Change control

The v0.14 dependency graph has 8 simulated requests and 195 required downstream relationships. Important propagation paths include:

- CR-003 primary ACTOT visit -> T20/T21/T22;
- CR-005 treatment-discontinuation strategy -> T16-T22 as required by the dependency graph;
- CR-007 v0.13 MI-base assumptions -> T20/T21 and T22 because reference-based MI reuses that base model;
- CR-008 reference-based assumptions -> estimand alignment review, ICE audit, reference-based QC and T22.

The verified run covered **195/195** required relationships with no missing declarations, no extra declarations and no unresolved required resources.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register T01-T22. The final structural gate checks:

- one controlled registry version;
- registry/contract ID agreement;
- generated output existence;
- required columns and minimum rows;
- linked analysis data;
- linked QC evidence;
- SHA256 output identity.

The v0.14 registry version is `0.14.0`.

## Key files

```text
R/independent_qc.R                         separate R reconstruction/QC
R/mmrm_analysis.R                          longitudinal ACTOT MMRM
R/rbmi_sensitivity.R                       v0.13 subject-level MI
R/rbmi_mcse_qc.R                           v0.13 independent MCSE gate
R/rbmi_reference_based.R                   v0.14 MAR/JR/CR/CIR analysis
spec/estimands.json                        ACTOT estimand
spec/mnar_sensitivity.json                 deterministic sensitivity
spec/mi_sensitivity.json                   subject-level MI specification
spec/reference_based_mi.json               reference-based MI specification
spec/analysis_traceability.csv             versioned T01-T22 registry
spec/output_contracts.json                 executable TLF contracts
spec/change_impact_graph.json              statistical dependency graph
spec/change_requests.json                  CR-001 to CR-008
docs/sap.md                                consolidated SAP through v0.13
docs/sap_v0_14_reference_based_addendum.md v0.14 controlled SAP addendum
docs/rbmi_reference_based_sensitivity.md   v0.14 method and live evidence
docs/tlf_shells_v0_14_addendum.md          T22 shell
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
python scripts/run_estimand_review.py
python scripts/run_mnar_sensitivity.py
Rscript R/rbmi_sensitivity.R
Rscript R/rbmi_mcse_qc.R
Rscript R/rbmi_reference_based.R
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

Generated evidence is written under `outputs/`; CI uploads the output directory even for many downstream failures so diagnostics remain inspectable.

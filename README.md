# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, public-reference validation, separate R/Python programming QC, longitudinal MMRM, estimand and missing-data review, deterministic and multiple-imputation sensitivity analyses, Monte Carlo precision QC, protocol-design calculations, randomisation exercises, multiplicity control, executable TLF contracts, structural traceability and statistical change-impact assessment.

> **Evidence boundary:** this is independent public-data portfolio work. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP/multiplicity decisions, validated production programming or independent second-programmer validation.

## Current milestone: v0.15

The controlled analysis chain is:

```text
public CDISC data
  -> source-to-analysis derivation and R/Python QC
  -> primary observed-data ACTOT MMRM
  -> Week 24 Bonferroni family-wise decision layer
  -> estimand and missingness review
  -> deterministic fixed-delta diagnostic
  -> subject-level MAR/delta MI + MCSE QC
  -> reference-based MI (MAR / JR / CR / CIR) + MCSE QC
  -> analysis-dataset/TLF reviewer
  -> versioned statistical change-impact assessment
  -> executable 23-TLF structural traceability
```

The final v0.15 formalisation run verifies:

- **23/23** TLF outputs found and contracts passed;
- **23/23** analysis-data links and QC-evidence links resolved;
- **12/12** primary multiplicity QC checks passed;
- family-wise alpha **0.05**, two controlled hypotheses and Bonferroni local alpha **0.025**;
- **0/2** primary hypotheses rejected after multiplicity control;
- **9** simulated change requests assessed;
- **217/217** graph-required impact relationships declared;
- **217/217** required resources resolved;
- zero missing, extra or unresolved required change-control resources.

The v0.15 change-control layer is intentionally implemented as an extension over the byte-preserved v0.14 base specifications. This avoids rewriting large validated JSON specifications merely to add one new statistical dependency layer.

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

Primary fit: REML, unstructured within-subject covariance and Satterthwaite degrees of freedom. Heterogeneous AR(1) is retained as a covariance sensitivity analysis.

| Week 24 contrast | Estimate | SE | 95% CI | Raw p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not source-trial confirmatory results.

## v0.15 multiplicity control

`spec/multiplicity.json` connects the existing illustrative protocol-design rule to analysis-side decisions. The controlled family contains exactly two Week 24 primary unstructured-MMRM hypotheses:

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

The live v0.14 analysis identified 68 Low Dose and 39 High Dose subjects with an affected scheduled visit. T22 contains 8 comparison × strategy rows; **27/27** required reference-based checks passed and the maximum `MCSE(estimate) / pooled SE` ratio was **5.381%**.

## Statistical change control

v0.15 keeps the validated v0.14 base files unchanged:

```text
spec/change_impact_graph.json
spec/change_requests.json
```

and layers controlled additions through:

```text
spec/change_impact_graph_v0_15_extension.json
spec/change_requests_v0_15_extension.json
```

The merged logical graph is version 0.15.0 and contains **9 simulated change requests (CR-001–CR-009)**.

Important propagation includes:

- CR-003 primary ACTOT visit -> T23 through both planning and primary-contrast dependencies;
- CR-004 primary MMRM covariance -> T23;
- CR-005 treatment-discontinuation strategy / MMRM-estimand alignment -> T23;
- CR-009 multiplicity-rule change -> multiplicity spec, planning spec, primary MMRM input/QC and T23.

The verified run covers **217/217** required relationships and **217/217** required resources, with zero missing declarations, zero extra declarations and zero unresolved resources.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register **T01–T23** at registry version `0.15.0`. The final structural gate requires:

- one common non-empty registry version;
- exact registry/contract ID and output-path agreement;
- generated output existence;
- required columns and minimum rows;
- linked analysis datasets;
- linked QC evidence;
- SHA256 identity for every validated output.

The final v0.15 run passes all four 23/23 structural counts.

## Key files

```text
R/mmrm_analysis.R                              primary longitudinal ACTOT MMRM
R/rbmi_sensitivity.R                          v0.13 subject-level MI
R/rbmi_mcse_qc.R                              independent MI precision gate
R/rbmi_reference_based.R                      v0.14 MAR/JR/CR/CIR sensitivity
src/cdisc_portfolio/multiplicity.py            v0.15 family-wise decision logic
src/cdisc_portfolio/change_control_v015.py     versioned v0.15 change-control merger
spec/multiplicity.json                         controlled multiplicity specification
spec/analysis_traceability.csv                 versioned T01-T23 registry
spec/output_contracts.json                     executable TLF contracts
spec/change_impact_graph_v0_15_extension.json  v0.15 dependency extension
spec/change_requests_v0_15_extension.json      CR-009 and v0.15 impact additions
docs/multiplicity_control.md                   multiplicity method and live evidence
docs/sap_v0_15_multiplicity_addendum.md        versioned SAP addendum
docs/tlf_shells_v0_15_addendum.md              T23 shell
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

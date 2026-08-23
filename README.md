# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, ADaM-style BDS/TTE programming, public-reference validation, separate R/Python programming QC, longitudinal MMRM, distinct-package MMRM re-programming, estimand and missing-data review, multiple-imputation sensitivity analysis, Monte Carlo precision QC, protocol-design calculations, randomisation exercises, multiplicity control, Kaplan–Meier/Cox survival analysis, executable TLF contracts, structural traceability and statistical change-impact assessment.

> **Evidence boundary:** this is independent public-data portfolio work. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does not claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP/multiplicity decisions, validated production programming or formal independent second-programmer validation.

## Current milestone: v0.17

The controlled analysis chain is:

```text
public CDISC / pharmaverse test data
  -> source-to-analysis derivation and R/Python QC
  -> primary observed-data ACTOT MMRM (mmrm)
  -> independently reconstructed ACTOT rows + nlme MMRM validation
  -> Week 24 Bonferroni family-wise decision layer
  -> estimand + missingness review
  -> deterministic fixed-delta sensitivity
  -> subject-level MAR/delta MI + MCSE QC
  -> reference-based MI (MAR / JR / CR / CIR) + MCSE QC
  -> randomized-arm ADTTE-style TTDISC derivation
  -> Kaplan–Meier + exploratory log-rank/Cox retention analysis
  -> analysis-dataset/TLF reviewer
  -> versioned statistical change-impact assessment
  -> executable T01–T25 structural traceability
```

The validated v0.17 live run verifies:

- **254** randomized subjects in the retention analysis;
- planned randomized arm sizes **86 / 84 / 84** for Placebo / Low Dose / High Dose;
- **12** subjects with planned-versus-actual treatment differences, retained as explicit audit evidence rather than reassigned;
- **144** study-discontinuation events and **110** protocol-completion censors;
- **16/16** blocking ADTTE-style derivation checks passed;
- **14/14** blocking R survival-analysis checks passed;
- Day-182 KM retention **67.44% / 29.76% / 33.25%** for Placebo / Low / High;
- exploratory discontinuation HR **3.0852** for Low vs Placebo and **2.9246** for High vs Placebo;
- `cox.zph` p-values **0.8310** and **0.7577**, with zero PH diagnostic signals at alpha 0.05;
- **25/25** TLF outputs, contracts, analysis-data links and QC-evidence links passed;
- **11** simulated change requests across **77** propagated component links;
- **267/267** graph-required impact relationships declared and resolved;
- zero missing, extra or unresolved required change-control resources.

The new T24/T25 retention outputs are **exploratory and separate from the ACTOT confirmatory multiplicity family**.

## Public CDISC evidence

The workflow downloads pinned public CDISC efficacy inputs in CI. Key inputs include:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects and 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with exact selected `QSSEQ`/`DTYPE`. `AVAL` agreement is 695/705; the ten source/reference differences remain visible and trace to the selected public QS source row.

For selected ACTOT (`ANL01FL=Y`), **1,016/1,016** selected analysis keys have exact selected `QSSEQ`/`DTYPE` agreement.

## Primary ACTOT MMRM

The ACTOT analysis uses actual-treatment context from the existing analysis derivation. This is intentionally distinct from the v0.17 randomized-arm retention analysis below.

The longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline:

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

`R/mmrm_cross_package_qc.R` independently rebuilds the observed Week 8/16/24 ACTOT rows from `outputs/adqs_actot_style.csv` rather than reading the primary MMRM analysis dataset. It then fits the same fixed-effects mean model using `nlme::gls` with `corSymm + varIdent` as a separate unstructured marginal-covariance implementation.

The blocking gate validates **451/451** analysis rows and **189/189** subjects, with zero missing/extra keys, zero exact-field mismatches and zero numeric mismatch rows. It passes **18/18** checks. Maximum Week 24 estimate difference is **1.30015e-05** and maximum model-based SE difference is **2.63230e-06**, both well below locked **0.0005** tolerances.

Degrees of freedom and p-values are deliberately not compared because the primary `mmrm` program uses Satterthwaite inference while the `nlme` reconstruction is intended to validate population, point estimates and model-based SEs.

This is distinct-package re-programming by the same portfolio author, not formal independent second-programmer validation.

## v0.15 multiplicity control

The controlled family contains exactly two Week 24 primary unstructured-MMRM hypotheses. Family-wise alpha is 0.05; Bonferroni gives local alpha 0.025.

| Hypothesis | Raw p-value | Bonferroni adjusted p-value | Family-wise reject |
|---|---:|---:|---|
| H_LOW | 0.169334 | 0.338669 | No |
| H_HIGH | 0.421970 | 0.843940 | No |

Sensitivity analyses, alternative covariance structures, ANCOVA, MI analyses and the v0.17 retention endpoint are excluded from this primary family.

## Estimand and missing-data sensitivity

`spec/estimands.json` defines portfolio estimand `EST-ACTOT-W24-TP`, with treatment discontinuation handled using a treatment-policy strategy. MAR is a working estimator assumption rather than an estimand attribute.

The efficacy analysis has 116 observed and 138 missing Week 24 ACTOT outcomes. Its actual-treatment arm counts remain Placebo=86, Low Dose=96 and High Dose=72; these are **not** the randomized TTDISC arm denominators.

Sensitivity layers include:

- T18/T19 deterministic fixed-delta and directional tipping diagnostics;
- T20/T21 subject-level approximate-Bayesian `rbmi` MAR/delta MI with **200 imputations** and independent MCSE QC;
- T22 reference-based MAR/JR/CR/CIR MI with discontinuation timing audit and MCSE QC.

The reference-based layer passes **27/27** required checks; maximum `MCSE(estimate) / pooled SE` is **5.381%** against a 7.5% threshold.

## v0.17 ADTTE-style randomized retention analysis

### Analysis assignment and audit trail

`spec/tte_retention.json` locks the endpoint and analysis rules. One `TTDISC` row is derived per randomized subject:

```text
STARTDT = TRTSDT
ADT     = EOSDT
AVAL    = ADT - STARTDT + 1
DCSFL=Y   -> event, CNSR=0
COMPLFL=Y -> protocol-completion censor, CNSR=1
```

The survival comparison uses **planned randomized assignment**:

```text
ANLTRT = TRT01P
```

`TRT01A` remains in the ADTTE-style dataset as actual-treatment context. `TRTDIFFL`, `ANLTRTSRC`, `CNSRSRC` and `EVNTSRC` preserve treatment and event/censor provenance.

This distinction matters in the public data: **12/254** randomized subjects have `TRT01P != TRT01A`; all 12 were planned High Dose and recorded as actual Low Dose. Reclassifying them by actual treatment would change arm denominators from randomized **86/84/84** to actual **86/96/72** and materially change the retention estimates. v0.17 therefore keeps the randomized comparison on `TRT01P` and audits the mismatch instead of hiding it.

Derivation results:

| Randomized arm | Subjects | Discontinuations | Completion censors |
|---|---:|---:|---:|
| Placebo | 86 | 28 | 58 |
| Xanomeline Low Dose | 84 | 59 | 25 |
| Xanomeline High Dose | 84 | 57 | 27 |

The derivation gate passes **16/16** required checks and records SHA256 identities for the TTE specification, ADSL-style source and ADTTE-style output.

### Kaplan–Meier retention — T24

`R/tte_retention_analysis.R` uses `survival::survfit` with log-log confidence intervals.

| Day | Placebo | Low Dose | High Dose |
|---:|---:|---:|---:|
| 56 | 88.37% | 70.24% | 67.86% |
| 112 | 81.40% | 47.62% | 41.67% |
| 168 | 68.60% | 30.95% | 38.10% |
| 182 | **67.44%** | **29.76%** | **33.25%** |

The KM median is not reached for Placebo. Median TTDISC is **105 days** for Low Dose (95% CI 69–119) and **80 days** for High Dose (95% CI 64–146).

### Pairwise survival diagnostics — T25

| Comparison | Cox HR | 95% CI | Cox p | Log-rank p | `cox.zph` p |
|---|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | **3.0852** | 1.9606–4.8548 | 0.000001 | 3.11e-07 | 0.8310 |
| High Dose vs Placebo | **2.9246** | 1.8557–4.6092 | 0.000004 | 1.31e-06 | 0.7577 |

HR > 1 denotes a higher **study-discontinuation hazard**, not worse efficacy. Cox models use Efron ties. `cox.zph` is a diagnostic rather than an acceptance criterion; the validated run has **0/2** PH signals at alpha 0.05.

No multiplicity adjustment is applied because T25 is explicitly exploratory.

## Statistical change control

The byte-preserved v0.14 base remains layered with versioned extensions:

```text
v0.15 -> multiplicity
v0.16 -> cross-package MMRM validation
v0.17 -> randomized-retention TTE definition / derivation / survival / T24–T25
```

The merged v0.17 graph contains **11 simulated changes (CR-001–CR-011)**. CR-011 covers changes to the retention population, analysis assignment, dates, event/censor rules, KM timepoints and exploratory survival specification.

The validated assessment has:

- **77** propagated component links;
- **267/267** required impact relationships declared;
- **267/267** required resources resolved;
- zero missing, extra or unresolved required resources.

CR-011 requires 13 downstream relationships and impacts only T24/T25; it does not propagate into the ACTOT confirmatory family.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register **T01–T25** at version `0.17.0`.

The live structural gate passes:

- outputs found: **25/25**;
- output contracts: **25/25**;
- analysis-data links: **25/25**;
- QC-evidence links: **25/25**;
- complete TLF validation: **25/25**.

T24 requires the ADTTE derivation and survival QC evidence. T25 additionally exposes planned randomized assignment in the output itself. T23 remains tied to primary `mmrm` inference and multiplicity QC only.

## CI execution control

GitHub Actions uses branch/event-level concurrency with `cancel-in-progress: true`, so superseded upgrade commits do not consume a full MI/reference-based-MI run.

## Key files

```text
R/mmrm_analysis.R                                  primary ACTOT MMRM
R/mmrm_cross_package_qc.R                          independent rows + nlme MMRM
R/tte_retention_analysis.R                         v0.17 KM/log-rank/Cox retention analysis
R/rbmi_sensitivity.R                               subject-level MI
R/rbmi_reference_based.R                           MAR/JR/CR/CIR sensitivity
src/cdisc_portfolio/tte.py                         spec-driven ADTTE-style derivation/QC
src/cdisc_portfolio/mmrm_validation.py             cross-package MMRM gate
src/cdisc_portfolio/change_control_v017.py         layered v0.17 change-control merger
spec/tte_retention.json                             randomized-retention TTE specification
spec/analysis_traceability.csv                     versioned T01–T25 registry
spec/output_contracts.json                         executable TLF contracts
spec/change_impact_graph_v0_17_extension.json      v0.17 dependency extension
spec/change_requests_v0_17_extension.json          CR-011
docs/tte_retention_analysis.md                     v0.17 method and evidence boundary
docs/sap_v0_17_tte_addendum.md                     controlled portfolio SAP addendum
docs/tlf_shells_v0_17_addendum.md                  T24/T25 shells
```

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_tte_retention.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
Rscript R/mmrm_cross_package_qc.R
python scripts/run_mmrm_cross_validation.py
Rscript R/tte_retention_analysis.R
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

Generated evidence is written under `outputs/`; CI uploads the complete output directory so statistical and governance evidence can be inspected from the same run.
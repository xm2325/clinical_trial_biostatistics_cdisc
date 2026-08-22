# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository covers source-to-analysis derivation, safety and efficacy analysis, public-reference validation, separate R/Python programming QC, longitudinal MMRM, estimand/missing-data review, fixed-delta missing-data sensitivity, TLF-style outputs, executable SAP-to-TLF traceability, protocol-design/sample-size calculations, a controlled randomisation/initial-kit exercise, analysis-dataset/TLF review and statistical change-control impact assessment.

> **Evidence boundary:** this is an independent portfolio project. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does **not** claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP decisions, production MNAR multiple imputation or independent second-programmer validation.

## Verified v0.12 live workflow

The full GitHub Actions workflow was executed against downloaded public source data and pinned public CDISC reference files.

| Verification layer | Verified result |
|---|---:|
| Python unit tests | **57/57 passed** |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| ACTOT estimand/missing-data review | **21/21 passed** |
| Fixed-delta sensitivity QC | **19/19 passed** |
| Analysis-dataset/TLF reviewer QC | **24/24 passed** |
| SAP-to-TLF structural traceability | **19/19 TLFs passed** |
| Protocol-design/sample-size QC | **7/7 passed** |
| Randomisation/initial-kit schedule QC | **10/10 passed** |
| Statistical change-impact declarations | **118/118 covered** |
| Statistical change-impact resources resolved | **118/118** |
| Randomised / safety subjects | 254 / 254 |
| Official CDISC QS rows | 121,749 |
| Portfolio-defined TEAE events | 1,116 |
| ACTOT Week 24 observed / missing | 116 / 138 |
| MMRM observed records / subjects | 451 / 189 |
| Fixed-delta sensitivity grid | 78 rows |
| Directional tipping-point output | 6 rows |

The verified R runtime uses **R 4.6.1**, **mmrm 0.3.18** and **emmeans 2.0.4**.

## Analysis and QC flow

```text
Public DM / EX / DS / AE / QS
        |
        +--> Python derivations
        |       +--> ADSL-style / ADAE-style / ACTOT analysis data
        |       +--> safety TLFs
        |       +--> Week 24 ANCOVA + LOCF supportive sensitivity
        |       +--> Python QC
        |
        +--> Public CDISC ADaM references
        |       +--> ADQSCIBC / ADQSADAS key, QSSEQ and DTYPE checks
        |       +--> source-first discrepancy tracing
        |
        +--> Separate R reconstruction
        |       +--> R/Python programming comparison
        |
        +--> Observed ACTOT Week 8 / 16 / 24
        |       +--> primary unstructured REML MMRM
        |       +--> heterogeneous AR(1) covariance sensitivity
        |       +--> estimand / missingness review
        |       +--> fixed-delta sensitivity + directional tipping points
        |
        +--> analysis-dataset / TLF reviewer
        +--> statistical change-impact gate
        +--> 19-TLF output contracts + SHA256 traceability
```

## Public CDISC evidence

The workflow pins the public CDISC pilot repository commit used for the analysis and downloads official Dataset-JSON inputs in CI.

Key efficacy inputs:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects, 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with **100% QSSEQ** and **100% DTYPE** agreement. `AVAL` agreement is 695/705 (98.58%); all ten differences are retained and traced to the exact public QS source row rather than overwritten to force reference agreement.

For official selected ACTOT (`ANL01FL=Y`), the portfolio reconstructs **1,016/1,016** selected analysis keys with exact selected `QSSEQ` and `DTYPE` agreement. Source/reference value differences remain visible as diagnostics.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public raw inputs and does not call the Python derivation functions. Python outputs are read only for the final cross-language comparison.

The verified run passes **16/16 required checks**, covering:

- 254 randomised and 254 safety subjects;
- 110 completed subjects;
- 217 subjects with at least one TEAE and 1,116 TEAE events;
- CIBIC selection and source-derived values;
- ACTOT source records, baseline and change derivations;
- Week 24 and LOCF ANCOVA contrasts.

The maximum current R/Python ANCOVA numerical difference is **4e-14**, below the pre-specified `1e-8` tolerance.

This is a separate implementation by the same portfolio author, not an independent second human programmer.

## ACTOT efficacy analysis

### Primary longitudinal MMRM

The observed-data MMRM uses Week 8, Week 16 and Week 24 ACTOT change from baseline. LOCF records do not enter the model.

```text
CHG ~ treatment * visit + baseline * visit
```

Primary fit: REML, unstructured within-subject covariance, Satterthwaite degrees of freedom. Heterogeneous AR(1) is a covariance sensitivity model.

The verified model input contains **451 observed post-baseline records from 189 subjects**.

| Week 24 contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are portfolio analyses, not the source trial's confirmatory efficacy results.

### Week 24 missingness

The estimand target population is 254 randomised subjects with observed baseline ACTOT.

| Arm | Target N | Observed | Missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Xanomeline Low Dose | 96 | 27 | 69 | 71.9% |
| Xanomeline High Dose | 72 | 30 | 42 | 58.3% |
| **Overall** | **254** | **116** | **138** | **54.3%** |

Among subjects missing Week 24, recorded final disposition is adverse event for 8/27 placebo, 49/69 Low Dose and 34/42 High Dose subjects. These counts describe the public data; they do not establish an MAR or MNAR mechanism.

The current public run contains **0 observed ACTOT arm-visit records after recorded treatment discontinuation**. The treatment-policy retention rule is therefore covered by executable positive/negative fixtures but does not have a positive live-data example in this dataset.

## Estimand and estimator separation

`spec/estimands.json` defines portfolio estimand `EST-ACTOT-W24-TP` using an ICH E9(R1)-style five-attribute structure.

| Attribute | Portfolio specification |
|---|---|
| Treatment | Placebo, Low Dose, High Dose; each active arm versus placebo |
| Population | Randomised subjects with observed baseline ACTOT |
| Variable | Week 24 ACTOT change from baseline |
| Intercurrent event | Treatment discontinuation |
| Strategy | Treatment policy |
| Population summary | Active-minus-placebo adjusted mean change |

The **primary estimator** is the observed-data MMRM above. MAR is recorded as a working estimator assumption, not an estimand attribute. The existing LOCF ANCOVA remains a supportive legacy-style stress test only.

The estimand/missing-data gate passes **21/21 required checks**.

## v0.12 fixed-delta missing-data sensitivity

Version 0.12 adds a transparent pattern-mixture mean-shift diagnostic for departures from the MAR reference analysis. It is deliberately **not** presented as production MNAR multiple imputation or reference-based imputation.

For an active-versus-placebo Week 24 contrast:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

where `m_active` and `m_placebo` are the observed Week 24 missing proportions. ACTOT is treated as lower-is-better; positive delta represents a worse assumed missing outcome.

The controlled grid is **0 to 6 ACTOT points in 0.5-point steps**. Three adverse stress paths are pre-specified:

| Scenario | Active missing outcomes | Placebo missing outcomes |
|---|---|---|
| Common worsening | +delta | +delta |
| Active-only worsening | +delta | unchanged |
| Divergent worsening | +delta | -delta |

Because both primary Week 24 contrasts already have `p >= 0.05` at delta=0, a “loss of significance” tipping point is not informative. The primary v0.12 threshold is the **direction-of-effect crossing**, where the shifted active-minus-placebo point estimate reaches zero.

### Verified directional tipping points

| Scenario | Low Dose vs Placebo | High Dose vs Placebo |
|---|---:|---:|
| Common worsening | **3.985** | **3.442** |
| Active-only worsening | **2.244** | **1.589** |
| Divergent worsening | **1.562** | **1.033** |

All six analytic thresholds fall inside the pre-specified 0–6 grid. The first non-negative 0.5-point grid values bracket the analytic thresholds as required.

The v0.12 gate passes **19/19 required checks**. It requires delta=0 to reproduce the primary MMRM estimate exactly, checks missingness denominators, monotonic adverse movement, analytic/grid agreement and interpretation of the already non-significant primary contrasts.

T18 diagnostic confidence intervals reuse the primary MMRM SE/df after the deterministic delta shift. They do **not** include imputation-model uncertainty and must not be described as Rubin's-rules MI inference.

See `docs/mnar_sensitivity.md` and `docs/sap_v0_12_mnar_addendum.md`.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register **19 planned TLFs**. CI requires every TLF to have:

- objective, population, endpoint and method metadata;
- resolvable source/analysis-data links;
- a generated output file;
- required columns and minimum row count;
- linked QC evidence;
- SHA256 output identity.

The verified v0.12 run passes **19/19** for output existence, output contracts, analysis-dataset links and QC-evidence links.

New sensitivity outputs:

- **T18** — 78-row fixed-delta scenario × contrast × delta grid;
- **T19** — six analytic direction-of-effect tipping points.

## Statistical change control

The machine-readable dependency graph now contains six portfolio change scenarios and propagates review requirements transitively across datasets, TLFs, QC evidence, documents and specifications.

The verified v0.12 run covers **118/118 required impact relationships** and resolves **118/118 required resources** with no missing or extra declarations.

| Scenario | Propagated components | Required impacts | Main TLF scope |
|---|---:|---:|---|
| CR-001 safety population definition | 4 | 18 | T01–T07 |
| CR-002 TEAE follow-up window | 3 | 14 | T04–T07 |
| CR-003 primary ACTOT visit | 9 | 35 | T08–T12, T15, T18–T19 |
| CR-004 primary MMRM covariance | 5 | 15 | T11–T15, T18–T19 |
| CR-005 treatment-discontinuation strategy | 7 | 25 | T11–T19 |
| CR-006 fixed-delta sensitivity assumption | 3 | 11 | T18–T19 |

These are impact-assessment simulations; they do not silently change the analysed portfolio.

## Protocol-design and randomisation exercises

The repository also includes an explicitly illustrative three-arm ACTOT planning exercise with Bonferroni control for two active-versus-placebo comparisons, dropout inflation and achieved-power back-checking. The selected `E2.5_P80` planning scenario drives a deterministic 390-subject stratified permuted-block randomisation/initial-kit exercise.

Verified randomisation properties include **390 unique randomisation IDs**, **390 unique initial-kit codes**, exact **130/130/130** treatment allocation and **10/10** required schedule QC checks.

This is not an IRT/IWRS production schedule and does not model resupply, inventory, expiry, replacement or emergency-unblinding operations.

## Key files

```text
R/independent_qc.R                 separate R derivation/QC path
R/mmrm_analysis.R                  longitudinal ACTOT MMRM
src/cdisc_portfolio/               Python derivation, QC and review code
spec/estimands.json                machine-readable estimand
spec/mnar_sensitivity.json         fixed-delta sensitivity assumptions
spec/analysis_traceability.csv     19-TLF registry
spec/output_contracts.json         executable TLF contracts
spec/change_impact_graph.json      transitive statistical dependency graph
spec/change_requests.json          six simulated change requests
docs/sap.md                        portfolio SAP
docs/mnar_sensitivity.md           v0.12 sensitivity method
docs/sap_v0_12_mnar_addendum.md    controlled v0.12 addendum
```

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript -e 'install.packages(c("jsonlite", "mmrm", "emmeans"))'
Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R

python scripts/run_estimand_review.py
python scripts/run_mnar_sensitivity.py
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

Generated evidence is written under `outputs/`; CI uploads the complete output directory even for many downstream failure modes so QC diagnostics remain inspectable.

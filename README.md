# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository covers source-to-analysis derivation, safety and efficacy analysis, public-reference validation, separate R/Python programming QC, longitudinal MMRM, estimand/missing-data review, deterministic fixed-delta sensitivity, subject-level multiple imputation (MI), Monte Carlo precision QC, TLF-style outputs, executable SAP-to-TLF traceability, protocol-design/sample-size calculations, a controlled randomisation/initial-kit exercise, analysis-dataset/TLF review and statistical change-control impact assessment.

> **Evidence boundary:** this is an independent portfolio project. `*-style` datasets are not claimed to be submission-ready ADaM. The repository does **not** claim sponsor/CRO production, SAS production, DSMB work, regulatory submission experience, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP decisions, validated production programming, independent second-programmer validation or reference-based imputation.

## Current milestone: v0.13

The current controlled analysis chain is:

```text
estimand
  -> missingness review
  -> primary observed-data MMRM
  -> deterministic fixed-delta MNAR diagnostic
  -> subject-level MI sensitivity
  -> Monte Carlo precision QC
  -> TLF output contracts
  -> statistical change impact
  -> executable structural traceability
```

The machine-readable registry now contains **21 planned TLFs (T01-T21)** and the change-control specification contains **7 simulated change requests (CR-001-CR-007)**. T20 and T21 are formal registry outputs with executable output contracts and required QC links; they are not stand-alone analysis files.

The v0.13 subject-level MI specification uses:

- two pairwise analyses: Xanomeline Low Dose vs Placebo and Xanomeline High Dose vs Placebo;
- Week 8/16/24 ACTOT change-from-baseline history;
- approximate-Bayesian `rbmi` MI with unstructured covariance and REML;
- **200 imputations** per pairwise analysis;
- Week 24 baseline-adjusted ANCOVA within each imputed data set;
- Rubin pooling;
- four controlled scenarios: MAR, active +1, active +2, and active +1/placebo -1 for originally missing Week 24 outcomes;
- a separate Monte Carlo precision gate requiring `MCSE(estimate) / pooled SE <= 7.5%` for each MAR comparison.

The fixed-delta v0.12 analysis remains in the repository as a deterministic diagnostic and is not relabelled as MI. The versioned v0.13 SAP/TLF addenda remain as change history; the consolidated `docs/sap.md`, `docs/qc_plan.md`, `docs/tlf_shells.md`, change-control and traceability documents state the current effective v0.13 plan.

## Analysis and QC flow

```text
Public DM / EX / DS / AE / QS
        |
        +--> Python derivations
        |       +--> ADSL-style / ADAE-style / ACTOT analysis data
        |       +--> safety TLFs
        |       +--> Week 24 ANCOVA + LOCF supportive analysis
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
        |       +--> pairwise subject-level MI + Rubin pooling
        |       +--> delta-adjusted MI sensitivity
        |       +--> independent MCSE precision gate
        |
        +--> analysis-dataset / TLF reviewer
        +--> statistical change-impact gate
        +--> 21-TLF output contracts + SHA256 traceability
```

## Public CDISC evidence

The workflow pins the public CDISC pilot repository commit used for the analysis and downloads official Dataset-JSON inputs in CI.

Key efficacy inputs:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects, 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with **100% QSSEQ** and **100% DTYPE** agreement. `AVAL` agreement is 695/705 (98.58%); all ten differences remain visible and are traced to the exact public QS source row rather than overwritten to force reference agreement.

For official selected ACTOT (`ANL01FL=Y`), the portfolio reconstructs **1,016/1,016** selected analysis keys with exact selected `QSSEQ` and `DTYPE` agreement. Source/reference value differences remain visible as diagnostics.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public raw inputs and does not call the Python derivation functions. Python outputs are read only for the final cross-language comparison.

The cross-language checks cover randomised/safety/completion populations, TEAE outputs, CIBIC selection/source values, ACTOT source records/baseline/change and Week 24/LOCF ANCOVA contrasts. The observed numerical ANCOVA differences are far below the pre-specified `1e-8` tolerance.

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

The current public run contains **0 observed ACTOT arm-visit records after recorded treatment discontinuation**. The treatment-policy retention rule is therefore covered by executable positive/negative fixtures but has no positive live-data example in this dataset.

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

The primary estimator is the observed-data MMRM. MAR is recorded as a working estimator assumption, not an estimand attribute. The existing LOCF ANCOVA remains a supportive legacy-style stress test only.

## v0.12 deterministic fixed-delta sensitivity

Version 0.12 added a transparent pattern-mixture mean-shift diagnostic for departures from the MAR reference analysis. It is deliberately not presented as MI or reference-based imputation.

For an active-versus-placebo Week 24 contrast:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

The controlled grid is 0 to 6 ACTOT points in 0.5-point steps under common worsening, active-only worsening and divergent worsening paths. Because both primary Week 24 contrasts already have `p >= 0.05` at delta=0, the controlled tipping threshold is the direction-of-effect crossing rather than loss of significance.

Verified directional thresholds from the deterministic diagnostic are 3.985/3.442 (common), 2.244/1.589 (active-only) and 1.562/1.033 (divergent) for Low/High Dose versus Placebo respectively.

T18 diagnostic confidence intervals reuse primary MMRM SE/df after the deterministic shift. They do not include imputation uncertainty and must not be described as Rubin-pooling inference.

## v0.13 subject-level MI sensitivity

T20 reports one MAR row per active-versus-placebo comparison. T21 reports **8 rows** from 2 comparisons × 4 controlled scenarios. Delta shifts can be applied only to outcomes that were originally missing at Week 24; observed Week 24 values and non-Week-24 outcomes must remain unchanged.

Required evidence includes:

- `outputs/table20_rbmi_mar_pairwise.csv`;
- `outputs/table21_rbmi_delta_sensitivity.csv`;
- `outputs/rbmi_mi_qc.csv`;
- `outputs/rbmi_mcse_qc.csv`;
- `outputs/rbmi_draw_diagnostics.csv` for T20;
- `outputs/rbmi_delta_audit.csv` for T21.

The MI analysis is a sensitivity analysis alongside the primary observed-data MMRM. MAR MI versus primary MMRM equality is not an acceptance criterion because the estimators differ.

## Executable TLF traceability

`spec/analysis_traceability.csv` and `spec/output_contracts.json` register **21 planned TLFs**. CI requires every TLF to have objective/population/endpoint/method metadata, resolvable analysis-data links, a generated output, required columns/minimum rows, linked QC evidence and SHA256 output identity.

Current sensitivity outputs are:

- **T18** — 78-row deterministic fixed-delta grid;
- **T19** — six analytic direction-of-effect tipping points;
- **T20** — MAR subject-level MI pairwise analysis, minimum 2 rows;
- **T21** — delta-adjusted MI sensitivity, minimum 8 rows.

## Statistical change control

The machine-readable dependency graph contains **seven** simulated change requests. CR-007 controls v0.13 MI assumptions including number of imputations, the longitudinal imputation model, Monte Carlo precision threshold and delta scenarios.

The dependency graph also prevents the MI outputs from becoming stale when upstream assumptions change. In particular, CR-003 (primary ACTOT visit) and CR-005 (treatment-discontinuation/intercurrent-event strategy) propagate to T20/T21 and their linked QC/specification review. The fixed-delta CR-006 continues to govern T18/T19.

These are impact-assessment simulations; they do not silently change the analysed portfolio.

## Key files

```text
R/independent_qc.R                    separate R derivation/QC path
R/mmrm_analysis.R                     longitudinal ACTOT MMRM
src/cdisc_portfolio/                  Python derivation, QC and review code
spec/estimands.json                   machine-readable estimand
spec/mnar_sensitivity.json            deterministic fixed-delta assumptions
spec/mi_sensitivity.json              v0.13 subject-level MI assumptions
spec/analysis_traceability.csv        21-TLF registry
spec/output_contracts.json            executable TLF contracts
spec/change_impact_graph.json         transitive statistical dependency graph
spec/change_requests.json             seven simulated change requests
docs/sap.md                           consolidated effective SAP
docs/sap_v0_13_rbmi_addendum.md       v0.13 MI change record
docs/tlf_shells.md                    consolidated T01-T21 shells
docs/tlf_shells_v0_13_addendum.md     v0.13 T20/T21 change record
docs/qc_plan.md                       consolidated QC plan
docs/analysis_traceability.md         executable traceability design
docs/change_control_impact_assessment.md  statistical change-control design
```

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript -e 'install.packages(c("jsonlite", "mmrm", "emmeans", "rbmi"))'
Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R

python scripts/run_estimand_review.py
python scripts/run_mnar_sensitivity.py
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

The GitHub Actions workflow additionally executes the controlled v0.13 MI and MCSE gates. Generated evidence is written under `outputs/`; CI retains the output directory for inspection on many downstream failure paths.
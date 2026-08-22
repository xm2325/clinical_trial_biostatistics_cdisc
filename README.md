# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible clinical-trial biostatistics work sample built from public CDISC pilot data and public pharmaverse SDTM test data.

The repository demonstrates source-to-analysis derivation, safety and efficacy analysis, TLF-style outputs, public-reference validation, separate R/Python programming QC, longitudinal MMRM, machine-readable estimands and missing-data review, executable SAP-to-TLF traceability, protocol-design/sample-size calculations, a controlled portfolio randomisation/initial-kit schedule, analysis-dataset/TLF review and statistical change-control impact assessment.

> **Evidence boundary:** this is an independent portfolio project. Outputs are labelled `*-style` where they are not claimed to be submission-ready ADaM. The repository does **not** claim sponsor/CRO production, SAS production, DSMB, regulatory-submission, formal ADaM conformance, IRT/IWRS production, sponsor-approved estimand/SAP decisions or independent second-programmer validation experience. Change requests are portfolio simulations rather than approved protocol/SAP amendments.

## Verified v0.11 live workflow

The workflow is executed in GitHub Actions against downloaded public source data and pinned public CDISC reference files.

| Verification layer | v0.11 result |
|---|---:|
| Python unit tests | **49/49** final-head target |
| Required Python pipeline QC | **24/24 passed** |
| Required R/Python cross-language QC | **16/16 passed** |
| Required MMRM QC | **11/11 passed** |
| ACTOT estimand/missing-data review | **21/21 passed** |
| Analysis-dataset/TLF reviewer QC | **24/24 passed** |
| SAP-to-TLF structural traceability | **17/17 TLFs passed** |
| Protocol-design/sample-size QC | **7/7 passed** |
| Randomisation/initial-kit schedule QC | **10/10 passed** |
| Statistical change-impact declarations | **88/88 covered** |
| Statistical change-impact resources resolved | **88/88** |
| Randomised / safety subjects | 254 / 254 |
| Official CDISC QS rows | 121,749 |
| Portfolio-defined TEAE events | 1,116 |
| ACTOT Week 24 observed / missing | 116 / 138 |
| MMRM observed records / subjects | 451 / 189 |

The verified R runtime uses **R 4.6.1**, **mmrm 0.3.18** and **emmeans 2.0.4**.

## Analysis and validation flow

```text
Public DM / EX / DS / AE / QS
        |
        +--> Python derivations --> ADSL-style / ADAE-style / questionnaire analysis data
        |                           |
        |                           +--> safety TLFs
        |                           +--> Week 24 ANCOVA + LOCF sensitivity
        |                           +--> Python QC
        |
        +--> Public CDISC ADaM references --> key / source-row / DTYPE validation
        |
        +--> Separate R reconstruction --> R/Python programming comparison
        |
        +--> Observed ACTOT Week 8/16/24 --> longitudinal MMRM + covariance sensitivity
        |                                      |
        |                                      +--> estimand/estimator alignment
        |                                      +--> missingness + disposition review (T16/T17)
        |
        +--> Dataset contracts + cross-dataset reviewer --> TLF denominator reconciliation
        |
        +--> Change request + dependency graph --> downstream dataset/TLF/QC/document/spec impact gate
        |
        +--> SAP/TLF registry --> output contracts --> QC evidence --> SHA256 output identity

Machine-readable protocol-design assumptions
        |
        +--> multiplicity + sample size + dropout inflation + achieved-power back-check
        |
        +--> selected E2.5_P80 scenario (390 randomisations)
                |
                +--> stratified permuted-block randomisation
                +--> blinded / unblinded schedule separation
                +--> treatment-coded initial-kit allocation
                +--> schedule QC + output hashes
```

## ACTOT estimand and missing-data review

Version 0.11 adds a machine-readable estimand specification in `spec/estimands.json`, following the ICH E9(R1)-style separation between the scientific estimand and the estimator.

### Portfolio estimand `EST-ACTOT-W24-TP`

| Attribute | Specification |
|---|---|
| Treatment | Placebo, Xanomeline Low Dose, Xanomeline High Dose; each active arm versus placebo |
| Population | Randomised subjects with observed baseline ACTOT |
| Variable | ACTOT change from baseline at Week 24 |
| Intercurrent event | Treatment discontinuation |
| Strategy | Treatment policy: retain observed outcomes after discontinuation |
| Population summary | Active-versus-placebo difference in adjusted mean change at Week 24 |

The **primary estimator remains the observed-data REML MMRM** with treatment-by-visit and baseline-by-visit fixed effects, unstructured covariance and Satterthwaite degrees of freedom. Its working missing-data assumption is recorded as MAR. MAR is an estimator assumption, not one of the estimand attributes.

The existing Week 24 LOCF ANCOVA is retained only as a supportive legacy-style sensitivity/stress test. LOCF rows do not enter the primary MMRM and LOCF does not define the treatment-policy estimand.

### Live missingness evidence

The target denominator is all 254 randomised subjects with an observed baseline ACTOT score.

| Arm | Target N | Week 24 observed | Week 24 missing | Missing % |
|---|---:|---:|---:|---:|
| Placebo | 86 | 59 | 27 | 31.4% |
| Xanomeline Low Dose | 96 | 27 | 69 | 71.9% |
| Xanomeline High Dose | 72 | 30 | 42 | 58.3% |
| **Overall** | **254** | **116** | **138** | **54.3%** |

The Week 24 disposition-context table shows that **49/69** Low Dose missing subjects and **34/42** High Dose missing subjects have a recorded final disposition of adverse event; Placebo has **8/27**. These are descriptive counts from the public data, not evidence that a particular missing-data mechanism is true.

The current public run identifies **0 observed ACTOT arm-visit records after recorded treatment discontinuation**. Therefore the treatment-policy retention rule is executable and covered by positive/negative unit-test fixtures, but this live dataset does not provide a positive post-discontinuation retention example. The portfolio does not invent one.

The estimand gate passes **21/21 required checks** covering five-attribute completeness, treatment/visit definition, ICH strategy labels, primary MMRM/no-LOCF specification, missingness denominator reconciliation, Week 24 disposition reconciliation, exact observed-record alignment and treatment-policy retention logic.

Generated evidence includes:
- `outputs/table16_actot_missingness_by_visit.csv`;
- `outputs/actot_missingness_patterns.csv`;
- `outputs/table17_week24_missingness_by_disposition.csv`;
- `outputs/estimand_review.csv`;
- `outputs/estimand_metrics.json`;
- `outputs/estimand_summary.md`.

The descriptive review does not establish that MAR is clinically plausible and does not infer unrecorded rescue medication, switching or other intercurrent events from absent source fields.

## Public-reference validation

### CIBIC+

The portfolio derives 705 `ADQSCIBC-style` analysis records from public SDTM `QS` records with `QSTESTCD=CIBIC`.

| Check | Verified result |
|---|---:|
| Analysis-key coverage | **100% (705/705)** |
| `QSSEQ` source-row agreement | **100%** |
| `DTYPE` agreement | **100%** |
| `AVAL` agreement | 98.58% (695/705) |

The ten `AVAL` differences are not overwritten. In all ten cases the portfolio value equals the selected public SDTM QS `QSSTRESN`, while the public reference ADaM value differs from that selected source row. The discrepancy trace is retained in `outputs/adqscibc_mismatch_source_trace.csv`.

### ADQSADAS / ACTOT

The public `ADQSADAS` reference contains 12,463 rows for 254 subjects across 15 ADAS-Cog parameters. The portfolio reconstructs all 1,016 selected ACTOT analysis keys with exact selected `QSSEQ` and `DTYPE` agreement while keeping source-derived values visible when source and reference differ.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public raw inputs and does not call the Python derivation code. Python outputs are read only for the final cross-language comparison.

The live workflow passes **16/16 required checks**. Safety counts, TEAE outputs, CIBIC selection, ACTOT derivations and Week 24/LOCF ANCOVA outputs reconcile across the two implementations. The latest maximum R/Python ANCOVA numerical difference is **4e-14**, below the pre-specified `1e-8` tolerance.

This remains a separate implementation by the same portfolio author, not review by a second independent programmer.

## ACTOT efficacy analyses

### Week 24 ANCOVA and LOCF sensitivity

```text
Week 24 AVAL = intercept + treatment + centred baseline + error
```

| Analysis | Contrast | Estimate | 95% CI | p-value |
|---|---|---:|---:|---:|
| Observed Week 24 | Low Dose vs Placebo | -2.028 | [-4.596, 0.539] | 0.1204 |
| Observed Week 24 | High Dose vs Placebo | -0.923 | [-3.411, 1.564] | 0.4635 |
| LOCF sensitivity | Low Dose vs Placebo | -1.218 | [-2.830, 0.394] | 0.1378 |
| LOCF sensitivity | High Dose vs Placebo | -1.191 | [-2.921, 0.538] | 0.1760 |

Observed Week 24 uses 116 subjects; the separate LOCF sensitivity uses 235 subjects.

### Longitudinal MMRM

The longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline; LOCF records are not used.

```text
CHG ~ treatment * visit + baseline * visit
```

The primary fit uses REML, unstructured within-subject covariance and Satterthwaite df; heterogeneous AR(1) is a covariance sensitivity analysis. The verified MMRM contains **451 observations from 189 subjects** and passes **11/11 required MMRM QC checks**.

| Week 24 contrast | Estimate | SE | 95% CI | p-value |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

These are independent portfolio analyses, not the source trial's confirmatory efficacy results.

## Analysis-dataset and TLF reviewer gate

The blocking reviewer layer runs after generated analysis datasets/MMRM and checks cross-file consistency rather than repeating derivation code.

The live workflow retains **24/24 required reviewer checks** across analysis-dataset parentage, derivations, metadata contracts, population consistency, TLF denominators and TLF structure. Five machine-readable dataset contracts cover ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM.

The correctly reconstructed randomised/safety arm denominators are **86 Placebo, 96 Low Dose and 72 High Dose**. Observed Week 24 Ns are **59 Placebo, 27 Low Dose and 30 High Dose**. Historical prose labels that swapped these arm names were corrected in v0.11; the analysis outputs themselves were unchanged.

Negative controls deliberately corrupt treatment consistency, a safety-table denominator, MMRM `CHG`, a required dataset column and a controlled flag; validators must reject them.

This is same-author portfolio review, not formal ADaM conformance assessment, sponsor programming review or independent second-programmer sign-off.

## Statistical change-control impact gate

Version 0.11 extends the machine-readable dependency graph to estimand and missingness governance. `spec/change_impact_graph.json` and `spec/change_requests.json` must declare the same version; a mismatch is now a hard failure rather than producing a stale version label.

The live v0.11 specifications cover **88/88 graph-required impact relationships** and resolve **88/88 required resources** across five scenarios:

| Scenario | Propagated components | Required impacts | Impacted TLFs |
|---|---:|---:|---|
| CR-001 Safety population definition | 4 | 18 | T01–T07 |
| CR-002 TEAE follow-up window | 3 | 14 | T04–T07 |
| CR-003 Primary ACTOT visit | 6 | 27 | T08–T12, T15 |
| CR-004 Primary MMRM covariance | 3 | 11 | T11–T15 |
| CR-005 Treatment-discontinuation strategy | 4 | 18 | T11–T17 |

CR-005 is an illustrative change from treatment-policy to hypothetical handling of discontinuation. It forces review of the estimand specification, MMRM path, longitudinal TLFs, T16/T17, QC and controlled documentation. It does **not** change the current analysed treatment-policy estimand.

Other scenarios likewise do not silently change the current 30-day TEAE rule, Week 24 analysis focus or unstructured primary MMRM.

## Executable SAP-to-TLF traceability

The registry now covers **17 planned TLFs**. CI requires a planned objective/population/endpoint/method, resolvable source and analysis-dataset links, an actual output, a passing output contract, linked QC evidence and SHA256 output identity. T16/T17 are linked directly to `outputs/estimand_review.csv`.

The v0.11 first-pass live run passes **17/17** structural traceability across output existence, output contracts, analysis-dataset links and QC-evidence links.

## Protocol design and sample-size exercise

The machine-readable three-arm Week 24 ACTOT planning exercise is explicitly a portfolio scenario rather than the original study design.

Assumptions: 1:1:1 allocation, two active-versus-placebo comparisons, two-sided family-wise alpha 0.05, Bonferroni alpha 0.025 per comparison, common planning SD 6.0, 15% anticipated dropout, target power 80%/90%, and mean-difference scenarios 2.0/2.5/3.0.

| Scenario | Effect | Power | Evaluable N/arm | Randomised N/arm | Total randomised | Back-checked power |
|---|---:|---:|---:|---:|---:|---:|
| E2.0_P80 | 2.0 | 80% | 172 | 203 | 609 | 0.802 |
| E2.0_P90 | 2.0 | 90% | 224 | 264 | 792 | 0.901 |
| E2.5_P80 | 2.5 | 80% | 110 | 130 | 390 | 0.802 |
| E2.5_P90 | 2.5 | 90% | 143 | 169 | 507 | 0.900 |
| E3.0_P80 | 3.0 | 80% | 77 | 91 | 273 | 0.805 |
| E3.0_P90 | 3.0 | 90% | 100 | 118 | 354 | 0.902 |

The design gate passes **7/7 required checks**.

## Randomisation and initial-kit schedule

The illustrative `E2.5_P80` scenario drives a reproducible 390-subject stratified permuted-block randomisation/initial-kit schedule. This is not an IRT/IWRS production schedule.

| Schedule property | Verified result |
|---|---:|
| Randomisation numbers | **390** |
| Unique initial-kit codes | **390** |
| Treatment allocation | **130 / 130 / 130** |
| Strata | **5** |
| Allocation within each stratum | **26 / 26 / 26** |
| Permuted blocks | **87** |
| Block-size 3 / block-size 6 | **44 / 43** |
| Required schedule QC | **10/10 passed** |
| Kit-to-treatment mismatches | **0** |

The blinded schedule exposes only `randomisation_id`, `stratum` and `kit_id`; treatment, blind code and block structure remain in unblinded portfolio outputs. Production seed/list access, independent verification, IRT/vendor validation, emergency unblinding and drug-supply operations are outside the claimed scope.

## Safety analysis

The safety population requires at least one observed EX record. The portfolio-defined TEAE window is treatment start through 30 days after treatment end, with documented disposition-date fallback where exposure end is unavailable.

| Comparison | Active risk | Placebo risk | Risk difference | 95% Wald CI | Fisher p |
|---|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | 0.8750 | 0.7558 | +0.1192 | [0.0068, 0.2315] | 0.053041 |
| High Dose vs Placebo | 0.9444 | 0.7558 | +0.1886 | [0.0835, 0.2937] | 0.001726 |

These comparisons are exploratory and not multiplicity-adjusted.

## Key reviewer documents

- `docs/protocol_summary.md` — portfolio protocol scope and analysis populations.
- `docs/sap.md` — core portfolio SAP.
- `docs/sap_v0_9_review_addendum.md` — dataset/TLF review addendum.
- `docs/sap_v0_10_change_control_addendum.md` — statistical change-control addendum.
- `docs/sap_v0_11_estimand_addendum.md` — ACTOT estimand/missing-data addendum.
- `docs/estimand_missing_data_review.md` — estimand, missingness, assumptions, failure rules and limitations.
- `docs/tlf_shells.md` — T01–T17 definitions and output structure.
- `docs/analysis_traceability.md` — executable SAP-to-TLF traceability design.
- `docs/analysis_dataset_spec.md` — source-to-analysis mappings and dataset contracts.
- `docs/analysis_dataset_review.md` — reviewer rules, negative controls and CI evidence.
- `docs/change_control_impact_assessment.md` — dependency graph and change-impact design.
- `docs/protocol_statistical_design.md` — protocol-design and sample-size rationale.
- `docs/protocol_statistical_review_checklist.md` — protocol statistical-review checklist.
- `docs/randomisation_kit_schedule.md` — randomisation/blinding boundary and initial-kit QC.
- `docs/qc_plan.md` — required and informational QC through v0.11.
- `docs/independent_programming_qc.md` — cross-language QC design.

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
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

Analysis scripts cache public inputs under `cache/`. GitHub Actions runs the same calculation/QC chain and uploads generated `outputs/` as an artifact, including estimand, missingness, reviewer and change-impact diagnostics when available.

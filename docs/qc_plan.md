# QC plan — portfolio version 0.13

The workflow separates derivation QC, public-reference validation, separate R/Python programming checks, MMRM model/data QC, estimand/missing-data review, deterministic fixed-delta sensitivity QC, subject-level multiple-imputation (MI) QC, Monte Carlo precision QC, analysis-dataset/TLF review, statistical change-impact assessment and final SAP-to-TLF traceability. Required failures exit non-zero.

Informational discrepancies remain visible rather than being converted into arbitrary acceptance rules. Aggregate unit-test totals are not part of the controlled QC specification because the test suite can increase without changing the statistical acceptance rules.

## v0.13 blocking QC stack

The current workflow requires all of the following layers to succeed on the same commit:

1. Python unit/regression tests;
2. core Python derivation/pipeline QC;
3. public CDISC reference validation;
4. separate R/Python programming QC;
5. MMRM data/model/inference QC;
6. estimand and missing-data review;
7. deterministic fixed-delta sensitivity QC;
8. subject-level MI model/pooling/delta-application QC;
9. independent Monte Carlo precision QC;
10. analysis-dataset/TLF reviewer;
11. protocol-design QC;
12. randomisation/initial-kit QC;
13. statistical change-impact gate;
14. **21-TLF** structural traceability.

Documentation consistency is part of release readiness: a release candidate is not accepted from an earlier implementation-only head. The final documentation head must itself pass the complete CI workflow.

## Core Python pipeline

The core checks cover ADSL-/ADAE-style keys and population flags, exposure/treatment dates, disposition, portfolio TEAE timing, CIBIC/ACTOT derivations, Week 24 analysis sets and official-reference structural/source-row agreement.

Blocking examples include:

- safety subjects must have observed exposure and usable treatment dates;
- portfolio-defined TEAEs cannot occur outside the safety population or the controlled treatment-emergent window;
- ACTOT `CHG = AVAL - BASE`;
- observed Week 24 ANCOVA must contain one row per subject;
- official ADQSCIBC analysis-key, `DTYPE` and selected `QSSEQ` agreement must each be 100%.

Reference `AVAL` disagreement is not automatically treated as failure when the selected public source row is the same and the source-derived value is preserved. Such differences remain in explicit source-trace outputs.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public DM/EX/DS/AE/QS inputs and does not call Python derivation functions. Python outputs are read only for the final comparison.

Checks cover population counts, TEAE outputs, CIBIC selection/source values, ACTOT source rows/baseline/change and Week 24/LOCF ANCOVA inference. Numerical agreement is evaluated against the controlled `1e-8` tolerance.

This is same-author cross-language replication, not validation by a second independent programmer.

## MMRM QC

`R/mmrm_analysis.R` uses observed Week 8, Week 16 and Week 24 ACTOT records; LOCF rows do not enter the repeated-measures model.

Required checks cover:

- planned treatment/visit levels;
- subject-visit uniqueness;
- exact `CHG = AVAL - BASE`;
- within-subject baseline consistency;
- finite likelihood for unstructured and heterogeneous AR(1) fits;
- expected contrast cardinality;
- finite estimate/SE/df/CI/p-value output;
- the two primary Week 24 active-versus-placebo contrasts.

Verified model input: **451 observed post-baseline records from 189 subjects**.

## Estimand and missing-data review

`spec/estimands.json` defines `EST-ACTOT-W24-TP` and keeps the scientific estimand separate from the primary estimator and its assumptions.

The primary estimator remains the unstructured REML MMRM. MAR is a working missing-data assumption, not an estimand attribute. LOCF remains supportive only.

Checks cover five-attribute completeness, treatment/visit definition, treatment-policy handling, exclusion of LOCF from the primary MMRM, target-population/visit denominator reconciliation, disposition reconciliation, exact observed-record alignment and post-discontinuation retention logic.

Verified target population: **254**; Week 24 observed/missing: **116/138**. The public data contain no positive live-data example of observed ACTOT after recorded treatment discontinuation, so the retention rule is also tested with controlled fixtures.

## Deterministic fixed-delta sensitivity QC

`spec/mnar_sensitivity.json` controls the v0.12 fixed-delta pattern-mixture mean-shift diagnostic based on the primary Week 24 MMRM contrast and observed Week 24 missing proportions.

The controlled formula is:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

The grid is **0-6 ACTOT points by 0.5** under three pre-specified adverse scenarios. QC includes complete unique scenario definitions, valid zero-based grid, arm denominators/proportions, finite primary contrasts, the complete **78-row** scenario × contrast × delta grid, exact delta-zero reproduction of primary MMRM estimates, monotone adverse movement and analytic/grid agreement for directional tipping thresholds.

T18 fixed-delta CI/p-value columns reuse primary MMRM SE/df after deterministic mean shift. They are not MI inference.

## v0.13 subject-level MI QC

The controlled specification is `spec/mi_sensitivity.json`. The MI stage runs separately for Low Dose versus Placebo and High Dose versus Placebo with **200 imputations** per pairwise analysis.

Required MI QC includes, at minimum:

- controlled specification/version and method agreement;
- expected pairwise treatment populations and Week 8/16/24 visit grid;
- observed values retained before imputation and missing scheduled outcomes represented as missing;
- approximate-Bayesian `rbmi` model fit with unstructured covariance and REML;
- maximum bootstrap-fit failure fraction not exceeding the controlled 10% limit;
- complete imputation count for each accepted pairwise analysis;
- Week 24 baseline-adjusted ANCOVA on each imputed data set;
- Rubin pooling with finite pooled estimates, SEs, confidence intervals and p-values;
- exactly two MAR active-versus-placebo comparison rows for T20;
- complete 2 comparisons × 4 scenarios = **8 rows** for T21;
- delta shifts applied only to outcomes originally missing at Week 24;
- no delta shift to observed Week 24 outcomes or non-Week-24 outcomes;
- reuse of the controlled imputation draws across MAR and delta scenarios;
- required MI QC and diagnostic artifacts present for downstream traceability.

Required evidence includes:

```text
outputs/rbmi_mi_qc.csv
outputs/rbmi_draw_diagnostics.csv
outputs/rbmi_delta_audit.csv
outputs/rbmi_vs_mmrm_week24.csv
```

The MAR MI estimates are compared with the primary MMRM diagnostically. Numerical equality is not an acceptance rule because the estimators differ.

## Independent Monte Carlo precision QC

Monte Carlo precision is checked separately from model fitting and Rubin pooling. For each MAR active-versus-placebo comparison, CI calculates:

```text
MCSE(estimate) / pooled SE
```

The controlled upper bound is **7.5%**. A run can therefore fail the MCSE gate even when all imputation-model fits succeeded.

Required evidence:

```text
outputs/rbmi_mcse_diagnostics.csv
outputs/rbmi_mcse_qc.csv
```

T20/T21 are not accepted as QC-complete if the required MCSE evidence is absent or the controlled MAR precision criterion fails.

## Analysis-dataset/TLF reviewer

The reviewer remains separate from derivation programs and checks parentage, derivation consistency, dataset contracts, population consistency, TLF denominators and TLF structure. Negative controls corrupt controlled treatment consistency, safety denominators, MMRM `CHG`, required dataset columns and controlled flags; validators must reject them.

## Statistical change-impact gate

The current machine-readable request set contains **seven** simulated change requests.

Acceptance requires:

- graph/request versions to agree;
- changed components to exist;
- the dependency graph to remain acyclic;
- every transitive required impact to be declared;
- required static resources to resolve;
- required generated datasets/QC outputs to exist in the same live run;
- impacted TLFs to resolve through the current TLF registry.

CR-006 controls deterministic fixed-delta assumptions for T18/T19. CR-007 controls MI assumptions including imputation count, longitudinal imputation model, MCSE threshold and delta scenarios for T20/T21.

Regression/negative-control coverage must also protect upstream propagation. Primary ACTOT visit changes (CR-003) and treatment-discontinuation/intercurrent-event strategy changes (CR-005) must reach T20/T21 and their relevant QC/specification review.

## 21-TLF structural traceability

The final traceability gate validates registry/contract agreement, generated files, required columns/minimum rows, analysis-data links, QC links and SHA256 output identity for **T01-T21**.

T20 requires at least **2 rows** and links to MI QC, MCSE QC and draw diagnostics. T21 requires at least **8 rows** and links to MI QC, MCSE QC and the delta audit. A final CSV alone is insufficient for traceability acceptance.

## CI evidence retention

GitHub Actions prints run summaries and retains `outputs/` for many downstream failure paths. This keeps reference-discrepancy traces, model diagnostics, deterministic sensitivity evidence, MI/MCSE evidence, reviewer outputs, change-impact diagnostics and traceability diagnostics available for investigation.
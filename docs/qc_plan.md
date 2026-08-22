# QC plan — portfolio version 0.12

The workflow separates derivation QC, official-reference validation, separate R/Python programming checks, MMRM model/data QC, estimand/missing-data review, fixed-delta sensitivity QC, analysis-dataset/TLF review, statistical change-impact assessment and final SAP-to-TLF traceability. Required failures exit non-zero.

Informational discrepancies remain visible rather than being converted into arbitrary acceptance rules.

## Verified v0.12 QC stack

| Layer | Verified result |
|---|---:|
| Python unit tests | **57/57 passed** |
| Core Python pipeline QC | **24/24 passed** |
| Separate R/Python programming QC | **16/16 passed** |
| MMRM data/model QC | **11/11 passed** |
| Estimand/missing-data review | **21/21 passed** |
| Fixed-delta sensitivity QC | **19/19 passed** |
| Analysis-dataset/TLF reviewer | **24/24 passed** |
| Protocol-design QC | **7/7 passed** |
| Randomisation/initial-kit QC | **10/10 passed** |
| Structural TLF traceability | **19/19 passed** |
| Change-impact relationships | **118/118 covered and resolved** |

## Core Python pipeline

The 24 required checks cover ADSL-/ADAE-style keys and population flags, exposure/treatment dates, disposition, portfolio TEAE timing, CIBIC/ACTOT derivations, Week 24 analysis sets and official-reference structural/source-row agreement.

Examples of blocking conditions:

- safety subjects must have observed exposure and usable treatment dates;
- portfolio-defined TEAEs cannot occur outside the safety population or the controlled treatment-emergent window;
- ACTOT `CHG = AVAL - BASE`;
- observed Week 24 ANCOVA must contain one row per subject;
- official ADQSCIBC analysis-key, `DTYPE` and selected `QSSEQ` agreement must each be 100%.

Reference `AVAL` disagreement is not automatically treated as failure when the selected public source row is the same and the source-derived value is preserved. Such differences are retained in explicit source-trace outputs.

## Separate R/Python programming QC

`R/independent_qc.R` starts from the same cached public DM/EX/DS/AE/QS inputs and does not call Python derivation functions. Python outputs are read only for the final comparison.

The 16 required checks cover population counts, TEAE outputs, CIBIC selection/source values, ACTOT source rows/baseline/change and Week 24/LOCF ANCOVA inference. The verified maximum R/Python ANCOVA numerical difference is **4e-14**, below the controlled `1e-8` tolerance.

This is same-author cross-language replication, not independent validation by a second programmer.

## MMRM QC

`R/mmrm_analysis.R` uses observed Week 8, Week 16 and Week 24 ACTOT records; LOCF rows do not enter the repeated-measures model.

The 11 required checks cover:

- all planned treatment/visit levels;
- subject-visit uniqueness;
- exact `CHG = AVAL - BASE`;
- within-subject baseline consistency;
- finite likelihood for unstructured and heterogeneous AR(1) fits;
- expected primary contrast cardinality;
- finite estimate/SE/df/CI/p-value output;
- two primary Week 24 active-versus-placebo contrasts.

Verified input: **451 observed post-baseline records / 189 subjects**.

## Estimand and missing-data review

`spec/estimands.json` defines `EST-ACTOT-W24-TP` and separates the scientific estimand from the primary estimator and its assumptions.

The primary estimator remains the unstructured REML MMRM. MAR is a working missing-data assumption, not an estimand attribute. LOCF remains supportive only.

The 21 required checks cover five-attribute completeness, treatment/visit definition, treatment-policy handling, no LOCF in the primary model, target-population/visit denominator reconciliation, disposition reconciliation, exact observed-record alignment and post-discontinuation retention logic.

Verified target population: **254**; Week 24 observed/missing: **116/138**. The current public data contain **0 observed ACTOT arm-visit records after recorded treatment discontinuation**; the retention rule is therefore unit-tested with fixtures but has no positive live-data example.

## v0.12 fixed-delta sensitivity QC

`spec/mnar_sensitivity.json` controls a fixed-delta pattern-mixture mean-shift diagnostic based on the primary Week 24 MMRM contrast and observed Week 24 missing proportions.

The controlled formula is:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

The grid is **0–6 ACTOT points by 0.5** under three pre-specified adverse scenarios.

The **19 required checks** include:

1. version/method/endpoint/reference-analysis consistency;
2. complete unique scenario definitions and numeric multipliers;
3. valid zero-based delta grid;
4. all three Week 24 arm denominators and proportions;
5. both finite primary Week 24 MMRM contrasts;
6. complete **78-row** scenario × contrast × delta grid;
7. exact delta-zero reproduction of primary MMRM estimates to `1e-12`;
8. positive adverse shift coefficients for the current configured scenarios;
9. monotone movement under increasing adverse delta;
10. finite positive analytic directional tipping deltas;
11. grid bracketing of each analytic threshold within one 0.5-point step;
12. correct `not applicable` loss-of-significance status because current primary p-values are already >=0.05.

Verified directional tipping deltas:

| Scenario | Low Dose vs Placebo | High Dose vs Placebo |
|---|---:|---:|
| Common worsening | 3.985 | 3.442 |
| Active-only worsening | 2.244 | 1.589 |
| Divergent worsening | 1.562 | 1.033 |

All six thresholds lie inside the controlled grid.

T18 fixed-delta confidence intervals reuse the primary MMRM SE/df after deterministic mean shift. They do not include MI model/delta uncertainty and are not Rubin's-rules inference.

## Analysis-dataset/TLF reviewer

The reviewer remains separate from the derivation programs and checks parentage, derivation consistency, dataset contracts, population consistency, TLF denominators and TLF structure. The verified v0.12 run retains **24/24** reviewer checks.

Existing negative controls corrupt treatment consistency, safety denominators, MMRM `CHG`, a required dataset column and a controlled flag; validators must reject them.

## Statistical change-impact gate

The v0.12 graph/request specifications must both declare `0.12.0`. Six simulated requests cover **118/118 required impact relationships** and **118/118 resolved resources**.

New negative controls require failure when:

- treatment-discontinuation strategy review omits a missingness or MNAR TLF;
- direct sensitivity-assumption change omits T19;
- primary MMRM covariance changes do not propagate to T18/T19 and sensitivity QC;
- graph/request versions disagree;
- an unknown or cyclic dependency is introduced.

## 19-TLF structural traceability

The final traceability gate validates registry/contract agreement, generated files, required columns/minimum rows, analysis-data links, QC links and SHA256 output identity for T01–T19. The verified v0.12 run passes **19/19**.

## CI evidence retention

GitHub Actions prints the main run summaries and uploads `outputs/` even for many downstream failures. This preserves reference-discrepancy traces, model diagnostics, sensitivity QC, reviewer evidence and change-impact diagnostics for investigation.

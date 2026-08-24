# v0.21 CSR-style statistical interpretation pack

## Purpose

v0.21 adds a controlled statistical-interpretation layer after the validated v0.20 analysis-evidence closure. It does not add another model, estimand, analysis population or TLF. The purpose is to show how a Study Statistician can move from validated analysis outputs to bounded study-level interpretation while keeping confirmatory, supportive, descriptive and exploratory evidence separate.

This remains independent public-data portfolio work. It is not a sponsor clinical study report (CSR), medical-writing sign-off, benefit-risk decision, regulatory conclusion or submission-ready report.

## Position in the evidence chain

The v0.21 runner executes only after v0.20 evidence closure succeeds:

```text
validated analysis outputs
  -> analysis readiness
  -> statistical change control
  -> SAP-to-TLF traceability
  -> v0.20 evidence closure
  -> v0.21 CSR-style statistical interpretation
```

This order is deliberate. The interpretation layer cannot turn an incomplete analysis package into a complete one. `outputs/analysis_closure_metrics.json` must report both `all_passed=true` and `PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE` before v0.21 can pass.

The v0.21 interpretation layer has its own executable QC and negative controls. It does not add CR-015 to the pre-closure change-control graph because CSR interpretation is generated after that graph has already been assessed. Adding post-closure outputs as pre-closure required resources would create a circular execution dependency.

## Statistical roles are explicit

Every row in `outputs/csr_conclusion_matrix.csv` is assigned one of four controlled roles:

```text
CONFIRMATORY_DECISION
SUPPORTIVE_SENSITIVITY
DESCRIPTIVE_SAFETY
EXPLORATORY_RETENTION
```

The role controls what can be concluded. A small p-value in a descriptive or exploratory analysis does not promote that analysis into the confirmatory family.

The validated matrix contains **10 rows**:

- 2 primary efficacy decision rows;
- 2 reference-based missing-data sensitivity rows;
- 2 fixed-delta directional-sensitivity rows;
- 2 descriptive safety rows;
- 2 exploratory retention rows.

## Primary efficacy decision

The controlled Week 24 ACTOT family contains Low Dose versus Placebo and High Dose versus Placebo. The interpretation layer reconciles the primary MMRM table directly to the multiplicity decision table before writing any efficacy text.

Validated results are:

| Comparison | Estimate | 95% CI | Raw p | Adjusted p | Family-wise decision |
|---|---:|---:|---:|---:|---|
| Low Dose vs Placebo | -1.6131 | [-3.9216, 0.6953] | 0.169334 | 0.338669 | No rejection |
| High Dose vs Placebo | -0.9271 | [-3.2032, 1.3489] | 0.421970 | 0.843940 | No rejection |

The v0.21 cross-file audit has zero estimate drift and zero raw-p drift between the primary MMRM and multiplicity outputs. It also independently verifies that every `reject_familywise` flag agrees with both the local-alpha rule and the adjusted-p/family-alpha rule.

The controlled family therefore has **0/2 family-wise rejections**. The generated interpretation explicitly states that no confirmatory efficacy success conclusion is supported.

## Reference-based missing-data sensitivity

For each active-versus-placebo comparison, v0.21 requires all four controlled reference-based multiple-imputation strategies:

```text
MAR
JR
CR
CIR
```

The live run contains **8/8 expected comparison-strategy rows** and **8/8 MCSE passes**. All four strategy estimates retain the same effect sign for each active comparison.

This is not reported as confirmatory evidence. The controlled text states that reference-based MI is supportive sensitivity evidence and does not replace the primary multiplicity decision.

## Fixed-delta directional sensitivity

Reference-based MI alone can give an incomplete impression of robustness. v0.21 therefore also reads the existing T19 directional tipping output and requires all three controlled fixed-delta scenarios for both comparisons:

```text
COMMON_WORSENING
ACTIVE_ONLY_WORSENING
DIVERGENT_WORSENING
```

The live table contains **6/6 expected rows**. The earliest analytic direction-tipping thresholds are:

| Comparison | Earliest scenario | Direction-tipping delta |
|---|---|---:|
| Low Dose vs Placebo | DIVERGENT_WORSENING | 1.5621 ACTOT points |
| High Dose vs Placebo | DIVERGENT_WORSENING | 1.0333 ACTOT points |

Both thresholds occur within the controlled grid. The generated interpretation therefore records that direction is assumption-sensitive under stronger MNAR shifts even though the reference-based strategies retain the same sign.

Because the primary hypotheses are not significant, the existing T19 `significance_tipping_status` remains `not_applicable_primary_not_significant`. v0.21 does not invent a significance-tipping claim where the primary result did not first cross the confirmatory decision threshold.

## Safety interpretation

The CSR-style matrix reads the existing any-TEAE risk-difference output for the two active-versus-placebo comparisons:

| Comparison | Risk difference | 95% CI | Fisher p |
|---|---:|---:|---:|
| Low Dose vs Placebo | 0.1192 | [0.0068, 0.2315] | 0.053041 |
| High Dose vs Placebo | 0.1886 | [0.0835, 0.2937] | 0.001726 |

The interpretation records the observed higher TEAE risk relative to placebo, but the analysis role is `DESCRIPTIVE_SAFETY`. The p-values are not used to create a new multiplicity-controlled safety claim or a benefit-risk conclusion.

## Exploratory retention interpretation

The retention layer remains outside the ACTOT confirmatory family. v0.21 requires the source interpretation to preserve both hazard direction and exploratory status.

Validated Cox results are:

| Comparison | HR | 95% CI |
|---|---:|---:|
| Low Dose vs Placebo | 3.0852 | [1.9606, 4.8548] |
| High Dose vs Placebo | 2.9246 | [1.8557, 4.6092] |

For this endpoint, HR greater than 1 means a **higher study-discontinuation hazard** than placebo. It is not written as worse efficacy. The generated rows remain `EXPLORATORY_RETENTION` and explicitly state that they are not efficacy conclusions.

## Executable interpretation QC

The v0.21 base gate passes **11/11** required checks:

```text
required source files exist
v0.20 closure is complete
exact primary comparison set
valid family alpha
exact MMRM primary rows
MMRM-to-multiplicity estimate/p reconciliation
complete MAR/JR/CR/CIR set with MCSE pass
exact safety comparison set
exact retention comparison set
correct retention hazard direction and exploratory role
no prohibited overclaim fragments
```

The fixed-delta extension passes **4/4** required checks:

```text
required fixed-delta interpretation files exist
reject_familywise agrees with local-alpha and adjusted-p rules
exact three-scenario fixed-delta set per comparison
fixed-delta primary estimates reconcile to multiplicity estimates
```

Negative-control tests intentionally create failed closure, primary estimate drift, missing MI strategies, MCSE failure, wrong retention hazard interpretation, inconsistent family-wise rejection flags, missing fixed-delta scenarios, fixed-delta estimate drift and regulatory overclaims. These cases must fail rather than merely add a warning.

## Generated evidence

The complete v0.21 pack writes:

```text
outputs/csr_conclusion_matrix.csv
outputs/csr_interpretation_checks.csv
outputs/csr_interpretation_metrics.json
outputs/csr_fixed_delta_context.csv
outputs/csr_interpretation_extension_checks.csv
outputs/csr_interpretation_extension_metrics.json
outputs/csr_statistical_interpretation.md
```

The controlled interpretation claim is:

```text
PORTFOLIO_STATISTICAL_INTERPRETATION_READY
```

The claim means that the portfolio interpretation rules and required inputs passed. It does not mean sponsor CSR approval, regulatory readiness or benefit-risk approval.

## Validated clean-run evidence

Actions **#625 / run 32701384371** on head `2c7186255004b286b483e0564b162dcc1edfad55` completed successfully before documentation freeze.

The run verifies:

- base interpretation checks: **11/11 PASS**;
- fixed-delta extension checks: **4/4 PASS**;
- final conclusion matrix rows: **10**;
- primary family-wise rejections: **0/2**;
- MMRM-to-multiplicity maximum estimate difference: **0**;
- MMRM-to-multiplicity maximum raw-p difference: **0**;
- reference-based MI MCSE passes: **8/8**;
- fixed-delta rows/scenarios/comparisons: **6 / 3 / 2**;
- multiplicity decision flags consistent with p-value rules: **true**.

Artifact: `9510775094`.

Artifact digest: `sha256:30f046072cc4207bf6686d3bcc877384a74e3c43efe69da8f65e1719a7b3b8b8`.

A final clean run is still required after documentation changes before v0.21 is treated as frozen and merge-ready.

# Reference-based multiple-imputation sensitivity — v0.14

## Purpose

Version 0.14 adds a controlled reference-based multiple-imputation (MI) sensitivity analysis for Week 24 ACTOT. It supplements the v0.13 MAR and delta-adjusted MI analyses; it does not replace the primary observed-data MMRM or change the treatment-policy estimand.

The analysis uses public portfolio data and `rbmi` 1.6.1. It is not a sponsor-approved missing-data strategy, validated production program or regulatory analysis.

## Intercurrent-event timing

Recorded treatment discontinuation is operationalised consistently with the existing ACTOT estimand review:

- subject flag: `DCSFL=Y`;
- recorded discontinuation date: `EOSDT`;
- observed outcome date: `ADT`;
- observed ACTOT with `ADT <= EOSDT` is retained;
- the first affected visit is the first scheduled Week 8/16/24 visit after discontinuation and after all observed pre-discontinuation scheduled outcomes.

Two separate blocking checks are required before MAR/non-MAR strategy switching:

1. no observed scheduled ACTOT outcome has `ADT > EOSDT`;
2. no observed ACTOT value occurs on or after the derived first affected visit used in `data_ice`.

The live v0.14 core run passed both checks with zero violations.

## Imputation and analysis

The analysis reuses the controlled v0.13 pairwise approximate-Bayesian imputation model:

- Low Dose versus Placebo and High Dose versus Placebo are fitted separately;
- Week 8/16/24 ACTOT change-from-baseline history;
- unstructured covariance, common across pairwise treatment groups;
- REML;
- baseline-by-visit and treatment-by-visit terms;
- 200 imputations;
- Week 24 ANCOVA adjusted for baseline ACTOT;
- Rubin pooling.

Placebo remains MAR and supplies the reference distribution. For active-arm discontinuers with an affected scheduled visit, the same parameter draws and fixed ICE timing are reused under four strategies:

- `MAR` — Missing at Random;
- `JR` — Jump to Reference;
- `CR` — Copy Reference;
- `CIR` — Copy Increments in Reference.

## Live core evidence

The successful v0.14 core run used 116 active-arm discontinuers. Of these, 107 had an affected scheduled visit and therefore entered the reference-based strategy update: 68 Low Dose subjects and 39 High Dose subjects.

First affected visits were:

| Comparison | Week 8 | Week 16 | Week 24 | Total with affected visit |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | 35 | 18 | 15 | 68 |
| High Dose vs Placebo | 13 | 22 | 4 | 39 |

The reference-based output contains 8 rows: 2 comparisons × 4 strategies.

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

All four reference-based strategies move the active-minus-placebo point estimate toward zero relative to MAR in this public-data analysis. This is a result of the controlled sensitivity assumptions and observed discontinuation/missingness pattern; it is not a general property that should be assumed for other trials.

## Monte Carlo precision

Each of the eight rows must satisfy:

```text
MCSE(estimate) / pooled SE <= 0.075
```

The maximum observed ratio in the successful core run was 0.053811. All 8/8 strategy rows passed.

## Outputs and QC

- `outputs/table22_rbmi_reference_based.csv`;
- `outputs/rbmi_reference_ice_audit.csv`;
- `outputs/rbmi_reference_ice_counts.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_vs_v013_mar.csv`;
- `outputs/rbmi_reference_metrics.json`.

The core run passed 27/27 required reference-based MI checks, with zero model-fit failures in both pairwise analyses.

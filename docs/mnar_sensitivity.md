# ACTOT fixed-delta missing-data sensitivity — portfolio v0.12

## Purpose

Version 0.12 adds a transparent sensitivity diagnostic for the Week 24 ACTOT treatment contrasts when the primary observed-data MMRM is interpreted under a MAR working assumption.

The purpose is not to assert that the public data are MNAR and not to imitate a sponsor-approved multiple-imputation analysis. The purpose is to quantify how large a specified departure from the MAR reference would need to be before the active-versus-placebo point estimate changes direction.

## Reference analysis

The reference estimate is the primary Week 24 contrast from the unstructured REML MMRM:

```text
CHG ~ treatment * visit + baseline * visit
```

The reference analysis uses observed ACTOT records at Week 8, Week 16 and Week 24. LOCF records do not enter the MMRM.

Let:

- `theta_MAR` be the Week 24 active-minus-placebo MMRM estimate;
- `m_A` be the observed Week 24 missing proportion in the active arm;
- `m_P` be the observed Week 24 missing proportion in placebo;
- `delta` be a fixed ACTOT-point shift applied only to the assumed mean of missing outcomes relative to the MAR reference;
- `a_s` and `p_s` be scenario-specific active and placebo multipliers.

The fixed-delta shifted contrast is

```text
theta_s(delta) = theta_MAR + delta * (m_A * a_s - m_P * p_s)
```

ACTOT is treated as lower-is-better in this portfolio analysis. A positive shift therefore represents a worse assumed outcome.

## Sensitivity scenarios

Three pre-specified stress paths are stored in `spec/mnar_sensitivity.json`.

| Scenario | Active missing outcomes | Placebo missing outcomes | Contrast shift coefficient |
|---|---|---|---|
| `COMMON_WORSENING` | `+delta` | `+delta` | `m_A - m_P` |
| `ACTIVE_ONLY_WORSENING` | `+delta` | unchanged | `m_A` |
| `DIVERGENT_WORSENING` | `+delta` | `-delta` | `m_A + m_P` |

The common scenario asks what happens if missing outcomes in every arm are worse than their MAR reference by the same amount. Because Week 24 missingness is higher in both active arms than placebo in the pinned public data, this common shift moves the active-minus-placebo contrasts towards zero.

The active-only and divergent scenarios are progressively more adverse stress tests. They are not claims about the true missing-data mechanism.

## Delta grid

The machine-readable specification uses a grid from **0 to 6 ACTOT points in 0.5-point steps**. `delta=0` must reproduce the primary MMRM estimate exactly.

The grid is used for inspectable TLF output and to bracket the analytic tipping point. The analytic threshold is not estimated by searching the grid.

## Directional tipping point

For a contrast that initially favours active treatment (`theta_MAR < 0`) and a positive adverse shift coefficient `c_s`, the direction-of-effect threshold is

```text
delta* = -theta_MAR / c_s
```

At `delta*`, the shifted active-minus-placebo point estimate reaches zero.

The current primary Week 24 MMRM contrasts are already non-significant at `delta=0`. Therefore a conventional 'loss of statistical significance' tipping point would start from a condition that is already met and is not used as the primary sensitivity threshold. Version 0.12 reports the directional tipping point instead.

## Confidence intervals in T18

For each fixed delta, T18 also shows a diagnostic confidence interval and p-value using the primary MMRM standard error and degrees of freedom after shifting the point estimate.

This is a **fixed-delta mean-shift diagnostic**. It does not add uncertainty from an imputation model, delta estimation or reference-based MI procedure. The output column names explicitly include `fixed_delta` where relevant to prevent those intervals from being presented as Rubin's-rules MI inference.

## Blocking QC

The v0.12 gate requires, among other checks:

- the machine-readable method, endpoint direction and MAR reference analysis to match the controlled specification;
- Week 24 missingness denominators to reconcile exactly;
- both primary Week 24 active-versus-placebo MMRM contrasts to be present and finite;
- `delta=0` to reproduce the primary estimates to `1e-12`;
- all configured adverse scenarios to move the current contrasts monotonically towards worse active-arm values;
- analytic tipping deltas to be finite and positive;
- the 0.5-point grid to bracket each analytic tipping threshold within one grid step;
- the loss-of-significance label to remain `not applicable` while the primary p-values are already at least 0.05.

Negative-control unit tests corrupt a missingness denominator, endpoint direction/reference assumption and the current significance state; the corresponding validators must reject the change.

## Generated evidence

```text
outputs/mnar_sensitivity_inputs.csv
outputs/table18_actot_delta_sensitivity.csv
outputs/table19_actot_directional_tipping_points.csv
outputs/mnar_sensitivity_qc.csv
outputs/mnar_sensitivity_metrics.json
outputs/mnar_sensitivity_summary.md
```

T18 contains the full scenario-by-contrast-by-delta grid. T19 contains one analytic direction-of-effect tipping point per scenario and active-versus-placebo contrast.

## Evidence boundary

This is an independent public-data portfolio exercise. It is not sponsor-approved MNAR multiple imputation, jump-to-reference/copy-reference analysis, a reference-based MI implementation, a regulator-agreed sensitivity strategy, or evidence of production clinical-trial programming. The fixed-delta calculation is deliberately simpler and more transparent than those methods and is labelled accordingly throughout the repository.

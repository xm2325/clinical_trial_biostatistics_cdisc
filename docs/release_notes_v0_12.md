# Release notes — portfolio v0.12

Date: 2026-08-22

## Summary

Version 0.12 adds a fixed-delta missing-data sensitivity layer to the existing Week 24 ACTOT estimand/MMRM workflow. The new analysis quantifies how large a specified adverse departure from the MAR reference must be before each active-versus-placebo point estimate reaches zero.

The method is deliberately labelled as a **fixed-delta pattern-mixture mean-shift diagnostic**. It is not presented as production MNAR multiple imputation, jump-to-reference/copy-reference analysis or regulator-agreed reference-based MI.

## Verified live evidence

- Python unit tests: **57/57 passed**.
- Core Python QC: **24/24 passed**.
- Separate R/Python programming QC: **16/16 passed**.
- MMRM QC: **11/11 passed**.
- Estimand/missing-data review: **21/21 passed**.
- v0.12 sensitivity QC: **19/19 passed**.
- Dataset/TLF reviewer: **24/24 passed**.
- Structural SAP-to-TLF traceability: **19/19**.
- Statistical change impacts: **118/118 declared and 118/118 resources resolved**.

## New controlled analysis

Machine-readable assumptions are stored in `spec/mnar_sensitivity.json`.

Controlled delta grid:

```text
0.0 to 6.0 ACTOT points by 0.5
```

Scenarios:

1. `COMMON_WORSENING`: +delta to missing outcomes in every arm;
2. `ACTIVE_ONLY_WORSENING`: +delta only to missing active-arm outcomes;
3. `DIVERGENT_WORSENING`: +delta for missing active-arm outcomes and -delta for missing placebo outcomes.

For active-versus-placebo contrast `theta_MAR`:

```text
theta_s(delta) = theta_MAR
               + delta * (m_active * active_multiplier
                          - m_placebo * placebo_multiplier)
```

## Verified directional tipping points

The current primary Week 24 MMRM contrasts are already non-significant at delta zero, so loss-of-significance is not used as the main tipping threshold. v0.12 reports the positive delta at which the shifted point estimate reaches zero.

| Scenario | Low Dose vs Placebo | High Dose vs Placebo |
|---|---:|---:|
| Common worsening | **3.985** | **3.442** |
| Active-only worsening | **2.244** | **1.589** |
| Divergent worsening | **1.562** | **1.033** |

All six analytic thresholds are inside the controlled 0–6 grid and are bracketed by the 0.5-point grid as required.

## New TLFs

- **T18** `outputs/table18_actot_delta_sensitivity.csv`: 78 scenario × contrast × delta rows;
- **T19** `outputs/table19_actot_directional_tipping_points.csv`: six analytic tipping-point rows.

Both TLFs require `outputs/mnar_sensitivity_inputs.csv` and `outputs/mnar_sensitivity_qc.csv` in the executable traceability registry.

## New change-control coverage

The dependency graph is now version `0.12.0` and contains six simulated changes. v0.12 makes the sensitivity outputs downstream of the primary ACTOT visit, primary MMRM model fit and treatment-discontinuation estimand strategy.

New **CR-006** tests a direct change to the delta range/scenario multipliers and requires regeneration/review of the sensitivity inputs, T18/T19, sensitivity QC, controlled sensitivity documentation and `spec/mnar_sensitivity.json`.

Verified change-control result: **118/118** required relationships covered and **118/118** required resources resolved.

## Failure-path improvement

The v0.12 runner writes sensitivity QC, metrics and summary evidence **before** exiting on a failed gate. A malformed input therefore leaves inspectable diagnostic artifacts instead of being masked by a downstream output-construction error.

## Documentation

The current consolidated SAP is `docs/sap.md` at portfolio version 0.12. Versioned v0.9–v0.12 addenda remain in the repository as change history.

The existing root `CHANGELOG.md` is intentionally not rewritten through the connector because it contains the prior release history; these release notes provide the v0.12 publication record without deleting earlier entries.

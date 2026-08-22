# Subject-level ACTOT MI sensitivity with rbmi

## Why this layer exists

The v0.12 fixed-delta calculation is useful for showing how much the Week 24 treatment contrast would move under explicit missing-outcome shifts, but its confidence intervals deliberately reuse the primary MMRM standard error and therefore do not represent imputation uncertainty. v0.13 adds a separate subject-level MI layer so missing outcomes are imputed, re-analysed and pooled rather than represented only by an analytic mean shift.

## Controlled workflow

For each active treatment versus placebo, the program:

1. constructs the complete Week 8/16/24 subject-visit grid for randomised subjects with baseline ACTOT;
2. retains observed ACTOT change values and leaves unobserved scheduled outcomes missing;
3. fits an approximate-Bayesian `rbmi` longitudinal imputation model with unstructured covariance, baseline-by-visit and treatment-by-visit terms;
4. generates 200 imputations using a fixed comparison-specific seed;
5. analyses Week 24 with baseline-adjusted ANCOVA;
6. pools the active-minus-placebo contrast with Rubin's rules;
7. reuses the same imputation draws for controlled delta-adjusted departures from MAR;
8. records draw failures, delta audit rows, MCSE, T20/T21 outputs and CI QC evidence.

The package version is checked at runtime against `rbmi` 1.6.1. Package-version drift fails the analysis rather than silently changing the implementation.

## Precision and failure controls

Model-fit and simulation precision are treated as separate questions.

- requested imputations: 200;
- allowed approximate-Bayes fit-failure fraction: at most 10%;
- required MAR `MCSE(estimate) / pooled SE`: at most 7.5% for both active-versus-placebo comparisons;
- requested versus completed draw counts must reconcile;
- Rubin pooling must be reported by the fitted object;
- pooled estimates, standard errors, intervals and p-values must be finite.

The first executable 50-imputation smoke run passed all model/QC checks with zero model failures, but its MCSE(est)/SE ratios were about 10.3% for Low versus Placebo and 9.1% for High versus Placebo. That evidence motivated the controlled increase to 200 imputations rather than treating a merely successful run as sufficiently precise. Final v0.13 results are taken from the final-head 200-imputation CI artifact.

## Delta scenarios

`MAR` is the reference. Three departures are applied only to originally missing Week 24 outcomes:

- active +1 ACTOT point;
- active +2 ACTOT points;
- active +1 / placebo -1 ACTOT point.

The QC layer verifies that active-only +1 and +2 move the active-minus-placebo estimate monotonically in the adverse direction and that the divergent +1/-1 scenario is more adverse than active-only +1.

## Relationship to the primary MMRM

The primary longitudinal model remains the three-arm observed-data MMRM. v0.13 performs pairwise MI followed by Week 24 ANCOVA, so the MAR MI estimate and primary MMRM estimate are expected to be related but not identical. `outputs/rbmi_vs_mmrm_week24.csv` is therefore a diagnostic comparison, not an equality test.

## Traceability

The MI outputs are registered as:

- **T20** — MAR pairwise MI results;
- **T21** — delta-adjusted MI sensitivity results.

Their contracts require the inferential fields, MCSE fields, pool method and imputation count. Traceability also requires the rbmi QC, MCSE QC, draw diagnostics and delta audit evidence to exist.

## Evidence boundary

This is an independent public-data portfolio implementation. It does not claim sponsor/CRO production experience, regulatory submission use, sponsor-approved missing-data assumptions, independent second-programmer review, or reference-based imputation. v0.13 does not claim J2R.

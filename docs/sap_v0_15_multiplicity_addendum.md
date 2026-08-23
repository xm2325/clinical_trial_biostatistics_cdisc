# SAP v0.15 addendum — primary ACTOT multiplicity

This versioned addendum supplements the consolidated SAP material through v0.14. It does not claim to reproduce the source study's sponsor-approved SAP.

## Primary family

The portfolio primary multiplicity family comprises two Week 24 ACTOT change-from-baseline hypotheses from the primary unstructured-covariance MMRM:

1. Xanomeline Low Dose versus Placebo.
2. Xanomeline High Dose versus Placebo.

The family-wise two-sided Type I error rate is 0.05.

## Multiplicity procedure

Bonferroni adjustment is applied across the two hypotheses. The local two-sided alpha is therefore 0.025. Adjusted p-values are calculated as `min(raw p * 2, 1)`. The null hypothesis is rejected on the family-wise scale if the adjusted p-value is no greater than 0.05.

The analysis program must select only Week 24 rows from the primary unstructured MMRM contrast output. Alternative covariance results, Week 8/16 contrasts, ANCOVA, fixed-delta sensitivity, MAR multiple imputation, delta multiple imputation and reference-based MI are excluded from the primary multiplicity family.

## Decision output

T23 reports the hypothesis identifier, contrast, primary MMRM estimate and inference, raw p-value, family alpha, comparison count, local alpha, Bonferroni adjusted p-value and family-wise reject flag.

The public-data run yields no family-wise rejection for either active-versus-placebo hypothesis.

## Quality control

The multiplicity gate fails if the planning and analysis multiplicity specifications disagree, if the exact controlled hypothesis set is not present, if the selected visit/covariance is incorrect, or if the adjusted-p/rejection calculations are inconsistent.

Evidence boundary: independent public-data portfolio work, not sponsor-approved or regulatory analysis.

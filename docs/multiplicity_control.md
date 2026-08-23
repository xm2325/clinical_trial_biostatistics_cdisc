# Primary ACTOT multiplicity control

## Scope

v0.15 closes the gap between the illustrative protocol-design multiplicity assumption and analysis-side decision reporting. The controlled family contains exactly two primary Week 24 ACTOT hypotheses from the unstructured-covariance MMRM:

- H_LOW: Xanomeline Low Dose versus Placebo.
- H_HIGH: Xanomeline High Dose versus Placebo.

Sensitivity analyses, alternative covariance structures, ANCOVA analyses and missing-data sensitivity outputs are not members of this primary family.

## Controlled rule

The family-wise two-sided alpha is 0.05. Bonferroni control across two hypotheses gives a local alpha of 0.025. For each raw MMRM p-value, the adjusted p-value is `min(2 * p, 1)`. A family-wise rejection is recorded when the adjusted p-value is no greater than 0.05; equivalently, when the raw p-value is no greater than 0.025.

The machine-readable source of truth is `spec/multiplicity.json`. The planning-side alpha and comparison count are cross-checked against `spec/protocol_design.json`.

## Public-data result

The validated public-data run produced:

| Hypothesis | Raw p-value | Bonferroni adjusted p-value | Family-wise rejection |
|---|---:|---:|---|
| H_LOW | 0.169334 | 0.338669 | No |
| H_HIGH | 0.421970 | 0.843940 | No |

Neither hypothesis is rejected under the controlled family. This is retained as the actual result rather than selecting a different family or method to obtain statistical significance.

## Executable QC

`outputs/multiplicity_qc.csv` requires all of the following to pass:

- analysis method, family alpha and comparison count match the planning specification;
- exactly the two controlled Week 24 unstructured MMRM contrasts are selected;
- contrast labels are unique and the exact hypothesis set is present;
- estimates, standard errors, degrees of freedom and raw p-values are finite;
- raw p-values lie in [0, 1];
- local alpha equals family alpha divided by comparison count;
- adjusted p-values follow the Bonferroni formula;
- reject flags agree with both the raw-alpha and adjusted-p decision rules.

T23 (`outputs/table23_actot_multiplicity.csv`) is the controlled decision output.

## Evidence boundary

This is independent public-data portfolio work aligned to an illustrative planning specification. It is not the source trial's sponsor-approved multiplicity strategy, a regulatory confirmatory analysis, a clinical efficacy claim or a validated production program.

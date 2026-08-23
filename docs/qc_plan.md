# QC plan — portfolio version 0.16

The workflow uses separate blocking QC layers for derivation, public-reference checks, R/Python replication, repeated-measures modelling, cross-package MMRM validation, primary multiplicity control, estimand/missing-data review, deterministic sensitivity, subject-level MI, reference-based MI, reviewer checks, statistical change impact and final TLF traceability. A required failure exits non-zero.

## QC stack

The current live workflow checks:

1. Python unit tests and derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. protocol-design and randomisation/initial-kit QC;
4. separate R reconstruction and R/Python comparison;
5. ACTOT MMRM data/model/inference QC;
6. **v0.16 primary MMRM cross-package validation**;
7. v0.15 primary multiplicity QC;
8. estimand and missing-data review;
9. v0.12 deterministic fixed-delta sensitivity QC;
10. v0.13 subject-level MI model/pooling/delta QC;
11. independent v0.13 MI Monte Carlo precision QC;
12. v0.14 reference-based MI ICE/model/pooling/MCSE QC;
13. analysis-dataset/TLF reviewer;
14. v0.16 versioned statistical change-control impact gate;
15. versioned **T01–T23** structural traceability.

The workflow also uses branch/event concurrency with `cancel-in-progress: true`, so superseded upgrade commits no longer consume a full long-running MI pipeline.

## v0.16 MMRM cross-package validation

`R/mmrm_cross_package_qc.R` independently reconstructs the observed ACTOT longitudinal rows from `outputs/adqs_actot_style.csv` instead of reading the primary MMRM analysis dataset. It writes `outputs/mmrm_cross_package_analysis_dataset.csv`, then fits the same fixed-effects mean model with `nlme::gls`, using `corSymm + varIdent` to represent an unstructured marginal covariance.

The blocking gate first checks analysis-population identity:

- unique `STUDYID × USUBJID × AVISIT` keys in both implementations;
- identical key sets;
- exact treatment assignment;
- finite `QSSEQ`, `AVAL`, `BASE` and `CHG` values;
- numeric row agreement within **1e-12**.

The validated run has **451/451 rows**, **189/189 subjects**, zero missing/extra keys, zero exact-field mismatches and zero numeric mismatch rows.

The independent Week 24 Low Dose vs Placebo and High Dose vs Placebo contrast vectors are built directly from the `nlme` fitted design matrix. The model-comparison part then requires:

- exactly the two specified Week 24 active-versus-placebo hypotheses in both implementations;
- finite point estimates and model-based SEs;
- absolute estimate difference <= **0.0005** for each contrast;
- absolute SE difference <= **0.0005** for each contrast;
- treatment-effect sign agreement;
- no df or p-value comparison, because the primary program uses Satterthwaite inference and the independent `nlme` reconstruction is not intended to reproduce that package-specific denominator-df method.

The validated v0.16 gate passes **18/18** required checks. Maximum estimate absolute difference is **1.30015e-05** and maximum SE absolute difference is **2.63230e-06**. The metrics artifact also records SHA256 fingerprints for the validation specification, both contrast sources and both analysis datasets.

## Primary multiplicity QC

`python scripts/run_multiplicity.py` reads the primary MMRM contrasts and `spec/multiplicity.json`, then cross-checks the family against `spec/protocol_design.json`.

The 12 required checks enforce:

- Bonferroni is the controlled method;
- family alpha matches the planning specification;
- comparison count matches planning;
- exactly the two controlled hypotheses are selected;
- only Week 24 primary `Unstructured` MMRM rows enter the family;
- hypothesis/contrast mappings are exact and unique;
- estimates, SEs, df and raw p-values are finite;
- raw p-values are in [0, 1];
- local alpha equals 0.05 / 2 = 0.025;
- adjusted p-values equal `min(2 * raw_p, 1)`;
- reject flags agree with the raw local-alpha rule;
- reject flags agree with the adjusted-p family-alpha rule.

The live result passes **12/12** required checks. H_LOW raw p=0.169334 gives adjusted p=0.338669; H_HIGH raw p=0.421970 gives adjusted p=0.843940. Neither hypothesis is rejected family-wise.

Sensitivity analyses are deliberately excluded from the primary family.

## Reference-based MI QC

The v0.14 reference-based layer remains blocking. Its two separate timing guards require:

```text
observed scheduled ACTOT with ADT > EOSDT == 0
```

and

```text
observed ACTOT on/after the first affected scheduled visit == 0
```

The validated reference-based analysis passes **27/27** required checks, uses 200 imputations for each pairwise model and requires `MCSE(estimate) / pooled SE <= 0.075`. The maximum observed ratio is **0.053811**.

## T12 and T23 traceability evidence

T12 now links the cross-package validation directly into controlled traceability. Its primary output remains `outputs/mmrm_treatment_contrasts.csv`, while required QC evidence includes both `outputs/mmrm_qc.csv` and `outputs/mmrm_cross_package_qc.csv`.

T23 continues to require, in the same live run:

- `outputs/mmrm_analysis_dataset.csv`;
- `outputs/mmrm_treatment_contrasts.csv`;
- `outputs/table23_actot_multiplicity.csv`;
- `outputs/mmrm_qc.csv`;
- `outputs/multiplicity_qc.csv`.

The v0.16 cross-package layer is deliberately not attached to T23 as multiplicity evidence because it does not reproduce Satterthwaite degrees of freedom or p-values. T23 therefore continues to use the controlled primary `mmrm` inference plus the multiplicity QC layer.

## Change-control QC

The v0.14 base graph/request files remain byte-preserved. v0.15 adds the multiplicity extension; v0.16 adds a second controlled extension for cross-package MMRM validation.

The v0.16 graph adds:

- the validation rule, analysis-row identity rule and pre-specified numerical tolerances;
- independent `nlme` analysis-row reconstruction dependencies;
- the executable cross-package comparison gate;
- propagation from primary visit, MMRM covariance, primary contrast focus, model fit and estimand alignment;
- CR-010 for changes to independent package, row-identity rule, validation scope, controlled hypotheses or tolerance.

The validated merged assessment covers:

- **10** simulated change requests;
- **73** propagated component links;
- **254/254** required impact relationships declared;
- **254/254** required resources resolved;
- zero missing required declarations;
- zero extra declared resources;
- zero unresolved required resources.

CR-010 itself propagates through three validation components and requires 12 downstream impact relationships without inventing a new TLF.

## Traceability version QC

`spec/analysis_traceability.csv` contains `registry_version`. Every TLF row must declare one identical non-empty version. v0.16 retains the controlled **T01–T23** output set while advancing the registry version to `0.16.0` because the blocking QC/governance environment changed.

The validated structural gate passes:

- outputs found: **23/23**;
- output contracts: **23/23**;
- analysis-data links: **23/23**;
- QC-evidence links: **23/23**;
- complete structural traceability: **23/23**.

`traceability_metrics.json` derives `analysis_version` from the registry instead of using a hard-coded constant.

## Evidence boundary

These checks are portfolio QC. Same-author R/Python replication and the v0.16 distinct-package MMRM reconstruction are not formal independent second-programmer validation. Successful cross-package, multiplicity and missing-data QC does not make the portfolio procedure sponsor-approved or regulatory-confirmatory.

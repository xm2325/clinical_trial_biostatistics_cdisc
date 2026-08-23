# QC plan — portfolio version 0.15

The workflow uses separate blocking QC layers for derivation, public-reference checks, R/Python replication, repeated-measures modelling, primary multiplicity control, estimand/missing-data review, deterministic sensitivity, subject-level MI, reference-based MI, reviewer checks, statistical change impact and final TLF traceability. A required failure exits non-zero.

## QC stack

The current live workflow checks:

1. Python unit tests and derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. protocol-design and randomisation/initial-kit QC;
4. separate R reconstruction and R/Python comparison;
5. ACTOT MMRM data/model/inference QC;
6. **v0.15 primary multiplicity QC**;
7. estimand and missing-data review;
8. v0.12 deterministic fixed-delta sensitivity QC;
9. v0.13 subject-level MI model/pooling/delta QC;
10. independent v0.13 MI Monte Carlo precision QC;
11. v0.14 reference-based MI ICE/model/pooling/MCSE QC;
12. analysis-dataset/TLF reviewer;
13. v0.15 versioned statistical change-control impact gate;
14. versioned **T01–T23** structural traceability.

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

The live v0.15 result passes **12/12** required checks. H_LOW raw p=0.169334 gives adjusted p=0.338669; H_HIGH raw p=0.421970 gives adjusted p=0.843940. Neither hypothesis is rejected family-wise.

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

## T23 traceability evidence

T23 requires, in the same live run:

- `outputs/mmrm_analysis_dataset.csv`;
- `outputs/mmrm_treatment_contrasts.csv`;
- `outputs/table23_actot_multiplicity.csv`;
- `outputs/mmrm_qc.csv`;
- `outputs/multiplicity_qc.csv`.

Its output contract requires the family/hypothesis identifiers, contrast, visit/covariance, primary MMRM estimate/inference, raw p-value, adjustment method, family alpha, comparison count, local alpha, adjusted p-value and family-wise reject flag. Minimum rows: 2.

## Change-control QC

The v0.14 base graph/request files remain byte-preserved and declare `0.14.0`. v0.15 adds controlled extension specifications declaring base version 0.14.0 and logical version 0.15.0.

The merged live assessment covers:

- **9** simulated change requests;
- **62** propagated component links;
- **217/217** required impact relationships declared;
- **217/217** required resources resolved;
- zero missing required declarations;
- zero extra declarations;
- zero unresolved required resources.

CR-003, CR-004 and CR-005 propagate to T23 through visit, covariance and estimand-alignment dependencies. CR-009 directly controls the primary multiplicity assumptions. Negative controls require failure when T23 is omitted from CR-009 or when an extension declares the wrong base version.

## Traceability version QC

`spec/analysis_traceability.csv` contains `registry_version`. Every TLF row must declare one identical non-empty version. The controlled current value is `0.15.0`.

The final v0.15 live result passes:

- outputs found: **23/23**;
- output contracts: **23/23**;
- analysis-data links: **23/23**;
- QC-evidence links: **23/23**;
- complete structural traceability: **23/23**.

`traceability_metrics.json` derives `analysis_version` from the registry instead of using a hard-coded constant.

## Evidence boundary

These checks are portfolio QC. Same-author R/Python replication is not independent second-programmer validation. Successful multiplicity and missing-data QC does not make the portfolio procedure sponsor-approved or regulatory-confirmatory.

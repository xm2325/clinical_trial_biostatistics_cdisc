# QC plan — portfolio version 0.18

The workflow uses blocking QC layers for derivation, public-reference checks, analysis metadata/lineage, R/Python replication, longitudinal modelling, cross-package validation, multiplicity, missing-data sensitivity, survival analysis, reviewer checks, statistical change impact and TLF traceability. Required failures exit non-zero.

## Current QC stack

1. Python unit tests and source-to-analysis derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. v0.17 ADTTE-style randomized-retention derivation QC;
4. **v0.18 ADaM-style variable metadata and lineage QC**;
5. protocol-design and randomisation/initial-kit QC;
6. separate R reconstruction and R/Python comparison;
7. ACTOT MMRM data/model/inference QC;
8. v0.16 distinct-package MMRM validation;
9. v0.17 randomized-arm Kaplan–Meier/log-rank/Cox retention QC;
10. v0.15 primary multiplicity QC;
11. estimand and missing-data review;
12. deterministic fixed-delta sensitivity QC;
13. subject-level MI model/pooling/delta QC;
14. independent MI Monte Carlo precision QC;
15. reference-based MI ICE/model/pooling/MCSE QC;
16. analysis-dataset/TLF reviewer;
17. **v0.18 versioned statistical change-control impact gate**;
18. T01–T25 structural traceability.

GitHub Actions uses branch/event concurrency with `cancel-in-progress: true`, so superseded upgrade commits are cancelled rather than consuming a complete MI cycle.

## v0.18 variable metadata and lineage QC

`python scripts/run_metadata_lineage.py` runs after the public source-to-analysis workflow and ADTTE derivation. It validates the actual generated schemas for:

```text
outputs/adsl_style.csv
outputs/adae_style.csv
outputs/adqs_actot_style.csv
outputs/adtte_retention_style.csv
```

The controlled metadata catalog records, for every covered variable:

- variable name and label;
- data type;
- analytical role;
- predecessor versus derived origin;
- one or more `DOMAIN.VARIABLE` source references;
- derivation text;
- dataset-key status.

Blocking checks require exact generated-column/metadata coverage, no stale extra metadata, exact key declarations, non-empty labels/source references, derivation text for derived variables, valid lineage syntax, resolvable cross-analysis-dataset references and accepted raw/source domains.

The validated live result is:

- analysis datasets: **4**;
- generated variables: **85**;
- metadata variables: **85**;
- exact coverage: **85/85 (100%)**;
- declared source references: **110**;
- cross-analysis-dataset references resolved: **39/39**;
- derived variables: **52**;
- predecessor variables: **33**.

### Define-XML-inspired export QC

The same gate writes and reparses `outputs/define_xml_like_metadata.xml`.

Required invariants:

- XML parses successfully;
- root reference standard is `Define-XML`;
- reference package is **2.1.11**;
- conformance is exactly `NOT_ASSESSED`;
- XML dataset definitions equal metadata dataset definitions;
- XML variable definitions equal metadata variable definitions.

Validated XML counts are **4 dataset definitions / 85 variable definitions**. The validated XML SHA256 is:

```text
32e378b57d85e548ac2513de0d2ec7cef678873615648e480a6d413587cc4b39
```

The export is intentionally Define-XML-inspired portfolio evidence. The gate rejects an attempted `CONFORMANT` status; schema conformance and submission readiness are not assessed.

### Negative controls

Unit tests require failure when:

- a generated column has no metadata definition;
- stale metadata is added for a nonexistent column;
- a cross-analysis lineage reference points to a nonexistent upstream variable;
- a derived variable has blank derivation text;
- formal conformance is asserted instead of `NOT_ASSESSED`.

The first complete v0.18 live run passes **146 Python unit tests** before downloading/running the public-data analysis.

## ADTTE-style retention QC retained from v0.17

One `TTDISC` row is derived per randomized subject. Analysis assignment is locked to:

```text
ANLTRT = TRT01P
```

Actual treatment (`TRT01A`) remains context; `TRTDIFFL` audits planned/actual differences. The public data contain **12/254** randomized subjects with `TRT01P != TRT01A`.

Validated derivation evidence remains:

- subjects **254**;
- events **144**;
- censors **110**;
- planned arm counts **86 / 84 / 84**;
- **16/16** derivation QC checks passed.

The R survival layer retains **14/14** blocking checks. Day-182 KM retention is **67.44% / 29.76% / 33.25%** for Placebo / Low / High; exploratory discontinuation HRs are **3.0852** and **2.9246**. `cox.zph` p-values are **0.8310 / 0.7577**.

## MMRM cross-package QC retained from v0.16

The independent `nlme::gls` program reconstructs the longitudinal ACTOT rows instead of reading the primary MMRM analysis dataset. The gate validates:

- **451/451** rows;
- **189/189** subjects;
- zero missing/extra keys;
- zero exact-field/numeric mismatch rows;
- **18/18** blocking checks;
- maximum estimate absolute difference **1.30015e-05**;
- maximum model-based SE absolute difference **2.63230e-06**;
- locked tolerance **0.0005** for estimates and SEs.

Degrees of freedom and p-values are deliberately not compared because primary `mmrm` uses Satterthwaite inference while the separate `nlme` implementation validates population, point estimates and model-based SEs.

## Multiplicity and missing-data QC

Primary multiplicity retains **12/12** required checks. The controlled family has two Week 24 ACTOT hypotheses, family-wise alpha 0.05 and Bonferroni local alpha 0.025; neither hypothesis is rejected.

Reference-based MAR/JR/CR/CIR sensitivity remains blocking. It passes **27/27** required checks with maximum `MCSE(estimate) / pooled SE = 0.053811` against a 0.075 threshold.

## v0.18 change-control QC

The validated logical graph layers v0.18 metadata governance over the byte-preserved earlier specifications. `CR-012` represents a change to dataset/variable metadata scope, labels/types/roles, origins/derivations, lineage, Define-XML reference package or deterministic XML-export rule.

The metadata chain is:

```text
adam_metadata_definition
  -> adam_metadata_lineage_validation
  -> define_like_metadata_export
```

It is deliberately separate from MMRM, multiplicity and retention-analysis components and has no TLF impact.

The validated merged assessment covers:

- **12** simulated change requests;
- **80** propagated component links;
- **279/279** graph-required impact relationships declared;
- **279/279** required resources resolved;
- zero missing required declarations;
- zero extra declared resources;
- zero unresolved required resources.

`CR-012` itself has three propagated components, **12 required impacts** and **0 impacted TLFs**.

## TLF traceability boundary

v0.18 does not add a statistical output, so `spec/analysis_traceability.csv` remains **T01–T25 at registry version 0.17.0**. The same v0.18 workflow still requires and passes:

- outputs found **25/25**;
- output contracts **25/25**;
- analysis-data links **25/25**;
- QC-evidence links **25/25**;
- passed TLFs **25/25**.

This separation is intentional: metadata/lineage governance is additional evidence, not a fabricated TLF.

## Evidence boundary

All checks are portfolio QC. Successful metadata, lineage, cross-package, multiplicity, MI and survival QC does not make the datasets formally ADaM-conformant, the XML formally Define-XML-conformant, or any procedure sponsor-approved/regulatory-confirmatory. Same-author R/Python and distinct-package replication is not formal independent second-programmer validation.

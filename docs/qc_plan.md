# QC plan — portfolio version 0.19

The workflow uses blocking QC layers for derivation, public-reference checks, analysis metadata/lineage, official exchange-schema validation, CDISC CORE rule-availability governance, R/Python replication, longitudinal modelling, cross-package validation, multiplicity, missing-data sensitivity, survival analysis, reviewer checks, statistical change impact and TLF traceability. Required failures exit non-zero.

## Current QC stack

1. Python unit tests and source-to-analysis derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. v0.17 ADTTE-style randomized-retention derivation QC;
4. v0.18 ADaM-style variable metadata and lineage QC;
5. **v0.19 Dataset-JSON 1.1 exchange + pinned official-schema validation**;
6. **v0.19 pinned CDISC CORE cache/rule-availability audit and mutually exclusive executed-versus-NOT_AVAILABLE evidence state**;
7. protocol-design and randomisation/initial-kit QC;
8. separate R reconstruction and R/Python comparison;
9. ACTOT MMRM data/model/inference QC;
10. v0.16 distinct-package MMRM validation;
11. v0.17 randomized-arm Kaplan–Meier/log-rank/Cox retention QC;
12. v0.15 primary multiplicity QC;
13. estimand and missing-data review;
14. deterministic fixed-delta sensitivity QC;
15. subject-level MI model/pooling/delta QC;
16. independent MI Monte Carlo precision QC;
17. reference-based MI ICE/model/pooling/MCSE QC;
18. analysis-dataset/TLF reviewer;
19. **v0.19 versioned statistical change-control impact gate**;
20. T01–T25 structural traceability.

GitHub Actions uses branch/event concurrency with `cancel-in-progress: true`, so superseded upgrade commits are cancelled rather than consuming a complete MI cycle.

## v0.19 Dataset-JSON and CORE standards QC

`python scripts/run_dataset_json.py` consumes the actual four generated analysis datasets plus the validated v0.18 85-variable metadata catalog. The gate validates each exchange file against the pinned official Dataset-JSON 1.1 schema, reparses the generated JSON, checks exact record/value/null-mask preservation, verifies metadata-driven `keySequence`, and preserves ADaM date exchange metadata.

Validated clean-runner evidence from Actions run #548:

- datasets: **4**;
- variables: **85**;
- records: **2,569**;
- JSON null values preserved: **1,675**;
- official Dataset-JSON schema errors: **0**;
- CORE CSV transport metadata: **4 datasets / 85 variables**;
- CORE declared type vocabulary: **Char / Num**;
- Dataset-JSON gate: **PASS**.

The CORE layer is deliberately split into availability and execution states. The workflow pins the engine, a populated official cache snapshot and `cdisc-open-rules`, rejects placeholder cache files, hashes required cache files and runs both unfiltered and ADaMIG 1.3-filtered rule discovery.

Run #548 records:

- complete populated-cache rule inventory: **981** unique CORE IDs;
- literal rule IDs in `rules_dictionary.pkl`: **981**;
- literal rule IDs in `rules.pkl`: **981**;
- dictionary/rules-data overlap: **981/981**;
- requested `adamig/1-3` key: **present**;
- rules returned for `adamig/1-3`: **0**;
- `Unpublished/ADAMIG` YAML files in the pinned open-rules source: **191**;
- published YAML files explicitly referencing ADaMIG: **1**;
- controlled execution state: **`NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE`**.

This is a positive governance result, not a positive ADaM validation result. With zero official rules returned for the requested ruleset, executable CORE validation is **not performed** and no `core_official_report.json` is fabricated. If a future pinned official cache exposes non-zero ADaMIG rules, the workflow automatically switches to the strict executable path, which requires at least one executed rule and blocks any `EXECUTION ERROR`, unknown status or CLI failure.

See `docs/cdisc_standards_validation.md` for the full provenance and evidence boundary.

## v0.18 variable metadata and lineage QC retained

`python scripts/run_metadata_lineage.py` validates the actual generated schemas for:

```text
outputs/adsl_style.csv
outputs/adae_style.csv
outputs/adqs_actot_style.csv
outputs/adtte_retention_style.csv
```

The controlled metadata catalog records, for every covered variable, variable name/label, data type, analytical role, predecessor-versus-derived origin, source references, derivation text and dataset-key status.

Blocking checks require exact generated-column/metadata coverage, no stale extra metadata, exact key declarations, non-empty labels/source references, derivation text for derived variables, valid lineage syntax, resolvable cross-analysis-dataset references and accepted raw/source domains.

Validated evidence remains:

- analysis datasets: **4**;
- generated variables: **85**;
- metadata variables: **85**;
- exact coverage: **85/85 (100%)**;
- declared source references: **110**;
- cross-analysis-dataset references resolved: **39/39**;
- derived variables: **52**;
- predecessor variables: **33**.

### Define-XML-inspired export QC

The same gate writes and reparses `outputs/define_xml_like_metadata.xml`. Required invariants include successful XML parse, reference standard `Define-XML`, reference package **2.1.11**, conformance exactly `NOT_ASSESSED`, and dataset/variable definition counts matching the metadata catalog.

Validated XML counts are **4 dataset definitions / 85 variable definitions**. The export remains Define-XML-inspired portfolio evidence; schema conformance and submission readiness are not assessed.

### Negative controls

Unit tests require failure when, among other cases:

- a generated column has no metadata definition;
- stale metadata is added for a nonexistent column;
- a cross-analysis lineage reference points to a nonexistent upstream variable;
- a derived variable has blank derivation text;
- formal conformance is asserted instead of `NOT_ASSESSED`;
- a required CORE cache file is a five-byte placeholder;
- the configured expected CORE rule-availability state disagrees with discovered official evidence;
- zero CORE rules are represented as executable validation success;
- executable CORE output contains no executed rules or an `EXECUTION ERROR`;
- CR-013 omits required Dataset-JSON or CORE availability evidence from review.

## ADTTE-style retention QC retained from v0.17

One `TTDISC` row is derived per randomized subject. Analysis assignment is locked to `ANLTRT = TRT01P`; actual treatment remains context and `TRTDIFFL` audits planned/actual differences. The public data contain **12/254** randomized subjects with `TRT01P != TRT01A`.

Validated derivation evidence remains **254 subjects / 144 events / 110 censors / 86-84-84 planned arm counts / 16/16 derivation checks**. The R survival layer retains **14/14** blocking checks. Day-182 KM retention is **67.44% / 29.76% / 33.25%** for Placebo / Low / High; exploratory discontinuation HRs are **3.0852** and **2.9246**.

## MMRM cross-package QC retained from v0.16

The independent `nlme::gls` program reconstructs longitudinal ACTOT rows instead of reading the primary MMRM analysis dataset. The gate validates:

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

## v0.19 change-control QC

The logical graph now layers standards-tooling governance over the byte-preserved earlier specifications.

CR-013 represents a change to the pinned Dataset-JSON/CORE/open-rules references, exchange transport rules, expected ADaMIG rule-availability state or evidence boundary. Its controlled chain is:

```text
standards_validation_configuration
  -> dataset_json_exchange_validation
  -> core_rule_availability_audit
       -> core_validation_evidence_state
```

The Dataset-JSON and CORE branches are separate first-level descendants so executable exchange-schema validation is not made dependent on ADaMIG rule availability. CR-013 has **0 impacted TLFs** and does not propagate into MMRM, multiplicity, missing-data sensitivity or retention-survival families.

The final v0.19 clean-runner gate is required to validate CR-001–CR-013, all declared resource relationships and zero unresolved required resources before the milestone is merged.

## TLF traceability boundary

v0.19 adds standards governance, not another statistical table/listing/figure, so `spec/analysis_traceability.csv` remains **T01–T25 at registry version 0.17.0**. The workflow continues to require:

- outputs found **25/25**;
- output contracts **25/25**;
- analysis-data links **25/25**;
- QC-evidence links **25/25**;
- passed TLFs **25/25**.

## Evidence boundary

All checks are portfolio QC. Successful Dataset-JSON schema validation, metadata/lineage, cross-package, multiplicity, MI and survival QC does not make the datasets formally ADaM-conformant, the XML formally Define-XML-conformant, or any procedure sponsor-approved/regulatory-confirmatory. A `NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE` CORE state is a documented limitation, not a conformance pass. Same-author R/Python and distinct-package replication is not formal independent second-programmer validation.

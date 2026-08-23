# Statistical change-control impact assessment — portfolio version 0.18

## Purpose

The project treats controlled statistical/programming specification changes as dependency changes rather than isolated file edits. A machine-readable graph derives downstream analysis datasets, TLFs, QC evidence, documents and specifications that require review.

This is a portfolio simulation, not a sponsor-approved protocol/SAP change-control process.

## Layered version architecture

Previously validated specifications are preserved and extended rather than rewritten wholesale:

```text
v0.14 base
  -> v0.15 multiplicity extension
  -> v0.16 cross-package MMRM extension
  -> v0.17 randomized-retention TTE extension
  -> v0.18 analysis-metadata/lineage extension
```

v0.18 adds:

```text
spec/change_impact_graph_v0_18_extension.json
spec/change_requests_v0_18_extension.json
src/cdisc_portfolio/change_control_v018.py
```

The v0.18 loader requires both new extensions to declare exact base version `0.17.0`, requires matching extension version `0.18.0`, merges the graph/request layers and reruns graph validation before impact assessment.

## CR-012 — metadata and lineage definition change

CR-012 covers illustrative changes to:

- analysis-dataset metadata scope;
- variable labels, data types or roles;
- predecessor/derived origin classification;
- source-reference lineage;
- derivation descriptions;
- Define-XML reference package;
- deterministic XML-export rules or evidence boundary.

The dependency path is intentionally small and separate from inferential analysis:

```text
adam_metadata_definition
  -> adam_metadata_lineage_validation
  -> define_like_metadata_export
```

Required review resources include:

- four described generated analysis datasets;
- generated variable metadata JSON;
- variable-level lineage validation CSV;
- metadata metrics JSON;
- Define-XML-inspired XML export;
- generated metadata summary;
- controlled metadata design/QC documentation;
- `spec/adam_metadata_config.json`.

CR-012 does **not** propagate to TLFs, MMRM, multiplicity or retention-analysis components. This is deliberate: a metadata-governance change must force metadata/lineage review without pretending that it changes a statistical endpoint or creates a new table.

## Validated v0.18 live result

The merged v0.18 assessment verifies:

- simulated change requests: **12** (`CR-001`–`CR-012`);
- changed roots: **12**;
- propagated component links: **80**;
- graph-required impact relationships: **279**;
- required declarations covered: **279/279**;
- required resources resolved: **279/279**;
- missing required declarations: **0**;
- extra declared resources: **0**;
- unresolved required resources: **0**;
- overall gate: **PASS**.

CR-012 specifically verifies:

- propagated metadata components: **3**;
- required impacts: **12**;
- missing required impacts: **0**;
- extra declared impacts: **0**;
- impacted TLFs: **0**.

## Retained earlier boundaries

The layered graph keeps the earlier semantics:

- ACTOT primary-visit/MMRM changes propagate through the relevant MMRM, estimand and multiplicity evidence;
- multiplicity changes propagate to T23 but do not pull sensitivity analyses into the confirmatory family;
- cross-package validation changes force row/model validation review without claiming independent second-programmer validation;
- retention TTE changes propagate to ADTTE derivation, survival QC and T24/T25 while remaining separate from the ACTOT confirmatory family;
- metadata changes propagate only through metadata/lineage/export review.

## Negative controls

Tests require failure if:

- a version extension declares the wrong exact base version;
- graph/request extension versions disagree;
- a graph-required impact declaration is omitted;
- an unknown component or graph cycle is introduced;
- CR-012 omits the generated XML evidence;
- CR-012 is incorrectly connected to analysis families or TLFs.

Conservative extras are reported separately; missing required relationships or unresolved required resources fail the live gate.

## Generated evidence

```text
outputs/change_impact_assessment.csv
outputs/change_impact_metrics.json
outputs/change_impact_summary.md
```

The metrics also record SHA256 identities for the layered change-control specifications and the TLF traceability registry used by the same run.

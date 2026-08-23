# ADaM-style variable metadata and lineage — v0.18

## Purpose

The earlier portfolio versions demonstrate derivation, statistical analysis, QC, TLF contracts and change control. v0.18 closes a different statistical-programming gap: **variable-level analysis metadata, executable lineage and deterministic metadata export**.

The controlled scope covers four generated portfolio datasets:

- `outputs/adsl_style.csv`;
- `outputs/adae_style.csv`;
- `outputs/adqs_actot_style.csv`;
- `outputs/adtte_retention_style.csv`.

For every generated column in those files, the metadata catalog records a label, data type, role, origin type, source references, derivation text and key status. CI requires the metadata variable set to match generated CSV columns exactly; both missing and stale extra metadata fail.

## Validated live evidence

The first complete v0.18 live artifact verifies:

- datasets: **4**;
- generated variables: **85**;
- metadata variables: **85**;
- exact variable coverage: **85/85 (100%)**;
- source references: **110**;
- cross-analysis-dataset references: **39/39 resolved**;
- derived variables: **52**;
- predecessor variables: **33**;
- XML parse: **PASS**;
- XML dataset definitions: **4**;
- XML variable definitions: **85**;
- XML counts equal validated metadata counts: **PASS**.

The generated XML SHA256 is:

```text
32e378b57d85e548ac2513de0d2ec7cef678873615648e480a6d413587cc4b39
```

## Lineage model

Source references use compact `DOMAIN.VARIABLE` notation.

Raw/source domains include:

```text
DM EX DS AE QS
```

Cross-analysis references such as `ADSL.TRT01P` and `ADQS.BASE` are resolved against another dataset definition in the same metadata catalog. Controlled constants/rules use `SPEC.*` references.

The blocking validator requires:

- exact metadata-to-generated-column coverage;
- exact key metadata;
- non-empty labels and source references;
- explicit derivation text for derived variables;
- valid lineage syntax;
- resolvable upstream analysis-dataset references;
- recognized raw/source domains;
- deterministic XML generation and successful reparse;
- exact XML dataset/variable count reconciliation.

## Negative controls

Tests deliberately:

- remove a generated variable from the metadata scope;
- add stale metadata for a nonexistent variable;
- blank a derived-variable derivation;
- point analysis lineage at a nonexistent upstream variable;
- attempt to change the conformance claim from `NOT_ASSESSED` to `CONFORMANT`.

All are required to fail. The first complete v0.18 live validation passes **146 Python unit tests** before executing the public-data pipeline.

## Define-XML reference and evidence boundary

The portfolio references **CDISC Define-XML v2.1.11 (6 April 2026)**. Define-XML is used to describe metadata for tabular datasets, including ADaM analysis datasets.

v0.18 writes `outputs/define_xml_like_metadata.xml` as a deterministic **Define-XML-inspired portfolio export** containing dataset definitions, variable definitions, roles, origin types, source references and derivation descriptions.

The XML root explicitly records:

```text
referenceStandard=Define-XML
referencePackageVersion=2.1.11
conformance=NOT_ASSESSED
```

`conformance=NOT_ASSESSED` is a blocking invariant, not a disclaimer added after the fact. The tests reject an attempted `CONFORMANT` status.

The repository does **not** claim that this XML is an ODM/Define-XML v2.1.11 submission document, that it has passed official schema/conformance rules, that the `*-style` datasets are formally ADaM-conformant, or that any output is submission-ready or regulator-validated.

Official references for context:

- CDISC Define-XML: `https://www.cdisc.org/standards/data-exchange/define-xml`
- Define-XML v2.1.11: `https://www.cdisc.org/standards/data-exchange/define-xml/define-xml-v2-1`

## Generated evidence

```text
spec/adam_metadata_config.json
  -> python scripts/run_metadata_lineage.py
  -> outputs/adam_variable_metadata.json
  -> outputs/metadata_lineage_validation.csv
  -> outputs/metadata_lineage_metrics.json
  -> outputs/metadata_lineage_summary.md
  -> outputs/define_xml_like_metadata.xml
```

## Change-control linkage

`CR-012` models changes to metadata scope, labels/types/roles, origins/derivations, source lineage, Define-XML reference package or XML-export rules.

Its dependency path is:

```text
adam_metadata_definition
  -> adam_metadata_lineage_validation
  -> define_like_metadata_export
```

The validated CR-012 result has **3 propagated components / 12 required impacts / 0 TLF impacts**. It is intentionally separate from ACTOT MMRM/multiplicity and TTDISC survival-analysis families.

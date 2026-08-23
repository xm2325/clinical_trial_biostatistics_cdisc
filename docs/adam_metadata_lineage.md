# ADaM-style variable metadata and lineage — v0.18

## Why this exists

The earlier portfolio versions demonstrate derivation, statistical analysis, QC, TLF contracts and change control. v0.18 closes a different statistical-programming gap: **variable-level analysis metadata and machine-readable lineage**.

The controlled scope covers four generated portfolio datasets:

- `outputs/adsl_style.csv`;
- `outputs/adae_style.csv`;
- `outputs/adqs_actot_style.csv`;
- `outputs/adtte_retention_style.csv`.

For every generated column in those files, the v0.18 metadata catalog records a label, data type, role, origin type, source references, derivation text and key status. CI requires the metadata variable set to match the generated CSV column set exactly; missing and stale extra metadata both fail.

## Lineage model

Source references use a compact `DOMAIN.VARIABLE` notation. Raw-domain references include `DM`, `EX`, `DS`, `AE` and `QS`. Analysis-dataset references such as `ADSL.TRT01P` and `ADQS.BASE` are resolved against another dataset definition in the same metadata catalog. Controlled constants/rules use `SPEC.*` references.

The blocking validator requires exact metadata-to-generated-column coverage, exact key metadata, non-empty labels and source references, derivation text for derived variables, valid lineage syntax, resolvable analysis-dataset references, and a deterministic XML export whose dataset/variable counts match the validated metadata.

Negative-control unit tests deliberately remove a generated variable, add stale metadata, blank a derivation, point lineage at a nonexistent upstream variable and attempt to change the conformance claim. All are required to fail.

## Define-XML reference and evidence boundary

The current CDISC Define-XML package referenced by this portfolio is **v2.1.11**, published 6 April 2026. Define-XML is the CDISC data-exchange standard used to transmit metadata describing tabular datasets, including ADaM analysis datasets.

v0.18 writes `outputs/define_xml_like_metadata.xml` as a deterministic **Define-XML-inspired portfolio export**. It contains dataset definitions, variable/item definitions, roles, origin types, source references and derivation descriptions, and it is reparsed in CI.

The root explicitly records:

```text
referenceStandard=Define-XML
referencePackageVersion=2.1.11
conformance=NOT_ASSESSED
```

This is intentional. The repository does **not** claim that the XML is an ODM/Define-XML v2.1.11 submission document, that it has passed the official CDISC schema/conformance rules, that the `*-style` datasets are formally ADaM-conformant, or that any output is submission-ready or regulator-validated.

Official references used for context:

- CDISC Define-XML: https://www.cdisc.org/standards/data-exchange/define-xml
- Define-XML v2.1.11: https://www.cdisc.org/standards/data-exchange/define-xml/define-xml-v2-1

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

Generated metrics are promoted to CV/interview evidence only after the exact GitHub Actions artifact has been inspected. Development-time local counts are not treated as validated claims.

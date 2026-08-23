# CDISC standards validation evidence — v0.19

v0.19 adds an official standards-tooling layer over the validated v0.18 analysis metadata. It separates two materially different evidence states rather than treating every standards tool invocation as a conformance result:

1. **Dataset-JSON 1.1 official-schema validation is executable and passes.**
2. **CDISC CORE ADaMIG 1.3 executable validation is not available from the pinned official CORE cache, so it is explicitly recorded as `NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE` and is not represented as zero issues or conformance success.**

This is independent public-data portfolio evidence. Formal ADaM conformance, Define-XML conformance, regulatory-submission readiness and sponsor/CRO validation remain `NOT_ASSESSED`.

## Pinned official references

The reproducible CI layer pins:

- Dataset-JSON repository: `cdisc-org/DataExchange-DatasetJson`;
- Dataset-JSON commit: `a379f49a3f43c2aaed63bdeca761bdb7140df2c3`;
- Dataset-JSON version: **1.1.0**;
- CDISC CORE engine repository: `cdisc-org/cdisc-rules-engine`;
- CORE engine commit: `4270ccac9304bd0ed9627470fc9d9d922ea52939`;
- populated official CORE cache commit: `73d07f32a7469cd21111b18376166d4ec4d328f9`;
- `cdisc-open-rules` commit: `618ab81d9bb38cf499469cd01aea5aa25ecda1ab`;
- requested CORE product/version: `adamig/1-3`.

The separate populated cache snapshot is required because the pinned engine checkout contains placeholder cache files. The cache commit is declared and checked as an ancestor of the pinned engine commit.

## Dataset-JSON executable gate

`scripts/run_dataset_json.py` consumes the exact v0.18 85-variable metadata catalog and the four generated analysis datasets:

```text
outputs/adsl_style.csv
outputs/adae_style.csv
outputs/adqs_actot_style.csv
outputs/adtte_retention_style.csv
```

For every dataset, the gate requires:

- zero errors against the pinned official Dataset-JSON 1.1 JSON Schema;
- deterministic JSON serialization and reparse;
- exact record count and value/null-mask round trip;
- `keySequence` aligned to controlled metadata;
- ADaM date exchange metadata using `dataType=date`, `targetDataType=integer` and `displayFormat=E8601DA.`;
- CORE CSV transport metadata restricted to recognised `Char`/`Num` types.

Validated clean-runner evidence from GitHub Actions run **#548**:

- analysis datasets: **4**;
- variables: **85**;
- records exchanged: **2,569**;
- JSON null values preserved: **1,675**;
- official schema errors: **0**;
- CORE transport variables: **85**;
- CORE transport type vocabulary: **Char / Num**;
- gate: **PASS**.

Generated exchange files are written to `outputs/dataset_json/`; CORE transport files are written to `outputs/core_input/`.

## CORE cache and rule-availability audit

The workflow hydrates the pinned CORE engine with the pinned populated official cache, installs CORE in an isolated Python environment, then runs both:

```text
core.py list-rules
core.py list-rules --standard adamig --version 1-3
```

The audit uses Python standard-library `pickletools` to inspect literal strings in cache pickle opcodes without executing pickle payloads. It also hashes required cache files, rejects five-byte placeholders and compares the filtered rule discovery with the complete rule inventory.

Run #548 demonstrates:

- unique CORE rule IDs available across the populated cache: **981**;
- literal CORE IDs observed in `rules_dictionary.pkl`: **981**;
- literal CORE IDs observed in `rules.pkl`: **981**;
- dictionary/rules-data overlap: **981/981**;
- requested ruleset key `adamig/1-3`: **present**;
- related keys `adamig/1-0` through `adamig/1-3`: **present**;
- rule IDs returned for `adamig/1-3`: **0**;
- required cache files missing: **0**;
- required cache placeholders: **0**.

This distinguishes a healthy populated CORE cache from an unavailable ADaMIG executable ruleset. The project does not rewrite the official cache or insert an alias/compatibility shim to manufacture a green rule run.

## `cdisc-open-rules` source-state evidence

At the pinned `cdisc-open-rules` commit, the CI audit observes:

- **191** YAML files below `Unpublished/ADAMIG`;
- **1** published YAML file explicitly referencing ADaMIG: `Published/CORE-000560/rule.yml`.

`CORE-000560` is a published, fully executable rule requiring the ADSL dataset to exist and cites ADaMIG 1.3. Its presence does **not** change the key fact that the pinned official CORE cache returns zero rule IDs for the requested `adamig/1-3` ruleset. Therefore the project does not infer that a complete executable ADaMIG 1.3 ruleset is available.

## Mutually exclusive CORE evidence states

The CI deliberately has two paths.

### Official executable rules available

If future pinned official cache evidence returns at least one rule ID for `adamig/1-3`, the workflow runs `core.py validate` and blocks on:

- non-zero CORE CLI exit;
- empty `Rules_Report`;
- unknown rule status;
- zero executed rules;
- any `EXECUTION ERROR`;
- reported standard/version mismatch;
- any attempted formal conformance claim.

`ISSUE REPORTED` is retained as review evidence rather than treated as a tool crash.

### Official executable rules unavailable

For the current pinned official cache, the controlled state is:

```text
NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE
```

The gate requires:

- cache audit itself passed;
- actual state equals the explicitly configured expected state;
- requested rule count is exactly zero;
- formal conformance remains `NOT_ASSESSED`.

It writes machine-readable availability evidence but deliberately does **not** create `core_official_report.json`. Zero rules is therefore never presented as zero issues, a successful ADaM validation, or a conformance result.

Run #548 records:

- executable CORE ADaMIG validation performed: **false**;
- rules executed: **0**;
- execution status: **`NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE`**;
- evidence gate: **PASS**.

## Change control

v0.19 adds `CR-013 — Official CDISC standards-engine or rule-availability change`. Its controlled dependency chain is:

```text
standards_validation_configuration
  -> dataset_json_exchange_validation
  -> core_rule_availability_audit
       -> core_validation_evidence_state
```

The two first-level branches are independent: Dataset-JSON schema validation can execute even when the requested CORE ADaMIG ruleset is unavailable.

CR-013 requires review of the four exchanged analysis datasets, Dataset-JSON exchange/QC artifacts, CORE rule-discovery/cache evidence, CORE executed-versus-unavailable evidence state, documentation and the standards-validation specification. It has **zero TLF impact** and does not propagate into MMRM, multiplicity, missing-data sensitivity or retention-survival components.

## Evidence boundary

The project demonstrates reproducible standards integration, negative controls, provenance pinning, machine-readable validation states and explicit limitation handling. It does not claim:

- submission-ready or formally ADaM-conformant analysis datasets;
- formal Define-XML conformance;
- sponsor/CRO production validation;
- regulatory submission experience;
- that automated CORE rules are sufficient for complete ADaM conformance;
- that an unavailable rule set has passed with zero issues.

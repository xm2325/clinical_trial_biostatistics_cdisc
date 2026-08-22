# Statistical change control and impact assessment — portfolio v0.11

## Purpose

The executable statistical change-control layer answers a practical review question: when a protocol, SAP or estimand assumption changes, which downstream analysis datasets, TLFs, QC evidence, controlled documents and machine-readable specifications must be reviewed again?

Two machine-readable records drive the gate:

- `spec/change_impact_graph.json` defines transitive dependency propagation;
- `spec/change_requests.json` contains illustrative change requests and the impacts declared for review.

The graph and request specifications must declare the same version. A version mismatch is a hard failure. The CI gate derives required impacts from the graph and compares them with the declared review set; an omitted required item or unresolved required resource fails the build.

> **Evidence boundary:** these change requests are portfolio simulations. They are not sponsor-approved protocol amendments, approved SAP changes, production change-control records, regulatory commitments or evidence that the hypothetical changes were adopted in the source trial.

## Impact categories

| Category | Meaning in this portfolio |
|---|---|
| `analysis_datasets` | Generated analysis datasets that must be regenerated or reviewed |
| `tlfs` | Planned TLF IDs whose analysis or displayed denominator is affected |
| `qc` | Generated QC evidence that must be rerun/reviewed |
| `documents` | Statistical/reviewer documents requiring consistency review |
| `specs` | Machine-readable estimand, design or randomisation specifications requiring review |

For TLF impacts, each ID is resolved through `spec/analysis_traceability.csv`; the linked generated output must exist in the same CI run.

## Transitive dependency examples

```text
safety_population_definition
    -> adsl_population_flags
        -> adae_subject_context
        -> safety_population_tlfs

teae_followup_window
    -> adae_teae_flag
        -> teae_tlfs

actot_primary_visit
    -> ancova_primary_analysis -> actot_primary_tlfs
    -> mmrm_primary_contrast_focus
    -> protocol_design_assumptions -> randomisation_planned_n

treatment_discontinuation_strategy
    -> actot_missingness_review
    -> mmrm_estimand_alignment -> mmrm_tlfs
```

This prevents an impact review from stopping at only the first dataset or program that obviously changes.

## Portfolio scenarios

| Change | What is changed in the simulation | Propagated components | Required impacts | TLF scope |
|---|---|---:|---:|---|
| CR-001 | Safety population definition | 4 | 18 | T01–T07 |
| CR-002 | TEAE follow-up 30 → 45 days | 3 | 14 | T04–T07 |
| CR-003 | Primary ACTOT focus Week 24 → Week 16 | 6 | 27 | T08–T12, T15 |
| CR-004 | Primary MMRM covariance UN → heterogeneous AR(1) | 3 | 11 | T11–T15 |
| CR-005 | Treatment-discontinuation strategy treatment-policy → hypothetical | 4 | 18 | T11–T17 |

The v0.11 first-pass live run covers **88/88 required impact relationships** and resolves **88/88 required resources**, with zero missing and zero extra declarations.

CR-005 is important because it starts from the scientific question rather than a code file. Changing the intercurrent-event strategy requires review of the estimand specification, MMRM input/fit path, longitudinal TLFs, missingness TLFs, QC evidence and controlled statistical documents.

None of the five scenarios silently changes the current analysed portfolio. The current analysis retains the 30-day TEAE window, Week 24 ACTOT focus, unstructured primary MMRM and treatment-policy handling of recorded treatment discontinuation.

## Acceptance rules

For every change request, CI requires:

1. graph and request versions to be non-empty and identical;
2. every changed component to exist in the graph;
3. the dependency graph to be acyclic;
4. every change request to contain a rationale;
5. every graph-derived required impact to be declared;
6. every required static document/specification to exist;
7. every required generated dataset/QC output to exist in the live run;
8. every impacted TLF to resolve through the SAP-to-TLF registry and its generated output to exist.

Conservative extra review items are allowed but reported.

## Negative controls

Unit tests deliberately require failure when:

- a graph-required TLF is omitted from the declared impact set;
- CR-005 omits T16 missingness review;
- a changed component is unknown;
- a dependency cycle is introduced;
- graph and request versions disagree.

Separate tests verify transitive propagation and permit conservative extra review items.

## Generated evidence

`scripts/run_change_impact.py` writes:

- `outputs/change_impact_assessment.csv` — one row per change/resource relationship;
- `outputs/change_impact_metrics.json` — aggregate counts plus SHA256 identity for graph, requests and traceability registry;
- `outputs/change_impact_summary.md` — concise scenario-level review.

The script exits non-zero when a required declaration is missing, a specification is inconsistent or a required downstream resource cannot be resolved.

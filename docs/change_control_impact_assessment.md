# Statistical change control and impact assessment — portfolio v0.10

## Purpose

Version 0.10 adds an executable statistical change-control exercise. It is designed to answer a practical review question: when a protocol or SAP assumption changes, which downstream analysis datasets, TLFs, QC evidence and controlled documents must be reviewed again?

The implementation separates two machine-readable records:

- `spec/change_impact_graph.json` defines dependency propagation from a changed statistical component to downstream review targets;
- `spec/change_requests.json` contains illustrative change requests and the impacts declared for review.

The CI gate derives the required impacts from the graph and compares them with the declared change assessment. A required downstream item that is omitted causes the build to fail.

> **Evidence boundary:** the change requests are portfolio simulations. They are not sponsor-approved protocol amendments, approved SAP changes, production change-control records, regulatory commitments or evidence that the changed analyses were actually adopted in the source trial.

## Impact categories

The gate reviews five impact categories:

| Category | Meaning in this portfolio |
|---|---|
| `analysis_datasets` | Generated analysis datasets that must be regenerated or reviewed |
| `tlfs` | Planned TLF IDs whose analysis or displayed denominator is affected |
| `qc` | Generated QC evidence that must be rerun/reviewed |
| `documents` | Statistical/reviewer documents that require review for consistency |
| `specs` | Machine-readable planning/schedule specifications whose assumptions require review |

For TLF impacts, the gate resolves each TLF ID through `spec/analysis_traceability.csv` and verifies that the corresponding generated output exists in the live CI run.

## Dependency propagation

The graph is deliberately transitive. A change request declares only the component that changed; downstream components are then traversed until no new dependency nodes remain.

Examples:

```text
safety_population_definition
    -> adsl_population_flags
        -> adae_subject_context
        -> safety_population_tlfs

teae_followup_window
    -> adae_teae_flag
        -> teae_tlfs

actot_primary_visit
    -> ancova_primary_analysis
        -> actot_primary_tlfs
    -> mmrm_primary_contrast_focus
    -> protocol_design_assumptions
        -> randomisation_planned_n

mmrm_primary_covariance
    -> mmrm_model_fit
        -> mmrm_tlfs
```

This prevents a change assessment from stopping at the first dataset or program that obviously changes.

## Portfolio change scenarios

### CR-001 — Safety population definition

This scenario tests whether a revised safety-population rule reaches ADSL-style population flags, ADAE-style subject context, the programming/reviewer QC layers and all TLFs whose population or denominator depends on safety status.

### CR-002 — TEAE follow-up window

This scenario changes the illustrative TEAE follow-up window from 30 to 45 days after treatment end. The required review therefore includes the ADAE-style treatment-emergent flag, TEAE outputs and each QC layer that independently reconstructs or checks TEAE status.

The current analysed portfolio remains based on the existing 30-day TEAE definition; CR-002 is an impact-assessment exercise, not a silent change to the analysed results.

### CR-003 — Primary ACTOT visit

This scenario changes the primary analysis focus from Week 24 to Week 16. The dependency graph requires review of ANCOVA analysis-subject construction, the relevant ACTOT/MMRM TLFs, protocol-design assumptions and the illustrative randomisation count linked to the selected planning scenario.

The current analysed portfolio remains based on the existing Week 24 analyses; the scenario is used only to test change propagation.

### CR-004 — Primary MMRM covariance

This scenario changes the primary longitudinal covariance structure from unstructured to heterogeneous AR(1). The graph propagates the change through model fit/QC and all TLFs that report, compare or diagnose the MMRM.

The current primary MMRM remains the pre-specified unstructured model, with heterogeneous AR(1) retained as the existing sensitivity analysis.

## Acceptance rules

For each change request, CI requires:

1. every changed component to exist in the dependency graph;
2. the dependency graph to be acyclic;
3. every change request to contain a rationale;
4. every graph-derived required impact to be declared for review;
5. every required static document/specification to exist in the repository;
6. every required generated dataset/QC output to exist in the live run;
7. every impacted TLF ID to resolve through the SAP-to-TLF registry and its generated output to exist.

Conservative extra review items are allowed and reported rather than treated as failures.

## Negative controls

Unit tests deliberately demonstrate failure behaviour by:

- removing a graph-required TLF from a declared impact assessment;
- requesting an unknown changed component;
- inserting a cycle into the dependency graph.

Additional tests verify that transitive propagation reaches downstream dataset, QC and TLF resources and that conservative extra review items remain permitted.

## Generated evidence

`scripts/run_change_impact.py` writes:

- `outputs/change_impact_assessment.csv` — one row per change/resource relationship, including required/declared/existence status;
- `outputs/change_impact_metrics.json` — aggregate counts and SHA256 identity for the graph, change requests and SAP-to-TLF registry;
- `outputs/change_impact_summary.md` — concise change-level summary.

The script exits non-zero when a required declaration is missing or a required downstream resource cannot be resolved.

# Statistical change control and impact assessment — portfolio v0.12

## Purpose

The executable change-control layer asks: if a statistical assumption changes, which downstream analysis datasets, TLFs, QC evidence, documents and machine-readable specifications require review?

Two files drive the gate:

- `spec/change_impact_graph.json` — transitive dependency graph;
- `spec/change_requests.json` — simulated changes and their declared review scope.

Both specifications must declare the same version. A version mismatch, missing graph-required impact or unresolved required resource fails CI.

> **Evidence boundary:** all change requests are portfolio simulations. They are not sponsor-approved amendments, production change records or regulatory commitments.

## Controlled impact categories

| Category | Meaning |
|---|---|
| `analysis_datasets` | generated analysis/input files requiring regeneration or review |
| `tlfs` | planned TLF IDs affected by the change |
| `qc` | generated QC evidence requiring rerun/review |
| `documents` | statistical/reviewer documents requiring consistency review |
| `specs` | machine-readable estimand/design/randomisation/sensitivity specifications |

TLF IDs are resolved through `spec/analysis_traceability.csv`; the linked generated output must exist in the same CI run.

## v0.12 dependency additions

The fixed-delta sensitivity is not treated as an isolated downstream report.

```text
actot_primary_visit
    -> mnar_sensitivity_assumption
        -> mnar_sensitivity_calculation
            -> T18 / T19

mmrm_primary_covariance
    -> mmrm_model_fit
        -> mnar_sensitivity_calculation
            -> T18 / T19

treatment_discontinuation_strategy
    -> mnar_sensitivity_assumption
        -> mnar_sensitivity_calculation
            -> T18 / T19
```

Therefore changing the primary endpoint visit, the primary MMRM fit or the intercurrent-event strategy forces re-review of the relevant sensitivity outputs rather than leaving them based on stale assumptions.

## Verified v0.12 scenarios

The live run covers **118/118 graph-required impact relationships** and resolves **118/118 required resources**, with zero missing and zero extra declarations.

| Change | Simulated change | Propagated components | Required impacts | Impacted TLFs |
|---|---|---:|---:|---|
| CR-001 | Safety population definition | 4 | 18 | T01–T07 |
| CR-002 | TEAE follow-up 30 → 45 days | 3 | 14 | T04–T07 |
| CR-003 | Primary ACTOT focus Week 24 → Week 16 | 9 | 35 | T08–T12, T15, T18–T19 |
| CR-004 | Primary MMRM covariance UN → heterogeneous AR(1) | 5 | 15 | T11–T15, T18–T19 |
| CR-005 | Discontinuation strategy treatment-policy → hypothetical | 7 | 25 | T11–T19 |
| CR-006 | Fixed-delta sensitivity assumptions | 3 | 11 | T18–T19 |

CR-006 changes the adverse delta range or scenario multipliers. It requires regeneration/review of `outputs/mnar_sensitivity_inputs.csv`, T18, T19, dedicated sensitivity QC, the sensitivity specification and controlled missing-data/SAP documentation.

None of the six simulated requests changes the analysed portfolio. The current analysis retains the 30-day TEAE window, Week 24 ACTOT focus, unstructured primary MMRM, treatment-policy strategy for recorded treatment discontinuation and the v0.12 fixed-delta grid/scenarios.

## Acceptance rules

For every request CI requires:

1. graph/request versions to be non-empty and identical;
2. every changed component to exist;
3. an acyclic dependency graph;
4. a non-empty rationale;
5. every transitive graph-required impact to be declared;
6. every required static document/specification to exist;
7. every required generated dataset/QC output to exist in the live run;
8. every impacted TLF to resolve through the TLF registry and have a generated output.

Conservative extra review items are permitted but reported.

## Negative controls

Unit tests deliberately require failure when:

- a graph-required TLF is omitted;
- graph/request versions disagree;
- an unknown component is requested;
- a dependency cycle is introduced;
- CR-005 omits a missingness or MNAR-sensitivity TLF;
- CR-006 omits T19;
- a primary MMRM covariance change does not reach T18/T19 and sensitivity QC.

These tests protect the dependency rules themselves; they do not substitute for the live resource-existence gate.

## Generated evidence

```text
outputs/change_impact_assessment.csv
outputs/change_impact_metrics.json
outputs/change_impact_summary.md
```

`change_impact_metrics.json` records the controlled specification version and SHA256 identities for the dependency graph, request file and TLF registry. The runner exits non-zero if a required declaration/resource is missing.

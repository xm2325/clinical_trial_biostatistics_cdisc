# Statistical change control and impact assessment — portfolio v0.13

## Purpose

The executable change-control layer asks: if a statistical assumption changes, which downstream analysis datasets, TLFs, QC evidence, documents and machine-readable specifications require review?

Two files drive the gate:

- `spec/change_impact_graph.json` — transitive dependency graph;
- `spec/change_requests.json` — simulated changes and their declared review scope.

Both specifications must declare the same version. The current request specification is **0.13.0** and contains **seven** simulated change requests. A version mismatch, missing graph-required impact or unresolved required resource fails CI.

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

## Dependency design through v0.13

The deterministic fixed-delta analysis and subject-level MI analysis are both linked to their upstream assumptions. Neither is treated as an isolated report.

```text
actot_primary_visit
    -> estimand / primary analysis timing
    -> fixed-delta sensitivity inputs
    -> subject-level MI inputs/model
    -> T18 / T19 / T20 / T21

treatment_discontinuation_strategy
    -> estimand / observed-data path
    -> missingness and sensitivity assumptions
    -> T11-T21 as declared by the request graph

mnar_sensitivity_assumption
    -> fixed-delta calculation
    -> T18 / T19

mi_sensitivity_assumption
    -> pairwise MI + Rubin pooling
    -> MCSE precision QC
    -> T20 / T21
```

The primary MMRM covariance continues to propagate to the deterministic fixed-delta analysis because T18/T19 use the primary Week 24 MMRM contrast as their reference. The v0.13 pairwise MI analysis has its own controlled longitudinal imputation model under `spec/mi_sensitivity.json` and is not incorrectly tied to equality with the primary MMRM estimator.

## Controlled v0.13 scenarios

| Change | Simulated change | Main TLF scope |
|---|---|---|
| CR-001 | Safety population definition | T01-T07 |
| CR-002 | TEAE follow-up 30 → 45 days | T04-T07 |
| CR-003 | Primary ACTOT focus Week 24 → Week 16 | T08-T12, T15, T18-T21 |
| CR-004 | Primary MMRM covariance UN → heterogeneous AR(1) | T11-T15, T18-T19 |
| CR-005 | Treatment-discontinuation strategy treatment-policy → hypothetical | T11-T21 |
| CR-006 | Deterministic fixed-delta sensitivity assumptions | T18-T19 |
| CR-007 | Subject-level MI sensitivity assumptions | T20-T21 |

### CR-003 — primary ACTOT visit

CR-003 now reaches the subject-level MI branch as well as the deterministic branch. Its declared impacts include the pairwise MI input counts, T20/T21, MI QC, MCSE QC, draw diagnostics, delta audit, `spec/mi_sensitivity.json`, the v0.13 SAP addendum and the consolidated statistical documents.

This prevents a primary endpoint-timing change from leaving T20/T21 based on a stale Week 24 analysis definition.

### CR-005 — treatment-discontinuation intercurrent-event strategy

CR-005 now reaches T20/T21 and their MI/MCSE QC resources in addition to the estimand, MMRM, missingness and deterministic fixed-delta paths.

This is important because an intercurrent-event strategy change can alter the scientific handling expected for missing/post-discontinuation outcomes; it must therefore trigger review of the MI sensitivity assumptions rather than leave a disconnected sensitivity analysis.

### CR-006 — deterministic fixed-delta assumptions

CR-006 changes the adverse delta range or scenario multipliers used by the deterministic v0.12 mean-shift diagnostic. It requires review/regeneration of:

- `outputs/mnar_sensitivity_inputs.csv`;
- T18 and T19;
- `outputs/mnar_sensitivity_qc.csv`;
- `spec/mnar_sensitivity.json`;
- controlled missing-data/SAP/TLF/QC documentation.

CR-006 does not silently modify the v0.13 subject-level MI specification.

### CR-007 — subject-level MI assumptions

CR-007 is new in v0.13 and controls changes to:

- the number of `rbmi` imputations;
- the controlled longitudinal imputation model;
- the Monte Carlo precision threshold;
- the Week 24 delta scenarios.

Its declared impacts include:

- `outputs/rbmi_pairwise_input_counts.csv`;
- T20 and T21;
- `outputs/rbmi_mi_qc.csv`;
- `outputs/rbmi_mcse_qc.csv`;
- `outputs/rbmi_draw_diagnostics.csv`;
- `outputs/rbmi_delta_audit.csv`;
- `spec/mi_sensitivity.json`;
- `docs/sap.md`, `docs/tlf_shells.md`, `docs/qc_plan.md`, missing-data/MI documentation and the v0.13 SAP addendum.

The current controlled MI settings remain 200 imputations, the specified Week 8/16/24 approximate-Bayesian longitudinal model, the 7.5% `MCSE(estimate) / pooled SE` threshold and four Week 24 scenarios. A simulated change request does not itself change these settings.

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

Conservative extra review items are permitted but reported. A release is accepted only from the same final commit whose live resources and documentation pass these checks.

## Negative and regression controls

Tests require failure when controlled dependency rules are broken, including cases such as:

- a graph-required TLF is omitted;
- graph/request versions disagree;
- an unknown component is requested;
- a dependency cycle is introduced;
- CR-005 omits a required missingness or sensitivity TLF;
- CR-006 omits T19;
- a primary MMRM covariance change does not reach T18/T19 and deterministic sensitivity QC;
- CR-003 or CR-005 fails to propagate to T20/T21 and their v0.13 MI review path;
- CR-007 omits controlled MI outputs/QC/specification impacts.

A previous v0.13 CI iteration caught a real regression caused by tests that still hard-coded the v0.12 change count. The regression was corrected rather than weakening the seven-request control.

## Generated evidence

```text
outputs/change_impact_assessment.csv
outputs/change_impact_metrics.json
outputs/change_impact_summary.md
```

`change_impact_metrics.json` records the controlled specification version and SHA256 identities for the dependency graph, request file and TLF registry. The runner exits non-zero if a required declaration/resource is missing.
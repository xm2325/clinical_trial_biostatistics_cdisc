# Statistical change control and impact assessment — portfolio v0.14

## Purpose

The change-control layer answers a practical review question: if a statistical definition or assumption changes, which downstream datasets, TLFs, QC evidence, documents and machine-readable specifications must be reviewed or regenerated?

Two files drive the gate:

- `spec/change_impact_graph.json` — transitive dependency graph;
- `spec/change_requests.json` — simulated portfolio changes and their declared review scope.

Both must declare the same version. Missing required impacts or unresolved required resources fail CI.

> All requests are portfolio simulations. They are not sponsor-approved amendments or production change records.

## v0.14 reference-based MI dependencies

Version 0.14 adds three controlled dependency nodes:

```text
reference_based_mi_assumption
  -> reference_based_mi_calculation
      -> reference_based_mi_tlf (T22)
```

The assumption node controls the recorded-discontinuation timing rule, placebo reference mapping, MAR/JR/CR/CIR strategy set and reference-based MCSE rule.

It depends on upstream choices rather than forming a stand-alone analysis:

```text
actot_primary_visit -----------------------> reference_based_mi_assumption
treatment_discontinuation_strategy --------> reference_based_mi_assumption
mi_sensitivity_assumption -----------------> reference_based_mi_assumption
```

The last path is required because v0.14 reuses the v0.13 pairwise imputation model and 200-imputation setting.

## Verified v0.14 scenarios

The live run assessed **8 change requests** and verified **195/195 required impact relationships** and **195/195 required resources**. Missing declarations, extra declarations and unresolved required resources were all zero.

| Change | Propagated components | Required impacts | Main TLF scope |
|---|---:|---:|---|
| CR-001 safety population definition | 4 | 18 | T01-T07 |
| CR-002 TEAE follow-up window | 3 | 14 | T04-T07 |
| CR-003 primary ACTOT visit | 15 | 55 | T08-T12, T15, T18-T22 |
| CR-004 primary MMRM covariance | 5 | 15 | T11-T15, T18-T19 |
| CR-005 treatment-discontinuation strategy | 13 | 44 | T11-T22 |
| CR-006 deterministic fixed-delta assumptions | 3 | 11 | T18-T19 |
| CR-007 subject-level MI base assumptions | 6 | 24 | T20-T22 |
| CR-008 reference-based MI assumptions | 3 | 14 | T22 |

CR-008 requires review/regeneration of:

- `outputs/rbmi_reference_ice_audit.csv`;
- T22;
- `outputs/estimand_review.csv`;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`;
- the v0.14 reference-based specification and controlled documents.

## Negative controls

Unit tests require failure when, among other cases:

- a graph-required TLF is omitted;
- graph/request versions disagree;
- an unknown component or dependency cycle is introduced;
- CR-005 omits missingness, deterministic, subject-level MI or T22 outputs;
- CR-007 changes the MI base without reaching T22;
- CR-008 omits T22, estimand review or reference-based MCSE evidence.

## Acceptance rules

For each request CI requires:

1. graph/request versions are non-empty and identical;
2. every changed component exists;
3. the graph is acyclic;
4. the rationale is non-empty;
5. every transitive required impact is declared;
6. every required static document/spec exists;
7. every required generated dataset/QC output exists in the live run;
8. each impacted TLF resolves through the versioned registry and has a generated output.

## Generated evidence

```text
outputs/change_impact_assessment.csv
outputs/change_impact_metrics.json
outputs/change_impact_summary.md
```

The metrics file records specification SHA256 identities and the exact required-impact counts used in that CI run.

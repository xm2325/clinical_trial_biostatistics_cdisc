# Statistical change-control impact assessment — portfolio version 0.15

## Purpose

The project treats statistical specification changes as dependency changes rather than isolated file edits. A machine-readable graph derives downstream analysis datasets, TLFs, QC evidence, documents and specifications that require review.

This remains a portfolio simulation, not a sponsor-approved protocol/SAP change-control process.

## Version architecture

The validated v0.14 base specifications remain byte-preserved:

```text
spec/change_impact_graph.json
spec/change_requests.json
```

v0.15 adds controlled extensions:

```text
spec/change_impact_graph_v0_15_extension.json
spec/change_requests_v0_15_extension.json
```

`src/cdisc_portfolio/change_control_v015.py` requires both extensions to declare the exact base version `0.14.0` and the same new logical version `0.15.0`. It then validates the merged acyclic graph and assesses the merged request set.

This design avoids rewriting large, already validated base JSON merely to add the multiplicity dependency layer.

## v0.15 multiplicity propagation

Three new logical components are added:

```text
primary_multiplicity_assumption
  -> primary_multiplicity_calculation
  -> primary_multiplicity_tlf (T23)
```

Upstream propagation is added from:

- `protocol_design_assumptions` -> multiplicity assumptions;
- `mmrm_primary_contrast_focus` -> multiplicity calculation;
- `mmrm_primary_covariance` -> multiplicity calculation;
- `mmrm_estimand_alignment` -> multiplicity calculation.

Consequently:

- **CR-003** primary ACTOT visit now reaches T23;
- **CR-004** primary MMRM covariance now reaches T23;
- **CR-005** treatment-discontinuation strategy / MMRM-estimand alignment now reaches T23;
- **CR-009** directly controls the multiplicity rule and reaches T23.

CR-009 covers illustrative changes to the family-wise alpha, number of controlled Week 24 hypotheses or Bonferroni decision procedure. It requires review of `spec/multiplicity.json`, `spec/protocol_design.json`, the primary MMRM contrast input, MMRM/multiplicity QC, the v0.15 multiplicity documents and T23.

## Verified live result

The v0.15 live run assesses **9 change requests** and verifies:

- propagated component links: **62**;
- graph-required impact relationships: **217**;
- required declarations covered: **217/217**;
- required resources resolved: **217/217**;
- missing required declarations: **0**;
- extra declared resources: **0**;
- unresolved required resources: **0**;
- overall gate: **PASS**.

Selected request-level results:

| Change | Propagated components | Required impacts | Impacted v0.15 TLFs |
|---|---:|---:|---|
| CR-003 primary ACTOT visit | 18 | 62 | includes T23 |
| CR-004 primary MMRM covariance | 7 | 18 | includes T23 |
| CR-005 discontinuation strategy | 15 | 47 | includes T23 |
| CR-009 multiplicity rule | 3 | 9 | T23 |

## Negative controls

Tests require failure if:

- a v0.15 extension declares the wrong base version;
- the merged request/graph versions disagree;
- T23 is omitted from CR-009;
- any graph-required downstream declaration is omitted;
- an unknown component or graph cycle is introduced.

The gate does not reward conservative over-declaration: extra resources are reported separately, while missing required relationships or unresolved required resources fail the live run.

## Generated evidence

```text
outputs/change_impact_assessment.csv
outputs/change_impact_metrics.json
outputs/change_impact_summary.md
```

The metrics record SHA256 identities for both v0.14 base specifications, both v0.15 extensions and the TLF registry used in the same run.

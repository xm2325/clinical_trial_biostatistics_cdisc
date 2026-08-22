# Statistical Analysis Plan addendum — portfolio v0.10

## 1. Status

This addendum extends the portfolio statistical documentation with the v0.10 statistical change-control and impact-assessment framework. It does **not** adopt any of the illustrative changes in `spec/change_requests.json` and does not alter the current statistical analyses specified by `docs/sap.md` and the v0.9 review addendum.

The current portfolio therefore retains:

- safety population based on at least one observed EX record;
- treatment-emergent AE follow-up through 30 days after treatment end;
- Week 24 as the current ACTOT primary analysis focus in the portfolio analyses/planning exercise;
- unstructured covariance as the current primary ACTOT MMRM covariance, with heterogeneous AR(1) as sensitivity.

This is an independent portfolio document. It is not a sponsor-approved SAP amendment, protocol amendment, production change-control record or regulatory-submission document.

## 2. Reason for addendum

Version 0.10 adds a controlled way to answer a review question that arises after statistical specifications are written: if one assumption changes, what downstream analysis work requires reassessment?

`spec/change_impact_graph.json` records transitive dependencies between statistical components. `spec/change_requests.json` records illustrative changed components and the downstream resources declared for review. The CI gate derives required impacts independently from the graph and compares them with the declaration.

## 3. Impact categories

The change-control assessment covers:

1. analysis datasets that require regeneration or review;
2. TLFs whose analysis, population, denominator or interpretation may change;
3. QC evidence that must be rerun or reviewed;
4. statistical/reviewer documents requiring consistency review;
5. machine-readable design or randomisation specifications whose assumptions are linked to the changed component.

TLF IDs are resolved through the existing `spec/analysis_traceability.csv` registry so that a change-impact declaration cannot refer only to an abstract table identifier; the generated output must resolve in the same CI run.

## 4. Illustrative change requests

### CR-001 — Safety population definition

A changed safety-population definition propagates through ADSL-style population flags, ADAE-style subject context, safety-population denominators and T01–T07. This scenario has 4 propagated components and 18 required impacts in the verified v0.10 graph.

### CR-002 — TEAE follow-up window

An illustrative change from 30 to 45 days propagates through ADAE-style `TRTEMFL`, TEAE QC and T04–T07. This scenario has 3 propagated components and 14 required impacts.

The 45-day rule is **not** adopted in the current analysis.

### CR-003 — Primary ACTOT visit

An illustrative primary-focus change from Week 24 to Week 16 propagates through ANCOVA analysis-subject construction, ACTOT/MMRM reporting, protocol-design assumptions and the randomisation count linked to the selected planning scenario. This scenario has 6 propagated components and 24 required impacts, including T08–T12 and T15.

Week 16 is **not** adopted as the current primary portfolio analysis visit.

### CR-004 — Primary MMRM covariance

An illustrative primary covariance change from unstructured to heterogeneous AR(1) propagates through model fit/QC and T11–T15. This scenario has 3 propagated components and 11 required impacts.

Heterogeneous AR(1) remains the current sensitivity model rather than replacing the unstructured primary model.

## 5. Acceptance

The verified v0.10 GitHub Actions run requires every changed component to exist in an acyclic dependency graph, every graph-derived required impact to be declared, and every required resource to resolve.

The live evidence is:

| Change-control measure | Verified result |
|---|---:|
| Portfolio change requests | **4/4 assessed** |
| Graph-required impact declarations | **67/67 covered** |
| Required downstream resources | **67/67 resolved** |
| Missing required declarations | **0** |
| Extra declared resources | **0** |

The full workflow also retains **40/40 Python unit tests**, **24/24 Python pipeline QC**, **16/16 R/Python programming QC**, **11/11 MMRM QC**, **24/24 analysis-dataset/TLF reviewer checks**, **15/15 SAP-to-TLF traceability**, **7/7 protocol-design QC** and **10/10 randomisation/kit QC**.

## 6. Failure-mode testing

Automated tests require failure when:

- a graph-required TLF is omitted from a change declaration;
- a change references an unknown dependency component;
- the dependency graph contains a cycle.

Tests also verify transitive propagation and allow conservative extra review items while reporting them explicitly.

## 7. Outputs

The v0.10 change-control gate writes:

- `outputs/change_impact_assessment.csv`;
- `outputs/change_impact_metrics.json`;
- `outputs/change_impact_summary.md`.

The metrics record SHA256 identity for the dependency graph, change-request specification and SAP-to-TLF registry used in the run. A missing required declaration or unresolved required resource exits non-zero and blocks CI.

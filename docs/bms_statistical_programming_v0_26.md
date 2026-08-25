# v0.26 — BMS statistical-programming evidence

## Objective

v0.26 is a role-driven upgrade for Senior Statistical Programmer vacancies such
as Bristol Myers Squibb. It does **not** add another statistical model. Instead,
it strengthens evidence around the work expected between source data,
analysis-dataset programming, TFL production, QC, metadata and submission
handoff.

The controlled path is:

```text
public SDTM/source data
  -> SAS analysis-dataset source
  -> SAS TFL source
  -> static semantic/QC review in CI
  -> external licensed-SAS execution/reconciliation contract
  -> analysis Data Definition Table
  -> Define-XML 2.1-shaped portfolio candidate
  -> Pinnacle 21 handoff contract
  -> SHA256 evidence manifest
```

## Why this is different from v0.25

v0.25 proved a controlled clinical-programming release path across seven
representative packages. v0.26 answers a narrower BMS-style question:
**can the portfolio show reviewable SAS source for both derived datasets and
TFLs, and can those artefacts be handed off through controlled metadata and
validation steps without overstating execution or submission readiness?**

## SAS evidence

Four controlled SAS source programs are reviewed:

- `sas/macros/qc_contract.sas` — fail-fast required-variable checks.
- `sas/derive_adsl_adae.sas` — ADSL-style and ADAE-style derivation translation
  from the same public DM/EX/DS/AE sources used by the executed Python workflow.
- `sas/teae_risk_difference.sas` — subject-level any-TEAE risk-difference TFL
  translation using `PROC FREQ` and Fisher exact testing.
- `sas/actot_mmrm_primary.sas` — ACTOT longitudinal MMRM translation using
  `PROC MIXED`, REML, unstructured within-subject covariance and Satterthwaite
  denominator degrees of freedom.

CI verifies required SAS semantic fragments, translation-basis files and the
explicit runtime limitation. This is source-review evidence; GitHub Actions
does not contain a licensed SAS runtime.

## External SAS execution/reconciliation contract

`outputs/sas_external_execution_contract.csv` defines what a licensed SAS run
must export and what it must be compared against. The contract covers:

- SAS-generated ADSL-style and ADAE-style datasets;
- low/high dose TEAE risk-difference and Fisher ODS outputs;
- MMRM treatment-difference ODS output.

The runtime status remains
`NOT_EXECUTED_NO_SAS_RUNTIME` until those external artefacts actually exist and
are reconciled. Static source review is not promoted to executed-SAS evidence.

## Metadata and submission handoff

The v0.26 gate builds two review artefacts from the live controlled datasets:

1. `analysis_data_definition_table_v0_26.csv` — dataset/variable inventory,
   order, data type, key status, contract-required status and missingness.
2. `define_xml_candidate_v0_26.xml` — a well-formed portfolio metadata candidate
   shaped around ODM/Define-XML 2.1 concepts for ADSL-style, ADAE-style,
   ADQS-style and ADTTE-style datasets.

The XML artefact is intentionally labelled a **portfolio candidate**, not a
validated Define-XML submission file and not evidence of formal ADaM
conformance.

`outputs/pinnacle21_handoff_v0_26.csv` records the four dataset/metadata packages
that would be supplied to an authorised Pinnacle 21 environment. Its status is
fixed to `NOT_EXECUTED_NO_PINNACLE21_RUNTIME` in this CI.

## Release gate

The v0.26 gate requires:

- the v0.25 clinical-programming release gate to have passed;
- four public source inputs and their required schemas;
- all four controlled SAS source programs and required semantics;
- four analysis datasets, their required variables and unique keys;
- a generated Data Definition Table;
- a well-formed Define-XML-shaped candidate;
- complete external SAS reconciliation and Pinnacle 21 handoff contracts;
- absence of fake external SAS outputs in CI;
- explicit non-production/non-submission evidence boundaries.

A successful run issues:

```text
PORTFOLIO_BMS_STATISTICAL_PROGRAMMING_EVIDENCE_READY
```

## Evidence boundary

This is independent public-data portfolio evidence only: no sponsor/CRO
employment claim, no executed SAS output in this CI, no Pinnacle 21 execution,
no formal ADaM conformance, no validated GxP environment, and not
submission-ready.

The purpose is to provide concrete, reviewable statistical-programming evidence
for SAS source, derived datasets, TFLs, metadata and validation handoff while
keeping each execution and regulatory claim at the level actually demonstrated.

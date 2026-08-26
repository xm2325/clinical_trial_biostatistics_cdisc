# v0.26 / v0.26.1 — BMS statistical-programming evidence

## Objective

v0.26 is a role-driven upgrade for Senior Statistical Programmer vacancies such
as Bristol Myers Squibb. It does **not** add another statistical model. Instead,
it strengthens evidence around source data, analysis-dataset programming, TFL
production, QC, metadata and submission handoff. v0.26.1 adds a separately
controlled **real SAS execution and reconciliation** layer after the original
v0.26 source-review/metadata gate.

The controlled path is:

```text
public SDTM/source data
  -> controlled Python/R reference workflow
  -> reviewable SAS analysis-dataset and TFL source
  -> credential-free static semantic/QC gate
  -> trusted GitHub Actions SAS ODA workflow
       -> SASPy Remote IOM
       -> SAS OnDemand for Academics
       -> execute SAS programs
       -> return SAS datasets / ODS results
       -> reconcile against Python/R references
  -> analysis Data Definition Table
  -> Define-XML 2.1-shaped portfolio candidate
  -> Pinnacle 21 handoff contract (not executed)
  -> SHA256 evidence
```

## Why this is different from v0.25

v0.25 proved a controlled clinical-programming release path across seven
representative packages. v0.26 adds BMS-focused SAS source, metadata and
validation handoff evidence. v0.26.1 then answers the stronger execution
question: **can the portfolio execute representative SAS analysis-dataset and
TFL/statistical programs in a real SAS runtime and reconcile the resulting
outputs against independently generated Python/R evidence?**

## SAS source evidence

The controlled source layer contains:

- `sas/macros/qc_contract.sas` — fail-fast required-variable checks;
- `sas/derive_adsl_adae.sas` — ADSL-style and ADAE-style derivation translation
  from public DM/EX/DS/AE sources;
- `sas/teae_risk_difference.sas` — subject-level any-TEAE risk-difference TFL
  using `PROC FREQ` and Fisher exact testing;
- `sas/actot_mmrm_primary.sas` — ACTOT longitudinal MMRM using `PROC MIXED`,
  REML, unstructured within-subject covariance and Satterthwaite denominator
  degrees of freedom.

The original v0.26 credential-free gate continues to statically verify required
SAS semantic fragments, translation-basis files, analysis-dataset contracts and
explicit evidence boundaries. That gate deliberately does not depend on SAS
credentials and does not promote static source review into runtime evidence.

## Trusted SAS OnDemand execution

A separate trusted-push workflow (`.github/workflows/sas_oda_validation.yml`)
uses repository secrets plus an encrypted SAS ODA client bundle. On the
GitHub-hosted runner it installs the required client JARs ephemerally, configures
SASPy Remote IOM, opens a SAS OnDemand for Academics session, executes the SAS
programs, returns SAS datasets/ODS tables to the runner and performs
machine-readable reconciliation.

The workflow is intentionally separate from the public pull-request workflow:
untrusted fork PRs do not receive ODA credentials. The presence of a `.sas`
file or a static SAS check is therefore never represented as executed SAS.

### Final executed evidence

Trusted-push Actions **run #6 / run 32913069051** completed **SUCCESS** on exact
head `f09f403eafff23dcbaa7e2168245aba0310f4cc2`.

The generated `sas_oda_validation_metrics.json` reports:

- SAS runtime executed: **true**;
- runtime: **SAS OnDemand for Academics via SASPy Remote IOM**;
- SAS analysis-dataset programs executed: **1**;
- SAS TFL/statistical programs executed: **2**;
- ADSL rows: **306**;
- ADAE rows: **1,191**;
- TEAE subject rows: **254**;
- MMRM analysis rows: **451**;
- MMRM ODS `Diffs` rows: **36**;
- required reconciliation checks: **45/45 PASS**;
- controlled claim: `PORTFOLIO_SAS_ODA_EXECUTION_RECONCILED`.

Artifact: `sas-oda-validation-32913069051`, ID **9587271667**, digest
`sha256:c9f59a22613992285612237ccf007673f8f97feede4eacf743ccb3f1713518d7`.

The standard credential-free PR workflow independently passed Actions **#749 /
run 32913073831** on the same code head before the documentation-only release
update.

## Reconciliation detail

### ADSL / ADAE

The SAS-created ADSL-style dataset reconciles **306/306** subject keys and the
controlled treatment, population, treatment-date and exposure-derived fields
against the Python reference. Numeric derivations including `TRTDURN`, `EXN`,
`EXDOSE_MAX` and `EXDOSE_MEAN` have zero mismatches at the declared tolerance.

The SAS-created ADAE-style dataset reconciles **1,191/1,191**
`STUDYID/USUBJID/AESEQ` keys and controlled treatment, safety, treatment-emergent,
relatedness, severity and analysis-date/day fields against the Python reference.
Cross-language transport representations such as integral numeric keys are
canonicalised for comparison; this does not alter the underlying SAS program or
statistical tolerance.

### TEAE `PROC FREQ`

The SAS workflow builds the subject-level any-TEAE population and retains the
`PROC FREQ` ODS risk-difference and Fisher outputs for both active-versus-placebo
comparisons. The reconciled results include:

- Low Dose: 96 active / 86 placebo; risks **0.8750 / 0.7558**; risk difference
  **0.1192**; Fisher p **0.053041**;
- High Dose: 72 active / 86 placebo; risks **0.9444 / 0.7558**; risk difference
  **0.1886**; Fisher p **0.001726**.

These remain descriptive portfolio safety outputs; this layer does not promote
them into a benefit-risk or regulatory conclusion.

### `PROC MIXED` MMRM

The SAS MMRM analysis dataset reconciles **451/451** subject/visit rows against
the R reference. The SAS `PROC MIXED` and R `mmrm` implementations use the same
observed-data model definition. The predeclared absolute estimate/SE tolerance
remains **0.0005** and was not loosened after seeing the results.

At Week 24:

- Low Dose vs Placebo: SAS estimate **-1.6131269**, SE **1.16773847**; reference
  estimate **-1.6131495**, SE **1.16778993**; absolute differences about
  **2.26e-05 / 5.15e-05**;
- High Dose vs Placebo: SAS estimate **-0.927148074**, SE **1.15112604**;
  reference estimate **-0.92713794**, SE **1.15117695**; absolute differences
  about **1.01e-05 / 5.09e-05**.

Both pass the fixed **0.0005** reconciliation tolerance.

## Metadata and submission handoff

The original v0.26 gate builds two review artefacts from the controlled live
datasets:

1. `analysis_data_definition_table_v0_26.csv` — dataset/variable inventory,
   order, data type, key status, contract-required status and missingness;
2. `define_xml_candidate_v0_26.xml` — a well-formed portfolio metadata candidate
   shaped around ODM/Define-XML 2.1 concepts for ADSL-style, ADAE-style,
   ADQS-style and ADTTE-style datasets.

The XML artefact remains a **portfolio candidate**, not a validated Define-XML
submission file and not evidence of formal ADaM conformance.

`outputs/pinnacle21_handoff_v0_26.csv` records the four dataset/metadata packages
that would be supplied to an authorised Pinnacle 21 environment. Pinnacle 21
has **not** been executed; its controlled status remains
`NOT_EXECUTED_NO_PINNACLE21_RUNTIME`.

## Two complementary gates

The credential-free v0.26 release gate still issues:

```text
PORTFOLIO_BMS_STATISTICAL_PROGRAMMING_EVIDENCE_READY
```

only after the source/metadata/contracts checks pass. The trusted SAS ODA
execution workflow separately issues:

```text
PORTFOLIO_SAS_ODA_EXECUTION_RECONCILED
```

only after a real SAS session has executed and every required reconciliation
check passes. Keeping the claims separate prevents static evidence, runtime
evidence and submission-validation evidence from being conflated.

## Evidence boundary

This is independent public-data portfolio evidence. SAS **was executed** in SAS
OnDemand for Academics from a GitHub-hosted runner for the bounded v0.26.1
reconciliation workflow. This is not sponsor/CRO employment or production SAS,
not a validated GxP environment, not formal second-programmer sign-off, not
formal ADaM conformance, not a validated Define-XML submission artefact, and not
a regulatory submission package. Pinnacle 21 execution is not claimed.

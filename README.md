# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible public-data work sample for clinical-trial biostatistics and statistical programming. The repository combines study-design QC, source-to-analysis derivation, safety/efficacy analyses, longitudinal modelling, estimands, missing-data sensitivity, survival analysis, machine-readable analysis metadata, official exchange-schema validation, executable QC, statistical change control and SAP-to-TLF traceability.

> **Evidence boundary:** this is independent portfolio work using public CDISC/pharmaverse test data. `*-style` datasets are not claimed to be submission-ready or formally ADaM-conformant. The repository does not claim sponsor/CRO production, SAS production, regulatory submission experience, validated production programming, formal independent second-programmer validation, formal Define-XML conformance, or a successful ADaMIG CORE conformance run when the pinned official ruleset is unavailable.

## Current milestone: v0.19 — official standards integration without false conformance claims

v0.19 extends the validated v0.18 analysis-metadata layer in two distinct ways:

1. generate four **CDISC Dataset-JSON 1.1** exchange files and validate them against the pinned official schema;
2. pin the official **CDISC CORE** engine, a populated official cache snapshot and `cdisc-open-rules`, then distinguish executable ADaMIG rule validation from official-rule unavailability.

The clean-runner evidence verifies:

- Dataset-JSON datasets: **4**;
- variables: **85**;
- exchanged records: **2,569**;
- JSON null values preserved: **1,675**;
- official Dataset-JSON schema errors: **0**;
- CORE CSV transport: **4 datasets / 85 variables**, using `Char` / `Num` declared types;
- populated CORE cache inventory: **981** unique CORE IDs;
- literal rule IDs in `rules_dictionary.pkl` and `rules.pkl`: **981 / 981**, with **981/981 overlap**;
- requested cache key `adamig/1-3`: **present**;
- rule IDs returned for `adamig/1-3`: **0**;
- pinned `cdisc-open-rules` source: **191** `Unpublished/ADAMIG` YAML files plus **1** published rule explicitly referencing ADaMIG;
- current controlled CORE state: **`NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE`**;
- executable ADaMIG CORE validation performed: **false**;
- conformance claim: **`NOT_ASSESSED`**.

A zero-rule result is deliberately **not** reported as zero issues, validation success or formal conformance. If a future pinned official cache exposes non-zero ADaMIG rules, the same CI path automatically switches to strict executable validation and requires at least one executed rule with no CORE `EXECUTION ERROR`.

See `docs/cdisc_standards_validation.md` for the full provenance, state machine and evidence boundary.

## Controlled evidence chain

```text
public CDISC / pharmaverse test data
  -> protocol-design + sample-size QC
  -> randomisation / initial-kit QC
  -> source-to-analysis derivation + Python/R QC
  -> ADSL-/ADAE-/ADQS-/ADTTE-style analysis datasets
  -> exact 85-variable metadata + source/derivation lineage
  -> Define-XML-inspired metadata export + reparse QC
  -> Dataset-JSON 1.1 exchange + official-schema validation
  -> CORE CSV transport
  -> pinned CORE cache/rule-availability audit
       -> executable CORE triage when rules exist
       -> controlled NOT_AVAILABLE evidence when they do not

  -> primary observed-data ACTOT MMRM (mmrm)
  -> independent ACTOT row reconstruction + nlme cross-package validation
  -> Week 24 Bonferroni family-wise decision layer
  -> estimand + missingness review
  -> fixed-delta diagnostics
  -> subject-level MAR/delta MI + MCSE QC
  -> reference-based MAR/JR/CR/CIR MI + MCSE QC
  -> randomized-arm ADTTE-style TTDISC derivation
  -> Kaplan–Meier + exploratory log-rank/Cox retention analysis

  -> analysis-dataset/TLF reviewer
  -> layered CR-001–CR-013 statistical change-impact assessment
  -> T01–T25 executable structural traceability
```

Standards/metadata governance remains separate from the TLF registry. v0.19 does **not** invent a T26; the statistical output registry remains **T01–T25 at version 0.17.0** because no new statistical table/listing/figure is added.

## Public CDISC/reference evidence

The CI workflow downloads pinned public efficacy inputs. Key references include:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects and 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with exact selected `QSSEQ`/`DTYPE`; `AVAL` agreement is **695/705**, and all ten differences remain visible with source-row traceability. For selected ACTOT (`ANL01FL=Y`), **1,016/1,016** analysis keys have exact selected `QSSEQ`/`DTYPE` agreement.

## Analysis metadata and lineage

The controlled metadata layer covers:

```text
outputs/adsl_style.csv
outputs/adae_style.csv
outputs/adqs_actot_style.csv
outputs/adtte_retention_style.csv
```

Validated evidence:

- **4** analysis datasets;
- **85/85 variables (100%)** exact metadata-to-generated-column coverage;
- **110** declared source references;
- **39/39** cross-analysis-dataset lineage references resolved;
- **52 derived** and **33 predecessor** variables;
- labels, data types, roles, origin type, source references, derivation text and key status for every covered variable;
- reparsable Define-XML-inspired export with **4 dataset / 85 variable definitions**;
- Define-XML reference package **2.1.11**, with `conformance=NOT_ASSESSED` locked in configuration and output.

The XML is intentionally named `define_xml_like_metadata.xml`; it is metadata-modelling evidence, not an ODM/Define-XML submission package.

## Primary ACTOT MMRM and distinct-package validation

The primary longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit: `mmrm::mmrm`, REML, unstructured covariance, Satterthwaite degrees of freedom. A separate same-author validation program independently reconstructs ACTOT analysis rows and refits the fixed-effects model with `nlme::gls` plus `corSymm + varIdent`.

Validated cross-package evidence:

- **451/451** primary/independent rows;
- **189/189** subjects;
- zero missing/extra keys;
- zero exact-field or numeric row mismatches;
- **18/18** blocking validation checks;
- max Week 24 estimate absolute difference **1.30015e-05**;
- max model-based SE absolute difference **2.63230e-06**;
- locked estimate/SE tolerance **0.0005**.

Week 24 primary contrasts:

| Contrast | Estimate | SE | 95% CI | Raw p |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

Degrees of freedom and p-values are not compared across packages because the `nlme` reconstruction validates population, point estimates and model-based SEs rather than reproducing package-specific Satterthwaite inference.

## Multiplicity, estimand and missing-data sensitivity

The controlled Week 24 ACTOT family contains two active-versus-placebo hypotheses. Family-wise alpha is **0.05** and Bonferroni local alpha is **0.025**. Raw p-values **0.169334 / 0.421970** become adjusted p-values **0.338669 / 0.843940**, so **0/2** hypotheses are rejected.

Sensitivity evidence includes:

- machine-readable ACTOT estimand and arm-by-visit missingness review;
- deterministic fixed-delta and directional tipping diagnostics (T18/T19);
- subject-level approximate-Bayesian `rbmi` MAR/delta MI with **200 imputations** and separate MCSE QC (T20/T21);
- reference-based MAR/JR/CR/CIR MI with discontinuation timing audit and MCSE QC (T22).

The reference-based layer passes **27/27** required checks; maximum `MCSE(estimate) / pooled SE` is **5.381%** against a 7.5% threshold.

## Randomized-arm ADTTE / survival evidence

A material public-data assignment issue is retained rather than hidden: **12/254 randomized subjects have `TRT01P != TRT01A`**. Exploratory retention therefore uses planned randomized assignment:

```text
ANLTRT = TRT01P
```

`TRT01A` remains context and `TRTDIFFL` audits the mismatch.

Validated TTDISC evidence:

- randomized arms: Placebo **86**, Low Dose **84**, High Dose **84**;
- study-discontinuation events **144**; completion censors **110**;
- **16/16** derivation checks;
- **14/14** R survival checks;
- Day-182 KM retention: **67.44% / 29.76% / 33.25%**;
- Low vs Placebo discontinuation HR **3.0852**;
- High vs Placebo discontinuation HR **2.9246**;
- `cox.zph` p-values **0.8310 / 0.7577**.

HR > 1 means higher **study-discontinuation hazard**, not worse efficacy. T24/T25 are exploratory and remain outside the ACTOT confirmatory family.

## v0.19 statistical change control

The change-control graph is layered rather than rewriting earlier validated specifications:

```text
v0.15 -> multiplicity
v0.16 -> cross-package MMRM validation
v0.17 -> randomized-retention TTE / T24–T25
v0.18 -> analysis metadata / lineage / Define-XML-inspired export
v0.19 -> Dataset-JSON + CORE standards-validation governance
```

`CR-013 — Official CDISC standards-engine or rule-availability change` propagates through:

```text
standards_validation_configuration
  -> dataset_json_exchange_validation
  -> core_rule_availability_audit
       -> core_validation_evidence_state
```

CR-013 reviews the four exchanged analysis datasets, Dataset-JSON artifacts/QC, CORE cache/rule-discovery evidence, the executed-versus-NOT_AVAILABLE state, documentation and the v0.19 standards spec. It has **0 impacted TLFs** and does not propagate into MMRM, multiplicity, missing-data sensitivity or retention-survival families.

This is portfolio change-control simulation, not a sponsor-approved protocol/SAP change process.

## Executable TLF traceability

The statistical output registry remains **T01–T25 at version 0.17.0**. The workflow requires:

- outputs found: **25/25**;
- output contracts: **25/25**;
- analysis-dataset links: **25/25**;
- QC-evidence links: **25/25**;
- complete validated TLFs: **25/25**.

## Key v0.19 files

```text
spec/standards_validation_v0_19.json                  pinned official standards evidence contract
src/cdisc_portfolio/dataset_json.py                  Dataset-JSON + CORE transport generation
src/cdisc_portfolio/core_cache.py                    safe cache/rule-availability audit
src/cdisc_portfolio/core_validation.py               executable / NOT_AVAILABLE evidence state
scripts/run_dataset_json.py                           official-schema gate
scripts/run_core_cache_audit.py                       CORE cache/rule discovery gate
scripts/run_core_validation.py                        strict executable-rule triage
scripts/run_core_unavailable.py                       controlled no-execution evidence path

docs/cdisc_standards_validation.md                   provenance, metrics and evidence boundary
src/cdisc_portfolio/change_control_v019.py            layered v0.19 change-control merger
spec/change_impact_graph_v0_19_extension.json         standards dependency extension
spec/change_requests_v0_19_extension.json             CR-013

R/mmrm_analysis.R                                     primary ACTOT MMRM
R/mmrm_cross_package_qc.R                             independent rows + nlme MMRM
R/tte_retention_analysis.R                            KM/log-rank/Cox retention
R/rbmi_reference_based.R                              MAR/JR/CR/CIR sensitivity
spec/analysis_traceability.csv                        T01–T25 registry
spec/output_contracts.json                            executable TLF contracts
```

## Reproduce

The full GitHub Actions workflow pins and downloads the external standards repositories. Core local analysis commands include:

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_tte_retention.py
python scripts/run_metadata_lineage.py
python scripts/run_dataset_json.py
python scripts/run_protocol_design.py
python scripts/run_randomisation.py

Rscript R/independent_qc.R
Rscript R/mmrm_analysis.R
Rscript R/mmrm_cross_package_qc.R
python scripts/run_mmrm_cross_validation.py
Rscript R/tte_retention_analysis.R
python scripts/run_multiplicity.py
python scripts/run_estimand_review.py
python scripts/run_mnar_sensitivity.py
Rscript R/rbmi_sensitivity.R
Rscript R/rbmi_mcse_qc.R
Rscript R/rbmi_reference_based.R
python scripts/run_dataset_review.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
```

Generated evidence is written under `outputs/`; GitHub Actions uploads the complete output directory so statistical, metadata, standards, lineage and governance evidence can be inspected from the same clean run.

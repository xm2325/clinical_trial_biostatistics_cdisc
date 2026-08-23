# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible public-data work sample for clinical-trial biostatistics and statistical programming. The repository combines source-to-analysis derivation, safety/efficacy analyses, longitudinal modelling, missing-data sensitivity, survival analysis, executable QC, statistical change control and machine-readable analysis metadata.

> **Evidence boundary:** this is independent portfolio work using public CDISC/pharmaverse test data. `*-style` datasets are not claimed to be submission-ready or formally ADaM-conformant. The repository does not claim sponsor/CRO production, SAS production, regulatory submission experience, validated production programming, formal independent second-programmer validation, or formal Define-XML conformance.

## Current milestone: v0.18 — analysis metadata and lineage

v0.18 closes a statistical-programming gap that was not addressed by the earlier modelling stages: **variable-level analysis metadata, source/derivation lineage and deterministic metadata export**.

The controlled evidence now covers four generated analysis datasets:

- `outputs/adsl_style.csv`;
- `outputs/adae_style.csv`;
- `outputs/adqs_actot_style.csv`;
- `outputs/adtte_retention_style.csv`.

The validated live workflow verifies:

- **4** analysis-dataset metadata definitions;
- **85/85 variables (100%)** with exact metadata-to-generated-column coverage;
- **110** declared source references;
- **39/39** cross-analysis-dataset lineage references resolved;
- **52 derived** and **33 predecessor** variables;
- labels, data types, roles, origin type, source references, derivation text and key status for every covered variable;
- a reparsable Define-XML-inspired XML export containing **4 DatasetDef** and **85 ItemDef-style variable definitions**;
- XML dataset/variable counts exactly matching the validated metadata catalog;
- Define-XML reference package **2.1.11** with `conformance=NOT_ASSESSED` locked in both configuration and XML;
- **146 Python unit tests** passed in the first complete v0.18 live validation, including negative controls for missing/stale metadata, unresolved lineage, blank derivations and attempted conformance overclaiming.

The generated XML is deliberately called `define_xml_like_metadata.xml`: it is evidence that the project can model and validate analysis metadata, **not** a claim that the file is an ODM/Define-XML submission package or has passed official schema/conformance validation.

## Controlled evidence chain

```text
public CDISC / pharmaverse test data
  -> source-to-analysis derivation + Python/R QC
  -> ADSL-/ADAE-/ADQS-/ADTTE-style analysis datasets
  -> v0.18 exact variable-level metadata + source/derivation lineage
  -> deterministic Define-XML-inspired metadata export + reparse QC

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
  -> v0.18 layered statistical change-impact assessment
  -> T01–T25 executable structural traceability
```

Metadata evidence is intentionally separate from the TLF registry. v0.18 does **not** invent a `T26`; the existing output registry remains **T01–T25 at registry version 0.17.0** because no statistical TLF was added.

## v0.18 metadata and lineage gate

`src/cdisc_portfolio/metadata_lineage.py` builds and validates the controlled metadata catalog. `scripts/run_metadata_lineage.py` runs after the public derivation and ADTTE derivation so it checks the actual generated CSV schemas rather than fixtures alone.

Blocking rules require:

- every generated column has exactly one metadata definition;
- no stale extra metadata variables are permitted;
- dataset key definitions agree exactly with variable key flags;
- every variable has a non-empty label and at least one source reference;
- every derived variable has explicit derivation text;
- `DOMAIN.VARIABLE` lineage syntax is valid;
- references to upstream analysis datasets resolve to real variables in the same controlled catalog;
- unknown source domains fail;
- the XML export reparses successfully;
- XML dataset/variable counts equal the validated catalog counts;
- configuration must remain `conformance=NOT_ASSESSED`.

Machine-readable evidence is generated as:

```text
outputs/adam_variable_metadata.json
outputs/metadata_lineage_validation.csv
outputs/metadata_lineage_metrics.json
outputs/metadata_lineage_summary.md
outputs/define_xml_like_metadata.xml
```

The first complete live artifact produced XML SHA256:

```text
32e378b57d85e548ac2513de0d2ec7cef678873615648e480a6d413587cc4b39
```

See `docs/adam_metadata_lineage.md` for the detailed design and evidence boundary.

## Public CDISC/reference evidence

The CI workflow downloads pinned public efficacy inputs. Key references include:

- official `QS` Dataset-JSON: **121,749 rows**;
- official `ADQSCIBC` reference: **730 rows**;
- official `ADQSADAS` reference: **12,463 rows**, 254 subjects and 15 parameters.

The portfolio reconstructs **705/705** selected CIBIC analysis keys with exact selected `QSSEQ`/`DTYPE`; `AVAL` agreement is 695/705, and all ten differences remain visible with source-row traceability. For selected ACTOT (`ANL01FL=Y`), **1,016/1,016** analysis keys have exact selected `QSSEQ`/`DTYPE` agreement.

## Primary ACTOT MMRM and distinct-package validation

The primary longitudinal model uses observed Week 8, Week 16 and Week 24 ACTOT change from baseline:

```text
CHG ~ treatment * visit + BASE * visit
```

Primary fit: `mmrm::mmrm`, REML, unstructured covariance, Satterthwaite degrees of freedom. The same-author validation program independently reconstructs the ACTOT analysis rows and refits the fixed-effects model with `nlme::gls` plus `corSymm + varIdent`.

Validated cross-package evidence:

- **451/451** primary/independent rows;
- **189/189** subjects;
- zero missing/extra keys;
- zero exact-field or numeric row mismatches;
- **18/18** blocking validation checks passed;
- max Week 24 estimate absolute difference **1.30015e-05**;
- max model-based SE absolute difference **2.63230e-06**;
- locked estimate/SE tolerances **0.0005**.

Week 24 primary contrasts remain:

| Contrast | Estimate | SE | 95% CI | Raw p |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.6131 | 1.1678 | [-3.9216, 0.6953] | 0.1693 |
| High Dose vs Placebo | -0.9271 | 1.1512 | [-3.2032, 1.3489] | 0.4220 |

Degrees of freedom and p-values are not compared across packages because the independent `nlme` reconstruction is used to validate population, point estimates and model-based SEs rather than reproduce package-specific Satterthwaite inference.

## Multiplicity and missing-data sensitivity

The controlled Week 24 ACTOT family contains two active-versus-placebo hypotheses. Family-wise alpha is **0.05**; Bonferroni local alpha is **0.025**. Raw p-values 0.169334 and 0.421970 become adjusted p-values 0.338669 and 0.843940, so **0/2** hypotheses are rejected.

Sensitivity evidence includes:

- deterministic fixed-delta and directional tipping diagnostics (T18/T19);
- subject-level approximate-Bayesian `rbmi` MAR/delta MI with **200 imputations** and independent MCSE QC (T20/T21);
- reference-based MAR/JR/CR/CIR MI with discontinuation timing audit and MCSE QC (T22).

The reference-based layer passes **27/27** required checks; maximum `MCSE(estimate) / pooled SE` is **5.381%** against a 7.5% threshold.

## Randomized-arm ADTTE/survival evidence

v0.17 identified a material assignment issue in the public data: **12/254 randomized subjects have `TRT01P != TRT01A`**. The exploratory retention comparison therefore uses planned randomized assignment:

```text
ANLTRT = TRT01P
```

`TRT01A` remains context and `TRTDIFFL` audits the mismatch.

Validated TTDISC evidence:

- randomized arms: Placebo **86**, Low Dose **84**, High Dose **84**;
- study-discontinuation events **144**; completion censors **110**;
- **16/16** ADTTE-style derivation checks passed;
- **14/14** R survival checks passed;
- Day-182 KM retention: **67.44% / 29.76% / 33.25%** for Placebo / Low / High;
- Low vs Placebo discontinuation HR **3.0852**;
- High vs Placebo discontinuation HR **2.9246**;
- `cox.zph` p-values **0.8310 / 0.7577**, giving **0/2** PH diagnostic signals at alpha 0.05.

HR > 1 means higher **study-discontinuation hazard**, not worse efficacy. T24/T25 are exploratory and remain outside the ACTOT confirmatory family.

## v0.18 statistical change control

The change-control graph remains layered rather than rewriting previously validated specifications:

```text
v0.15 -> multiplicity
v0.16 -> cross-package MMRM validation
v0.17 -> randomized-retention TTE / T24–T25
v0.18 -> analysis metadata definition / lineage QC / Define-XML-inspired export
```

The validated v0.18 assessment covers:

- **12** simulated change requests (`CR-001`–`CR-012`);
- **80** propagated component links;
- **279/279** graph-required impact relationships declared;
- **279/279** required resources resolved;
- **0** missing required declarations;
- **0** extra declared resources;
- **0** unresolved required resources.

`CR-012` propagates through exactly three metadata components and requires **12** review relationships. It has **0 impacted TLFs** and does not propagate into MMRM, multiplicity or survival families.

This remains portfolio change-control simulation, not a sponsor-approved protocol/SAP change process.

## Executable TLF traceability

The statistical output registry remains **T01–T25 at version 0.17.0**. The same v0.18 live run still passes:

- outputs found: **25/25**;
- output contracts: **25/25**;
- analysis-dataset links: **25/25**;
- QC-evidence links: **25/25**;
- complete validated TLFs: **25/25**.

Keeping the registry version unchanged is deliberate: v0.18 adds metadata governance, not another statistical table/listing/figure.

## Key files

```text
src/cdisc_portfolio/metadata_lineage.py             v0.18 variable metadata + lineage + XML export
scripts/run_metadata_lineage.py                      v0.18 blocking metadata gate
spec/adam_metadata_config.json                       Define-XML reference + evidence boundary
src/cdisc_portfolio/change_control_v018.py           layered v0.18 change-control merger
spec/change_impact_graph_v0_18_extension.json        metadata dependency extension
spec/change_requests_v0_18_extension.json            CR-012

docs/adam_metadata_lineage.md                        metadata/lineage design and boundary
R/mmrm_analysis.R                                    primary ACTOT MMRM
R/mmrm_cross_package_qc.R                            independent rows + nlme MMRM
R/tte_retention_analysis.R                           KM/log-rank/Cox retention analysis
R/rbmi_reference_based.R                             MAR/JR/CR/CIR sensitivity
src/cdisc_portfolio/tte.py                           ADTTE-style derivation/QC
spec/analysis_traceability.csv                       T01–T25 registry
spec/output_contracts.json                           executable TLF contracts
```

## Reproduce

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/profile_official_references.py
python scripts/run_all.py
python scripts/run_tte_retention.py
python scripts/run_metadata_lineage.py
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

Generated evidence is written under `outputs/`; GitHub Actions uploads the complete output directory so statistical, metadata, lineage and governance evidence can be inspected from the same run.

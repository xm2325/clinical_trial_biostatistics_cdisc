# Clinical Trial Biostatistics & CDISC Portfolio

A reproducible public-data work sample for clinical-trial biostatistics and statistical programming. The repository combines study-design QC, source-to-analysis derivation, safety/efficacy analyses, longitudinal modelling, estimands, missing-data sensitivity, survival analysis, machine-readable analysis metadata, official exchange-schema validation, executable QC, statistical change control, SAP-to-TLF traceability, study-statistician analysis readiness, controlled CSR-style statistical interpretation and machine-validated statistical reviewer responses.

> **Evidence boundary:** this is independent portfolio work using public CDISC/pharmaverse test data. `*-style` datasets are not claimed to be submission-ready or formally ADaM-conformant. The repository does not claim sponsor/CRO production, SAS production, regulatory submission experience, validated production programming, formal independent second-programmer validation, formal Define-XML conformance, sponsor database lock, formal blinded data review, sponsor/CRO sign-off, sponsor CSR approval, health-authority correspondence, benefit-risk approval, or a successful ADaMIG CORE conformance run when the pinned official ruleset is unavailable.

## Current milestone: v0.23 — randomised-assignment consistency repair and population provenance

v0.23 is a **repair**, not a new efficacy model. A subject-level audit found that **12/254 randomised subjects** have `TRT01P != TRT01A`, all planned High Dose -> actual Low Dose. Those 12 subjects contribute no observed Week 8/16/24 ACTOT rows to the primary MMRM, but they do belong to the 254-subject missing-data target and therefore affect imputation-group assignment.

The previous T20/T21/T22 sensitivity path grouped that target by actual treatment (`TRT01A`), giving Placebo / Low / High **86 / 96 / 72** and pairwise MI targets **182 / 158**. v0.23 aligns efficacy missing-data sensitivity with the randomised treatment condition by using planned assignment (`TRT01P`) for MI grouping while retaining actual treatment as explicit context. The corrected randomised allocation is **86 / 84 / 84**, giving **170 / 170** Low-vs-Placebo and High-vs-Placebo targets.

The repair is deliberately bounded:

```text
original ADSL-/ADQS-style files with actual-treatment provenance
  -> planned/actual subject-level audit
  -> planned-assignment MI input copies
  -> hard guard for mismatch subjects in observed primary MMRM
  -> T20/T21 subject-level MAR/delta MI + MCSE
  -> T22 MAR/JR/CR/CIR reference-based MI + MCSE
  -> executed-target audit
  -> byte-for-byte restore of original analysis inputs
```

Governance-inclusive clean validation Actions **#689 / run 32851464310** on head `bee4e338099d2a769037ec9f4190308a0c350de2` passed the complete Python/R/CDISC/MMRM/MI/readiness/change-control/traceability/closure/reviewer-response workflow. It verified:

- subjects / randomised / baseline-ACTOT target: **306 / 254 / 254**;
- planned randomised allocation: **86 / 84 / 84**;
- actual-treatment allocation among randomised subjects: **86 / 96 / 72**;
- planned-versus-actual mismatches: **12**;
- mismatch subjects in observed primary MMRM: **0**;
- primary MMRM subjects: **189**;
- randomised baseline subjects with no observed post-baseline ACTOT: **65**;
- Week 24 observed / missing: **116 / 138**;
- corrected executed MI pair targets: **170 / 170**;
- pre-MI assignment checks: **10/10 PASS**;
- post-MI execution/restore checks: **4/4 PASS**;
- reference-based MAR/JR/CR/CIR rows: **8/8**, with **8/8 MCSE passes**;
- controlled assignment claim: **`PORTFOLIO_RANDOMISED_ASSIGNMENT_CONSISTENCY_READY`**;
- active change control: **CR-001–CR-015**, **94** propagated links and **333/333** required impacts, with **0 missing / 0 extra / 0 unresolved**;
- CR-015 propagates through **6** components and **22** required impacts to **T20/T21/T22**.

Corrected Week 24 MAR estimates are approximately **-1.5397** for Low Dose versus Placebo and **-0.7237** for High Dose versus Placebo. The primary Bonferroni family remains **0/2 rejected** with adjusted p-values **0.338669 / 0.843940**, so the repair does not opportunistically change the controlled conclusion: no confirmatory efficacy-success claim is supported, and MI remains supportive sensitivity evidence.

The #689 artifact is `clinical-biostatistics-cdisc-outputs`, ID **9564651055**, digest `sha256:106abf356e19437e2f60cfdb4fc5b0fca55db712e45270c6b1865ac9780f2623`.

See `docs/mi_randomised_assignment_repair_v0_23.md` for the repair rationale, controlled boundary and evidence.

## v0.22 baseline retained under v0.23 — statistical review query and decision provenance

v0.22 adds a post-interpretation Study Statistician reviewer-response layer. It does **not** add another model, estimand, analysis population, TLF or pre-closure change request. Instead, it makes difficult review questions reproducible by forcing every answer to resolve to current statistical evidence, a bounded decision status and a permitted claim:

```text
validated analysis / TLF / QC evidence
  -> v0.20 analysis readiness + evidence closure
  -> v0.21 controlled statistical interpretation
  -> v0.22 statistical reviewer responses
       -> SRQ-001 primary efficacy decision
       -> SRQ-002 missing-data robustness context
       -> SRQ-003 treatment-assignment mismatch handling
       -> SRQ-004 descriptive safety boundary
       -> SRQ-005 exploratory retention boundary
```

First full live implementation run Actions **#651 / run 32774536503** on head `a130bc12f591fcccc989242148698edfd490bc52` completed the entire Python/R/CDISC/MMRM/MI/readiness/closure workflow plus the reviewer-response gate. The live v0.22 evidence was:

- controlled reviewer queries: **5/5**;
- reviewer-response checks: **10/10 PASS**;
- Week 24 primary family-wise rejections: **0/2**;
- adjusted primary p-values: **0.338669 / 0.843940**;
- Week 24 ACTOT observed / missing: **116 / 138** of **254 randomized**, or **54.3% missing**;
- reference-based MAR/JR/CR/CIR evidence: **8/8 expected rows** with **8/8 MCSE passes**;
- fixed-delta reviewer context: **2/2 comparisons**, with directional tipping at **1.5621 / 1.0333 ACTOT points** for Low / High versus Placebo;
- planned-versus-actual treatment mismatches: **12** and reconciled directly to ADTTE-style data;
- descriptive safety response rows: **2/2**, with TEAE risk differences **0.1192 to 0.1886**;
- exploratory retention response rows: **2/2**, with discontinuation HRs **3.0852 / 2.9246**;
- controlled review-response claim: **`PORTFOLIO_STATISTICAL_REVIEW_RESPONSE_READY`**.

The first-live-run artifact was `clinical-biostatistics-cdisc-outputs`, ID **9537615679**, digest `sha256:561e3c8c50c7697a7306e78018280add24ac89f75c750c753810d3c0488b0b63`.

After that live run, v0.22 was hardened further: each primary comparison must contain exactly MAR/JR/CR/CIR reference-based evidence, both primary comparisons must have fixed-delta context, generated overclaim text has no exception path, and additional negative controls block primary decision drift, incomplete MI strategies and missing tipping evidence. The final documentation-inclusive head is revalidated in a separate full clean run before merge.

The five controlled reviewer questions are deliberately decision-focused rather than presentation-only. For example, the missing-data response must report **138/254 Week 24 missingness**, **8/8 MCSE passes** and the two fixed-delta tipping thresholds together; it is not allowed to call the result simply “fully robust”. Likewise, HR > 1 is interpreted as higher **study-discontinuation hazard**, not worse efficacy.

See `docs/statistical_review_query_provenance.md` for the complete v0.22 query contract, blocking checks, negative controls and evidence boundary.

## v0.21 baseline retained under v0.22 — controlled CSR-style statistical interpretation

v0.21 adds a post-closure Study Statistician interpretation layer. It does **not** add another model, estimand, analysis population or TLF. Instead, it makes the interpretation of already validated statistical results executable and testable:

```text
validated analysis / TLF / QC evidence
  -> v0.20 analysis readiness
  -> statistical change control
  -> SAP-to-TLF traceability
  -> v0.20 evidence closure
  -> v0.21 controlled statistical interpretation
       -> primary multiplicity decision
       -> reference-based MI context
       -> fixed-delta directional tipping context
       -> descriptive safety interpretation
       -> exploratory retention interpretation
```

Pre-documentation clean-run Actions **#625 / run 32701384371** on head `2c7186255004b286b483e0564b162dcc1edfad55` verifies:

- base CSR-style interpretation checks: **11/11 PASS**;
- fixed-delta interpretation extension checks: **4/4 PASS**;
- final conclusion-matrix rows: **10**;
- Week 24 primary family-wise rejections: **0/2**;
- primary MMRM-to-multiplicity estimate drift: **0**;
- primary MMRM-to-multiplicity raw-p drift: **0**;
- `reject_familywise` flags consistent with local-alpha and adjusted-p rules: **2/2**;
- reference-based MAR/JR/CR/CIR rows: **8/8 expected**;
- reference-based MCSE passes: **8/8**;
- fixed-delta scenario rows: **6/6 expected** across **3 scenarios / 2 comparisons**;
- earliest directional tipping delta: **1.5621 ACTOT points** for Low Dose versus Placebo and **1.0333 ACTOT points** for High Dose versus Placebo, both under `DIVERGENT_WORSENING`;
- safety comparison rows: **2/2** and retained as descriptive evidence;
- retention comparison rows: **2/2**, with HR > 1 retained as higher study-discontinuation hazard and exploratory evidence;
- prohibited efficacy/regulatory overclaim fragments: **0**.

The controlled primary family has adjusted p-values **0.338669 / 0.843940**, so v0.21 explicitly states that no confirmatory efficacy success conclusion is supported. Reference-based MI retains the same effect sign across MAR/JR/CR/CIR for both comparisons, but this is not presented as complete robustness: the fixed-delta layer also reports where direction changes under stronger MNAR shifts.

The controlled interpretation claim is:

```text
PORTFOLIO_STATISTICAL_INTERPRETATION_READY
```

It means the portfolio interpretation contract and executable checks passed. It does not mean sponsor CSR approval, medical-writing sign-off, regulatory readiness or a benefit-risk decision.

See `docs/csr_statistical_interpretation.md` for the full v0.21 interpretation logic, statistical roles, tipping context and evidence boundary.

## v0.20 baseline retained under v0.22 — study-statistician analysis readiness and evidence closure

v0.20 moved the portfolio from standards plumbing back to study-statistician review work. It did **not** add another statistical model or another TLF. It added a controlled transition from the validated analysis package to a review decision:

```text
analysis data / TLF / metadata / standards evidence
  -> treatment-blind aggregate readiness review
  -> explicit known-issue disposition
  -> pre-closure analysis-readiness gate
  -> statistical change-control impact gate
  -> SAP-to-TLF traceability gate
  -> evidence-closure gate
```

Final v0.20 frozen-head validation was Actions **#607 / run 32695875945** on head `e5f4049f98d3b64a5b8677fe918cd382990f416f`. It verified:

- configured analysis data cutoff: **2015-03-05**;
- subjects / randomized: **306 / 254**;
- randomized subjects with ACTOT baseline: **254/254**;
- Week 24 ACTOT observed / missing: **116 / 138**;
- date values after the configured cutoff: **0**;
- treatment-blind aggregate checks: **5/5 PASS**;
- controlled known issues dispositioned: **3/3**;
- blocking open issues: **0**;
- pre-closure readiness checks: **7/7 PASS**;
- change requests: **CR-001–CR-014**;
- propagated component links: **88**;
- required change-impact relationships/resources: **311/311**;
- missing / extra / unresolved required change impacts: **0 / 0 / 0**;
- TLF output / contract / analysis-data / QC links: **25/25** for each layer;
- evidence-closure checks: **4/4 PASS**;
- closure claim: **`PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE`**.

The three retained issues are not hidden: **12** planned/actual treatment mismatches, **138** randomized subjects without observed Week 24 ACTOT, and **10** selected ADQSCIBC value differences. Their controlled dispositions are count-reconciled on every clean run. A count drift, blank disposition, blocking disposition, date beyond cutoff, failed prerequisite, failed change-control gate or failed traceability gate blocks the appropriate readiness/closure stage.

See `docs/study_statistician_analysis_readiness.md` for the v0.20 review sequence and evidence boundary.

## v0.19 standards evidence retained underneath v0.20

v0.19 added four **CDISC Dataset-JSON 1.1** exchange files plus a pinned official **CDISC CORE** engine/cache/open-rule evidence path. The validated evidence remains:

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

A zero-rule result is deliberately **not** reported as zero issues, validation success or formal conformance. If a future pinned official cache exposes non-zero ADaMIG rules, the same CI path switches to strict executable validation and requires at least one executed rule with no CORE `EXECUTION ERROR`.

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
  -> v0.23 planned-randomisation MI assignment boundary + subject-level audit
  -> subject-level MAR/delta MI + MCSE QC
  -> reference-based MAR/JR/CR/CIR MI + MCSE QC
  -> randomized-arm ADTTE-style TTDISC derivation
  -> Kaplan–Meier + exploratory log-rank/Cox retention analysis

  -> analysis-dataset/TLF reviewer
  -> pre-closure study-statistician readiness review
  -> layered CR-001–CR-015 statistical change-impact assessment
  -> T01–T25 executable structural traceability
  -> portfolio evidence closure
  -> CSR-style interpretation contract + cross-output reconciliation
  -> bounded confirmatory/supportive/descriptive/exploratory conclusions
  -> reviewer question + evidence + decision + allowed-claim provenance
```

Readiness, governance, interpretation and reviewer-response evidence remain separate from the TLF registry. The statistical output registry remains **T01–T25 at version 0.17.0**: v0.23 does not create a T26. Unlike post-closure v0.21/v0.22, v0.23 changes an upstream missing-data sensitivity assignment source, so it is controlled as **CR-015** and explicitly propagates to T20/T21/T22.

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

v0.21 reads both sensitivity families during interpretation. The reference-based strategies retain the same effect sign for both active comparisons, while fixed-delta `DIVERGENT_WORSENING` reaches direction tipping at **1.5621 / 1.0333 ACTOT points** for Low / High. v0.22 then turns that combined evidence into the controlled SRQ-002 reviewer response, so the sensitivity evidence is not reduced to a single “robust/not robust” label.

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

HR > 1 means higher **study-discontinuation hazard**, not worse efficacy. T24/T25 are exploratory and remain outside the ACTOT confirmatory family. v0.21 tests the interpretation and v0.22 requires the same direction/status in the reviewer response rather than relying on prose alone.

## v0.20 statistical change control

The change-control graph is layered rather than rewriting earlier validated specifications:

```text
v0.15 -> multiplicity
v0.16 -> cross-package MMRM validation
v0.17 -> randomized-retention TTE / T24–T25
v0.18 -> analysis metadata / lineage / Define-XML-inspired export
v0.19 -> Dataset-JSON + CORE standards-validation governance
v0.20 -> study-statistician analysis readiness + evidence closure
v0.21 -> post-closure CSR-style interpretation QC
v0.22 -> post-interpretation statistical reviewer-response QC
v0.23 -> randomised-assignment consistency repair for T20–T22
```

`CR-014 — Analysis-readiness definition or known-issue disposition change` propagates through:

```text
analysis_readiness_configuration
  -> blinded_analysis_readiness_review
  -> final_analysis_readiness_review
  -> analysis_evidence_closure
```

CR-014 reviews the v0.20 readiness specification, treatment-blind review artifact, final issue-disposition/readiness evidence and review documentation. It has **0 impacted TLFs** and does not propagate into MMRM, multiplicity, missing-data sensitivity, retention-survival or standards-validation analysis families.

The validated v0.20 change-control result is **14 changes / 88 propagated links / 311 of 311 required impact relationships/resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources.

v0.23 advances the active layered change-control result to **15 changes / 94 propagated links / 333 of 333 required impact relationships/resources**, again with zero missing declarations, zero extra declarations and zero unresolved required resources. **CR-015** controls the randomised-assignment source used by efficacy missing-data sensitivity analyses and propagates to **T20/T21/T22**; the TLF registry itself remains T01–T25.

v0.21 and v0.22 deliberately remain after the pre-closure dependency graph. Interpretation/reviewer-response rules are controlled by their own executable contracts and negative-control tests. This avoids making pre-closure change control depend on evidence generated only after closure.

This is portfolio change-control simulation, not a sponsor-approved protocol/SAP change process.

## Executable TLF traceability

The statistical output registry remains **T01–T25 at version 0.17.0**. The workflow requires:

- outputs found: **25/25**;
- output contracts: **25/25**;
- analysis-dataset links: **25/25**;
- QC-evidence links: **25/25**;
- complete validated TLFs: **25/25**.

## Study-statistician readiness and closure artifacts

Pre-closure readiness writes:

```text
outputs/blinded_analysis_readiness_review.csv
outputs/analysis_readiness_review.csv
outputs/analysis_readiness_metrics.json
outputs/analysis_readiness_summary.md
```

The treatment-blind artifact is blocked from containing the configured treatment-assignment fields/tokens `TRT01P`, `TRT01A` or `ANLTRT`.

After change control and traceability pass, closure writes:

```text
outputs/analysis_closure_review.csv
outputs/analysis_closure_metrics.json
outputs/analysis_closure_summary.md
```

The readiness claim is `PORTFOLIO_ANALYSIS_PACKAGE_READY_FOR_REVIEW`; the closure claim is `PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE`. Tests reject regulatory/submission-ready replacements.

## CSR-style interpretation artifacts

After evidence closure, v0.21 writes:

```text
outputs/csr_conclusion_matrix.csv
outputs/csr_interpretation_checks.csv
outputs/csr_interpretation_metrics.json
outputs/csr_fixed_delta_context.csv
outputs/csr_interpretation_extension_checks.csv
outputs/csr_interpretation_extension_metrics.json
outputs/csr_statistical_interpretation.md
```

The conclusion matrix records source, analysis role, comparison, estimate/context, decision and controlled interpretation. Negative controls block incomplete source sets, cross-output drift, invalid multiplicity flags, MI MCSE failures, missing fixed-delta scenarios, reversed retention-hazard interpretation and regulatory/efficacy overclaims.

## Statistical reviewer-response artifacts

After v0.21 interpretation, v0.22 writes:

```text
outputs/statistical_review_queries.csv
outputs/statistical_review_query_checks.csv
outputs/statistical_review_query_metrics.json
outputs/statistical_review_query_response.md
```

The response table records query ID, risk area, reviewer question, evidence sources, decision status, generated response and allowed claim. Negative controls block primary decision drift, Week 24 denominator drift, incomplete MAR/JR/CR/CIR evidence, missing fixed-delta comparison context, treatment-assignment mismatch drift, safety role promotion, retention-hazard direction errors, generated overclaim fragments and regulatory-scoped review claims.

## Key v0.22 and inherited files

```text
spec/statistical_review_queries_v0_22.json              reviewer-query contract and claim boundary
src/cdisc_portfolio/statistical_review_queries.py       evidence reconciliation + response generation
scripts/run_statistical_review_queries.py               standalone reviewer-response runner
tests/test_statistical_review_queries.py                positive + blocking negative controls
docs/statistical_review_query_provenance.md             v0.22 design, evidence and boundary

spec/csr_interpretation_v0_21.json                      base interpretation contract and claim boundary
spec/csr_interpretation_extension_v0_21.json            multiplicity decision + fixed-delta context controls
src/cdisc_portfolio/csr_interpretation.py               cross-output CSR-style interpretation logic
src/cdisc_portfolio/csr_interpretation_extension.py     fixed-delta and reject-flag interpretation audit
scripts/run_csr_interpretation.py                       standalone complete interpretation runner
tests/test_csr_interpretation.py                        base positive + negative interpretation controls
tests/test_csr_interpretation_extension.py              multiplicity/tipping negative controls
docs/csr_statistical_interpretation.md                  statistical interpretation design and evidence

spec/analysis_readiness_v0_20.json                      cutoff, checks, issue dispositions and closure claims
src/cdisc_portfolio/analysis_readiness.py               readiness + closure implementation
scripts/run_analysis_readiness.py                       pre-closure readiness runner
scripts/run_analysis_closure.py                         closure -> v0.21 interpretation -> v0.22 reviewer responses
docs/study_statistician_analysis_readiness.md           v0.20 review sequence and evidence boundary

src/cdisc_portfolio/change_control_v020.py              layered v0.20 change-control merger
spec/change_impact_graph_v0_20_extension.json           readiness dependency extension
spec/change_requests_v0_20_extension.json               CR-014

spec/standards_validation_v0_19.json                    pinned official standards evidence contract
src/cdisc_portfolio/dataset_json.py                     Dataset-JSON + CORE transport generation
src/cdisc_portfolio/core_cache.py                       safe cache/rule-availability audit
src/cdisc_portfolio/core_validation.py                  executable / NOT_AVAILABLE evidence state

R/mmrm_analysis.R                                       primary ACTOT MMRM
R/mmrm_cross_package_qc.R                               independent rows + nlme MMRM
R/tte_retention_analysis.R                              KM/log-rank/Cox retention
R/rbmi_reference_based.R                                MAR/JR/CR/CIR sensitivity
spec/analysis_traceability.csv                          T01–T25 registry
spec/output_contracts.json                              executable TLF contracts
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
python scripts/run_analysis_readiness.py
python scripts/run_change_impact.py
python scripts/validate_traceability.py
python scripts/run_analysis_closure.py
```

`run_analysis_closure.py` executes evidence closure, the complete v0.21 CSR-style interpretation pack, and then the v0.22 reviewer-response pack. `scripts/run_statistical_review_queries.py` can rerun only the reviewer-response layer after all required upstream outputs already exist.

Generated evidence is written under `outputs/`; GitHub Actions uploads the complete output directory so statistical, metadata, standards, lineage, readiness, governance, interpretation and reviewer-response evidence can be inspected from the same clean run.

# Changelog

## 0.22.0 — 2026-08-25

- Add a post-interpretation Statistical Review Query and Decision-Provenance Pack that converts Study Statistician review questions into executable evidence reconciliations rather than adding another model, estimand, analysis population or TLF.
- Add exactly five controlled reviewer queries, SRQ-001–SRQ-005, covering the primary Week 24 efficacy decision, missing-data robustness, planned-versus-actual treatment mismatches, descriptive safety interpretation and exploratory retention interpretation.
- Reconcile the primary reviewer response to the controlled multiplicity decision; the live evidence remains **0/2 family-wise rejections** with adjusted p-values **0.338669 / 0.843940**, so no confirmatory efficacy-success conclusion is supported.
- Require the missing-data reviewer response to reconcile **116 observed + 138 missing = 254 randomized subjects (54.3% missing)**, require exact MAR/JR/CR/CIR strategy coverage for both primary comparisons, require all reference-based MCSE gates to pass, and include fixed-delta directional-tipping context.
- Retain **8/8** reference-based strategy/comparison rows with **8/8 MCSE passes** and report directional tipping at **1.5621 ACTOT points** for Low Dose versus Placebo and **1.0333 ACTOT points** for High Dose versus Placebo; the response explicitly avoids a blanket `fully robust` claim.
- Recount planned-versus-actual treatment assignment mismatches directly from the generated ADTTE-style data and reconcile the result to readiness evidence; the live count remains **12**. Exploratory retention continues to use planned randomized treatment (`TRT01P`) as `ANLTRT` while retaining actual treatment as context.
- Keep the two TEAE risk-difference rows descriptive only; first-live-run risk differences range from **0.1192 to 0.1886** and are not promoted to inferential safety or benefit-risk claims.
- Preserve the two retention hazard ratios as exploratory study-discontinuation evidence: **3.0852** and **2.9246**, both interpreted as higher study-discontinuation hazard rather than efficacy results.
- Generate `outputs/statistical_review_queries.csv`, `outputs/statistical_review_query_checks.csv`, `outputs/statistical_review_query_metrics.json` and `outputs/statistical_review_query_response.md` after v0.21 statistical interpretation.
- First live implementation run Actions **#651 / run 32774536503** on head `a130bc12f591fcccc989242148698edfd490bc52` completed the full Python/R/CDISC/MMRM/MI/readiness/closure/reviewer-response workflow successfully with **10/10 reviewer-response checks PASS**; artifact `9537615679`, digest `sha256:561e3c8c50c7697a7306e78018280add24ac89f75c750c753810d3c0488b0b63`.
- Harden the post-live-run gate by requiring exact strategy coverage per comparison, exact fixed-delta comparison coverage and a lexical overclaim guard with no exception path.
- Expand negative controls to block primary multiplicity/CSR decision drift, Week 24 denominator drift, incomplete reference-based strategies, missing fixed-delta comparison evidence, treatment-mismatch drift, safety-role promotion, retention-hazard direction errors, generated overclaim fragments and regulatory-scoped review claims.
- Keep CR-001–CR-014 and T01–T25 unchanged. v0.22 is a post-closure/post-interpretation reviewer-response layer and does not create a circular dependency into the pre-closure change-control graph.
- Controlled review-response claim: `PORTFOLIO_STATISTICAL_REVIEW_RESPONSE_READY`. This is independent public-data portfolio evidence only, not sponsor/CRO correspondence, a health-authority response, sponsor-approved CSR review, benefit-risk approval or submission readiness.

## 0.21.0 — 2026-08-24

- Add a post-closure Study Statistician interpretation layer that turns already validated efficacy, missing-data, safety and retention evidence into an executable CSR-style conclusion matrix rather than adding another model, estimand, population or TLF.
- Reconcile the two Week 24 primary `mmrm::mmrm` contrasts directly against the controlled Bonferroni multiplicity table; require exact agreement of estimates and raw p-values and independently audit `reject_familywise` against both local-alpha and adjusted-p decision rules.
- Preserve the primary statistical conclusion: adjusted p-values **0.338669 / 0.843940** yield **0/2 family-wise rejections**, so the interpretation layer explicitly blocks a confirmatory efficacy-success conclusion.
- Keep reference-based MAR/JR/CR/CIR analyses as supportive sensitivity evidence: validate **8/8 expected rows** and **8/8 MCSE passes** without promoting sensitivity analyses into the confirmatory family.
- Add fixed-delta directional-tipping interpretation alongside reference-based MI so same-direction MI results are not over-described as complete robustness. Validate **6/6 expected fixed-delta rows** across three scenarios and two active-versus-placebo comparisons.
- Record earliest directional tipping deltas of **1.5621 ACTOT points** for Low Dose versus Placebo and **1.0333 ACTOT points** for High Dose versus Placebo, both under `DIVERGENT_WORSENING`.
- Retain TEAE risk differences as descriptive safety evidence and time-to-discontinuation hazard ratios as exploratory retention evidence; HR > 1 is explicitly interpreted as higher study-discontinuation hazard, not worse efficacy.
- Generate `outputs/csr_conclusion_matrix.csv`, `outputs/csr_interpretation_checks.csv`, `outputs/csr_interpretation_metrics.json` and `outputs/csr_statistical_interpretation.md` after v0.20 evidence closure.
- Pass **11/11** base interpretation checks plus **4/4** fixed-delta extension checks, producing a **10-row** final conclusion matrix with zero prohibited efficacy/regulatory overclaim fragments.
- Add negative controls for failed evidence closure, MMRM/multiplicity drift, inconsistent family-wise rejection flags, incomplete MI strategy coverage, MCSE failure, missing fixed-delta scenarios, invalid tipping provenance, retention-hazard direction errors and sponsor/regulatory overclaims.
- Keep CR-001–CR-014 and the T01–T25 registry unchanged. v0.21 is a post-closure interpretation/review layer; forcing a new pre-closure change-request dependency would create a circular governance order.
- Controlled interpretation claim: `PORTFOLIO_STATISTICAL_INTERPRETATION_READY`. This is public-data portfolio evidence only, not a sponsor CSR, medical-writing sign-off, benefit-risk decision or regulatory-submission decision.
- Functional clean run Actions **#625 / run 32701384371** on head `2c7186255004b286b483e0564b162dcc1edfad55` passed the full Python/R/CDISC/MMRM/MI/readiness/closure/interpretation workflow; artifact `9510775094`, digest `sha256:30f046072cc4207bf6686d3bcc877384a74e3c43efe69da8f65e1719a7b3b8b8`.
- README/documentation head `07e4026d9dfdfe581138aa874a5afec26ee8fb97` subsequently passed Actions **#629 / run 32702193882** before this changelog entry was added.

## 0.20.0 — 2026-08-24

- Add a controlled study-statistician analysis-readiness specification with analysis data cutoff **2015-03-05**, treatment-blind aggregate checks, expected known-issue counts/dispositions and portfolio-only readiness/closure claims.
- Add a pre-closure readiness runner and separate post-governance evidence-closure runner so readiness, change control, traceability and closure have a one-way dependency order rather than a circular gate.
- Validate **306** subjects / **254** randomized subjects, **254/254** randomized ACTOT baselines, **116** observed and **138** missing Week 24 ACTOT records, and **0** analysed dates beyond the configured cutoff.
- Pass **5/5** treatment-blind aggregate checks and **7/7** final pre-closure readiness checks; retain **3** controlled public-data issues with explicit dispositions and **0** blocking open issues.
- Retain the three audited issue counts rather than suppressing them: **12** planned/actual treatment mismatches, **138** randomized subjects without observed Week 24 ACTOT and **10** selected ADQSCIBC reference-value differences.
- Block the blinded readiness artifact from containing the treatment-assignment field names/tokens `TRT01P`, `TRT01A` or `ANLTRT`.
- Add `CR-014` for analysis-readiness definition or known-issue-disposition changes. The v0.20 dependency chain covers readiness configuration, blinded aggregate review, final readiness review and evidence closure while intentionally affecting **0 TLFs**.
- Advance layered statistical change control to **14 change requests**, **88 propagated component links** and **311/311 required impact relationships/resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources.
- Keep the executable statistical output registry at **T01–T25 / version 0.17.0** and retain **25/25** output, contract, analysis-data and QC-evidence links because v0.20 adds statistician review/governance evidence rather than another statistical TLF.
- Add evidence closure requiring same-run analysis-readiness, change-control and traceability evidence; pass **4/4** closure checks with controlled claim `PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE`.
- Add negative controls for cutoff overrun, known-issue count drift, blank/blocking issue dispositions, failed readiness prerequisites, failed closure prerequisites and regulatory/submission-readiness overclaims.
- Repair the readiness/closure unit-test fixtures after the initial refactor exposed stale one-layer assumptions; the full implementation validation passes **192 Python tests**.
- Order CI as analysis-dataset/TLF reviewer -> pre-closure readiness -> statistical change control -> SAP-to-TLF traceability -> evidence closure.
- Full implementation clean-runner Actions **#603 / run 32695160717** on head `e2ba881ea08520fa2b337f9979df904fd7133640` passes the complete Python/R analysis, standards, readiness, change-control, traceability and closure workflow; artifact digest `sha256:41433bad895224845f84853533fd990ea72cd0fa722b193847a4be479cabb55d`.
- Add `docs/study_statistician_analysis_readiness.md` and update the README while preserving the evidence boundary: this is public-data portfolio evidence, not a sponsor database lock, formal blinded data review meeting, sponsor/CRO sign-off, validated production release or regulatory-submission readiness decision.

## 0.19.0 — 2026-08-24

- Add CDISC Dataset-JSON 1.1 exchange generation for the four validated ADSL-, ADAE-, ADQS- and ADTTE-style analysis datasets and validate every generated payload against a pinned official Dataset-JSON schema.
- Exchange **4 datasets / 85 variables / 2,569 records**, preserve **1,675** missing values as JSON `null`, and complete the official schema gate with **0 errors**.
- Generate CORE CSV transport metadata from the same controlled v0.18 metadata catalog, using CORE-recognised `Char` / `Num` types and SAS-epoch numeric days for transported date values while retaining ISO dates in Dataset-JSON.
- Pin the official CDISC CORE engine, an official populated cache snapshot and `cdisc-open-rules` source; reject placeholder cache files and record SHA256 identities for required cache and rule-discovery evidence.
- Verify the populated official cache contains **981** unique CORE rule IDs, with **981/981** literal ID overlap between `rules_dictionary.pkl` and `rules.pkl`, while the requested `adamig/1-3` dictionary key is present but returns **0 executable rule IDs**.
- Verify the pinned open-rule source contains **191** `Unpublished/ADAMIG` YAML files and one published executable rule explicitly referencing ADaMIG; do not reinterpret that evidence as a complete published ADaMIG 1.3 executable ruleset.
- Introduce the controlled state **`NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE`**. A zero-rule result is never reported as zero issues, successful executable validation or formal ADaM conformance; no `core_official_report.json` is fabricated when executable validation is unavailable.
- Retain a strict alternate execution path for future official caches that expose non-zero ADaMIG rules: at least one rule must execute and CLI failure, unknown status or CORE `EXECUTION ERROR` is blocking.
- Add negative controls for cache placeholders, availability-state mismatch, zero-rule success overclaiming, empty executable reports and CORE execution errors.
- Add `CR-013` for official standards-engine/rule-availability changes and a four-component standards governance chain covering configuration, Dataset-JSON exchange validation, CORE rule-availability audit and executable-versus-NOT_AVAILABLE evidence state.
- Validate **13 change requests**, **84 propagated component links** and **304/304 required impact relationships/resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources; CR-013 has **0 impacted TLFs**.
- Retain the statistical output registry at **T01–T25 / version 0.17.0** and pass **25/25** output, output-contract, analysis-data and QC-evidence links because v0.19 adds standards/governance evidence rather than another statistical TLF.
- Clean-runner Actions #564 on head `051b74ec7335ecb5da0e48b24bb60a25d1701f79` passes the complete Python/R analysis, standards, reviewer, change-control and traceability workflow; artifact digest `sha256:925e8d5b02f8cefc5e8b3fe9c589b333d2b446428403b4a1a37d6294bd0b8c85`.
- Preserve the explicit evidence boundary: successful Dataset-JSON schema validation plus CORE availability governance is portfolio evidence only, not formal ADaM/Define-XML conformance, submission readiness, sponsor/CRO production experience or regulatory validation.

## 0.18.0 — 2026-08-23

- Add controlled ADaM-style variable metadata and source/derivation lineage for four generated analysis datasets: ADSL-, ADAE-, ADQS- and ADTTE-style outputs.
- Validate **85/85 generated variables (100%)** with exact metadata coverage, including labels, data types, roles, predecessor/derived origin, source references, derivation text and key status.
- Validate **110** declared source references and resolve **39/39** cross-analysis-dataset lineage references; classify **52 derived** and **33 predecessor** variables.
- Add a deterministic Define-XML-inspired metadata export with **4 dataset definitions / 85 variable definitions** and reparse/count reconciliation in CI.
- Reference CDISC Define-XML **2.1.11** while locking `conformance=NOT_ASSESSED`; negative controls reject attempts to claim formal conformance.
- Add negative-control tests for missing/stale metadata, unresolved upstream lineage, blank derivations and conformance overclaiming; first complete v0.18 live validation passes **146 Python tests**.
- Add `CR-012` and a three-component metadata governance chain: metadata definition -> lineage validation -> Define-XML-inspired export.
- Validate **12 change requests**, **80 propagated component links** and **279/279 required impact relationships/resources** with zero missing, extra or unresolved resources.
- Keep `CR-012` separate from inferential analysis families with **12 required impacts / 0 impacted TLFs**.
- Retain the statistical output registry at **T01–T25 / version 0.17.0** because v0.18 adds metadata governance rather than a new TLF; the v0.18 live run still passes 25/25 output, contract, analysis-data and QC-evidence links.
- Preserve the explicit portfolio boundary: metadata/XML evidence is not formal ADaM conformance, submission-ready Define-XML, regulatory validation or sponsor/CRO production experience.

## 0.17.0 — 2026-08-23

- Add an exploratory ADTTE-style `TTDISC` analysis from first treatment date (`TRTSDT`) to study discontinuation/protocol-completion date (`EOSDT`).
- Correct a material analysis-definition issue discovered during review: **12/254** randomized subjects have `TRT01P != TRT01A`, so the survival comparison now uses planned randomized assignment (`ANLTRT=TRT01P`) while retaining `TRT01A` as actual-treatment context.
- Add `TRTDIFFL`, `ANLTRTSRC`, `CNSRSRC` and `EVNTSRC` so planned/actual treatment differences and event/censor provenance remain visible in the ADTTE-style dataset.
- Make event, censor, date and description derivations specification-driven through `spec/tte_retention.json` rather than hard-coded source-column names.
- Verify randomized arm sizes Placebo=86, Low Dose=84 and High Dose=84, with 144 discontinuation events and 110 protocol-completion censors.
- Pass **16/16** blocking ADTTE-style derivation checks and record SHA256 identities for the TTE spec, ADSL-style source and ADTTE-style output.
- Add T24 Kaplan–Meier retention at days 56/112/168/182 and T25 exploratory active-versus-placebo log-rank/Cox diagnostics using R `survival`.
- Verify Day-182 retention **67.44% / 29.76% / 33.25%** for Placebo / Low / High; exploratory HRs are **3.0852** and **2.9246**.
- Report `cox.zph` diagnostics without turning PH significance into an artificial CI acceptance constraint; validated p-values are 0.8310 and 0.7577 with 0/2 diagnostic signals.
- Pass **14/14** blocking R survival checks.
- Extend executable traceability from T01–T23 to **T01–T25** at registry version `0.17.0`; pass 25/25 outputs, contracts, analysis-data links and QC-evidence links.
- Add CR-011 and a layered v0.17 TTE dependency extension; validate **11** change requests, **77** propagated component links and **267/267** required impact relationships/resources with zero missing, extra or unresolved resources.
- Keep T24/T25 exploratory and explicitly outside the ACTOT Week 24 Bonferroni confirmatory family.

## 0.16.0 — 2026-08-23

- Add distinct-package primary MMRM re-programming using `nlme::gls` with `corSymm + varIdent` while retaining `mmrm::mmrm` as the primary model.
- Independently reconstruct the observed ACTOT subject-visit analysis rows rather than reusing the primary MMRM analysis dataset.
- Validate **451/451** primary/independent rows and **189/189** subjects with identical key sets, zero missing/extra keys, zero exact-field mismatches and zero numeric mismatch rows.
- Compare Week 24 point estimates, model-based SEs and treatment-effect signs against pre-specified 0.0005 absolute tolerances; pass **18/18** required checks.
- Observe maximum estimate difference **1.30015e-05** and maximum SE difference **2.63230e-06**.
- Deliberately exclude df/p-value agreement because the primary implementation uses Satterthwaite inference and the `nlme` reconstruction does not reproduce that denominator-df method.
- Add provenance SHA256 fingerprints for validation spec, contrast sources and both analysis datasets.
- Add CR-010 and a layered cross-package validation dependency extension; validate 10 change requests, 73 propagated links and **254/254** required impact relationships/resources.
- Add branch/event CI concurrency with `cancel-in-progress: true` so superseded long-running MI workflows are cancelled.

## 0.15.0 — 2026-08-23

- Add a controlled Week 24 primary multiplicity decision layer for Low Dose vs Placebo and High Dose vs Placebo MMRM hypotheses.
- Lock family-wise alpha 0.05 and Bonferroni local alpha 0.025 across two primary hypotheses.
- Verify raw p-values 0.169334 and 0.421970, adjusted p-values 0.338669 and 0.843940, and no family-wise rejection for either hypothesis.
- Add T23 as the executable multiplicity output and pass **12/12** multiplicity QC checks.
- Add CR-009 so multiplicity-rule changes propagate through the controlled spec, primary MMRM evidence and T23 without pulling sensitivity analyses into the confirmatory family.

## 0.14.0 — 2026-08-22

- Add reference-based `rbmi` sensitivity analyses for MAR, Jump to Reference (JR), Copy Reference (CR) and Copy Increments in Reference (CIR) using placebo as the reference distribution.
- Anchor treatment-discontinuation timing to `EOSDT` and add independent guards against invalid use of observations after the affected scheduled visit.
- Add T22 reference-based MI with ICE audit, draw diagnostics, Rubin pooling and Monte Carlo precision QC.
- Run 200 imputations per pairwise model; pass **27/27** required reference-based checks with maximum `MCSE(estimate) / pooled SE` **0.053811** against a 0.075 threshold.
- Extend change control and traceability while keeping the reference-based analyses explicitly sensitivity analyses rather than primary confirmatory inference.

## 0.13.0 — 2026-08-22

- Add controlled subject-level multiple-imputation sensitivity for Week 24 ACTOT using pairwise Xanomeline Low Dose versus Placebo and High Dose versus Placebo analyses.
- Increase the controlled `rbmi` run from the earlier 50-imputation development setting to **200 imputations** per pairwise comparison.
- Use approximate-Bayesian longitudinal MI with Week 8/16/24 ACTOT change-from-baseline history, unstructured covariance, REML and baseline-by-visit/treatment-by-visit model terms.
- Analyse Week 24 within each imputed data set using baseline-adjusted ANCOVA and combine active-minus-placebo inference using Rubin pooling.
- Add four controlled MI sensitivity scenarios: MAR, active +1, active +2, and active +1/placebo -1 for outcomes originally missing at Week 24; observed Week 24 and non-Week-24 outcomes cannot receive delta shifts.
- Add a separate Monte Carlo precision gate requiring `MCSE(estimate) / pooled SE <= 7.5%` for both MAR active-versus-placebo comparisons. Model-fit success alone is not sufficient for MI acceptance.
- Add T20 MAR pairwise MI and T21 delta-adjusted MI sensitivity to the formal SAP-to-TLF registry and executable output contracts, extending structural traceability from 19 to **21 TLFs**.
- Require T20/T21 to resolve dedicated MI QC and MCSE QC; additionally require draw diagnostics for T20 and the delta audit for T21.
- Add **CR-007** for controlled MI-assumption changes covering imputation count, longitudinal imputation model, MCSE threshold and delta scenarios, increasing the machine-readable request set from six to **seven change requests**.
- Extend CR-003 primary-visit and CR-005 treatment-discontinuation/intercurrent-event strategy propagation to T20/T21 and their MI review/QC path so v0.13 sensitivity outputs cannot remain isolated from upstream statistical changes.
- Add regression coverage after CI detected stale v0.12 assumptions hard-coded in tests, including the former six-change-request expectation; correct the tests rather than weakening the v0.13 specification.
- Synchronise the consolidated README, SAP, QC plan, TLF shells, change-control document and analysis-traceability document to the current v0.13 state while retaining the versioned v0.13 addenda as change history.

## 0.12.0 — 2026-08-22

- Add a deterministic fixed-delta pattern-mixture mean-shift diagnostic for departures from the primary Week 24 MMRM MAR reference analysis.
- Add three controlled adverse paths over a 0-6 ACTOT point grid in 0.5-point steps and analytic direction-of-effect tipping thresholds.
- Add T18 fixed-delta sensitivity grid and T19 directional tipping-point output, extending the executable registry to **19 TLFs**.
- Extend statistical change control to **six** simulated requests with CR-006 governing fixed-delta sensitivity assumptions and upstream primary-visit/MMRM/intercurrent-event changes propagating to T18/T19.
- Keep the deterministic fixed-delta CI/p-value calculation explicitly separate from multiple-imputation inference; v0.12 does not claim Rubin pooling or reference-based imputation.

## 0.11.0 — 2026-08-22

- Add machine-readable ACTOT estimand `EST-ACTOT-W24-TP` using the ICH E9(R1)-style five-attribute structure: treatment, population, variable, treatment-discontinuation strategy and population-level summary measure.
- Keep estimator assumptions separate from the estimand: the primary analysis remains observed-data REML MMRM with unstructured covariance and Satterthwaite df; MAR is recorded as a working estimator assumption rather than an estimand attribute.
- Keep the existing Week 24 LOCF ANCOVA only as a supportive legacy-style sensitivity/stress test; LOCF does not enter the primary MMRM.
- Add executable arm-by-visit ACTOT missingness review and subject-level Week 8/16/24 observed/missing patterns.
- Add T16 ACTOT missingness by visit and T17 Week 24 missingness by recorded disposition context.
- Verify a first-pass public-data target population of 254 randomised subjects with observed baseline ACTOT: Week 24 observed=116 and missing=138 (**54.3% missing**).
- Verify Week 24 missingness by arm as Placebo 27/86 (31.4%), Low Dose 69/96 (71.9%) and High Dose 42/72 (58.3%).
- Record that the current public run contains **0 observed post-discontinuation arm-visit ACTOT records**; treatment-policy retention is therefore validated by executable rules and negative-control fixtures rather than a positive live-data example.
- Add **21 required estimand/missing-data checks**, including five-attribute completeness, treatment-policy handling, observed-data MMRM alignment, denominator reconciliation and no LOCF in the primary model.
- Add negative controls that make LOCF primary, remove a post-discontinuation observation from an MMRM fixture and corrupt a missingness denominator.
- Extend SAP-to-TLF structural traceability from 15 to **17 planned TLFs**; first-pass live validation passes 17/17 output, contract, analysis-dataset and QC-evidence links.
- Extend statistical change control with CR-005, an illustrative treatment-discontinuation strategy change from treatment-policy to hypothetical strategy, requiring review of T11-T17, MMRM inputs/QC, estimand QC, controlled documents and `spec/estimands.json`.
- Expand v0.11 change-control coverage to **88/88 required impact declarations** and **88/88 resolved resources** across five scenarios in the first-pass live run.
- Remove the stale hard-coded change-control version: graph and request specifications must declare the same version, otherwise the gate fails. Add a regression test for version mismatch.
- Expand the final-head Python unit-test target from 40 to **49** while retaining the established Python pipeline, R/Python, MMRM, reviewer, design and randomisation gates.
- Correct two historical reviewer prose labels: actual arm sizes are Placebo=86, Low Dose=96, High Dose=72; observed Week 24 Ns are Placebo=59, Low Dose=27, High Dose=30. Analysis outputs were unchanged.
- Add `docs/estimand_missing_data_review.md`, `docs/sap_v0_11_estimand_addendum.md` and v0.11 TLF/QC documentation. This remains independent public-data portfolio work, not a sponsor-approved estimand, SAP decision or regulatory analysis.

## 0.10.0 — 2026-08-22

- Add a machine-readable statistical change-impact dependency graph spanning analysis datasets, TLFs, QC evidence, controlled documents and planning/schedule specifications.
- Add four illustrative portfolio change requests: safety-population definition, TEAE follow-up window, primary ACTOT visit and primary MMRM covariance structure.
- Propagate impacts transitively from each changed statistical component rather than relying on a manually entered flat affected-file list.
- Verify **67/67 graph-required impact declarations** and **67/67 required downstream resources** in the live GitHub Actions run, with zero missing and zero extra declarations across the four scenarios.
- Resolve every impacted TLF ID through the existing SAP-to-TLF registry and require the corresponding generated output to exist in the same live run.
- Verify CR-001 across 4 propagated components / 18 impacts / T01-T07; CR-002 across 3 / 14 / T04-T07; CR-003 across 6 / 24 / T08-T12 plus T15; and CR-004 across 3 / 11 / T11-T15.
- Add hard validation for unknown dependency nodes and dependency cycles.
- Add negative-control tests that remove a graph-required TLF declaration and require failure; retain explicit tests for transitive propagation and conservative extra review items.
- Add `outputs/change_impact_assessment.csv`, `outputs/change_impact_metrics.json` and `outputs/change_impact_summary.md`, with SHA256 identity for the dependency graph, change requests and SAP-to-TLF registry.
- Make statistical change-impact review a blocking CI gate after the v0.9 dataset/TLF reviewer and before final SAP-to-TLF traceability validation.
- Expand Python unit tests to **40/40 passed** while retaining 24/24 Python pipeline QC, 16/16 R/Python programming QC, 11/11 MMRM QC, 24/24 dataset/TLF reviewer QC, 15/15 SAP-to-TLF traceability, 7/7 protocol-design QC and 10/10 randomisation/kit QC.
- Add `docs/change_control_impact_assessment.md` and a controlled v0.10 SAP change-control addendum. The four change requests remain portfolio simulations and do not alter the currently analysed 30-day TEAE window, Week 24 analysis focus or unstructured primary MMRM.

## 0.9.0 — 2026-08-22

- Add a blocking post-generation analysis-dataset and TLF reviewer gate that runs after R MMRM and before final SAP-to-TLF traceability validation.
- Add 19 required cross-dataset, derivation, population, TLF-denominator and TLF-structure checks across generated ADSL-style, ADAE-style, ACTOT, ANCOVA, MMRM and safety/efficacy outputs.
- Add five machine-readable dataset contracts for ADSL-style, ADAE-style, ACTOT, ANCOVA and MMRM, covering keys, required columns, non-missing fields and controlled values.
- Verify **24/24 required reviewer checks** in GitHub Actions across six review areas: analysis dataset, derivation, metadata contract, population, TLF denominator and TLF structure.
- Review 17 generated files and record SHA256 for every reviewed file; also record the exact dataset-contract specification hash.
- Reconstruct randomised/safety arm denominators as Placebo=86, Low Dose=96 and High Dose=72 and reconcile them to linked TLF-style outputs.
- Reconstruct observed Week 24 Ns as Placebo=59, Low Dose=27 and High Dose=30 and reconcile Week 24 ANCOVA/MMRM output coverage to generated analysis datasets.
- Require every MMRM row to trace to the exact ACTOT source record through `STUDYID + USUBJID + QSSEQ` with treatment, `AVAL`, `BASE` and `CHG` agreement.
- Add negative-control tests that deliberately corrupt treatment consistency, a safety-table denominator, MMRM `CHG`, a required dataset column and a controlled flag; validators must reject the corrupted inputs.
- Expand Python unit tests to **34/34 passed** while retaining 24/24 Python pipeline QC, 16/16 R/Python programming QC, 11/11 MMRM QC, 15/15 SAP-to-TLF traceability, 7/7 protocol-design QC and 10/10 randomisation/kit QC.
- Add `docs/analysis_dataset_review.md`, update the analysis-dataset specification for v0.9 and add a versioned SAP review addendum rather than silently overwriting the v0.8 analysis plan.

## 0.8.0 — 2026-08-22

- Add a deterministic portfolio randomisation and initial-kit schedule linked to the v0.7 `E2.5_P80` planning scenario with 390 planned randomisations.
- Generate stratified permuted-block 1:1:1 allocation across five illustrative strata using block sizes 3 and 6.
- Verify 390 unique randomisation numbers and 390 unique initial kit codes with exactly 130 allocations per treatment arm and 26 allocations per arm within every stratum.
- Generate 87 balanced blocks: 44 blocks of size 3 and 43 blocks of size 6; every block is balanced across all three treatment arms.
- Separate blinded and unblinded schedule outputs. The blinded schedule contains only `randomisation_id`, `stratum` and `kit_id`; treatment, blind-code and block information remain in unblinded outputs.
- Add a kit-to-treatment decoding list and verify zero mismatches between assigned kits and unblinded treatment allocations.
- Add 10 required randomisation/kit QC checks covering planned count, unique IDs, overall/stratum/block balance, kit reconciliation, blinded-column isolation and key reconciliation; the verified live run passes 10/10.
- Report longest same-treatment runs by stratum as an informational diagnostic rather than a post hoc acceptance constraint.
- Record SHA256 digests for the randomisation specification and generated schedule/QC outputs.
- Expand Python unit tests to 29 while retaining 24/24 Python pipeline QC, 16/16 R/Python programming QC, 11/11 MMRM QC, 15/15 SAP-to-TLF traceability and 7/7 protocol-design QC.
- Update README and SAP to portfolio version 0.8 and document the access-control boundary: this public exercise is not an IRT/IWRS production schedule and does not model resupply, site inventory, expiry, replacement or emergency-unblinding transactions.

## 0.7.0 — 2026-08-22

- Add a machine-readable three-arm protocol-design specification for a portfolio Week 24 ACTOT change-from-baseline planning scenario.
- Define two active-versus-placebo comparisons with two-sided family-wise alpha 0.05 and Bonferroni per-comparison alpha 0.025.
- Add continuous-endpoint sample-size utilities, dropout inflation and achieved-power back-calculation after integer rounding.
- Evaluate six effect/power scenarios using common planning SD 6.0 and 15% anticipated dropout.
- Verify scenario totals from 273 to 792 randomised subjects across the six illustrative scenarios; assumptions are explicitly not claimed as the source trial design.
- Add seven required protocol-design QC checks covering alpha reconciliation, dropout inflation, achieved power, unique scenarios, total-N reconciliation and effect/power monotonicity; verified run passes 7/7.
- Record SHA256 of the exact machine-readable design specification used by the calculation.
- Add `docs/protocol_statistical_design.md` and a protocol statistical-review checklist covering design, endpoints, estimand components, multiplicity, sample size, populations, models, safety, programming implications and DSMB/interim-analysis boundaries.
- Update the SAP and README to portfolio version 0.7 with the verified protocol-design outputs and current analysis/QC evidence.
- Expand Python unit tests to 19 while retaining 24/24 Python pipeline QC, 16/16 R/Python programming QC, 11/11 MMRM QC and 15/15 SAP-to-TLF structural traceability.

## 0.6.0 — 2026-08-22

- Add a machine-readable SAP-to-TLF registry for 15 planned outputs spanning safety, ANCOVA and longitudinal MMRM analyses.
- Add executable output contracts checking required files, minimum row counts and required columns.
- Require every planned TLF to resolve to its analysis dataset(s) and QC evidence.
- Record SHA256 identity for every generated TLF output.
- Add an independent CI gate that validates the final generated artifacts rather than only checking static specifications.
- Detect and correct a real T08 specification mismatch (`chg_mean` versus the generated `change_mean`) without weakening the validation rule; the final T08 contract also requires baseline, Week 24 and change mean/SD fields.
- Verify 15/15 planned TLFs, 15/15 output files, 15/15 output contracts, 15/15 analysis-dataset links and 15/15 QC-evidence links.
- Add `docs/analysis_traceability.md` and extend the CI artifact summary with traceability detail.

## 0.5.0 — 2026-08-22

- Add an observed-data ACTOT longitudinal MMRM using Week 8, Week 16 and Week 24 change from baseline; LOCF values are not used in the repeated-measures model.
- Pre-specify `CHG ~ treatment * visit + baseline * visit` with REML, unstructured within-subject covariance and Satterthwaite degrees of freedom.
- Add a heterogeneous AR(1) covariance sensitivity fit using the same fixed-effects model.
- Add visit-specific estimated marginal means and six active-versus-placebo primary contrasts.
- Verify the MMRM input as 451 observed post-baseline records from 189 subjects: Week 8=189, Week 16=146 and Week 24=116.
- Add 11 required MMRM data/model/inference checks; the verified GitHub Actions run passes 11/11.
- Verify finite primary and sensitivity fits. Unstructured: logLik -1299.3136, AIC 2610.6272, BIC 2630.0777. Heterogeneous AR(1): logLik -1309.7404, AIC 2627.4809, BIC 2640.4479.
- Verify primary Week 24 treatment contrasts: Low Dose vs Placebo -1.6131 (95% CI -3.9216 to 0.6953, p=0.1693); High Dose vs Placebo -0.9271 (95% CI -3.2032 to 1.3489, p=0.4220).
- Add a diagnostic comparison of Week 24 MMRM and the existing observed-case ANCOVA without requiring the estimands to match numerically.
- Add machine-readable MMRM dataset, visit-count, LS-mean, contrast, covariance-sensitivity, model-diagnostic, QC and metrics outputs.
- Extend GitHub Actions with R syntax parsing, `mmrm`/`emmeans` installation, the MMRM analysis gate and retained diagnostic artifacts.
- Expand the SAP and TLF planning documents so efficacy outputs are specified through Table 15, including MMRM and covariance sensitivity.
- Preserve the existing 10/10 Python unit tests, 24/24 required Python pipeline QC checks and 16/16 R/Python cross-language programming checks.

## 0.4.0 — 2026-08-22

- Add an independent R implementation of selected safety and efficacy derivations using the same public DM, EX, DS, AE and QS inputs.
- Keep executable derivation code separate: R does not call Python derivation functions and reads Python outputs only for the final comparison.
- Independently reproduce randomised, safety and completed populations, TEAE counts and DS treatment-end fallback counts in R.
- Independently reproduce the any-TEAE risk-difference table in R with zero difference at the reported precision.
- Independently reconstruct all 705 CIBIC analysis records with exact R/Python key, `QSSEQ`, `DTYPE` and source-derived `AVAL` agreement.
- Independently reconstruct all 818 ACTOT source rows with exact R/Python key, `AVAL`, `BASE`, `CHG`, baseline-flag and efficacy-flag agreement.
- Refit observed Week 24 and LOCF ANCOVA models in R with the same N and residual df as Python.
- Verify R/Python ANCOVA estimates, standard errors, confidence limits, p-values and baseline references with a maximum numeric difference of `7.11e-15` against a pre-specified `1e-8` tolerance.
- Add 16 required cross-language QC checks; the verified live run passes 16/16 while retaining the existing 10/10 Python unit tests and 24/24 Python pipeline QC checks.
- Pin the CI R runtime to R 4.6.1 and record `jsonlite` 2.0.0 plus full R session information.
- Add an R syntax parse gate before the independent R analysis.
- Add machine-readable R QC, R metrics, R safety/ANCOVA outputs and a dedicated cross-language QC design document.

## 0.3.0 — 2026-08-22

- Add pinned public CDISC QS Dataset-JSON input with 121,749 records.
- Add public `ADQSCIBC` and `ADQSADAS` Dataset-JSON reference inputs.
- Derive 705 CIBIC+ analysis records with Week 8/16/24 analysis windows and LOCF.
- Reproduce 100% of public ADQSCIBC analysis keys, source `QSSEQ` values and `DTYPE` classifications.
- Add source tracing for ten ADQSCIBC reference-value differences; all ten portfolio values match their selected public QS source records.
- Profile public ADQSADAS: 12,463 rows, 254 subjects and 15 ADAS-Cog parameters.
- Add ACTOT baseline/change derivation, descriptive outputs, Week 24 ANCOVA and LOCF sensitivity analysis.
- Reconstruct all 1,016 public selected ACTOT (`ANL01FL=Y`) keys with 100% `QSSEQ` and `DTYPE` agreement.
- Add a separate 11-item ADAS-Cog total recalculation diagnostic without replacing the public source ACTOT values.
- Split structural/source reference checks from informational value-agreement metrics when the public source and public reference disagree.
- Expand unit tests to 10 and required pipeline QC to 24 checks.
- Add a pre-analysis reference profiler to GitHub Actions so discrepancies remain inspectable even when the main workflow fails.
- Verify the complete v0.3 workflow in GitHub Actions with 10/10 unit tests and 24/24 required pipeline QC checks passing.

## 0.2.0 — 2026-08-21

- Use EX to define observed exposure and safety population.
- Add explicit exposure-date source flags and DS-disposition fallback when EX/DM end dates are both missing.
- Separate raw EX duration (`EXDURN_RAW`) from final treatment-window duration (`TRTDURN`) so fallback dates do not hide source-data incompleteness.
- Use DS to derive randomisation, completion and discontinuation.
- Add subject-level exposure summaries and source-date traceability.
- Add related and moderate/severe TEAE flags.
- Add disposition, exposure, severity and any-TEAE risk-difference outputs.
- Expand required QC plan and machine-readable run metrics.
- Expand tests from derivation/QC smoke tests to analysis and sample-size checks.
- Update GitHub Actions to print measurable live-run results and upload outputs.

## 0.1.0

- Initial DM/AE safety workflow with ADSL-style / ADAE-style derivation, TEAE summaries, sample-size utilities and provenance hashing.

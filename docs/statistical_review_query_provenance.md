# v0.22 Statistical Review Query and Decision-Provenance Pack

## Purpose

v0.22 adds a controlled post-interpretation reviewer-response layer. It does not add a statistical model, estimand, analysis population, TLF, or pre-closure change request. Its purpose is to make Study Statistician review judgement reproducible: a reviewer question must resolve to current analysis evidence, a bounded decision status, and an explicitly permitted claim.

The execution order is intentionally one-way:

```text
validated analysis / TLF / QC evidence
  -> v0.20 analysis readiness and evidence closure
  -> v0.21 CSR-style statistical interpretation
  -> v0.22 statistical reviewer query responses
```

This avoids circular governance dependencies and preserves the existing T01–T25 output registry and CR-001–CR-014 pre-closure change-control graph.

## Controlled reviewer queries

The machine-readable contract `spec/statistical_review_queries_v0_22.json` requires exactly five queries.

### SRQ-001 — Primary efficacy

**Question:** Do the primary Week 24 results support a confirmatory efficacy success conclusion?

The response is regenerated from the controlled multiplicity table and reconciled to the v0.21 CSR interpretation metrics. In the first full live run, the Week 24 family has **0/2 family-wise rejections** with adjusted p-values **0.338669 / 0.843940**. The only allowed conclusion is that the controlled primary family does not support confirmatory efficacy success.

### SRQ-002 — Missing data and robustness

**Question:** Given Week 24 missingness, how robust is the primary efficacy interpretation to missing-data assumptions?

The reviewer response must reconcile **116 observed + 138 missing = 254 randomized subjects**, report the **54.3% Week 24 missingness**, require the full MAR/JR/CR/CIR reference-based sensitivity set for both active comparisons, require every reference-based MCSE gate to pass, and include the fixed-delta directional-tipping context.

The validated live evidence contains **8/8 reference-based strategy/comparison rows with 8/8 MCSE passes**. Directional tipping occurs at **1.5621 ACTOT points** for Low Dose versus Placebo and **1.0333 ACTOT points** for High Dose versus Placebo. The response therefore cannot reduce the evidence to a single `robust/not robust` label: reference-based MI agreement is supportive, while stronger controlled MNAR shifts can reverse direction.

### SRQ-003 — Planned versus actual treatment mismatch

**Question:** How are planned-versus-actual treatment mismatches handled in the retention analysis?

The response independently recounts `TRT01P != TRT01A` in the generated ADTTE-style data and requires agreement with the readiness metric. The live data contain **12** mismatches. Exploratory retention uses planned randomized treatment (`TRT01P`) as `ANLTRT`, while actual treatment remains visible as context. The mismatch is retained as a known issue rather than hidden or reclassified as efficacy evidence.

### SRQ-004 — Safety

**Question:** Can the TEAE risk-difference results be used as an inferential safety or benefit-risk conclusion?

The reviewer response cross-checks the two TEAE risk-difference rows against the v0.21 conclusion matrix and requires `DESCRIPTIVE_SAFETY` / `DESCRIPTIVE_ONLY`. In the first live run, active-versus-placebo TEAE risk differences range from **0.1192 to 0.1886**. These are descriptive portfolio comparisons only and do not establish a benefit-risk conclusion or constitute evidence of established safety.

### SRQ-005 — Retention

**Question:** What do the retention hazard ratios mean, and can they be interpreted as efficacy results?

The response requires the source interpretation to preserve hazard direction and exploratory status. The live estimates are **HR 3.0852** for Low Dose versus Placebo and **HR 2.9246** for High Dose versus Placebo. Because both are greater than one, they indicate a higher **study-discontinuation hazard**, not worse efficacy. T24/T25 remain exploratory retention analyses outside the confirmatory ACTOT family.

## Blocking checks

The v0.22 gate requires all of the following to remain true in the same clean run:

1. all controlled reviewer-response inputs exist;
2. v0.20 readiness and v0.21 interpretation are complete;
3. the primary reviewer response reconciles to the controlled multiplicity decision;
4. the Week 24 observed/missing denominator reconciles to the randomized population;
5. each primary comparison contains exactly MAR/JR/CR/CIR reference-based evidence with passing MCSE, and both comparisons have fixed-delta tipping context;
6. the planned-versus-actual treatment mismatch count reconciles to ADTTE-style data;
7. safety remains descriptive;
8. retention preserves hazard direction and exploratory status;
9. the response pack contains exactly SRQ-001–SRQ-005;
10. generated responses contain no configured positive overclaim fragments.

Negative controls deliberately corrupt primary decision reconciliation, the Week 24 denominator, reference-based strategy completeness, fixed-delta comparison coverage, treatment mismatch counts, safety analysis role, retention hazard direction, the review claim, and generated-response overclaim text. These failures are blocking rather than informational.

## Generated evidence

A clean run writes:

```text
outputs/statistical_review_queries.csv
outputs/statistical_review_query_checks.csv
outputs/statistical_review_query_metrics.json
outputs/statistical_review_query_response.md
```

The controlled claim is:

```text
PORTFOLIO_STATISTICAL_REVIEW_RESPONSE_READY
```

## First live validation

GitHub Actions **#651 / run 32774536503** on implementation head `a130bc12f591fcccc989242148698edfd490bc52` completed successfully across the full Python/R/CDISC/MMRM/MI/readiness/closure workflow and the new reviewer-response gate.

The v0.22 metrics from that live artifact were:

- reviewer queries: **5**;
- reviewer-response checks: **10/10 PASS**;
- primary family-wise rejections: **0/2**;
- Week 24 missing: **138/254 (54.3%)**;
- reference-based MCSE: **8/8 PASS**;
- fixed-delta comparison context rows: **2/2**;
- planned/actual treatment mismatches: **12**;
- safety response rows: **2**;
- retention response rows: **2**.

Artifact `clinical-biostatistics-cdisc-outputs`: ID **9537615679**, digest `sha256:561e3c8c50c7697a7306e78018280add24ac89f75c750c753810d3c0488b0b63`.

The post-live-run hardening removes lexical overclaim exceptions and tightens exact MAR/JR/CR/CIR and fixed-delta comparison coverage. The final documentation-inclusive head is revalidated in a separate full clean run before merge.

## Evidence boundary

This is independent public-data portfolio reviewer-response evidence. It is not sponsor/CRO correspondence, a response to a health authority, a sponsor-approved CSR review, medical-writing approval, a benefit-risk decision, database-lock authority, or regulatory/submission readiness.

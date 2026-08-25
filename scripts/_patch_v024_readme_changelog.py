from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
old = "## Current milestone: v0.23 — randomised-assignment consistency repair and population provenance"
if old not in text:
    raise SystemExit("README v0.23 milestone marker not found")
if "## Current milestone: v0.24 — Study Statistician design, safety and governance decision suite" not in text:
    section = r'''## Current milestone: v0.24 — Study Statistician design, safety and governance decision suite

v0.24 is an **additive Study Statistician decision layer** on the validated v0.23 analysis package. It does not replace the primary MMRM, add T26, or convert supportive sensitivity analyses into confirmatory analyses. It closes three distinct gaps: prospective design operating characteristics, purpose-specific safety treatment assignment, and a controlled post-data-review primary-analysis change decision.

The first full live implementation run, Actions **#727 / run 32874178501** on head `6fefbca6aec511133cec330b3d7110d482bdcedb`, passed the complete Python/R/CDISC/MMRM/MI/readiness/change-control/traceability/closure workflow plus all three new v0.24 gates. Its artifact is `clinical-biostatistics-cdisc-outputs`, ID **9573449472**, digest `sha256:c42bbd9a7f6e77d61067f388d5da08676131c7686a79179fd853a3fb8e4e4af5`.

### Prospective design operating characteristics

The controlled planning exercise uses the randomised **86 / 84 / 84** allocation, a correlated longitudinal generator and a Week 24 baseline-adjusted planning approximation with Bonferroni control across the two active-versus-placebo comparisons. It is explicitly **not** claimed to reproduce a sponsor protocol power calculation or a full `mmrm` operating-characteristics engine.

Across five controlled scenarios, each with **2,000 alternative + 2,000 null replicates**:

- under 20% / 35% / 50% MAR dropout, mean observed Week 24 N falls **202.9 -> 165.1 -> 126.9** and probability of at least one primary rejection under the hypothetical -3-point planning alternative falls **65.5% -> 53.2% -> 45.1%**;
- the maximum simulated global-null family-wise error is **0.065**, below the predeclared **0.07** simulation gate;
- under 50% adverse-MNAR stress, the largest observed-analysis bias versus the latent full-data target is approximately **1.054 ACTOT points**;
- design-operating-characteristics QC is **11/11 PASS**;
- controlled claim: **`PORTFOLIO_DESIGN_OPERATING_CHARACTERISTICS_READY`**.

### Safety population and treatment-assignment judgement

The same 12 planned-versus-actual mismatches that require **planned randomised treatment (`TRT01P`)** for v0.23 efficacy MI provide a deliberately different safety question. For this portfolio's exposure-based safety summary, denominators use **actual treatment (`TRT01A`)**.

The live review verifies **254** unique safety subjects, **217** subjects with at least one TEAE and **1,116** TEAE records. It separates subject incidence from event count and reconciles ADAE-style treatment labels back to ADSL-style actual treatment. If planned assignment were incorrectly substituted into this safety question, an arm denominator would shift by up to **12 subjects** and any-TEAE risk by up to **0.0516 (5.16 percentage points)**. Safety-assignment QC is **6/6 PASS** with controlled claim **`PORTFOLIO_SAFETY_POPULATION_ASSIGNMENT_READY`**.

The point is not “planned is right” or “actual is right”; the treatment variable follows the statistical question and analysis-population definition.

### Post-data-review statistical change decision

Controlled decision `SCD-001` asks whether **138/254 = 54.3% Week 24 missingness** should justify replacing the primary MMRM after data review with reference-based MI. The evidence includes complete MAR/JR/CR/CIR sensitivity evidence (**8/8 MCSE-pass rows**) and the unchanged primary Bonferroni conclusion (**0/2 rejected**).

The controlled decision is **`REJECT_PRIMARY_CHANGE`**: retain the primary MMRM and multiplicity family and keep reference-based MI supportive. High missingness warrants sensitivity analysis, but does not by itself justify an outcome-driven promotion of a post-data-review sensitivity method to the confirmatory role. The decision rule is deliberately independent of whether the alternative analysis looks more or less favourable. Change-decision QC is **7/7 PASS** with claim **`PORTFOLIO_STATISTICAL_CHANGE_DECISION_READY`**.

The suite-level contract requires all three v0.24 component claims plus the inherited v0.23 evidence closure before it can emit **`PORTFOLIO_STUDY_STATISTICIAN_DECISION_SUITE_READY`**.

See `docs/study_statistician_design_safety_governance_v0_24.md` for the assumptions, scenario-level results, assignment logic, governance rationale and evidence boundary.

## v0.23 baseline retained under v0.24 — randomised-assignment consistency repair and population provenance'''
    text = text.replace(old, section, 1)
    readme.write_text(text, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
marker = "# Changelog\n\n"
if not text.startswith(marker):
    raise SystemExit("CHANGELOG top marker not found")
if "## 0.24.0 — 2026-08-25" not in text:
    entry = r'''## 0.24.0 — 2026-08-25

- Add a three-part Study Statistician decision suite while retaining the v0.23 primary MMRM, multiplicity decision, T01–T25 registry and controlled evidence closure unchanged.
- Add prospective operating-characteristics stress testing with the controlled 86/84/84 allocation, correlated longitudinal outcome generation, Bonferroni two-comparison family, five MAR/adverse-MNAR dropout scenarios and 2,000 alternative plus 2,000 null replicates per scenario.
- Under the hypothetical -3 ACTOT-point planning alternative, observed Week 24 N decreases **202.9 -> 165.1 -> 126.9** and probability of at least one primary rejection decreases **65.5% -> 53.2% -> 45.1%** across 20%/35%/50% MAR dropout; the largest simulated null FWER is **0.065** and the design QC gate passes **11/11**.
- Keep the design claim bounded: this is a public-portfolio planning stress test using a Week 24 baseline-adjusted approximation, not a sponsor protocol power calculation or a full `mmrm` operating-characteristics engine.
- Add a safety-population assignment audit that deliberately contrasts with v0.23 efficacy MI: this exposure-based safety question uses actual treatment (`TRT01A`), while randomised efficacy missing-data grouping continues to use planned treatment (`TRT01P`).
- Reconcile **254** unique safety subjects, **217** subjects with >=1 TEAE and **1,116** TEAE records; separate subject incidence from event count and verify ADAE-style treatment labels against ADSL-style actual treatment. A diagnostic planned-treatment substitution would shift an arm denominator by up to **12** and any-TEAE risk by up to **0.0516**; safety QC passes **6/6**.
- Add controlled post-data-review decision `SCD-001`: despite **138/254 (54.3%)** Week 24 missingness and complete **8/8** MAR/JR/CR/CIR MCSE-pass evidence, reject replacing the primary MMRM with reference-based MI after data review. Retain the original MMRM/multiplicity family with **0/2** primary rejections and keep RBMI supportive; governance QC passes **7/7**.
- Add suite-level claim `PORTFOLIO_STUDY_STATISTICIAN_DECISION_SUITE_READY`, requiring the design, safety and post-data-review decision claims plus inherited v0.23 evidence closure to pass together.
- First full live implementation Actions **#727 / run 32874178501** on head `6fefbca6aec511133cec330b3d7110d482bdcedb` passes the complete legacy and v0.24 workflow. Artifact **9573449472**, digest `sha256:c42bbd9a7f6e77d61067f388d5da08676131c7686a79179fd853a3fb8e4e4af5`.
- Add `docs/study_statistician_design_safety_governance_v0_24.md`. Evidence remains public-data portfolio evidence only, not a sponsor-approved protocol power calculation, SAP amendment, safety convention for every protocol, health-authority decision or formal ADaM conformance claim.

'''
    text = marker + entry + text[len(marker):]
    changelog.write_text(text, encoding="utf-8")

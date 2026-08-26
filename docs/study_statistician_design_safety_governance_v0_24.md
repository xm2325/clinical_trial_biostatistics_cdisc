# v0.24 Study Statistician decision suite

## Purpose

v0.24 is an additive decision-evidence layer on the validated v0.23 analysis package. It does **not** replace the primary model, create a new TLF, amend a sponsor SAP, or claim regulatory acceptance. It addresses three deliberately different Study Statistician questions:

1. **Prospective design:** how do the planned three-arm efficacy family's operating characteristics degrade as dropout increases, and what does adverse MNAR selection do to the relationship between the observed analysis and the latent full-data target?
2. **Safety population:** when the safety question is exposure-based, why must actual treatment be used even though the v0.23 randomised efficacy missing-data analysis correctly uses planned treatment?
3. **Post-data-review governance:** does high Week 24 missingness justify promoting a supportive reference-based MI analysis to replace the controlled primary MMRM after data review?

The controlled suite claim is `PORTFOLIO_STUDY_STATISTICIAN_DECISION_SUITE_READY` and can pass only when all three v0.24 component claims pass and the inherited v0.23 evidence closure remains complete.

## 1. Prospective design operating characteristics

Controlled claim: `PORTFOLIO_DESIGN_OPERATING_CHARACTERISTICS_READY`.

The simulation uses the controlled allocation of 86 placebo, 84 low-dose and 84 high-dose randomised subjects. A correlated longitudinal generator creates Week 8/16/24 outcomes with within-subject correlation 0.55. The hypothetical planning alternative is -3 ACTOT points at Week 24 for each active arm versus placebo. Family-wise alpha is 0.05 with Bonferroni control across the two active-versus-placebo comparisons.

Each scenario uses 2,000 replicates under the planning alternative and another 2,000 under the global null. The analysis is a Week 24 baseline-adjusted planning approximation. It is intentionally **not** represented as a full `mmrm`-package operating-characteristics engine or as the original protocol's sponsor-approved power calculation.

| Scenario | Mean observed Week 24 N | Low-dose rejection | High-dose rejection | Any rejection | Null FWER | Bias vs latent full-data target, Low / High |
|---|---:|---:|---:|---:|---:|---:|
| 20% MAR dropout | 202.9 | 49.05% | 47.85% | 65.50% | 4.95% | -0.046 / +0.030 |
| 35% MAR dropout | 165.1 | 37.30% | 36.30% | 53.20% | 4.85% | -0.022 / +0.007 |
| 50% MAR dropout | 126.9 | 30.30% | 29.90% | 45.10% | 5.20% | +0.019 / +0.066 |
| 35% adverse MNAR | 165.2 | 38.95% | 40.65% | 56.75% | 5.20% | -0.687 / -0.741 |
| 50% adverse MNAR | 126.9 | 31.50% | 30.80% | 45.40% | 6.50% | -1.021 / -1.054 |

The controlled result is **not** “the trial has 65.5% power”. The result is that, under the stated hypothetical -3-point planning alternative and simplified baseline-adjusted decision model, information loss from increasing dropout materially reduces rejection probability. Under the adverse-MNAR stress, the observed records can also diverge from the latent full-data treatment-effect target by about one ACTOT point even when the observed-data decision model itself is unchanged.

Quality result: **11/11 checks PASS**. The largest simulated null family-wise error across the five scenarios is 0.065, within the predeclared 0.07 simulation gate; all probability Monte Carlo standard errors remain below 0.012.

## 2. Purpose-specific efficacy versus safety treatment assignment

Controlled claim: `PORTFOLIO_SAFETY_POPULATION_ASSIGNMENT_READY`.

v0.23 established that planned randomised treatment (`TRT01P`) is the correct grouping variable for the randomised efficacy missing-data sensitivity analyses. v0.24 deliberately asks a different question: for this portfolio's **exposure-based safety summary**, the denominator follows actual treatment (`TRT01A`).

The live safety review contains:

- 254 unique safety subjects;
- 217 subjects with at least one treatment-emergent adverse event (TEAE);
- 1,116 treatment-emergent AE records;
- 12 safety subjects with `TRT01P != TRT01A`.

The review explicitly separates **subject incidence** from **event count**: a subject contributes at most once to the any-TEAE incidence endpoint, while multiple TEAE records remain valid for event-count summaries.

The planned-treatment calculation is retained only as a diagnostic counterfactual. If planned treatment were silently substituted for actual treatment in this exposure-based safety question, the low/high arm denominators would change by 12 subjects and the any-TEAE risk would shift by up to **0.0516 (5.16 percentage points)**. This is precisely why “always use planned” and “always use actual” are both incorrect rules: treatment assignment must follow the statistical question and analysis population definition.

Quality result: **6/6 checks PASS**, including unique safety denominators, TEAE-subject containment, ADAE-to-ADSL actual-treatment reconciliation, subject-incidence/event-count separation, and reconciliation of the reported risk-difference denominators to unique `SAFFL=Y` subjects grouped by `TRT01A`.

## 3. Post-data-review primary-analysis change decision

Controlled claim: `PORTFOLIO_STATISTICAL_CHANGE_DECISION_READY`.

Controlled proposal `SCD-001` asks:

> Because Week 24 missingness is high, should the primary Week 24 MMRM be replaced after data review by reference-based multiple imputation?

The evidence available to the decision is intentionally uncomfortable rather than selected to make the answer easy:

- Week 24 ACTOT missingness is **138/254 = 54.33%**;
- reference-based MAR/JR/CR/CIR evidence is complete for both comparisons, with **8/8** Monte Carlo precision rows passing;
- the existing Bonferroni primary family still has **0/2** rejected hypotheses;
- the inherited analysis package has already passed evidence closure.

The controlled decision is **`REJECT_PRIMARY_CHANGE`**.

High missingness is a reason to perform and interpret missing-data sensitivity analyses; it is not, by itself, a reason to promote a post-data-review supportive analysis into the confirmatory primary role. The decision therefore retains the controlled primary MMRM and multiplicity family and keeps reference-based MI as supportive sensitivity evidence.

Crucially, the decision rule is outcome-independent. The switch would be rejected under this controlled scenario whether the reference-based estimates looked more or less favourable. That prevents an analysis-role or multiplicity redefinition from becoming an outcome-rescue mechanism.

This exercise does **not** claim that every SAP change is prohibited. A prospectively justified change made before unblinded review could require a different governance process. This is a public portfolio governance exercise, not a sponsor SAP amendment or health-authority interaction.

Quality result: **7/7 checks PASS**.

## 4. Why these three pieces belong together

The three components are intentionally not three variants of the same model:

- **before the trial / before data:** quantify operating characteristics under explicit assumptions;
- **during analysis:** choose treatment assignment and denominators from the estimand/safety question rather than from variable convenience;
- **after data review:** protect the prespecified primary analysis role from outcome-driven redefinition while still using sensitivity analyses to understand uncertainty.

This extends v0.23's defect-discovery story into a broader Study Statistician decision framework without changing the validated primary MMRM, multiplicity conclusion, T01-T25 output set, or the controlled limitation around official ADaM CORE rule availability.

## Evidence boundary

All evidence is generated from a public clinical-trial/CDISC portfolio workflow. The project does not claim sponsor/CRO production experience, a sponsor-approved SAP or CSR, regulatory submission acceptance, or formal ADaM conformance where executable official ADaMIG 1.3 CORE rules are unavailable in the pinned cache.

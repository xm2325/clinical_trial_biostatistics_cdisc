# ACTOT estimand and missing-data review — portfolio v0.11

## Purpose

Version 0.11 makes the scientific target, intercurrent-event handling and missing-data assumptions explicit for the longitudinal ACTOT analysis. The design follows the ICH E9(R1) estimand framework: treatment, population, variable, handling of intercurrent events and population-level summary measure are specified separately from the estimator.

Official framework reference: https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf

> **Evidence boundary:** this is an independent portfolio exercise using public CDISC pilot data. It is not a sponsor-approved estimand, protocol amendment, SAP approval, regulatory analysis decision or evidence of production clinical-trial experience.

## Portfolio estimand

Machine-readable source: `spec/estimands.json`.

**ID:** `EST-ACTOT-W24-TP`

| Attribute | Portfolio specification |
|---|---|
| Treatment | Placebo, Xanomeline Low Dose and Xanomeline High Dose; each active arm compared with placebo |
| Population | Randomised subjects with an observed baseline ACTOT score |
| Variable | ACTOT change from baseline at Week 24 |
| Intercurrent event | Treatment discontinuation |
| Strategy | Treatment policy: retain observed ACTOT outcomes after recorded discontinuation |
| Summary measure | Active-versus-placebo difference in adjusted mean ACTOT change at Week 24 |

Only treatment discontinuation is operationalised as an intercurrent event in this review because it is explicitly represented in the current DS-derived subject data. Rescue medication, treatment switching and other potential intercurrent events are not inferred when the public portfolio inputs do not explicitly support them.

## Estimator and missing-data assumption

The primary estimator is the existing observed-data REML MMRM with treatment-by-visit and baseline-by-visit fixed effects, unstructured within-subject covariance and Satterthwaite degrees of freedom.

The primary MMRM does not create LOCF records. Observed Week 8, Week 16 and Week 24 ACTOT values are used when available, including observed values after treatment discontinuation. Missing post-baseline outcomes are therefore missing observations in the likelihood-based model rather than values filled by the primary analysis.

The portfolio labels the working missing-data assumption as **MAR** conditional on variables represented in the fitted model. MAR is an estimator assumption; it is not one of the five estimand attributes. The descriptive missingness review does not prove that MAR is true.

The existing Week 24 LOCF ANCOVA is retained only as a supportive legacy-style stress test. It is not the primary estimator and is not presented as preferred missing-data handling under ICH E9(R1).

## Executable missingness review

`python scripts/run_estimand_review.py` creates:

- `outputs/table16_actot_missingness_by_visit.csv` — arm-by-visit target N, observed N, missing N/%, discontinuation timing decomposition and observed post-discontinuation counts;
- `outputs/actot_missingness_patterns.csv` — subject-level Week 8/16/24 observed/missing pattern;
- `outputs/table17_week24_missingness_by_disposition.csv` — disposition context among subjects missing Week 24 ACTOT;
- `outputs/estimand_review.csv` — blocking consistency checks;
- `outputs/estimand_metrics.json` and `outputs/estimand_summary.md` — machine-readable and reviewer-facing evidence.

The denominator for T16/T17 is the portfolio target population operationalisation: randomised subjects with an observed baseline ACTOT score. This is deliberately broader than the observed longitudinal MMRM rows, because a missing outcome should remain visible in the missingness denominator rather than disappear from review.

## Blocking consistency checks

The v0.11 gate requires the following types of conditions to pass:

1. the machine-readable estimand contains all five attributes and valid ICH strategy labels;
2. the target treatment conditions reconcile to the three portfolio arms;
3. the primary estimator is MMRM, does not use LOCF and explicitly records its MAR assumption;
4. every arm-by-visit missingness cell reconciles `observed + missing = target`;
5. missing subjects decompose into those with and without recorded discontinuation before/on the visit;
6. Week 24 disposition-reason counts reconcile to Week 24 missing counts;
7. the MMRM contains exactly the eligible observed ACTOT Week 8/16/24 records used by its current code path;
8. observed post-discontinuation ACTOT records are retained under the treatment-policy strategy;
9. the primary MMRM contains no LOCF rows.

Negative-control unit tests deliberately make LOCF the primary estimator, remove a post-discontinuation observation from the MMRM and corrupt a missingness denominator. Each defect must be rejected.

## Interpretation limits

The missingness tables describe the observed public dataset. They do not establish that missingness is ignorable, that MAR is clinically plausible, or that treatment-policy is the estimand that the source trial originally intended. Those are study-specific scientific decisions that require protocol context and sponsor/statistical agreement.

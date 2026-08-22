# Protocol statistical review checklist

This checklist is a portfolio review aid for translating a clinical protocol into an executable Statistical Analysis Plan and analysis programme. It does not represent sponsor or regulatory approval experience.

## Study design

| Review item | Minimum statistical question before sign-off |
|---|---|
| Design | Is the design parallel, crossover, cluster, adaptive or otherwise, and is the analysis aligned to that design? |
| Treatment arms | Are all treatment groups, control groups and planned comparisons unambiguous? |
| Allocation | Is the randomisation ratio stated and consistent with the sample-size calculation? |
| Stratification | Are randomisation strata defined and is their planned use in analysis stated? |
| Blinding | Are blinded/unblinded responsibilities and data flows clear? |
| Visit schedule | Are endpoint assessment windows and analysis visits defined sufficiently for programming? |

## Objectives, endpoints and estimands

| Review item | Minimum statistical question before sign-off |
|---|---|
| Primary objective | Does each primary objective map to a single primary endpoint and treatment contrast? |
| Endpoint definition | Are variable, scale, unit, direction, timepoint and derivation clear? |
| Baseline | Is baseline defined when multiple pre-treatment assessments are possible? |
| Population | Which subjects contribute to each primary and secondary analysis? |
| Intercurrent events | How are discontinuation, rescue treatment, treatment switching, death or other relevant events handled? |
| Missing data | Is the primary missing-data strategy aligned to the clinical question and estimand? |
| Sensitivity analyses | Do sensitivity analyses address departures from the primary assumptions rather than merely repeat the same analysis? |

A protocol can name an endpoint without providing enough information to program it. Ambiguous baseline, windowing, intercurrent-event or missing-data rules should be resolved before SAP/TLF finalisation.

## Hypotheses and multiplicity

Check that every inferential objective states:

- null and alternative hypotheses or an equivalent treatment contrast;
- one-sided or two-sided testing;
- alpha level;
- the family of hypotheses requiring multiplicity control;
- the testing procedure and order, if hierarchical;
- how confidence intervals correspond to the testing strategy.

For the v0.7 portfolio planning example, two active-versus-placebo comparisons use family-wise two-sided alpha 0.05 with Bonferroni alpha 0.025 per comparison. This is an illustrative design rule, not a claim about the source trial.

## Sample size and power

Before accepting a sample-size section, verify that the calculation explicitly states:

1. endpoint type and planned statistical test/model;
2. treatment effect used for planning;
3. variance, event rate or other nuisance assumptions;
4. alpha and multiplicity adjustment;
5. target power;
6. allocation ratio;
7. evaluable sample size;
8. inflation for dropout/non-evaluability;
9. total randomised sample size;
10. source or clinical rationale for key assumptions.

The calculation should be reproducible from those inputs. `spec/protocol_design.json` and `scripts/run_protocol_design.py` demonstrate this requirement for the portfolio continuous-endpoint scenario.

## Statistical model

For each planned model, confirm:

- response variable and scale;
- fixed effects and covariates;
- interactions;
- repeated or random-effects structure where applicable;
- reference levels;
- estimation method;
- degrees-of-freedom method;
- covariance structure and any sensitivity covariance;
- treatment contrasts;
- confidence-interval level;
- model-failure or non-convergence handling.

For longitudinal outcomes, the protocol should not simply state "MMRM". Visit handling, baseline adjustment, covariance assumptions and estimand implications must be clear enough for the SAP and programming specifications.

## Analysis populations

Check that each population has an executable rule and that apparent clinical wording can be translated into data conditions. Typical issues include:

- randomised but never treated subjects;
- wrong-treatment subjects;
- subjects without baseline;
- subjects without post-baseline efficacy data;
- major protocol deviations;
- ambiguous treatment assignment for safety summaries.

Population definitions should then reconcile with analysis dataset flags and TLF denominators.

## Safety analysis

Verify:

- treatment-emergent window;
- treatment exposure boundaries;
- partial/missing date rules;
- severity and relatedness categories;
- serious adverse-event definition;
- subject-level incidence versus event counts;
- denominator population;
- coding dictionary/version when relevant;
- planned summaries and inferential comparisons, if any.

## Data and programming implications

Before final SAP/TLF programming begins, check that the protocol supports:

- source-to-analysis mapping for all endpoints;
- required visit windows;
- analysis flags;
- derivation ordering;
- treatment and population variables;
- shell denominators and display precision;
- traceability from source records to analysis values;
- independent or separate-program QC strategy where required.

The portfolio's `spec/analysis_traceability.csv` and `spec/output_contracts.json` provide executable examples of the final two items.

## DSMB / interim analyses

If a study includes an interim analysis or independent data monitoring committee, the protocol/statistical documentation should define at minimum:

- timing or information fraction;
- unblinded access rules;
- statistical boundaries or decision criteria;
- data snapshot and transfer process;
- who receives unblinded outputs;
- separation of blinded and unblinded programming/statistical responsibilities;
- impact of interim review on type-I error and final analysis.

This portfolio does not claim DSMB or unblinded production responsibility; the checklist records what would need to be specified and reviewed.

## Sign-off blockers

A statistical reviewer should not treat a protocol section as analysis-ready when any primary endpoint lacks an executable definition, the hypothesis family and alpha are inconsistent with the sample-size calculation, population rules cannot be programmed, missing-data/intercurrent-event handling is undefined, or planned TLFs cannot be traced back to the stated objectives and analyses.

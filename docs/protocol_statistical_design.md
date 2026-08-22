# Protocol statistical design — portfolio version 0.7

## Purpose

This document demonstrates how a biostatistician can translate a protocol objective into explicit planning assumptions, multiplicity control, sample-size calculations and reproducible design QC.

It is an independent portfolio design exercise. It is **not** the source study protocol, a sponsor-approved statistical section, or a claim about the original trial's sample-size assumptions.

## 1. Planning question

The illustrative design is a three-arm parallel-group study with:

- Placebo;
- Xanomeline Low Dose;
- Xanomeline High Dose.

The planning endpoint is **Week 24 ACTOT change from baseline**. Each active arm is compared with placebo.

The machine-readable source of truth is `spec/protocol_design.json`.

## 2. Estimand-style planning statement

For planning purposes, the target contrast is the difference in mean Week 24 ACTOT change from baseline between each active dose and placebo in the planned analysis population.

This portfolio sample-size calculation does not attempt to encode a complete ICH E9(R1) estimand. Intercurrent-event handling, rescue medication, treatment discontinuation and missing-data strategy would need protocol-specific clinical definitions before a confirmatory design could be finalised.

## 3. Multiplicity

There are two active-versus-placebo comparisons. The portfolio design controls a two-sided family-wise alpha of 0.05 using a Bonferroni split:

```text
alpha_per_comparison = 0.05 / 2 = 0.025
```

This is deliberately simple and auditable. A real programme could instead use a hierarchical procedure, Dunnett adjustment or another pre-specified multiple-testing strategy if justified by the clinical objectives.

## 4. Planning assumptions

The illustrative assumptions are:

| Assumption | Value |
|---|---:|
| Allocation | 1:1:1 |
| Continuous endpoint | Week 24 ACTOT change from baseline |
| Common SD | 6.0 |
| Family-wise two-sided alpha | 0.05 |
| Active-versus-placebo comparisons | 2 |
| Per-comparison alpha | 0.025 |
| Anticipated dropout | 15% |
| Target powers | 80%, 90% |
| Mean-difference scenarios | 2.0, 2.5, 3.0 points |

These values are planning scenarios, not retrospective claims about the original study design. The calculations do not use the observed treatment estimate as a prospective design input.

## 5. Sample-size method

For an equal-allocation two-arm comparison of a continuous mean difference, the portfolio uses the normal approximation:

```text
n_evaluable_per_arm = ceil(
    2 * SD^2 * (z_(1-alpha/2) + z_power)^2 / effect^2
)
```

The evaluable per-arm requirement is then inflated for anticipated dropout:

```text
n_randomised_per_arm = ceil(n_evaluable_per_arm / (1 - dropout_rate))
```

Because the planned design has three equal-sized arms:

```text
total_randomised = 3 * n_randomised_per_arm
```

The code then back-calculates achieved power at the rounded evaluable sample size. This catches mistakes where a rounded or transformed sample size would fail to meet the requested target.

## 6. Reproducible outputs

`python scripts/run_protocol_design.py` reads only the machine-readable design specification and writes:

- `outputs/protocol_design_scenarios.csv` — scenario-level assumptions and calculated sample sizes;
- `outputs/protocol_design_qc.csv` — required design checks;
- `outputs/protocol_design_metrics.json` — compact metrics plus SHA256 of the design specification;
- `outputs/protocol_design_summary.md` — reviewer-readable summary.

The design specification hash makes the generated calculation traceable to the exact set of assumptions used for the run.

## 7. Required design QC

The executable QC requires all of the following:

1. Bonferroni per-comparison alpha exactly reconciles to family alpha divided by the number of comparisons;
2. dropout adjustment cannot reduce the sample size;
3. achieved power at the rounded evaluable N meets or exceeds target power;
4. scenario IDs are unique;
5. total randomised N reconciles to per-arm N multiplied by the number of arms;
6. required N cannot increase when the assumed treatment effect becomes larger at fixed target power;
7. required N cannot decrease when target power increases at fixed treatment effect.

A required failure exits non-zero in GitHub Actions.

## 8. Interpretation boundary

This module demonstrates protocol-design reasoning and reproducible sample-size programming. It does not establish that the assumptions are clinically justified. In production work, effect size, variance, dropout, estimand, multiplicity strategy and analysis model would be agreed from clinical evidence, prior studies, programme objectives and regulatory strategy before the design is finalised.

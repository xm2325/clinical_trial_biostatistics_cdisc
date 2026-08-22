# QC plan — portfolio version 0.14

The workflow uses separate blocking QC layers for derivation, public-reference checks, R/Python replication, repeated-measures modelling, estimand/missing-data review, deterministic sensitivity, subject-level MI, reference-based MI, reviewer checks, change impact and final TLF traceability. A required failure exits non-zero.

## QC stack

The current live workflow checks:

1. Python unit tests and core derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. protocol-design and randomisation/initial-kit QC;
4. separate R reconstruction and R/Python comparison;
5. ACTOT MMRM data/model/inference QC;
6. estimand and missing-data review;
7. v0.12 deterministic fixed-delta sensitivity QC;
8. v0.13 subject-level MI model/pooling/delta QC;
9. independent v0.13 MI Monte Carlo precision QC;
10. v0.14 reference-based MI ICE/model/pooling/MCSE QC;
11. analysis-dataset/TLF reviewer;
12. statistical change-control impact gate;
13. versioned T01-T22 structural traceability.

## Reference-based MI QC

`R/rbmi_reference_based.R` reads the same generated ADSL-style and ACTOT analysis data used by the existing estimand and MI layers.

The v0.14 required checks include:

- installed `rbmi` version equals 1.6.1;
- v0.13 MI base specification remains the controlled parent model;
- target population remains 254 randomised subjects with baseline ACTOT;
- scheduled ACTOT subject-visit rows are unique;
- existing estimand review reports zero observed ACTOT after recorded discontinuation;
- strategies are exactly MAR, JR, CR and CIR;
- 200 imputations are retained;
- every active discontinuer has usable `TRTSDT`/`EOSDT` timing;
- actual-date post-discontinuation ACTOT count is zero (`ADT > EOSDT`);
- observed ACTOT on/after the first affected visit used for strategy switching is zero;
- each pairwise model returns 200 draws and remains within the 10% model-failure limit;
- the output contains 2 comparisons × 4 strategies = 8 rows;
- pooled estimates/inference are finite;
- all analyses use Rubin pooling;
- all eight rows pass `MCSE(estimate) / pooled SE <= 0.075`.

The successful v0.14 core/formalisation runs passed **27/27** required reference-based checks. Both pairwise models had zero model-fit failures. The maximum reference-based MCSE ratio was **0.053811**.

## ICE timing guard

The reference-based analysis deliberately has two separate timing checks.

The first is an actual-date estimand-alignment check:

```text
observed scheduled ACTOT with ADT > EOSDT == 0
```

The second is the visit-level condition needed before MAR/non-MAR strategy switching:

```text
observed ACTOT on/after the first affected scheduled visit == 0
```

These checks answer different questions and neither replaces the other.

The first live v0.14 implementation used `TRTEDT` as the ICE date and failed the visit-level guard. The implementation was corrected to `EOSDT`, which is the discontinuation timing already used by the project estimand review. The guard was not removed or relaxed.

## T22 traceability evidence

T22 requires all of the following in the same live run:

- `outputs/table22_rbmi_reference_based.csv`;
- `outputs/rbmi_reference_ice_audit.csv`;
- `outputs/estimand_review.csv`;
- `outputs/rbmi_reference_qc.csv`;
- `outputs/rbmi_reference_mcse_qc.csv`;
- `outputs/rbmi_reference_draw_diagnostics.csv`.

The final traceability validator also checks the T22 required columns, minimum 8 rows and SHA256 output identity.

## Change-control QC

The v0.14 graph/request specifications both declare version `0.14.0`. Eight simulated requests are assessed.

The verified machine result is **195/195 required impact relationships declared and 195/195 required resources resolved**, with zero missing declarations, zero extra declarations and zero unresolved required resources.

Important negative controls require failure when T22 or its reference-based QC evidence is omitted from an upstream change that should reach it.

## Traceability version QC

`spec/analysis_traceability.csv` contains `registry_version`. Every TLF row must declare one identical non-empty version. `traceability_metrics.json` derives `analysis_version` from this field rather than a hard-coded constant.

This rule was added after the v0.14 formalisation artifact exposed a stale historical `0.6.0` value in otherwise successful 22-TLF metrics.

## Evidence boundary

These checks are portfolio QC. Same-author R/Python replication is not independent second-programmer validation, and successful reference-based MI QC is not sponsor approval of an MNAR strategy.

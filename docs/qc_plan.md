# QC plan — portfolio version 0.17

The workflow uses separate blocking QC layers for derivation, public-reference checks, R/Python replication, repeated-measures modelling, cross-package MMRM validation, primary multiplicity control, estimand/missing-data review, deterministic sensitivity, subject-level MI, reference-based MI, ADTTE-style retention derivation, survival analysis, reviewer checks, statistical change impact and final TLF traceability. A required failure exits non-zero.

## QC stack

The current live workflow checks:

1. Python unit tests and source-to-analysis derivation QC;
2. official CDISC efficacy-reference structure/source trace;
3. **v0.17 ADTTE-style randomized-retention derivation QC**;
4. protocol-design and randomisation/initial-kit QC;
5. separate R reconstruction and R/Python comparison;
6. ACTOT MMRM data/model/inference QC;
7. v0.16 primary MMRM cross-package validation;
8. **v0.17 randomized-arm Kaplan–Meier/log-rank/Cox retention QC**;
9. v0.15 primary multiplicity QC;
10. estimand and missing-data review;
11. v0.12 deterministic fixed-delta sensitivity QC;
12. v0.13 subject-level MI model/pooling/delta QC;
13. independent v0.13 MI Monte Carlo precision QC;
14. v0.14 reference-based MI ICE/model/pooling/MCSE QC;
15. analysis-dataset/TLF reviewer;
16. **v0.17 versioned statistical change-control impact gate**;
17. versioned **T01–T25** structural traceability.

The workflow also uses branch/event concurrency with `cancel-in-progress: true`, so superseded upgrade commits no longer consume a full long-running MI pipeline.

## v0.17 ADTTE-style retention derivation

`python scripts/run_tte_retention.py` reads the generated ADSL-style dataset and `spec/tte_retention.json` and derives one `TTDISC` row per randomized subject.

The analysis assignment is explicitly locked to planned randomized treatment:

```text
ANLTRT = TRT01P
```

Actual treatment (`TRT01A`) is retained as context. `TRTDIFFL` records planned-versus-actual treatment differences. This distinction is blocking because the live public data contain **12/254** randomized subjects with `TRT01P != TRT01A`; all 12 are planned High Dose subjects recorded as actual Low Dose.

The 16 blocking derivation checks require:

- non-empty randomized population;
- all three planned treatment arms;
- one row per subject;
- `ANLTRT` follows the configured planned randomized assignment variable;
- `TRTDIFFL` exactly reproduces planned/actual differences;
- complete treatment origin/end dates;
- mutually exclusive and exhaustive discontinuation/completion status;
- positive analysis duration;
- exact `AVAL = ADT - STARTDT + 1`;
- `CNSR` restricted to 0/1;
- discontinuation events map to `CNSR=0`;
- protocol completion maps to `CNSR=1`;
- non-empty event/censor descriptions;
- event source trace follows the specification;
- censor source trace follows the specification.

The validated live result is:

- subjects: **254**;
- events: **144**;
- censors: **110**;
- planned arm counts: Placebo **86**, Low Dose **84**, High Dose **84**;
- planned/actual mismatch subjects: **12**;
- required derivation QC: **16/16 PASS**.

The metrics artifact records SHA256 fingerprints for the exact TTE specification, ADSL-style source and ADTTE-style output.

## v0.17 survival-analysis QC

`R/tte_retention_analysis.R` independently verifies that the ADTTE-style dataset retains the randomized assignment contract before fitting survival models. All KM/log-rank/Cox analyses use `ANLTRT`, not `TRT01A`.

T24 reports Kaplan–Meier retention at days 56, 112, 168 and 182. T25 reports Low Dose vs Placebo and High Dose vs Placebo exploratory log-rank/Cox summaries. Cox models use Efron ties; `cox.zph` is reported as a proportional-hazards diagnostic.

The 14 blocking survival checks cover:

- three randomized arms and unique subject rows;
- `ANLTRT == TRT01P`;
- exact `TRTDIFFL` audit flag;
- positive finite TTE values and valid censor codes;
- presence of both events and censored observations;
- complete KM arm × timepoint rows;
- bounded finite KM probabilities/confidence limits;
- non-increasing KM survival;
- exactly two active-vs-placebo comparisons;
- finite positive Cox HR/confidence intervals;
- valid Cox/log-rank p-values;
- available valid `cox.zph` diagnostic p-values.

The validated run passes **14/14** checks. Day-182 KM retention is **67.44% / 29.76% / 33.25%** for Placebo / Low / High. Exploratory HRs are **3.0852** and **2.9246**; `cox.zph` p-values are **0.8310** and **0.7577**, so the run has **0/2** PH diagnostic signals at alpha 0.05.

A PH diagnostic signal would not itself fail the pipeline; it would limit interpretation of the Cox HR. The endpoint remains exploratory and is not part of the ACTOT multiplicity family.

## v0.16 MMRM cross-package validation

`R/mmrm_cross_package_qc.R` independently reconstructs the observed ACTOT longitudinal rows from `outputs/adqs_actot_style.csv` instead of reading the primary MMRM analysis dataset. It fits the same fixed-effects mean model with `nlme::gls`, using `corSymm + varIdent` for a general unstructured marginal covariance.

The validated gate has **451/451** rows, **189/189** subjects, zero missing/extra keys, zero exact-field mismatches and zero numeric mismatch rows. It passes **18/18** required checks. Maximum estimate absolute difference is **1.30015e-05** and maximum SE absolute difference is **2.63230e-06**, against locked **0.0005** tolerances.

Degrees of freedom and p-values are deliberately not compared because the primary `mmrm` model uses Satterthwaite inference.

## Primary multiplicity QC

`python scripts/run_multiplicity.py` reads the primary MMRM contrasts and `spec/multiplicity.json`, then cross-checks the family against `spec/protocol_design.json`.

The 12 required checks enforce the two Week 24 primary active-versus-placebo hypotheses, family alpha 0.05, Bonferroni local alpha 0.025, exact hypothesis mapping, finite valid inference fields, adjusted-p formula and reject-flag consistency.

The validated result passes **12/12** checks. H_LOW raw p=0.169334 gives adjusted p=0.338669; H_HIGH raw p=0.421970 gives adjusted p=0.843940. Neither hypothesis is rejected family-wise.

T24/T25 are explicitly excluded from this family.

## Reference-based MI QC

The v0.14 reference-based layer remains blocking. Its timing guards prevent invalid use of observations after recorded discontinuation / affected visits. The validated analysis passes **27/27** required checks, uses 200 imputations per pairwise model and requires `MCSE(estimate) / pooled SE <= 0.075`; maximum observed ratio is **0.053811**.

## Change-control QC

The v0.14 base graph/request files remain byte-preserved. v0.15 adds multiplicity, v0.16 adds cross-package MMRM validation, and v0.17 adds a separate retention-TTE chain:

```text
tte_retention_definition
  -> tte_retention_derivation
  -> tte_retention_survival_analysis
  -> tte_retention_tlfs (T24/T25)
```

CR-011 simulates a change to the retention population, randomized analysis assignment, origin/end dates, event/censor rules, KM timepoints or exploratory survival specification.

The validated merged assessment covers:

- **11** simulated change requests;
- **77** propagated component links;
- **267/267** required impact relationships declared;
- **267/267** required resources resolved;
- zero missing required declarations;
- zero extra declared resources;
- zero unresolved required resources.

CR-011 itself requires **13** downstream impact relationships and affects T24/T25 only; it does not propagate into the ACTOT confirmatory family.

## Traceability version QC

`spec/analysis_traceability.csv` contains one common `registry_version`. v0.17 advances the controlled registry to **T01–T25 / 0.17.0**.

The validated structural gate passes:

- outputs found: **25/25**;
- output contracts: **25/25**;
- analysis-data links: **25/25**;
- QC-evidence links: **25/25**;
- complete structural traceability: **25/25**.

T24/T25 require both ADTTE-style derivation evidence and survival QC. T23 continues to use the controlled primary `mmrm` inference plus multiplicity QC and does not absorb the exploratory retention endpoint.

## Evidence boundary

These checks are portfolio QC. The v0.17 ADTTE-style dataset is not claimed to be formal submission-ready ADaM, and T24/T25 are not sponsor-approved efficacy or confirmatory endpoints. Same-author cross-package/programming checks are not formal independent second-programmer validation.
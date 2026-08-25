# v0.23 randomised-treatment assignment consistency repair

## Why this is a repair rather than a new analysis feature

The public pilot data contain **254 randomised subjects**. Planned randomised treatment (`TRT01P`) is balanced as:

- Placebo: **86**;
- Xanomeline Low Dose: **84**;
- Xanomeline High Dose: **84**.

Actual treatment (`TRT01A`) among those same randomised subjects is:

- Placebo: **86**;
- Xanomeline Low Dose: **96**;
- Xanomeline High Dose: **72**.

The difference is caused by **12/254 planned-versus-actual treatment mismatches**, all with planned High Dose and actual Low Dose.

Earlier versions already retained this issue explicitly for the exploratory retention analysis. v0.23 found a second consequence: the subject-level and reference-based `rbmi` sensitivity analyses built their 254-subject target from `TRT01A`. Because all 12 mismatched subjects require missing-data handling, this changed the imputation-group population itself.

This is therefore treated as a statistical analysis-definition repair under **CR-015**, not as code cleanup or a cosmetic portfolio enhancement.

## Why the observed primary MMRM is not numerically changed

The controlled population audit shows:

- total subjects: **306**;
- randomised subjects: **254**;
- randomised subjects with baseline ACTOT: **254**;
- observed primary MMRM subjects: **189**;
- randomised baseline subjects with no observed Week 8/16/24 ACTOT: **65**;
- Week 24 observed / missing: **116 / 138**;
- planned/actual mismatch subjects entering the observed primary MMRM: **0/12**.

All 12 assignment-mismatch subjects are among the randomised baseline subjects with no observed post-baseline ACTOT. The current primary MMRM therefore has no row whose treatment grouping changes under the repair. v0.23 nevertheless adds a blocking guard: if a future data refresh causes any `TRT01P != TRT01A` subject to enter the observed primary MMRM, the assignment gate fails rather than silently assuming the current situation still holds.

## What changes for missing-data sensitivity

Before v0.23, the `rbmi` target used actual-treatment grouping:

```text
actual-treatment target
Placebo = 86
Low     = 96
High    = 72

Low vs Placebo pair target  = 182
High vs Placebo pair target = 158
```

v0.23 stages an MI-specific planned-assignment view:

```text
planned-randomisation target
Placebo = 86
Low     = 84
High    = 84

Low vs Placebo pair target  = 170
High vs Placebo pair target = 170
```

The original ADSL-/ADQS-style files remain the source of actual-treatment provenance. Before T20/T21/T22 execute, v0.23 creates:

```text
outputs/adsl_mi_planned.csv
outputs/adqs_actot_mi_planned.csv
```

The MI-specific copies:

- retain the original actual treatment in `TRT01A_ACTUAL`;
- retain planned treatment in `TRT01P`;
- set the existing `TRT01A` grouping field to planned randomised treatment only for the temporary `rbmi` execution boundary;
- record `MI_ASSIGNMENT_SOURCE=TRT01P`.

This lets the existing R `rbmi` implementation remain unchanged while making the treatment-assignment source explicit and auditable. The original analysis files are byte-backed-up before MI and restored before the generic analysis-dataset reviewer, readiness, change-control and evidence-closure stages run.

## First live repair evidence

Actions **#673 / run 32850380975** on repair head `876a474b27ae153fc0eaee99d652052be5c56976` completed the full Python/R/CDISC/MMRM/MI/readiness/closure/reviewer-response workflow successfully.

The v0.23 assignment gates passed:

- input assignment checks: **10/10**;
- post-MI assignment checks: **4/4**;
- planned randomised counts: **86 / 84 / 84**;
- actual-treatment counts: **86 / 96 / 72**;
- assignment mismatches: **12**;
- mismatch subjects in observed primary MMRM: **0**;
- executed pairwise MI target counts: **170 / 170**;
- reference-based strategy rows: **8/8**;
- reference-based MCSE passes: **8/8**.

Artifact: `clinical-biostatistics-cdisc-outputs`, ID **9564218814**, digest `sha256:43da7360a86da6647ca8cb69442b883a884557d9551414ba5a92bbef51cde1e4`.

## Numerical effect of the repair

The repair changes the sensitivity-analysis population but does **not** reverse the controlled statistical interpretation.

### MAR pairwise MI

| Comparison | Before v0.23 | After planned-assignment repair | After-repair SE | After-repair p |
|---|---:|---:|---:|---:|
| Low Dose vs Placebo | -1.4966 | **-1.5397** | 1.2754 | 0.2313 |
| High Dose vs Placebo | -0.6874 | **-0.7237** | 1.1078 | 0.5154 |

Both remain non-significant supportive sensitivity results.

### Delta sensitivity

For Low Dose versus Placebo, the controlled scenarios move from:

```text
MAR            -1.4966 -> -1.5397
Active +1      -0.7786 -> -0.8615
Active +2      -0.0606 -> -0.1833
Divergent +1   -0.4630 -> -0.5464
```

For High Dose versus Placebo:

```text
MAR            -0.6874 -> -0.7237
Active +1      -0.1011 -> -0.0765
Active +2       0.4853 ->  0.5707
Divergent +1    0.2036 ->  0.2312
```

The qualitative sensitivity story is unchanged: stronger adverse MNAR shifts can move the High Dose comparison through zero, so sensitivity evidence must not be labelled simply as fully robust.

### Reference-based MI

All eight MAR/JR/CR/CIR rows remain Monte Carlo-precision acceptable. The most important composition correction is visible in the discontinuation/ICE counts:

```text
Low active discontinuers:  71 -> 59
Low active ICE subjects:   68 -> 56
High active discontinuers: 45 -> 57
High active ICE subjects:  39 -> 51
```

The 12-subject movement from Low to High is exactly the planned High / actual Low mismatch issue being corrected.

Selected after-repair estimates are:

| Comparison | MAR | JR | CR | CIR |
|---|---:|---:|---:|---:|
| Low vs Placebo | -1.5397 | -0.5292 | -0.2464 | -0.3415 |
| High vs Placebo | -0.7237 | -0.3394 | -0.1930 | -0.1626 |

All remain supportive sensitivity evidence rather than confirmatory inference.

## Population-provenance artifact

`outputs/analysis_population_provenance.csv` gives a subject-level audit trail containing:

- planned and actual treatment;
- randomisation and safety flags;
- assignment-mismatch flag;
- baseline ACTOT availability;
- primary-MMRM inclusion;
- Week 8 / Week 16 / Week 24 observed flags;
- Week 24 missing flag;
- controlled population status.

This makes the denominator transition inspectable at subject level instead of relying only on aggregate prose.

## Change control

**CR-015 — Randomised treatment-assignment source correction for efficacy missing-data sensitivity analyses** propagates to:

- the treatment-assignment/estimand specification;
- planned-assignment MI input construction;
- T20/T21 subject-level MI sensitivity;
- T22 reference-based MI sensitivity;
- assignment/population QC and post-execution audit;
- the current observed-primary-MMRM mismatch guard.

No new TLF is invented. The executable registry remains **T01–T25**; CR-015 requires T20–T22 to be regenerated under the corrected assignment rule.

## Evidence boundary

This is independent public-data portfolio evidence. It demonstrates detection, correction and controlled propagation of a statistical assignment-source issue. It is not a sponsor-approved SAP amendment, formal GCP change-control record, health-authority response, validated production release or regulatory-submission decision.

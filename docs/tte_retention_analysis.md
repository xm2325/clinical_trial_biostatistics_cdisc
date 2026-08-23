# Exploratory time-to-study-discontinuation analysis — v0.17

## Purpose

v0.17 adds an ADTTE-style BDS exercise for trial retention using public portfolio data. The endpoint is **time from first treatment date to study discontinuation or protocol completion**. It is an exploratory operational/retention endpoint, not an efficacy endpoint and not part of the ACTOT primary multiplicity family.

## Randomized analysis assignment

The survival comparison follows planned randomized assignment:

```text
ANLTRT = TRT01P
```

Actual treatment (`TRT01A`) is retained only as treatment context. `TRTDIFFL` explicitly records whether planned and actual treatment differ.

This distinction is material in the public data. Among **254** randomized subjects, **12** have `TRT01P != TRT01A`: all 12 were planned High Dose and recorded as actual Low Dose. Using actual treatment would produce arm sizes 86/96/72; using randomized assignment gives 86/84/84. The v0.17 analysis therefore preserves the randomized comparison and audits the 12 treatment differences instead of reclassifying those subjects.

## Derivation

One `TTDISC` record is created per randomized subject in Placebo, Xanomeline Low Dose and Xanomeline High Dose.

- `STARTDT`: ADSL-style `TRTSDT`;
- `ADT`: ADSL-style `EOSDT`;
- `AVAL = ADT - STARTDT + 1` days;
- `DCSFL=Y`: study-discontinuation event, `CNSR=0`;
- `COMPLFL=Y`: censored at protocol completion, `CNSR=1`;
- `EVNTDESC`: discontinuation reason for events, `STUDY COMPLETED` for protocol-completion censors;
- `ANLTRTSRC`: source of randomized analysis treatment;
- `CNSRSRC`: source of event/censor status;
- `EVNTSRC`: source of event/censor description.

The implementation is specification-driven: treatment variables, event/censor status variables, event-description sources and fallback source come from `spec/tte_retention.json` rather than being hard-coded in the derivation.

The validated derivation contains:

| Randomized arm | Subjects | Events | Censored |
|---|---:|---:|---:|
| Placebo | 86 | 28 | 58 |
| Xanomeline Low Dose | 84 | 59 | 25 |
| Xanomeline High Dose | 84 | 57 | 27 |
| **Total** | **254** | **144** | **110** |

The derivation gate passes **16/16** blocking checks. It also records SHA256 fingerprints for the TTE specification, ADSL-style source and generated ADTTE-style dataset.

## Kaplan–Meier analysis — T24

`R/tte_retention_analysis.R` uses `survival::survfit` and independently re-checks that `ANLTRT == TRT01P` before fitting the model.

Retention probabilities with log-log 95% confidence intervals are reported at days 56, 112, 168 and 182:

| Day | Placebo | Low Dose | High Dose |
|---:|---:|---:|---:|
| 56 | 0.8837 | 0.7024 | 0.6786 |
| 112 | 0.8140 | 0.4762 | 0.4167 |
| 168 | 0.6860 | 0.3095 | 0.3810 |
| 182 | **0.6744** | **0.2976** | **0.3325** |

Median TTDISC is not reached for Placebo. It is **105 days** for Low Dose (95% CI 69–119) and **80 days** for High Dose (95% CI 64–146).

## Pairwise survival diagnostics — T25

T25 contains exploratory active-versus-placebo log-rank and Cox summaries. Cox models use Efron ties.

| Comparison | Hazard ratio | 95% CI | Cox p | Log-rank p | `cox.zph` p |
|---|---:|---:|---:|---:|---:|
| Low Dose vs Placebo | **3.0852** | 1.9606–4.8548 | 1.0e-06 | 3.11e-07 | 0.8310 |
| High Dose vs Placebo | **2.9246** | 1.8557–4.6092 | 4.0e-06 | 1.31e-06 | 0.7577 |

HR > 1 means a higher **study-discontinuation hazard** than placebo. It must not be described as lower efficacy.

`cox.zph` is reported for proportional-hazards diagnostics. The validated run has **0/2** signals at alpha 0.05. A future diagnostic signal would not itself fail the pipeline; it would limit interpretation of the Cox HR while leaving KM and log-rank results visible.

No multiplicity adjustment is applied to T25 because it is explicitly exploratory. T24/T25 are not incorporated into the controlled ACTOT Week 24 Bonferroni family.

## Blocking survival QC

The R survival layer passes **14/14** required checks, covering randomized-arm identity, planned/actual mismatch audit consistency, one row per subject, positive finite times, censor coding, event/censor presence, KM completeness/bounds/monotonicity, pairwise comparison count, valid Cox estimates, valid p-values and available PH diagnostics.

## Traceability

Controlled sources and outputs:

```text
outputs/adsl_style.csv
  -> outputs/adtte_retention_style.csv
  -> outputs/adtte_retention_qc.csv
  -> outputs/adtte_retention_metrics.json
  -> R survival analysis
  -> outputs/table24_retention_km.csv
  -> outputs/table25_retention_pairwise.csv
  -> outputs/tte_retention_survival_qc.csv
  -> outputs/tte_retention_survival_metrics.json
```

T24 and T25 are registered at `registry_version=0.17.0` and both pass executable output contracts, analysis-dataset links and QC-evidence links in the same live run.

## Evidence boundary

This is independent public-data portfolio work. `adtte_retention_style.csv` is an ADTTE-style exercise and is not claimed to be sponsor-approved, formally ADaM-conformant/submission-ready, independently validated production programming, an efficacy endpoint or a regulatory conclusion.
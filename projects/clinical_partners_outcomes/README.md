# Clinical Outcomes & Longitudinal Methods Workbench

This subproject uses open longitudinal mental-health data and official NHS Talking Therapies aggregate statistics to demonstrate statistical reasoning for a research-oriented Clinical Data Scientist role. It separates longitudinal description, clinically meaningful change, prospective prediction, missing outcome collection, exploratory trajectory phenotyping and service benchmarking.

## Data sources

### PSYCHE-D

- Dataset: Makhmutova et al., Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Paper: Makhmutova M, Kainkaryam R, Ferreira M, Min J, Jaggi M, Clay I. *Predicting Changes in Depression Severity Using the PSYCHE-D Model Involving Person-Generated Health Data.* JMIR mHealth and uHealth. 2022;10(3):e34148. DOI `10.2196/34148`.
- Original code: `evidation-opensource/PSYCHE-D`.
- Dataset licence: CC BY-NC 4.0.

The release contains 35,694 rows and 154 columns. The real-data workflow finds 4,948 participants and reproduces 10,866 three-month score intervals from 4,036 participants.

### NHS Talking Therapies

v0.3 downloads the latest published key-measures time series available when this version was built: June 2025-June 2026, from the June 2026 NHS Talking Therapies publication dated 13 August 2026. The CSV contains 182,512 aggregate rows, 13 reporting months, five aggregation levels and 11 key measures. Provider benchmarking uses the `Provider` roll-up and does not use patient-level data.

## v0.2 foundation

v0.2 established the score-level analysis:

- 10,866 paired three-month PHQ-9 intervals;
- 15,261 reconstructed participant-month PHQ-9 measurements;
- 8.72% of intervals with PHQ-9 decrease >=6 points;
- 7.24% with PHQ-9 increase >=6 points;
- participant-random-intercept mixed model with descriptive month coefficient -0.055 PHQ-9 points (95% CI -0.068 to -0.042);
- expected-quarter outcome-availability grid with 19,792 opportunities and 54.9% overall analytical-file availability;
- endpoint-availability AUC 0.623;
- explicit comparison showing that class weighting barely changes deterioration AUC but worsens Brier score and calibration.

These are observational and predictive quantities. They are not treatment-effect estimates.

## v0.3: strict prediction-time experiment

The earlier source feature set contains dynamic lifestyle, medication-change and wearable summaries that can extend into the three-month interval being predicted. v0.3 therefore creates two models on the same participant-held-out test cohort.

### Strict t0 model

Endpoint:

```text
PHQ-9 increase >= 6 points over the next 3-month interval
```

Allowed predictors are only:

```text
interval-start PHQ-9 score
+ participant baseline/screener variables frozen from the first released row
```

Real held-out performance:

| Metric | Strict t0 model |
|---|---:|
| Event prevalence | 0.0724 |
| ROC-AUC | 0.6201 |
| Average precision | 0.1068 |
| Brier score | 0.0621 |
| Calibration intercept | -0.5302 |
| Calibration slope | 0.8274 |
| Train/test participant overlap | 0 |

### Broad interval-feature reference

A second model adds the wider source candidate set, including variables whose collection can occur within the future interval. It is reported only as a leakage-risk reference:

- ROC-AUC: 0.6279;
- Brier score: 0.0619.

The small discrimination gain does not justify calling the broader model prospective. v0.3 keeps it out of the deployment-safe feature set.

## v0.3: trajectory phenotyping

PHQ-9 trajectories are analysed separately from prospective prediction. For participants with at least three score measurements, v0.3 estimates a participant-specific linear slope and forms exploratory Gaussian-mixture phenotypes using baseline PHQ-9 and slope.

Real-data result:

- participants with >=3 PHQ-9 measurements: 3,107;
- candidate classes: 2-5;
- selection: lowest BIC among solutions where every class has at least 5% of participants;
- selected classes: 3;
- minimum class fraction: 23.9%;
- mean repeated-initialisation adjusted Rand index: 0.819;
- minimum repeated-initialisation adjusted Rand index: 0.688.

These classes are model-based exploratory phenotypes. They are not labelled as validated clinical or biological subtypes.

## v0.3: NHS Talking Therapies service benchmark

The official time-series schema contains:

```text
REPORTING_PERIOD_START
REPORTING_PERIOD_END
GROUP_TYPE
ORG_CODE1 / ORG_NAME1
ORG_CODE2 / ORG_NAME2
MEASURE_ID
MEASURE_NAME
MEASURE_VALUE
```

The provider benchmark uses six percentage outcomes:

- `Percentage_AccessingServices6WeeksFinishedCourseTreatment`;
- `Percentage_AccessingServices18WeeksFinishedCourseTreatment`;
- `Percentage_ReliableDeterioration`;
- `Percentage_ReliableImprovement`;
- `Percentage_Recovery`;
- `Percentage_ReliableRecovery`.

It also retains relevant count measures for context. Suppressed values (`*`) are converted to missing rather than treated as zero.

The module produces:

1. England key-measure time series;
2. provider-level key-measure panel;
3. June 2026 provider distributions and England aggregate comparisons;
4. favourable provider percentiles, with deterioration direction reversed;
5. June 2025 to June 2026 provider changes where both values are observed;
6. provider-level Spearman associations between access and outcome measures;
7. a benchmark figure showing provider median/IQR against the England aggregate.

The provider correlations are ecological descriptions only. They do not identify patient-level waiting-time effects and they do not adjust for case mix. NHS measure M351 (mean days waited between treatments), which has a current data-quality warning, is not used.

## Outcome availability and missingness boundary

The PSYCHE-D public analytical release supports an audit of whether scheduled PHQ-9 endpoints are present, but not the exact reason why they are absent. Missing rows can reflect questionnaire non-completion, attrition or source preprocessing. The project therefore does not claim to have identified MAR or MNAR from the public release alone.

## Reliable-change boundary

A 6-point PHQ-9 change is used for PHQ-specific reliable improvement/deterioration. A PHQ-9 score below 10 is reported separately as a caseness-cutoff crossing. These PHQ-only quantities are not called full NHS Talking Therapies reliable improvement or reliable recovery because the service definition can also depend on the paired anxiety measure.

## Run locally

```bash
python -m pip install -r projects/clinical_partners_outcomes/requirements.txt

python projects/clinical_partners_outcomes/analysis.py \
  --data data/psyche_d/anon_processed_df.parquet \
  --out outputs/clinical_partners_outcomes

python projects/clinical_partners_outcomes/v02_score_longitudinal.py \
  --data data/psyche_d/anon_processed_df.parquet \
  --out outputs/clinical_partners_outcomes

python projects/clinical_partners_outcomes/v03_prospective_trajectory.py \
  --data data/psyche_d/anon_processed_df.parquet \
  --out outputs/clinical_partners_outcomes

python projects/clinical_partners_outcomes/v03_nhs_schema_audit.py \
  --data data/nhs_talking_therapies/key_measures_jun2025_jun2026.csv \
  --out outputs/clinical_partners_outcomes

python projects/clinical_partners_outcomes/v03_nhs_provider_benchmark.py \
  --data data/nhs_talking_therapies/key_measures_jun2025_jun2026.csv \
  --out outputs/clinical_partners_outcomes
```

## Tests and CI

```bash
cd projects/clinical_partners_outcomes
pytest -q
```

GitHub Actions downloads PSYCHE-D and the official NHS time series, verifies the PSYCHE-D MD5 checksums, runs all analysis stages and unit tests, checks source scale, score counts, zero participant overlap, trajectory constraints and NHS provider-benchmark invariants, then uploads the full real-data result package.

## Interview summary

> I started from a public longitudinal mental-health dataset and separated four questions that are often mixed together: how symptoms change over time, whether reliable deterioration can be predicted using only information available at prediction time, whether outcome collection is selective, and how service-level outcomes vary across providers. The strict prospective model uses only interval-start PHQ-9 and frozen baseline variables, with no participant leakage. It obtained AUC 0.620 and calibration slope 0.827; adding interval-derived variables raised AUC only to 0.628, so I kept them out of the prospective model. I also identified three exploratory PHQ-9 trajectory phenotypes with repeated-initialisation ARI 0.819, and linked the project to official NHS Talking Therapies provider benchmarks while keeping aggregate benchmarking separate from patient-level causal claims.

## Remaining high-value extensions

The next methods with clear additional value are temporal/external validation, bootstrap uncertainty for calibration and subgroup metrics, richer longitudinal trajectory comparison, and a separate patient-level causal study with an explicit exposure, time zero, estimand and identification assumptions. Bayesian service/clinician partial pooling also requires a dataset with a real service hierarchy rather than inventing one from PSYCHE-D.

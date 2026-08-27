# Clinical Outcomes & Longitudinal Methods Workbench

This subproject uses the public PSYCHE-D release to demonstrate clinical-data-science reasoning that is directly relevant to research-oriented mental-health work: repeated outcome measurements, clinically meaningful score change, participant-level validation, outcome availability, calibration, subgroup review and reproducible evidence generation.

## Data and paper

- Dataset: Makhmutova et al., **PSYCHE-D dataset**, Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Published paper: Makhmutova M, Kainkaryam R, Ferreira M, Min J, Jaggi M, Clay I. *Predicting Changes in Depression Severity Using the PSYCHE-D (Prediction of Severity Change-Depression) Model Involving Person-Generated Health Data: Longitudinal Case-Control Observational Study.* JMIR mHealth and uHealth. 2022;10(3):e34148. DOI `10.2196/34148`.
- Original code: `evidation-opensource/PSYCHE-D`.
- Released dataset licence: CC BY-NC 4.0. Raw source files are downloaded at run time and are not committed to this repository.

The release contains 35,694 rows and 154 columns. The real-data run finds 4,948 participants in the released monthly file and reproduces the source modelling cohort of 10,866 three-month samples from 4,036 participants.

## What v0.2 adds

The public release contains both `phq9_score_start` and `phq9_score_end`. v0.2 therefore moves beyond category-only analysis and adds:

1. PHQ-9 score validation on the 0-27 scale;
2. 10,866 paired three-month score intervals;
3. reconstruction of 15,261 unique participant-month PHQ-9 measurements;
4. PHQ-specific reliable improvement/deterioration using a 6-point change rule;
5. PHQ-9 caseness-cutoff crossing at 10, reported separately from reliable change;
6. 20% relative reduction as an MCID sensitivity analysis, not a universal threshold;
7. a participant-random-intercept mixed model for repeated PHQ-9 scores;
8. an expected-quarter outcome-availability grid across months 3, 6, 9 and 12;
9. participant-held-out modelling of endpoint availability;
10. unweighted versus class-weight-balanced deterioration probability models to show the effect of class weighting on calibration.

## Real v0.2 findings

The score-level run uses 10,866 intervals from 4,036 participants. Mean PHQ-9 changes from 7.662 at interval start to 7.468 at interval end; median change is 0. Across intervals, 8.72% show a PHQ-9 decrease of at least 6 points and 7.24% show an increase of at least 6 points.

Among intervals beginning at PHQ-9 >=10, 30.13% cross below 10, while 15.47% both improve by at least 6 points and end below 10. A 20% relative reduction is seen in 42.32% of baseline-case intervals, but that quantity is retained only as a sensitivity analysis because MCID depends on baseline severity and decision context.

The repeated-score reconstruction contains 15,261 unique participant-month measurements with zero conflicting score values at shared quarter boundaries. A random-intercept mixed model converges successfully. Its descriptive time coefficient is -0.055 PHQ-9 points per study month (95% CI -0.068 to -0.042). This is a population time trend in the selected observational cohort, not a treatment-effect estimate.

## Outcome availability

The first version conditioned on rows with a baseline category and therefore selected a cohort where the endpoint was always present. v0.2 fixes this by constructing four expected quarterly PHQ assessment opportunities for every participant in the released monthly file: 19,792 participant-quarter opportunities in total.

Availability in the analytical release declines by scheduled month:

- month 3: 65.6%;
- month 6: 57.2%;
- month 9: 55.2%;
- month 12: 41.6%.

A participant-held-out logistic model using baseline variables plus scheduled month obtains ROC-AUC 0.623 and is well calibrated at the aggregate test-set level (calibration intercept -0.048; slope 1.020). This is evidence that analytical-file availability is structured rather than random. It is not enough to identify a clinical missingness mechanism because absence can reflect questionnaire non-completion, study attrition or source preprocessing.

## Deterioration probability calibration

The source category deterioration endpoint is:

```text
phq9_cat_end > phq9_cat_start
```

The participant-held-out baseline has only modest discrimination (AUC about 0.596). The important result is the calibration comparison:

| Model | AUC | Brier | Calibration intercept | Calibration slope |
|---|---:|---:|---:|---:|
| Unweighted logistic | 0.596 | 0.162 | -0.720 | 0.453 |
| Class-weight balanced logistic | 0.597 | 0.242 | -1.327 | 0.424 |

Class balancing leaves discrimination almost unchanged but makes the Brier score much worse. This is a useful clinical-prediction lesson: class weighting should not be assumed to produce calibrated patient-level probabilities.

## Timing boundary

The original PSYCHE-D samples include dynamic lifestyle, medication and wearable measurements within the three-month interval. For that reason, this workbench describes the current task as **participant-held-out deterioration classification**, not as a deployable prospective risk forecast. A true deployment study would first fix a prediction timestamp and then exclude all information collected after it.

## Leakage control

Train/test splitting is by participant. A participant can occur in training or testing, never both. The CI checks participant overlap directly. Endpoint fields and generated phase-1 probabilities are excluded from the safe candidate list used by the baseline classification audit.

## Reliable-change boundary

The 6-point threshold is used only as a PHQ-specific reliable-change rule. A score below 10 is reported separately as a caseness-cutoff crossing. The module does not label these PHQ-only quantities as full NHS Talking Therapies reliable improvement or reliable recovery because those service outcomes can also depend on the paired anxiety measure.

## Run locally

```bash
python -m pip install -r projects/clinical_partners_outcomes/requirements.txt
mkdir -p data/psyche_d
curl -fL --retry 8 --retry-all-errors \
  'https://zenodo.org/records/5085146/files/anon_processed_df_parquet?download=1' \
  -o data/psyche_d/anon_processed_df.parquet

python projects/clinical_partners_outcomes/analysis.py \
  --data data/psyche_d/anon_processed_df.parquet \
  --out outputs/clinical_partners_outcomes

python projects/clinical_partners_outcomes/v02_score_longitudinal.py \
  --data data/psyche_d/anon_processed_df.parquet \
  --out outputs/clinical_partners_outcomes
```

## Tests and CI

```bash
cd projects/clinical_partners_outcomes
pytest -q
```

GitHub Actions downloads the real Zenodo files, verifies their published MD5 checksums, runs the tests and both analysis stages, checks source-scale and participant-leakage invariants, and uploads the real-data result package.

## Interview use

A concise explanation is:

> I reproduced a public longitudinal mental-health data workflow and then tested assumptions that matter for clinical use. I reconstructed repeated PHQ-9 scores, separated reliable score change from caseness crossing, fitted a participant-level mixed model, audited outcome availability over follow-up, and compared discrimination with probability calibration. One useful result was that class weighting barely changed AUC but materially worsened Brier score. I also found that the released feature timing does not support calling my baseline a prospective clinical risk model, so I kept that claim out of the analysis.

## Next methods

The strongest next additions are a prespecified prospective prediction-time analysis, uncertainty intervals for subgroup calibration, a trajectory-model comparison with stability checks, and a separate NHS Talking Therapies service-benchmarking module. Causal pathway questions should remain a separate study with an explicit exposure, time zero, estimand and identification assumptions.

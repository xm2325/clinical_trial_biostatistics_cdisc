# Clinical Outcomes & Longitudinal Methods Workbench

This subproject is a job-relevant real-data analysis built around the public PSYCHE-D release. It is designed to show the statistical reasoning expected in a research-oriented Clinical Data Scientist role: longitudinal outcome definition, participant-level validation, missing-data diagnostics, calibration, subgroup review, and reproducible evidence generation.

## Data and paper

- Dataset: Makhmutova et al., **PSYCHE-D dataset**, Zenodo record `5085146`, DOI `10.5281/zenodo.5085146`.
- Published paper: Makhmutova M, Kainkaryam R, Ferreira M, Min J, Jaggi M, Clay I. *Predicting Changes in Depression Severity Using the PSYCHE-D (Prediction of Severity Change-Depression) Model Involving Person-Generated Health Data: Longitudinal Case-Control Observational Study.* JMIR mHealth and uHealth. 2022;10(3):e34148. DOI `10.2196/34148`.
- Original code: `evidation-opensource/PSYCHE-D`.
- Released dataset licence: CC BY-NC 4.0. The raw dataset is downloaded at run time and is not committed to this repository.

The Zenodo release contains 35,694 rows and 154 columns indexed by `[participant]_[month]`. The source description states that it yields 10,866 three-month samples from 4,036 unique participants.

## Why this is not a generic mental-health classifier

The workbench starts from a clinical analysis question rather than from an algorithm. The current stage asks whether future PHQ-9 severity-category deterioration can be predicted without participant leakage and whether endpoint observation itself is predictable from measured variables. These are separate questions.

The pipeline therefore reports:

1. schema and cohort audit;
2. PHQ-related variables actually present in the public release;
3. PHQ-9 severity-category transition counts and row-normalised transition rates;
4. participant-held-out deterioration prediction;
5. ROC-AUC, average precision, Brier score, calibration intercept and calibration slope;
6. calibration curve;
7. subgroup metrics for available sex, race-indicator and insurance variables;
8. endpoint-observation rate over study month;
9. a participant-held-out model of endpoint observation as a missingness diagnostic;
10. explicit interpretation boundaries.

## Endpoint

The released PSYCHE-D implementation defines deterioration as:

```text
phq9_cat_end > phq9_cat_start
```

This project follows that definition for the first real-data stage so that the target is tied to the source release rather than invented for the application.

## Leakage control

Train/test splitting is performed by participant. A participant can occur in either training or testing but never both. Candidate predictors are restricted to baseline, lifestyle/medication and wearable variables that the released PSYCHE-D code used or explicitly considered. `phq9_cat_end` and generated phase-1 probability variables are excluded.

The CI tests fail if participant overlap is detected or if endpoint/generated-probability variables enter the safe candidate list.

## Missing-data interpretation

The endpoint-observation model is a diagnostic, not a causal claim. If observation status is predictable from measured variables, complete-case analysis should not be treated as obviously missing completely at random (MCAR). This does not by itself distinguish missing at random (MAR) from missing not at random (MNAR).

## Reliable change / MCID boundary

Reliable change and minimal clinically important difference (MCID) require a defensible score-level definition. The first stage does not manufacture one from severity categories. The pipeline writes `phq_schema_columns.csv` and records whether a raw PHQ total-score field appears in the public release. Score-level psychometrics will be added only when the source data support it, or through a separate open item-level PHQ-9/GAD-7 dataset with clear provenance.

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
```

## Tests

```bash
cd projects/clinical_partners_outcomes
pytest -q
```

## Interview use

A concise interpretation of this work is:

> I used an open longitudinal mental-health dataset to separate three questions that are often mixed together: whether symptoms change, whether deterioration can be predicted for unseen patients, and whether outcome measurement is itself selective. I used participant-held-out validation, calibration rather than AUC alone, subgroup review and an explicit missingness diagnostic. I also kept causal and clinically meaningful-change claims out of the analysis where the public data did not support them.

## Next methods after the first real-data run

The next stage is conditional on the schema audit rather than assumed in advance. If score-level longitudinal PHQ-9 data are present, add mixed-effects symptom trajectories and score-level clinically meaningful change. If not, link a separate open score/item-level dataset for psychometrics while keeping PSYCHE-D for deterioration, calibration and missingness. A service-level NHS Talking Therapies module can then add waiting-time and recovery benchmarking without pretending aggregate provider statistics are patient-level causal data.

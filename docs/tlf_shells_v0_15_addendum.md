# TLF shells v0.15 addendum

## T23 — ACTOT Week 24 multiplicity decisions

**Purpose:** report family-wise decisions for the two primary Week 24 active-versus-placebo ACTOT MMRM hypotheses.

**Population:** observed longitudinal ACTOT population used by the primary MMRM.

**Source:** primary `Unstructured` rows from `outputs/mmrm_treatment_contrasts.csv` at `Week 24`.

**Expected rows:** exactly 2.

**Required columns:**

- `family_id`
- `hypothesis_id`
- `contrast`
- `endpoint`
- `visit`
- `covariance`
- `estimate`
- `SE`
- `df`
- `raw_p_value`
- `adjustment_method`
- `family_alpha`
- `comparison_count`
- `local_alpha`
- `adjusted_p_value`
- `reject_familywise`

**QC evidence:** `outputs/mmrm_qc.csv` and `outputs/multiplicity_qc.csv`.

**Interpretation:** T23 is a portfolio family-wise decision table. It does not convert sensitivity analyses or secondary displays into additional confirmatory hypotheses and is not presented as the source trial's regulatory decision table.

# Advanced NONMEM dataflow and public PK work samples

This folder extends the repository's introductory, synthetic NONMEM dataset generation module. It covers three distinct evidence levels:

1. SYNTHETIC source-to-event programming in R, with independent source re-derivation in Python.
2. SYNTHETIC fixed-parameter one-compartment PK predictions independently compared between closed-form solutions and scipy ODE integration.
3. REAL PUBLIC Theoph observations, transformed to NONMEM-style rows and used for a pooled scipy nonlinear least-squares PK fit. This is not a NONMEM fit.

None of these is a sponsor clinical trial dataset, compliant SDTM transfer, GxP validated program, regulatory electronic submission, or proof of running licensed NONMEM.

## Reproduce the synthetic advanced M1/M3 exercise

Run at repository root after installing Python dependencies from requirements.txt and base R:

```bash
for MODE in m1 m3; do
  Rscript case_studies/nonmem_dataflow_demo/advanced/R/10_build_advanced.R --blq-mode=$MODE
  python case_studies/nonmem_dataflow_demo/advanced/scripts/20_independent_qc.py --output-dir outputs/nonmem_advanced/$MODE
  python case_studies/nonmem_dataflow_demo/advanced/scripts/30_pk_crosscheck.py --output-dir outputs/nonmem_advanced/$MODE
  python case_studies/nonmem_dataflow_demo/advanced/scripts/40_package_handoff.py --output-dir outputs/nonmem_advanced/$MODE
done
```

Outputs, in outputs/nonmem_advanced/{m1,m3}:

- data/nonmem_input.csv: numeric, headerless, specified model column order
- data/nonmem_input_review.csv: with source record IDs
- metadata/: subject crosswalk, metadata specification and BLQ strategy
- qc/: subject, check name, findings and follow-up for each independent check
- model/: unexecuted teaching control stream with a relative $DATA reference
- validation/: predictions from analytic equations and an independent scipy ODE
- handoff/: file links, SHA256 file index and explicit scope restrictions

The sample inputs contain four invented subjects. They cover repeated doses, oral depot doses, constant-rate IV infusions, a subject receiving both routes, concentration and weight unit conversions, simultaneous dose/observation time, M1 exclusion versus M3 censoring input preparation, and controlled source keys.

## BLQ/M3 technical boundary

Input PC contains an exercise-specific BLQ_FLAG plus LLOQ_NG_ML, which are NOT presented as CDISC standard variables.

In M1, a below-limit sample uses MDV=1, DV=0 as an explicit missing-value sentinel; it is excluded from fitting.

In M3, a below-limit sample uses CENS=1, MDV=0, and DV=LLOQ as an explicit threshold placeholder, not a measured value. The unexecuted control stream uses F_FLAG=1 and PHI((LLOQ-F)/W), with a Laplace estimation request. It does not implement, run or validate a NONMEM M3 fit.

For the illustrated additive normally distributed measurement error, a censored observation contributes the probability

L = Phi((LLOQ - predicted concentration)/residual standard deviation).

The fixed-parameter cross-check is NOT model fitting: it compares two computations of the same structural one-compartment model with CL=5 L/h, V=40 L, KA=1.2/h. Oral dose: depot absorption into central compartment; IV infusion: finite-duration constant-rate input.

## Public Theoph study: separate from synthetic exercise

Theoph comes from `datasets::Theoph` in base R: 12 subjects, 132 observed serum concentrations after an oral dose. Its Dose is mg/kg, Wt is kg, Time is hours since administration, conc is mg/L. The scripts explicitly apply Dose_mg=Dose_mg_per_kg*Wt_kg and DV_ng_per_mL=1000*conc_mg_per_L.

```bash
Rscript case_studies/nonmem_dataflow_demo/advanced/R/50_theoph_public_data.R
python case_studies/nonmem_dataflow_demo/advanced/scripts/51_theoph_independent_qc_and_fit.py
```

Outputs are in outputs/nonmem_theoph_public. Age and sex are unavailable in the public source and are flagged -99 and -1 in UNUSED variables; they are not inferred. Time is relative, not mapped to a fabricated collection date. No assay LLOQ or BLQ flags are provided. The script therefore does NOT claim to know the assay lower limit.

An independent Python script verifies the mapping against an exported copy of the public source values, then performs pooled nonlinear least squares with fixed population parameters and an 8-subject training / 4-subject held-out split. It does NOT estimate nonlinear mixed-effects models or individual ETAs, and it makes no claims about trial, sponsor, submission or NONMEM execution.

R source: https://search.r-project.org/R/refmans/datasets/html/Theoph.html

## Adversarial tests

The advanced GitHub Actions workflow executes M1/M3 build, row-level independent QC, ODE structural cross-check, and a self-contained integrity-checked handoff. It also intentionally corrupts MDV, duplicates a source sequence key, and modifies a packaged CSV to demonstrate failure handling. A separate workflow step validates the Theoph source conversion and fits the simple open-source PK model.

A green workflow means that these bounded tests ran; it does not replace clinical programming certification, GxP validation, actual NONMEM installation, study lead sign-off, official Define-XML, or a real electronic submission.

## CI isolation and descriptive noncompartmental analysis (NCA)

The introductory and advanced NONMEM workflows are triggered only by their own paths on pull requests, or by manual dispatch. Feature-branch push duplicates are disabled (main-branch push remains enabled). The large CDISC, P21 and v0.28 handoff workflows ignore changes that are solely inside the NONMEM demo and its two workflows; they retain manual dispatch. **Changing these larger workflow YAML files in the same PR can still cause a one-off rerun.** Check required branch protection statuses before relying on path filtering.

After generating the public Theoph data, `python case_studies/nonmem_dataflow_demo/advanced/scripts/52_theoph_nca.py` computes per-subject Cmax, Tmax and AUC0-last (manual trapezoid independently checked against scipy.integrate.trapezoid). It reports an explicitly descriptive terminal slope and half-life using the last three post-Cmax positive samples when possible. It is not formal validated NCA and does not change or replace the pooled least-squares fit.


## Source transfer gate and auditable query lifecycle

The advanced CI now executes the source intake validator `scripts/60_transfer_gate.py` before
the source-to-model independent QC and handoff, for both M1 and M3 variants.

The gate checks file and variable contracts, subject/sequence identifiers,
complete actual timestamps, exposure amount and unit, IV duration, PK values
and LLOQ/BLQ conflicts, weight timing and source coverage. Each query
contains table, source key, check code, severity, proposed action, reviewer,
decision and evidence columns. ERROR places transfer on HOLD; WARNING stays
open for human review (including a same-time dose and sample). The dataset
is never silently corrected. The handoff packages the exact source snapshot,
query log, source SHA256 identities and release gate status. A changed source
fails the pre-handoff hash check.

The negative-case suite `65_transfer_regression.py` deliberately injects 10
independent issues, each of which must be rejected with its declared reason.
These files are synthetic teaching materials, not source data from EDC, a
sponsor-approved DTA or actual EPOD exchange.

## Executable censored likelihood

`70_m3_censored_likelihood.py` uses a reproducible artificial oral PK dataset.
It fits pooled CL and additive residual SD (V and KA fixed) by:

- M1: log normal-density contributions from observed samples only.
- M3: observed normal-density log likelihood plus left-censored
  log Phi((LLOQ - prediction) / SD).

It checks the normal CDF against an independent error-function computation,
including a numerically extreme lower tail. Hidden BLQ concentrations are
not passed to either estimator. This is not NONMEM or NLME, and a single
synthetic comparison does not prove a method always performs better.

Relevant public technical references:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6709422/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2691472/
- https://nonmem.iconplc.com/nonmem750/nm750.pdf

## Licensed NONMEM runner boundary

`90_licensed_nonmem_runner.py` checks model input structure and prepares
a separate working directory. Without `--execute` it **only creates a plan**:

```bash
python case_studies/nonmem_dataflow_demo/advanced/scripts/90_licensed_nonmem_runner.py --output-dir outputs/nonmem_advanced/m3
```

A person with an actual authorised local NONMEM installation may request:

```bash
python case_studies/nonmem_dataflow_demo/advanced/scripts/90_licensed_nonmem_runner.py --output-dir outputs/nonmem_advanced/m3 --execute --executable /path/to/nmfe75
```

CI exercises plan-only mode. It does NOT install, license or run NONMEM. A zero
process exit and an output report require independent scientific review,
model convergence checking and validation before any interpretation.

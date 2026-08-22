# Randomisation and initial-kit schedule — portfolio version 0.8

## Purpose and evidence boundary

This module demonstrates the statistical and programming controls around creating a randomisation schedule and a simple initial-kit code list.

It is an **illustrative portfolio simulation**. It is not an IRT/IWRS system, is not for a real clinical trial, and does not claim sponsor randomisation or drug-supply production responsibility.

In a real blinded study, the random seed, block structure, treatment allocation list and kit decoding list would be access-controlled. They are visible here only because the repository is a public technical work sample built on public/simulated information.

## 1. Link to protocol design

The v0.8 schedule links to the illustrative v0.7 planning scenario `E2.5_P80`, which requires 390 randomised subjects after 15% dropout inflation.

The randomisation specification therefore generates exactly 390 randomisation numbers.

This link is a portfolio consistency check. It does not imply that the public source trial used the v0.7 assumptions.

## 2. Allocation method

The schedule uses stratified permuted blocks with equal 1:1:1 allocation across:

- Placebo;
- Xanomeline Low Dose;
- Xanomeline High Dose.

Five illustrative strata each contribute 78 planned randomisations. Because 78 is divisible by three, every stratum can finish with exact balance of 26 subjects per treatment.

Allowed block sizes are 3 and 6. Every generated block contains the same number of assignments to each of the three treatment arms.

The machine-readable source of truth is `spec/randomisation_schedule.json`.

## 3. Reproducibility

The portfolio uses NumPy's deterministic random-number generator with a fixed seed recorded in the specification. The same specification and software environment therefore reproduce the same allocation and kit schedules.

This reproducibility is useful for technical verification. For a real blinded study, a production seed would be confidential and handled under controlled procedures rather than committed to a public repository.

## 4. Randomisation identifiers and blinded boundary

The generator writes two schedule views.

### Blinded schedule

`outputs/randomisation_schedule_blinded.csv` contains only:

```text
randomisation_id
stratum
kit_id
```

It deliberately excludes:

```text
treatment
blind_code
block_id
block_size
position_in_block
```

### Unblinded schedule

`outputs/randomisation_schedule_unblinded.csv` contains the full allocation information needed to verify block balance and treatment-kit consistency.

The separation is tested automatically rather than relying only on a written convention.

## 5. Initial-kit code list

The module creates one illustrative initial kit for every randomisation number. `outputs/kit_code_list_unblinded.csv` maps each kit ID to its treatment and blind code.

The generated kit pool is balanced to the randomisation allocation, shuffled deterministically and then assigned only to randomisations receiving the matching treatment.

The scope intentionally stops at a single initial-kit assignment. It does **not** model:

- resupply visits;
- site inventory;
- packaging batches;
- expiry dates;
- replacement kits;
- temperature excursions;
- emergency unblinding;
- IRT/IWRS transactions;
- depot/site shipment logic.

Those are operational drug-supply/IRT functions rather than claims this portfolio should imitate without the corresponding systems and procedures.

## 6. Required QC

The v0.8 gate requires all of the following:

1. generated randomisation count equals the planned total;
2. randomisation IDs are unique;
3. kit IDs are unique;
4. overall treatment allocation is exactly balanced;
5. treatment allocation is exactly balanced within every stratum;
6. every permuted block is balanced across treatment arms;
7. each assigned kit decodes to the same treatment as the unblinded randomisation allocation;
8. blinded output contains no allocation or block-structure columns;
9. blinded and unblinded randomisation/kit keys reconcile exactly;
10. the kit code list covers every assigned kit exactly once.

The maximum consecutive run of the same treatment within each stratum is also reported as an **informational** diagnostic. No arbitrary run-length limit is imposed after randomisation because that would add another sequence constraint not specified by this portfolio design.

## 7. Generated evidence

`python scripts/run_randomisation.py` writes:

- `randomisation_schedule_unblinded.csv`;
- `randomisation_schedule_blinded.csv`;
- `kit_code_list_unblinded.csv`;
- `randomisation_balance.csv`;
- `randomisation_block_summary.csv`;
- `randomisation_qc.csv`;
- `randomisation_metrics.json`;
- `randomisation_summary.md`.

The summary records SHA256 identities of the generated CSV schedules. The metrics file records the specification hash, seed, total randomisations, number of strata/blocks, treatment counts and required-QC result.

## 8. What a production review would additionally require

Before a real schedule could be released, a statistician would normally need controlled approval of the protocol randomisation section and population assumptions, independent verification of the randomisation program/output, documented access roles, secure transfer of the unblinded list, treatment-code governance, emergency-unblinding procedures, IRT/vendor specifications, version control and change control, plus documented reconciliation between the statistical schedule and drug-supply configuration.

The portfolio demonstrates the allocation logic and QC structure, not those operational approvals.

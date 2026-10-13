# Training SOP: synthetic PK source intake, review and handoff

**Purpose:** demonstrate a clinical programmer's source validation, issue
management, independent QC and analysis handoff. **Not sponsor/CRO SOP or
a clinical submission.** All transfer records here are invented.

## Separation of duties

- Source owner / data manager: confirms collection timestamps, PK assay units,
  actual dosing, BLQ coding and subject identity; answers transfer queries.
- Statistical programmer: maps EX, PC, DM, VS to NONMEM event records and
  documents derivations, naming, source identifiers and assumptions.
- Independent QC programmer: uses a separate Python reconstruction, logs
  full-subject checks, tests data corruption and reviews discrepancies.
- Pharmacometric lead: approves PK parameterisation, BLQ strategy, estimand,
  model diagnostics and any licensed NONMEM model outputs; **not simulated**.
- Release reviewer: checks file index SHA256 and linkage; **not a qualified
  sign-off or regulatory submission**.

## Decision gates

| Gate | Inputs | Condition | Evidence |
| --- | --- | --- | --- |
| Intake | Synthetic CSV extracts | No blocking ERROR queries | transfer_report.json; transfer_query_log.csv |
| Mapping | EX/PC/DM/VS, specified variables | Deterministic ID, EVID/MDV/CMT, dose units, time | nonmem_input_review.csv; variable_definitions.csv |
| Independent QC | Source and review data | All subject/event checks PASS | qc_log.csv; qc_summary.md |
| Structural checks | Time, route, dose | Closed-form matches scipy solve_ivp at sample times | pk_crosscheck.csv |
| Package | Source snapshot, QC, model sketch | Matching source hashes, relative links, SHA256 | file_index.csv; process_note.md |
| Model estimation | Licensed NONMEM when available | Executed and reviewed | **NOT PERFORMED** |
| Sponsor transfer | Approved study workflow | Review, QA and permissions | **NOT PERFORMED** |

If intake is HOLD, stop downstream handoff. Do not silently impute
missing dates, convert unknown units, relabel BLQ or remove subject rows.
Persist unresolved queries as OPEN until a data owner provides an auditable
resolution. The training dataset intentionally includes a same-time
dose/sample ambiguity; it is WARN rather than a fabricated correction.

## Release contents

The generated `handoff/` directory includes an exact copy of the
synthetic source tables, intake transfer report/query log and their
SHA256 provenance; headerless model input and inspected model input;
illustrative model; independent row-level QC; a PK structural cross-check;
variable definitions; relative file links; and a SHA256 file index.

Censored M3 input uses LLOQ as a threshold placeholder in DV and CENS=1,
not as an observed concentration. The illustrative NONMEM control stream
remains unexecuted. A Python M3 likelihood example is separate from
the NONMEM control stream.

## Regulatory and privacy boundary

No real subject identifiers, proprietary clinical records, licensed software,
real Define-XML submission, authorised DataFlow, vendor exchange, EPOD
records, production audit trail, Part 11 validation or certified independent
programmer sign-off are involved.

Public NONMEM 7.5.0 manual:
https://nonmem.iconplc.com/nonmem750/nm750.pdf

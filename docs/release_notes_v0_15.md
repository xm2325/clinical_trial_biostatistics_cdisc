# Release notes — v0.15.0

## Primary multiplicity decision layer

- Add a machine-readable primary multiplicity specification aligned to the existing illustrative protocol-design family: two Week 24 ACTOT active-versus-placebo hypotheses, two-sided family alpha 0.05 and Bonferroni local alpha 0.025.
- Add executable selection of only the primary `Unstructured` Week 24 MMRM contrasts; sensitivity covariance structures, ANCOVA and missing-data sensitivity analyses are excluded from the controlled family.
- Add raw-to-adjusted p-value and reject/non-reject decisions with 12 blocking QC checks.
- Verify H_LOW raw p=0.169334 -> adjusted p=0.338669 and H_HIGH raw p=0.421970 -> adjusted p=0.843940; **0/2 family-wise rejections**.
- Register T23 `outputs/table23_actot_multiplicity.csv` with an executable required-column/minimum-row contract and linked MMRM/multiplicity QC evidence.

## Traceability

- Advance the controlled TLF registry to `0.15.0` and T01-T23.
- Verify **23/23** output files, contracts, analysis-data links and QC-evidence links.
- Keep registry-derived analysis versioning; no hard-coded traceability version is reintroduced.

## Change control

- Preserve the validated v0.14 base graph/request JSON byte-for-byte.
- Add versioned v0.15 graph/request extensions and an executable merger requiring exact base-version compatibility.
- Add multiplicity assumption, calculation and T23 dependency nodes.
- Extend CR-003 primary-visit, CR-004 MMRM-covariance and CR-005 treatment-discontinuation/estimand-alignment propagation to T23.
- Add CR-009 for primary multiplicity-rule changes.
- Verify **9** change requests, **62** propagated component links and **217/217** required impact relationships/resources with zero missing, extra or unresolved required items.

## Evidence boundary

v0.15 remains independent public-data portfolio work. The Bonferroni family is an internally controlled portfolio analysis aligned to the illustrative planning specification; it is not claimed to be the source trial's sponsor-approved or regulatory confirmatory multiplicity strategy.

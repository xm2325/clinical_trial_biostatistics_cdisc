from pathlib import Path

README = Path("README.md")
CHANGELOG = Path("CHANGELOG.md")

readme = README.read_text(encoding="utf-8")
marker = "## Current milestone: v0.22 — statistical review query and decision provenance"
new_heading = "## Current milestone: v0.23 — randomised-assignment consistency repair and population provenance"

if new_heading not in readme:
    if marker not in readme:
        raise SystemExit("README v0.22 milestone marker not found")
    section = '''## Current milestone: v0.23 — randomised-assignment consistency repair and population provenance

v0.23 is a **repair**, not a new efficacy model. A subject-level audit found that **12/254 randomised subjects** have `TRT01P != TRT01A`, all planned High Dose -> actual Low Dose. Those 12 subjects contribute no observed Week 8/16/24 ACTOT rows to the primary MMRM, but they do belong to the 254-subject missing-data target and therefore affect imputation-group assignment.

The previous T20/T21/T22 sensitivity path grouped that target by actual treatment (`TRT01A`), giving Placebo / Low / High **86 / 96 / 72** and pairwise MI targets **182 / 158**. v0.23 aligns efficacy missing-data sensitivity with the randomised treatment condition by using planned assignment (`TRT01P`) for MI grouping while retaining actual treatment as explicit context. The corrected randomised allocation is **86 / 84 / 84**, giving **170 / 170** Low-vs-Placebo and High-vs-Placebo targets.

The repair is deliberately bounded:

```text
original ADSL-/ADQS-style files with actual-treatment provenance
  -> planned/actual subject-level audit
  -> planned-assignment MI input copies
  -> hard guard for mismatch subjects in observed primary MMRM
  -> T20/T21 subject-level MAR/delta MI + MCSE
  -> T22 MAR/JR/CR/CIR reference-based MI + MCSE
  -> executed-target audit
  -> byte-for-byte restore of original analysis inputs
```

Governance-inclusive clean validation Actions **#689 / run 32851464310** on head `bee4e338099d2a769037ec9f4190308a0c350de2` passed the complete Python/R/CDISC/MMRM/MI/readiness/change-control/traceability/closure/reviewer-response workflow. It verified:

- subjects / randomised / baseline-ACTOT target: **306 / 254 / 254**;
- planned randomised allocation: **86 / 84 / 84**;
- actual-treatment allocation among randomised subjects: **86 / 96 / 72**;
- planned-versus-actual mismatches: **12**;
- mismatch subjects in observed primary MMRM: **0**;
- primary MMRM subjects: **189**;
- randomised baseline subjects with no observed post-baseline ACTOT: **65**;
- Week 24 observed / missing: **116 / 138**;
- corrected executed MI pair targets: **170 / 170**;
- pre-MI assignment checks: **10/10 PASS**;
- post-MI execution/restore checks: **4/4 PASS**;
- reference-based MAR/JR/CR/CIR rows: **8/8**, with **8/8 MCSE passes**;
- controlled assignment claim: **`PORTFOLIO_RANDOMISED_ASSIGNMENT_CONSISTENCY_READY`**;
- active change control: **CR-001–CR-015**, **94** propagated links and **333/333** required impacts, with **0 missing / 0 extra / 0 unresolved**;
- CR-015 propagates through **6** components and **22** required impacts to **T20/T21/T22**.

Corrected Week 24 MAR estimates are approximately **-1.5397** for Low Dose versus Placebo and **-0.7237** for High Dose versus Placebo. The primary Bonferroni family remains **0/2 rejected** with adjusted p-values **0.338669 / 0.843940**, so the repair does not opportunistically change the controlled conclusion: no confirmatory efficacy-success claim is supported, and MI remains supportive sensitivity evidence.

The #689 artifact is `clinical-biostatistics-cdisc-outputs`, ID **9564651055**, digest `sha256:106abf356e19437e2f60cfdb4fc5b0fca55db712e45270c6b1865ac9780f2623`.

See `docs/mi_randomised_assignment_repair_v0_23.md` for the repair rationale, controlled boundary and evidence.

## v0.22 baseline retained under v0.23 — statistical review query and decision provenance'''
    readme = readme.replace(marker, section, 1)

old_boundary = (
    "Readiness, governance, interpretation and reviewer-response evidence remain separate from the TLF registry. "
    "v0.22 does **not** invent a T26 or CR-015; the statistical output registry remains **T01–T25 at version 0.17.0** "
    "and the pre-closure change-control graph remains **CR-001–CR-014** because v0.22 adds post-closure statistical review evidence "
    "rather than a new statistical table/listing/figure or upstream analysis change."
)
new_boundary = (
    "Readiness, governance, interpretation and reviewer-response evidence remain separate from the TLF registry. "
    "The statistical output registry remains **T01–T25 at version 0.17.0**: v0.23 does not create a T26. "
    "Unlike post-closure v0.21/v0.22, v0.23 changes an upstream missing-data sensitivity assignment source, so it is controlled as **CR-015** and explicitly propagates to T20/T21/T22."
)
if old_boundary in readme:
    readme = readme.replace(old_boundary, new_boundary, 1)

readme = readme.replace(
    "  -> fixed-delta diagnostics\n  -> subject-level MAR/delta MI + MCSE QC",
    "  -> fixed-delta diagnostics\n  -> v0.23 planned-randomisation MI assignment boundary + subject-level audit\n  -> subject-level MAR/delta MI + MCSE QC",
    1,
)
readme = readme.replace(
    "  -> layered CR-001–CR-014 statistical change-impact assessment",
    "  -> layered CR-001–CR-015 statistical change-impact assessment",
    1,
)
readme = readme.replace(
    "v0.22 -> post-interpretation statistical reviewer-response QC\n```",
    "v0.22 -> post-interpretation statistical reviewer-response QC\nv0.23 -> randomised-assignment consistency repair for T20–T22\n```",
    1,
)
retained = "The validated v0.20 change-control result is **14 changes / 88 propagated links / 311 of 311 required impact relationships/resources**, with zero missing declarations, zero extra declarations and zero unresolved required resources."
if retained in readme and "v0.23 advances the active layered change-control result" not in readme:
    readme = readme.replace(
        retained,
        retained + "\n\nv0.23 advances the active layered change-control result to **15 changes / 94 propagated links / 333 of 333 required impact relationships/resources**, again with zero missing declarations, zero extra declarations and zero unresolved required resources. **CR-015** controls the randomised-assignment source used by efficacy missing-data sensitivity analyses and propagates to **T20/T21/T22**; the TLF registry itself remains T01–T25.",
        1,
    )
README.write_text(readme, encoding="utf-8")

changelog = CHANGELOG.read_text(encoding="utf-8")
if "## 0.23.0 — 2026-08-25" not in changelog:
    header = "# Changelog\n\n"
    if not changelog.startswith(header):
        raise SystemExit("CHANGELOG header not found")
    entry = '''## 0.23.0 — 2026-08-25

- Repair a material efficacy missing-data treatment-assignment inconsistency found by a subject-level population audit: **12/254 randomised subjects** have `TRT01P != TRT01A`, all planned High Dose -> actual Low Dose.
- Verify **0/12** mismatch subjects enter the observed Week 8/16/24 primary MMRM, so the observed-data primary model and multiplicity decision are not silently changed by the repair.
- Correct T20/T21/T22 MI grouping from actual treatment (`TRT01A`) to planned randomised assignment (`TRT01P`) for the estimand-defined randomised baseline-ACTOT target while retaining actual treatment as context.
- Correct target allocation from **86 / 96 / 72** to **86 / 84 / 84**, changing pairwise MI targets from **182 / 158** to **170 / 170**.
- Add planned-assignment MI input copies, `TRT01A_ACTUAL` provenance, pre-MI **10/10** checks, post-MI **4/4** execution/restore checks, `analysis_population_provenance.csv`, and a hard guard against future mismatch subjects silently entering the primary MMRM.
- Re-run 200-imputation MAR/delta MI and MAR/JR/CR/CIR reference-based MI on the corrected randomised grouping. Corrected Week 24 MAR estimates are approximately **-1.5397** and **-0.7237** for Low/High versus Placebo; reference-based evidence retains **8/8 MCSE passes**.
- Preserve the primary conclusion: adjusted MMRM p-values remain **0.338669 / 0.843940**, so **0/2** primary hypotheses are rejected and no confirmatory efficacy-success conclusion is supported.
- Add **CR-015 — Randomised treatment-assignment source correction for efficacy missing-data sensitivity analyses**. It propagates through **6** components, requires **22** impacts and explicitly affects **T20/T21/T22**.
- Advance layered change control to **15 changes / 94 propagated links / 333/333 required impacts**, with **0 missing / 0 extra / 0 unresolved**. The TLF registry remains **T01–T25 / version 0.17.0**; no T26 is created.
- Governance-inclusive clean run Actions **#689 / run 32851464310** on head `bee4e338099d2a769037ec9f4190308a0c350de2` passes the full workflow. Artifact `9564651055`, digest `sha256:106abf356e19437e2f60cfdb4fc5b0fca55db712e45270c6b1865ac9780f2623`.
- Evidence remains public-data portfolio evidence only, not a sponsor-approved SAP amendment, database-lock change, regulatory response, formal ADaM validation or submission-ready analysis.

'''
    changelog = header + entry + changelog[len(header):]
    CHANGELOG.write_text(changelog, encoding="utf-8")

print("v0.23 documentation patch complete")

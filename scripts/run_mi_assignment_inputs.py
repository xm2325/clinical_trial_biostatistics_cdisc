from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mi_assignment import build_mi_assignment_inputs


def _backup_and_stage() -> None:
    outputs = ROOT / "outputs"
    pairs = [
        (outputs / "adsl_style.csv", outputs / "adsl_style_actual_pre_mi.csv", outputs / "adsl_mi_planned.csv"),
        (outputs / "adqs_actot_style.csv", outputs / "adqs_actot_style_actual_pre_mi.csv", outputs / "adqs_actot_mi_planned.csv"),
    ]
    for original, backup, planned in pairs:
        if not original.exists() or not planned.exists():
            raise FileNotFoundError(
                f"cannot stage MI assignment input: original={original.exists()} planned={planned.exists()} path={original}"
            )
        shutil.copyfile(original, backup)
        shutil.copyfile(planned, original)


def _write_clear_summary(metrics: dict) -> None:
    outputs = ROOT / "outputs"
    lines = [
        "# v0.23 randomised-treatment assignment and population provenance",
        "",
        f"Input gate: **{'PASS' if metrics['all_passed'] else 'FAIL'}**",
        f"Controlled claim: `{metrics['assignment_claim']}`",
        "",
        f"- Subjects / randomised: **{metrics['subjects']} / {metrics['randomised_subjects']}**.",
        f"- Planned randomised counts: **{metrics['randomised_planned_counts']}**.",
        f"- Actual-treatment counts among randomised subjects: **{metrics['randomised_actual_counts']}**.",
        f"- Planned/actual mismatches: **{metrics['assignment_mismatches']}**; mismatch subjects in observed primary MMRM: **{metrics['mismatch_primary_mmrm_subjects']}**.",
        f"- Randomised baseline ACTOT / primary MMRM subjects: **{metrics['baseline_randomised_subjects']} / {metrics['primary_mmrm_subjects']}**.",
        f"- Randomised baseline subjects with no observed post-baseline ACTOT: **{metrics['randomised_baseline_no_observed_postbaseline']}**.",
        f"- Week 24 observed / missing: **{metrics['week24_observed']} / {metrics['week24_missing']}**.",
        f"- Planned-assignment pairwise MI target counts: **{metrics['pairwise_mi_target_counts']}**.",
        f"- Required checks: **{metrics['required_checks_passed']}/{metrics['required_checks']} PASS**.",
        "",
        "The MI-specific copies preserve the original actual-treatment value in `TRT01A_ACTUAL` while using planned randomised assignment as the grouping value for the controlled rbmi execution boundary.",
        "",
        "Independent public-data portfolio evidence only; not a sponsor-approved SAP amendment, production validation or regulatory decision.",
        "",
    ]
    (outputs / "mi_assignment_input_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    metrics = build_mi_assignment_inputs(ROOT)
    _write_clear_summary(metrics)
    _backup_and_stage()
    print(
        "MI assignment inputs: "
        f"randomised={metrics['randomised_subjects']}; "
        f"mismatches={metrics['assignment_mismatches']}; "
        f"mmrm_mismatches={metrics['mismatch_primary_mmrm_subjects']}; "
        f"pair_targets={metrics['pairwise_mi_target_counts']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"passed={metrics['all_passed']}; staged=planned"
    )

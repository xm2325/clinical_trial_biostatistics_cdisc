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
            raise FileNotFoundError(f"cannot stage MI assignment input: original={original.exists()} planned={planned.exists()} path={original}")
        shutil.copyfile(original, backup)
        shutil.copyfile(planned, original)


if __name__ == "__main__":
    metrics = build_mi_assignment_inputs(ROOT)
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

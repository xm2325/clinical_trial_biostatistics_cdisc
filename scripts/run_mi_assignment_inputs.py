from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mi_assignment import build_mi_assignment_inputs


if __name__ == "__main__":
    metrics = build_mi_assignment_inputs(ROOT)
    print(
        "MI assignment inputs: "
        f"randomised={metrics['randomised_subjects']}; "
        f"mismatches={metrics['assignment_mismatches']}; "
        f"mmrm_mismatches={metrics['mismatch_primary_mmrm_subjects']}; "
        f"pair_targets={metrics['pairwise_mi_target_counts']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"passed={metrics['all_passed']}"
    )

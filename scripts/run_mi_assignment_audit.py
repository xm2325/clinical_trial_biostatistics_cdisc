from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mi_assignment import assess_mi_assignment_outputs


if __name__ == "__main__":
    metrics = assess_mi_assignment_outputs(ROOT)
    print(
        "MI assignment audit: "
        f"pair_targets={metrics['executed_pairwise_mi_target_counts']}; "
        f"reference_rows={metrics['reference_based_rows']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"passed={metrics['all_passed']}"
    )

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.analysis_readiness import write_analysis_readiness_outputs


def main() -> None:
    metrics = write_analysis_readiness_outputs(ROOT)
    print(
        "Analysis readiness: "
        f"cutoff={metrics['analysis_data_cutoff']}; "
        f"subjects={metrics['subjects']}; randomized={metrics['randomized_subjects']}; "
        f"week24_missing={metrics['week24_actot_missing']}; "
        f"issues={metrics['known_issues_dispositioned']}/{metrics['known_issues']}; "
        f"blocking_open={metrics['blocking_open_issues']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

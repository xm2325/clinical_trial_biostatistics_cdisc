from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.analysis_readiness import write_analysis_closure_outputs


def main() -> None:
    metrics = write_analysis_closure_outputs(ROOT)
    print(
        "Analysis closure: "
        f"checks={metrics['closure_checks_passed']}/{metrics['closure_checks']}; "
        f"known_issues={metrics['readiness_known_issues']}; "
        f"blocking_open={metrics['readiness_blocking_open_issues']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

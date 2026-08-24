from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.sas_static_review import write_sas_static_review_outputs


def main() -> None:
    metrics = write_sas_static_review_outputs(ROOT)
    print(
        "SAS static review: "
        f"programs={metrics['programs_passed']}/{metrics['programs_expected']}; "
        f"sources={metrics['source_contracts_read']}/{metrics['source_contracts_expected']}; "
        f"semantics={metrics['matched_required_fragments']}/{metrics['required_fragments']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"runtime={metrics['runtime_status']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.statistical_review_queries import write_statistical_review_query_outputs


def main() -> None:
    metrics = write_statistical_review_query_outputs(ROOT)
    print(
        "Statistical review responses: "
        f"queries={metrics['query_rows']}; "
        f"primary_rejections={metrics['primary_familywise_rejections']}/{metrics['primary_hypotheses']}; "
        f"week24_missing={metrics['week24_missing']}/{metrics['week24_randomized']}; "
        f"rbmi_mcse={metrics['reference_based_mcse_passed']}/{metrics['reference_based_rows']}; "
        f"mismatches={metrics['planned_actual_treatment_mismatches']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

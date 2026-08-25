from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.statistical_change_decision import write_statistical_change_decision  # noqa: E402
from cdisc_portfolio.study_statistician_decision_suite import write_study_statistician_decision_suite  # noqa: E402


if __name__ == "__main__":
    decision_metrics = write_statistical_change_decision(ROOT)
    suite_metrics = write_study_statistician_decision_suite(ROOT)
    print(json.dumps({
        "statistical_change_decision": decision_metrics,
        "study_statistician_decision_suite": suite_metrics,
    }, indent=2, sort_keys=True))

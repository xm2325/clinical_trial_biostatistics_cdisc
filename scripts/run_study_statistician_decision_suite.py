from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.study_statistician_decision_suite import write_study_statistician_decision_suite  # noqa: E402


if __name__ == "__main__":
    metrics = write_study_statistician_decision_suite(ROOT)
    print(json.dumps(metrics, indent=2, sort_keys=True))

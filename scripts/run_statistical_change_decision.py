from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.statistical_change_decision import write_statistical_change_decision  # noqa: E402


if __name__ == "__main__":
    metrics = write_statistical_change_decision(ROOT)
    print(json.dumps(metrics, indent=2, sort_keys=True))

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.design_operating_characteristics import write_design_operating_characteristics  # noqa: E402


if __name__ == "__main__":
    metrics = write_design_operating_characteristics(ROOT)
    print(json.dumps(metrics, indent=2, sort_keys=True))

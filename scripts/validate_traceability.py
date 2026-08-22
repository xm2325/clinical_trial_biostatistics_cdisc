from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.traceability import write_traceability_outputs  # noqa: E402


if __name__ == "__main__":
    metrics = write_traceability_outputs(ROOT)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not metrics["all_passed"]:
        raise SystemExit("Required SAP-to-TLF traceability validation failed; see outputs/traceability_validation.csv")

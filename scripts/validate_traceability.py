from __future__ import annotations

import json
from pathlib import Path

from cdisc_portfolio.traceability import write_traceability_outputs


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    metrics = write_traceability_outputs(root)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not metrics["all_passed"]:
        raise SystemExit("Required SAP-to-TLF traceability validation failed; see outputs/traceability_validation.csv")

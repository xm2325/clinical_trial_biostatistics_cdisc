from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.core_validation import write_core_unavailable_outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record controlled CDISC CORE ADaMIG no-execution evidence when the pinned official ruleset is unavailable"
    )
    parser.add_argument("--cache-manifest", required=True, type=Path)
    args = parser.parse_args()
    metrics = write_core_unavailable_outputs(ROOT, args.cache_manifest)
    print(
        "CORE executable validation availability: "
        f"status={metrics['execution_status']}; performed={metrics['executable_validation_performed']}; "
        f"rules={metrics['rules_executed']}; passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

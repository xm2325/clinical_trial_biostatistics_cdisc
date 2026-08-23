from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.core_validation import write_core_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage a pinned official CDISC CORE JSON report")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--cli-exit-code", type=int, default=0)
    args = parser.parse_args()
    metrics = write_core_outputs(ROOT, args.report, cli_exit_code=args.cli_exit_code)
    print(
        "CORE triage: "
        f"rules={metrics['rules_total']}; executed={metrics['rules_executed']}; "
        f"success={metrics['success_rules']}; issues={metrics['issue_reported_rules']}; "
        f"skipped={metrics['skipped_rules']}; execution_errors={metrics['execution_error_rules']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()

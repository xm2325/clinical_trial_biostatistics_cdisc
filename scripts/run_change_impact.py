from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.change_control_v018 import run_change_impact_assessment


def main() -> None:
    output_dir = ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows, metrics, summary = run_change_impact_assessment(ROOT)

    csv_path = output_dir / "change_impact_assessment.csv"
    fieldnames = [
        "change_id",
        "title",
        "category",
        "resource",
        "resolved_path",
        "required_by_graph",
        "declared_for_review",
        "resource_exists",
        "status",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    (output_dir / "change_impact_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "change_impact_summary.md").write_text(summary, encoding="utf-8")

    print(summary)
    if not metrics["all_passed"]:
        raise SystemExit("Statistical change-impact gate failed; inspect outputs/change_impact_assessment.csv")


if __name__ == "__main__":
    main()

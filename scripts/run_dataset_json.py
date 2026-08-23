from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.dataset_json import write_exchange_outputs


if __name__ == "__main__":
    metrics = write_exchange_outputs(ROOT)
    print(
        f"Dataset-JSON: datasets={metrics['datasets']}; variables={metrics['variables']}; "
        f"records={metrics['records']}; nulls={metrics['null_values_preserved']}; "
        f"schema_errors={metrics['official_schema_errors']}; passed={metrics['all_passed']}"
    )

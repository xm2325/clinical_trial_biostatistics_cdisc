from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_dataset_contracts(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dataset_contract(frame: pd.DataFrame, contract: dict[str, object]) -> tuple[bool, str]:
    required_columns = list(contract.get("required_columns", []))
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        return False, f"missing columns={missing_columns}"

    key = list(contract.get("key", []))
    duplicate_keys = int(frame.duplicated(key).sum()) if key else 0

    missing_required_values = 0
    for column in contract.get("non_missing", []):
        series = frame[column]
        blank = series.isna() | series.fillna("").astype(str).str.strip().eq("")
        missing_required_values += int(blank.sum())

    controlled_value_violations = 0
    controlled_details: list[str] = []
    for column, rule in contract.get("controlled_values", {}).items():
        series = frame[column]
        blank = series.isna() | series.fillna("").astype(str).str.strip().eq("")
        allowed = {str(value) for value in rule.get("values", [])}
        bad_nonblank = (~blank) & ~series.astype(str).isin(allowed)
        bad_blank = blank if not bool(rule.get("allow_blank", False)) else pd.Series(False, index=series.index)
        bad_count = int((bad_nonblank | bad_blank).sum())
        controlled_value_violations += bad_count
        if bad_count:
            controlled_details.append(f"{column}={bad_count}")

    passed = duplicate_keys + missing_required_values + controlled_value_violations == 0
    detail = (
        f"duplicate keys={duplicate_keys}; missing required values={missing_required_values}; "
        f"controlled-value violations={controlled_value_violations}"
    )
    if controlled_details:
        detail += f" ({', '.join(controlled_details)})"
    return passed, detail


def review_dataset_contracts(
    frames: dict[str, pd.DataFrame],
    contract_spec: dict[str, object],
) -> pd.DataFrame:
    checks: list[dict[str, object]] = []
    for dataset_name, contract in contract_spec.get("datasets", {}).items():
        if dataset_name not in frames:
            checks.append(
                {
                    "check": f"{contract.get('label', dataset_name)} dataset contract",
                    "passed": False,
                    "required": True,
                    "area": "metadata_contract",
                    "detail": f"review frame '{dataset_name}' not loaded",
                }
            )
            continue
        passed, detail = validate_dataset_contract(frames[dataset_name], contract)
        checks.append(
            {
                "check": f"{contract.get('label', dataset_name)} dataset contract",
                "passed": bool(passed),
                "required": True,
                "area": "metadata_contract",
                "detail": detail,
            }
        )
    return pd.DataFrame(checks)

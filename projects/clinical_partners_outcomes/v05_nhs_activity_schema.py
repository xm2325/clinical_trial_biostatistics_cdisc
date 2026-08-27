from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from v03_nhs_schema_audit import read_csv_flex

TARGET_MEASURES = [
    "Count_FinishedCourseTreatment",
    "Count_ReliableImprovement",
    "Percentage_ReliableImprovement",
    "Count_ReliableDeterioration",
    "Percentage_ReliableDeterioration",
    "Count_Recovery",
    "Count_NotAtCaseness",
    "Percentage_Recovery",
    "Count_ReliableRecovery",
    "Percentage_ReliableRecovery",
]


def infer_value_column(df: pd.DataFrame) -> str | None:
    preferred = ["MEASURE_VALUE", "MEASURE_VALUE_NUMERATOR", "VALUE", "MEASURE_VALUE_NUMERIC"]
    for col in preferred:
        if col in df.columns:
            return col
    candidates = [c for c in df.columns if "VALUE" in c.upper()]
    return candidates[0] if len(candidates) == 1 else None


def audit_activity_file(df: pd.DataFrame) -> dict:
    required = {"GROUP_TYPE", "ORG_CODE2", "ORG_NAME2", "MEASURE_NAME"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"NHS monthly activity file missing expected identity columns: {missing}")

    measures = sorted(df["MEASURE_NAME"].dropna().astype(str).unique())
    target_present = [m for m in TARGET_MEASURES if m in measures]
    target_missing = [m for m in TARGET_MEASURES if m not in measures]
    provider = df[df["GROUP_TYPE"].eq("Provider")].copy()
    value_column = infer_value_column(df)

    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "value_column": value_column,
        "value_like_columns": [c for c in df.columns if "VALUE" in c.upper()],
        "n_measure_names": int(len(measures)),
        "n_provider_rows": int(len(provider)),
        "n_provider_codes": int(provider["ORG_CODE2"].nunique()),
        "target_measures_present": target_present,
        "target_measures_missing": target_missing,
        "all_measure_names": measures,
    }


def main(path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flex(path)
    summary = audit_activity_file(df)
    (outdir / "v05_nhs_activity_schema_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    pd.DataFrame({"measure_name": summary["all_measure_names"]}).to_csv(
        outdir / "v05_nhs_activity_measure_names.csv", index=False
    )

    target_rows = df[df["MEASURE_NAME"].isin(summary["target_measures_present"])].head(30)
    target_rows.to_csv(outdir / "v05_nhs_activity_target_row_sample.csv", index=False)

    compact = {k: v for k, v in summary.items() if k != "all_measure_names"}
    print("V05_NHS_ACTIVITY_SCHEMA:", json.dumps(compact))
    print("V05_NHS_ACTIVITY_MEASURES:", json.dumps(summary["all_measure_names"]))
    print("V05_NHS_ACTIVITY_TARGET_ROWS:\n", target_rows.to_string(index=False))

    if not summary["target_measures_present"]:
        raise RuntimeError("No target outcome measures were found in the NHS monthly activity file")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

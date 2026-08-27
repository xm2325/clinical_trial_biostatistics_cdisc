from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

KEYWORDS = [
    "recover", "reliable improvement", "deterior", "6 week", "18 week",
    "waiting", "course of treatment", "caseness", "provider", "organisation",
]


def read_csv_flex(path: Path) -> pd.DataFrame:
    errors = []
    for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, low_memory=False, encoding=encoding)
        except Exception as exc:
            errors.append(f"{encoding}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Could not read NHS CSV; " + " | ".join(errors))


def keyword_hits(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col].astype(str)
        mask = pd.Series(False, index=df.index)
        for keyword in KEYWORDS:
            mask = mask | s.str.contains(keyword, case=False, na=False, regex=False)
        if mask.any():
            examples = s[mask].drop_duplicates().head(25).tolist()
            rows.append({
                "column": col,
                "n_matching_rows": int(mask.sum()),
                "examples": " || ".join(examples),
            })
    return pd.DataFrame(rows)


def main(path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flex(path)
    schema = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "missing_fraction": [float(df[c].isna().mean()) for c in df.columns],
        "n_unique": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    schema.to_csv(outdir / "nhs_time_series_schema.csv", index=False)
    hits = keyword_hits(df)
    hits.to_csv(outdir / "nhs_time_series_keyword_hits.csv", index=False)

    object_samples = []
    for col in df.select_dtypes(include=["object"]).columns:
        vals = df[col].dropna().astype(str).drop_duplicates().head(30).tolist()
        object_samples.append({"column": col, "examples": " || ".join(vals)})
    object_samples_df = pd.DataFrame(object_samples)
    object_samples_df.to_csv(outdir / "nhs_time_series_object_samples.csv", index=False)

    summary = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "keyword_hit_columns": int(len(hits)),
        "source": "NHS Talking Therapies Monthly Time Series for Key Measures, June 2025-June 2026; publication dated 13 August 2026",
        "interpretation_boundary": "This file contains published aggregate statistics. It supports provider/service benchmarking and temporal monitoring, not patient-level causal inference.",
    }
    (outdir / "nhs_time_series_schema_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    # CI-visible compact schema trace so benchmark code is built from the real NHS file,
    # not from assumptions about a historical release schema.
    print("NHS_COLUMNS:", json.dumps(list(df.columns)))
    print("NHS_SCHEMA:\n", schema.to_string(index=False))
    print("NHS_KEYWORD_HITS:\n", hits.to_string(index=False))
    print("NHS_OBJECT_SAMPLES:\n", object_samples_df.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)

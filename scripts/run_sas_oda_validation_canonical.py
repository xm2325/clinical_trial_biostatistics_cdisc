"""Run the v0.26.1 SAS ODA reconciliation with transport-safe key canonicalisation.

SASPy can round-trip numeric identifiers such as AESEQ as floating-point values
(e.g. 1 -> 1.0), while pandas/R references may retain integer dtypes. Visit
labels can likewise differ only by case after transport. These differences do
not change record identity, so this wrapper canonicalises *keys only* before the
existing reconciliation functions run. Statistical values, derivations, model
outputs and tolerances are unchanged.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_sas_oda_validation.py"

spec = importlib.util.spec_from_file_location("sas_oda_validation_base", TARGET)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load {TARGET}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

_original_compare_keys = module._compare_keys
_original_compare_columns = module._compare_columns


def _canonical_key(series: pd.Series, key: str) -> pd.Series:
    key_upper = key.upper()
    if key_upper.endswith("SEQ") or key_upper.endswith("VISITN"):
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.map(
            lambda value: "" if pd.isna(value) else f"{float(value):.15g}"
        )
    text = series.fillna("").astype(str).str.strip()
    if key_upper in {"AVISIT", "PARAM", "PARAMCD"}:
        return text.str.upper()
    return text


def _canonical_frame(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for key in keys:
        out[key] = _canonical_key(out[key], key)
    return out


def _compare_keys(area, sas_df, ref_df, keys, rows):
    return _original_compare_keys(
        area,
        _canonical_frame(sas_df, keys),
        _canonical_frame(ref_df, keys),
        keys,
        rows,
    )


def _compare_columns(
    area,
    sas_df,
    ref_df,
    keys,
    string_cols,
    numeric_cols,
    date_cols,
    rows,
    numeric_tol=1e-10,
):
    return _original_compare_columns(
        area,
        _canonical_frame(sas_df, keys),
        _canonical_frame(ref_df, keys),
        keys,
        string_cols,
        numeric_cols,
        date_cols,
        rows,
        numeric_tol,
    )


module._compare_keys = _compare_keys
module._compare_columns = _compare_columns

if __name__ == "__main__":
    module.main()

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pyreadstat
import saspy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SPEC_PATH = ROOT / "spec" / "submission_projection_v0_28.json"
XPT_DIR = OUT / "submission_xpt_v0_28"
XPT_DIR.mkdir(parents=True, exist_ok=True)

KEYS = {
    "ADSL": ["STUDYID", "USUBJID"],
    "ADAE": ["STUDYID", "USUBJID", "AESEQ"],
    "ADQS": ["STUDYID", "USUBJID", "QSSEQ"],
    "ADTTE": ["STUDYID", "USUBJID", "PARAMCD"],
}
NUMERIC_KEYS = {"AESEQ", "QSSEQ"}
CONTROLLED_CLAIM = "PORTFOLIO_SAS_ODA_XPORT_V5_HANDOFF_RECONCILED"
EVIDENCE_BOUNDARY = (
    "SAS XPORT v5 files were written by SAS OnDemand for Academics from an explicit FDA-compatible projection of controlled "
    "public-data portfolio analysis datasets and independently read back on the GitHub runner. Long-name audit/helper variables "
    "remain in the full portfolio datasets but are excluded from the submission projection rather than silently truncated or aliased. "
    "This is submission-style portfolio evidence only; it is not a validated GxP environment, sponsor/CRO production, formal ADaM "
    "conformance, or an FDA submission."
)


def _load_spec() -> dict[str, object]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=[])


def _norm(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normalise keys by transport semantics without weakening character identifiers.

    SAS XPORT stores AESEQ/QSSEQ as SAS numerics, so integer-valued source keys can
    legitimately round-trip through pyreadstat as floats (for example 1 -> 1.0).
    Character identifiers remain exact trimmed strings; only the explicitly known
    numeric sequence keys receive numeric-semantic normalisation.
    """
    out = frame.loc[:, columns].copy()
    for col in columns:
        if col in NUMERIC_KEYS:
            numeric = pd.to_numeric(out[col], errors="raise")
            out[col] = numeric.map(
                lambda value: "" if pd.isna(value) else format(float(value), ".15g")
            )
        else:
            out[col] = out[col].fillna("").astype(str).str.strip()
    return out


def _project(dataset: str, source: Path, excluded: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    frame = _read_csv(source)
    missing = sorted(set(excluded).difference(frame.columns))
    if missing:
        raise RuntimeError(f"{dataset}: projection spec references missing columns: {missing}")
    actual_long = sorted(col for col in frame.columns if len(col) > 8)
    if sorted(excluded) != actual_long:
        raise RuntimeError(
            f"{dataset}: every >8-char source variable must be explicitly excluded and no <=8-char variable may be excluded; "
            f"spec={sorted(excluded)} actual={actual_long}"
        )
    projected = frame.drop(columns=excluded)
    bad_names = sorted(col for col in projected.columns if len(col) > 8 or not col.isascii())
    if bad_names:
        raise RuntimeError(f"{dataset}: XPORT v5 projection has incompatible variable names: {bad_names}")

    too_wide: dict[str, int] = {}
    for col in projected.columns:
        if pd.api.types.is_object_dtype(projected[col]) or pd.api.types.is_string_dtype(projected[col]):
            max_len = int(projected[col].fillna("").astype(str).map(len).max()) if len(projected) else 0
            if max_len > 200:
                too_wide[col] = max_len
    if too_wide:
        raise RuntimeError(f"{dataset}: XPORT v5 character values exceed 200 characters: {too_wide}")

    projection_metrics = {
        "dataset": dataset,
        "source_rows": int(len(frame)),
        "source_columns": int(len(frame.columns)),
        "excluded_columns": excluded,
        "submission_columns": int(len(projected.columns)),
        "all_variable_names_le_8": True,
        "all_character_values_le_200": True,
    }
    return projected, projection_metrics


def _upload(sas: saspy.SASsession, frame: pd.DataFrame, table: str) -> None:
    sas.df2sd(frame, table=table.lower(), libref="work")
    if not sas.exist(table.lower(), "work"):
        raise RuntimeError(f"WORK.{table} was not created on SAS ODA")


def _export_one(
    sas: saspy.SASsession,
    dataset: str,
    frame: pd.DataFrame,
    projection: dict[str, object],
) -> tuple[Path, dict[str, object]]:
    _upload(sas, frame, dataset)
    remote = f"{sas.workpath}{dataset.lower()}.xpt"
    code = f'''
libname _xpt xport "{remote}";
proc copy in=work out=_xpt memtype=data;
  select {dataset.lower()};
run;
libname _xpt clear;
'''
    result = sas.submit(code, results="text")
    log = str(result.get("LOG", ""))
    if "ERROR:" in log.upper():
        raise RuntimeError(f"SAS XPORT export failed for {dataset}: {log[-2500:]}")

    local = XPT_DIR / f"{dataset.lower()}.xpt"
    transfer = sas.download(str(local), remote, overwrite=True)
    if not transfer.get("Success") or not local.exists() or local.stat().st_size == 0:
        raise RuntimeError(f"SASPy download failed for {dataset}: {transfer}")

    roundtrip, meta = pyreadstat.read_xport(str(local), disable_datetime_conversion=True)
    expected_cols = list(frame.columns)
    got_cols = list(roundtrip.columns)
    row_ok = len(roundtrip) == len(frame)
    columns_ok = got_cols == expected_cols
    table_name = str(getattr(meta, "table_name", "") or "").upper()
    table_ok = table_name == dataset

    keys = [key for key in KEYS[dataset] if key in frame.columns]
    key_ok = True
    duplicate_count = 0
    if keys:
        left = _norm(frame, keys)
        right = _norm(roundtrip, keys)
        duplicate_count = int(right.duplicated(keys).sum())
        key_ok = (
            set(map(tuple, left.to_numpy())) == set(map(tuple, right.to_numpy()))
            and duplicate_count == 0
        )

    qc = {
        "dataset": dataset,
        "xpt_file": local.name,
        "xpt_bytes": local.stat().st_size,
        "source_rows": int(projection["source_rows"]),
        "source_columns": int(projection["source_columns"]),
        "excluded_columns": "|".join(projection["excluded_columns"]),
        "submission_columns": int(projection["submission_columns"]),
        "roundtrip_rows": int(len(roundtrip)),
        "row_count_pass": bool(row_ok),
        "column_order_pass": bool(columns_ok),
        "table_name": table_name,
        "table_name_pass": bool(table_ok),
        "key_columns": "|".join(keys),
        "key_set_pass": bool(key_ok),
        "roundtrip_duplicate_keys": duplicate_count,
        "xport_name_limit_pass": bool(projection["all_variable_names_le_8"]),
        "xport_character_width_pass": bool(projection["all_character_values_le_200"]),
        "required_pass": bool(
            row_ok
            and columns_ok
            and table_ok
            and key_ok
            and projection["all_variable_names_le_8"]
            and projection["all_character_values_le_200"]
        ),
    }
    return local, qc


def main() -> None:
    cfgfile = os.environ.get("SASPY_CFGFILE")
    if not cfgfile:
        raise SystemExit("SASPY_CFGFILE is not set")

    spec = _load_spec()
    dataset_specs = spec["datasets"]
    sources = {dataset: OUT / cfg["source_file"] for dataset, cfg in dataset_specs.items()}
    missing = [str(path.relative_to(ROOT)) for path in sources.values() if not path.exists()]
    if missing:
        raise SystemExit(f"Controlled analysis datasets missing before XPORT export: {missing}")

    projected: dict[str, pd.DataFrame] = {}
    projection_metrics: dict[str, dict[str, object]] = {}
    for dataset, cfg in dataset_specs.items():
        frame, metrics = _project(dataset, sources[dataset], list(cfg["exclude_from_submission"]))
        projected[dataset] = frame
        projection_metrics[dataset] = metrics
        frame.to_csv(XPT_DIR / f"{dataset}.csv", index=False)

    qc_rows: list[dict[str, object]] = []
    sas = saspy.SASsession(cfgname="oda", cfgfile=cfgfile, results="TEXT")
    try:
        for dataset, frame in projected.items():
            _, qc = _export_one(sas, dataset, frame, projection_metrics[dataset])
            qc_rows.append(qc)
    finally:
        try:
            sas.endsas()
        except Exception:
            pass

    qc = pd.DataFrame(qc_rows)
    qc_path = OUT / "submission_xpt_v0_28_qc.csv"
    qc.to_csv(qc_path, index=False)
    all_passed = bool(qc["required_pass"].all())
    metrics = {
        "version": "0.28.0",
        "sas_runtime": "SAS OnDemand for Academics via SASPy Remote IOM",
        "xport_writer": "SAS LIBNAME XPORT",
        "xport_version": 5,
        "projection_policy": spec["policy"],
        "datasets_exported": int(len(qc)),
        "datasets_roundtrip_passed": int(qc["required_pass"].sum()),
        "excluded_audit_helper_variables": int(
            sum(len(cfg["exclude_from_submission"]) for cfg in dataset_specs.values())
        ),
        "all_required_passed": all_passed,
        "controlled_claim": CONTROLLED_CLAIM if all_passed else None,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    (OUT / "submission_xpt_v0_28_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = (
        "# v0.28 SAS XPORT v5 export\n\n"
        f"- SAS runtime: **{metrics['sas_runtime']}**\n"
        f"- Writer: **{metrics['xport_writer']}**\n"
        f"- XPORT version: **{metrics['xport_version']}**\n"
        f"- Explicitly excluded long-name audit/helper variables: **{metrics['excluded_audit_helper_variables']}**\n"
        f"- Dataset round-trip checks: **{metrics['datasets_roundtrip_passed']}/{metrics['datasets_exported']}**\n"
        f"- Controlled claim: `{metrics['controlled_claim']}`\n\n"
        f"Projection policy: {metrics['projection_policy']}\n\n"
        f"Evidence boundary: {EVIDENCE_BOUNDARY}\n"
    )
    (OUT / "submission_xpt_v0_28_summary.md").write_text(summary, encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not all_passed:
        raise SystemExit(
            "SAS XPORT v5 handoff gate failed; inspect outputs/submission_xpt_v0_28_qc.csv"
        )


if __name__ == "__main__":
    main()

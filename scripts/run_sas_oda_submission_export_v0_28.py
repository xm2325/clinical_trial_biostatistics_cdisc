from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pyreadstat
import saspy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
XPT_DIR = OUT / "submission_xpt_v0_28"
XPT_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "ADSL": OUT / "adsl_style.csv",
    "ADAE": OUT / "adae_style.csv",
    "ADQS": OUT / "adqs_actot_style.csv",
    "ADTTE": OUT / "adtte_retention_style.csv",
}
KEYS = {
    "ADSL": ["STUDYID", "USUBJID"],
    "ADAE": ["STUDYID", "USUBJID", "AESEQ"],
    "ADQS": ["STUDYID", "USUBJID", "QSSEQ"],
    "ADTTE": ["STUDYID", "USUBJID", "PARAMCD"],
}
CONTROLLED_CLAIM = "PORTFOLIO_SAS_ODA_XPORT_V5_HANDOFF_RECONCILED"
EVIDENCE_BOUNDARY = (
    "SAS XPORT v5 files were written by SAS OnDemand for Academics from controlled public-data portfolio datasets "
    "and independently read back on the GitHub runner. This is submission-style portfolio evidence only; it is not "
    "a validated GxP environment, sponsor/CRO production, formal ADaM conformance, or an FDA submission."
)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=[])


def _norm(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.loc[:, columns].copy()
    for col in columns:
        out[col] = out[col].fillna("").astype(str).str.strip()
    return out


def _upload(sas: saspy.SASsession, frame: pd.DataFrame, table: str) -> None:
    sas.df2sd(frame, table=table.lower(), libref="work")
    if not sas.exist(table.lower(), "work"):
        raise RuntimeError(f"WORK.{table} was not created on SAS ODA")


def _export_one(sas: saspy.SASsession, dataset: str, frame: pd.DataFrame) -> tuple[Path, dict[str, object]]:
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
        key_ok = set(map(tuple, left.to_numpy())) == set(map(tuple, right.to_numpy())) and duplicate_count == 0

    qc = {
        "dataset": dataset,
        "xpt_file": local.name,
        "xpt_bytes": local.stat().st_size,
        "source_rows": int(len(frame)),
        "roundtrip_rows": int(len(roundtrip)),
        "row_count_pass": bool(row_ok),
        "column_order_pass": bool(columns_ok),
        "table_name": table_name,
        "table_name_pass": bool(table_ok),
        "key_columns": "|".join(keys),
        "key_set_pass": bool(key_ok),
        "roundtrip_duplicate_keys": duplicate_count,
        "required_pass": bool(row_ok and columns_ok and table_ok and key_ok),
    }
    return local, qc


def main() -> None:
    cfgfile = os.environ.get("SASPY_CFGFILE")
    if not cfgfile:
        raise SystemExit("SASPY_CFGFILE is not set")
    missing = [str(path.relative_to(ROOT)) for path in DATASETS.values() if not path.exists()]
    if missing:
        raise SystemExit(f"Controlled analysis datasets missing before XPORT export: {missing}")

    frames = {name: _read_csv(path) for name, path in DATASETS.items()}
    qc_rows: list[dict[str, object]] = []
    sas = saspy.SASsession(cfgname="oda", cfgfile=cfgfile, results="TEXT")
    try:
        for dataset, frame in frames.items():
            _, qc = _export_one(sas, dataset, frame)
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
        "datasets_exported": int(len(qc)),
        "datasets_roundtrip_passed": int(qc["required_pass"].sum()),
        "all_required_passed": all_passed,
        "controlled_claim": CONTROLLED_CLAIM if all_passed else None,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    (OUT / "submission_xpt_v0_28_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = (
        "# v0.28 SAS XPORT v5 export\n\n"
        f"- SAS runtime: **{metrics['sas_runtime']}**\n"
        f"- Writer: **{metrics['xport_writer']}**\n"
        f"- XPORT version: **{metrics['xport_version']}**\n"
        f"- Dataset round-trip checks: **{metrics['datasets_roundtrip_passed']}/{metrics['datasets_exported']}**\n"
        f"- Controlled claim: `{metrics['controlled_claim']}`\n\n"
        f"Evidence boundary: {EVIDENCE_BOUNDARY}\n"
    )
    (OUT / "submission_xpt_v0_28_summary.md").write_text(summary, encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not all_passed:
        raise SystemExit("SAS XPORT v5 handoff gate failed; inspect outputs/submission_xpt_v0_28_qc.csv")


if __name__ == "__main__":
    main()

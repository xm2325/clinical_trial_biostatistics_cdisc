from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from jsonschema import Draft201909Validator

VERSION = "0.19.0"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_value(value: Any, data_type: str) -> Any:
    if pd.isna(value):
        return None
    if data_type == "integer":
        return int(value)
    if data_type == "double":
        return float(value)
    return str(value)


def _physical_type(series: pd.Series, logical_type: str) -> str:
    if logical_type == "date":
        return "date"
    if logical_type != "numeric":
        return "string"
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty or bool(((values - values.round()).abs() < 1e-12).all()):
        return "integer"
    return "double"


def _string_length(series: pd.Series) -> int:
    values = series.dropna().astype(str)
    return max(1, max((len(v) for v in values), default=1))


def build_dataset_json(dataset: dict[str, Any], frame: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    alias = dataset["alias"]
    metadata_by_name = {v["name"]: v for v in dataset["variables"]}
    columns = []
    physical_types: dict[str, str] = {}
    for index, name in enumerate(frame.columns, start=1):
        if name not in metadata_by_name:
            raise ValueError(f"{alias}.{name} missing from v0.18 metadata catalog")
        meta = metadata_by_name[name]
        physical = _physical_type(frame[name], meta["data_type"])
        physical_types[name] = physical
        column = {
            "itemOID": f"IT.{alias}.{name}",
            "name": name,
            "label": meta["label"],
            "dataType": physical,
        }
        if physical == "string":
            column["length"] = _string_length(frame[name])
        elif physical == "date":
            column["targetDataType"] = "integer"
            column["displayFormat"] = "E8601DA."
        if name in dataset["keys"]:
            column["keySequence"] = dataset["keys"].index(name) + 1
        columns.append(column)

    rows = [
        [_json_value(value, physical_types[name]) for name, value in zip(frame.columns, row)]
        for row in frame.itertuples(index=False, name=None)
    ]
    dj_cfg = cfg["dataset_json"]
    return {
        "datasetJSONCreationDateTime": dj_cfg["creation_datetime"],
        "datasetJSONVersion": dj_cfg["version"],
        "fileOID": f"PORTFOLIO.{alias}.V019",
        "originator": dj_cfg["originator"],
        "sourceSystem": dj_cfg["source_system"],
        "itemGroupOID": f"IG.{alias}",
        "records": len(frame),
        "name": alias,
        "label": dataset["label"],
        "columns": columns,
        "rows": rows,
    }


def _compare_round_trip(frame: pd.DataFrame, payload: dict[str, Any]) -> tuple[bool, str]:
    names = [c["name"] for c in payload["columns"]]
    if names != list(frame.columns):
        return False, "column order mismatch"
    if payload["records"] != len(frame) or len(payload["rows"]) != len(frame):
        return False, "record count mismatch"
    if any(len(row) != len(names) for row in payload["rows"]):
        return False, "row width mismatch"

    rebuilt = pd.DataFrame(payload["rows"], columns=names)
    for column_meta in payload["columns"]:
        name = column_meta["name"]
        kind = column_meta["dataType"]
        left = frame[name]
        right = rebuilt[name]
        if not left.isna().equals(right.isna()):
            return False, f"{name}: missing-value mask mismatch"
        mask = ~left.isna()
        if kind in {"integer", "double"}:
            l = pd.to_numeric(left[mask], errors="coerce").astype(float).to_numpy()
            r = pd.to_numeric(right[mask], errors="coerce").astype(float).to_numpy()
            if len(l) != len(r) or any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12) for a, b in zip(l, r)):
                return False, f"{name}: numeric round-trip mismatch"
        else:
            if left[mask].astype(str).tolist() != right[mask].astype(str).tolist():
                return False, f"{name}: string/date round-trip mismatch"
    return True, "exact values/null masks preserved"


def _validate_official_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft201909Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    result = []
    for error in errors:
        path = "/".join(str(x) for x in error.absolute_path)
        result.append(f"{path}: {error.message}" if path else error.message)
    return result


def write_exchange_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    cfg = json.loads((root / "spec" / "standards_validation_v0_19.json").read_text(encoding="utf-8"))
    if cfg.get("version") != VERSION:
        raise ValueError("standards-validation config must be version 0.19.0")
    if cfg["core"].get("conformance_claim") != "NOT_ASSESSED":
        raise ValueError("CORE conformance claim must remain NOT_ASSESSED")
    catalog = json.loads((root / "outputs" / "adam_variable_metadata.json").read_text(encoding="utf-8"))
    if catalog.get("version") != "0.18.0":
        raise ValueError("v0.19 exchange must consume validated v0.18 metadata catalog")

    schema_path = root / cfg["dataset_json"]["schema_relative_path"]
    if not schema_path.is_file():
        raise ValueError(f"official Dataset-JSON schema not found: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    out_dir = root / "outputs" / "dataset_json"
    core_dir = root / "outputs" / "core_input"
    out_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)

    validation_rows: list[dict[str, Any]] = []
    dataset_rows: list[dict[str, Any]] = []
    variable_rows: list[dict[str, Any]] = []
    total_records = total_variables = total_nulls = total_schema_errors = 0

    for dataset in catalog["datasets"]:
        source = root / dataset["file"]
        frame = pd.read_csv(source)
        payload = build_dataset_json(dataset, frame, cfg)
        target = out_dir / f"{dataset['alias'].lower()}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        parsed = json.loads(target.read_text(encoding="utf-8"))
        round_trip_ok, round_trip_detail = _compare_round_trip(frame, parsed)
        schema_errors = _validate_official_schema(parsed, schema)
        key_sequence = [c["name"] for c in parsed["columns"] if "keySequence" in c]
        key_ok = key_sequence == dataset["keys"]
        dates_ok = all(
            c.get("targetDataType") == "integer" and c.get("displayFormat") == "E8601DA."
            for c in parsed["columns"] if c["dataType"] == "date"
        )
        nulls = sum(value is None for row in parsed["rows"] for value in row)

        validation_rows.extend([
            {"dataset": dataset["alias"], "check": "official Dataset-JSON 1.1 schema", "passed": len(schema_errors) == 0, "detail": f"errors={len(schema_errors)}"},
            {"dataset": dataset["alias"], "check": "record and value round-trip", "passed": round_trip_ok, "detail": round_trip_detail},
            {"dataset": dataset["alias"], "check": "keySequence follows controlled metadata", "passed": key_ok, "detail": f"keys={key_sequence}"},
            {"dataset": dataset["alias"], "check": "ADaM date exchange metadata", "passed": dates_ok, "detail": "date + targetDataType=integer + E8601DA."},
        ])
        for error in schema_errors[:100]:
            validation_rows.append({"dataset": dataset["alias"], "check": "official schema error", "passed": False, "detail": error})

        core_target = core_dir / f"{dataset['alias']}.csv"
        shutil.copyfile(source, core_target)
        dataset_rows.append({"Filename": dataset["alias"], "Dataset Name": dataset["alias"], "Label": dataset["label"]})
        for column in parsed["columns"]:
            ctype = column["dataType"]
            if ctype == "date":
                core_type = "integer"
                length = ""
            elif ctype in {"integer", "double"}:
                core_type = ctype
                length = ""
            else:
                core_type = "string"
                length = column.get("length", "")
            variable_rows.append({"dataset": dataset["alias"], "variable": column["name"], "label": column["label"], "type": core_type, "length": length})

        total_records += len(frame)
        total_variables += len(frame.columns)
        total_nulls += nulls
        total_schema_errors += len(schema_errors)

    pd.DataFrame(dataset_rows).to_csv(core_dir / "_datasets.csv", index=False)
    pd.DataFrame(variable_rows).to_csv(core_dir / "_variables.csv", index=False)
    validation = pd.DataFrame(validation_rows)
    validation.to_csv(root / "outputs" / "dataset_json_validation.csv", index=False)

    required = validation[validation["check"] != "official schema error"]
    all_passed = bool(required["passed"].all() and total_schema_errors == 0)
    metrics = {
        "analysis_version": VERSION,
        "dataset_json_version": cfg["dataset_json"]["version"],
        "official_schema_repository": cfg["dataset_json"]["official_repository"],
        "official_schema_commit": cfg["dataset_json"]["official_commit"],
        "datasets": len(catalog["datasets"]),
        "variables": total_variables,
        "records": total_records,
        "null_values_preserved": total_nulls,
        "official_schema_errors": total_schema_errors,
        "core_transport_datasets": len(dataset_rows),
        "core_transport_variables": len(variable_rows),
        "conformance_claim": "NOT_ASSESSED",
        "dataset_json_sha256": {p.name: _sha256(p) for p in sorted(out_dir.glob("*.json"))},
        "all_passed": all_passed,
    }
    (root / "outputs" / "dataset_json_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = [
        "# Dataset-JSON 1.1 exchange validation",
        "",
        f"- Datasets: {metrics['datasets']}.",
        f"- Variables: {metrics['variables']}.",
        f"- Records exchanged: {metrics['records']}.",
        f"- Missing values preserved as JSON null: {metrics['null_values_preserved']}.",
        f"- Official Dataset-JSON schema errors: {metrics['official_schema_errors']}.",
        f"- CORE CSV transport metadata: {metrics['core_transport_datasets']} datasets / {metrics['core_transport_variables']} variables.",
        f"- Overall gate: {'PASS' if all_passed else 'FAIL'}.",
        "",
        "This validates a portfolio exchange representation and prepares a reproducible CORE transport layer. It does not establish formal ADaM or regulatory-submission conformance.",
    ]
    (root / "outputs" / "dataset_json_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    if not all_passed:
        raise ValueError("Dataset-JSON exchange gate failed; inspect outputs/dataset_json_validation.csv")
    return metrics

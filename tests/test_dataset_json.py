import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.dataset_json import build_dataset_json, write_exchange_outputs


def _cfg() -> dict:
    return {
        "version": "0.19.0",
        "dataset_json": {
            "standard": "Dataset-JSON",
            "version": "1.1.0",
            "official_repository": "cdisc-org/DataExchange-DatasetJson",
            "official_commit": "test",
            "schema_relative_path": ".external/dataset-json/schema/dataset.schema.json",
            "creation_datetime": "2026-08-23T00:00:00Z",
            "originator": "Independent public-data portfolio",
            "source_system": {"name": "test", "version": "0.19.0"},
        },
        "core": {"conformance_claim": "NOT_ASSESSED"},
    }


def _dataset() -> dict:
    return {
        "name": "ADSL_STYLE",
        "alias": "ADSL",
        "file": "outputs/adsl_style.csv",
        "label": "Subject-Level Analysis Dataset Style",
        "class": "SUBJECT LEVEL ANALYSIS DATASET STYLE",
        "keys": ["STUDYID", "USUBJID"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "data_type": "text", "key": True},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "data_type": "text", "key": True},
            {"name": "AGE", "label": "Age", "data_type": "numeric", "key": False},
            {"name": "TRTSDT", "label": "Date of First Exposure", "data_type": "date", "key": False},
            {"name": "AVAL", "label": "Analysis Value", "data_type": "numeric", "key": False},
        ],
    }


def test_dataset_json_preserves_nulls_keys_and_adam_date_metadata() -> None:
    frame = pd.DataFrame({
        "STUDYID": ["S1", "S1"],
        "USUBJID": ["01", "02"],
        "AGE": [70, None],
        "TRTSDT": ["2026-01-01", None],
        "AVAL": [1.25, 2.0],
    })
    payload = build_dataset_json(_dataset(), frame, _cfg())
    assert payload["datasetJSONVersion"] == "1.1.0"
    assert payload["rows"][1][2] is None
    assert payload["rows"][1][3] is None
    columns = {c["name"]: c for c in payload["columns"]}
    assert columns["STUDYID"]["keySequence"] == 1
    assert columns["USUBJID"]["keySequence"] == 2
    assert columns["AGE"]["dataType"] == "integer"
    assert columns["AVAL"]["dataType"] == "double"
    assert columns["TRTSDT"]["dataType"] == "date"
    assert columns["TRTSDT"]["targetDataType"] == "integer"
    assert columns["TRTSDT"]["displayFormat"] == "E8601DA."


def test_missing_v018_metadata_is_rejected() -> None:
    frame = pd.DataFrame({"STUDYID": ["S1"], "USUBJID": ["01"], "NEWVAR": [1]})
    with pytest.raises(ValueError, match="missing from v0.18 metadata catalog"):
        build_dataset_json(_dataset(), frame, _cfg())


def test_end_to_end_exchange_uses_official_schema_path(tmp_path: Path) -> None:
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec").mkdir()
    schema_dir = tmp_path / ".external" / "dataset-json" / "schema"
    schema_dir.mkdir(parents=True)
    schema = {
        "$schema": "https://json-schema.org/draft/2019-09/schema",
        "type": "object",
        "required": ["datasetJSONVersion", "rows", "columns"],
    }
    (schema_dir / "dataset.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    cfg = _cfg()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(json.dumps(cfg), encoding="utf-8")
    dataset = _dataset()
    frame = pd.DataFrame({
        "STUDYID": ["S1", "S1"], "USUBJID": ["01", "02"], "AGE": [70, None],
        "TRTSDT": ["2026-01-01", None], "AVAL": [1.25, 2.0],
    })
    frame.to_csv(tmp_path / dataset["file"], index=False)
    catalog = {"version": "0.18.0", "datasets": [dataset]}
    (tmp_path / "outputs" / "adam_variable_metadata.json").write_text(json.dumps(catalog), encoding="utf-8")

    metrics = write_exchange_outputs(tmp_path)
    assert metrics["all_passed"] is True
    assert metrics["datasets"] == 1
    assert metrics["variables"] == 5
    assert metrics["records"] == 2
    assert metrics["null_values_preserved"] == 2
    assert metrics["official_schema_errors"] == 0
    assert metrics["core_transport_type_vocab"] == ["Char", "Num"]
    assert metrics["core_transport_type_vocab_ok"] is True
    assert (tmp_path / "outputs" / "dataset_json" / "adsl.json").is_file()
    core_csv = tmp_path / "outputs" / "core_input" / "ADSL.csv"
    assert core_csv.is_file()
    variables = pd.read_csv(tmp_path / "outputs" / "core_input" / "_variables.csv")
    assert set(variables.columns) == {"dataset", "variable", "label", "type", "length"}
    types = dict(zip(variables["variable"], variables["type"]))
    assert types["STUDYID"] == "Char"
    assert types["AGE"] == "Num"
    assert types["AVAL"] == "Num"
    assert types["TRTSDT"] == "Num"
    transported = pd.read_csv(core_csv)
    assert pd.api.types.is_numeric_dtype(transported["TRTSDT"])
    assert transported.loc[0, "TRTSDT"] == (pd.Timestamp("2026-01-01") - pd.Timestamp("1960-01-01")).days
    assert pd.isna(transported.loc[1, "TRTSDT"])


def test_conformance_overclaim_is_blocked(tmp_path: Path) -> None:
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec").mkdir()
    cfg = _cfg()
    cfg["core"]["conformance_claim"] = "CONFORMANT"
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "outputs" / "adam_variable_metadata.json").write_text(json.dumps({"version": "0.18.0", "datasets": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="NOT_ASSESSED"):
        write_exchange_outputs(tmp_path)

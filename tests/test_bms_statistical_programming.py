from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cdisc_portfolio.bms_statistical_programming import (
    ODM_NS,
    P21_STATUS,
    SAS_RUNTIME_STATUS,
    _load_json,
    _review_sas,
    _validate_config,
    _write_define_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v026_config_has_explicit_nonproduction_boundary() -> None:
    cfg = _load_json(ROOT / "spec" / "bms_statistical_programming_v0_26.json")
    _validate_config(cfg)
    assert cfg["sas_runtime_status"] == SAS_RUNTIME_STATUS
    assert cfg["pinnacle21_status"] == P21_STATUS
    assert "no sponsor/CRO employment claim" in cfg["evidence_boundary"]
    assert "not submission-ready" in cfg["evidence_boundary"]

    broken = json.loads(json.dumps(cfg))
    broken["evidence_boundary"] = "portfolio"
    with pytest.raises(ValueError):
        _validate_config(broken)


def test_v026_sas_sources_cover_datasets_and_tfls_without_runtime_overclaim() -> None:
    cfg = _load_json(ROOT / "spec" / "bms_statistical_programming_v0_26.json")
    checks: list[dict[str, object]] = []
    rows = _review_sas(ROOT, cfg, checks)

    assert len(rows) == 4
    assert all(row["passed"] for row in rows)
    roles = {row["role"] for row in rows}
    assert "DERIVED_ANALYSIS_DATASET_STATIC_TRANSLATION" in roles
    assert "SAFETY_TFL_STATIC_TRANSLATION" in roles
    assert "MMRM_TFL_STATIC_TRANSLATION" in roles
    assert all(row["runtime_status"] == SAS_RUNTIME_STATUS for row in rows)
    assert all(row["forbidden_hits"] == 0 for row in rows)


def test_define_xml_candidate_is_well_formed_and_portfolio_scoped(tmp_path: Path) -> None:
    datasets = [
        {"dataset": "ADSL", "label": "ADSL-style", "repeating": "No"},
        {"dataset": "ADAE", "label": "ADAE-style", "repeating": "Yes"},
        {"dataset": "ADQS", "label": "ADQS-style", "repeating": "Yes"},
        {"dataset": "ADTTE", "label": "ADTTE-style", "repeating": "No"},
    ]
    variables = [{"dataset":dataset["dataset"],"variable":"USUBJID","ordinal":1,"pandas_dtype":"object","required_by_contract":True,"key_variable":True} for dataset in datasets]
    path = tmp_path / "define.xml"
    counts = _write_define_candidate(path, datasets, variables)
    tree = ET.parse(path)
    root = tree.getroot()
    item_groups = root.findall(f".//{{{ODM_NS}}}ItemGroupDef")
    assert counts == {"datasets": 4, "variables": 4}
    assert len(item_groups) == 4
    assert "not a regulatory submission artifact" in path.read_text(encoding="utf-8")

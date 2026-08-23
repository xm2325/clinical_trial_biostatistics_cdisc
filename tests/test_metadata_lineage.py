import copy
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

from cdisc_portfolio.metadata_lineage import DATASETS, build_metadata_catalog, validate_metadata_lineage, write_metadata_outputs


def _config(conformance: str = "NOT_ASSESSED") -> dict:
    return {
        "version": "0.18.0",
        "define_xml_reference": {
            "standard": "Define-XML",
            "package_version": "2.1.11",
            "reference_date": "2026-04-06",
            "conformance": conformance,
            "note": "test",
        },
    }


def _write_outputs(root: Path) -> None:
    (root / "outputs").mkdir(parents=True)
    for ds in DATASETS.values():
        pd.DataFrame(columns=ds["columns"]).to_csv(root / ds["file"], index=False)


def _write_config(root: Path, conformance: str = "NOT_ASSESSED") -> None:
    (root / "spec").mkdir(parents=True)
    (root / "spec" / "adam_metadata_config.json").write_text(json.dumps(_config(conformance)), encoding="utf-8")


def test_catalog_has_exact_four_dataset_85_variable_scope() -> None:
    catalog = build_metadata_catalog(_config())
    assert len(catalog["datasets"]) == 4
    assert sum(len(ds["variables"]) for ds in catalog["datasets"]) == 85
    assert catalog["define_xml_reference"]["conformance"] == "NOT_ASSESSED"


def test_live_shape_validation_and_xml_roundtrip(tmp_path: Path) -> None:
    _write_outputs(tmp_path)
    _write_config(tmp_path)
    metrics = write_metadata_outputs(tmp_path)
    assert metrics["all_passed"] is True
    assert metrics["variables_with_exact_coverage"] == 85
    assert metrics["analysis_dataset_references"] == metrics["analysis_dataset_references_resolved"]
    xml_root = ET.parse(tmp_path / "outputs" / "define_xml_like_metadata.xml").getroot()
    assert xml_root.attrib["conformance"] == "NOT_ASSESSED"
    assert len(xml_root.findall("DatasetDef")) == 4
    assert len(xml_root.findall("./DatasetDef/ItemDef")) == 85


def test_missing_generated_column_is_rejected(tmp_path: Path) -> None:
    _write_outputs(tmp_path)
    _write_config(tmp_path)
    p = tmp_path / DATASETS["ADSL_STYLE"]["file"]
    cols = DATASETS["ADSL_STYLE"]["columns"][:-1]
    pd.DataFrame(columns=cols).to_csv(p, index=False)
    catalog = build_metadata_catalog(_config())
    with pytest.raises(ValueError, match="metadata coverage mismatch"):
        validate_metadata_lineage(tmp_path, catalog)


def test_stale_extra_metadata_is_rejected(tmp_path: Path) -> None:
    _write_outputs(tmp_path)
    catalog = build_metadata_catalog(_config())
    catalog = copy.deepcopy(catalog)
    catalog["datasets"][0]["variables"].append({
        "name": "STALEVAR", "label": "Stale", "data_type": "text", "role": "Record Qualifier",
        "origin_type": "Derived", "source_refs": ["SPEC.STALE"], "derivation": "stale", "key": False,
    })
    with pytest.raises(ValueError, match="metadata coverage mismatch"):
        validate_metadata_lineage(tmp_path, catalog)


def test_broken_analysis_lineage_reference_is_rejected(tmp_path: Path) -> None:
    _write_outputs(tmp_path)
    catalog = copy.deepcopy(build_metadata_catalog(_config()))
    adtte = next(ds for ds in catalog["datasets"] if ds["name"] == "ADTTE_RETENTION_STYLE")
    anltrt = next(v for v in adtte["variables"] if v["name"] == "ANLTRT")
    anltrt["source_refs"] = ["ADSL.NOT_A_VARIABLE"]
    with pytest.raises(ValueError, match="unresolved source refs"):
        validate_metadata_lineage(tmp_path, catalog)


def test_derived_variable_without_derivation_is_rejected(tmp_path: Path) -> None:
    _write_outputs(tmp_path)
    catalog = copy.deepcopy(build_metadata_catalog(_config()))
    adtte = next(ds for ds in catalog["datasets"] if ds["name"] == "ADTTE_RETENTION_STYLE")
    anltrt = next(v for v in adtte["variables"] if v["name"] == "ANLTRT")
    anltrt["derivation"] = ""
    with pytest.raises(ValueError, match="requires derivation text"):
        validate_metadata_lineage(tmp_path, catalog)


def test_formal_conformance_claim_is_blocked() -> None:
    with pytest.raises(ValueError, match="conformance=NOT_ASSESSED"):
        build_metadata_catalog(_config("CONFORMANT"))

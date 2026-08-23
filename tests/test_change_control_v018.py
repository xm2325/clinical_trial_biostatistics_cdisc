from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cdisc_portfolio.change_control import assess_change_requests
from cdisc_portfolio.change_control_v018 import (
    _require_v018_versions,
    load_versioned_change_control,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v018_merged_change_control_advances_version_and_adds_cr012() -> None:
    graph, requests, _, version = load_versioned_change_control(ROOT)
    assert version == "0.18.0"
    assert graph["version"] == "0.18.0"
    assert requests["version"] == "0.18.0"
    ids = [c["change_id"] for c in requests["changes"]]
    assert ids[-1] == "CR-012"
    assert len(ids) == 12


def test_cr012_exact_metadata_chain_has_no_tlf_impact() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(a for a in assess_change_requests(graph, requests) if a["change_id"] == "CR-012")
    assert assessment["passed"] is True
    assert assessment["required"]["tlfs"] == []
    assert assessment["propagated_components"] == [
        "adam_metadata_definition",
        "adam_metadata_lineage_validation",
        "define_like_metadata_export",
    ]
    assert set(assessment["required"]["analysis_datasets"]) == {
        "outputs/adsl_style.csv",
        "outputs/adae_style.csv",
        "outputs/adqs_actot_style.csv",
        "outputs/adtte_retention_style.csv",
    }
    assert set(assessment["required"]["qc"]) == {
        "outputs/adam_variable_metadata.json",
        "outputs/metadata_lineage_validation.csv",
        "outputs/metadata_lineage_metrics.json",
        "outputs/define_xml_like_metadata.xml",
        "outputs/metadata_lineage_summary.md",
    }


def test_cr012_does_not_propagate_into_analysis_families() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(a for a in assess_change_requests(graph, requests) if a["change_id"] == "CR-012")
    components = set(assessment["propagated_components"])
    assert not any(name.startswith("tte_retention_") for name in components)
    assert "multiplicity_decision" not in components
    assert "primary_mmrm" not in components


def test_cr012_missing_define_export_declaration_fails() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    broken = copy.deepcopy(requests)
    cr012 = next(c for c in broken["changes"] if c["change_id"] == "CR-012")
    cr012["declared_impacts"]["qc"].remove("outputs/define_xml_like_metadata.xml")
    assessment = next(a for a in assess_change_requests(graph, broken) if a["change_id"] == "CR-012")
    assert assessment["passed"] is False
    assert "outputs/define_xml_like_metadata.xml" in assessment["missing"]["qc"]


def test_v018_rejects_wrong_base_version() -> None:
    graph_ext = json.loads((ROOT / "spec" / "change_impact_graph_v0_18_extension.json").read_text())
    req_ext = json.loads((ROOT / "spec" / "change_requests_v0_18_extension.json").read_text())
    graph_ext["base_version"] = "0.16.0"
    with pytest.raises(ValueError, match="exact merged v0.17 base version"):
        _require_v018_versions("0.17.0", graph_ext, req_ext)

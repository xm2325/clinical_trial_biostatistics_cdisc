from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cdisc_portfolio.change_control import assess_change_requests
from cdisc_portfolio.change_control_v019 import (
    _require_v019_versions,
    load_versioned_change_control,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v019_merged_change_control_advances_version_and_adds_cr013() -> None:
    graph, requests, _, version = load_versioned_change_control(ROOT)
    assert version == "0.19.0"
    assert graph["version"] == "0.19.0"
    assert requests["version"] == "0.19.0"
    ids = [change["change_id"] for change in requests["changes"]]
    assert ids[-1] == "CR-013"
    assert len(ids) == 13


def test_cr013_exact_standards_chain_has_no_tlf_impact() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(
        item
        for item in assess_change_requests(graph, requests)
        if item["change_id"] == "CR-013"
    )
    assert assessment["passed"] is True
    assert assessment["required"]["tlfs"] == []
    assert assessment["propagated_components"] == [
        "core_rule_availability_audit",
        "core_validation_evidence_state",
        "dataset_json_exchange_validation",
        "standards_validation_configuration",
    ]
    assert set(assessment["required"]["analysis_datasets"]) == {
        "outputs/adsl_style.csv",
        "outputs/adae_style.csv",
        "outputs/adqs_actot_style.csv",
        "outputs/adtte_retention_style.csv",
    }
    assert "outputs/dataset_json_metrics.json" in assessment["required"]["qc"]
    assert "outputs/core_cache_manifest.json" in assessment["required"]["qc"]
    assert "outputs/core_validation_metrics.json" in assessment["required"]["qc"]


def test_cr013_does_not_propagate_into_statistical_analysis_families() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(
        item
        for item in assess_change_requests(graph, requests)
        if item["change_id"] == "CR-013"
    )
    components = set(assessment["propagated_components"])
    assert "primary_mmrm" not in components
    assert "mmrm_model_fit" not in components
    assert "primary_multiplicity_assumption" not in components
    assert "reference_based_mi_assumption" not in components
    assert "tte_retention_definition" not in components


def test_cr013_missing_core_availability_declaration_fails() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    broken = copy.deepcopy(requests)
    cr013 = next(change for change in broken["changes"] if change["change_id"] == "CR-013")
    cr013["declared_impacts"]["qc"].remove("outputs/core_cache_manifest.json")
    assessment = next(
        item
        for item in assess_change_requests(graph, broken)
        if item["change_id"] == "CR-013"
    )
    assert assessment["passed"] is False
    assert "outputs/core_cache_manifest.json" in assessment["missing"]["qc"]


def test_cr013_missing_dataset_json_schema_evidence_declaration_fails() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    broken = copy.deepcopy(requests)
    cr013 = next(change for change in broken["changes"] if change["change_id"] == "CR-013")
    cr013["declared_impacts"]["qc"].remove("outputs/dataset_json_validation.csv")
    assessment = next(
        item
        for item in assess_change_requests(graph, broken)
        if item["change_id"] == "CR-013"
    )
    assert assessment["passed"] is False
    assert "outputs/dataset_json_validation.csv" in assessment["missing"]["qc"]


def test_v019_rejects_wrong_base_version() -> None:
    graph_ext = json.loads(
        (ROOT / "spec" / "change_impact_graph_v0_19_extension.json").read_text()
    )
    req_ext = json.loads(
        (ROOT / "spec" / "change_requests_v0_19_extension.json").read_text()
    )
    graph_ext["base_version"] = "0.17.0"
    with pytest.raises(ValueError, match="exact merged v0.18 base version"):
        _require_v019_versions("0.18.0", graph_ext, req_ext)

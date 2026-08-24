from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cdisc_portfolio.change_control import assess_change_requests
from cdisc_portfolio.change_control_v020 import (
    _require_v020_versions,
    load_versioned_change_control,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v020_merged_change_control_advances_version_and_adds_cr014() -> None:
    graph, requests, _, version = load_versioned_change_control(ROOT)
    assert version == "0.20.0"
    assert graph["version"] == "0.20.0"
    assert requests["version"] == "0.20.0"
    ids = [change["change_id"] for change in requests["changes"]]
    assert ids[-1] == "CR-014"
    assert len(ids) == 14


def test_cr014_controls_readiness_chain_without_tlf_impact() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(
        item
        for item in assess_change_requests(graph, requests)
        if item["change_id"] == "CR-014"
    )
    assert assessment["passed"] is True
    assert assessment["required"]["tlfs"] == []
    assert assessment["required"]["analysis_datasets"] == []
    assert assessment["propagated_components"] == [
        "analysis_evidence_closure",
        "analysis_readiness_configuration",
        "blinded_analysis_readiness_review",
        "final_analysis_readiness_review",
    ]
    assert "outputs/blinded_analysis_readiness_review.csv" in assessment["required"]["qc"]
    assert "outputs/analysis_readiness_metrics.json" in assessment["required"]["qc"]
    assert "spec/analysis_readiness_v0_20.json" in assessment["required"]["specs"]


def test_cr014_does_not_propagate_into_statistical_analysis_families() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    assessment = next(
        item
        for item in assess_change_requests(graph, requests)
        if item["change_id"] == "CR-014"
    )
    components = set(assessment["propagated_components"])
    assert "primary_mmrm" not in components
    assert "primary_multiplicity_assumption" not in components
    assert "reference_based_mi_assumption" not in components
    assert "tte_retention_definition" not in components
    assert "standards_validation_configuration" not in components


def test_cr014_missing_readiness_evidence_declaration_fails() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    broken = copy.deepcopy(requests)
    cr014 = next(change for change in broken["changes"] if change["change_id"] == "CR-014")
    cr014["declared_impacts"]["qc"].remove("outputs/analysis_readiness_metrics.json")
    assessment = next(
        item
        for item in assess_change_requests(graph, broken)
        if item["change_id"] == "CR-014"
    )
    assert assessment["passed"] is False
    assert "outputs/analysis_readiness_metrics.json" in assessment["missing"]["qc"]


def test_v020_rejects_wrong_base_version() -> None:
    graph_ext = json.loads(
        (ROOT / "spec" / "change_impact_graph_v0_20_extension.json").read_text()
    )
    req_ext = json.loads(
        (ROOT / "spec" / "change_requests_v0_20_extension.json").read_text()
    )
    graph_ext["base_version"] = "0.18.0"
    with pytest.raises(ValueError, match="exact merged v0.19 base version"):
        _require_v020_versions("0.19.0", graph_ext, req_ext)

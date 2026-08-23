import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.change_control import assess_change, assess_change_requests, load_json
from cdisc_portfolio.change_control_v015 import load_versioned_change_control as load_v015
from cdisc_portfolio.change_control_v016 import (
    GRAPH_EXTENSION,
    REQUEST_EXTENSION,
    _require_v016_versions,
    load_versioned_change_control,
)


def _change_by_id(requests, change_id):
    return next(change for change in requests["changes"] if change["change_id"] == change_id)


def test_repository_v016_layers_over_validated_v015():
    _, _, _, prior_version = load_v015(ROOT)
    assert prior_version == "0.15.0"

    graph, requests, paths, version = load_versioned_change_control(ROOT)
    assert version == "0.16.0"
    assert graph["version"] == "0.16.0"
    assert requests["version"] == "0.16.0"
    assert paths["graph_extension_v016"].name == GRAPH_EXTENSION
    assert paths["request_extension_v016"].name == REQUEST_EXTENSION
    assert "mmrm_cross_package_validation_rule" in graph["components"]
    assert "mmrm_cross_package_reconstruction" in graph["components"]
    assert "mmrm_cross_package_validation_gate" in graph["components"]
    assert len(requests["changes"]) == 10


def test_repository_v016_all_merged_change_requests_cover_required_impacts():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    results = assess_change_requests(graph, requests)
    assert len(results) == 10
    assert all(result["passed"] for result in results)
    assert all(not any(result["missing"].values()) for result in results)


def test_v016_visit_covariance_and_estimand_changes_propagate_to_validation_qc():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    for change_id in ("CR-003", "CR-004", "CR-005"):
        result = assess_change(graph, _change_by_id(requests, change_id))
        assert result["passed"]
        assert "outputs/mmrm_cross_package_validation.csv" in result["required"]["qc"]
        assert "outputs/mmrm_cross_package_qc.csv" in result["required"]["qc"]
        assert "outputs/mmrm_cross_package_validation_metrics.json" in result["required"]["qc"]
        assert "outputs/mmrm_cross_package_analysis_dataset.csv" in result["required"]["analysis_datasets"]
        assert "outputs/mmrm_analysis_dataset.csv" in result["required"]["analysis_datasets"]
        assert "outputs/mmrm_treatment_contrasts.csv" in result["required"]["analysis_datasets"]

    visit = assess_change(graph, _change_by_id(requests, "CR-003"))
    covariance = assess_change(graph, _change_by_id(requests, "CR-004"))
    estimand = assess_change(graph, _change_by_id(requests, "CR-005"))
    assert "spec/mmrm_cross_package_validation.json" in visit["required"]["specs"]
    assert "spec/mmrm_cross_package_validation.json" in covariance["required"]["specs"]
    assert "spec/mmrm_cross_package_validation.json" not in estimand["required"]["specs"]


def test_v016_cr010_requires_validation_spec_docs_inputs_and_qc_but_no_tlf():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    result = assess_change(graph, _change_by_id(requests, "CR-010"))
    assert result["passed"]
    assert result["required"]["tlfs"] == []
    assert result["required"]["analysis_datasets"] == [
        "outputs/adqs_actot_style.csv",
        "outputs/mmrm_analysis_dataset.csv",
        "outputs/mmrm_cross_package_analysis_dataset.csv",
        "outputs/mmrm_treatment_contrasts.csv",
    ]
    assert "outputs/mmrm_cross_package_contrasts.csv" in result["required"]["qc"]
    assert "outputs/mmrm_cross_package_validation.csv" in result["required"]["qc"]
    assert "outputs/mmrm_cross_package_qc.csv" in result["required"]["qc"]
    assert "docs/mmrm_cross_package_validation.md" in result["required"]["documents"]
    assert "docs/qc_plan.md" in result["required"]["documents"]
    assert result["required"]["specs"] == ["spec/mmrm_cross_package_validation.json"]


def test_v016_negative_control_detects_omitted_cross_package_qc():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-010"))
    change["declared_impacts"]["qc"].remove("outputs/mmrm_cross_package_qc.csv")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["qc"] == ["outputs/mmrm_cross_package_qc.csv"]


def test_v016_negative_control_detects_omitted_independent_analysis_dataset():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-010"))
    change["declared_impacts"]["analysis_datasets"].remove(
        "outputs/mmrm_cross_package_analysis_dataset.csv"
    )
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["analysis_datasets"] == [
        "outputs/mmrm_cross_package_analysis_dataset.csv"
    ]


def test_v016_extensions_reject_wrong_prior_base_version():
    graph_extension = load_json(ROOT / "spec" / GRAPH_EXTENSION)
    request_extension = load_json(ROOT / "spec" / REQUEST_EXTENSION)

    broken_graph = copy.deepcopy(graph_extension)
    broken_graph["base_version"] = "0.14.0"
    with pytest.raises(ValueError, match="exact merged v0.15 base version"):
        _require_v016_versions("0.15.0", broken_graph, request_extension)

    broken_request = copy.deepcopy(request_extension)
    broken_request["base_version"] = "0.14.0"
    with pytest.raises(ValueError, match="exact merged v0.15 base version"):
        _require_v016_versions("0.15.0", graph_extension, broken_request)

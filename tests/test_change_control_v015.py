import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.change_control import assess_change, assess_change_requests, load_json
from cdisc_portfolio.change_control_v015 import (
    GRAPH_BASE,
    GRAPH_EXTENSION,
    REQUEST_BASE,
    REQUEST_EXTENSION,
    load_versioned_change_control,
    merge_graph_extension,
    merge_request_extension,
)


def _change_by_id(requests, change_id):
    return next(change for change in requests["changes"] if change["change_id"] == change_id)


def test_repository_v015_extension_preserves_v014_base_and_merges_to_v015():
    base_graph = load_json(ROOT / "spec" / GRAPH_BASE)
    base_requests = load_json(ROOT / "spec" / REQUEST_BASE)
    assert base_graph["version"] == "0.14.0"
    assert base_requests["version"] == "0.14.0"

    graph, requests, paths, version = load_versioned_change_control(ROOT)
    assert version == "0.15.0"
    assert graph["version"] == "0.15.0"
    assert requests["version"] == "0.15.0"
    assert paths["graph_extension"].name == GRAPH_EXTENSION
    assert paths["request_extension"].name == REQUEST_EXTENSION
    assert "primary_multiplicity_assumption" in graph["components"]
    assert len(requests["changes"]) == 9


def test_repository_v015_all_merged_change_requests_cover_required_impacts():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    results = assess_change_requests(graph, requests)
    assert len(results) == 9
    assert all(result["passed"] for result in results)
    assert all(not any(result["missing"].values()) for result in results)


def test_v015_primary_visit_covariance_and_estimand_changes_propagate_to_t23():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    for change_id in ("CR-003", "CR-004", "CR-005"):
        result = assess_change(graph, _change_by_id(requests, change_id))
        assert result["passed"]
        assert "T23" in result["required"]["tlfs"]
        assert "outputs/multiplicity_qc.csv" in result["required"]["qc"]
        assert "outputs/mmrm_treatment_contrasts.csv" in result["required"]["analysis_datasets"]


def test_v015_multiplicity_rule_change_requires_t23_specs_docs_and_qc():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-009"))
    result = assess_change(graph, change)
    assert result["passed"]
    assert result["required"]["tlfs"] == ["T23"]
    assert "outputs/multiplicity_qc.csv" in result["required"]["qc"]
    assert "outputs/mmrm_qc.csv" in result["required"]["qc"]
    assert "spec/multiplicity.json" in result["required"]["specs"]
    assert "spec/protocol_design.json" in result["required"]["specs"]
    assert "docs/multiplicity_control.md" in result["required"]["documents"]


def test_v015_negative_control_detects_omitted_t23_from_cr009():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-009"))
    change["declared_impacts"]["tlfs"].remove("T23")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T23"]


def test_v015_extension_rejects_wrong_base_version():
    base_graph = load_json(ROOT / "spec" / GRAPH_BASE)
    graph_extension = load_json(ROOT / "spec" / GRAPH_EXTENSION)
    broken = copy.deepcopy(graph_extension)
    broken["base_version"] = "0.13.0"
    with pytest.raises(ValueError, match="base_version"):
        merge_graph_extension(base_graph, broken)

    base_requests = load_json(ROOT / "spec" / REQUEST_BASE)
    request_extension = load_json(ROOT / "spec" / REQUEST_EXTENSION)
    broken_requests = copy.deepcopy(request_extension)
    broken_requests["base_version"] = "0.13.0"
    with pytest.raises(ValueError, match="base_version"):
        merge_request_extension(base_requests, broken_requests)

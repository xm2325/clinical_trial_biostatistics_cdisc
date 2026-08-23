import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.change_control import assess_change, assess_change_requests, load_json
from cdisc_portfolio.change_control_v016 import load_versioned_change_control as load_v016
from cdisc_portfolio.change_control_v017 import (
    GRAPH_EXTENSION,
    REQUEST_EXTENSION,
    _require_v017_versions,
    load_versioned_change_control,
)


def _change_by_id(requests, change_id):
    return next(change for change in requests["changes"] if change["change_id"] == change_id)


def test_repository_v017_layers_over_validated_v016():
    _, _, _, prior_version = load_v016(ROOT)
    assert prior_version == "0.16.0"

    graph, requests, paths, version = load_versioned_change_control(ROOT)
    assert version == "0.17.0"
    assert graph["version"] == "0.17.0"
    assert requests["version"] == "0.17.0"
    assert paths["graph_extension_v017"].name == GRAPH_EXTENSION
    assert paths["request_extension_v017"].name == REQUEST_EXTENSION
    assert "tte_retention_definition" in graph["components"]
    assert "tte_retention_derivation" in graph["components"]
    assert "tte_retention_survival_analysis" in graph["components"]
    assert "tte_retention_tlfs" in graph["components"]
    assert len(requests["changes"]) == 11


def test_repository_v017_all_merged_change_requests_cover_required_impacts():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    results = assess_change_requests(graph, requests)
    assert len(results) == 11
    assert all(result["passed"] for result in results)
    assert all(not any(result["missing"].values()) for result in results)


def test_v017_cr011_requires_adtte_survival_tlfs_spec_docs_and_qc():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    result = assess_change(graph, _change_by_id(requests, "CR-011"))
    assert result["passed"]
    assert result["required"]["analysis_datasets"] == [
        "outputs/adsl_style.csv",
        "outputs/adtte_retention_style.csv",
    ]
    assert result["required"]["tlfs"] == ["T24", "T25"]
    assert "outputs/adtte_retention_qc.csv" in result["required"]["qc"]
    assert "outputs/adtte_retention_metrics.json" in result["required"]["qc"]
    assert "outputs/tte_retention_survival_qc.csv" in result["required"]["qc"]
    assert "outputs/tte_retention_survival_metrics.json" in result["required"]["qc"]
    assert "docs/tte_retention_analysis.md" in result["required"]["documents"]
    assert "docs/sap_v0_17_tte_addendum.md" in result["required"]["documents"]
    assert "docs/tlf_shells_v0_17_addendum.md" in result["required"]["documents"]
    assert "docs/qc_plan.md" in result["required"]["documents"]
    assert result["required"]["specs"] == ["spec/tte_retention.json"]


def test_v017_retention_chain_does_not_enter_actot_multiplicity_family():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    result = assess_change(graph, _change_by_id(requests, "CR-011"))
    assert "T23" not in result["required"]["tlfs"]
    assert "outputs/multiplicity_qc.csv" not in result["required"]["qc"]
    assert "spec/multiplicity.json" not in result["required"]["specs"]


def test_v017_negative_control_detects_omitted_t25():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-011"))
    change["declared_impacts"]["tlfs"].remove("T25")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T25"]


def test_v017_negative_control_detects_omitted_adtte_qc():
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    change = copy.deepcopy(_change_by_id(requests, "CR-011"))
    change["declared_impacts"]["qc"].remove("outputs/adtte_retention_qc.csv")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["qc"] == ["outputs/adtte_retention_qc.csv"]


def test_v017_extensions_reject_wrong_prior_base_version():
    graph_extension = load_json(ROOT / "spec" / GRAPH_EXTENSION)
    request_extension = load_json(ROOT / "spec" / REQUEST_EXTENSION)

    broken_graph = copy.deepcopy(graph_extension)
    broken_graph["base_version"] = "0.15.0"
    with pytest.raises(ValueError, match="exact merged v0.16 base version"):
        _require_v017_versions("0.16.0", broken_graph, request_extension)

    broken_request = copy.deepcopy(request_extension)
    broken_request["base_version"] = "0.15.0"
    with pytest.raises(ValueError, match="exact merged v0.16 base version"):
        _require_v017_versions("0.16.0", graph_extension, broken_request)

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.change_control import (
    _matched_spec_version,
    assess_change,
    assess_change_requests,
    required_impacts,
    transitive_components,
    validate_impact_graph,
)


def _graph():
    return {
        "components": {
            "protocol_rule": {
                "downstream": ["dataset_rule"],
                "impacts": {"documents": ["docs/sap.md"]},
            },
            "dataset_rule": {
                "downstream": ["tlf_rule"],
                "impacts": {
                    "analysis_datasets": ["outputs/adsl_style.csv"],
                    "qc": ["outputs/qc_report.csv"],
                },
            },
            "tlf_rule": {
                "downstream": [],
                "impacts": {"tlfs": ["T01"]},
            },
        }
    }


def _complete_change():
    return {
        "change_id": "CR-X",
        "title": "Example",
        "rationale": "Exercise downstream impact propagation.",
        "changed_components": ["protocol_rule"],
        "declared_impacts": {
            "analysis_datasets": ["outputs/adsl_style.csv"],
            "tlfs": ["T01"],
            "qc": ["outputs/qc_report.csv"],
            "documents": ["docs/sap.md"],
            "specs": [],
        },
    }


def _repository_specs():
    graph = json.loads((ROOT / "spec" / "change_impact_graph.json").read_text(encoding="utf-8"))
    requests = json.loads((ROOT / "spec" / "change_requests.json").read_text(encoding="utf-8"))
    return graph, requests


def _change_by_id(requests, change_id):
    return next(change for change in requests["changes"] if change["change_id"] == change_id)


def test_change_impact_propagates_transitively():
    reached = transitive_components(_graph(), ["protocol_rule"])
    assert reached == ["dataset_rule", "protocol_rule", "tlf_rule"]
    reached, impacts = required_impacts(_graph(), ["protocol_rule"])
    assert len(reached) == 3
    assert impacts["analysis_datasets"] == ["outputs/adsl_style.csv"]
    assert impacts["tlfs"] == ["T01"]
    assert impacts["qc"] == ["outputs/qc_report.csv"]
    assert impacts["documents"] == ["docs/sap.md"]


def test_change_assessment_fails_when_required_tlf_is_omitted():
    change = _complete_change()
    change["declared_impacts"]["tlfs"] = []
    result = assess_change(_graph(), change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T01"]


def test_change_assessment_allows_conservative_extra_review_item():
    change = _complete_change()
    change["declared_impacts"]["documents"].append("docs/qc_plan.md")
    result = assess_change(_graph(), change)
    assert result["passed"]
    assert result["extra"]["documents"] == ["docs/qc_plan.md"]


def test_change_impact_graph_rejects_unknown_component_and_cycle():
    with pytest.raises(ValueError, match="unknown changed components"):
        transitive_components(_graph(), ["not_a_component"])
    cyclic = _graph()
    cyclic["components"]["tlf_rule"]["downstream"] = ["protocol_rule"]
    with pytest.raises(ValueError, match="contains a cycle"):
        validate_impact_graph(cyclic)


def test_repository_change_requests_cover_every_graph_required_impact():
    graph, requests = _repository_specs()
    results = assess_change_requests(graph, requests)
    assert len(results) == 8
    assert all(result["passed"] for result in results)
    assert all(not any(result["missing"].values()) for result in results)


def test_repository_change_control_versions_match_v014():
    graph, requests = _repository_specs()
    assert _matched_spec_version(graph, requests) == "0.14.0"
    broken = copy.deepcopy(requests)
    broken["version"] = "0.13.0"
    with pytest.raises(ValueError, match="version mismatch"):
        _matched_spec_version(graph, broken)


def test_repository_negative_control_detects_omitted_required_impact():
    graph, requests = _repository_specs()
    corrupted = copy.deepcopy(_change_by_id(requests, "CR-002"))
    corrupted["declared_impacts"]["tlfs"].remove("T04")
    result = assess_change(graph, corrupted)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T04"]


def test_estimand_strategy_change_requires_missingness_mnar_mi_and_reference_tlfs():
    graph, requests = _repository_specs()
    change = copy.deepcopy(_change_by_id(requests, "CR-005"))
    for tlf in ("T16", "T18", "T20", "T22"):
        change["declared_impacts"]["tlfs"].remove(tlf)
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T16", "T18", "T20", "T22"]


def test_mnar_assumption_change_requires_both_deterministic_sensitivity_tlfs():
    graph, requests = _repository_specs()
    change = copy.deepcopy(_change_by_id(requests, "CR-006"))
    change["declared_impacts"]["tlfs"].remove("T19")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T19"]


def test_primary_mmrm_covariance_change_propagates_to_deterministic_outputs():
    graph, requests = _repository_specs()
    result = assess_change(graph, _change_by_id(requests, "CR-004"))
    assert result["passed"]
    assert {"T18", "T19"}.issubset(result["required"]["tlfs"])
    assert "outputs/mnar_sensitivity_qc.csv" in result["required"]["qc"]


def test_primary_visit_change_propagates_to_t22_and_reference_qc():
    graph, requests = _repository_specs()
    result = assess_change(graph, _change_by_id(requests, "CR-003"))
    assert result["passed"]
    assert {"T20", "T21", "T22"}.issubset(result["required"]["tlfs"])
    assert "spec/reference_based_mi.json" in result["required"]["specs"]
    assert "outputs/rbmi_reference_mcse_qc.csv" in result["required"]["qc"]
    assert "outputs/estimand_review.csv" in result["required"]["qc"]


def test_mi_base_change_requires_reference_based_reanalysis():
    graph, requests = _repository_specs()
    result = assess_change(graph, _change_by_id(requests, "CR-007"))
    assert result["passed"]
    assert {"T20", "T21", "T22"}.issubset(result["required"]["tlfs"])
    assert "outputs/rbmi_reference_ice_audit.csv" in result["required"]["analysis_datasets"]
    assert "outputs/rbmi_reference_qc.csv" in result["required"]["qc"]


def test_reference_based_assumption_change_requires_t22_estimand_and_mcse_qc():
    graph, requests = _repository_specs()
    change = copy.deepcopy(_change_by_id(requests, "CR-008"))
    change["declared_impacts"]["tlfs"].remove("T22")
    change["declared_impacts"]["qc"].remove("outputs/estimand_review.csv")
    change["declared_impacts"]["qc"].remove("outputs/rbmi_reference_mcse_qc.csv")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T22"]
    assert result["missing"]["qc"] == [
        "outputs/estimand_review.csv",
        "outputs/rbmi_reference_mcse_qc.csv",
    ]

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
    graph = json.loads((ROOT / "spec" / "change_impact_graph.json").read_text(encoding="utf-8"))
    requests = json.loads((ROOT / "spec" / "change_requests.json").read_text(encoding="utf-8"))
    results = assess_change_requests(graph, requests)
    assert len(results) == 5
    assert all(result["passed"] for result in results)
    assert all(not any(result["missing"].values()) for result in results)


def test_repository_change_control_versions_match_v011():
    graph = json.loads((ROOT / "spec" / "change_impact_graph.json").read_text(encoding="utf-8"))
    requests = json.loads((ROOT / "spec" / "change_requests.json").read_text(encoding="utf-8"))
    assert _matched_spec_version(graph, requests) == "0.11.0"
    broken = copy.deepcopy(requests)
    broken["version"] = "0.10.0"
    with pytest.raises(ValueError, match="version mismatch"):
        _matched_spec_version(graph, broken)


def test_repository_negative_control_detects_omitted_required_impact():
    graph = json.loads((ROOT / "spec" / "change_impact_graph.json").read_text(encoding="utf-8"))
    requests = json.loads((ROOT / "spec" / "change_requests.json").read_text(encoding="utf-8"))
    corrupted = copy.deepcopy(requests["changes"][1])
    corrupted["declared_impacts"]["tlfs"].remove("T04")
    result = assess_change(graph, corrupted)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T04"]


def test_estimand_strategy_change_requires_missingness_tlfs():
    graph = json.loads((ROOT / "spec" / "change_impact_graph.json").read_text(encoding="utf-8"))
    requests = json.loads((ROOT / "spec" / "change_requests.json").read_text(encoding="utf-8"))
    change = copy.deepcopy(requests["changes"][4])
    change["declared_impacts"]["tlfs"].remove("T16")
    result = assess_change(graph, change)
    assert not result["passed"]
    assert result["missing"]["tlfs"] == ["T16"]

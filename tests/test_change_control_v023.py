from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from cdisc_portfolio.change_control import assess_change_requests
from cdisc_portfolio.change_control_v023 import load_versioned_change_control

ROOT = Path(__file__).resolve().parents[1]


def test_v023_change_control_adds_cr015_and_t20_to_t22_impacts() -> None:
    graph, requests, _, version = load_versioned_change_control(ROOT)
    assert version == "0.23.0"
    assessments = {row["change_id"]: row for row in assess_change_requests(graph, requests)}
    assert "CR-015" in assessments
    cr = assessments["CR-015"]
    assert cr["passed"] is True
    assert cr["missing"] == {
        "analysis_datasets": [],
        "tlfs": [],
        "qc": [],
        "documents": [],
        "specs": [],
    }
    assert cr["extra"] == {
        "analysis_datasets": [],
        "tlfs": [],
        "qc": [],
        "documents": [],
        "specs": [],
    }
    assert cr["required"]["tlfs"] == ["T20", "T21", "T22"]
    assert "planned_assignment_mi_inputs" in cr["propagated_components"]
    assert "primary_mmrm_assignment_guard" in cr["propagated_components"]
    assert "mi_assignment_post_execution_audit" in cr["propagated_components"]


def test_cr015_missing_t22_declaration_is_detected() -> None:
    graph, requests, _, _ = load_versioned_change_control(ROOT)
    altered = deepcopy(requests)
    cr = next(row for row in altered["changes"] if row["change_id"] == "CR-015")
    cr["declared_impacts"]["tlfs"].remove("T22")
    assessments = {row["change_id"]: row for row in assess_change_requests(graph, altered)}
    assert assessments["CR-015"]["passed"] is False
    assert assessments["CR-015"]["missing"]["tlfs"] == ["T22"]

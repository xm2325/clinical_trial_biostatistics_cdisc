from __future__ import annotations

import json
from pathlib import Path

from cdisc_portfolio.study_statistician_decision_suite import run_study_statistician_decision_suite


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    _write_json(tmp_path / "spec" / "study_statistician_decision_suite_v0_24.json", {
        "version": "0.24.0",
        "claim": "PORTFOLIO_STUDY_STATISTICIAN_DECISION_SUITE_READY",
        "components": [
            {"id": "prospective_design", "metrics": "outputs/design.json", "required_claim": "DESIGN"},
            {"id": "safety_assignment", "metrics": "outputs/safety.json", "required_claim": "SAFETY"},
            {"id": "change_decision", "metrics": "outputs/change.json", "required_claim": "CHANGE"}
        ],
        "inherited_closure": "outputs/closure.json",
        "scope": "test",
        "interpretation_boundary": ["test"]
    })
    for name, claim in [("design", "DESIGN"), ("safety", "SAFETY"), ("change", "CHANGE")]:
        _write_json(tmp_path / "outputs" / f"{name}.json", {
            "version": "0.24.0", "claim": claim, "all_passed": True
        })
    _write_json(tmp_path / "outputs" / "closure.json", {
        "closure_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE", "all_passed": True
    })
    return tmp_path


def test_decision_suite_requires_all_three_components_and_inherited_closure(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    checks, metrics = run_study_statistician_decision_suite(root)
    assert metrics["all_passed"] is True
    assert metrics["checks_passed"] == 4
    assert metrics["checks_total"] == 4
    assert checks["passed"].all()


def test_decision_suite_blocks_component_claim_drift(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    _write_json(root / "outputs" / "safety.json", {
        "version": "0.24.0", "claim": "WRONG", "all_passed": True
    })
    checks, metrics = run_study_statistician_decision_suite(root)
    assert metrics["all_passed"] is False
    safety = checks.loc[checks["component"].eq("safety_assignment")].iloc[0]
    assert bool(safety["passed"]) is False

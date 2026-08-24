from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.analysis_readiness import assess_analysis_readiness, write_analysis_readiness_outputs


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.20.0",
        "analysis_data_cutoff": "2020-12-31",
        "blinded_review": {
            "forbidden_fields": ["TRT01P", "TRT01A", "ANLTRT"],
            "required_subject_count": 3,
            "required_randomized_count": 2,
            "required_eos_date_count": 3,
            "required_actot_baseline_randomized_count": 2,
        },
        "final_analysis_review": {
            "expected_planned_actual_mismatch_count": 1,
            "expected_week24_missing_count": 1,
            "expected_adqscibc_value_difference_count": 1,
            "required_prior_gates": [
                "dataset_review",
                "metadata_lineage",
                "dataset_json",
                "core_standards_state",
                "change_control",
                "traceability",
            ],
        },
        "issue_dispositions": {
            "AR-001": {"title": "mismatch", "expected_count": 1, "status": "ACCEPTED_FOR_ANALYSIS", "blocking": False, "resolution": "planned assignment retained"},
            "AR-002": {"title": "missing", "expected_count": 1, "status": "ADDRESSED_BY_SENSITIVITY", "blocking": False, "resolution": "sensitivity reviewed"},
            "AR-003": {"title": "reference", "expected_count": 1, "status": "SOURCE_TRACE_ACCEPTED", "blocking": False, "resolution": "source trace retained"},
        },
        "readiness_claim": "PORTFOLIO_ANALYSIS_PACKAGE_READY_FOR_REVIEW",
        "evidence_boundary": "test",
    }
    _write_json(tmp_path / "spec" / "analysis_readiness_v0_20.json", cfg)

    pd.DataFrame(
        {
            "USUBJID": ["S1", "S2", "S3"],
            "RANDFL": ["Y", "Y", "N"],
            "EOSDT": ["2020-06-01", "2020-06-02", "2020-06-03"],
            "TRTSDT": ["2020-01-01", "2020-01-02", None],
            "TRTEDT": ["2020-05-01", "2020-05-02", None],
        }
    ).to_csv(tmp_path / "outputs" / "adsl_style.csv", index=False)
    pd.DataFrame(
        {
            "USUBJID": ["S1"],
            "ASTDT": ["2020-02-01"],
            "AENDT": ["2020-02-02"],
            "TRTSDT": ["2020-01-01"],
            "TRTEDT": ["2020-05-01"],
        }
    ).to_csv(tmp_path / "outputs" / "adae_style.csv", index=False)
    pd.DataFrame(
        {
            "USUBJID": ["S1", "S2", "S1"],
            "AVISIT": ["BASELINE", "BASELINE", "WEEK 24"],
            "ABLFL": ["Y", "Y", "N"],
            "EFFFL": ["Y", "Y", "Y"],
            "ADT": ["2020-01-01", "2020-01-02", "2020-06-01"],
        }
    ).to_csv(tmp_path / "outputs" / "adqs_actot_style.csv", index=False)
    pd.DataFrame(
        {
            "USUBJID": ["S1", "S2"],
            "TRT01P": ["A", "B"],
            "TRT01A": ["A", "C"],
            "ANLTRT": ["A", "B"],
            "STARTDT": ["2020-01-01", "2020-01-02"],
            "ADT": ["2020-06-01", "2020-06-02"],
        }
    ).to_csv(tmp_path / "outputs" / "adtte_retention_style.csv", index=False)
    pd.DataFrame({"AVAL_MATCH": [True, False]}).to_csv(
        tmp_path / "outputs" / "adqscibc_reference_detail.csv", index=False
    )

    _write_json(tmp_path / "outputs" / "analysis_dataset_review_metrics.json", {"all_required_review_passed": True})
    for name in [
        "metadata_lineage_metrics.json",
        "dataset_json_metrics.json",
        "core_validation_metrics.json",
        "change_impact_metrics.json",
        "traceability_metrics.json",
    ]:
        _write_json(tmp_path / "outputs" / name, {"all_passed": True})
    return tmp_path


def test_analysis_readiness_happy_path_and_blinded_artifact_boundary(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    metrics = write_analysis_readiness_outputs(root)
    assert metrics["all_passed"] is True
    assert metrics["blocking_open_issues"] == 0
    assert metrics["week24_actot_missing"] == 1
    blinded_path = root / "outputs" / "blinded_analysis_readiness_review.csv"
    blinded = pd.read_csv(blinded_path)
    assert not {"TRT01P", "TRT01A", "ANLTRT"} & set(blinded.columns)
    blinded_text = blinded_path.read_text().lower()
    assert all(token.lower() not in blinded_text for token in ["TRT01P", "TRT01A", "ANLTRT"])
    assert bool(blinded["passed"].all())


def test_date_value_after_data_cutoff_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    adsl = pd.read_csv(root / "outputs" / "adsl_style.csv")
    adsl.loc[0, "EOSDT"] = "2021-01-01"
    adsl.to_csv(root / "outputs" / "adsl_style.csv", index=False)
    blinded, _, metrics = assess_analysis_readiness(root)
    assert metrics["all_passed"] is False
    assert metrics["date_values_after_data_cutoff"] == 1
    assert any(
        row["check"] == "no analysed date values exceed configured data cutoff" and not row["passed"]
        for row in blinded
    )


def test_known_issue_count_drift_is_blocking(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    adtte = pd.read_csv(root / "outputs" / "adtte_retention_style.csv")
    adtte.loc[1, "TRT01A"] = "B"
    adtte.to_csv(root / "outputs" / "adtte_retention_style.csv", index=False)
    _, final, metrics = assess_analysis_readiness(root)
    assert metrics["all_passed"] is False
    issue = next(row for row in final if row.get("issue_id") == "AR-001")
    assert issue["actual_count"] == 0
    assert issue["passed"] is False


def test_blocking_or_blank_issue_disposition_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "analysis_readiness_v0_20.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["issue_dispositions"]["AR-002"]["blocking"] = True
    cfg["issue_dispositions"]["AR-002"]["resolution"] = ""
    cfg_path.write_text(json.dumps(cfg))
    _, _, metrics = assess_analysis_readiness(root)
    assert metrics["all_passed"] is False
    assert metrics["blocking_open_issues"] >= 1


def test_failed_prior_gate_blocks_final_readiness(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    _write_json(root / "outputs" / "traceability_metrics.json", {"all_passed": False})
    _, final, metrics = assess_analysis_readiness(root)
    assert metrics["all_passed"] is False
    assert any(
        row.get("check") == "prior gate: traceability" and not row["passed"]
        for row in final
    )


def test_expected_count_configuration_drift_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "analysis_readiness_v0_20.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["final_analysis_review"]["expected_week24_missing_count"] = 999
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="expected-count configuration drift for AR-002"):
        assess_analysis_readiness(root)


def test_missing_controlled_issue_disposition_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "analysis_readiness_v0_20.json"
    cfg = json.loads(cfg_path.read_text())
    del cfg["issue_dispositions"]["AR-003"]
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="exactly the controlled issue IDs"):
        assess_analysis_readiness(root)


def test_regulatory_readiness_overclaim_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    cfg_path = root / "spec" / "analysis_readiness_v0_20.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["readiness_claim"] = "SUBMISSION_READY"
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="portfolio-scoped"):
        assess_analysis_readiness(root)

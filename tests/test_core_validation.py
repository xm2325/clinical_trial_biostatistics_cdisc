import json
from pathlib import Path

import pytest

from cdisc_portfolio.core_validation import (
    NOT_AVAILABLE,
    triage_core_report,
    write_core_outputs,
    write_core_unavailable_outputs,
)


def _cfg() -> dict:
    return {
        "version": "0.19.0",
        "core": {
            "repository": "cdisc-org/cdisc-rules-engine",
            "commit": "test-commit",
            "cache_commit": "test-cache-commit",
            "open_rules_repository": "cdisc-org/cdisc-open-rules",
            "open_rules_commit": "test-open-rules-commit",
            "expected_ruleset_state": NOT_AVAILABLE,
            "standard": "adamig",
            "version": "1-3",
            "allowed_statuses": ["SUCCESS", "ISSUE REPORTED", "SKIPPED", "EXECUTION ERROR"],
            "blocking_statuses": ["EXECUTION ERROR"],
            "require_executed_rule": True,
            "conformance_claim": "NOT_ASSESSED",
        },
    }


def _report(statuses: list[str]) -> dict:
    return {
        "Conformance_Details": {"Standard": "adamig", "Version": "V1-3"},
        "Rules_Report": [
            {
                "core_id": f"CORE-{index:06d}",
                "cdisc_rule_id": f"ADAM-{index}",
                "fda_rule_id": "",
                "message": f"rule {index}",
                "status": status,
            }
            for index, status in enumerate(statuses, start=1)
        ],
        "Issue_Summary": [
            {"dataset": "ADSL", "core_id": "CORE-000002", "message": "example", "issues": 3}
        ] if "ISSUE REPORTED" in statuses else [],
    }


def test_issue_reported_and_skipped_are_triaged_not_treated_as_engine_failure() -> None:
    metrics, checks = triage_core_report(
        _report(["SUCCESS", "ISSUE REPORTED", "SKIPPED"]), _cfg(), cli_exit_code=0
    )
    assert metrics["all_passed"] is True
    assert metrics["executable_validation_performed"] is True
    assert metrics["execution_status"] == "EXECUTED"
    assert metrics["rules_total"] == 3
    assert metrics["rules_executed"] == 2
    assert metrics["success_rules"] == 1
    assert metrics["issue_reported_rules"] == 1
    assert metrics["skipped_rules"] == 1
    assert metrics["execution_error_rules"] == 0
    assert metrics["issue_observations"] == 3
    assert all(row["passed"] for row in checks)


def test_execution_error_is_blocking() -> None:
    metrics, checks = triage_core_report(
        _report(["SUCCESS", "EXECUTION ERROR"]), _cfg(), cli_exit_code=0
    )
    assert metrics["all_passed"] is False
    assert metrics["execution_error_rules"] == 1
    assert any(row["check"] == "no CORE execution errors" and not row["passed"] for row in checks)


def test_all_skipped_is_blocking() -> None:
    metrics, _ = triage_core_report(_report(["SKIPPED", "SKIPPED"]), _cfg(), cli_exit_code=0)
    assert metrics["all_passed"] is False
    assert metrics["rules_executed"] == 0


def test_empty_rules_report_is_blocking_but_parseable() -> None:
    metrics, checks = triage_core_report(_report([]), _cfg(), cli_exit_code=0)
    assert metrics["all_passed"] is False
    assert metrics["rules_total"] == 0
    assert metrics["rules_executed"] == 0
    assert any(row["check"] == "CORE Rules_Report is non-empty" and not row["passed"] for row in checks)


def test_unknown_status_is_blocking() -> None:
    metrics, _ = triage_core_report(_report(["SUCCESS", "MYSTERY"]), _cfg(), cli_exit_code=0)
    assert metrics["all_passed"] is False
    assert metrics["unknown_statuses"] == ["MYSTERY"]


def test_nonzero_cli_exit_is_blocking() -> None:
    metrics, _ = triage_core_report(_report(["SUCCESS"]), _cfg(), cli_exit_code=2)
    assert metrics["all_passed"] is False
    assert metrics["cli_exit_code"] == 2


def test_write_outputs_retains_raw_report_and_machine_evidence(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    report_path = tmp_path / "core_report.json"
    report_path.write_text(
        json.dumps(_report(["SUCCESS", "ISSUE REPORTED", "SKIPPED"])), encoding="utf-8"
    )
    metrics = write_core_outputs(tmp_path, report_path, cli_exit_code=0)
    assert metrics["all_passed"] is True
    assert len(metrics["official_report_sha256"]) == 64
    assert (tmp_path / "outputs" / "core_official_report.json").is_file()
    assert (tmp_path / "outputs" / "core_rules_report.csv").is_file()
    assert (tmp_path / "outputs" / "core_issue_summary.csv").is_file()
    assert (tmp_path / "outputs" / "core_validation_qc.csv").is_file()
    assert (tmp_path / "outputs" / "core_validation_metrics.json").is_file()
    assert (tmp_path / "outputs" / "core_validation_summary.md").is_file()


def test_unavailable_state_writes_evidence_without_fabricating_official_report(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    manifest = {
        "all_passed": True,
        "ruleset_state": NOT_AVAILABLE,
        "rule_count": 0,
        "unpublished_adamig_rule_count": 24,
        "published_adamig_reference_count": 0,
    }
    manifest_path = tmp_path / "outputs" / "core_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    metrics = write_core_unavailable_outputs(tmp_path, manifest_path)
    assert metrics["all_passed"] is True
    assert metrics["executable_validation_performed"] is False
    assert metrics["execution_status"] == NOT_AVAILABLE
    assert metrics["rules_executed"] == 0
    assert not (tmp_path / "outputs" / "core_official_report.json").exists()
    assert (tmp_path / "outputs" / "core_validation_metrics.json").is_file()
    assert "Zero rules" in (tmp_path / "outputs" / "core_validation_summary.md").read_text(encoding="utf-8")


def test_unavailable_state_rejects_inconsistent_nonzero_rule_count(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    manifest_path = tmp_path / "outputs" / "core_cache_manifest.json"
    manifest_path.write_text(
        json.dumps({"all_passed": True, "ruleset_state": NOT_AVAILABLE, "rule_count": 2}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unavailable-state evidence gate failed"):
        write_core_unavailable_outputs(tmp_path, manifest_path)


def test_zero_rule_report_writes_failure_evidence_before_raising(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    report_path = tmp_path / "core_report.json"
    report_path.write_text(json.dumps(_report([])), encoding="utf-8")
    with pytest.raises(ValueError, match="CORE triage gate failed"):
        write_core_outputs(tmp_path, report_path, cli_exit_code=0)
    metrics = json.loads((tmp_path / "outputs" / "core_validation_metrics.json").read_text(encoding="utf-8"))
    assert metrics["rules_total"] == 0
    assert metrics["all_passed"] is False
    assert (tmp_path / "outputs" / "core_rules_report.csv").is_file()


def test_write_outputs_raises_after_writing_failed_qc(tmp_path: Path) -> None:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    report_path = tmp_path / "core_report.json"
    report_path.write_text(json.dumps(_report(["EXECUTION ERROR"])), encoding="utf-8")
    with pytest.raises(ValueError, match="CORE triage gate failed"):
        write_core_outputs(tmp_path, report_path, cli_exit_code=0)
    assert (tmp_path / "outputs" / "core_validation_qc.csv").is_file()

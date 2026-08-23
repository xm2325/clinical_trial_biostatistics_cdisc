from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.19.0"
DEFAULT_ALLOWED_STATUSES = {
    "SUCCESS",
    "ISSUE REPORTED",
    "SKIPPED",
    "EXECUTION ERROR",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalise_status(value: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").upper().split())


def _rules_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if "Rules_Report" not in report:
        raise ValueError("CORE JSON report is missing Rules_Report")
    rows = report["Rules_Report"]
    if not isinstance(rows, list):
        raise ValueError("CORE Rules_Report must be a list")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("CORE Rules_Report must be a list of objects")
    return rows


def _issue_summary(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("Issue_Summary", [])
    return rows if isinstance(rows, list) else []


def triage_core_report(
    report: dict[str, Any],
    cfg: dict[str, Any],
    cli_exit_code: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if cfg.get("version") != VERSION:
        raise ValueError("standards-validation config must be version 0.19.0")
    core_cfg = cfg.get("core", {})
    if core_cfg.get("conformance_claim") != "NOT_ASSESSED":
        raise ValueError("CORE conformance claim must remain NOT_ASSESSED")

    rules = _rules_report(report)
    statuses = [_normalise_status(row.get("status")) for row in rules]
    allowed = {
        _normalise_status(value)
        for value in core_cfg.get("allowed_statuses", sorted(DEFAULT_ALLOWED_STATUSES))
    }
    unknown = sorted(set(statuses) - allowed)
    counts = Counter(statuses)
    success_rules = counts.get("SUCCESS", 0)
    issue_rules = counts.get("ISSUE REPORTED", 0)
    skipped_rules = counts.get("SKIPPED", 0)
    execution_errors = counts.get("EXECUTION ERROR", 0)
    executed_rules = success_rules + issue_rules

    issues = _issue_summary(report)
    issue_observations = 0
    for row in issues:
        try:
            issue_observations += int(row.get("issues") or 0)
        except (TypeError, ValueError):
            pass

    details = report.get("Conformance_Details", {})
    if not isinstance(details, dict):
        details = {}
    reported_standard = str(details.get("Standard") or "")
    reported_version = str(details.get("Version") or "")
    expected_standard = str(core_cfg.get("standard") or "")
    expected_version = str(core_cfg.get("version") or "")
    standard_ok = not reported_standard or reported_standard.lower() == expected_standard.lower()
    version_ok = not reported_version or reported_version.upper().lstrip("V") == expected_version.upper().lstrip("V")

    checks = [
        {
            "check": "CORE CLI process exited successfully",
            "passed": int(cli_exit_code) == 0,
            "detail": f"exit_code={int(cli_exit_code)}",
        },
        {
            "check": "CORE Rules_Report is non-empty",
            "passed": len(rules) > 0,
            "detail": f"rules={len(rules)}",
        },
        {
            "check": "CORE rule statuses are recognised",
            "passed": not unknown,
            "detail": f"unknown={unknown}",
        },
        {
            "check": "at least one CORE rule executed",
            "passed": executed_rules > 0,
            "detail": f"executed={executed_rules}; skipped={skipped_rules}",
        },
        {
            "check": "no CORE execution errors",
            "passed": execution_errors == 0,
            "detail": f"execution_errors={execution_errors}",
        },
        {
            "check": "reported CORE standard matches pinned request",
            "passed": standard_ok,
            "detail": f"reported={reported_standard or 'not supplied'}; expected={expected_standard}",
        },
        {
            "check": "reported CORE version matches pinned request",
            "passed": version_ok,
            "detail": f"reported={reported_version or 'not supplied'}; expected=V{expected_version}",
        },
        {
            "check": "formal conformance claim remains disabled",
            "passed": core_cfg.get("conformance_claim") == "NOT_ASSESSED",
            "detail": "portfolio triage evidence only",
        },
    ]
    all_passed = all(bool(row["passed"]) for row in checks)
    metrics = {
        "analysis_version": VERSION,
        "core_repository": core_cfg.get("repository"),
        "core_commit": core_cfg.get("commit"),
        "cache_commit": core_cfg.get("cache_commit"),
        "standard": expected_standard,
        "version": expected_version,
        "cli_exit_code": int(cli_exit_code),
        "rules_total": len(rules),
        "rules_executed": executed_rules,
        "status_counts": {key: counts.get(key, 0) for key in sorted(allowed)},
        "success_rules": success_rules,
        "issue_reported_rules": issue_rules,
        "skipped_rules": skipped_rules,
        "execution_error_rules": execution_errors,
        "issue_summary_rows": len(issues),
        "issue_observations": issue_observations,
        "unknown_statuses": unknown,
        "conformance_claim": "NOT_ASSESSED",
        "all_passed": all_passed,
    }
    return metrics, checks


def write_core_outputs(
    root: Path,
    report_path: Path,
    cli_exit_code: int = 0,
) -> dict[str, Any]:
    root = Path(root)
    report_path = Path(report_path)
    if not report_path.is_file():
        raise ValueError(f"CORE JSON report not found: {report_path}")
    cfg = json.loads((root / "spec" / "standards_validation_v0_19.json").read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics, checks = triage_core_report(report, cfg, cli_exit_code=cli_exit_code)

    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    raw_target = outputs / "core_official_report.json"
    if report_path.resolve() != raw_target.resolve():
        shutil.copyfile(report_path, raw_target)
    metrics["official_report_sha256"] = _sha256(raw_target)

    rules = _rules_report(report)
    rule_columns = ["core_id", "cdisc_rule_id", "fda_rule_id", "message", "status"]
    rule_rows = []
    for row in rules:
        rule_rows.append(
            {
                "core_id": row.get("core_id"),
                "cdisc_rule_id": row.get("cdisc_rule_id"),
                "fda_rule_id": row.get("fda_rule_id"),
                "message": row.get("message"),
                "status": _normalise_status(row.get("status")),
            }
        )
    pd.DataFrame(rule_rows, columns=rule_columns).to_csv(outputs / "core_rules_report.csv", index=False)
    pd.DataFrame(_issue_summary(report)).to_csv(outputs / "core_issue_summary.csv", index=False)
    pd.DataFrame(checks).to_csv(outputs / "core_validation_qc.csv", index=False)
    (outputs / "core_validation_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = [
        "# CDISC CORE executable validation triage",
        "",
        f"- Pinned CORE commit: `{metrics['core_commit']}`.",
        f"- Pinned official cache commit: `{metrics['cache_commit']}`.",
        f"- Requested standard: `{metrics['standard']} {metrics['version']}`.",
        f"- Rules in report: {metrics['rules_total']}.",
        f"- Executed rules: {metrics['rules_executed']}.",
        f"- SUCCESS: {metrics['success_rules']}.",
        f"- ISSUE REPORTED: {metrics['issue_reported_rules']}.",
        f"- SKIPPED: {metrics['skipped_rules']}.",
        f"- EXECUTION ERROR: {metrics['execution_error_rules']}.",
        f"- Issue observations reported: {metrics['issue_observations']}.",
        f"- Machine gate: {'PASS' if metrics['all_passed'] else 'FAIL'}.",
        "",
        "ISSUE REPORTED is retained as review evidence rather than treated as a pipeline crash. The blocking conditions are tool/process failure, unknown statuses, no executed rules, or CORE EXECUTION ERROR.",
        "Successful CORE execution does not establish formal ADaM conformance or regulatory-submission readiness.",
    ]
    (outputs / "core_validation_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise ValueError("CDISC CORE triage gate failed; inspect outputs/core_validation_qc.csv")
    return metrics

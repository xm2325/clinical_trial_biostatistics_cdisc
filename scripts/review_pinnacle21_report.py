from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

CLAIM = "PORTFOLIO_PINNACLE21_COMMUNITY_VALIDATION_EXECUTED"


def _norm(value: Any) -> str:
    text = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", text).strip()


def _header_row(raw: pd.DataFrame, required: set[str]) -> int:
    for idx in range(min(len(raw), 80)):
        values = {_norm(value) for value in raw.iloc[idx].tolist() if _norm(value)}
        if required.issubset(values):
            return idx
    raise ValueError(f"Could not find header with required columns {sorted(required)}")


def _read_issue_summary(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Issue Summary", header=None, engine="openpyxl")
    idx = _header_row(raw, {"Pinnacle 21 ID", "Message", "Found"})
    header = [_norm(v) or f"column_{i+1}" for i, v in enumerate(raw.iloc[idx].tolist())]
    body = raw.iloc[idx + 1 :].copy()
    body.columns = header
    body = body.dropna(how="all")
    body["Pinnacle 21 ID"] = body["Pinnacle 21 ID"].map(_norm)
    body["Message"] = body["Message"].map(_norm)
    body["Severity"] = body.get("Severity", pd.Series(index=body.index, dtype=object)).map(_norm)
    body["Found"] = pd.to_numeric(body["Found"], errors="coerce")
    body = body[body["Pinnacle 21 ID"].str.match(r"^[A-Z]{2}\d{4}$", na=False) & body["Found"].notna()].copy()
    body["Found"] = body["Found"].astype(int)
    return body[[c for c in ["Source", "Pinnacle 21 ID", "Message", "Severity", "Found"] if c in body.columns]]


def _read_details(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Details", header=None, engine="openpyxl")
    idx = _header_row(raw, {"Pinnacle 21 ID", "Message", "Variables", "Values"})
    header = [_norm(v) or f"column_{i+1}" for i, v in enumerate(raw.iloc[idx].tolist())]
    body = raw.iloc[idx + 1 :].copy()
    body.columns = header
    body = body.dropna(how="all")
    for col in ["Domain", "Variables", "Values", "Pinnacle 21 ID", "Message", "Severity"]:
        if col not in body:
            body[col] = ""
        body[col] = body[col].map(_norm)
    body = body[body["Pinnacle 21 ID"].str.match(r"^[A-Z]{2}\d{4}$", na=False)].copy()
    body = body.rename(
        columns={
            "Domain": "source",
            "Variables": "variables",
            "Values": "values",
            "Pinnacle 21 ID": "rule_id",
            "Message": "message",
            "Severity": "severity",
        }
    )
    body["review_disposition"] = "REVIEW_REQUIRED"
    body["review_rationale"] = (
        "Captured from the Pinnacle 21 Details sheet; remediation/disposition is tracked in the v0.27 findings cycle."
    )
    return body[[
        "source", "rule_id", "message", "severity", "variables", "values",
        "review_disposition", "review_rationale",
    ]]


def _inventory(path: Path) -> pd.DataFrame:
    book = pd.ExcelFile(path, engine="openpyxl")
    rows = []
    for sheet in book.sheet_names:
        raw = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
        rows.append({"sheet": sheet, "rows": int(len(raw)), "columns": int(len(raw.columns))})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--community-version", default="4.2.0")
    args = parser.parse_args()

    report = Path(args.report)
    log = Path(args.log)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not report.exists() or report.stat().st_size == 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-6000:] if log.exists() else "missing log"
        raise SystemExit(f"Pinnacle 21 execution did not produce a report: {report}\n{tail}")

    issue_summary = _read_issue_summary(report)
    findings = _read_details(report)
    inventory = _inventory(report)

    issue_summary.rename(
        columns={
            "Source": "source",
            "Pinnacle 21 ID": "rule_id",
            "Message": "message",
            "Severity": "severity",
            "Found": "occurrences",
        }
    ).to_csv(out / "pinnacle21_issue_summary.csv", index=False)
    findings.to_csv(out / "pinnacle21_findings_review.csv", index=False)
    inventory.to_csv(out / "pinnacle21_report_inventory.csv", index=False)

    reported_occurrences = int(issue_summary["Found"].sum())
    detail_occurrences = int(len(findings))
    if reported_occurrences != detail_occurrences:
        accounting = "REPORT_CUTOFF_OR_DETAIL_MISMATCH"
    else:
        accounting = "ISSUE_SUMMARY_MATCHES_DETAILS"

    severity_counts: dict[str, int] = {}
    for _, row in issue_summary.iterrows():
        severity = _norm(row.get("Severity")) or "UNSPECIFIED"
        severity_counts[severity] = severity_counts.get(severity, 0) + int(row["Found"])

    validation_raw = pd.read_excel(report, sheet_name="Validation Summary", header=None, engine="openpyxl")
    validation_text = "\n".join(_norm(v) for v in validation_raw.to_numpy().ravel() if _norm(v))
    unsupported_os = "Unsupported OS used" in validation_text

    metrics = {
        "version": "0.27.0",
        "pinnacle21_community_version": args.community_version,
        "runtime_executed": True,
        "report_generated": True,
        "report_bytes": int(report.stat().st_size),
        "report_sheets": int(len(inventory)),
        "issue_classes": int(len(issue_summary)),
        "reported_occurrences": reported_occurrences,
        "machine_readable_findings": detail_occurrences,
        "finding_accounting": accounting,
        "severity_counts": severity_counts,
        "review_required": detail_occurrences,
        "validator_environment_warning": "UNSUPPORTED_OS" if unsupported_os else "NONE_DETECTED",
        "controlled_claim": CLAIM,
        "conformance_claim": "NOT_ASSESSED",
        "submission_readiness_claim": "NOT_CLAIMED",
        "evidence_boundary": (
            "Pinnacle 21 Community execution on public-data portfolio metadata only; not a validated GxP environment, "
            "not sponsor/CRO production, not formal ADaM conformance, and not a regulatory submission package."
        ),
    }
    (out / "pinnacle21_validation_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Pinnacle 21 Community validation summary",
        "",
        f"- Community version: **{args.community_version}**",
        "- Runtime executed: **yes**",
        f"- Report: `{report.name}` ({report.stat().st_size:,} bytes)",
        f"- P21 issue classes: **{len(issue_summary)}**",
        f"- P21 reported occurrences: **{reported_occurrences}**",
        f"- Detail rows captured for review: **{detail_occurrences}**",
        f"- Finding accounting: **{accounting}**",
        f"- Validator environment warning: **{'UNSUPPORTED_OS' if unsupported_os else 'NONE_DETECTED'}**",
        f"- Controlled claim: `{CLAIM}`",
        "- Formal ADaM conformance: **NOT_ASSESSED**",
        "- Regulatory submission readiness: **NOT_CLAIMED**",
        "",
        "## Findings disposition",
        "",
        "Only the `Details` sheet is counted as finding occurrences; the `Rules` sheet is a rule catalogue and is not counted as findings. All detail rows remain `REVIEW_REQUIRED` until the remediation cycle classifies or eliminates them.",
    ]
    (out / "pinnacle21_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

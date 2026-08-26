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


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(value).lower()).strip("_")


def _find_header(raw: pd.DataFrame) -> int | None:
    tokens = {"rule_id", "ruleid", "severity", "message", "description", "dataset", "domain", "variable"}
    best: tuple[int, int] | None = None
    for idx in range(min(len(raw), 80)):
        row_tokens = {_slug(value) for value in raw.iloc[idx].tolist() if _norm(value)}
        score = len(tokens & row_tokens)
        if score >= 2 and (best is None or score > best[1]):
            best = (idx, score)
    return None if best is None else best[0]


def _sheet_findings(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    book = pd.ExcelFile(path, engine="openpyxl")
    findings: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    for sheet in book.sheet_names:
        raw = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
        header_idx = _find_header(raw)
        sheets.append({"sheet": sheet, "rows": int(len(raw)), "header_row": header_idx if header_idx is not None else -1})
        if header_idx is None:
            continue
        header = [_slug(value) or f"column_{i+1}" for i, value in enumerate(raw.iloc[header_idx].tolist())]
        seen: dict[str, int] = {}
        unique_header: list[str] = []
        for name in header:
            seen[name] = seen.get(name, 0) + 1
            unique_header.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
        body = raw.iloc[header_idx + 1 :].copy()
        body.columns = unique_header
        body = body.dropna(how="all")
        for _, row in body.iterrows():
            record = {key: _norm(value) for key, value in row.to_dict().items()}
            populated = [value for value in record.values() if value]
            if not populated:
                continue
            rule = record.get("rule_id") or record.get("ruleid") or record.get("rule") or record.get("id") or ""
            severity = record.get("severity") or record.get("level") or ""
            message = record.get("message") or record.get("description") or record.get("issue") or ""
            if not (rule or severity or message):
                continue
            findings.append({
                "sheet": sheet,
                "rule_id": rule,
                "severity": severity,
                "message": message,
                "dataset": record.get("dataset") or record.get("domain") or "",
                "variable": record.get("variable") or "",
                "value": record.get("value") or "",
                "review_disposition": "REVIEW_REQUIRED",
                "review_rationale": "Initial machine-readable capture; remediation/disposition is performed in the v0.27 findings-review cycle.",
            })
    return findings, sheets


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

    findings, sheets = _sheet_findings(report)
    findings_df = pd.DataFrame(findings, columns=[
        "sheet", "rule_id", "severity", "message", "dataset", "variable", "value",
        "review_disposition", "review_rationale",
    ])
    findings_df.to_csv(out / "pinnacle21_findings_review.csv", index=False)
    pd.DataFrame(sheets).to_csv(out / "pinnacle21_report_inventory.csv", index=False)

    severity_counts: dict[str, int] = {}
    for severity, count in findings_df.get("severity", pd.Series(dtype=str)).fillna("").value_counts().items():
        severity_counts[str(severity) or "UNSPECIFIED"] = int(count)

    metrics = {
        "version": "0.27.0",
        "pinnacle21_community_version": args.community_version,
        "runtime_executed": True,
        "report_generated": True,
        "report_bytes": int(report.stat().st_size),
        "report_sheets": len(sheets),
        "machine_readable_findings": int(len(findings_df)),
        "severity_counts": severity_counts,
        "review_required": int(len(findings_df)),
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
        f"- Workbook sheets inventoried: **{len(sheets)}**",
        f"- Machine-readable findings captured: **{len(findings_df)}**",
        f"- Controlled claim: `{CLAIM}`",
        "- Formal ADaM conformance: **NOT_ASSESSED**",
        "- Regulatory submission readiness: **NOT_CLAIMED**",
        "",
        "## Initial findings disposition",
        "",
        "All captured findings are initially `REVIEW_REQUIRED`. The next v0.27 step classifies each finding as fixable, explainable portfolio boundary, or tool/configuration limitation and reruns Pinnacle 21 after remediation.",
    ]
    if severity_counts:
        lines += ["", "## Severity counts", ""] + [f"- {key or 'UNSPECIFIED'}: **{value}**" for key, value in sorted(severity_counts.items())]
    (out / "pinnacle21_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.22.0"
RUNTIME_STATUS = "NOT_EXECUTED_NO_SAS_RUNTIME"
EVIDENCE_CLAIM = "PORTFOLIO_SAS_STATIC_REVIEW_COMPLETE"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "required": True, "detail": detail})


def _validate_configuration(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError("SAS static review config must be version 0.22.0")
    if cfg.get("runtime_status") != RUNTIME_STATUS:
        raise ValueError("SAS runtime status must remain NOT_EXECUTED_NO_SAS_RUNTIME")
    if cfg.get("evidence_claim") != EVIDENCE_CLAIM:
        raise ValueError("SAS evidence claim must remain portfolio-scoped")
    boundary = str(cfg.get("evidence_boundary", ""))
    if "no SAS runtime" not in boundary or "no executed SAS output" not in boundary:
        raise ValueError("SAS evidence boundary must explicitly state the unexecuted-runtime limitation")

    programs = cfg.get("programs")
    if not isinstance(programs, list) or len(programs) < 3:
        raise ValueError("at least three SAS program contracts are required")
    ids = [str(item.get("id", "")) for item in programs]
    paths = [str(item.get("path", "")) for item in programs]
    if any(not value for value in ids + paths) or len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
        raise ValueError("SAS program ids and paths must be non-empty and unique")
    for item in programs:
        required = item.get("required_fragments")
        forbidden = item.get("forbidden_fragments")
        if not isinstance(required, list) or not required or len(required) != len(set(required)):
            raise ValueError(f"{item['id']} required_fragments must be a non-empty unique list")
        if not isinstance(forbidden, list) or len(forbidden) != len(set(forbidden)):
            raise ValueError(f"{item['id']} forbidden_fragments must be a unique list")

    sources = cfg.get("source_contracts")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source_contracts must be a non-empty list")
    source_paths = [str(item.get("path", "")) for item in sources]
    if any(not path for path in source_paths) or len(source_paths) != len(set(source_paths)):
        raise ValueError("source contract paths must be non-empty and unique")
    for item in sources:
        cols = item.get("required_columns")
        if not isinstance(cols, list) or not cols or len(cols) != len(set(cols)):
            raise ValueError(f"{item['path']} required_columns must be a non-empty unique list")


def assess_sas_static_review(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "sas_static_review_v0_22.json")
    _validate_configuration(cfg)
    checks: list[dict[str, Any]] = []

    source_ok = True
    source_rows = 0
    for contract in cfg["source_contracts"]:
        path = root / contract["path"]
        exists = path.exists()
        _check(checks, f"source exists: {contract['path']}", exists, f"exists={exists}")
        if not exists:
            source_ok = False
            continue
        frame = pd.read_csv(path, nrows=5)
        missing = sorted(set(contract["required_columns"]) - set(frame.columns))
        passed = not missing
        source_ok = source_ok and passed
        source_rows += 1
        _check(
            checks,
            f"source schema matches: {contract['path']}",
            passed,
            "missing=" + (",".join(missing) if missing else "0"),
        )

    program_rows: list[dict[str, Any]] = []
    program_ok = True
    prohibited = [_norm(item) for item in cfg.get("prohibited_claim_fragments", [])]
    total_required_fragments = 0
    matched_required_fragments = 0
    total_forbidden_hits = 0

    for contract in cfg["programs"]:
        path = root / contract["path"]
        exists = path.exists()
        _check(checks, f"SAS program exists: {contract['id']}", exists, str(path.relative_to(root)))
        if not exists:
            program_ok = False
            program_rows.append(
                {
                    "program_id": contract["id"],
                    "role": contract["role"],
                    "path": contract["path"],
                    "sha256": "",
                    "required_fragments": len(contract["required_fragments"]),
                    "matched_required_fragments": 0,
                    "forbidden_hits": 0,
                    "runtime_status": RUNTIME_STATUS,
                    "passed": False,
                }
            )
            continue

        text = path.read_text(encoding="utf-8")
        normalised = _norm(text)
        required = [_norm(item) for item in contract["required_fragments"]]
        missing_required = [raw for raw, normed in zip(contract["required_fragments"], required) if normed not in normalised]
        forbidden = [_norm(item) for item in contract["forbidden_fragments"]]
        forbidden_hits = [raw for raw, normed in zip(contract["forbidden_fragments"], forbidden) if normed and normed in normalised]
        prohibited_hits = [item for item in prohibited if item and item in normalised]
        status_present = _norm(RUNTIME_STATUS) in normalised

        basis = contract.get("translation_basis")
        basis_exists = True if not basis else (root / str(basis)).exists()

        matched = len(required) - len(missing_required)
        total_required_fragments += len(required)
        matched_required_fragments += matched
        total_forbidden_hits += len(forbidden_hits) + len(prohibited_hits)
        passed = not missing_required and not forbidden_hits and not prohibited_hits and status_present and basis_exists
        program_ok = program_ok and passed

        _check(
            checks,
            f"required SAS semantics present: {contract['id']}",
            not missing_required,
            "missing=" + (" | ".join(missing_required) if missing_required else "0"),
        )
        _check(
            checks,
            f"forbidden SAS semantics absent: {contract['id']}",
            not forbidden_hits and not prohibited_hits,
            "hits=" + (" | ".join(forbidden_hits + prohibited_hits) if forbidden_hits or prohibited_hits else "0"),
        )
        _check(
            checks,
            f"unexecuted SAS status explicit: {contract['id']}",
            status_present,
            f"runtime_status={RUNTIME_STATUS}",
        )
        _check(
            checks,
            f"translation basis exists: {contract['id']}",
            basis_exists,
            str(basis or "not_applicable"),
        )

        program_rows.append(
            {
                "program_id": contract["id"],
                "role": contract["role"],
                "path": contract["path"],
                "sha256": _sha256(path),
                "required_fragments": len(required),
                "matched_required_fragments": matched,
                "forbidden_hits": len(forbidden_hits) + len(prohibited_hits),
                "runtime_status": RUNTIME_STATUS,
                "passed": passed,
            }
        )

    analytic = [row for row in program_rows if row["program_id"] in {"SAS-MMRM-01", "SAS-SAFETY-01"}]
    macro_use_ok = len(analytic) == 2 and all(row["passed"] for row in analytic)
    _check(
        checks,
        "both analytic translations use the controlled macro contract",
        macro_use_ok,
        f"analytic_programs={len(analytic)}; passed={sum(bool(row['passed']) for row in analytic)}",
    )

    mmrm_basis = (root / "R" / "mmrm_analysis.R").read_text(encoding="utf-8") if (root / "R" / "mmrm_analysis.R").exists() else ""
    mmrm_basis_norm = _norm(mmrm_basis)
    basis_semantics_ok = all(
        token in mmrm_basis_norm
        for token in [
            _norm("CHG ~ TRT01A * AVISIT + BASE * AVISIT"),
            _norm("us(AVISIT | USUBJID)"),
            _norm('method = "Satterthwaite"'),
            _norm("reml = TRUE"),
        ]
    )
    _check(
        checks,
        "SAS MMRM translation basis still carries the validated R model contract",
        basis_semantics_ok,
        "R/mmrm_analysis.R model/covariance/df/REML markers",
    )

    safety_basis = (root / "src" / "cdisc_portfolio" / "analysis.py").read_text(encoding="utf-8") if (root / "src" / "cdisc_portfolio" / "analysis.py").exists() else ""
    safety_basis_ok = "def teae_risk_differences" in safety_basis and 'adae["TRTEMFL"].eq("Y")' in safety_basis
    _check(
        checks,
        "SAS safety translation basis still carries subject-level TEAE risk-difference logic",
        safety_basis_ok,
        "src/cdisc_portfolio/analysis.py teae_risk_differences",
    )

    required_checks = sum(bool(row["required"]) for row in checks)
    required_passed = sum(bool(row["required"] and row["passed"]) for row in checks)
    all_passed = bool(source_ok and program_ok and basis_semantics_ok and safety_basis_ok and required_checks == required_passed)

    metrics: dict[str, Any] = {
        "analysis_version": VERSION,
        "runtime_status": RUNTIME_STATUS,
        "sas_runtime_executed": False,
        "evidence_claim": EVIDENCE_CLAIM,
        "programs_expected": len(cfg["programs"]),
        "programs_passed": sum(bool(row["passed"]) for row in program_rows),
        "source_contracts_expected": len(cfg["source_contracts"]),
        "source_contracts_read": source_rows,
        "required_fragments": total_required_fragments,
        "matched_required_fragments": matched_required_fragments,
        "forbidden_or_overclaim_hits": total_forbidden_hits,
        "required_checks": required_checks,
        "required_checks_passed": required_passed,
        "all_passed": all_passed,
        "evidence_boundary": cfg["evidence_boundary"],
    }
    return program_rows, checks, metrics


def write_sas_static_review_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    program_rows, checks, metrics = assess_sas_static_review(root)

    pd.DataFrame(program_rows).to_csv(outputs / "sas_static_review.csv", index=False)
    pd.DataFrame(checks).to_csv(outputs / "sas_static_review_checks.csv", index=False)
    (outputs / "sas_static_review_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# SAS static translation review",
        "",
        f"- version: **{metrics['analysis_version']}**",
        f"- runtime status: **{metrics['runtime_status']}**",
        f"- SAS runtime executed: **{str(metrics['sas_runtime_executed']).lower()}**",
        f"- programs passed: **{metrics['programs_passed']}/{metrics['programs_expected']}**",
        f"- live source contracts read: **{metrics['source_contracts_read']}/{metrics['source_contracts_expected']}**",
        f"- required SAS semantic fragments: **{metrics['matched_required_fragments']}/{metrics['required_fragments']}**",
        f"- forbidden/overclaim hits: **{metrics['forbidden_or_overclaim_hits']}**",
        f"- required review checks: **{metrics['required_checks_passed']}/{metrics['required_checks']}**",
        f"- evidence claim: **`{metrics['evidence_claim']}`**",
        "",
        "This is static source and semantic-contract evidence only. No SAS runtime was available in this workflow, so no SAS-generated numerical result is presented or compared as executed evidence.",
        "",
        "## Program review",
        "",
    ]
    for row in program_rows:
        lines.append(
            f"- `{row['program_id']}` — {row['role']}: "
            f"{row['matched_required_fragments']}/{row['required_fragments']} required fragments, "
            f"forbidden hits={row['forbidden_hits']}, passed={row['passed']}."
        )
    (outputs / "sas_static_review_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not metrics["all_passed"]:
        raise RuntimeError("SAS static translation review failed")
    return metrics

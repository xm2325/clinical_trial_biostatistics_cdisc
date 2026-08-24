from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.20.0"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _bool_metric(path: Path, *keys: str) -> bool:
    data = _load_json(path)
    for key in keys:
        if key in data:
            return bool(data[key])
    raise ValueError(f"none of {keys} found in {path}")


def _date_after_cutoff(frame: pd.DataFrame, columns: list[str], cutoff: pd.Timestamp) -> int:
    total = 0
    for column in columns:
        if column not in frame.columns:
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce")
        total += int((parsed > cutoff).sum())
    return total


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def assess_analysis_readiness(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "analysis_readiness_v0_20.json")
    if cfg.get("version") != VERSION:
        raise ValueError("analysis-readiness config must be version 0.20.0")
    if cfg.get("readiness_claim") != "PORTFOLIO_ANALYSIS_PACKAGE_READY_FOR_REVIEW":
        raise ValueError("readiness_claim must remain portfolio-scoped")

    outputs = root / "outputs"
    adsl = pd.read_csv(outputs / "adsl_style.csv")
    adae = pd.read_csv(outputs / "adae_style.csv")
    adqs = pd.read_csv(outputs / "adqs_actot_style.csv")
    adtte = pd.read_csv(outputs / "adtte_retention_style.csv")
    ref = pd.read_csv(outputs / "adqscibc_reference_detail.csv")

    _require_columns(adsl, {"USUBJID", "RANDFL", "EOSDT"}, "ADSL-style")
    _require_columns(adqs, {"USUBJID", "AVISIT", "ABLFL", "EFFFL"}, "ADQS-style")
    _require_columns(adtte, {"USUBJID", "TRT01P", "TRT01A", "ANLTRT"}, "ADTTE-style")
    _require_columns(ref, {"AVAL_MATCH"}, "ADQSCIBC reference detail")

    cutoff = pd.Timestamp(cfg["analysis_data_cutoff"])
    randomized = set(adsl.loc[adsl["RANDFL"].eq("Y"), "USUBJID"].astype(str))
    baseline_randomized = set(
        adqs.loc[
            adqs["USUBJID"].astype(str).isin(randomized) & adqs["ABLFL"].eq("Y"),
            "USUBJID",
        ].astype(str)
    )
    week24_observed = set(
        adqs.loc[
            adqs["USUBJID"].astype(str).isin(randomized)
            & adqs["AVISIT"].astype(str).str.upper().eq("WEEK 24")
            & adqs["EFFFL"].eq("Y"),
            "USUBJID",
        ].astype(str)
    )

    date_after_cutoff = (
        _date_after_cutoff(adsl, ["TRTSDT", "TRTEDT", "EOSDT"], cutoff)
        + _date_after_cutoff(adae, ["ASTDT", "AENDT", "TRTSDT", "TRTEDT"], cutoff)
        + _date_after_cutoff(adqs, ["ADT"], cutoff)
        + _date_after_cutoff(adtte, ["STARTDT", "ADT"], cutoff)
    )

    blinded_cfg = cfg["blinded_review"]
    blinded_rows = [
        {
            "review_scope": "BLINDED_AGGREGATE",
            "check": "subject count reconciles",
            "actual": int(adsl["USUBJID"].nunique()),
            "expected": int(blinded_cfg["required_subject_count"]),
            "passed": int(adsl["USUBJID"].nunique()) == int(blinded_cfg["required_subject_count"]),
            "detail": "aggregate count only; no treatment assignment emitted",
        },
        {
            "review_scope": "BLINDED_AGGREGATE",
            "check": "randomized subject count reconciles",
            "actual": len(randomized),
            "expected": int(blinded_cfg["required_randomized_count"]),
            "passed": len(randomized) == int(blinded_cfg["required_randomized_count"]),
            "detail": "RANDFL count only",
        },
        {
            "review_scope": "BLINDED_AGGREGATE",
            "check": "end-of-study dates complete",
            "actual": int(adsl["EOSDT"].notna().sum()),
            "expected": int(blinded_cfg["required_eos_date_count"]),
            "passed": int(adsl["EOSDT"].notna().sum()) == int(blinded_cfg["required_eos_date_count"]),
            "detail": "EOSDT completeness",
        },
        {
            "review_scope": "BLINDED_AGGREGATE",
            "check": "randomized ACTOT baseline coverage",
            "actual": len(baseline_randomized),
            "expected": int(blinded_cfg["required_actot_baseline_randomized_count"]),
            "passed": len(baseline_randomized) == int(blinded_cfg["required_actot_baseline_randomized_count"]),
            "detail": "baseline coverage without treatment labels",
        },
        {
            "review_scope": "BLINDED_AGGREGATE",
            "check": "no analysed dates exceed configured data cutoff",
            "actual": date_after_cutoff,
            "expected": 0,
            "passed": date_after_cutoff == 0,
            "detail": f"cutoff={cutoff.date().isoformat()}",
        },
    ]

    mismatch_count = int((adtte["TRT01P"].astype(str) != adtte["TRT01A"].astype(str)).sum())
    week24_missing = len(randomized) - len(week24_observed)
    aval_match = ref["AVAL_MATCH"]
    if aval_match.dtype == object:
        aval_match = aval_match.astype(str).str.lower().map({"true": True, "false": False})
    reference_differences = int((aval_match == False).sum())  # noqa: E712

    issue_counts = {
        "AR-001": mismatch_count,
        "AR-002": week24_missing,
        "AR-003": reference_differences,
    }
    issue_rows: list[dict[str, Any]] = []
    for issue_id, issue_cfg in cfg["issue_dispositions"].items():
        actual = int(issue_counts.get(issue_id, -1))
        expected = int(issue_cfg["expected_count"])
        status = str(issue_cfg.get("status", "")).strip()
        resolution = str(issue_cfg.get("resolution", "")).strip()
        blocking = bool(issue_cfg.get("blocking", True))
        passed = actual == expected and bool(status) and bool(resolution) and not blocking
        issue_rows.append(
            {
                "issue_id": issue_id,
                "title": issue_cfg["title"],
                "actual_count": actual,
                "expected_count": expected,
                "status": status,
                "blocking": blocking,
                "resolution": resolution,
                "passed": passed,
            }
        )

    prior_gate_paths = {
        "dataset_review": (outputs / "analysis_dataset_review_metrics.json", ("all_required_review_passed",)),
        "metadata_lineage": (outputs / "metadata_lineage_metrics.json", ("all_passed",)),
        "dataset_json": (outputs / "dataset_json_metrics.json", ("all_passed",)),
        "core_standards_state": (outputs / "core_validation_metrics.json", ("all_passed",)),
        "change_control": (outputs / "change_impact_metrics.json", ("all_passed",)),
        "traceability": (outputs / "traceability_metrics.json", ("all_passed",)),
    }
    final_rows: list[dict[str, Any]] = []
    required_prior = list(cfg["final_analysis_review"]["required_prior_gates"])
    for gate in required_prior:
        if gate not in prior_gate_paths:
            raise ValueError(f"unknown required prior gate: {gate}")
        path, keys = prior_gate_paths[gate]
        passed = _bool_metric(path, *keys)
        final_rows.append(
            {
                "review_scope": "FINAL_ANALYSIS",
                "check": f"prior gate: {gate}",
                "passed": passed,
                "detail": path.name,
            }
        )

    final_rows.extend(
        [
            {
                "review_scope": "FINAL_ANALYSIS",
                "check": "all known analysis issues are dispositioned and count-reconciled",
                "passed": all(bool(row["passed"]) for row in issue_rows),
                "detail": f"issues={len(issue_rows)}",
            },
            {
                "review_scope": "FINAL_ANALYSIS",
                "check": "blinded aggregate review contains no blocking failures",
                "passed": all(bool(row["passed"]) for row in blinded_rows),
                "detail": f"checks={len(blinded_rows)}",
            },
            {
                "review_scope": "FINAL_ANALYSIS",
                "check": "portfolio readiness claim remains non-regulatory",
                "passed": cfg["readiness_claim"] == "PORTFOLIO_ANALYSIS_PACKAGE_READY_FOR_REVIEW",
                "detail": cfg["readiness_claim"],
            },
        ]
    )

    all_passed = (
        all(bool(row["passed"]) for row in blinded_rows)
        and all(bool(row["passed"]) for row in issue_rows)
        and all(bool(row["passed"]) for row in final_rows)
    )
    metrics = {
        "analysis_version": VERSION,
        "analysis_data_cutoff": cutoff.date().isoformat(),
        "subjects": int(adsl["USUBJID"].nunique()),
        "randomized_subjects": len(randomized),
        "randomized_with_actot_baseline": len(baseline_randomized),
        "week24_actot_observed": len(week24_observed),
        "week24_actot_missing": week24_missing,
        "planned_actual_treatment_mismatches": mismatch_count,
        "adqscibc_value_differences": reference_differences,
        "records_after_data_cutoff": date_after_cutoff,
        "blinded_checks": len(blinded_rows),
        "blinded_checks_passed": sum(bool(row["passed"]) for row in blinded_rows),
        "known_issues": len(issue_rows),
        "known_issues_dispositioned": sum(bool(row["passed"]) for row in issue_rows),
        "blocking_open_issues": sum(bool(row["blocking"]) or not bool(row["passed"]) for row in issue_rows),
        "final_checks": len(final_rows),
        "final_checks_passed": sum(bool(row["passed"]) for row in final_rows),
        "readiness_claim": cfg["readiness_claim"],
        "all_passed": all_passed,
    }
    return blinded_rows, issue_rows + final_rows, metrics


def write_analysis_readiness_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    blinded_rows, final_rows, metrics = assess_analysis_readiness(root)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    blinded = pd.DataFrame(blinded_rows)
    forbidden = set(_load_json(root / "spec" / "analysis_readiness_v0_20.json")["blinded_review"]["forbidden_fields"])
    if forbidden & set(blinded.columns):
        raise ValueError("blinded review artifact contains forbidden treatment-assignment fields")
    blinded.to_csv(outputs / "blinded_analysis_readiness_review.csv", index=False)
    pd.DataFrame(final_rows).to_csv(outputs / "analysis_readiness_review.csv", index=False)
    (outputs / "analysis_readiness_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = [
        "# Study-statistician analysis-readiness review",
        "",
        f"- Analysis data cutoff: `{metrics['analysis_data_cutoff']}`.",
        f"- Subjects / randomized: {metrics['subjects']} / {metrics['randomized_subjects']}.",
        f"- Randomized with ACTOT baseline: {metrics['randomized_with_actot_baseline']}.",
        f"- Week 24 ACTOT observed / missing: {metrics['week24_actot_observed']} / {metrics['week24_actot_missing']}.",
        f"- Planned/actual treatment mismatches retained for review: {metrics['planned_actual_treatment_mismatches']}.",
        f"- ADQSCIBC reference-value differences retained with source trace: {metrics['adqscibc_value_differences']}.",
        f"- Records after configured cutoff: {metrics['records_after_data_cutoff']}.",
        f"- Blinded aggregate checks: {metrics['blinded_checks_passed']}/{metrics['blinded_checks']}.",
        f"- Known issues dispositioned: {metrics['known_issues_dispositioned']}/{metrics['known_issues']}.",
        f"- Blocking open issues: {metrics['blocking_open_issues']}.",
        f"- Final readiness checks: {metrics['final_checks_passed']}/{metrics['final_checks']}.",
        f"- Readiness gate: {'PASS' if metrics['all_passed'] else 'FAIL'}.",
        "",
        "The blinded artifact contains aggregate readiness checks only and does not emit treatment assignment fields. The separate final-analysis review retains known non-blocking issues with explicit dispositions rather than hiding them.",
        "This is portfolio analysis-package readiness evidence, not a sponsor database-lock decision, formal blinded-data-review sign-off, or regulatory-submission readiness certification.",
    ]
    (outputs / "analysis_readiness_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise ValueError("analysis-readiness gate failed; inspect outputs/analysis_readiness_review.csv")
    return metrics

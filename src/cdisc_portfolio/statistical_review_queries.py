from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.22.0"
REVIEW_CLAIM = "PORTFOLIO_STATISTICAL_REVIEW_RESPONSE_READY"
QUERY_IDS = {"SRQ-001", "SRQ-002", "SRQ-003", "SRQ-004", "SRQ-005"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError("boolean field contains values other than true/false")
    return mapped.astype(bool)


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "required": True, "detail": detail})


def _validate_config(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError("statistical review query config must be version 0.22.0")
    if cfg.get("review_claim") != REVIEW_CLAIM:
        raise ValueError("review claim must remain portfolio-scoped")
    ids = cfg.get("required_query_ids")
    if not isinstance(ids, list) or set(ids) != QUERY_IDS or len(ids) != len(QUERY_IDS):
        raise ValueError("required_query_ids must contain exactly SRQ-001 through SRQ-005")
    required_inputs = cfg.get("required_inputs")
    if not isinstance(required_inputs, list) or not required_inputs or len(required_inputs) != len(set(required_inputs)):
        raise ValueError("required_inputs must be a non-empty unique list")
    required_rules = {
        "primary_response_must_follow_familywise_decision",
        "missing_data_response_must_report_missingness_and_tipping",
        "treatment_mismatch_response_must_reconcile_to_analysis_data",
        "safety_response_must_remain_descriptive",
        "retention_response_must_remain_exploratory",
    }
    rules = cfg.get("rules", {})
    if set(rules) != required_rules or not all(bool(rules[key]) for key in required_rules):
        raise ValueError("all statistical review response rules must remain enabled")


def assess_statistical_review_queries(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "statistical_review_queries_v0_22.json")
    _validate_config(cfg)
    outputs = root / "outputs"
    checks: list[dict[str, Any]] = []

    missing_inputs = [item for item in cfg["required_inputs"] if not (root / item).exists()]
    _check(
        checks,
        "all controlled reviewer-response inputs exist",
        not missing_inputs,
        "missing=" + (",".join(missing_inputs) if missing_inputs else "0"),
    )
    if missing_inputs:
        return [], checks, {
            "analysis_version": VERSION,
            "review_claim": cfg["review_claim"],
            "all_passed": False,
            "missing_required_inputs": len(missing_inputs),
        }

    readiness = _load_json(outputs / "analysis_readiness_metrics.json")
    csr = _load_json(outputs / "csr_interpretation_metrics.json")
    extension = _load_json(outputs / "csr_interpretation_extension_metrics.json")
    prior_ok = (
        bool(readiness.get("all_passed"))
        and bool(csr.get("all_passed"))
        and bool(extension.get("all_passed"))
        and csr.get("interpretation_claim") == cfg["required_interpretation_claim"]
    )
    _check(
        checks,
        "v0.20 readiness and v0.21 interpretation are complete before reviewer responses",
        prior_ok,
        f"readiness={readiness.get('all_passed')}; csr={csr.get('all_passed')}; extension={extension.get('all_passed')}; claim={csr.get('interpretation_claim')}",
    )

    multiplicity = pd.read_csv(outputs / "table23_actot_multiplicity.csv")
    rbmi = pd.read_csv(outputs / "table22_rbmi_reference_based.csv")
    fixed = pd.read_csv(outputs / "csr_fixed_delta_context.csv")
    safety = pd.read_csv(outputs / "table7_teae_risk_difference.csv")
    retention = pd.read_csv(outputs / "table25_retention_pairwise.csv")
    adtte = pd.read_csv(outputs / "adtte_retention_style.csv")
    matrix = pd.read_csv(outputs / "csr_conclusion_matrix.csv")

    multiplicity["reject_familywise"] = _bool_series(multiplicity["reject_familywise"])
    rbmi["mcse_pass"] = _bool_series(rbmi["mcse_pass"])

    primary_rejections = int(multiplicity["reject_familywise"].sum())
    primary_total = len(multiplicity)
    csr_primary_ok = (
        int(csr.get("primary_familywise_rejections", -1)) == primary_rejections
        and int(csr.get("primary_hypotheses", -1)) == primary_total
    )
    _check(
        checks,
        "primary reviewer response reconciles to the controlled multiplicity decision",
        csr_primary_ok,
        f"rejections={primary_rejections}/{primary_total}; csr={csr.get('primary_familywise_rejections')}/{csr.get('primary_hypotheses')}",
    )

    randomized = int(readiness.get("randomized_subjects", -1))
    observed = int(readiness.get("week24_actot_observed", -1))
    missing = int(readiness.get("week24_actot_missing", -1))
    missingness_ok = randomized > 0 and observed >= 0 and missing >= 0 and observed + missing == randomized
    missing_rate = missing / randomized if randomized > 0 else float("nan")
    _check(
        checks,
        "Week 24 missingness denominator reconciles before robustness response",
        missingness_ok,
        f"observed={observed}; missing={missing}; randomized={randomized}; missing_rate={missing_rate:.6f}",
    )

    expected_comparisons = set(multiplicity["contrast"].astype(str))
    expected_strategies = {"MAR", "JR", "CR", "CIR"}
    rbmi_structure_ok = set(rbmi["comparison"].astype(str)) == expected_comparisons
    rbmi_details: list[str] = []
    for comparison in sorted(expected_comparisons):
        subset = rbmi.loc[rbmi["comparison"].astype(str).eq(comparison)]
        observed_strategies = set(subset["strategy_id"].astype(str))
        comparison_ok = len(subset) == len(expected_strategies) and observed_strategies == expected_strategies
        rbmi_structure_ok = rbmi_structure_ok and comparison_ok
        rbmi_details.append(
            f"{comparison}:strategies={sorted(observed_strategies)},mcse={int(subset['mcse_pass'].sum())}/{len(subset)}"
        )
    rbmi_ok = len(rbmi) == len(expected_comparisons) * len(expected_strategies) and rbmi_structure_ok and bool(rbmi["mcse_pass"].all())
    fixed_ok = (
        len(fixed) == len(expected_comparisons)
        and set(fixed["section"].astype(str)) == {"FIXED_DELTA_SENSITIVITY"}
        and set(fixed["comparison"].astype(str)) == expected_comparisons
    )
    _check(
        checks,
        "missing-data reviewer response includes complete reference-based MI and directional tipping evidence",
        rbmi_ok and fixed_ok,
        "; ".join(rbmi_details) + f"; fixed_delta_context_rows={len(fixed)}",
    )

    if {"TRT01P", "TRT01A"}.issubset(adtte.columns):
        mismatch_count = int((adtte["TRT01P"].astype(str) != adtte["TRT01A"].astype(str)).sum())
    else:
        mismatch_count = -1
    readiness_mismatch = int(readiness.get("planned_actual_treatment_mismatches", -2))
    mismatch_ok = mismatch_count >= 0 and mismatch_count == readiness_mismatch
    _check(
        checks,
        "planned-versus-actual treatment mismatch response reconciles to ADTTE-style analysis data",
        mismatch_ok,
        f"adtte={mismatch_count}; readiness={readiness_mismatch}",
    )

    safety_matrix = matrix.loc[matrix["section"].astype(str).eq("SAFETY")]
    safety_ok = (
        len(safety) == 2
        and len(safety_matrix) == 2
        and set(safety_matrix["analysis_role"].astype(str)) == {"DESCRIPTIVE_SAFETY"}
        and set(safety_matrix["decision"].astype(str)) == {"DESCRIPTIVE_ONLY"}
    )
    _check(
        checks,
        "safety reviewer response remains descriptive",
        safety_ok,
        f"source_rows={len(safety)}; matrix_rows={len(safety_matrix)}",
    )

    retention_matrix = matrix.loc[matrix["section"].astype(str).eq("RETENTION")]
    retention_direction_ok = True
    for row in retention.itertuples(index=False):
        text = str(getattr(row, "interpretation", "")).lower()
        hr = float(row.hazard_ratio)
        if hr > 1:
            retention_direction_ok = retention_direction_ok and "higher study-discontinuation hazard" in text
        elif hr < 1:
            retention_direction_ok = retention_direction_ok and "lower study-discontinuation hazard" in text
        retention_direction_ok = retention_direction_ok and "exploratory" in text
    retention_ok = (
        len(retention) == 2
        and len(retention_matrix) == 2
        and set(retention_matrix["analysis_role"].astype(str)) == {"EXPLORATORY_RETENTION"}
        and retention_direction_ok
    )
    _check(
        checks,
        "retention reviewer response preserves hazard direction and exploratory status",
        retention_ok,
        f"source_rows={len(retention)}; matrix_rows={len(retention_matrix)}",
    )

    adjusted = ", ".join(f"{float(v):.6f}" for v in multiplicity["adjusted_p_value"].astype(float))
    if primary_rejections == 0:
        primary_response = (
            f"The controlled Week 24 family has {primary_rejections}/{primary_total} family-wise rejections "
            f"(adjusted p-values {adjusted}). No confirmatory efficacy success conclusion is supported."
        )
        primary_status = "NO_CONFIRMATORY_EFFICACY_SUCCESS"
    else:
        primary_response = (
            f"The controlled Week 24 family has {primary_rejections}/{primary_total} family-wise rejections. "
            "Any efficacy conclusion is restricted to hypotheses meeting the controlled family-wise rule."
        )
        primary_status = "CONTROLLED_REJECTIONS_PRESENT"

    tipping_details = []
    for row in fixed.itertuples(index=False):
        tipping_details.append(f"{row.comparison}: {float(row.estimate):.4f} ACTOT points")
    missing_response = (
        f"Week 24 ACTOT is missing for {missing}/{randomized} randomized subjects ({missing_rate:.1%}). "
        f"Reference-based MAR/JR/CR/CIR evidence has {int(rbmi['mcse_pass'].sum())}/{len(rbmi)} MCSE passes. "
        f"Directional tipping occurs at {'; '.join(tipping_details)} under the controlled fixed-delta context. "
        "These analyses are supportive sensitivity evidence only; agreement in one sensitivity family is not described as full robustness."
    )

    mismatch_response = (
        f"There are {mismatch_count} planned-versus-actual treatment mismatches in the randomized ADTTE-style data. "
        "The exploratory retention analysis uses planned randomized treatment (TRT01P) as ANLTRT and retains actual treatment as context; the mismatch is not hidden or reclassified as efficacy evidence."
    )

    rd_values = safety["risk_difference"].astype(float)
    safety_response = (
        f"The two active-versus-placebo TEAE risk differences range from {rd_values.min():.4f} to {rd_values.max():.4f}. "
        "They are descriptive safety comparisons in this portfolio; they do not establish a benefit-risk conclusion or constitute evidence of established safety."
    )

    retention_bits = []
    for row in retention.itertuples(index=False):
        hr = float(row.hazard_ratio)
        direction = "higher" if hr > 1 else "lower" if hr < 1 else "equal"
        retention_bits.append(f"{row.comparison}: HR {hr:.4f} ({direction} discontinuation hazard)")
    retention_response = (
        "; ".join(retention_bits)
        + ". These are exploratory study-retention results, not efficacy endpoints."
    )

    rows = [
        {
            "query_id": "SRQ-001",
            "risk_area": "PRIMARY_EFFICACY",
            "reviewer_question": "Do the primary Week 24 results support a confirmatory efficacy success conclusion?",
            "evidence_sources": "outputs/table23_actot_multiplicity.csv; outputs/csr_conclusion_matrix.csv",
            "decision_status": primary_status,
            "response": primary_response,
            "allowed_claim": "Report the controlled multiplicity decision only.",
        },
        {
            "query_id": "SRQ-002",
            "risk_area": "MISSING_DATA",
            "reviewer_question": "Given Week 24 missingness, how robust is the primary efficacy interpretation to missing-data assumptions?",
            "evidence_sources": "outputs/analysis_readiness_metrics.json; outputs/table22_rbmi_reference_based.csv; outputs/csr_fixed_delta_context.csv",
            "decision_status": "SUPPORTIVE_SENSITIVITY_CONTEXT",
            "response": missing_response,
            "allowed_claim": "Describe reference-based MI and fixed-delta tipping together as supportive sensitivity evidence.",
        },
        {
            "query_id": "SRQ-003",
            "risk_area": "TREATMENT_ASSIGNMENT",
            "reviewer_question": "How are planned-versus-actual treatment mismatches handled in the retention analysis?",
            "evidence_sources": "outputs/analysis_readiness_metrics.json; outputs/adtte_retention_style.csv",
            "decision_status": "KNOWN_ISSUE_DISPOSITIONED",
            "response": mismatch_response,
            "allowed_claim": "Retain the mismatch count and planned-treatment analysis choice transparently.",
        },
        {
            "query_id": "SRQ-004",
            "risk_area": "SAFETY",
            "reviewer_question": "Can the TEAE risk-difference results be used as an inferential safety or benefit-risk conclusion?",
            "evidence_sources": "outputs/table7_teae_risk_difference.csv; outputs/csr_conclusion_matrix.csv",
            "decision_status": "DESCRIPTIVE_ONLY",
            "response": safety_response,
            "allowed_claim": "Report observed descriptive safety differences only.",
        },
        {
            "query_id": "SRQ-005",
            "risk_area": "RETENTION",
            "reviewer_question": "What do the retention hazard ratios mean, and can they be interpreted as efficacy results?",
            "evidence_sources": "outputs/table25_retention_pairwise.csv; outputs/csr_conclusion_matrix.csv",
            "decision_status": "EXPLORATORY_ONLY",
            "response": retention_response,
            "allowed_claim": "Interpret HR direction as study-discontinuation hazard and retain exploratory status.",
        },
    ]

    ids_ok = set(row["query_id"] for row in rows) == set(cfg["required_query_ids"]) and len(rows) == len(cfg["required_query_ids"])
    _check(
        checks,
        "review response pack contains exactly the controlled statistical query set",
        ids_ok,
        f"query_ids={sorted(row['query_id'] for row in rows)}",
    )

    response_text = "\n".join(row["response"] + " " + row["allowed_claim"] for row in rows).lower()
    prohibited = [
        str(fragment)
        for fragment in cfg.get("prohibited_claim_fragments", [])
        if str(fragment).lower() in response_text
    ]
    _check(
        checks,
        "generated reviewer responses contain no prohibited positive overclaim fragments",
        not prohibited,
        "matched=" + (",".join(prohibited) if prohibited else "0"),
    )

    all_passed = all(bool(item["passed"]) for item in checks)
    metrics = {
        "analysis_version": VERSION,
        "review_claim": cfg["review_claim"],
        "query_rows": len(rows),
        "primary_familywise_rejections": primary_rejections,
        "primary_hypotheses": primary_total,
        "week24_missing": missing,
        "week24_randomized": randomized,
        "week24_missing_rate": missing_rate,
        "reference_based_mcse_passed": int(rbmi["mcse_pass"].sum()),
        "reference_based_rows": len(rbmi),
        "fixed_delta_context_rows": len(fixed),
        "planned_actual_treatment_mismatches": mismatch_count,
        "safety_response_rows": len(safety),
        "retention_response_rows": len(retention),
        "required_checks": len(checks),
        "required_checks_passed": sum(bool(item["passed"]) for item in checks),
        "all_passed": all_passed,
    }
    return rows, checks, metrics


def write_statistical_review_query_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    rows, checks, metrics = assess_statistical_review_queries(root)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(outputs / "statistical_review_queries.csv", index=False)
    pd.DataFrame(checks).to_csv(outputs / "statistical_review_query_checks.csv", index=False)
    (outputs / "statistical_review_query_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    cfg = _load_json(root / "spec" / "statistical_review_queries_v0_22.json")
    lines = [
        "# Statistical review query and decision-provenance pack",
        "",
        f"Review-response gate: **{'PASS' if metrics['all_passed'] else 'FAIL'}**",
        f"Controlled claim: `{metrics['review_claim']}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['query_id']} — {row['risk_area']}",
                "",
                f"**Reviewer question:** {row['reviewer_question']}",
                "",
                f"**Response:** {row['response']}",
                "",
                f"**Decision status:** `{row['decision_status']}`",
                "",
                f"**Evidence:** `{row['evidence_sources']}`",
                "",
            ]
        )
    lines.extend(["## Evidence boundary", "", str(cfg["evidence_boundary"]), ""])
    (outputs / "statistical_review_query_response.md").write_text("\n".join(lines), encoding="utf-8")

    if not metrics["all_passed"]:
        raise ValueError(
            "statistical review query gate failed; inspect outputs/statistical_review_query_checks.csv"
        )
    return metrics

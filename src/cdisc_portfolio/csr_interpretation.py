from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.21.0"
INTERPRETATION_CLAIM = "PORTFOLIO_STATISTICAL_INTERPRETATION_READY"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError("boolean field contains values other than true/false")
    return mapped.astype(bool)


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "required": True, "detail": detail})


def _validate_configuration(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError("CSR interpretation config must be version 0.21.0")
    if cfg.get("interpretation_claim") != INTERPRETATION_CLAIM:
        raise ValueError("interpretation claim must remain portfolio-scoped")
    comparisons = cfg.get("primary_comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 2 or len(set(comparisons)) != 2:
        raise ValueError("primary_comparisons must contain exactly two unique comparisons")
    strategies = cfg.get("reference_based_strategies")
    if not isinstance(strategies, list) or not strategies or len(strategies) != len(set(strategies)):
        raise ValueError("reference_based_strategies must be a non-empty unique list")
    required_inputs = cfg.get("required_inputs")
    if not isinstance(required_inputs, list) or not required_inputs or len(required_inputs) != len(set(required_inputs)):
        raise ValueError("required_inputs must be a non-empty unique list")
    tolerance = float(cfg.get("primary_estimate_tolerance", -1.0))
    if tolerance < 0:
        raise ValueError("primary_estimate_tolerance must be non-negative")
    rules = cfg.get("rules", {})
    required_rules = {
        "efficacy_success_requires_familywise_rejection",
        "sensitivity_is_supportive_not_confirmatory",
        "safety_is_descriptive",
        "retention_is_exploratory",
        "retention_hr_above_one_means_higher_discontinuation_hazard",
    }
    if set(rules) != required_rules or not all(bool(rules[key]) for key in required_rules):
        raise ValueError("all controlled CSR interpretation rules must remain enabled")


def assess_csr_interpretation(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "csr_interpretation_v0_21.json")
    _validate_configuration(cfg)
    outputs = root / "outputs"
    checks: list[dict[str, Any]] = []

    missing_inputs = [item for item in cfg["required_inputs"] if not (root / item).exists()]
    _check(
        checks,
        "all controlled interpretation inputs exist",
        not missing_inputs,
        "missing=" + (",".join(missing_inputs) if missing_inputs else "0"),
    )
    if missing_inputs:
        return [], checks, {
            "analysis_version": VERSION,
            "interpretation_claim": cfg["interpretation_claim"],
            "all_passed": False,
            "missing_required_inputs": len(missing_inputs),
        }

    closure = _load_json(outputs / "analysis_closure_metrics.json")
    closure_ok = bool(closure.get("all_passed")) and closure.get("closure_claim") == cfg["required_closure_claim"]
    _check(
        checks,
        "v0.20 evidence closure is complete before interpretation",
        closure_ok,
        f"claim={closure.get('closure_claim')}; all_passed={closure.get('all_passed')}",
    )

    mmrm = pd.read_csv(outputs / "mmrm_treatment_contrasts.csv")
    multiplicity = pd.read_csv(outputs / "table23_actot_multiplicity.csv")
    rbmi = pd.read_csv(outputs / "table22_rbmi_reference_based.csv")
    safety = pd.read_csv(outputs / "table7_teae_risk_difference.csv")
    retention = pd.read_csv(outputs / "table25_retention_pairwise.csv")

    _require_columns(
        mmrm,
        {"contrast", "AVISIT", "estimate", "SE", "lower.CL", "upper.CL", "p.value", "covariance"},
        "MMRM contrasts",
    )
    _require_columns(
        multiplicity,
        {
            "family_id",
            "contrast",
            "visit",
            "estimate",
            "raw_p_value",
            "adjusted_p_value",
            "reject_familywise",
            "family_alpha",
        },
        "multiplicity table",
    )
    _require_columns(
        rbmi,
        {
            "comparison",
            "strategy_id",
            "estimate_active_minus_placebo",
            "ci95_lower",
            "ci95_upper",
            "p_value",
            "mcse_pass",
        },
        "reference-based MI table",
    )
    _require_columns(
        safety,
        {"comparison", "risk_difference", "ci95_lower", "ci95_upper", "fisher_p"},
        "TEAE risk-difference table",
    )
    _require_columns(
        retention,
        {"comparison", "hazard_ratio", "ci95_lower", "ci95_upper", "cox_p_value", "interpretation"},
        "retention table",
    )

    expected = list(cfg["primary_comparisons"])
    expected_set = set(expected)
    primary = multiplicity.loc[
        multiplicity["family_id"].astype(str).eq(str(cfg["primary_family_id"]))
        & multiplicity["visit"].astype(str).eq(str(cfg["primary_visit"]))
    ].copy()
    primary["reject_familywise"] = _bool_series(primary["reject_familywise"])
    _check(
        checks,
        "primary multiplicity family contains exactly the controlled comparisons",
        len(primary) == len(expected) and set(primary["contrast"].astype(str)) == expected_set,
        f"rows={len(primary)}; comparisons={sorted(primary['contrast'].astype(str).tolist())}",
    )
    _check(
        checks,
        "primary family alpha is unique and valid",
        primary["family_alpha"].nunique() == 1
        and len(primary) > 0
        and 0 < float(primary["family_alpha"].iloc[0]) < 1,
        "alpha=" + (str(primary["family_alpha"].iloc[0]) if len(primary) else "NA"),
    )

    mmrm_primary = mmrm.loc[
        mmrm["AVISIT"].astype(str).eq(str(cfg["primary_visit"]))
        & mmrm["contrast"].astype(str).isin(expected_set)
    ].copy()
    _check(
        checks,
        "MMRM primary rows contain exactly the controlled comparisons",
        len(mmrm_primary) == len(expected) and set(mmrm_primary["contrast"].astype(str)) == expected_set,
        f"rows={len(mmrm_primary)}",
    )

    merged_primary = primary.merge(
        mmrm_primary[["contrast", "estimate", "SE", "lower.CL", "upper.CL", "p.value", "covariance"]],
        on="contrast",
        suffixes=("_mult", "_mmrm"),
        how="left",
    )
    if len(merged_primary):
        estimate_diff = (merged_primary["estimate_mult"] - merged_primary["estimate_mmrm"]).abs()
        raw_p_diff = (merged_primary["raw_p_value"] - merged_primary["p.value"]).abs()
        max_estimate_diff = float(estimate_diff.max())
        max_raw_p_diff = float(raw_p_diff.max())
    else:
        max_estimate_diff = float("inf")
        max_raw_p_diff = float("inf")
    tolerance = float(cfg["primary_estimate_tolerance"])
    _check(
        checks,
        "multiplicity decision rows reconcile to primary MMRM estimates",
        max_estimate_diff <= tolerance and max_raw_p_diff <= tolerance,
        f"max_estimate_diff={max_estimate_diff:.12g}; max_raw_p_diff={max_raw_p_diff:.12g}; tolerance={tolerance}",
    )

    required_strategies = set(str(value) for value in cfg["reference_based_strategies"])
    rbmi["mcse_pass"] = _bool_series(rbmi["mcse_pass"])
    sensitivity_ok = True
    sensitivity_details: list[str] = []
    for comparison in expected:
        subset = rbmi.loc[rbmi["comparison"].astype(str).eq(comparison)]
        observed_strategies = set(subset["strategy_id"].astype(str))
        exact_strategies = len(subset) == len(required_strategies) and observed_strategies == required_strategies
        mcse_ok = exact_strategies and bool(subset["mcse_pass"].all())
        sensitivity_ok = sensitivity_ok and mcse_ok
        sensitivity_details.append(
            f"{comparison}:strategies={sorted(observed_strategies)},mcse={int(subset['mcse_pass'].sum())}/{len(subset)}"
        )
    _check(
        checks,
        "reference-based sensitivity strategies and MCSE gates are complete",
        sensitivity_ok,
        "; ".join(sensitivity_details),
    )

    _check(
        checks,
        "safety comparison set matches the controlled primary comparisons",
        len(safety) == len(expected) and set(safety["comparison"].astype(str)) == expected_set,
        f"rows={len(safety)}",
    )
    _check(
        checks,
        "retention comparison set matches the controlled primary comparisons",
        len(retention) == len(expected) and set(retention["comparison"].astype(str)) == expected_set,
        f"rows={len(retention)}",
    )

    retention_source_ok = True
    for row in retention.itertuples(index=False):
        text = str(row.interpretation).lower()
        if float(row.hazard_ratio) > 1:
            retention_source_ok = retention_source_ok and "higher study-discontinuation hazard" in text
        elif float(row.hazard_ratio) < 1:
            retention_source_ok = retention_source_ok and "lower study-discontinuation hazard" in text
        retention_source_ok = retention_source_ok and "exploratory" in text
    _check(
        checks,
        "retention source interpretation preserves hazard direction and exploratory status",
        retention_source_ok,
        f"rows={len(retention)}",
    )

    rows: list[dict[str, Any]] = []
    for comparison in expected:
        p = primary.loc[primary["contrast"].astype(str).eq(comparison)].iloc[0]
        m = mmrm_primary.loc[mmrm_primary["contrast"].astype(str).eq(comparison)].iloc[0]
        rejected = bool(p["reject_familywise"])
        decision = "FAMILYWISE_REJECTED" if rejected else "NO_FAMILYWISE_REJECTION"
        interpretation = (
            "The controlled family-wise hypothesis is rejected; this is the primary multiplicity decision for the portfolio analysis."
            if rejected
            else "The controlled family-wise hypothesis is not rejected; no confirmatory efficacy success claim is made."
        )
        rows.append(
            {
                "section": "PRIMARY_EFFICACY",
                "analysis_role": "CONFIRMATORY_DECISION",
                "comparison": comparison,
                "estimate": float(m["estimate"]),
                "ci95_lower": float(m["lower.CL"]),
                "ci95_upper": float(m["upper.CL"]),
                "p_value": float(m["p.value"]),
                "adjusted_p_value": float(p["adjusted_p_value"]),
                "decision": decision,
                "controlled_interpretation": interpretation,
                "evidence_source": "outputs/table23_actot_multiplicity.csv",
            }
        )

        s = rbmi.loc[rbmi["comparison"].astype(str).eq(comparison)].copy()
        estimates = s["estimate_active_minus_placebo"].astype(float)
        sign_state = "SAME_SIGN" if (estimates.gt(0).all() or estimates.lt(0).all()) else "SIGN_CHANGES"
        rows.append(
            {
                "section": "MISSING_DATA_SENSITIVITY",
                "analysis_role": "SUPPORTIVE_SENSITIVITY",
                "comparison": comparison,
                "estimate": float(estimates.min()),
                "ci95_lower": float(s["ci95_lower"].astype(float).min()),
                "ci95_upper": float(s["ci95_upper"].astype(float).max()),
                "p_value": float(s["p_value"].astype(float).max()),
                "adjusted_p_value": float("nan"),
                "decision": f"{sign_state}; {len(s)}/{len(required_strategies)} STRATEGIES; MCSE_PASS",
                "controlled_interpretation": "Reference-based MI is supportive sensitivity evidence only and does not replace the controlled primary multiplicity decision.",
                "evidence_source": "outputs/table22_rbmi_reference_based.csv",
            }
        )

        a = safety.loc[safety["comparison"].astype(str).eq(comparison)].iloc[0]
        rd = float(a["risk_difference"])
        direction = "higher" if rd > 0 else "lower" if rd < 0 else "equal"
        rows.append(
            {
                "section": "SAFETY",
                "analysis_role": "DESCRIPTIVE_SAFETY",
                "comparison": comparison,
                "estimate": rd,
                "ci95_lower": float(a["ci95_lower"]),
                "ci95_upper": float(a["ci95_upper"]),
                "p_value": float(a["fisher_p"]),
                "adjusted_p_value": float("nan"),
                "decision": "DESCRIPTIVE_ONLY",
                "controlled_interpretation": f"Observed TEAE risk is {direction} than placebo by risk difference; safety results are descriptive in this portfolio pack.",
                "evidence_source": "outputs/table7_teae_risk_difference.csv",
            }
        )

        r = retention.loc[retention["comparison"].astype(str).eq(comparison)].iloc[0]
        hr = float(r["hazard_ratio"])
        hazard_direction = "higher" if hr > 1 else "lower" if hr < 1 else "equal"
        rows.append(
            {
                "section": "RETENTION",
                "analysis_role": "EXPLORATORY_RETENTION",
                "comparison": comparison,
                "estimate": hr,
                "ci95_lower": float(r["ci95_lower"]),
                "ci95_upper": float(r["ci95_upper"]),
                "p_value": float(r["cox_p_value"]),
                "adjusted_p_value": float("nan"),
                "decision": "EXPLORATORY_ONLY",
                "controlled_interpretation": f"HR {hr:.3f} indicates a {hazard_direction} study-discontinuation hazard than placebo; this analysis is exploratory and is not an efficacy conclusion.",
                "evidence_source": "outputs/table25_retention_pairwise.csv",
            }
        )

    interpretation_text = "\n".join(str(row["controlled_interpretation"]) for row in rows).lower()
    prohibited = [
        fragment for fragment in cfg.get("prohibited_claim_fragments", [])
        if str(fragment).lower() in interpretation_text
    ]
    _check(
        checks,
        "generated interpretation contains no prohibited overclaim fragments",
        not prohibited,
        "matched=" + (",".join(prohibited) if prohibited else "0"),
    )

    required_checks_passed = sum(bool(item["passed"]) for item in checks)
    all_passed = required_checks_passed == len(checks)
    primary_rejections = int(primary["reject_familywise"].sum()) if len(primary) else 0
    metrics = {
        "analysis_version": VERSION,
        "interpretation_claim": cfg["interpretation_claim"],
        "primary_family_id": cfg["primary_family_id"],
        "primary_hypotheses": len(primary),
        "primary_familywise_rejections": primary_rejections,
        "reference_based_rows": len(rbmi),
        "reference_based_mcse_passed": int(rbmi["mcse_pass"].sum()),
        "safety_comparisons": len(safety),
        "retention_comparisons": len(retention),
        "conclusion_rows": len(rows),
        "required_checks": len(checks),
        "required_checks_passed": required_checks_passed,
        "max_primary_estimate_reconciliation_diff": max_estimate_diff,
        "max_primary_raw_p_reconciliation_diff": max_raw_p_diff,
        "all_passed": all_passed,
    }
    return rows, checks, metrics


def write_csr_interpretation_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    rows, checks, metrics = assess_csr_interpretation(root)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(outputs / "csr_conclusion_matrix.csv", index=False)
    pd.DataFrame(checks).to_csv(outputs / "csr_interpretation_checks.csv", index=False)
    (outputs / "csr_interpretation_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    efficacy = [row for row in rows if row["section"] == "PRIMARY_EFFICACY"]
    sensitivity = [row for row in rows if row["section"] == "MISSING_DATA_SENSITIVITY"]
    safety = [row for row in rows if row["section"] == "SAFETY"]
    retention = [row for row in rows if row["section"] == "RETENTION"]
    cfg = _load_json(root / "spec" / "csr_interpretation_v0_21.json")

    lines = [
        "# CSR-style statistical interpretation pack",
        "",
        f"Interpretation gate: **{'PASS' if metrics['all_passed'] else 'FAIL'}**",
        f"Controlled claim: `{metrics['interpretation_claim']}`",
        "",
        "## Primary efficacy decision",
        "",
        f"The controlled Week 24 family has **{metrics['primary_familywise_rejections']}/{metrics['primary_hypotheses']} family-wise rejections**.",
    ]
    if metrics["primary_hypotheses"] and metrics["primary_familywise_rejections"] == 0:
        lines.append("No confirmatory efficacy success conclusion is supported by the controlled primary family.")
    elif metrics["primary_familywise_rejections"]:
        lines.append("Any efficacy conclusion is limited to the hypotheses that satisfy the controlled family-wise decision rule.")
    for row in efficacy:
        lines.append(
            f"- {row['comparison']}: estimate {row['estimate']:.4f}, 95% CI [{row['ci95_lower']:.4f}, {row['ci95_upper']:.4f}], adjusted p={row['adjusted_p_value']:.4f}; {row['decision']}."
        )

    lines.extend(["", "## Missing-data sensitivity", ""])
    for row in sensitivity:
        lines.append(f"- {row['comparison']}: {row['decision']}. {row['controlled_interpretation']}")

    lines.extend(["", "## Safety", ""])
    for row in safety:
        lines.append(
            f"- {row['comparison']}: TEAE risk difference {row['estimate']:.4f}, 95% CI [{row['ci95_lower']:.4f}, {row['ci95_upper']:.4f}]. {row['controlled_interpretation']}"
        )

    lines.extend(["", "## Exploratory retention", ""])
    for row in retention:
        lines.append(
            f"- {row['comparison']}: HR {row['estimate']:.4f}, 95% CI [{row['ci95_lower']:.4f}, {row['ci95_upper']:.4f}]. {row['controlled_interpretation']}"
        )

    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            str(cfg["evidence_boundary"]),
        ]
    )
    summary_text = "\n".join(lines) + "\n"
    prohibited = [
        fragment for fragment in cfg.get("prohibited_claim_fragments", [])
        if str(fragment).lower() in summary_text.lower()
    ]
    if prohibited:
        raise ValueError(f"CSR interpretation summary contains prohibited claim fragments: {prohibited}")
    (outputs / "csr_statistical_interpretation.md").write_text(summary_text, encoding="utf-8")

    if not metrics["all_passed"]:
        raise ValueError("CSR statistical interpretation gate failed; inspect outputs/csr_interpretation_checks.csv")
    return metrics

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.21.0"


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


def _validate_config(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError("CSR interpretation extension config must be version 0.21.0")
    comparisons = cfg.get("primary_comparisons")
    scenarios = cfg.get("fixed_delta_scenarios")
    if not isinstance(comparisons, list) or len(comparisons) != 2 or len(set(comparisons)) != 2:
        raise ValueError("primary_comparisons must contain exactly two unique comparisons")
    if not isinstance(scenarios, list) or not scenarios or len(scenarios) != len(set(scenarios)):
        raise ValueError("fixed_delta_scenarios must be a non-empty unique list")
    rules = cfg.get("rules", {})
    required = {
        "multiplicity_reject_flag_must_match_adjusted_and_local_p_rules",
        "fixed_delta_is_supportive_not_confirmatory",
        "direction_tipping_context_must_be_reported",
    }
    if set(rules) != required or not all(bool(rules[key]) for key in required):
        raise ValueError("all CSR interpretation extension rules must remain enabled")


def assess_csr_interpretation_extension(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "csr_interpretation_extension_v0_21.json")
    _validate_config(cfg)
    outputs = root / "outputs"
    checks: list[dict[str, Any]] = []

    missing_inputs = [item for item in cfg["required_inputs"] if not (root / item).exists()]
    _check(
        checks,
        "all fixed-delta interpretation inputs exist",
        not missing_inputs,
        "missing=" + (",".join(missing_inputs) if missing_inputs else "0"),
    )
    if missing_inputs:
        return [], checks, {
            "analysis_version": VERSION,
            "all_passed": False,
            "missing_required_inputs": len(missing_inputs),
        }

    multiplicity = pd.read_csv(outputs / "table23_actot_multiplicity.csv")
    tipping = pd.read_csv(outputs / "table19_actot_directional_tipping_points.csv")
    _require_columns(
        multiplicity,
        {
            "contrast",
            "estimate",
            "raw_p_value",
            "adjusted_p_value",
            "local_alpha",
            "family_alpha",
            "reject_familywise",
        },
        "multiplicity table",
    )
    _require_columns(
        tipping,
        {
            "scenario_id",
            "comparison",
            "primary_estimate",
            "direction_tipping_delta",
            "tipping_within_grid",
            "first_grid_delta_nonnegative",
            "significance_tipping_status",
        },
        "fixed-delta tipping table",
    )

    multiplicity["reject_familywise"] = _bool_series(multiplicity["reject_familywise"])
    expected_reject = (
        multiplicity["raw_p_value"].astype(float).le(multiplicity["local_alpha"].astype(float))
        & multiplicity["adjusted_p_value"].astype(float).le(multiplicity["family_alpha"].astype(float))
    )
    reject_consistent = bool((expected_reject == multiplicity["reject_familywise"]).all())
    _check(
        checks,
        "family-wise reject flags match local-alpha and adjusted-p decision rules",
        reject_consistent,
        f"consistent={int((expected_reject == multiplicity['reject_familywise']).sum())}/{len(multiplicity)}",
    )

    expected_comparisons = set(str(x) for x in cfg["primary_comparisons"])
    expected_scenarios = set(str(x) for x in cfg["fixed_delta_scenarios"])
    tipping["tipping_within_grid"] = _bool_series(tipping["tipping_within_grid"])
    scenario_ok = True
    estimate_ok = True
    details: list[str] = []
    tolerance = float(cfg["primary_estimate_tolerance"])
    for comparison in cfg["primary_comparisons"]:
        subset = tipping.loc[tipping["comparison"].astype(str).eq(comparison)].copy()
        observed_scenarios = set(subset["scenario_id"].astype(str))
        exact = len(subset) == len(expected_scenarios) and observed_scenarios == expected_scenarios
        scenario_ok = scenario_ok and exact
        primary_row = multiplicity.loc[multiplicity["contrast"].astype(str).eq(comparison)]
        if len(primary_row) != 1 or subset.empty:
            estimate_ok = False
            max_diff = float("inf")
        else:
            primary_estimate = float(primary_row.iloc[0]["estimate"])
            max_diff = float((subset["primary_estimate"].astype(float) - primary_estimate).abs().max())
            estimate_ok = estimate_ok and max_diff <= tolerance
        details.append(
            f"{comparison}:scenarios={sorted(observed_scenarios)},max_primary_diff={max_diff:.12g}"
        )
    _check(
        checks,
        "fixed-delta tipping table contains exactly the controlled scenarios per comparison",
        scenario_ok and set(tipping["comparison"].astype(str)) == expected_comparisons,
        "; ".join(details),
    )
    _check(
        checks,
        "fixed-delta primary estimates reconcile to the multiplicity table",
        estimate_ok,
        f"tolerance={tolerance}",
    )

    rows: list[dict[str, Any]] = []
    for comparison in cfg["primary_comparisons"]:
        subset = tipping.loc[tipping["comparison"].astype(str).eq(comparison)].copy()
        subset = subset.sort_values("direction_tipping_delta")
        earliest = subset.iloc[0]
        within = bool(subset["tipping_within_grid"].any())
        decision = "DIRECTION_TIPPING_WITHIN_GRID" if within else "NO_DIRECTION_TIPPING_WITHIN_GRID"
        scenario = str(earliest["scenario_id"])
        delta = float(earliest["direction_tipping_delta"])
        interpretation = (
            f"Across the controlled fixed-delta scenarios, the earliest analytic direction tipping threshold is delta={delta:.3f} ACTOT points under {scenario}; direction is assumption-sensitive. This is supportive sensitivity evidence only, not confirmatory inference."
            if within
            else "No direction tipping occurs within the controlled fixed-delta grid; this remains supportive sensitivity evidence only, not confirmatory inference."
        )
        rows.append(
            {
                "section": "FIXED_DELTA_SENSITIVITY",
                "analysis_role": "SUPPORTIVE_SENSITIVITY",
                "comparison": comparison,
                "estimate": delta,
                "ci95_lower": float("nan"),
                "ci95_upper": float("nan"),
                "p_value": float("nan"),
                "adjusted_p_value": float("nan"),
                "decision": decision,
                "controlled_interpretation": interpretation,
                "evidence_source": "outputs/table19_actot_directional_tipping_points.csv",
            }
        )

    all_passed = all(bool(item["passed"]) for item in checks)
    metrics = {
        "analysis_version": VERSION,
        "fixed_delta_rows": len(tipping),
        "fixed_delta_comparisons": len(set(tipping["comparison"].astype(str))),
        "fixed_delta_scenarios": len(set(tipping["scenario_id"].astype(str))),
        "fixed_delta_conclusion_rows": len(rows),
        "multiplicity_decisions_consistent": reject_consistent,
        "required_checks": len(checks),
        "required_checks_passed": sum(bool(item["passed"]) for item in checks),
        "all_passed": all_passed,
    }
    return rows, checks, metrics


def write_csr_interpretation_extension_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    rows, checks, metrics = assess_csr_interpretation_extension(root)
    outputs = root / "outputs"
    pd.DataFrame(checks).to_csv(outputs / "csr_interpretation_extension_checks.csv", index=False)
    (outputs / "csr_interpretation_extension_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pd.DataFrame(rows).to_csv(outputs / "csr_fixed_delta_context.csv", index=False)

    if not metrics["all_passed"]:
        raise ValueError(
            "CSR fixed-delta interpretation audit failed; inspect outputs/csr_interpretation_extension_checks.csv"
        )

    matrix_path = outputs / "csr_conclusion_matrix.csv"
    matrix = pd.read_csv(matrix_path)
    if "section" in matrix.columns:
        matrix = matrix.loc[~matrix["section"].astype(str).eq("FIXED_DELTA_SENSITIVITY")]
    matrix = pd.concat([matrix, pd.DataFrame(rows)], ignore_index=True)
    matrix.to_csv(matrix_path, index=False)

    summary_path = outputs / "csr_statistical_interpretation.md"
    summary = summary_path.read_text(encoding="utf-8")
    section_lines = ["## Fixed-delta directional sensitivity", ""]
    for row in rows:
        section_lines.append(f"- {row['comparison']}: {row['controlled_interpretation']}")
    fixed_section = "\n".join(section_lines) + "\n\n"
    marker = "## Safety\n"
    if marker not in summary:
        raise ValueError("CSR summary missing Safety section insertion marker")
    summary = summary.replace(marker, fixed_section + marker, 1)
    summary_path.write_text(summary, encoding="utf-8")
    return metrics

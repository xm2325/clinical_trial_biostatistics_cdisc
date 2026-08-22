from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

EXPECTED_ARMS = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
EXPECTED_CONTRASTS = {
    "Xanomeline Low Dose vs Placebo": "Xanomeline Low Dose",
    "Xanomeline High Dose vs Placebo": "Xanomeline High Dose",
}
EXPECTED_SCENARIOS = {
    "COMMON_WORSENING",
    "ACTIVE_ONLY_WORSENING",
    "DIVERGENT_WORSENING",
}


def _add(rows: list[dict[str, Any]], check: str, passed: bool, detail: str, area: str = "mnar_sensitivity", required: bool = True) -> None:
    rows.append(
        {
            "check": check,
            "passed": bool(passed),
            "required": bool(required),
            "detail": str(detail),
            "area": area,
        }
    )


def _require(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


def delta_values(spec: dict[str, Any]) -> np.ndarray:
    grid = spec.get("delta_grid", {})
    start = float(grid.get("start", np.nan))
    stop = float(grid.get("stop", np.nan))
    step = float(grid.get("step", np.nan))
    if not (np.isfinite(start) and np.isfinite(stop) and np.isfinite(step) and step > 0 and stop >= start):
        raise ValueError("delta_grid requires finite start/stop and positive step")
    n = int(math.floor((stop - start) / step + 1e-10)) + 1
    values = start + step * np.arange(n, dtype=float)
    if len(values) == 0 or abs(values[-1] - stop) > 1e-8:
        raise ValueError("delta_grid stop must be reachable exactly from start by step")
    return np.round(values, 12)


def validate_sensitivity_spec(spec: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    _add(rows, "MNAR sensitivity specification version is 0.12.0", spec.get("version") == "0.12.0", f"version={spec.get('version')}", "spec")
    _add(
        rows,
        "Sensitivity method is fixed-delta pattern-mixture mean shift",
        spec.get("method") == "fixed_delta_pattern_mixture_mean_shift",
        f"method={spec.get('method')}",
        "spec",
    )

    endpoint = spec.get("endpoint", {})
    endpoint_ok = (
        endpoint.get("parameter") == "ACTOT"
        and endpoint.get("visit") == "Week 24"
        and endpoint.get("measure") == "change_from_baseline"
        and endpoint.get("scale_direction") == "lower_better"
    )
    _add(rows, "Sensitivity endpoint matches ACTOT Week 24 change with lower values better", endpoint_ok, f"endpoint={endpoint}", "spec")

    ref = spec.get("reference_analysis", {})
    ref_ok = (
        ref.get("method") == "MMRM"
        and ref.get("covariance") == "Unstructured"
        and ref.get("missing_data_assumption") == "MAR"
    )
    _add(rows, "Reference analysis is the primary unstructured MAR MMRM", ref_ok, f"reference={ref}", "spec")

    grid_ok = True
    try:
        values = delta_values(spec)
        grid_ok = len(values) >= 2 and abs(float(values[0])) <= 1e-12 and float(values[-1]) > 0
        grid_detail = f"n={len(values)}; start={values[0]}; stop={values[-1]}"
    except Exception as exc:  # noqa: BLE001 - validator should report malformed specs
        grid_ok = False
        grid_detail = str(exc)
    _add(rows, "Delta grid starts at zero and contains a positive stress range", grid_ok, grid_detail, "spec")

    scenarios = spec.get("scenarios", [])
    ids = [str(x.get("id", "")) for x in scenarios if isinstance(x, dict)]
    unique_ok = len(ids) == len(set(ids)) and set(ids) == EXPECTED_SCENARIOS
    _add(rows, "Sensitivity scenarios are unique and complete", unique_ok, f"ids={ids}", "spec")
    multiplier_ok = bool(scenarios) and all(
        isinstance(x, dict)
        and isinstance(x.get("active_multiplier"), (int, float))
        and isinstance(x.get("placebo_multiplier"), (int, float))
        for x in scenarios
    )
    _add(rows, "Sensitivity scenario multipliers are numeric", multiplier_ok, f"scenarios={len(scenarios)}", "spec")

    tipping = spec.get("tipping_definition", {})
    _add(
        rows,
        "Primary tipping definition is effect-direction crossing zero",
        tipping.get("primary") == "effect_direction_crosses_zero",
        f"primary={tipping.get('primary')}",
        "spec",
    )
    return pd.DataFrame(rows)


def _week24_missingness(missingness: pd.DataFrame) -> pd.DataFrame:
    _require(missingness, ["TRT01A", "AVISIT", "target_n", "observed_n", "missing_n"], "missingness table")
    wk24 = missingness.loc[missingness["AVISIT"].astype(str).eq("Week 24")].copy()
    if wk24["TRT01A"].duplicated().any():
        raise ValueError("Week 24 missingness contains duplicate treatment rows")
    for col in ["target_n", "observed_n", "missing_n"]:
        wk24[col] = pd.to_numeric(wk24[col], errors="coerce")
    wk24["missing_prop"] = wk24["missing_n"] / wk24["target_n"]
    return wk24


def _primary_week24_contrasts(contrasts: pd.DataFrame) -> pd.DataFrame:
    _require(contrasts, ["contrast", "AVISIT", "estimate", "SE", "df", "p.value", "covariance"], "MMRM contrasts")
    d = contrasts.loc[
        contrasts["AVISIT"].astype(str).eq("Week 24")
        & contrasts["covariance"].astype(str).eq("Unstructured")
        & contrasts["contrast"].astype(str).isin(EXPECTED_CONTRASTS),
    ].copy()
    for col in ["estimate", "SE", "df", "p.value"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    return d


def run_delta_sensitivity(
    spec: dict[str, Any],
    contrasts: pd.DataFrame,
    missingness: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], str]:
    checks = [validate_sensitivity_spec(spec)]
    rows: list[dict[str, Any]] = []

    wk24_miss = _week24_missingness(missingness)
    missing_arms = sorted(set(EXPECTED_ARMS) - set(wk24_miss["TRT01A"].astype(str)))
    _add(rows, "Week 24 missingness contains all three treatment arms", not missing_arms and len(wk24_miss) == 3, f"rows={len(wk24_miss)}; missing={missing_arms}", "input")
    denom_ok = bool(
        len(wk24_miss) == 3
        and np.isfinite(wk24_miss[["target_n", "observed_n", "missing_n", "missing_prop"]].to_numpy(dtype=float)).all()
        and (wk24_miss["target_n"] > 0).all()
        and (wk24_miss["observed_n"] + wk24_miss["missing_n"] == wk24_miss["target_n"]).all()
        and wk24_miss["missing_prop"].between(0, 1).all()
    )
    _add(rows, "Week 24 missingness denominators and proportions reconcile", denom_ok, "observed + missing = target; proportions in [0,1]", "input")

    primary = _primary_week24_contrasts(contrasts)
    contrast_names = set(primary["contrast"].astype(str))
    _add(
        rows,
        "Primary Week 24 MMRM contains both active-versus-placebo contrasts",
        len(primary) == 2 and contrast_names == set(EXPECTED_CONTRASTS),
        f"contrasts={sorted(contrast_names)}",
        "input",
    )
    finite_primary = bool(len(primary) == 2 and np.isfinite(primary[["estimate", "SE", "df", "p.value"]].to_numpy(dtype=float)).all() and (primary["SE"] > 0).all() and (primary["df"] > 0).all())
    _add(rows, "Primary Week 24 MMRM estimates and inferential quantities are finite", finite_primary, f"rows={len(primary)}", "input")

    if not denom_ok or len(primary) != 2:
        qc = pd.concat(checks + [pd.DataFrame(rows)], ignore_index=True)
        metrics = {"analysis_version": "0.12.0", "required_checks": int(qc["required"].sum()), "required_passed": int((qc["required"] & qc["passed"]).sum()), "all_required_passed": False}
        return pd.DataFrame(), pd.DataFrame(), qc, metrics, "# MNAR sensitivity summary\n\nInput validation failed.\n"

    miss_prop = wk24_miss.set_index("TRT01A")["missing_prop"].astype(float).to_dict()
    deltas = delta_values(spec)
    alpha = float(spec.get("tipping_definition", {}).get("alpha", 0.05))
    scenarios = spec.get("scenarios", [])

    grid_rows: list[dict[str, Any]] = []
    tip_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        sid = str(scenario["id"])
        label = str(scenario.get("label", sid))
        a_mult = float(scenario["active_multiplier"])
        p_mult = float(scenario["placebo_multiplier"])
        for _, r in primary.iterrows():
            comparison = str(r["contrast"])
            active_arm = EXPECTED_CONTRASTS[comparison]
            primary_estimate = float(r["estimate"])
            se = float(r["SE"])
            df = float(r["df"])
            p0 = float(r["p.value"])
            coefficient = miss_prop[active_arm] * a_mult - miss_prop["Placebo"] * p_mult
            tcrit = float(stats.t.ppf(1.0 - alpha / 2.0, df))

            scenario_estimates: list[tuple[float, float]] = []
            for delta in deltas:
                shifted = primary_estimate + coefficient * float(delta)
                lower = shifted - tcrit * se
                upper = shifted + tcrit * se
                t_ratio = shifted / se
                p_value = float(2.0 * stats.t.sf(abs(t_ratio), df))
                direction = "favours_active" if shifted < -1e-12 else ("favours_placebo" if shifted > 1e-12 else "neutral")
                grid_rows.append(
                    {
                        "scenario_id": sid,
                        "scenario_label": label,
                        "comparison": comparison,
                        "active_arm": active_arm,
                        "delta": float(delta),
                        "delta_units": spec["delta_grid"].get("units", "ACTOT points"),
                        "placebo_missing_prop": miss_prop["Placebo"],
                        "active_missing_prop": miss_prop[active_arm],
                        "active_multiplier": a_mult,
                        "placebo_multiplier": p_mult,
                        "contrast_shift_per_delta": coefficient,
                        "primary_estimate": primary_estimate,
                        "shifted_estimate": shifted,
                        "SE_fixed_delta": se,
                        "df": df,
                        "lower_CL_fixed_delta": lower,
                        "upper_CL_fixed_delta": upper,
                        "p_value_fixed_delta": p_value,
                        "direction": direction,
                    }
                )
                scenario_estimates.append((float(delta), shifted))

            tipping_delta = -primary_estimate / coefficient if coefficient > 0 and primary_estimate < 0 else np.nan
            nonnegative = [d for d, est in scenario_estimates if est >= -1e-12]
            first_grid = min(nonnegative) if nonnegative else np.nan
            tip_rows.append(
                {
                    "scenario_id": sid,
                    "comparison": comparison,
                    "active_arm": active_arm,
                    "contrast_shift_per_delta": coefficient,
                    "primary_estimate": primary_estimate,
                    "primary_p_value": p0,
                    "direction_tipping_delta": tipping_delta,
                    "tipping_within_grid": bool(np.isfinite(tipping_delta) and tipping_delta <= float(deltas[-1]) + 1e-12),
                    "first_grid_delta_nonnegative": first_grid,
                    "significance_tipping_status": "not_applicable_primary_not_significant" if p0 >= alpha else "primary_significant_requires_separate_threshold",
                }
            )

    grid = pd.DataFrame(grid_rows)
    tipping = pd.DataFrame(tip_rows)

    expected_grid_rows = len(scenarios) * len(EXPECTED_CONTRASTS) * len(deltas)
    _add(rows, "Sensitivity grid has complete scenario-by-contrast-by-delta coverage", len(grid) == expected_grid_rows, f"rows={len(grid)}; expected={expected_grid_rows}", "grid")

    delta0 = grid.loc[np.isclose(grid["delta"], 0.0)].copy()
    delta0_error = float(np.max(np.abs(delta0["shifted_estimate"] - delta0["primary_estimate"]))) if len(delta0) else np.inf
    _add(rows, "Delta zero exactly reproduces the primary MMRM estimates", len(delta0) == len(scenarios) * 2 and delta0_error <= 1e-12, f"max_abs_error={delta0_error:.3g}", "grid")

    coeff_ok = bool(len(tipping) == len(scenarios) * 2 and np.isfinite(tipping["contrast_shift_per_delta"]).all() and (tipping["contrast_shift_per_delta"] > 0).all())
    _add(rows, "All configured worsening scenarios move active-versus-placebo contrasts toward worse active-arm values", coeff_ok, f"min_shift_per_delta={tipping['contrast_shift_per_delta'].min() if len(tipping) else np.nan}", "grid")

    monotonic_ok = True
    for _, block in grid.groupby(["scenario_id", "comparison"], sort=False):
        ordered = block.sort_values("delta")
        if (np.diff(ordered["shifted_estimate"].to_numpy(dtype=float)) < -1e-12).any():
            monotonic_ok = False
            break
    _add(rows, "Shifted estimates are monotone under increasing adverse delta", monotonic_ok, f"blocks={grid.groupby(['scenario_id', 'comparison']).ngroups}", "grid")

    tip_finite = bool(len(tipping) == len(scenarios) * 2 and np.isfinite(tipping["direction_tipping_delta"]).all() and (tipping["direction_tipping_delta"] > 0).all())
    _add(rows, "Directional tipping deltas are finite and positive", tip_finite, f"rows={len(tipping)}", "tipping")

    bracket_ok = True
    step = float(spec["delta_grid"]["step"])
    for r in tipping.itertuples(index=False):
        tip = float(r.direction_tipping_delta)
        first = float(r.first_grid_delta_nonnegative) if pd.notna(r.first_grid_delta_nonnegative) else np.nan
        if tip <= float(deltas[-1]) + 1e-12:
            if not np.isfinite(first) or first + 1e-12 < tip or first - step - 1e-12 > tip:
                bracket_ok = False
                break
    _add(rows, "Grid crossing brackets each analytic directional tipping point within one step", bracket_ok, f"grid_step={step}", "tipping")

    p0_ok = bool((primary["p.value"] >= alpha).all())
    status_ok = bool((tipping["significance_tipping_status"] == "not_applicable_primary_not_significant").all())
    _add(rows, "Loss-of-significance tipping is correctly marked not applicable for the current non-significant primary contrasts", p0_ok and status_ok, f"alpha={alpha}; primary_p={primary['p.value'].tolist()}", "interpretation")

    checks.append(pd.DataFrame(rows))
    qc = pd.concat(checks, ignore_index=True)
    required = qc.loc[qc["required"]].copy()
    all_passed = bool(len(required) and required["passed"].all())

    tip_metrics: dict[str, dict[str, float]] = {}
    for r in tipping.itertuples(index=False):
        tip_metrics.setdefault(str(r.scenario_id), {})[str(r.comparison)] = float(r.direction_tipping_delta)

    metrics = {
        "analysis_version": "0.12.0",
        "method": spec.get("method"),
        "delta_grid_rows": int(len(grid)),
        "tipping_rows": int(len(tipping)),
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_passed,
        "week24_missing_proportion": {arm: float(miss_prop[arm]) for arm in EXPECTED_ARMS},
        "direction_tipping_delta": tip_metrics,
    }

    summary_lines = [
        "# ACTOT fixed-delta MNAR sensitivity summary",
        "",
        "Portfolio sensitivity diagnostic only; not sponsor-approved MNAR multiple imputation or reference-based imputation.",
        "",
        f"Required checks: **{int(required['passed'].sum())}/{len(required)} passed**",
        f"Delta grid: **{deltas[0]:.1f} to {deltas[-1]:.1f} ACTOT points in {step:.1f}-point steps**",
        "",
        "Week 24 missingness used by the sensitivity calculation:",
    ]
    for arm in EXPECTED_ARMS:
        summary_lines.append(f"- {arm}: **{100.0 * miss_prop[arm]:.1f}%**")
    summary_lines.extend(["", "Directional tipping points (shift at which the active-minus-placebo point estimate reaches zero):", ""])
    for r in tipping.itertuples(index=False):
        summary_lines.append(f"- {r.scenario_id} / {r.comparison}: **delta={float(r.direction_tipping_delta):.3f}** ACTOT points.")
    summary_lines.extend(
        [
            "",
            "Because both primary Week 24 MMRM contrasts already have p>=0.05 at delta=0, loss-of-statistical-significance is not used as a tipping criterion. The sensitivity analysis instead reports the direction-of-effect crossing. Fixed-delta confidence intervals reuse the primary MMRM SE/df and do not add imputation-model uncertainty.",
        ]
    )
    return grid, tipping, qc, metrics, "\n".join(summary_lines) + "\n"

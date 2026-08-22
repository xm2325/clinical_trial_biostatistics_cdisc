from __future__ import annotations

from typing import Any, Mapping


REQUIRED_STRATEGIES = ["MAR", "JR", "CR", "CIR"]
REQUIRED_VISIT_DAYS = {"8": 56, "16": 112, "24": 168}


def validate_reference_based_mi_spec(spec: Mapping[str, Any]) -> None:
    """Validate the controlled v0.14 reference-based MI specification."""
    if spec.get("version") != "0.14.0":
        raise ValueError("reference-based MI specification version must be 0.14.0")
    if spec.get("base_imputation_spec") != "spec/mi_sensitivity.json":
        raise ValueError("v0.14 must retain the controlled v0.13 MI base specification")

    endpoint = spec.get("endpoint", {})
    if endpoint.get("parameter") != "ACTOT" or str(endpoint.get("analysis_visit")) != "24":
        raise ValueError("reference-based MI endpoint must be ACTOT at Week 24")
    if endpoint.get("direction") != "lower_is_better":
        raise ValueError("ACTOT direction must remain lower_is_better")

    ice = spec.get("intercurrent_event", {})
    expected_ice = {
        "event": "recorded_treatment_discontinuation",
        "subject_flag": "DCSFL",
        "subject_flag_value": "Y",
        "treatment_start_date": "TRTSDT",
        "treatment_end_date": "TRTEDT",
        "treatment_end_day_rule": "TRTEDT_minus_TRTSDT_plus_1",
        "first_affected_visit_rule": "first_nominal_visit_with_nominal_day_greater_than_treatment_end_day",
    }
    for key, value in expected_ice.items():
        if ice.get(key) != value:
            raise ValueError(f"intercurrent_event.{key} must be {value}")
    visit_days = {str(k): int(v) for k, v in ice.get("nominal_visit_days", {}).items()}
    if visit_days != REQUIRED_VISIT_DAYS:
        raise ValueError("nominal visit days must remain Week 8=56, Week 16=112, Week 24=168")
    if ice.get("require_zero_observed_post_ice_for_strategy_switch") is not True:
        raise ValueError("strategy switching requires a zero observed post-ICE data gate")

    rb = spec.get("reference_based_imputation", {})
    if rb.get("package") != "rbmi" or rb.get("required_version") != "1.6.1":
        raise ValueError("reference-based MI must use controlled rbmi 1.6.1")
    if rb.get("reference_arm") != "Placebo":
        raise ValueError("Placebo must remain the reference arm")
    if rb.get("initial_draw_strategy") != "JR":
        raise ValueError("initial draw strategy must be JR")
    if rb.get("strategies") != REQUIRED_STRATEGIES:
        raise ValueError("strategy set and order must be MAR, JR, CR, CIR")
    if rb.get("apply_non_mar_to") != "active_arm_discontinuers_with_affected_scheduled_visit":
        raise ValueError("non-MAR reference strategies must be restricted to active-arm discontinuers")
    if rb.get("reference_arm_discontinuers_strategy") != "MAR":
        raise ValueError("reference-arm discontinuers must remain MAR")
    if rb.get("reuse_parameter_draws_across_strategies") is not True:
        raise ValueError("parameter draws must be reused across reference-based strategies")
    if rb.get("reuse_ice_timing_across_strategies") is not True:
        raise ValueError("ICE timing must be held fixed across reference-based strategies")
    mcse = rb.get("max_mcse_estimate_to_se_ratio")
    if not isinstance(mcse, (int, float)) or not 0 < float(mcse) <= 0.075:
        raise ValueError("reference-based MI MCSE ratio must be in (0, 0.075]")

    analysis = spec.get("analysis", {})
    if analysis.get("method") != "Week 24 ANCOVA":
        raise ValueError("reference-based analysis must remain Week 24 ANCOVA")
    if analysis.get("covariates") != ["BASE"] or analysis.get("pooling") != "Rubin":
        raise ValueError("reference-based analysis must use baseline adjustment and Rubin pooling")
    if analysis.get("confidence_level") != 0.95:
        raise ValueError("confidence level must remain 0.95")
    if analysis.get("expected_strategy_rows_per_comparison") != 4:
        raise ValueError("exactly four strategy rows per comparison are required")

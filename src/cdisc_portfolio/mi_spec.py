from __future__ import annotations

from typing import Any, Mapping


REQUIRED_SCENARIOS = {"MAR", "ACTIVE_PLUS_1", "ACTIVE_PLUS_2", "DIVERGENT_1"}
EXPECTED_ACTIVE_ARMS = {"Xanomeline Low Dose", "Xanomeline High Dose"}


def validate_mi_spec(spec: Mapping[str, Any]) -> None:
    """Validate the controlled v0.13 subject-level MI specification.

    Raises ValueError for invalid or internally inconsistent settings so CI tests
    exercise the same validation logic as the repository specification.
    """
    if spec.get("version") != "0.13.0":
        raise ValueError("MI specification version must be 0.13.0")

    endpoint = spec.get("endpoint", {})
    if endpoint.get("parameter") != "ACTOT" or str(endpoint.get("analysis_visit")) != "24":
        raise ValueError("MI endpoint must be ACTOT at Week 24")
    if endpoint.get("direction") != "lower_is_better":
        raise ValueError("ACTOT direction must be lower_is_better")

    imp = spec.get("imputation", {})
    expected = {
        "package": "rbmi",
        "required_version": "1.6.1",
        "method": "approxbayes",
        "covariance": "us",
    }
    for key, value in expected.items():
        if imp.get(key) != value:
            raise ValueError(f"imputation.{key} must be {value}")
    if imp.get("same_covariance_across_groups") is not True or imp.get("reml") is not True:
        raise ValueError("controlled rbmi covariance settings were changed")

    n_imp = imp.get("n_imputations")
    if not isinstance(n_imp, int) or isinstance(n_imp, bool) or n_imp < 200:
        raise ValueError("n_imputations must be an integer >= 200")
    fail_threshold = imp.get("failure_threshold")
    if not isinstance(fail_threshold, (int, float)) or not 0 < float(fail_threshold) <= 0.10:
        raise ValueError("failure_threshold must be in (0, 0.10]")
    mcse_ratio = imp.get("max_mcse_estimate_to_se_ratio")
    if not isinstance(mcse_ratio, (int, float)) or not 0 < float(mcse_ratio) <= 0.075:
        raise ValueError("max_mcse_estimate_to_se_ratio must be in (0, 0.075]")
    if [str(x) for x in imp.get("visits", [])] != ["8", "16", "24"]:
        raise ValueError("MI longitudinal visits must be Week 8, 16 and 24")
    covariates = set(imp.get("imputation_model_covariates", []))
    if not {"BASE*VISIT", "TRT01A*VISIT"}.issubset(covariates):
        raise ValueError("MI model must retain baseline-by-visit and treatment-by-visit terms")

    analysis = spec.get("analysis", {})
    if analysis.get("pooling") != "Rubin" or analysis.get("covariates") != ["BASE"]:
        raise ValueError("Week 24 analysis must use Rubin pooling and baseline adjustment")
    comparisons = analysis.get("comparisons", [])
    if len(comparisons) != 2:
        raise ValueError("exactly two active-versus-placebo comparisons are required")
    ids = [c.get("id") for c in comparisons]
    seeds = [c.get("seed") for c in comparisons]
    active = {c.get("active_arm") for c in comparisons}
    if len(set(ids)) != 2 or active != EXPECTED_ACTIVE_ARMS:
        raise ValueError("pairwise comparison definitions are incomplete or duplicated")
    if any(c.get("reference_arm") != "Placebo" for c in comparisons):
        raise ValueError("Placebo must remain the reference arm")
    if len(set(seeds)) != 2 or any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in seeds):
        raise ValueError("comparison seeds must be unique positive integers")

    scenarios = spec.get("scenarios", [])
    by_id = {x.get("id"): x for x in scenarios}
    if len(by_id) != len(scenarios) or set(by_id) != REQUIRED_SCENARIOS:
        raise ValueError("MI scenario set must contain four unique controlled scenarios")
    expected_deltas = {
        "MAR": (0.0, 0.0),
        "ACTIVE_PLUS_1": (1.0, 0.0),
        "ACTIVE_PLUS_2": (2.0, 0.0),
        "DIVERGENT_1": (1.0, -1.0),
    }
    for scenario_id, (active_delta, placebo_delta) in expected_deltas.items():
        scenario = by_id[scenario_id]
        if float(scenario.get("active_delta")) != active_delta or float(scenario.get("placebo_delta")) != placebo_delta:
            raise ValueError(f"controlled delta values changed for {scenario_id}")

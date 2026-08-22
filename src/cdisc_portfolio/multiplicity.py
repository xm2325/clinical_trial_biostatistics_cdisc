from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_METHOD = "Bonferroni"
REQUIRED_FAMILY_ALPHA = 0.05
REQUIRED_COMPARISON_COUNT = 2
REQUIRED_LOCAL_ALPHA = 0.025
REQUIRED_VISIT = "Week 24"
REQUIRED_COVARIANCE = "Unstructured"
REQUIRED_HYPOTHESES = [
    ("H_LOW", "Xanomeline Low Dose vs Placebo"),
    ("H_HIGH", "Xanomeline High Dose vs Placebo"),
]
REQUIRED_SOURCE_COLUMNS = {
    "contrast",
    "AVISIT",
    "estimate",
    "SE",
    "df",
    "lower.CL",
    "upper.CL",
    "p.value",
    "covariance",
}


@dataclass(frozen=True)
class MultiplicityResult:
    decisions: pd.DataFrame
    qc: pd.DataFrame


def validate_multiplicity_spec(spec: dict[str, Any], planning_spec: dict[str, Any] | None = None) -> None:
    """Validate the controlled v0.15 primary multiplicity specification."""
    if spec.get("version") != "0.15.0":
        raise ValueError("multiplicity specification version must be 0.15.0")
    if spec.get("planning_spec") != "spec/protocol_design.json":
        raise ValueError("v0.15 must align to spec/protocol_design.json")
    if spec.get("source_output") != "outputs/mmrm_treatment_contrasts.csv":
        raise ValueError("multiplicity source output must remain the primary MMRM contrast table")

    family = spec.get("family", {})
    if family.get("id") != "ACTOT_W24_ACTIVE_VS_PLACEBO":
        raise ValueError("family id must remain ACTOT_W24_ACTIVE_VS_PLACEBO")
    if family.get("endpoint") != "ACTOT change from baseline":
        raise ValueError("multiplicity endpoint must remain ACTOT change from baseline")
    if family.get("visit") != REQUIRED_VISIT:
        raise ValueError("multiplicity visit must remain Week 24")
    if family.get("covariance") != REQUIRED_COVARIANCE:
        raise ValueError("multiplicity source covariance must remain Unstructured")
    if family.get("method") != REQUIRED_METHOD:
        raise ValueError("multiplicity method must remain Bonferroni")
    if float(family.get("family_alpha", -1)) != REQUIRED_FAMILY_ALPHA:
        raise ValueError("family alpha must remain 0.05")
    if family.get("two_sided") is not True:
        raise ValueError("multiplicity family must remain two-sided")

    hypotheses = family.get("hypotheses")
    if not isinstance(hypotheses, list):
        raise ValueError("multiplicity hypotheses must be a list")
    observed = [(str(x.get("id")), str(x.get("contrast"))) for x in hypotheses if isinstance(x, dict)]
    if observed != REQUIRED_HYPOTHESES:
        raise ValueError("hypothesis set and order must remain Low Dose then High Dose versus Placebo")

    rule = spec.get("decision_rule", {})
    if int(rule.get("comparison_count", -1)) != REQUIRED_COMPARISON_COUNT:
        raise ValueError("comparison count must remain 2")
    if float(rule.get("local_alpha", -1)) != REQUIRED_LOCAL_ALPHA:
        raise ValueError("Bonferroni local alpha must remain 0.025")
    if rule.get("adjusted_p_formula") != "min(raw_p_value * comparison_count, 1)":
        raise ValueError("adjusted p-value formula must remain controlled Bonferroni")
    if rule.get("reject_rule") != "adjusted_p_value <= family_alpha":
        raise ValueError("family-wise rejection rule must remain adjusted_p_value <= family_alpha")

    if planning_spec is not None:
        planning_mult = planning_spec.get("multiplicity", {})
        if planning_mult.get("method") != REQUIRED_METHOD:
            raise ValueError("planning multiplicity method is not aligned with v0.15")
        if float(planning_mult.get("family_alpha", -1)) != REQUIRED_FAMILY_ALPHA:
            raise ValueError("planning family alpha is not aligned with v0.15")
        if int(planning_mult.get("active_vs_control_comparisons", -1)) != REQUIRED_COMPARISON_COUNT:
            raise ValueError("planning comparison count is not aligned with v0.15")


def evaluate_primary_multiplicity(
    spec: dict[str, Any],
    planning_spec: dict[str, Any],
    contrasts: pd.DataFrame,
) -> MultiplicityResult:
    """Apply the planned Bonferroni family to primary Week 24 MMRM contrasts."""
    validate_multiplicity_spec(spec, planning_spec)

    missing = sorted(REQUIRED_SOURCE_COLUMNS - set(contrasts.columns))
    if missing:
        raise ValueError(f"MMRM contrast input missing columns: {missing}")

    family = spec["family"]
    rule = spec["decision_rule"]
    hypotheses = family["hypotheses"]

    source = contrasts.copy()
    source["AVISIT"] = source["AVISIT"].astype(str)
    source["contrast"] = source["contrast"].astype(str)
    source["covariance"] = source["covariance"].astype(str)
    primary = source.loc[
        (source["AVISIT"] == family["visit"])
        & (source["covariance"] == family["covariance"])
        & source["contrast"].isin([h["contrast"] for h in hypotheses])
    ].copy()

    qc_rows: list[dict[str, Any]] = []

    def add_check(check: str, passed: bool, detail: str, required: bool = True) -> None:
        qc_rows.append(
            {
                "check": check,
                "passed": bool(passed),
                "required": bool(required),
                "detail": str(detail),
            }
        )

    add_check(
        "Planning multiplicity method matches analysis decision method",
        planning_spec["multiplicity"]["method"] == family["method"],
        f"planning={planning_spec['multiplicity']['method']}; analysis={family['method']}",
    )
    add_check(
        "Planning family alpha matches analysis family alpha",
        abs(float(planning_spec["multiplicity"]["family_alpha"]) - float(family["family_alpha"])) <= 1e-12,
        f"planning={planning_spec['multiplicity']['family_alpha']}; analysis={family['family_alpha']}",
    )
    add_check(
        "Planning comparison count matches analysis family",
        int(planning_spec["multiplicity"]["active_vs_control_comparisons"]) == int(rule["comparison_count"]),
        f"planning={planning_spec['multiplicity']['active_vs_control_comparisons']}; analysis={rule['comparison_count']}",
    )
    add_check(
        "Primary multiplicity input has exactly two Week 24 unstructured contrasts",
        len(primary) == REQUIRED_COMPARISON_COUNT,
        f"rows={len(primary)}",
    )
    add_check(
        "Primary multiplicity contrast labels are unique",
        primary["contrast"].nunique() == len(primary),
        f"unique={primary['contrast'].nunique()}; rows={len(primary)}",
    )

    observed_labels = set(primary["contrast"])
    expected_labels = {h["contrast"] for h in hypotheses}
    add_check(
        "Primary multiplicity input contains the exact controlled hypothesis set",
        observed_labels == expected_labels,
        f"observed={sorted(observed_labels)}",
    )

    numeric_cols = ["estimate", "SE", "df", "lower.CL", "upper.CL", "p.value"]
    for col in numeric_cols:
        primary[col] = pd.to_numeric(primary[col], errors="coerce")
    finite = bool(np.isfinite(primary[numeric_cols].to_numpy(dtype=float)).all()) if len(primary) else False
    add_check(
        "Primary multiplicity estimates and inference are finite",
        finite,
        f"rows={len(primary)}",
    )
    p_in_range = bool(primary["p.value"].between(0.0, 1.0, inclusive="both").all()) if len(primary) else False
    add_check(
        "Primary multiplicity raw p-values are within [0,1]",
        p_in_range,
        f"raw_p={primary['p.value'].tolist()}",
    )

    local_alpha = float(rule["local_alpha"])
    family_alpha = float(family["family_alpha"])
    comparisons = int(rule["comparison_count"])
    add_check(
        "Bonferroni local alpha equals family alpha divided by comparison count",
        abs(local_alpha - family_alpha / comparisons) <= 1e-12,
        f"family_alpha={family_alpha}; comparisons={comparisons}; local_alpha={local_alpha}",
    )

    by_contrast = {str(row["contrast"]): row for _, row in primary.iterrows()}
    decision_rows: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        contrast = hypothesis["contrast"]
        if contrast not in by_contrast:
            continue
        row = by_contrast[contrast]
        raw_p = float(row["p.value"])
        adjusted_p = min(raw_p * comparisons, 1.0)
        reject = adjusted_p <= family_alpha
        decision_rows.append(
            {
                "family_id": family["id"],
                "hypothesis_id": hypothesis["id"],
                "contrast": contrast,
                "endpoint": family["endpoint"],
                "visit": family["visit"],
                "covariance": family["covariance"],
                "estimate": float(row["estimate"]),
                "SE": float(row["SE"]),
                "df": float(row["df"]),
                "raw_p_value": raw_p,
                "adjustment_method": family["method"],
                "family_alpha": family_alpha,
                "comparison_count": comparisons,
                "local_alpha": local_alpha,
                "adjusted_p_value": adjusted_p,
                "reject_familywise": bool(reject),
            }
        )

    decisions = pd.DataFrame(decision_rows)
    add_check(
        "Multiplicity decision table contains one row per controlled hypothesis",
        len(decisions) == comparisons,
        f"rows={len(decisions)}; expected={comparisons}",
    )

    if len(decisions) == comparisons:
        formula_ok = bool(
            np.allclose(
                decisions["adjusted_p_value"].to_numpy(dtype=float),
                np.minimum(decisions["raw_p_value"].to_numpy(dtype=float) * comparisons, 1.0),
                rtol=0.0,
                atol=1e-15,
            )
        )
        raw_rule = decisions["raw_p_value"].to_numpy(dtype=float) <= local_alpha
        adjusted_rule = decisions["adjusted_p_value"].to_numpy(dtype=float) <= family_alpha
        flags = decisions["reject_familywise"].to_numpy(dtype=bool)
        decision_ok = bool(np.array_equal(raw_rule, adjusted_rule) and np.array_equal(flags, adjusted_rule))
    else:
        formula_ok = False
        decision_ok = False

    add_check(
        "Adjusted p-values follow the controlled Bonferroni formula",
        formula_ok,
        f"comparison_count={comparisons}",
    )
    add_check(
        "Family-wise rejection flags agree with raw-alpha and adjusted-p rules",
        decision_ok,
        f"family_alpha={family_alpha}; local_alpha={local_alpha}",
    )

    qc = pd.DataFrame(qc_rows)
    return MultiplicityResult(decisions=decisions, qc=qc)

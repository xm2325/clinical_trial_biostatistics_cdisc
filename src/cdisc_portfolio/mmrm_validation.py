from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ValidationResult:
    comparison: pd.DataFrame
    qc: pd.DataFrame
    metrics: dict[str, Any]


def _qc_row(check: str, passed: bool, detail: str, required: bool = True) -> dict[str, Any]:
    return {
        "check": check,
        "passed": bool(passed),
        "required": bool(required),
        "detail": str(detail),
    }


def _require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def validate_mmrm_cross_package(
    primary: pd.DataFrame,
    independent: pd.DataFrame,
    spec: dict[str, Any],
) -> ValidationResult:
    if spec.get("version") != "0.16.0":
        raise ValueError("Cross-package validation spec version must be 0.16.0")

    target = spec.get("target", {})
    validation = spec.get("validation", {})
    visit = target.get("visit")
    primary_covariance = target.get("primary_covariance")
    independent_covariance = target.get("independent_covariance")
    hypotheses = list(target.get("hypotheses", []))

    if not visit or not primary_covariance or not independent_covariance or len(hypotheses) != 2:
        raise ValueError("Cross-package validation target is incomplete")
    if len(set(hypotheses)) != len(hypotheses):
        raise ValueError("Cross-package validation hypotheses must be unique")

    estimate_tol = float(validation.get("estimate_abs_tolerance", np.nan))
    se_tol = float(validation.get("se_abs_tolerance", np.nan))
    if not np.isfinite(estimate_tol) or estimate_tol <= 0:
        raise ValueError("estimate_abs_tolerance must be finite and > 0")
    if not np.isfinite(se_tol) or se_tol <= 0:
        raise ValueError("se_abs_tolerance must be finite and > 0")
    require_sign = bool(validation.get("require_sign_agreement", True))
    if bool(validation.get("compare_degrees_of_freedom", False)):
        raise ValueError("v0.16 cross-package validation must not compare degrees of freedom")
    if bool(validation.get("compare_p_values", False)):
        raise ValueError("v0.16 cross-package validation must not compare p-values")

    _require_columns(primary, ["contrast", "AVISIT", "estimate", "SE", "covariance"], "primary source")
    _require_columns(independent, ["contrast", "AVISIT", "estimate", "SE", "covariance", "method"], "independent source")

    p = primary[
        (primary["AVISIT"].astype(str) == visit)
        & (primary["covariance"].astype(str) == primary_covariance)
    ].copy()
    i = independent[
        (independent["AVISIT"].astype(str) == visit)
        & (independent["covariance"].astype(str) == independent_covariance)
    ].copy()

    p = p[p["contrast"].astype(str).isin(hypotheses)].copy()
    i = i[i["contrast"].astype(str).isin(hypotheses)].copy()
    p["estimate"] = pd.to_numeric(p["estimate"], errors="coerce")
    p["SE"] = pd.to_numeric(p["SE"], errors="coerce")
    i["estimate"] = pd.to_numeric(i["estimate"], errors="coerce")
    i["SE"] = pd.to_numeric(i["SE"], errors="coerce")

    qc_rows: list[dict[str, Any]] = []
    qc_rows.append(_qc_row("Primary target has exactly two controlled contrasts", len(p) == 2, f"rows={len(p)}"))
    qc_rows.append(_qc_row("Independent target has exactly two controlled contrasts", len(i) == 2, f"rows={len(i)}"))
    qc_rows.append(
        _qc_row(
            "Primary hypothesis set matches specification",
            set(p["contrast"].astype(str)) == set(hypotheses),
            ", ".join(sorted(p["contrast"].astype(str).tolist())),
        )
    )
    qc_rows.append(
        _qc_row(
            "Independent hypothesis set matches specification",
            set(i["contrast"].astype(str)) == set(hypotheses),
            ", ".join(sorted(i["contrast"].astype(str).tolist())),
        )
    )
    primary_finite = len(p) == 2 and np.isfinite(p[["estimate", "SE"]].to_numpy(dtype=float)).all()
    independent_finite = len(i) == 2 and np.isfinite(i[["estimate", "SE"]].to_numpy(dtype=float)).all()
    qc_rows.append(_qc_row("Primary estimates and SEs are finite", primary_finite, f"rows={len(p)}"))
    qc_rows.append(_qc_row("Independent estimates and SEs are finite", independent_finite, f"rows={len(i)}"))

    if len(p) == 2 and len(i) == 2:
        p2 = p[["contrast", "estimate", "SE"]].rename(
            columns={"estimate": "primary_estimate", "SE": "primary_SE"}
        )
        i2 = i[["contrast", "estimate", "SE", "method", "covariance"]].rename(
            columns={
                "estimate": "independent_estimate",
                "SE": "independent_SE",
                "method": "independent_method",
                "covariance": "independent_covariance",
            }
        )
        comparison = p2.merge(i2, on="contrast", how="outer", validate="one_to_one")
        order = {name: index for index, name in enumerate(hypotheses)}
        comparison["_order"] = comparison["contrast"].map(order)
        comparison = comparison.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    else:
        comparison = pd.DataFrame(
            columns=[
                "contrast",
                "primary_estimate",
                "primary_SE",
                "independent_estimate",
                "independent_SE",
                "independent_method",
                "independent_covariance",
            ]
        )

    if len(comparison) == 2:
        comparison["estimate_abs_difference"] = (
            comparison["primary_estimate"] - comparison["independent_estimate"]
        ).abs()
        comparison["se_abs_difference"] = (comparison["primary_SE"] - comparison["independent_SE"]).abs()
        comparison["estimate_tolerance"] = estimate_tol
        comparison["se_tolerance"] = se_tol
        comparison["estimate_pass"] = comparison["estimate_abs_difference"] <= estimate_tol
        comparison["se_pass"] = comparison["se_abs_difference"] <= se_tol
        comparison["sign_agreement"] = np.sign(comparison["primary_estimate"]) == np.sign(
            comparison["independent_estimate"]
        )
        comparison["cross_package_pass"] = comparison["estimate_pass"] & comparison["se_pass"]
        if require_sign:
            comparison["cross_package_pass"] &= comparison["sign_agreement"]

        for row in comparison.itertuples(index=False):
            qc_rows.append(
                _qc_row(
                    f"{row.contrast}: estimate agrees within tolerance",
                    bool(row.estimate_pass),
                    f"abs_difference={row.estimate_abs_difference:.12g}; tolerance={estimate_tol:.12g}",
                )
            )
            qc_rows.append(
                _qc_row(
                    f"{row.contrast}: SE agrees within tolerance",
                    bool(row.se_pass),
                    f"abs_difference={row.se_abs_difference:.12g}; tolerance={se_tol:.12g}",
                )
            )
            qc_rows.append(
                _qc_row(
                    f"{row.contrast}: treatment-effect sign agrees",
                    bool(row.sign_agreement) if require_sign else True,
                    f"primary={row.primary_estimate:.12g}; independent={row.independent_estimate:.12g}",
                )
            )
    else:
        for hypothesis in hypotheses:
            qc_rows.append(_qc_row(f"{hypothesis}: estimate agrees within tolerance", False, "comparison unavailable"))
            qc_rows.append(_qc_row(f"{hypothesis}: SE agrees within tolerance", False, "comparison unavailable"))
            qc_rows.append(_qc_row(f"{hypothesis}: treatment-effect sign agrees", False, "comparison unavailable"))

    qc = pd.DataFrame(qc_rows)
    required = qc[qc["required"]]
    all_required = len(required) > 0 and bool(required["passed"].all())
    max_estimate_diff = (
        float(comparison["estimate_abs_difference"].max()) if "estimate_abs_difference" in comparison else None
    )
    max_se_diff = float(comparison["se_abs_difference"].max()) if "se_abs_difference" in comparison else None

    metrics: dict[str, Any] = {
        "analysis_version": "0.16.0",
        "visit": visit,
        "hypotheses": hypotheses,
        "estimate_abs_tolerance": estimate_tol,
        "se_abs_tolerance": se_tol,
        "compare_degrees_of_freedom": False,
        "compare_p_values": False,
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_required,
        "max_estimate_abs_difference": max_estimate_diff,
        "max_se_abs_difference": max_se_diff,
    }
    return ValidationResult(comparison=comparison, qc=qc, metrics=metrics)

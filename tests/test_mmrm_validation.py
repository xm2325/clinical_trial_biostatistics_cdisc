import copy

import pandas as pd
import pytest

from cdisc_portfolio.mmrm_validation import validate_mmrm_cross_package


HYPOTHESES = [
    "Xanomeline Low Dose vs Placebo",
    "Xanomeline High Dose vs Placebo",
]


def _spec():
    return {
        "version": "0.16.0",
        "target": {
            "endpoint": "ACTOT change from baseline",
            "visit": "Week 24",
            "primary_covariance": "Unstructured",
            "independent_covariance": "Unstructured (corSymm + varIdent)",
            "hypotheses": HYPOTHESES,
        },
        "validation": {
            "estimate_abs_tolerance": 0.0005,
            "se_abs_tolerance": 0.0005,
            "require_sign_agreement": True,
            "compare_degrees_of_freedom": False,
            "compare_p_values": False,
        },
    }


def _primary():
    return pd.DataFrame(
        {
            "contrast": HYPOTHESES + HYPOTHESES,
            "AVISIT": ["Week 24", "Week 24", "Week 16", "Week 16"],
            "estimate": [-1.61310, -0.92710, -1.0, -0.5],
            "SE": [1.16780, 1.15120, 1.0, 1.0],
            "covariance": ["Unstructured", "Unstructured", "Unstructured", "Unstructured"],
        }
    )


def _independent():
    return pd.DataFrame(
        {
            "contrast": HYPOTHESES,
            "AVISIT": ["Week 24", "Week 24"],
            "estimate": [-1.61312, -0.92708],
            "SE": [1.16782, 1.15118],
            "method": ["nlme::gls", "nlme::gls"],
            "covariance": ["Unstructured (corSymm + varIdent)"] * 2,
        }
    )


def test_cross_package_validation_passes_equivalent_results():
    result = validate_mmrm_cross_package(_primary(), _independent(), _spec())
    assert result.metrics["all_required_passed"] is True
    assert result.metrics["required_checks"] == 12
    assert result.comparison["cross_package_pass"].tolist() == [True, True]


def test_cross_package_validation_rejects_estimate_drift():
    independent = _independent()
    independent.loc[0, "estimate"] = -1.60
    result = validate_mmrm_cross_package(_primary(), independent, _spec())
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert any("estimate agrees within tolerance" in check for check in failed)


def test_cross_package_validation_rejects_se_drift():
    independent = _independent()
    independent.loc[1, "SE"] = 1.16
    result = validate_mmrm_cross_package(_primary(), independent, _spec())
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert any("SE agrees within tolerance" in check for check in failed)


def test_cross_package_validation_rejects_sign_flip():
    independent = _independent()
    independent.loc[1, "estimate"] = 0.92708
    result = validate_mmrm_cross_package(_primary(), independent, _spec())
    assert result.metrics["all_required_passed"] is False
    assert not result.comparison.loc[1, "sign_agreement"]


def test_cross_package_validation_rejects_missing_hypothesis():
    result = validate_mmrm_cross_package(_primary(), _independent().iloc[:1].copy(), _spec())
    assert result.metrics["all_required_passed"] is False
    assert len(result.comparison) == 0


def test_cross_package_validation_rejects_df_comparison_scope():
    spec = copy.deepcopy(_spec())
    spec["validation"]["compare_degrees_of_freedom"] = True
    with pytest.raises(ValueError, match="must not compare degrees of freedom"):
        validate_mmrm_cross_package(_primary(), _independent(), spec)


def test_cross_package_validation_rejects_pvalue_comparison_scope():
    spec = copy.deepcopy(_spec())
    spec["validation"]["compare_p_values"] = True
    with pytest.raises(ValueError, match="must not compare p-values"):
        validate_mmrm_cross_package(_primary(), _independent(), spec)


def test_cross_package_validation_rejects_nonpositive_tolerance():
    spec = copy.deepcopy(_spec())
    spec["validation"]["se_abs_tolerance"] = 0
    with pytest.raises(ValueError, match="se_abs_tolerance"):
        validate_mmrm_cross_package(_primary(), _independent(), spec)

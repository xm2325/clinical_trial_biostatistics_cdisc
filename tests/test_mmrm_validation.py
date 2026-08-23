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
        "row_validation": {
            "key_columns": ["STUDYID", "USUBJID", "AVISIT"],
            "exact_columns": ["TRT01A"],
            "numeric_columns": ["QSSEQ", "AVAL", "BASE", "CHG"],
            "numeric_abs_tolerance": 1e-12,
        },
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


def _analysis():
    return pd.DataFrame(
        {
            "STUDYID": ["CDISCPILOT01", "CDISCPILOT01", "CDISCPILOT01"],
            "USUBJID": ["01", "01", "02"],
            "AVISIT": ["Week 8", "Week 24", "Week 24"],
            "TRT01A": ["Placebo", "Placebo", "Xanomeline Low Dose"],
            "QSSEQ": [2, 4, 4],
            "AVAL": [18.0, 16.0, 19.0],
            "BASE": [22.0, 22.0, 23.0],
            "CHG": [-4.0, -6.0, -4.0],
        }
    )


def _run(independent=None, primary_analysis=None, independent_analysis=None, spec=None):
    return validate_mmrm_cross_package(
        _primary(),
        _independent() if independent is None else independent,
        _analysis() if primary_analysis is None else primary_analysis,
        _analysis() if independent_analysis is None else independent_analysis,
        _spec() if spec is None else spec,
    )


def test_cross_package_validation_passes_equivalent_results_and_analysis_rows():
    independent_analysis = _analysis()
    independent_analysis["QSSEQ"] = independent_analysis["QSSEQ"].astype(float)
    result = _run(independent_analysis=independent_analysis)
    assert result.metrics["all_required_passed"] is True
    assert result.metrics["required_checks"] == 18
    assert result.metrics["analysis_key_sets_match"] is True
    assert result.metrics["analysis_exact_mismatch_rows"] == 0
    assert result.metrics["analysis_numeric_mismatch_rows"] == 0
    assert result.comparison["cross_package_pass"].tolist() == [True, True]


def test_cross_package_validation_rejects_analysis_key_drift():
    independent_analysis = _analysis().iloc[:-1].copy()
    result = _run(independent_analysis=independent_analysis)
    assert result.metrics["all_required_passed"] is False
    assert result.metrics["analysis_key_sets_match"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert "Primary and independent MMRM analysis key sets match" in failed


def test_cross_package_validation_rejects_analysis_treatment_drift():
    independent_analysis = _analysis()
    independent_analysis.loc[2, "TRT01A"] = "Xanomeline High Dose"
    result = _run(independent_analysis=independent_analysis)
    assert result.metrics["all_required_passed"] is False
    assert result.metrics["analysis_exact_mismatch_rows"] == 1


def test_cross_package_validation_rejects_analysis_numeric_drift():
    independent_analysis = _analysis()
    independent_analysis.loc[2, "CHG"] += 1e-5
    result = _run(independent_analysis=independent_analysis)
    assert result.metrics["all_required_passed"] is False
    assert result.metrics["analysis_numeric_mismatch_rows"] == 1
    assert result.metrics["max_analysis_numeric_abs_difference"] == pytest.approx(1e-5)


def test_cross_package_validation_rejects_estimate_drift():
    independent = _independent()
    independent.loc[0, "estimate"] = -1.60
    result = _run(independent=independent)
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert any("estimate agrees within tolerance" in check for check in failed)


def test_cross_package_validation_rejects_se_drift():
    independent = _independent()
    independent.loc[1, "SE"] = 1.16
    result = _run(independent=independent)
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert any("SE agrees within tolerance" in check for check in failed)


def test_cross_package_validation_rejects_sign_flip():
    independent = _independent()
    independent.loc[1, "estimate"] = 0.92708
    result = _run(independent=independent)
    assert result.metrics["all_required_passed"] is False
    assert not result.comparison.loc[1, "sign_agreement"]


def test_cross_package_validation_rejects_missing_hypothesis():
    result = _run(independent=_independent().iloc[:1].copy())
    assert result.metrics["all_required_passed"] is False
    assert len(result.comparison) == 0


def test_cross_package_validation_rejects_df_comparison_scope():
    spec = copy.deepcopy(_spec())
    spec["validation"]["compare_degrees_of_freedom"] = True
    with pytest.raises(ValueError, match="must not compare degrees of freedom"):
        _run(spec=spec)


def test_cross_package_validation_rejects_pvalue_comparison_scope():
    spec = copy.deepcopy(_spec())
    spec["validation"]["compare_p_values"] = True
    with pytest.raises(ValueError, match="must not compare p-values"):
        _run(spec=spec)


def test_cross_package_validation_rejects_nonpositive_effect_tolerance():
    spec = copy.deepcopy(_spec())
    spec["validation"]["se_abs_tolerance"] = 0
    with pytest.raises(ValueError, match="se_abs_tolerance"):
        _run(spec=spec)


def test_cross_package_validation_rejects_invalid_row_tolerance():
    spec = copy.deepcopy(_spec())
    spec["row_validation"]["numeric_abs_tolerance"] = -1
    with pytest.raises(ValueError, match="numeric_abs_tolerance"):
        _run(spec=spec)

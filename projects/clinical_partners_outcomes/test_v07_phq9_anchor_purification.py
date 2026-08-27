import numpy as np
import pandas as pd

from v06_phq9_psychometrics import gh_quadrature, pack_initial_from_data
from v07_phq9_anchor_purification import (
    design_structure_audit,
    pattern_log_likelihood_multi,
)


def test_multi_replacement_likelihood_accepts_multiple_free_items():
    x = np.array(
        [
            [0, 0, 0],
            [1, 1, 1],
            [2, 2, 2],
            [3, 3, 3],
        ],
        dtype=int,
    )
    weights = np.ones(len(x))
    raw = pack_initial_from_data(x, weights)
    theta, quad_weights = gh_quadrature(9)
    patterns = x.copy()
    pattern_weights = weights.copy()

    base = pattern_log_likelihood_multi(
        raw, patterns, pattern_weights, theta, quad_weights
    )
    blocks = raw.reshape(3, 4)
    replaced = pattern_log_likelihood_multi(
        raw,
        patterns,
        pattern_weights,
        theta,
        quad_weights,
        replacements={0: blocks[0].copy(), 2: blocks[2].copy()},
    )
    assert np.isfinite(base)
    assert np.isclose(base, replaced)


def test_group_specific_replacement_changes_likelihood_when_parameters_change():
    x = np.array(
        [
            [0, 0],
            [0, 1],
            [1, 1],
            [2, 2],
            [3, 3],
        ],
        dtype=int,
    )
    weights = np.ones(len(x))
    raw = pack_initial_from_data(x, weights)
    theta, quad_weights = gh_quadrature(9)
    base = pattern_log_likelihood_multi(
        raw, x, weights, theta, quad_weights
    )
    changed = raw.reshape(2, 4)[0].copy()
    changed[0] += 0.7
    alternative = pattern_log_likelihood_multi(
        raw,
        x,
        weights,
        theta,
        quad_weights,
        replacements={0: changed},
    )
    assert np.isfinite(alternative)
    assert not np.isclose(base, alternative)


def test_design_structure_audit_reports_masked_variance_units():
    cohort = pd.DataFrame(
        {
            "SEQN": [1, 2, 3, 4, 5, 6],
            "WTMEC2YR": [1.0, 2.0, 1.5, 2.5, 3.0, 1.0],
            "SDMVSTRA": [10, 10, 11, 11, 12, 12],
            "SDMVPSU": [1, 2, 1, 2, 1, 2],
        }
    )
    table, summary = design_structure_audit(cohort)
    assert summary["available"]
    assert summary["n_masked_strata_in_complete_case_domain"] == 3
    assert summary["n_masked_psu_in_complete_case_domain"] == 6
    assert summary["naive_design_df_psu_minus_strata"] == 3
    assert len(table) == 6


def test_design_structure_audit_has_explicit_boundary_when_fields_absent():
    cohort = pd.DataFrame({"SEQN": [1, 2], "WTMEC2YR": [1.0, 1.0]})
    table, summary = design_structure_audit(cohort)
    assert table.empty
    assert not summary["available"]

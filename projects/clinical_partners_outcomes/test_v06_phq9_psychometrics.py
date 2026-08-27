import numpy as np

from v06_phq9_psychometrics import (
    aggregate_patterns,
    bh_fdr,
    category_probabilities,
    item_information,
    unpack_item_block,
    weighted_cronbach_alpha,
)


def test_ordered_grm_threshold_parameterisation():
    raw = np.tile([0.0, -1.0, 0.0, 0.0], 9)
    discrimination, thresholds = unpack_item_block(raw, 9)
    assert discrimination.shape == (9,)
    assert thresholds.shape == (9, 3)
    assert np.all(discrimination > 0)
    assert np.all(thresholds[:, 0] < thresholds[:, 1])
    assert np.all(thresholds[:, 1] < thresholds[:, 2])


def test_category_probabilities_are_valid_and_ordered_model_changes_with_theta():
    theta = np.array([-2.0, 0.0, 2.0])
    probs = category_probabilities(1.4, np.array([-0.8, 0.2, 1.1]), theta)
    assert probs.shape == (3, 4)
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert np.all(probs > 0)
    assert probs[0, 0] > probs[-1, 0]
    assert probs[-1, 3] > probs[0, 3]


def test_information_positive_and_change_threshold_finite():
    discrimination = np.array([1.0, 1.3])
    thresholds = np.array([[-1.0, 0.0, 1.0], [-0.7, 0.3, 1.4]])
    theta = np.array([-1.0, 0.0, 1.0])
    information = item_information(discrimination, thresholds, theta)
    test_information = information.sum(axis=1)
    sem = 1 / np.sqrt(test_information)
    change_threshold = 1.96 * np.sqrt(2) * sem
    assert information.shape == (3, 2)
    assert np.all(information > 0)
    assert np.all(np.isfinite(change_threshold))
    assert np.all(change_threshold > 0)


def test_weighted_alpha_pattern_aggregation_and_fdr():
    x = np.array(
        [
            [0, 0, 0],
            [0, 0, 0],
            [1, 1, 1],
            [2, 2, 2],
            [3, 3, 3],
        ]
    )
    weights = np.array([1.0, 2.0, 1.0, 1.0, 1.0])
    alpha = weighted_cronbach_alpha(x, weights)
    patterns, pattern_weights = aggregate_patterns(x, weights)
    q = bh_fdr(np.array([0.001, 0.02, 0.4, 0.8]))
    assert alpha > 0.99
    assert len(patterns) == 4
    assert np.isclose(pattern_weights.sum(), weights.sum())
    assert np.all((q >= 0) & (q <= 1))
    assert q[0] <= q[1] <= q[2] <= q[3]

import numpy as np
import pytest

from abtest.cuped import adjust


def test_a_correlated_covariate_reduces_variance():
    rng = np.random.default_rng(0)
    pre = rng.gamma(2, 50, 20_000)
    post = 0.7 * pre + rng.gamma(2, 20, 20_000)
    _, result = adjust(post, pre)
    assert result.variance_reduction > 0.5
    assert result.theta == pytest.approx(0.7, abs=0.05)


def test_an_unrelated_covariate_changes_almost_nothing():
    rng = np.random.default_rng(1)
    post = rng.gamma(2, 50, 20_000)
    noise = rng.normal(0, 1, 20_000)
    _, result = adjust(post, noise)
    assert abs(result.variance_reduction) < 0.02


def test_adjustment_preserves_the_mean():
    """CUPED must reduce variance without moving the estimate."""
    rng = np.random.default_rng(2)
    pre = rng.gamma(2, 50, 10_000)
    post = 0.5 * pre + rng.gamma(2, 20, 10_000)
    adjusted, _ = adjust(post, pre)
    assert adjusted.mean() == pytest.approx(post.mean(), rel=1e-9)


def test_constant_covariate_is_handled_rather_than_dividing_by_zero():
    metric = np.array([1.0, 2.0, 3.0])
    adjusted, result = adjust(metric, np.ones(3))
    assert result.theta == 0.0
    np.testing.assert_array_equal(adjusted, metric)


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError):
        adjust(np.ones(10), np.ones(5))

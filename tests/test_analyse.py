import numpy as np
import pytest

from abtest.analyse import bayesian, frequentist


def test_identical_variants_are_not_significant():
    result = frequentist(1000, 20000, 1000, 20000)
    assert result.p_value == pytest.approx(1.0)
    assert not result.significant


def test_confidence_interval_contains_the_observed_lift():
    result = frequentist(1000, 20000, 1090, 20000)
    low, high = result.confidence_interval
    assert low < result.absolute_lift < high


def test_bayesian_probability_is_a_half_when_variants_match():
    result = bayesian(1000, 20000, 1000, 20000)
    assert result.probability_treatment_better == pytest.approx(0.5, abs=0.02)


def test_expected_loss_falls_as_evidence_grows():
    weak = bayesian(100, 2000, 110, 2000).expected_loss_choosing_treatment
    strong = bayesian(1000, 20000, 1100, 20000).expected_loss_choosing_treatment
    assert strong < weak


def test_false_positive_rate_matches_alpha():
    """Simulation-based calibration of the test itself.

    Running 2,000 A/A tests with no true effect, the share declared significant
    at alpha = 0.05 must land near 5%. If the test is miscalibrated, every
    readout built on it inherits the error.
    """
    rng = np.random.default_rng(42)
    rate, users, trials = 0.05, 8_000, 2_000
    false_positives = sum(
        frequentist(
            int(rng.binomial(users, rate)), users,
            int(rng.binomial(users, rate)), users,
        ).significant
        for _ in range(trials)
    )
    observed = false_positives / trials
    # Binomial standard error at 5% over 2,000 trials is about 0.5pp.
    assert 0.035 < observed < 0.065

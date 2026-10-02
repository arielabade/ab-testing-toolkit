import pytest

from abtest.design import detectable_effect, sample_size_proportions


def test_smaller_effects_need_more_users():
    big = sample_size_proportions(0.05, 0.20).per_variant
    small = sample_size_proportions(0.05, 0.05).per_variant
    assert small > big
    # Halving the effect roughly quadruples the sample: n scales with 1/mde^2.
    assert 3.5 < small / sample_size_proportions(0.05, 0.10).per_variant < 4.5


def test_more_power_needs_more_users():
    assert sample_size_proportions(0.05, 0.1, power=0.9).per_variant > \
           sample_size_proportions(0.05, 0.1, power=0.8).per_variant


def test_detectable_effect_inverts_sample_size():
    required = sample_size_proportions(0.05, 0.10).per_variant
    assert detectable_effect(0.05, required) == pytest.approx(0.10, abs=0.005)


def test_rejects_an_impossible_treatment_rate():
    with pytest.raises(ValueError):
        sample_size_proportions(0.8, 0.5)  # would imply a rate above 1


def test_days_required_uses_total_not_per_variant():
    size = sample_size_proportions(0.05, 0.10)
    assert size.days_required(size.total) == pytest.approx(1.0)

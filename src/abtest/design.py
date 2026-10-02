"""Experiment design: how many users, for how long, to detect what.

Everything here is decided BEFORE the test runs. Choosing a sample size after
seeing the data is how a 5% false-positive rate becomes 30%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats


@dataclass(frozen=True)
class SampleSize:
    per_variant: int
    total: int
    baseline_rate: float
    mde_relative: float
    mde_absolute: float
    power: float
    alpha: float

    def days_required(self, daily_users: int) -> float:
        return self.total / daily_users


def sample_size_proportions(
    baseline_rate: float,
    mde_relative: float,
    power: float = 0.80,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> SampleSize:
    """Users per variant for a two-proportion test.

    `mde_relative` is the smallest lift worth detecting, as a share of the
    baseline: 0.05 means "a 5% relative improvement". Stating it relatively is
    deliberate — teams reason in "a 5% lift", not "0.0075 absolute".

    The MDE is a business input, not a statistical one. It should come from the
    smallest effect that would change a decision, and when a team cannot name
    that number, the test is usually not worth running.
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be a probability")
    if mde_relative <= 0:
        raise ValueError("mde_relative must be positive")

    treatment_rate = baseline_rate * (1 + mde_relative)
    if treatment_rate >= 1:
        raise ValueError("baseline_rate * (1 + mde_relative) must stay below 1")

    z_alpha = stats.norm.ppf(1 - alpha / (2 if two_sided else 1))
    z_power = stats.norm.ppf(power)

    pooled = (baseline_rate + treatment_rate) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power * math.sqrt(
            baseline_rate * (1 - baseline_rate) + treatment_rate * (1 - treatment_rate)
        )
    ) ** 2
    per_variant = math.ceil(numerator / (treatment_rate - baseline_rate) ** 2)

    return SampleSize(
        per_variant=per_variant,
        total=per_variant * 2,
        baseline_rate=baseline_rate,
        mde_relative=mde_relative,
        mde_absolute=treatment_rate - baseline_rate,
        power=power,
        alpha=alpha,
    )


def detectable_effect(
    baseline_rate: float, per_variant: int, power: float = 0.80, alpha: float = 0.05
) -> float:
    """The inverse question, and usually the more useful one.

    Teams rarely get to choose the sample size; they get the traffic they get.
    This answers "with the traffic we have, what is the smallest lift we could
    detect", which often reveals that the planned test cannot work.
    """
    low, high = 1e-6, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        try:
            required = sample_size_proportions(baseline_rate, middle, power, alpha).per_variant
        except ValueError:
            high = middle
            continue
        if required > per_variant:
            low = middle
        else:
            high = middle
    return high

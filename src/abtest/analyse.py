"""Reading a finished experiment, two ways.

Frequentist and Bayesian answers are reported side by side because they answer
different questions, and teams routinely state the frequentist result as if it
were the Bayesian one.

    p-value          P(data at least this extreme | no true effect)
    P(B beats A)     P(treatment is better | this data)

"95% confident the variant wins" is the second sentence attached to the first
number, and it is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class FrequentistResult:
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float
    p_value: float
    confidence_interval: tuple[float, float]
    significant: bool


@dataclass(frozen=True)
class BayesianResult:
    probability_treatment_better: float
    expected_relative_lift: float
    credible_interval: tuple[float, float]
    expected_loss_choosing_treatment: float


def frequentist(
    control_conversions: int, control_users: int,
    treatment_conversions: int, treatment_users: int,
    alpha: float = 0.05,
) -> FrequentistResult:
    """Two-proportion z-test with a confidence interval on the absolute lift."""
    control_rate = control_conversions / control_users
    treatment_rate = treatment_conversions / treatment_users
    difference = treatment_rate - control_rate

    pooled = (control_conversions + treatment_conversions) / (control_users + treatment_users)
    standard_error_pooled = np.sqrt(pooled * (1 - pooled) * (1 / control_users + 1 / treatment_users))
    z_statistic = difference / standard_error_pooled if standard_error_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))

    # The interval uses unpooled variance: pooling assumes the null, which is
    # right for the test and wrong for estimating the effect.
    standard_error = np.sqrt(
        control_rate * (1 - control_rate) / control_users
        + treatment_rate * (1 - treatment_rate) / treatment_users
    )
    margin = stats.norm.ppf(1 - alpha / 2) * standard_error

    return FrequentistResult(
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        absolute_lift=difference,
        relative_lift=difference / control_rate if control_rate > 0 else float("nan"),
        p_value=float(p_value),
        confidence_interval=(difference - margin, difference + margin),
        significant=bool(p_value < alpha),
    )


def bayesian(
    control_conversions: int, control_users: int,
    treatment_conversions: int, treatment_users: int,
    prior_alpha: float = 1.0, prior_beta: float = 1.0,
    draws: int = 200_000, seed: int = 20261002,
) -> BayesianResult:
    """Beta-Binomial posteriors, compared by sampling.

    The uniform Beta(1, 1) prior is deliberately uninformative: with a real
    baseline rate known from history, a tighter prior would be both legitimate
    and more efficient, and that choice should be stated rather than defaulted.

    `expected_loss_choosing_treatment` is the decision-theoretic quantity: the
    average amount of conversion rate given up if treatment is shipped and is in
    fact worse. Teams ship on it rather than on a probability threshold, because
    it is denominated in the thing they care about.
    """
    rng = np.random.default_rng(seed)
    control_posterior = rng.beta(
        prior_alpha + control_conversions,
        prior_beta + control_users - control_conversions,
        draws,
    )
    treatment_posterior = rng.beta(
        prior_alpha + treatment_conversions,
        prior_beta + treatment_users - treatment_conversions,
        draws,
    )

    relative = (treatment_posterior - control_posterior) / control_posterior
    loss = np.maximum(control_posterior - treatment_posterior, 0.0)

    return BayesianResult(
        probability_treatment_better=float((treatment_posterior > control_posterior).mean()),
        expected_relative_lift=float(relative.mean()),
        credible_interval=(float(np.quantile(relative, 0.025)), float(np.quantile(relative, 0.975))),
        expected_loss_choosing_treatment=float(loss.mean()),
    )

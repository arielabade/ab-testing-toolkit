"""The decision report.

An experiment readout that stops at "p < 0.05" has not made a decision. This
assembles the three things a shipping decision needs: is the effect real, is it
big enough to matter, and what does it cost to be wrong.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .analyse import BayesianResult, FrequentistResult, bayesian, frequentist
from .design import sample_size_proportions


@dataclass(frozen=True)
class Decision:
    verdict: str
    reason: str
    frequentist: FrequentistResult
    bayes: BayesianResult
    powered_for_mde: float | None
    observed_relative_lift: float


def decide(
    control_conversions: int, control_users: int,
    treatment_conversions: int, treatment_users: int,
    minimum_worthwhile_lift: float,
    alpha: float = 0.05,
    ship_probability: float = 0.95,
) -> Decision:
    """Ship, hold, or stop.

    `minimum_worthwhile_lift` is the relative lift below which shipping is not
    worth the engineering and risk, even if real. Without it, a test can be
    "significant" and still not justify the change — the most common way a
    statistically correct readout produces a bad decision.
    """
    freq = frequentist(control_conversions, control_users, treatment_conversions, treatment_users, alpha)
    bayes = bayesian(control_conversions, control_users, treatment_conversions, treatment_users)

    baseline = control_conversions / control_users
    try:
        powered = sample_size_proportions(baseline, minimum_worthwhile_lift, alpha=alpha)
        powered_for_mde = powered.per_variant
    except ValueError:
        powered_for_mde = None

    underpowered = powered_for_mde is not None and control_users < powered_for_mde

    if bayes.probability_treatment_better >= ship_probability and freq.relative_lift >= minimum_worthwhile_lift:
        verdict = "ship"
        reason = (
            f"P(treatment better) = {bayes.probability_treatment_better:.1%} and the observed lift "
            f"of {freq.relative_lift:.1%} clears the {minimum_worthwhile_lift:.1%} bar."
        )
    elif bayes.probability_treatment_better >= ship_probability:
        verdict = "hold"
        reason = (
            f"The effect looks real (P = {bayes.probability_treatment_better:.1%}) but the lift of "
            f"{freq.relative_lift:.1%} is below the {minimum_worthwhile_lift:.1%} worth shipping for."
        )
    elif underpowered:
        verdict = "inconclusive"
        reason = (
            f"Not powered to detect {minimum_worthwhile_lift:.1%}: needs {powered_for_mde:,} per "
            f"variant, has {control_users:,}. Absence of a result is not evidence of no effect."
        )
    else:
        verdict = "stop"
        reason = (
            f"Adequately powered and the effect did not appear "
            f"(P = {bayes.probability_treatment_better:.1%}, p = {freq.p_value:.3f})."
        )

    return Decision(
        verdict=verdict,
        reason=reason,
        frequentist=freq,
        bayes=bayes,
        powered_for_mde=powered_for_mde,
        observed_relative_lift=freq.relative_lift,
    )


def render(decision: Decision) -> str:
    freq, bayes = decision.frequentist, decision.bayes
    low, high = freq.confidence_interval
    credible_low, credible_high = bayes.credible_interval
    return "\n".join(
        [
            f"VERDICT: {decision.verdict.upper()}",
            f"  {decision.reason}",
            "",
            "Frequentist",
            f"  control            {freq.control_rate:.4%}",
            f"  treatment          {freq.treatment_rate:.4%}",
            f"  relative lift      {freq.relative_lift:+.2%}",
            f"  p-value            {freq.p_value:.4f}",
            f"  95% CI (absolute)  [{low:+.4%}, {high:+.4%}]",
            "",
            "Bayesian",
            f"  P(treatment better){bayes.probability_treatment_better:>8.1%}",
            f"  expected lift      {bayes.expected_relative_lift:+.2%}",
            f"  95% credible       [{credible_low:+.2%}, {credible_high:+.2%}]",
            f"  expected loss      {bayes.expected_loss_choosing_treatment:.6f} conversion rate",
            "",
            "Note: the p-value is P(data | no effect). P(treatment better) is",
            "P(effect | data). They are not the same statement and should not be",
            "swapped when the result is written up.",
        ]
    )

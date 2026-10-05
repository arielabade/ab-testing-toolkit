"""Figures for the README.

Unlike the other repositories in this portfolio, this one has no dataset: the
toolkit's subject is the procedure, not a particular experiment. So these
figures call the library itself, with the same worked scenarios the README
quotes, and the chart is the output of the thing being described.

Run with ``python -m abtest.figures``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import brandviz as bv
from .cuped import adjust
from .design import detectable_effect, sample_size_proportions
from .report import decide

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "assets" / "figures"

BASELINE = 0.05
DAILY_USERS = 20_000
MIN_WORTHWHILE = 0.05

#: The three readouts from ``example_readout.py``, in the order a team is
#: least to most likely to misread them.
SCENARIOS = {
    "A clear win": (3_300, 66_000, 3_600, 66_000),
    "Real effect, below\nthe bar worth shipping for": (12_200, 244_000, 12_566, 244_000),
    "Promising number,\nnever powered to answer": (250, 5_000, 275, 5_000),
}

VERDICT_COLOUR = {
    "ship": bv.COBALT,
    "hold": bv.AMBER,
    "inconclusive": bv.SLATE,
    "stop": bv.CRIMSON,
}


def verdicts() -> Path:
    """Three readouts, three verdicts, one picture.

    A forest plot: each scenario's observed lift with its confidence interval,
    against the lift that would actually be worth shipping. The two failure
    modes the toolkit exists to separate are visible as shapes — a tight
    interval sitting below the bar, and an interval so wide it contains both
    a large win and a large loss.
    """
    decisions = {name: decide(*counts, minimum_worthwhile_lift=MIN_WORTHWHILE)
                 for name, counts in SCENARIOS.items()}

    fig, ax = bv.panel(
        12.4, 5.8,
        title="Not significant and not powered are different findings",
        subtitle="Observed relative lift with its 95% confidence interval, against the lift worth shipping for",
    )
    positions = np.arange(len(decisions), dtype=float)
    ax.set_ylim(-0.75, len(decisions) - 0.25)

    # The band of outcomes that are real but not worth the change.
    ax.axvspan(0, MIN_WORTHWHILE * 100, color=bv.GRAPHITE, zorder=1)
    ax.axvline(0, color=bv.STEEL, linewidth=1.2, zorder=3)
    bv.reference_line(ax, MIN_WORTHWHILE * 100, f"{MIN_WORTHWHILE:.0%}: worth shipping for",
                      horizontal=False, where=0.055, ha="left")

    for position, (name, decision) in zip(positions, decisions.items()):
        colour = VERDICT_COLOUR[decision.verdict]
        baseline = decision.frequentist.control_rate
        low, high = (bound / baseline * 100 for bound in decision.frequentist.confidence_interval)
        centre = decision.observed_relative_lift * 100

        ax.plot([low, high], [position, position], color=colour, linewidth=3.0,
                solid_capstyle="round", zorder=4)
        ax.plot(centre, position, "o", markersize=11, markerfacecolor=colour,
                markeredgecolor=bv.CARBON, markeredgewidth=2.0, zorder=5)
        # The verdict is set in ink, not in the verdict's own colour: the
        # coloured interval beside it already carries that identity, and
        # SLATE-on-carbon text is not readable.
        ax.text(high + 1.4, position, decision.verdict.upper(), va="center", ha="left",
                fontsize=10.5, fontweight="bold", color=bv.IVORY, zorder=6)

    ax.set_yticks(positions, list(decisions))
    ax.set_xlabel("Relative lift against control")
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:+.0f}%")
    ax.set_xlim(-22, 42)
    bv.clean(ax, axis="x", spines=("top", "right", "left"))
    fig.text(0.045, 0.045,
             "The shaded band is the region where an effect is real and still not worth the change.",
             color=bv.STEEL, fontsize=10)
    fig.subplots_adjust(bottom=0.20)
    return bv.save(fig, FIGURES / "verdicts.svg")


def power_curve() -> Path:
    """What a test of a given length can actually detect.

    Teams pick a runtime and then ask what it found. This is the same question
    asked in the useful order, and the curve is steep enough early on that the
    difference between one and two weeks is usually the difference between an
    answerable and an unanswerable test.
    """
    days = np.arange(3, 43)
    detectable = np.array([
        detectable_effect(BASELINE, int(DAILY_USERS * day // 2)) * 100 for day in days
    ])

    fig, ax = bv.panel(
        12.4, 5.4,
        title="What a test of this length could detect, before it is run",
        subtitle=f"Smallest relative lift detectable at 80% power, {BASELINE:.0%} baseline, {DAILY_USERS:,} users a day",
    )
    ax.plot(days, detectable, color=bv.COBALT, linewidth=2.4, zorder=4)
    ax.set_xlim(days.min(), days.max())
    ax.set_ylim(0, detectable.max() * 1.08)

    plan = sample_size_proportions(BASELINE, MIN_WORTHWHILE)
    required_days = plan.days_required(DAILY_USERS)
    ax.plot([required_days], [MIN_WORTHWHILE * 100], "o", markersize=11,
            markerfacecolor=bv.COBALT, markeredgecolor=bv.CARBON,
            markeredgewidth=2.0, zorder=6)
    bv.annotate(
        ax,
        f"Detecting a {MIN_WORTHWHILE:.0%} lift needs {required_days:.0f} days\n"
        f"({plan.per_variant:,} users per variant)",
        xy=(required_days + 0.6, MIN_WORTHWHILE * 100),
        xytext=(required_days + 5, detectable.max() * 0.45), color=bv.IVORY,
    )

    week = detectable[days == 7][0]
    bv.annotate(
        ax, f"A one-week test can only see a {week:.0f}% lift",
        xy=(7, week), xytext=(10.5, detectable.max() * 0.80), color=bv.STEEL,
    )

    ax.set_xlabel("Days of traffic")
    ax.set_ylabel("Smallest detectable relative lift")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    bv.clean(ax, axis="both", spines=("top", "right"))
    return bv.save(fig, FIGURES / "power_curve.svg")


def cuped_variance(seed: int = 20261002) -> Path:
    """What a pre-period covariate buys, in traffic rather than in variance.

    Variance reduction is the statistician's units. The effective sample
    multiplier is the number a team can act on, so the chart is labelled in
    both and the second one is the headline.
    """
    rng = np.random.default_rng(seed)
    correlations = np.linspace(0.0, 0.95, 20)
    size = 40_000

    reductions, multipliers = [], []
    for correlation in correlations:
        covariate = rng.normal(size=size)
        noise = rng.normal(size=size)
        metric = correlation * covariate + np.sqrt(max(1 - correlation**2, 0.0)) * noise
        _, result = adjust(metric, covariate)
        reductions.append(result.variance_reduction * 100)
        multipliers.append(result.effective_sample_multiplier)

    fig, ax = bv.panel(
        12.4, 5.4,
        title="A pre-period covariate is traffic you already have",
        subtitle="CUPED variance reduction, and the traffic an unadjusted test would need to match it",
    )
    ax.plot(correlations, reductions, color=bv.COBALT, linewidth=2.4, zorder=4)
    ax.fill_between(correlations, 0, reductions, color=bv.COBALT, alpha=0.12, zorder=1)
    ax.set_xlim(0, 0.95)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Correlation between the pre-period covariate and the metric")
    ax.set_ylabel("Variance removed")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")

    for target in (0.5, 0.87):
        covariate = rng.normal(size=size)
        noise = rng.normal(size=size)
        metric = target * covariate + np.sqrt(max(1 - target**2, 0.0)) * noise
        _, marked = adjust(metric, covariate)
        reduction = marked.variance_reduction * 100
        ax.plot([target], [reduction], "o", markersize=10,
                markerfacecolor=bv.COBALT, markeredgecolor=bv.CARBON,
                markeredgewidth=2.0, zorder=6)
        ax.text(target, reduction + 4.5,
                f"r = {target}: {reduction:.0f}% variance removed\n"
                f"= {marked.effective_sample_multiplier:.1f}x the traffic",
                ha="center", va="bottom", fontsize=10, fontweight="bold", color=bv.IVORY)

    bv.clean(ax, axis="both", spines=("top", "right"))
    return bv.save(fig, FIGURES / "cuped_variance.svg")


def headline():
    """The three numbers the README leads with."""
    plan = sample_size_proportions(BASELINE, MIN_WORTHWHILE)
    rng = np.random.default_rng(20261002)
    covariate = rng.normal(size=60_000)
    metric = 0.87 * covariate + np.sqrt(1 - 0.87**2) * rng.normal(size=60_000)
    _, cuped = adjust(metric, covariate)

    fig, _ = bv.kpi_strip([
        ("3 of 3", "Worked readouts where the naive call\nand the correct call differ"),
        (f"{cuped.variance_reduction:.0%}", f"Variance removed by CUPED at r=0.87,\nworth {cuped.effective_sample_multiplier:.1f}x the traffic"),
        (f"{plan.per_variant:,}", f"Users per variant to detect a {MIN_WORTHWHILE:.0%} lift\nat a {BASELINE:.0%} baseline"),
    ])
    return bv.save(fig, FIGURES / "headline.svg")


def build_all() -> list[Path]:
    return [headline(), verdicts(), power_curve(), cuped_variance()]


if __name__ == "__main__":
    for path in build_all():
        print(path.relative_to(ROOT))

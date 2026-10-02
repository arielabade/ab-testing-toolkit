"""CUPED: variance reduction using pre-experiment data.

The idea in one line: a user's behaviour before the experiment predicts their
behaviour during it, and that predictable part is noise as far as the treatment
effect is concerned. Subtracting it shrinks the variance without touching the
expected effect, so the same traffic detects a smaller lift.

    adjusted = metric - theta * (covariate - mean(covariate))
    theta    = cov(metric, covariate) / var(covariate)

The estimate stays unbiased because the covariate is measured BEFORE
randomisation and so cannot be affected by the treatment. Using a covariate
measured during the experiment breaks exactly that, and is the one way to get
CUPED badly wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CupedResult:
    theta: float
    variance_before: float
    variance_after: float
    variance_reduction: float
    correlation: float

    @property
    def effective_sample_multiplier(self) -> float:
        """How much more traffic the unadjusted test would need to match this."""
        return 1.0 / (1.0 - self.variance_reduction) if self.variance_reduction < 1 else float("inf")


def adjust(metric: np.ndarray, covariate: np.ndarray) -> tuple[np.ndarray, CupedResult]:
    metric = np.asarray(metric, dtype=float)
    covariate = np.asarray(covariate, dtype=float)
    if metric.shape != covariate.shape:
        raise ValueError("metric and covariate must be the same length")

    covariate_variance = covariate.var(ddof=1)
    if covariate_variance == 0:
        # A constant covariate explains nothing; return the metric untouched
        # rather than dividing by zero.
        return metric.copy(), CupedResult(0.0, metric.var(ddof=1), metric.var(ddof=1), 0.0, 0.0)

    theta = np.cov(metric, covariate, ddof=1)[0, 1] / covariate_variance
    adjusted = metric - theta * (covariate - covariate.mean())

    variance_before = metric.var(ddof=1)
    variance_after = adjusted.var(ddof=1)
    return adjusted, CupedResult(
        theta=float(theta),
        variance_before=float(variance_before),
        variance_after=float(variance_after),
        variance_reduction=float(1 - variance_after / variance_before),
        correlation=float(np.corrcoef(metric, covariate)[0, 1]),
    )

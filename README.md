# A/B Testing Toolkit

Design an experiment, read it honestly, and decide.

---

## 1. Business problem

Most experiment failures are not statistical. They are decision failures: a test that ran without
enough traffic to answer anything, a "significant" result too small to be worth shipping, or a
p-value reported in the sentence that belongs to a posterior probability.

This toolkit covers the three moments where those failures happen — before the test, when reading it,
and when deciding — and refuses to produce a verdict without a business input.

---

## 2. Key results

**Design is where most tests are lost.** At a 5% baseline, detecting a 5% relative lift needs
**122,124 users per variant**. A team with 20,000 users a day plans a one-week test and can in fact
only detect a **6.6%** lift — so a real 5% improvement would be missed, and recorded as "no effect".

| Users per variant | Smallest detectable lift (relative) |
| --- | --- |
| 5,000 | 25.9% |
| 20,000 | 12.6% |
| 100,000 | 5.5% |

**CUPED buys traffic you do not have.** With a pre-experiment covariate correlated at 0.87, variance
falls **75.3%** — equivalent to running the test with **4.05x** the users. On the design above, that
turns a 12-day test into a 3-day one, at no cost in bias.

**Three verdicts, three different failures avoided.** The worked example in
[`reports/example_readout.txt`](reports/example_readout.txt):

| Scenario | p-value | P(treatment better) | Verdict |
| --- | --- | --- | --- |
| Clear win | 0.0002 | 100.0% | **SHIP** |
| Real effect, below the bar worth shipping for | — | 99.2% | **HOLD** |
| Promising number, never powered to answer | 0.2623 | 86.9% | **INCONCLUSIVE** |

The second case is the one that costs teams most: the effect is real with 99.2% probability, and
shipping it is still wrong, because a 3.0% lift does not clear the 5.0% bar the business set for the
engineering and risk involved.

The third is the one that gets misreported. A 10% observed lift with p = 0.26 is routinely written up
as "no difference". It is not: the test never had the power to tell. **Absence of a result is not
evidence of no effect.**

---

## 3. Data

**No external dataset.** Every number here is produced by the toolkit's own functions from inputs
given in the example, and the validation data is **simulated**, deliberately.

That is the right choice for this project: the question is not "what happened in some company's
experiment" but "does this implementation do the right arithmetic". That can only be checked against
a process whose truth is known. So:

- The false-positive rate is validated by running **2,000 simulated A/A tests** and confirming that
  the share declared significant lands within sampling error of the 5% alpha.
- CUPED's `theta` is validated by generating data with a known coefficient of 0.7 and confirming the
  estimator recovers it.

A toolkit that cannot demonstrate its own calibration should not be used to decide anything.

---

## 4. Approach

**Frequentist and Bayesian side by side, because they answer different questions.**

```
p-value       P(data at least this extreme | no true effect)
P(B beats A)  P(treatment is better | this data)
```

"We're 95% confident the variant wins" is the second statement attached to the first number. The
rendered report prints the distinction at the bottom of every readout, because that is where the
mistake gets made.

**Expected loss, not just probability.** `expected_loss_choosing_treatment` is the average conversion
rate given up if treatment ships and is in fact worse. It is denominated in the thing the business
cares about, which makes it a better ship gate than a probability threshold.

**Pooled variance for the test, unpooled for the interval.** Pooling assumes the null hypothesis,
which is correct when testing it and wrong when estimating the effect size.

**A minimum worthwhile lift is required, not optional.** `decide()` will not return a verdict without
one. A test whose team cannot name the smallest effect that would change their decision is usually a
test that should not run.

**CUPED's covariate must be pre-experiment.** The estimate stays unbiased only because the covariate
cannot have been affected by the treatment. Using a covariate measured during the experiment breaks
exactly that, and is the one way to get CUPED badly wrong.

---

## 5. Business metrics

```
n per variant     = (z_alpha * sqrt(2p(1-p)) + z_power * sqrt(p0(1-p0) + p1(1-p1)))^2 / (p1 - p0)^2
relative lift     = (treatment_rate - control_rate) / control_rate
CUPED theta       = cov(metric, covariate) / var(covariate)
adjusted metric   = metric - theta * (covariate - mean(covariate))
variance multiple = 1 / (1 - variance_reduction)
expected loss     = E[max(control_rate - treatment_rate, 0)]
```

Sample size scales with `1 / mde²`: halving the effect you want to detect quadruples the traffic you
need. There is a test asserting that relationship, because it is the single most useful intuition in
experiment planning.

---

## 6. Limitations and next steps

- **Binary outcomes only.** Conversion rates, not revenue per user. Revenue is heavy-tailed and needs
  different machinery; CUPED here applies to continuous metrics but the design and analysis functions
  assume proportions.
- **No sequential testing.** The sample size is fixed in advance and the analysis assumes a single
  look at the data. Peeking at a fixed-horizon test inflates the false-positive rate badly, and the
  honest fixes — alpha spending, always-valid inference — are not implemented here.
- **No multiple-comparison correction.** Testing four variants against one control at alpha = 0.05
  gives roughly a 19% chance of at least one false positive.
- **Independence is assumed.** Users in the same household, the same session, or the same network
  effect are not independent, and the standard errors are too small when they are not.
- **The Beta(1,1) prior is uninformative by choice.** A team with a well-known baseline rate should
  use a tighter prior, which would narrow the credible interval legitimately.
- **Next step:** add a sequential test with alpha spending, so a test can be stopped early without
  the peeking penalty, and extend the analysis layer to revenue-per-user with a bootstrap interval.

---

## 7. How to run

```bash
git clone https://github.com/arielabade/ab-testing-toolkit
cd ab-testing-toolkit

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python example_readout.py   # design, then three readouts
pytest                      # 15 tests, including 2,000 simulated A/A trials
```

```python
from abtest.design import sample_size_proportions
from abtest.report import decide, render

plan = sample_size_proportions(baseline_rate=0.05, mde_relative=0.05)
print(plan.per_variant, plan.days_required(daily_users=20_000))

print(render(decide(3_300, 66_000, 3_600, 66_000, minimum_worthwhile_lift=0.05)))
```

### Layout

```
src/abtest/design.py    sample size, minimum detectable effect
src/abtest/analyse.py   two-proportion z-test, Beta-Binomial posteriors, expected loss
src/abtest/cuped.py     variance reduction with a pre-experiment covariate
src/abtest/report.py    ship / hold / inconclusive / stop, with the reason
tests/                  including simulation-based calibration of the test itself
```

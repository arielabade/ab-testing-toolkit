"""A worked readout, end to end."""
import sys
from pathlib import Path
sys.path.insert(0, "src")

from abtest.design import detectable_effect, sample_size_proportions
from abtest.report import decide, render

BASELINE, DAILY_USERS, MIN_WORTHWHILE = 0.05, 20_000, 0.05

print("=" * 72)
print("1. DESIGN, before the test runs")
print("=" * 72)
plan = sample_size_proportions(BASELINE, MIN_WORTHWHILE)
print(f"baseline                  {BASELINE:.1%}")
print(f"minimum worthwhile lift   {MIN_WORTHWHILE:.1%} relative")
print(f"users per variant         {plan.per_variant:,}")
print(f"runtime at {DAILY_USERS:,}/day   {plan.days_required(DAILY_USERS):.1f} days")
print(f"\nWith only 7 days of traffic, the smallest detectable lift would be "
      f"{detectable_effect(BASELINE, DAILY_USERS * 7 // 2):.1%}.")

print()
print("=" * 72)
print("2. READOUT, three scenarios")
print("=" * 72)

# Each scenario demonstrates a different verdict, including the two that teams
# most often misread: a real effect too small to be worth shipping, and a test
# that simply never had the traffic to answer the question.
scenarios = {
    "clear win": (3_300, 66_000, 3_600, 66_000),
    "real effect, below the bar worth shipping for": (12_200, 244_000, 12_566, 244_000),
    "promising number, but never powered to answer": (250, 5_000, 275, 5_000),
}
for name, (cc, cu, tc, tu) in scenarios.items():
    print(f"\n--- {name}")
    print(render(decide(cc, cu, tc, tu, minimum_worthwhile_lift=MIN_WORTHWHILE)))

Path("reports").mkdir(exist_ok=True)

"""Honest verdicts. PASS needs a target committed before the run, and NO_TARGET is never a pass."""

from __future__ import annotations

import math
from typing import Iterable, Mapping

from stranded_physics.core.api import Verdict

Z_95 = 1.959964  # Two-sided 95% normal quantile.


def wilson_interval(successes: int, trials: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a proportion. Holds up for rare events, unlike the normal approximation."""
    if trials <= 0:
        return 0.0, 1.0
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def judge_value(value: float | None, target: float | None, tolerance: float | None) -> Verdict:
    """Compare a prediction with a committed target and an absolute tolerance."""
    if target is None or tolerance is None:
        return "NO_TARGET"
    if value is None or math.isnan(value):
        return "NOT_RUN"
    return "PASS" if abs(value - target) <= tolerance else "FAIL"


def judge_rate(successes: int, trials: int, low: float | None, high: float | None) -> Verdict:
    """A rate passes only if its whole interval sits inside the bar. Zero events alone never pass."""
    if low is None and high is None:
        return "NO_TARGET"
    if trials <= 0:
        return "NOT_RUN"
    ci_low, ci_high = wilson_interval(successes, trials)
    floor, ceiling = (0.0 if low is None else low), (1.0 if high is None else high)
    if floor <= ci_low and ci_high <= ceiling:
        return "PASS"
    if ci_high < floor or ci_low > ceiling:
        return "FAIL"
    return "INSUFFICIENT_DATA"


def agreement(rows: Iterable[Mapping[str, object]]) -> tuple[int, int]:
    """Passing and judged counts. Only predictions on holdout data count, so inputs can't inflate it."""
    judged = passed = 0
    for row in rows:
        if row.get("role") != "prediction" or row.get("split") != "holdout":
            continue
        verdict = row.get("verdict")
        if verdict in ("PASS", "FAIL"):
            judged += 1
            passed += verdict == "PASS"
    return passed, judged

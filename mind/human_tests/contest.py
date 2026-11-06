"""Scores quantum against classical on published human data, by the rules in PRE_REGISTERED.md. Nothing is fitted to the part being predicted.

python -m mind.human_tests.contest
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2

from mind.config import ETA
from mind.model import p_protect_closed_form

HERE = Path(__file__).resolve().parent
Z_AT_5_PERCENT = 1.959964
CHI2_DEGREES = 3
SIGNIFICANCE = 0.05
CELLS = ("yy", "yn", "ny", "nn")
FLOOR = 1e-9
START_ANGLES = tuple((x, y) for x in np.linspace(0.1, 1.5, 8) for y in np.linspace(0.1, 1.5, 8))


def _rows(name):
    with (HERE / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def disjunction():
    """Test 1: predict the unknown rate from the two known rates."""
    rows = []
    for row in _rows("disjunction.csv"):
        a, b, seen = float(row["known_a"]), float(row["known_b"]), float(row["unknown"])
        quantum = float(p_protect_closed_form(0.5, 1.0, a, b, ETA))
        average, best = (a + b) / 2, min(max(seen, min(a, b)), max(a, b))
        rows.append(
            dict(
                study=row["study"],
                scored=row["scored"] == "yes",
                observed=seen,
                quantum=quantum,
                classical_average=average,
                classical_best=best,
                error_quantum=abs(quantum - seen),
                error_average=abs(average - seen),
                error_best=abs(best - seen),
            )
        )
    return rows


def first_order_table(a, b):
    """A then B: yes yes, yes no, no yes, no no, for a two-dimensional model with p(A yes) = cos(a)^2 and p(B yes | A yes) = cos(b)^2."""
    pa, pb = math.cos(a) ** 2, math.cos(b) ** 2
    return np.array([pa * pb, pa * (1 - pb), (1 - pa) * (1 - pb), (1 - pa) * pb])


def first_order_angles(ab):
    """Maximum likelihood on the first order only."""

    def loss(angles):
        return -float(np.sum(ab * np.log(np.maximum(first_order_table(*angles), FLOOR))))

    results = (minimize(loss, start, method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-10)) for start in START_ANGLES)
    best = min(results, key=lambda result: result.fun)
    return float(best.x[0]), float(best.x[1])


def second_order_from_angles(a, b, sign):
    """B then A: yes yes, yes no, no yes, no no. B sits at a + sign * b from the state, and at b from A."""
    py, keep = math.cos(a + sign * b) ** 2, math.cos(b) ** 2
    return np.array([py * keep, py * (1 - keep), (1 - py) * (1 - keep), (1 - py) * keep])


def question_order():
    """Tests 2 and 3: predict the other question order, and test each theory's own zero-parameter claim."""
    rows = []
    for row in _rows("question_order.csv"):
        ab = np.array([float(row["ab_" + cell]) for cell in CELLS])
        ba = np.array([float(row["ba_" + cell]) for cell in CELLS])
        n1, n2 = int(row["n_ab"]), int(row["n_ba"])
        # If order does nothing, B yes then A no is the same people as A no then B yes.
        classical = np.array([ab[0], ab[2], ab[1], ab[3]])
        a, b = first_order_angles(ab)
        plus, minus = (0.5 * float(np.abs(second_order_from_angles(a, b, sign) - ba).sum()) for sign in (1, -1))
        pab, pba = ab[1] + ab[2], ba[1] + ba[2]
        q = pab - pba
        z = q / math.sqrt(pab * (1 - pab) / n1 + pba * (1 - pba) / n2)
        counts = np.array([classical * n1, ba * n2])
        expected = counts.sum(axis=1, keepdims=True) * counts.sum(axis=0, keepdims=True) / counts.sum()
        statistic = float(np.sum((counts - expected) ** 2 / np.maximum(expected, FLOOR)))
        rows.append(
            dict(
                study=row["study"],
                domain=row["domain"],
                tvd_classical=0.5 * float(np.abs(classical - ba).sum()),
                tvd_quantum_mean=(plus + minus) / 2,
                tvd_quantum_better=min(plus, minus),
                q=float(q),
                z=float(z),
                qq_survives=abs(z) < Z_AT_5_PERCENT,
                chi2=statistic,
                no_order_effect_survives=float(chi2.sf(statistic, CHI2_DEGREES)) > SIGNIFICANCE,
            )
        )
    return rows


def report():
    one, two = disjunction(), question_order()
    scored = [row for row in one if row["scored"]]

    def mean(rows, key):
        return float(np.mean([row[key] for row in rows]))

    summary = dict(
        eta=ETA,
        test1=dict(
            rows=len(scored),
            mean_error_quantum=mean(scored, "error_quantum"),
            mean_error_classical_average=mean(scored, "error_average"),
            mean_error_classical_best=mean(scored, "error_best"),
            quantum_beats_average=sum(row["error_quantum"] < row["error_average"] for row in scored),
            quantum_beats_best=sum(row["error_quantum"] < row["error_best"] for row in scored),
        ),
        test2=dict(
            rows=len(two),
            mean_tvd_classical=mean(two, "tvd_classical"),
            mean_tvd_quantum=mean(two, "tvd_quantum_mean"),
            mean_tvd_quantum_better_sign=mean(two, "tvd_quantum_better"),
            quantum_beats_classical=sum(row["tvd_quantum_mean"] < row["tvd_classical"] for row in two),
            better_sign_beats_classical=sum(row["tvd_quantum_better"] < row["tvd_classical"] for row in two),
        ),
        test3=dict(
            rows=len(two), qq_survives=sum(row["qq_survives"] for row in two), no_order_effect_survives=sum(row["no_order_effect_survives"] for row in two)
        ),
    )
    return one, two, summary


def main():
    one, two, summary = report()
    print("TEST 1: study, observed, quantum, classical average, best classical")
    for row in one:
        print(
            " ",
            row["study"][:38].ljust(39),
            *(f"{row[key]:.3f}" for key in ("observed", "quantum", "classical_average", "classical_best")),
            "" if row["scored"] else "(fit, not scored)",
        )
    print("TESTS 2 and 3: study, classical, quantum mean, quantum better sign, q, z, QQ holds, no order effect holds")
    for row in two:
        print(
            " ",
            row["study"][:24].ljust(25),
            *(f"{row[key]:.3f}" for key in ("tvd_classical", "tvd_quantum_mean", "tvd_quantum_better", "q")),
            f"{row['z']:.2f}",
            row["qq_survives"],
            row["no_order_effect_survives"],
        )
    print(json.dumps(summary, indent=1, default=int))


if __name__ == "__main__":
    main()

"""Checks the scoring code against published values and exact cases, so that its results can be trusted."""
import csv
from pathlib import Path

import numpy as np
import pytest

from mind.human_tests.contest import first_order_angles, first_order_table, question_order, report, second_order_from_angles


def by_study():
    return {row["study"]: row for row in question_order()}


@pytest.mark.parametrize("study, q, z", [("Clinton-Gore", -.0031, -.1090), ("Gingrich-Dole", -.0031, -.0896), ("White-Black", -.0189, -.7419), ("Rose-Jackson", .1514, 5.3026), ("Racial hostility", .0757, 1.4842), ("Affirmative action", .0430, .6945)])
def test_q_and_z_reproduce_the_published_table(study, q, z):
    row = by_study()[study]
    assert row["q"] == pytest.approx(q, abs=.002)
    assert row["z"] == pytest.approx(z, abs=.4)


def test_angles_recover_a_known_quantum_table():
    assert first_order_angles(first_order_table(.6, .9)) == pytest.approx((.6, .9), abs=1e-3)


def test_a_table_made_by_the_quantum_model_is_predicted_exactly_by_its_sign():
    a, b = .6, .3
    ab = first_order_table(a, b)
    found_a, found_b = first_order_angles(ab)
    assert np.allclose(second_order_from_angles(found_a, found_b, 1), second_order_from_angles(a, b, 1), atol=1e-3)


@pytest.mark.parametrize("sign", (1, -1))
def test_second_order_tables_sum_to_one(sign):
    assert second_order_from_angles(.4, .7, sign).sum() == pytest.approx(1.)


def test_the_best_classical_stays_between_the_known_rates():
    with (Path(__file__).parent / "disjunction.csv").open(encoding="utf-8", newline="") as stream:
        known = {row["study"]: sorted((float(row["known_a"]), float(row["known_b"]))) for row in csv.DictReader(stream)}
    for row in report()[0]:
        assert known[row["study"]][0] <= row["classical_best"] <= known[row["study"]][1]


def test_the_fitted_experiment_is_not_scored():
    one, _, summary = report()
    assert sum(not row["scored"] for row in one) == 2 and summary["test1"]["rows"] == 7


def test_quantum_reproduces_the_experiment_eta_was_solved_from():
    assert next(row for row in report()[0] if row["study"] == "Tversky & Shafir 1992")["quantum"] == pytest.approx(.36, abs=.001)


def test_every_row_counts():
    with (Path(__file__).parent / "question_order.csv").open(encoding="utf-8", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == len(question_order()) == 13

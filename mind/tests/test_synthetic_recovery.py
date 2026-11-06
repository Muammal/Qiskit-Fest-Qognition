"""Audit of Test 2: can contest.py recover a model that really is two-dimensional?

The data here come from cognition_models.luders_sequential_probs, which shares no code
with contest.py, so a convention mismatch between them would fail these tests.
See mind/human_tests/AUDIT_2026-11-06.md.
"""

import numpy as np
import pytest

from mind.cognition_models import luders_sequential_probs
from mind.human_tests.contest import first_order_angles, first_order_table, second_order_from_angles


def tables(theta_psi, theta_a, theta_b):
    probs = luders_sequential_probs(theta_psi, theta_a, theta_b)
    return (np.array([probs[f"AB_{c}"] for c in ("yy", "yn", "ny", "nn")]), np.array([probs[f"BA_{c}"] for c in ("yy", "yn", "ny", "nn")]))


def best_sign_gap(ab, ba):
    a, b = first_order_angles(ab)
    return min(0.5 * float(np.abs(second_order_from_angles(a, b, sign) - ba).sum()) for sign in (1, -1))


def test_exact_tables_are_recovered_by_the_better_sign():
    rng = np.random.default_rng(1)
    for _ in range(25):
        ab, ba = tables(*rng.uniform(0, 2 * np.pi, 3))
        assert best_sign_gap(ab, ba) < 1e-3


def test_sampled_tables_are_recovered_to_within_sampling_noise():
    rng = np.random.default_rng(2)
    gaps = []
    for _ in range(25):
        ab, ba = tables(*rng.uniform(0, 2 * np.pi, 3))
        sample = rng.multinomial(450, ab / ab.sum()) / 450
        gaps.append(best_sign_gap(sample, ba))
    assert np.mean(gaps) < 0.05


def test_the_model_cannot_fit_a_table_that_breaks_its_symmetry():
    """The limit behind Test 2. P(B yes | A yes) must equal P(B no | A no), and Clinton-Gore has .92 and .62."""
    ab = np.array([0.4899, 0.0447, 0.1767, 0.2886])
    a, b = first_order_angles(ab)
    fitted = first_order_table(a, b)
    assert fitted[0] / (fitted[0] + fitted[1]) == pytest.approx(fitted[3] / (fitted[2] + fitted[3]))
    assert 0.5 * np.abs(fitted - ab).sum() > 0.1

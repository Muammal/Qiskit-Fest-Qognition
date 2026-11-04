"""Walking checks against answers known exactly."""
from __future__ import annotations

import math

import numpy as np
import pytest

from stranded_physics.domains.agent.walking import NEIGHBOURS, step_seconds, tobler_speed_m_s, travel_field, walk

DX = 90.


def test_tobler_speed_peaks_on_a_slight_downhill():
    peak = tobler_speed_m_s(-.05)
    assert peak == pytest.approx(6. * .6 / 3.6)
    assert tobler_speed_m_s(0.) == pytest.approx(peak * math.exp(-3.5 * .05))
    assert tobler_speed_m_s(.3) < tobler_speed_m_s(0.) < peak
    assert tobler_speed_m_s(-.3) < peak


def test_flat_ground_time_is_exact_including_diagonals():
    ground = np.zeros((11, 11))
    field = travel_field(ground, np.ones(ground.shape, dtype=bool), (5, 5), DX)
    speed = tobler_speed_m_s(0.)
    assert field.seconds[5, 10] == pytest.approx(5 * DX / speed)
    assert field.seconds[10, 10] == pytest.approx(5 * math.sqrt(2) * DX / speed)
    assert field.seconds[8, 10] == pytest.approx((3 * math.sqrt(2) + 2) * DX / speed)


def test_matches_a_brute_force_best_route_on_random_ground():
    rng = np.random.default_rng(7)
    ground = rng.uniform(0, 150, (8, 8))
    land = rng.random(ground.shape) > .15
    goal = (4, 4)
    land[goal] = True
    best = np.full(ground.shape, np.inf)
    best[goal] = 0.
    for _ in range(ground.size):
        for row in range(8):
            for col in range(8):
                if not land[row, col]:
                    continue
                for d_row, d_col in NEIGHBOURS:
                    r, c = row + d_row, col + d_col
                    if 0 <= r < 8 and 0 <= c < 8 and land[r, c]:
                        run = DX * (math.sqrt(2.) if d_row and d_col else 1.)
                        best[row, col] = min(best[row, col], best[r, c] + step_seconds(float(ground[r, c] - ground[row, col]), run))
    field = travel_field(ground, land, goal, DX)
    assert np.allclose(np.nan_to_num(field.seconds, posinf=-1), np.nan_to_num(best, posinf=-1))


def test_climbing_takes_longer_than_descending_the_same_slope():
    ground = np.tile(np.arange(20.) * 20., (3, 1))
    land = np.ones(ground.shape, dtype=bool)
    assert travel_field(ground, land, (1, 19), DX).seconds[1, 0] > travel_field(ground, land, (1, 0), DX).seconds[1, 19]


def test_water_cannot_be_crossed_and_routes_go_around():
    ground = np.zeros((9, 9))
    land = np.ones(ground.shape, dtype=bool)
    land[:, 4] = False
    assert np.isinf(travel_field(ground, land, (4, 8), DX).seconds[4, 0])
    land[8, 4] = True
    field = travel_field(ground, land, (4, 8), DX)
    assert field.seconds[4, 0] > 8 * DX / tobler_speed_m_s(0.)


def test_walk_uses_exactly_its_time_and_keeps_the_rest():
    ground = np.zeros((1, 21))
    field = travel_field(ground, np.ones(ground.shape, dtype=bool), (0, 20), DX)
    one_cell = DX / tobler_speed_m_s(0.)
    cell, left = walk(field, (0, 0), 3.5 * one_cell, ground.shape)
    assert cell == (0, 3) and left == pytest.approx(.5 * one_cell)
    assert walk(field, (0, 0), 1e6, ground.shape) == ((0, 20), 0.)

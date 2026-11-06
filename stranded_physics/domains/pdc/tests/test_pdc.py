"""Flow checks against answers known exactly."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.pdc.model import GRAVITY_M_S2, SETTINGS, Pdc, energy_reach

DX = 50.0
SIZE = 201
CENTRE = (100, 100)
RATIO = 0.2
HEIGHT = 200.0


def flat() -> np.ndarray:
    return np.zeros((SIZE, SIZE))


def test_reach_on_flat_ground_is_the_energy_cone_radius():
    arrival = energy_reach(flat(), np.ones((SIZE, SIZE), dtype=bool), CENTRE, HEIGHT, RATIO, DX, 0.01)
    limit = HEIGHT / RATIO  # 1000 m.
    east = np.flatnonzero(np.isfinite(arrival[CENTRE[0], CENTRE[1] :])).max() * DX
    assert limit - DX <= east <= limit


def test_travel_time_matches_the_energy_integral():
    """With v = sqrt(2 g ratio (L - s)), the time to the end of a straight run is sqrt(2 L / (g ratio))."""
    arrival = energy_reach(flat(), np.ones((SIZE, SIZE), dtype=bool), CENTRE, HEIGHT, RATIO, DX, 0.01)
    limit = HEIGHT / RATIO
    at_half = arrival[CENTRE[0], CENTRE[1] + 10]  # 500 m out, where the exact time is known from the same integral.
    exact = (2 / math.sqrt(2 * GRAVITY_M_S2 * RATIO)) * (math.sqrt(limit) - math.sqrt(limit - 500.0))
    assert at_half == pytest.approx(exact, rel=0.05)


def test_a_wall_taller_than_the_energy_line_stops_the_flow():
    ground = flat()
    ground[:, CENTRE[1] + 5] = 500.0
    arrival = energy_reach(ground, np.ones((SIZE, SIZE), dtype=bool), CENTRE, HEIGHT, RATIO, DX, 5.0)
    assert np.isinf(arrival[CENTRE[0], CENTRE[1] + 6 :]).all()
    assert np.isfinite(arrival[CENTRE[0], CENTRE[1] - 6])


def test_a_low_gap_lets_the_flow_through_and_takes_longer():
    ground = flat()
    ground[:, CENTRE[1] + 5] = 500.0
    ground[CENTRE[0] + 8, CENTRE[1] + 5] = 0.0
    arrival = energy_reach(ground, np.ones((SIZE, SIZE), dtype=bool), CENTRE, HEIGHT, RATIO, DX, 5.0)
    open_ground = energy_reach(flat(), np.ones((SIZE, SIZE), dtype=bool), CENTRE, HEIGHT, RATIO, DX, 5.0)
    beyond = (CENTRE[0], CENTRE[1] + 7)
    assert np.isfinite(arrival[beyond]) and arrival[beyond] > open_ground[beyond]


def test_flow_only_runs_through_passable_cells():
    passable = np.zeros((SIZE, SIZE), dtype=bool)
    passable[CENTRE[0]] = True
    arrival = energy_reach(flat(), passable, CENTRE, HEIGHT, RATIO, DX, 5.0)
    assert np.isfinite(arrival[CENTRE[0], CENTRE[1] + 3]) and np.isinf(arrival[CENTRE[0] + 1, CENTRE[1]])


def run_domain(explosions: dict[int, float] | None = None, frames: int = 48):
    grid = GridSpec("EPSG:32620", 0.0, 10000.0, DX, SIZE, SIZE)
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200.0, frames)
    store = FieldStore()
    store.put("terrain.elevation", flat() + 1.0, "m", grid)
    store.put("terrain.land_mask", np.ones((SIZE, SIZE)), "dimensionless", grid)
    store.put("terrain.height_above_drainage", flat(), "m", grid)
    explosion = np.zeros(frames)
    for frame, value in (explosions or {}).items():
        explosion[frame] = value
    store.put("eruption.explosion", explosion, "dimensionless", time=axis)
    domain = Pdc(grid, axis, grid.centre(*CENTRE))
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    return store, grid


def test_no_frame_shows_a_flow_before_the_published_first_collapse():
    store, _ = run_domain()
    active = store.stored("pdc.active").data
    first_frame = math.ceil(SETTINGS["first_collapse_after_axis_start"] / 7200.0)
    assert active[:first_frame].sum() == 0 and active[first_frame].sum() > 0


def test_arrival_starts_at_the_first_collapse():
    store, _ = run_domain()
    arrival = store.stored("pdc.arrival").data
    assert arrival[CENTRE] == SETTINGS["first_collapse_after_axis_start"]
    assert np.isfinite(arrival).any() and (arrival[np.isfinite(arrival)] >= SETTINGS["first_collapse_after_axis_start"]).all()


def test_explosions_before_the_first_collapse_make_no_flow_and_later_ones_do():
    store, _ = run_domain({10: 1.0, 40: 1.0})
    active = store.stored("pdc.active").data
    assert active[10].sum() == 0 and active[40].sum() > 0


def test_an_axis_ending_before_the_first_collapse_has_no_flow():
    store, _ = run_domain(frames=20)
    assert store.stored("pdc.active").data.sum() == 0 and np.isinf(store.stored("pdc.arrival").data).all()

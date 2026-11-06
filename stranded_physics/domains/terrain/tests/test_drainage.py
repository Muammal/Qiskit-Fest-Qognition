"""Drainage checks against answers known exactly."""
from __future__ import annotations

import numpy as np
import pytest

from stranded_physics.domains.terrain.drainage import OUTLET, flow_accumulation, height_above_drainage, route, share_draining_out

DX = 90.
ROWS, COLS, MIDDLE = 40, 21, 10
SIDE_SLOPE, TILT = .30, .02


def tilted_v() -> tuple[np.ndarray, np.ndarray]:
    """A V-shaped valley, with its channel down the middle column, falling toward the last row, which is the sea."""
    rows, cols = np.mgrid[0:ROWS, 0:COLS]
    elevation = 200. + (ROWS - rows) * DX * TILT + np.abs(cols - MIDDLE) * DX * SIDE_SLOPE
    land = np.ones(elevation.shape, dtype=bool)
    land[-1] = False
    elevation[-1] = 0.
    return elevation, land


def test_tilted_v_contributing_area_is_exact():
    """Side slopes beat the tilt, so each row's cells enter the channel at that row, and the channel gathers full rows."""
    elevation, land = tilted_v()
    area = flow_accumulation(route(elevation, land, DX), land, DX)
    # Border columns are outlets by rule, so each interior row feeds the channel with COLS - 2 cells. Row 0 is all outlets.
    # The row beside the sea is left out, because its side cells drain straight into the sea.
    for row in range(1, ROWS - 2):
        assert area[row, MIDDLE] == pytest.approx(row * (COLS - 2) * DX ** 2)


def test_filled_pit_is_raised_to_its_spill_height_and_drains():
    elevation, land = tilted_v()
    elevation[20, MIDDLE] -= 80.  # A deep pit in the channel.
    drainage = route(elevation, land, DX)
    assert drainage.filled[20, MIDDLE] > elevation[20, MIDDLE] + 50.
    assert share_draining_out(drainage, land) == 1.
    assert drainage.filled[elevation.shape[0] - 2, MIDDLE] == pytest.approx(elevation[elevation.shape[0] - 2, MIDDLE])  # Downstream is left alone.


def test_routing_has_no_cycles_and_always_goes_down():
    rng = np.random.default_rng(3)
    elevation = rng.uniform(0, 300, (30, 30))
    land = np.ones(elevation.shape, dtype=bool)
    drainage = route(elevation, land, DX)
    flat = drainage.filled.ravel()
    moving = drainage.receivers != OUTLET
    assert (flat[moving] > flat[drainage.receivers[moving]]).all()
    assert share_draining_out(drainage, land) == 1.


def test_area_is_conserved_at_the_outlets():
    rng = np.random.default_rng(4)
    elevation = rng.uniform(1, 300, (25, 25))
    land = np.ones(elevation.shape, dtype=bool)
    drainage = route(elevation, land, DX)
    area = flow_accumulation(drainage, land, DX)
    at_outlets = area.ravel()[drainage.receivers == OUTLET].sum()
    assert at_outlets == pytest.approx(land.sum() * DX ** 2)


def test_height_above_drainage_equals_side_rise():
    elevation, land = tilted_v()
    drainage = route(elevation, land, DX)
    area = flow_accumulation(drainage, land, DX)
    height = height_above_drainage(elevation, drainage, area, channel_area_m2=12 * DX ** 2)  # More than any side slope gathers.
    assert height[20, MIDDLE] == 0.
    assert height[20, MIDDLE + 3] == pytest.approx(3 * DX * SIDE_SLOPE)
    assert (height >= 0).all()

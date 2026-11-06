"""Mudflow checks against answers known exactly."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.lahar.model import SETTINGS, Lahar, inundate, planimetric_area_m2

DX = 90.0
SIZE = 61
FRAMES = 12
GRID = GridSpec("EPSG:32620", 0.0, 10000.0, DX, SIZE, SIZE)
AXIS = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200.0, FRAMES)
VENT = GRID.centre(30, 30)
CHANNEL_AREA = 5e6


def run_domain(rain, ash):
    store = FieldStore()
    side = np.abs(np.arange(SIZE) - 30.0) * 10.0
    store.put("terrain.land_mask", np.ones((SIZE, SIZE)), "dimensionless", GRID)
    store.put("terrain.height_above_drainage", np.tile(side, (SIZE, 1)), "m", GRID)
    accumulation = np.full((SIZE, SIZE), 1e4)
    accumulation[:, 30] = CHANNEL_AREA
    store.put("terrain.flow_accumulation", accumulation, "m**2", GRID)
    store.put("atmos.rain_rate", np.asarray(rain, dtype=float), "mm/h", time=AXIS)
    store.put("tephra.deposit_load", np.full((FRAMES, SIZE, SIZE), 1.0) * np.asarray(ash, dtype=float)[:, None, None], "kg/m**2", GRID, AXIS)
    domain = Lahar(GRID, AXIS, VENT)
    budget = domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    return store.stored("lahar.depth").data, budget


WET = np.full(FRAMES, 20.0)
DRY = np.zeros(FRAMES)
ASHY = np.full(FRAMES, 10.0)
CLEAN = np.zeros(FRAMES)


def test_laharz_area_scales_with_volume_to_two_thirds():
    assert planimetric_area_m2(1e6) == pytest.approx(200.0 * 1e4)
    assert planimetric_area_m2(8e6) == pytest.approx(4 * planimetric_area_m2(1e6))


def test_inundation_area_and_volume_are_exact_and_start_in_the_channel():
    height = np.tile(np.abs(np.arange(101) - 50.0), (101, 1))
    volume = 1e4
    depth = inundate(height, np.ones(height.shape, dtype=bool), volume, 10.0)
    assert np.count_nonzero(depth) == round(planimetric_area_m2(volume) / 100.0)
    assert depth.sum() * 100.0 == pytest.approx(volume)
    assert height[depth > 0].max() < height[depth == 0].min() + 1e-9


def test_no_rain_or_no_ash_means_no_mudflow():
    assert run_domain(DRY, ASHY)[0].sum() == 0
    assert run_domain(WET, CLEAN)[0].sum() == 0


def test_rain_on_ash_makes_a_mudflow_that_keeps_its_volume():
    depth, budget = run_domain(WET, ASHY)
    assert depth.sum() > 0
    assert budget["volume_m3"] < 1e-9
    expected = 20.0 / 1000.0 * 2.0 * CHANNEL_AREA * SETTINGS["bulking"]
    assert depth[3].sum() * DX**2 == pytest.approx(expected)


def test_a_mudflow_starts_only_once_ash_has_landed_and_rain_is_falling():
    ash = CLEAN.copy()
    ash[6:] = 10.0
    rain = DRY.copy()
    rain[8] = 20.0
    depth, _ = run_domain(rain, ash)
    assert depth[:8].sum() == 0 and depth[8].sum() > 0 and depth[9:].sum() == 0


def test_rain_below_the_threshold_does_nothing():
    assert run_domain(np.full(FRAMES, SETTINGS["rain_threshold_mm_h"] * 0.99), ASHY)[0].sum() == 0

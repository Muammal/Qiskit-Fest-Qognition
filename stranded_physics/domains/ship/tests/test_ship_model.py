from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.ship.model import (
    Boats, Breach, SETTINGS, Ship, ShipDeck, _attitude, _geometry, _overflow,
    even_breach, flood, inflow_m3_s, make_ship, titanic_boats, titanic_breach, titanic_ship,
)


def box(**changes):
    arguments = dict(length_m=100., beam_m=20., draught_m=5., displacement_t=10000.,
                     compartments=4, bulkhead_top_m=3., boat_deck_m=10.)
    return make_ship(**(arguments | changes))


def test_records_and_dimensions():
    ship = titanic_ship()
    assert len(ship.compartments) == 16
    assert sum(c.length_m for c in ship.compartments) == pytest.approx(ship.length_m)
    assert ship.compartments[-1].length_m == pytest.approx(39.5 * .3048)
    breach = titanic_breach()
    assert sum(breach.areas_m2) == pytest.approx(12 * .3048**2)
    assert np.count_nonzero(breach.areas_m2) == 6
    assert np.ptp(np.array(breach.areas_m2[:6]) /
                  np.array([c.length_m for c in ship.compartments[:6]])) < 1e-15
    boats = titanic_boats()
    assert len(boats) == 20 and sum(b.capacity for b in boats) == 1178
    assert next(b for b in boats if b.name == "No. 7").launch_minutes == 65
    assert {b.name for b in boats if not b.from_record} == {"A", "B"}


@pytest.mark.parametrize("head", [-10., 0.])
def test_nonpositive_head_stops_flow(head):
    assert inflow_m3_s(2., head) == 0


def test_orifice_scaling_and_errors():
    assert inflow_m3_s(2., 16.) == pytest.approx(4 * inflow_m3_s(1., 4.))
    for area, head in [(-1, 2), (1, np.nan), (np.inf, 1)]:
        with pytest.raises(InterfaceError):
            inflow_m3_s(area, head)


def test_intact_and_symmetric_hulls():
    ship = box()
    intact = flood(ship, even_breach(ship, 0, 1, 0.), 120., 7.)
    assert intact.times_s[-1] == 120.
    assert not intact.water_t.any() and intact.foundered_s is None
    symmetric = flood(ship, even_breach(ship, 0, 4, 1.), 120.)
    assert np.allclose(symmetric.draught_bow_m, symmetric.draught_stern_m)
    assert np.all(np.diff(symmetric.water_t.sum(axis=1)) >= 0)
    expected_sink = symmetric.water_t.sum(axis=1) * 1000 / SETTINGS["water_density"] / 2000
    np.testing.assert_allclose(symmetric.draught_bow_m - 5, expected_sink, atol=1e-14)


def test_single_compartment_analytic_fill():
    ship = box(compartments=1, bulkhead_top_m=100., boat_deck_m=100.)
    area, duration = .5, 120.
    result = flood(ship, Breach((area,)), duration)
    plane = ship.length_m * ship.beam_m
    storage = plane * SETTINGS["permeability"]
    coefficient = 1 / storage - 1 / plane
    root = np.sqrt(SETTINGS["hole_depth_below_waterline"])
    rate = SETTINGS["discharge_coefficient"] * area * np.sqrt(2 * SETTINGS["gravity"])
    volume = (root**2 - (root - coefficient * rate * duration / 2)**2) / coefficient
    assert result.water_t[-1, 0] == pytest.approx(volume * SETTINGS["water_density"] / 1000, rel=2e-5)


def test_bulkhead_conservation_and_direction():
    ship = box(compartments=3, bulkhead_top_m=0., displacement_t=1e12)
    edges, centres, storage = _geometry(ship)
    volumes = np.array([storage[0] * (SETTINGS["hole_depth_below_waterline"] + 2), 0., 0.])
    before = volumes.sum()
    _overflow(ship, volumes, edges, centres, storage)
    assert volumes.sum() == pytest.approx(before, rel=1e-15)
    assert volumes[1] > 0 and volumes[2] == 0
    assert np.min(volumes) >= 0
    closed = box(compartments=3, bulkhead_top_m=100., displacement_t=1e12)
    unchanged = np.array([100., 0., 0.])
    _overflow(closed, unchanged, edges, centres, storage)
    np.testing.assert_array_equal(unchanged, [100, 0, 0])


def test_trim_follows_flood_moment():
    ship = box()
    bow = flood(ship, even_breach(ship, 0, 1, .5), 100.)
    stern = flood(ship, even_breach(ship, 3, 1, .5), 100.)
    assert bow.draught_bow_m[-1] > bow.draught_stern_m[-1]
    np.testing.assert_allclose(bow.draught_bow_m, stern.draught_stern_m)
    _, centres, _ = _geometry(ship)
    volumes = bow.water_t[-1] * 1000 / SETTINGS["water_density"]
    sink, slope = _attitude(ship, volumes, centres)
    gml = ship.length_m**2 / (12 * ship.draught_m)
    expected_slope = (bow.water_t[-1] @ centres) / ((ship.displacement_t + bow.water_t[-1].sum()) * gml)
    assert slope == pytest.approx(expected_slope)
    assert sink > 0 and slope < 0


def test_foundering_and_first_crossing():
    ship = box(boat_deck_m=.1)
    breach = even_breach(ship, 0, 1, 2.)
    result = flood(ship, breach, 60., .5)
    assert result.foundered_s is not None
    index = np.searchsorted(result.times_s, result.foundered_s)
    assert result.draught_bow_m[index] >= ship.draught_m + .1
    assert result.draught_bow_m[index-1] < ship.draught_m + .1
    assert flood(replace(ship, displacement_t=0), breach, 1.).water_t[-1].sum() > 0


def test_grid_domain_fields_and_causal_offset_impact():
    grid = GridSpec("local", 100, 200, 10, 12, 6)
    time = TimeAxis(datetime(2026, 1, 1, tzinfo=timezone.utc), 10., 5)
    ship = box(length_m=80., beam_m=20., boat_deck_m=10.)
    breach = even_breach(ship, 0, 1, .5)
    fields = FieldStore()
    terrain = ShipDeck(grid, ship)
    terrain.run(ScopedFields(fields, terrain.id, terrain.inputs, terrain.outputs), np.random.default_rng(0))
    mask = fields.get("terrain.land_mask", "dimensionless")
    assert mask.sum() == 16
    np.testing.assert_array_equal(fields.get("terrain.elevation", "m"), mask)
    for name in ("zone", "land_cover", "flow_accumulation", "height_above_drainage"):
        assert not fields.stored("terrain." + name).data.any()
    domain = Ship(grid, time, ship, breach, 12., 21.)
    domain.run(ScopedFields(fields, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    np.testing.assert_array_equal(fields.get("ship.impact", "dimensionless"), [0, 0, 1, 0, 0])
    np.testing.assert_array_equal(fields.get("ship.alarm", "dimensionless"), [0, 0, 0, 1, 1])
    water = fields.get("ship.water_mass", "kg")
    assert not water[:2].any()
    assert water[2] == pytest.approx(flood(ship, breach, 8.).water_t[-1].sum() * 1000)
    short = Ship(grid, replace(time, n=3), ship, breach, 12., 21.)
    prefix = FieldStore()
    short.run(prefix, np.random.default_rng(1))
    np.testing.assert_array_equal(water[:3], prefix.get("ship.water_mass", "kg"))


def test_foundered_submerges_every_cell_and_boats_aggregate():
    grid = GridSpec("local", -50, 30, 10, 10, 6)
    time = TimeAxis(datetime.now(timezone.utc), 10., 4)
    ship = box(boat_deck_m=0.)
    fields = FieldStore()
    Ship(grid, time, ship, even_breach(ship, 0, 1, 0), 11., 0).run(fields, np.random.default_rng(1))
    np.testing.assert_array_equal(fields.get("ship.afloat", "dimensionless"), [1, 1, 0, 0])
    frames = fields.get("ship.submerged", "dimensionless")
    assert not frames[:2].any() and frames[2:].all()
    boats = Boats(grid, [((0, 0), 40, 60.), ((1, -1), 65, 50.)])
    boats.run(fields, np.random.default_rng(1))
    seats = fields.get("boats.capacity", "dimensionless")
    launch = fields.get("boats.launch", "s")
    assert seats.sum() == 105 and np.count_nonzero(seats) == 1
    assert launch[grid.locate((0, 0))] == 50
    assert np.isinf(launch[seats == 0]).all()


@pytest.mark.parametrize("changes", [dict(length_m=0), dict(beam_m=-1), dict(draught_m=np.nan),
                                     dict(displacement_t=-1), dict(compartments=2.5), dict(bulkhead_top_m=-1)])
def test_invalid_geometry_raises(changes):
    with pytest.raises(InterfaceError):
        box(**changes)


def test_invalid_breaches_and_times_raise():
    ship = box()
    for args in [(-1, 1, 1), (0, 0, 1), (3, 2, 1), (0, 1, -1)]:
        with pytest.raises(InterfaceError):
            even_breach(ship, *args)
    for end, dt in [(-1, 1), (1, 0), (np.inf, 1)]:
        with pytest.raises(InterfaceError):
            flood(ship, even_breach(ship, 0, 1, 1), end, dt)
    with pytest.raises(InterfaceError):
        flood(ship, Breach((1.,)), 1)

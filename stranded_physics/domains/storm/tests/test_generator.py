from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.storm import generator as gen
from stranded_physics.domains.storm.model import Storm, great_circle_m, holland_wind_m_s, SETTINGS


def generate(seed=42, site=(-61., 13.), **dials):
    return gen.generate(np.random.default_rng(seed), site, 72 * 3600., **dials)


def test_seed_and_all_dial_overrides():
    one, two = generate(), generate()
    np.testing.assert_array_equal(one.track, two.track)
    assert (one.max_wind_m_s, one.closest_s, one.rmax_m) == (two.max_wind_m_s, two.closest_s, two.rmax_m)
    assert not one.track.flags.writeable
    event = generate(max_wind_m_s=60., closest_km=80., bearing_deg=90., speed_m_s=7., rmax_m=20000., closest_s=7200.)
    assert (event.max_wind_m_s, event.closest_km, event.bearing_deg, event.speed_m_s,
            event.rmax_m, event.closest_s) == (60., 80., 90., 7., 20000., 7200.)
    assert (event.track[:, 3] == 60.).all() and (event.track[:, 4] == 20000.).all()
    assert one.track[0, 0] < 0 and one.track[-1, 0] > 72 * 3600.
    np.testing.assert_allclose(np.diff(one.track[:, 0]), 3600., atol=1e-9)
    for seed in range(20):
        event = generate(seed)
        assert .25 * 72 * 3600 <= event.closest_s <= .75 * 72 * 3600


@pytest.mark.parametrize("dials", [dict(max_wind_m_s=-1), dict(max_wind_m_s=151),
    dict(closest_km=-1), dict(closest_km=2001), dict(bearing_deg=-1), dict(bearing_deg=361),
    dict(speed_m_s=0), dict(speed_m_s=31), dict(rmax_m=0), dict(rmax_m=200001),
    dict(closest_s=-1), dict(closest_s=72 * 3600 + 1), dict(max_wind_m_s=np.nan)])
def test_invalid_dials_are_refused(dials):
    with pytest.raises(InterfaceError):
        generate(**dials)


@pytest.mark.parametrize("site", [(181., 0), (0, -91.), (np.nan, 0), (0,), (0, 1, 2)])
def test_invalid_site_is_refused(site):
    with pytest.raises(InterfaceError):
        generate(site=site)


@pytest.mark.parametrize("axis", [-1, 0, np.inf, [1, 2], [0, 0], [0, np.nan], [[0, 1]]])
def test_invalid_axis_is_refused(axis):
    with pytest.raises(InterfaceError):
        gen.generate(np.random.default_rng(1), (0, 0), axis)


@pytest.mark.parametrize("site", [(-61., 13.), (179.9, 70.), (-179.9, -70.), (0., 90.)])
@pytest.mark.parametrize("bearing", [0., 90., 213., 360.])
@pytest.mark.parametrize("distance", [0., 80., 2000.])
def test_spherical_closest_pass_and_constant_speed(site, bearing, distance):
    event = generate(site=site, closest_km=distance, bearing_deg=bearing, speed_m_s=30., closest_s=12345.67)
    track = event.track
    distances = great_circle_m(site, track[:, 2], track[:, 1]) / 1000
    assert distances.min() == pytest.approx(distance, abs=1.)
    k = np.argmin(np.abs(track[:, 0] - event.closest_s))
    assert track[k, 0] == event.closest_s
    # Independent chord-angle distances between successive 3D unit vectors.
    lat, lon = np.deg2rad(track[:, 1]), np.deg2rad(track[:, 2])
    xyz = np.column_stack((np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))
    angles = 2 * np.arcsin(np.linalg.norm(np.diff(xyz, axis=0), axis=1) / 2)
    np.testing.assert_allclose(angles * SETTINGS["earth_radius"], np.diff(track[:, 0]) * 30., rtol=1e-11)
    probe = np.array([event.closest_s - 17., event.closest_s, event.closest_s + 17.])
    lat, lon, _, _ = gen.interpolate_track(track, probe)
    assert great_circle_m(site, lon[1], lat[1]) / 1000 == pytest.approx(distance, abs=1e-8)


def test_generated_domain_relative_time_holland_and_prefix(monkeypatch):
    import stranded_physics.domains.storm.model as model
    monkeypatch.setattr(model, "default_files", lambda: pytest.fail("generated path loaded replay files"))
    site = (179.9, 70.)
    event = generate(site=site, max_wind_m_s=60., closest_km=30., rmax_m=30000., closest_s=7200.)
    axis = TimeAxis(datetime(2032, 1, 1, tzinfo=timezone.utc), 300., 49)
    domain, store = Storm(axis, site, generated=event), FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    winds = store.get("storm.max_wind", "m/s")
    assert winds[24] == pytest.approx(60.)
    moments = np.arange(axis.n) * axis.dt_s
    # Right spherical triangle: cos(distance/R) = cos(cross_track/R) cos(along_track/R).
    distance = SETTINGS["earth_radius"] * np.arccos(np.cos(30000. / SETTINGS["earth_radius"])
               * np.cos((moments - event.closest_s) * event.speed_m_s / SETTINGS["earth_radius"]))
    expected = holland_wind_m_s(distance, 60., 30000., SETTINGS["holland_b"])
    np.testing.assert_allclose(winds, expected, rtol=1e-10)
    short = Storm(TimeAxis(axis.t0_utc, axis.dt_s, 12), site, generated=event)
    prefix = FieldStore()
    short.run(ScopedFields(prefix, short.id, short.inputs, short.outputs), np.random.default_rng(2))
    np.testing.assert_array_equal(prefix.get("storm.max_wind", "m/s"), winds[:12])
    bad_track = event.track.copy()
    bad_track[0, 4] = 0
    with pytest.raises(InterfaceError):
        Storm(axis, site, generated=replace(event, track=bad_track)).run(FieldStore(), np.random.default_rng(1))


def test_training_split_excludes_poisoned_holdout(tmp_path, monkeypatch):
    path = tmp_path / "storms.csv"
    path.write_text("season,max_wind_kt,closest_km\n2004,40,20\n2004,40,20\n2003,60,30\n2005,poison,poison\n", encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(gen, "CATALOG", path)
        gen.training_catalog.cache_clear()
        gen.wind_catalog.cache_clear()
        assert gen.wind_catalog(2005) == (40 * gen.KNOTS_TO_MS, 40 * gen.KNOTS_TO_MS, 60 * gen.KNOTS_TO_MS)
        assert gen.wind_catalog(2004) == (60 * gen.KNOTS_TO_MS,)
        with pytest.raises(InterfaceError):
            gen.sample_max_wind_m_s(np.random.default_rng(1), before_season=2006)
    gen.training_catalog.cache_clear()
    gen.wind_catalog.cache_clear()

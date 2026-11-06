import csv
from datetime import datetime, timezone
import hashlib

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.storm.model import (
    KNOTS_TO_MS, NAUTICAL_MILES_TO_M, SETTINGS, Storm, great_circle_m, holland_wind_m_s,
)
from stranded_physics.domains.storm.measure import cyclone_rate


def test_holland_peak_origin_and_limits():
    assert holland_wind_m_s(0., 60., 30000., 1.5) == 0
    assert holland_wind_m_s(30000., 60., 30000., 1.5) == pytest.approx(60.)
    radii = np.geomspace(1e-200, 1e10, 200)
    speeds = holland_wind_m_s(radii, 60., 30000., 1.5)
    assert np.isfinite(speeds).all()
    assert ((speeds >= 0) & (speeds <= 60)).all()
    for args in [(-1., 60., 30000., 1.5), (1., 60., 0., 1.5), (1., 60., 1., 0.)]:
        with pytest.raises(InterfaceError):
            holland_wind_m_s(*args)


def test_great_circle_uses_spherical_geometry():
    assert great_circle_m((0., 0.), 90., 0.) == pytest.approx(np.pi * 6371000 / 2)
    assert great_circle_m((179., 0.), -179., 0.) == pytest.approx(2 * np.pi / 180 * 6371000)
    assert great_circle_m((-61., 13.), -61., 13.) == 0


def fixture_track(tmp_path):
    path = tmp_path / "track.csv"
    path.write_text("ISO_TIME,LAT,LON,USA_WIND,USA_RMW\n"
                    "2024-07-01 00:00:00,13,-61,40,20\n"
                    "2024-07-01 01:00:00,80,80, ,10\n"
                    "2024-07-01 01:30:00,80,80,100, \n"
                    "2024-07-01 02:00:00,15,-59,80,40\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_track_interpolation_missing_fixes_and_outside_zero(tmp_path):
    path, sha = fixture_track(tmp_path)
    axis = TimeAxis(datetime(2024, 6, 30, 23, tzinfo=timezone.utc), 3600., 5)
    model = Storm(axis, (-61.2, 13.2), {"track": (path, sha)})
    store = FieldStore()
    fields = ScopedFields(store, model.id, model.inputs, model.outputs)
    assert model.check_validity(fields) == []
    model.run(fields, np.random.default_rng(1))
    values = store.get("storm.max_wind", "m/s")
    assert values[0] == values[-1] == 0
    distance = great_circle_m((-61.2, 13.2), -60., 14.)
    assert values[2] == pytest.approx(holland_wind_m_s(distance, 60 * KNOTS_TO_MS,
                                                      30 * NAUTICAL_MILES_TO_M, SETTINGS["holland_b"]))
    other = FieldStore()
    model.run(ScopedFields(other, model.id, model.inputs, model.outputs), np.random.default_rng(80))
    np.testing.assert_array_equal(other.get("storm.max_wind", "m/s"), values)


def test_track_validity_rejects_missing_hash_and_bad_axis(tmp_path):
    path, sha = fixture_track(tmp_path)
    axis = TimeAxis(datetime(2024, 7, 1, tzinfo=timezone.utc), 3600., 4)
    assert Storm(axis, (0., 0.), {"track": (path, "0" * 64)}).check_validity(None)
    assert Storm(axis, (0., 0.), {"track": (tmp_path / "missing", sha)}).check_validity(None)
    assert Storm(axis, (0., 100.), {"track": (path, sha)}).check_validity(None)
    assert Storm(TimeAxis(axis.t0_utc, -1., 4), (0., 0.), {"track": (path, sha)}).check_validity(None)


def test_named_catalog_rate_deduplicates_and_keeps_zero_years(tmp_path):
    path = tmp_path / "catalog.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["island", "sid", "season", "name", "closest_km"])
        writer.writerows([("st_vincent", "a", 1980, "ALLEN", 30),
                          ("st_vincent", "a", 1980, "ALLEN", 30),
                          ("st_vincent", "b", 1981, "UNNAMED", 50),
                          ("st_vincent", "c", 2025, "NAMED", 200),
                          ("st_vincent", "d", 2026, "INCOMPLETE", 20),
                          ("st_vincent", "e", 2024, "DISTANT", 201),
                          ("montserrat", "f", 2024, "OTHER", 20)])
    result = cyclone_rate(path)
    assert result["storms_per_year"] == pytest.approx(2 / 46)
    assert result["first_year"] == 1980
    assert result["last_year"] == 2025
    assert result["radius_km"] == 200

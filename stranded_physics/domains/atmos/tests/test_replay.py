import hashlib
import json
from datetime import datetime, timezone

import numpy as np

from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.atmos.model import Atmos


def fixture_files(tmp_path):
    times = [f"2021-04-08T{hour:02d}:00" for hour in range(6)]
    surface = {"time": times, "precipitation": [1, 4, 8, 20, 100, 200],
               "wind_speed_10m": [36] * 6, "wind_direction_10m": [350] * 6, "temperature_2m": [25] * 6}
    upper = {"time": times, "wind_speed_500hPa": [72] * 6, "wind_direction_500hPa": [0] * 6,
             "wind_speed_200hPa": [108] * 6, "wind_direction_200hPa": [250] * 6}
    files = {}
    for role, hourly in (("surface", surface), ("upper", upper)):
        path = tmp_path / (role + ".json")
        path.write_text(json.dumps({"hourly": hourly}), encoding="utf-8")
        files[role] = path, hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def test_exact_instant_winds_and_completed_rain_hours(tmp_path):
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200., 3)
    domain = Atmos(axis, fixture_files(tmp_path))
    store = FieldStore()
    assert not domain.check_validity(None)
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    np.testing.assert_array_equal(store.get("atmos.rain_rate", "mm/h"), [1, 6, 60])
    np.testing.assert_array_equal(store.get("atmos.wind_speed", "m/s"), [10] * 3)
    np.testing.assert_array_equal(store.get("atmos.wind_bearing", "degree"), [170] * 3)
    np.testing.assert_array_equal(store.get("atmos.wind_bearing_200hpa", "degree"), [70] * 3)


def test_missing_hash_uncovered_and_subhour_rejected(tmp_path):
    files = fixture_files(tmp_path)
    start = datetime(2021, 4, 8, tzinfo=timezone.utc)
    assert Atmos(TimeAxis(start, 3600., 7), files).check_validity(None)
    assert Atmos(TimeAxis(start, 1800., 3), files).check_validity(None)
    path, _ = files["upper"]
    files["upper"] = path, "0" * 64
    assert any("sha256" in r for r in Atmos(TimeAxis(start, 3600., 1), files).check_validity(None))
    path.unlink()
    assert any("missing" in r for r in Atmos(TimeAxis(start, 3600., 1), files).check_validity(None))

from datetime import datetime, timezone
import numpy as np
import pytest
from stranded_physics.core.api import GridSpec, TimeAxis, InterfaceError
from stranded_physics.core.fields import FieldStore


def setup():
    return GridSpec("EPSG:32620", -150.0, 150.0, 100.0, 3, 3), TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 60.0, 3)


from stranded_physics.domains.gas.model import Gas, SETTINGS, briggs_sigmas_m, ground_concentration_ug_m3, so2_rate_kg_s


def test_formula_and_reflection():
    sy, sz = briggs_sigmas_m(1000.0)
    assert sy == pytest.approx(0.08 * 1000 / np.sqrt(1.1))
    assert sz == pytest.approx(0.06 * 1000 / np.sqrt(2.5))
    expected = 1e9 / (np.pi * 5 * sy * sz) * np.exp(-(100**2) / (2 * sz**2))
    assert ground_concentration_ug_m3(1, 1000, 0, 100, 5) == pytest.approx(expected)
    assert ground_concentration_ug_m3(1, -1, 0, 100, 5) == 0
    assert ground_concentration_ug_m3(1, 1000, 20, 100, 5) == ground_concentration_ug_m3(1, 1000, -20, 100, 5)
    with pytest.raises(InterfaceError):
        ground_concentration_ug_m3(1, 1000, 0, 100, 0)


def test_direction_calm_and_causality():
    grid, time = setup()
    outputs = []
    for last in (0.0, 1e7):
        store = FieldStore()
        for name, data, unit in (
            ("eruption.phase", [1, 1, 2], "dimensionless"),
            ("eruption.mass_rate", [0, 0, last], "kg/s"),
            ("atmos.wind_speed", [0, 0, 0], "m/s"),
            ("atmos.wind_bearing", [90, 90, 90], "degree"),
        ):
            store.put(name, np.array(data), unit, time=time)
        Gas(grid, time, (0, 0)).run(store, np.random.default_rng(2))
        outputs.append(store.get("gas.so2_concentration", "ug/m**3"))
    np.testing.assert_array_equal(outputs[0][:2], outputs[1][:2])
    assert outputs[0][0, 1, 2] > 0
    assert outputs[0][0, 1, 0] == 0
    assert so2_rate_kg_s(0, 1e9) == 0
    assert so2_rate_kg_s(1, 0) == SETTINGS["peak_so2_flux"]

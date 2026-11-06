from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.sea.model import (
    SETTINGS,
    Sea,
    immersion_death_probability,
    incapacitation_median_minutes,
    titanic_sea_temperature_c,
)


def test_exact_medians_and_lifebelt_shift():
    for temperature in (-5, -2, 0, 10, 40):
        median = incapacitation_median_minutes(temperature)
        assert immersion_death_probability(median, temperature, False) == pytest.approx(0.5)
        assert immersion_death_probability(median * SETTINGS["lifebelt_factor"], temperature) == pytest.approx(0.5)
        assert immersion_death_probability(0, temperature) == 0
    assert incapacitation_median_minutes(SETTINGS["freezing_point"]) == SETTINGS["incapacitation_median_at_freezing"]


def test_time_temperature_and_flotation_monotonicity():
    times = np.geomspace(0.01, 10000.0, 100)
    for temperature in (-5.0, 0.0, 10.0, 40.0):
        probabilities = np.array([immersion_death_probability(t, temperature) for t in times])
        assert np.all(np.diff(probabilities) >= 0)
        assert np.all((0 <= probabilities) & (probabilities <= 1))
        assert all(immersion_death_probability(t, temperature) <= immersion_death_probability(t, temperature, False) for t in times)
    assert incapacitation_median_minutes(-5) < incapacitation_median_minutes(40)
    assert immersion_death_probability(20, -2) > immersion_death_probability(20, 20)


@pytest.mark.parametrize("temperature", [-5.001, 40.001, np.nan, np.inf])
def test_invalid_temperature(temperature):
    with pytest.raises(InterfaceError):
        incapacitation_median_minutes(temperature)
    with pytest.raises(InterfaceError):
        immersion_death_probability(0, temperature)


@pytest.mark.parametrize("minutes", [-0.001, np.nan, np.inf])
def test_invalid_duration(minutes):
    with pytest.raises(InterfaceError):
        immersion_death_probability(minutes, 0)


def test_constant_field_and_repeatability():
    axis = TimeAxis(datetime.now(timezone.utc), 3.0, 9)
    sea = Sea(axis, titanic_sea_temperature_c())
    results = []
    for seed in (1, 100):
        fields = FieldStore()
        sea.run(ScopedFields(fields, sea.id, sea.inputs, sea.outputs), np.random.default_rng(seed))
        results.append(fields.get("sea.temperature", "degC"))
    np.testing.assert_array_equal(results[0], np.full(9, -2.0))
    np.testing.assert_array_equal(*results)
    with pytest.raises(InterfaceError):
        Sea(TimeAxis(datetime.now(timezone.utc), 0.0, 2), 0.0)

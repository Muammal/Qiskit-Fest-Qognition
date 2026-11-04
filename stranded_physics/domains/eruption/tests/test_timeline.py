from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.eruption.model import Eruption, mastin_mass_rate_kg_s, mtt_height_m, read_events


def run(axis, seed):
    domain = Eruption(axis)
    store = FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(seed))
    return {name: store.stored(name).data for name in store.names()}


def test_arbitrary_axis_event_and_phase_boundaries():
    axis = TimeAxis(datetime(2021, 4, 9, 12, 40, tzinfo=timezone.utc), 60., 4)
    result = run(axis, 1)
    np.testing.assert_array_equal(result["eruption.explosion"], [0, 1, 0, 0])
    np.testing.assert_array_equal(result["eruption.phase"], [1, 2, 2, 2])
    assert result["eruption.column_height"][0] == 0
    assert (result["eruption.column_height"][1:] > 0).all()
    assert not result["eruption.gas"][1:].any()


def test_96_hour_axis_and_prefix_are_honoured():
    start = datetime(2021, 4, 8, tzinfo=timezone.utc)
    long = run(TimeAxis(start, 3600., 97), 1)
    short = run(TimeAxis(start, 3600., 20), 1)
    for name in ("phase", "column_height", "explosion", "mass_rate", "gas", "tremor"):
        np.testing.assert_array_equal(short["eruption." + name], long["eruption." + name][:20])
    for epoch, _, _ in read_events():
        k = int(np.ceil((epoch - start.timestamp()) / 3600))
        assert long["eruption.explosion"][k] == 1
    assert long["eruption.explosion"][93] == 1  # 11 April 20:22 survives beyond the default axis.


def test_seed_changes_only_precursors():
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 3600., 96)
    one, two = run(axis, 1), run(axis, 20)
    for name in ("phase", "column_height", "explosion", "mass_rate"):
        np.testing.assert_array_equal(one["eruption." + name], two["eruption." + name])
    for name in ("gas", "tremor"):
        assert not one["eruption." + name][:12].any()
        assert not one["eruption." + name][37:].any()
    assert not np.array_equal(one["eruption.tremor"], two["eruption.tremor"])


def test_physical_scalings_and_invalid_inputs():
    assert mastin_mass_rate_kg_s(2000.) == pytest.approx(2500.)
    assert mastin_mass_rate_kg_s(0.) == 0
    assert mtt_height_m(16., 1.) == pytest.approx(10.)
    with pytest.raises(InterfaceError):
        mastin_mass_rate_kg_s(-1.)
    with pytest.raises(InterfaceError):
        mtt_height_m(1., 0.)

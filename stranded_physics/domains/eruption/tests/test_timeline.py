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
    axis = TimeAxis(datetime(2021, 4, 9, 12, 40, tzinfo=timezone.utc), 60.0, 4)
    result = run(axis, 1)
    np.testing.assert_array_equal(result["eruption.explosion"], [0, 1, 0, 0])
    np.testing.assert_array_equal(result["eruption.phase"], [1, 2, 2, 2])
    assert result["eruption.column_height"][0] == 0
    assert result["eruption.column_height"][1] == 0
    assert (result["eruption.column_height"][2:] > 0).all()
    assert not result["eruption.gas"][1:].any()


def test_96_hour_axis_and_prefix_are_honoured():
    start = datetime(2021, 4, 8, tzinfo=timezone.utc)
    long = run(TimeAxis(start, 3600.0, 97), 1)
    short = run(TimeAxis(start, 3600.0, 20), 1)
    for name in ("phase", "column_height", "explosion", "mass_rate", "gas", "tremor"):
        np.testing.assert_array_equal(short["eruption." + name], long["eruption." + name][:20])
    for epoch, _, _ in read_events():
        k = int(np.ceil((epoch - start.timestamp()) / 3600))
        assert long["eruption.explosion"][k] == 1
    assert long["eruption.explosion"][93] == 1  # 11 April 20:22 survives beyond the default axis.


def test_seed_changes_only_precursors():
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 3600.0, 96)
    one, two = run(axis, 1), run(axis, 20)
    for name in ("phase", "column_height", "explosion", "mass_rate"):
        np.testing.assert_array_equal(one["eruption." + name], two["eruption." + name])
    for name in ("gas", "tremor"):
        assert not one["eruption." + name][:12].any()
        assert not one["eruption." + name][37:].any()
    assert not np.array_equal(one["eruption.tremor"], two["eruption.tremor"])


def test_physical_scalings_and_invalid_inputs():
    assert mastin_mass_rate_kg_s(2000.0) == pytest.approx(2500.0)
    assert mastin_mass_rate_kg_s(0.0) == 0
    assert mtt_height_m(16.0, 1.0) == pytest.approx(10.0)
    with pytest.raises(InterfaceError):
        mastin_mass_rate_kg_s(-1.0)
    with pytest.raises(InterfaceError):
        mtt_height_m(1.0, 0.0)


@pytest.mark.parametrize("step", [37.0, 300.0, 7200.0, 12713.0])
def test_interval_mass_is_independent_of_frame_alignment(step):
    start = datetime(2021, 4, 8, tzinfo=timezone.utc)
    n = int(np.ceil(96 * 3600 / step)) + 1
    axis = TimeAxis(start, step, n)
    result = run(axis, 1)
    end = start.timestamp() + (n - 1) * step
    expected = sum(mastin_mass_rate_kg_s(h) * max(0.0, min(t + duration, end) - max(t, start.timestamp())) for t, h, duration in read_events())
    assert result["eruption.mass_rate"][0] == 0
    assert result["eruption.mass_rate"].sum() * step == pytest.approx(expected, rel=1e-12)
    moments = start.timestamp() + np.arange(n) * step
    for k in range(1, n):
        heights = [h for t, h, duration in read_events() if min(t + duration, moments[k]) > max(t, moments[k - 1])]
        assert result["eruption.column_height"][k] == max(heights, default=0.0)


def test_short_and_overlapping_events_add_mass(monkeypatch):
    import stranded_physics.domains.eruption.model as model

    start = datetime(2021, 4, 9, tzinfo=timezone.utc)
    epoch = start.timestamp()
    monkeypatch.setattr(model, "read_events", lambda: [(epoch + 100, 8000.0, 1800.0), (epoch + 200, 12000.0, 1800.0)])
    result = run(TimeAxis(start, 7200.0, 2), 1)
    assert result["eruption.explosion"][1] == 1
    assert result["eruption.mass_rate"][1] > 0
    assert result["eruption.column_height"][1] == 12000
    assert result["eruption.mass_rate"].sum() * 7200 == pytest.approx(1800 * (mastin_mass_rate_kg_s(8000) + mastin_mass_rate_kg_s(12000)))

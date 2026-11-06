from dataclasses import replace
from datetime import datetime, timezone
from math import fsum

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.eruption import generator as gen
from stranded_physics.domains.eruption.model import Eruption, mastin_mass_rate_kg_s


def generate(seed=42, **dials):
    return gen.generate(np.random.default_rng(seed), 60 * 86400., **dials)


def test_seed_and_all_dial_overrides():
    assert generate() == generate()
    dials = dict(size=4, lead_s=300., onset_s=1200., column_m=8000.)
    event = generate(**dials)
    assert (event.size, event.lead_s, event.onset_s) == (4, 300., 1200.)
    assert all(e.height_m == 8000. for e in event.events)
    for seed in range(20):
        event = generate(seed)
        assert .25 * 60 * 86400 <= event.onset_s <= .75 * 60 * 86400
        assert event.onset_s >= event.lead_s


@pytest.mark.parametrize("dials", [dict(size=-1), dict(size=8), dict(size=2.5),
    dict(lead_s=-1), dict(lead_s=np.inf), dict(onset_s=-1), dict(onset_s=60 * 86400 + 1),
    dict(column_m=0), dict(column_m=60001), dict(column_m=np.nan),
    dict(onset_s=0, lead_s=1)])
def test_invalid_dials_are_refused(dials):
    with pytest.raises(InterfaceError):
        generate(**dials)


@pytest.mark.parametrize("axis", [-1, 0, np.inf, [1, 2], [0, 0], [0, np.nan], [[0, 1]]])
def test_invalid_axis_is_refused(axis):
    with pytest.raises(InterfaceError):
        gen.generate(np.random.default_rng(1), axis, lead_s=0)


def test_warning_is_never_resampled_to_fit():
    with pytest.raises(InterfaceError):
        gen.generate(np.random.default_rng(1), 100., lead_s=90.)
    result = gen.generate(np.random.default_rng(1), [0., 50., 100.], lead_s=90., onset_s=95.)
    assert result.onset_s == 95.


@pytest.mark.parametrize("size", range(8))
@pytest.mark.parametrize("column", [None, 1., 60000.])
def test_mass_and_order_for_every_size_and_extreme_columns(size, column):
    event = generate(size=size, column_m=column)
    actual = fsum(mastin_mass_rate_kg_s(e.height_m) * e.duration_s for e in event.events)
    assert actual == pytest.approx(event.total_mass_kg, rel=1e-14)
    assert event.events[0].start_s == event.onset_s
    assert all(e.duration_s > 0 for e in event.events)
    assert all(a.start_s + a.duration_s <= b.start_s for a, b in zip(event.events, event.events[1:]))
    volume = event.total_mass_kg / gen.SETTINGS["bulk_density"]
    assert gen.SETTINGS[f"size_{size}_volume_min"] <= volume <= gen.SETTINGS[f"size_{size}_volume_max"]
    gen.validate_generated(event)


@pytest.mark.parametrize("step", [37., 300., 7200.])
def test_domain_conserves_frame_overlap_and_obeys_time_rule(step):
    event = generate(size=2, lead_s=100., onset_s=200., column_m=5000.)
    start = datetime(2032, 1, 1, tzinfo=timezone.utc)
    end = event.events[-1].start_s + event.events[-1].duration_s
    axis = TimeAxis(start, step, int(np.ceil(end / step)) + 1)
    model, store = Eruption(axis, generated=event), FieldStore()
    fields = ScopedFields(store, model.id, model.inputs, model.outputs)
    assert model.check_validity(fields) == []
    model.run(fields, np.random.default_rng(9))
    moments = np.arange(axis.n) * step
    expected_phase = np.where(moments >= 200., 2., np.where(moments >= 100., 1., 0.))
    np.testing.assert_array_equal(store.get("eruption.phase", "dimensionless"), expected_phase)
    mass = store.get("eruption.mass_rate", "kg/s")
    assert mass[0] == 0
    assert mass.sum() * step == pytest.approx(event.total_mass_kg, rel=1e-12)
    for k in range(1, axis.n):
        expected = fsum(mastin_mass_rate_kg_s(e.height_m) * max(0., min(moments[k], e.start_s + e.duration_s)
                       - max(moments[k-1], e.start_s)) for e in event.events)
        assert mass[k] * step == pytest.approx(expected, rel=1e-12)
    short = Eruption(TimeAxis(start, step, 3), generated=event)
    prefix = FieldStore()
    short.run(ScopedFields(prefix, short.id, short.inputs, short.outputs), np.random.default_rng(9))
    for name in store.names():
        np.testing.assert_array_equal(prefix.get(name, store.stored(name).unit), store.stored(name).data[:3])


def test_generated_path_does_not_read_replay_facts(monkeypatch):
    import stranded_physics.domains.eruption.model as model
    monkeypatch.setattr(model, "read_events", lambda: pytest.fail("generated path read facts.csv"))
    axis = TimeAxis(datetime(2040, 1, 1, tzinfo=timezone.utc), 60., 10)
    event = generate(size=1, lead_s=0., onset_s=0.)
    domain, store = Eruption(axis, generated=event), FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(2))
    bad = replace(event, total_mass_kg=event.total_mass_kg * 2)
    with pytest.raises(InterfaceError):
        Eruption(axis, generated=bad).run(FieldStore(), np.random.default_rng(2))


def test_exact_onset_has_an_explosion_but_no_preceding_interval_mass():
    event = generate(size=2, lead_s=3600., onset_s=7200., column_m=8000.)
    axis = TimeAxis(datetime(2032, 1, 1, tzinfo=timezone.utc), 7200., 3)
    domain, store = Eruption(axis, generated=event), FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    rate = store.get("eruption.mass_rate", "kg/s")
    explosion = store.get("eruption.explosion", "dimensionless")
    assert rate[0] == rate[1] == 0.
    assert explosion[1] == 1.
    assert rate[2] > 0.


def test_training_split_is_checked_before_reading_size(tmp_path, monkeypatch):
    (tmp_path / "eruptions.csv").write_text("start_year,vei\n1999,2\n1999,2\n1998,4\n2000,poison\n", encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(gen, "CATALOG", tmp_path)
        gen.size_catalog.cache_clear()
        assert gen.size_catalog(2000) == (2, 2, 4)
        assert gen.size_catalog(1999) == (4,)
        with pytest.raises(InterfaceError):
            gen.sample_size(np.random.default_rng(1), before_year=2001)
    gen.size_catalog.cache_clear()


def test_samples_are_empirical_catalogue_values():
    rng = np.random.default_rng(5)
    assert {gen.sample_size(rng) for _ in range(100)} <= set(gen.size_catalog(2000))
    assert {gen.sample_lead_s(rng) for _ in range(100)} <= set(gen.lead_catalog())


@pytest.mark.parametrize("samples, ratio", [([3600.] * 4, .5),
    ([3600., 3600., 10800., 10800.], 1.), ([10800.] * 4, 1.5)])
def test_lead_measure_reports_sample_median_without_adjusting_it(monkeypatch, samples, ratio):
    from stranded_physics.domains.eruption import measure

    draws = iter(samples)
    monkeypatch.setitem(measure.SETTINGS, "lead_sample_count", len(samples))
    monkeypatch.setattr(gen, "sample_lead_s", lambda rng: next(draws))
    monkeypatch.setattr(gen, "lead_catalog", lambda: (3600., 10800.))
    result = measure.generator_measure("lead_time_ratio")
    assert result == {"value": ratio, "sample_median_s": ratio * 7200.,
                      "catalogue_median_s": 7200., "sample_count": 4, "catalogue_count": 2}

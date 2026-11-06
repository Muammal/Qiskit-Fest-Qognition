"""The T2 domain releases only on land and preserves the PDC time contract."""

from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.pdc import model_t2
from stranded_physics.domains.pdc.model_t2 import PdcT2, SETTINGS
from stranded_physics.solvers.depth_averaged import FlowResult


def setup_domain(frames=48, land=True, vent=None):
    grid = GridSpec("EPSG:32620", 0.0, 5100.0, 100.0, 51, 51)
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200.0, frames)
    store = FieldStore()
    store.put("terrain.elevation", np.zeros((51, 51)), "m", grid)
    store.put("terrain.land_mask", np.full((51, 51), land), "dimensionless", grid)
    explosion = np.zeros(frames)
    for frame in (10, 40):
        if frame < frames:
            explosion[frame] = 1
    store.put("eruption.explosion", explosion, "dimensionless", time=axis)
    domain = PdcT2(grid, axis, grid.centre(25, 25) if vent is None else vent)
    fields = ScopedFields(store, domain.id, domain.inputs, domain.outputs)
    return store, domain, fields


def test_release_settings_and_time_contract(monkeypatch):
    store, domain, fields = setup_domain()

    def capture(elevation, h0, dx, t_end, **kwargs):
        release = domain._release(np.ones_like(h0, bool))
        assert h0.sum() * dx**2 == pytest.approx(SETTINGS["pulse_volume"])
        assert np.all(h0[~release] == 0)
        assert np.ptp(h0[release]) == 0
        assert t_end == SETTINGS["duration"]
        assert kwargs["mu"] == SETTINGS["coulomb_friction"]
        assert kwargs["xi"] == SETTINGS["turbulent_friction"]
        assert kwargs["arrival_depth"] == SETTINGS["arrival_depth"]
        arrival = np.where(release, 0.0, np.inf)
        return FlowResult(h0, h0 * 0, h0 * 0, arrival, h0, h0 * 0, t_end, h0.sum() * dx**2, 0.0, 1)

    monkeypatch.setattr(model_t2, "simulate", capture)
    assert domain.check_validity(fields) == []
    assert abs(domain.run(fields, np.random.default_rng(0))["volume"]) < 1e-12
    active = store.stored("pdc.active").data
    assert active[:35].sum() == 0
    assert active[35].sum() > 0 and active[40].sum() > 0
    assert active[36:40].sum() == 0
    arrival = store.stored("pdc.arrival").data
    assert arrival[np.isfinite(arrival)].min() == SETTINGS["first_collapse_after_axis_start"]


def test_real_solver_budget_and_short_axis():
    store, domain, fields = setup_domain(frames=20)
    assert abs(domain.run(fields, np.random.default_rng(0))["volume"]) < 1e-9
    assert store.stored("pdc.active").data.sum() == 0
    assert np.isinf(store.stored("pdc.arrival").data).all()


@pytest.mark.parametrize("land,vent", [(False, None), (True, (-1.0, 0.0))])
def test_invalid_release_or_vent(land, vent):
    _, domain, fields = setup_domain(land=land, vent=vent)
    assert domain.check_validity(fields)
    with pytest.raises(InterfaceError):
        domain.run(fields, np.random.default_rng(0))

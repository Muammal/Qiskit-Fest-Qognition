from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.tephra.model import (
    Packet, Tephra, gaussian_load_kg_m2, integrated_packet_mass,
    stokes_settling_m_s, suzuki_weights, wind_at_height,
)


def test_stokes_reynolds_guard_and_scaling():
    one = stokes_settling_m_s(1e-5, 2500., 1.2, 1.8e-5)
    assert stokes_settling_m_s(2e-5, 2500., 1.2, 1.8e-5) == pytest.approx(4 * one)
    with pytest.raises(InterfaceError):
        stokes_settling_m_s(.001, 2500., 1.2, 1.8e-5)


def test_gaussian_peak_and_independent_quadrature():
    packet = Packet(1e8, 100., 1000., 10., 90., 1., 1000.)
    peak = gaussian_load_kg_m2(1e8, 10000., 0., 1000., 10., 90., 1., 1000.)
    assert peak == pytest.approx(1e8 / (2 * np.pi * 2e6))
    assert integrated_packet_mass(packet) == pytest.approx(1e8, rel=1e-7)
    assert packet.arrival_s == 1100


def test_suzuki_formula_support_and_wind_vectors():
    z = np.array([0., 1000., 2000., 3000.])
    expected = ((1 - z / 3000) * np.exp(4 * (z / 3000 - 1))) ** 1.5
    np.testing.assert_allclose(suzuki_weights(z, 3000., 4., 1.5), expected / expected.sum())
    assert wind_at_height(9125., 10., 90., 10., 90., 10., 270.)[0] < 1e-10
    assert wind_at_height(0., 10., 359., 20., 1., 30., 90.) == pytest.approx((10., 359.))
    assert wind_at_height(20000., 10., 359., 20., 1., 30., 90.) == pytest.approx((30., 90.))
    speed, bearing = wind_at_height(2930., 10., 359., 10., 1., 30., 90.)
    assert min(bearing, 360 - bearing) < 1e-10
    assert speed > 9.9


def run_case(future=False, future_wind=False, empty=False):
    axis = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 1000., 10)
    grid = GridSpec("EPSG:32620", -20000., 20000., 1000., 40, 40)
    store = FieldStore()
    rates, heights = np.zeros(10), np.zeros(10)
    if not empty:
        rates[1], heights[1] = 1e5, 1000.
    if future:
        rates[7], heights[7] = 1e6, 2000.
    for name, value, unit in (("eruption.mass_rate", rates, "kg/s"), ("eruption.column_height", heights, "m")):
        store.put(name, value, unit, time=axis)
    for suffix in ("", "_500hpa", "_200hpa"):
        store.put("atmos.wind_speed" + suffix, np.r_[np.full(3, 2.), np.full(7, 100. if future_wind else 2.)], "m/s", time=axis)
        store.put("atmos.wind_bearing" + suffix, np.full(10, 90.), "degree", time=axis)
    ash = Tephra(grid, axis, (0., 0.))
    budget = ash.run(ScopedFields(store, ash.id, ash.inputs, ash.outputs), np.random.default_rng(1))
    return ash, store.get("tephra.deposit_load", "kg/m**2"), budget, grid, axis


def test_packets_arrive_only_after_fall_and_preserve_past():
    ash, frames, budget, grid, axis = run_case()
    _, future, _, _, _ = run_case(True)
    assert not frames[:2].any()
    assert (np.diff(frames, axis=0) >= 0).all()
    np.testing.assert_array_equal(frames[:8], future[:8])
    assert budget["mass_kg"] < 1e-7
    first_arrival = min(p.arrival_s for p in ash._packets)
    assert ash.load_at((0., 0.), np.nextafter(first_arrival, -np.inf)) == 0
    assert ash.load_at((0., 0.), first_arrival) > 0
    xy = grid.centre(20, 25)
    assert ash.load_at(xy, 9 * axis.dt_s) == pytest.approx(frames[-1, 20, 25])
    assert np.isfinite(ash.load_at((500000., 0.), 9 * axis.dt_s))


def test_mass_budget_includes_airborne():
    ash, _, _, _, _ = run_case()
    landed = sum(p.mass_kg for p in ash._packets if p.arrival_s <= 9000.)
    assert landed < ash.released_mass_kg
    assert ash.integrated_mass_kg == pytest.approx(ash.released_mass_kg, rel=1e-7)


def test_future_wind_does_not_redirect_existing_packets():
    _, original, _, _, _ = run_case()
    _, changed, _, _, _ = run_case(future_wind=True)
    np.testing.assert_array_equal(original, changed)


def test_no_eruption_has_zero_load_and_zero_budget():
    ash, frames, budget, _, _ = run_case(empty=True)
    assert not frames.any()
    assert budget == {"mass_kg": 0.}
    assert ash.load_at((0., 0.), 9000.) == 0


def test_release_height_quadrature_converges():
    from scipy.integrate import quad

    def density(z):
        return (1 - z) * np.exp(4 * (z - 1))

    expected = quad(lambda z: z * density(z), 0., 1.)[0] / quad(density, 0., 1.)[0]
    errors = []
    for n in (12, 24, 48):
        heights = (np.arange(n) + .5) / n
        errors.append(abs(np.dot(heights, suzuki_weights(heights, 1., 4., 1.)) - expected))
    assert errors[2] < errors[1] < errors[0]
    assert errors[2] < 2e-4



def test_continuous_grains_and_terminal_force_balance():
    from stranded_physics.domains.tephra.model import SETTINGS, grain_classes, settling_speed_m_s

    diameters, fractions = grain_classes(129)
    assert diameters[0] == pytest.approx(.016)
    assert diameters[-1] == pytest.approx(.001 / 64)
    assert (fractions > 0).all()
    assert fractions.sum() == pytest.approx(1.)
    np.testing.assert_allclose(np.diff(np.log2(diameters)), -10 / 128)
    for diameter in np.geomspace(1e-6, .016, 50):
        speed = settling_speed_m_s(diameter, 2500., 1.2, 1.8e-5)
        re = 1.2 * speed * diameter / 1.8e-5
        cd = 24 / re * (1 + .15 * re ** .687) if re <= 1000 else .44
        drag = .5 * 1.2 * cd * np.pi * diameter ** 2 / 4 * speed ** 2
        weight = (2500 - 1.2) * SETTINGS["gravity"] * np.pi * diameter ** 3 / 6
        assert drag == pytest.approx(weight, rel=1e-7)
    small = settling_speed_m_s(1e-6, 2500., 1.2, 1.8e-5)
    assert small == pytest.approx(stokes_settling_m_s(1e-6, 2500., 1.2, 1.8e-5), rel=.001)
    with pytest.raises(InterfaceError):
        settling_speed_m_s(-1., 2500., 1.2, 1.8e-5)
    with pytest.raises(InterfaceError):
        grain_classes(1)

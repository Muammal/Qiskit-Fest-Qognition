"""Analytic solutions and conservation invariants, independent of island gates."""

import math

import numpy as np
import pytest

from stranded_physics.solvers.depth_averaged import GRAVITY as G, friction_deceleration, simulate


def ritter(n, depth=3.0, time=25.0):
    dx = 2000.0 / n
    x = (np.arange(n) + 0.5) * dx - 1000.0
    initial = np.where(x < 0, depth, 0.0)[None, :]
    result = simulate(np.zeros_like(initial), initial, dx, time)
    c = math.sqrt(G * depth)
    exact = np.where(x < -c * time, depth, np.where(x > 2 * c * time, 0.0, (2 * c - x / time) ** 2 / (9 * G)))
    return np.abs(result.h[0] - exact).mean() / depth, result


def test_ritter_profile_and_convergence():
    errors = [ritter(n)[0] for n in (200, 400, 800)]
    assert errors[2] < 0.01
    assert errors[0] > errors[1] > errors[2]
    assert math.log2(errors[0] / errors[2]) / 2 > 0.55


@pytest.mark.parametrize("depth", [1.0, 8.0])
def test_ritter_dry_front(depth):
    _, result = ritter(800, depth=depth, time=30.0)
    x = (np.arange(800) + 0.5) * 2.5 - 1000.0
    front = x[result.h[0] > 0.001 * depth].max()
    exact = 2 * math.sqrt(G * depth) * 30.0
    assert abs(front - exact) < 0.1 * exact


@pytest.mark.parametrize("island", [False, True])
def test_lake_at_rest(island):
    rng = np.random.default_rng(314)
    bed = rng.uniform(0.0, 7.0 if island else 3.0, (33, 37))
    initial = np.maximum(0.0, 5.0 - bed)
    result = simulate(bed, initial, 10.0, 30.0)
    np.testing.assert_allclose(result.h, initial, atol=1e-12, rtol=0)
    assert np.max(np.hypot(result.hu, result.hv)) < 1e-11


def test_thacker_period_and_amplitude():
    n, a, depth, offset = 800, 1000.0, 10.0, 1.0
    dx = 3 * a / n
    x = (np.arange(n) + 0.5) * dx - 1.5 * a
    bed = depth * (x / a) ** 2 - depth
    initial = np.maximum(0.0, offset * x / a - bed)[None, :]
    period = 2 * math.pi * a / math.sqrt(2 * G * depth)
    centre = lambda h: float((h * x).sum() / h.sum())
    first = centre(initial)
    half = simulate(bed[None, :], initial, dx, period / 2)
    full = simulate(bed[None, :], initial, dx, period)
    assert abs(centre(half.h) + first) < 0.1 * abs(first)
    assert abs(centre(full.h) - first) < 0.1 * abs(first)


@pytest.mark.parametrize("mu", [0.06, 0.18])
def test_frictional_dam_break_front(mu):
    dx, time, depth, slope = 1.0, 15.0, 2.0, 0.3
    x = (np.arange(2400) + 0.5) * dx - 500.0
    bed = (-slope * x)[None, :]
    initial = np.where(x < 0, depth, 0.0)[None, :]
    result = simulate(bed, initial, dx, time, mu=mu)
    front = x[result.h[0] > 0.001].max()
    exact = 2 * math.sqrt(G * depth) * time + 0.5 * G * (slope - mu) * time**2
    assert abs(front - exact) < 0.08 * exact


def test_friction_law_and_stopping_without_reversal():
    assert friction_deceleration(2.0, 10.0, 0.2, 500.0) == pytest.approx(0.2 * G + G * 100 / 1000)
    assert friction_deceleration(2.0, 10.0, 0.2, None) == pytest.approx(0.2 * G)
    h = np.ones((1, 1))
    result = simulate(h * 0, h, 10.0, 10.0, mu=0.2, hu0=h * 2)
    assert result.hu[0, 0] == 0
    rows, cols = np.mgrid[:51, :51]
    pile = np.where((rows - 25) ** 2 + (cols - 25) ** 2 < 25, 0.5, 0.0)
    result = simulate(-0.05 * cols, pile, 10.0, 200.0, mu=0.5)
    assert np.hypot(result.hu, result.hv).max() < 1e-3
    assert result.max_speed.max() < 3.0


def test_volume_positivity_sinks_and_rotation():
    rng = np.random.default_rng(45)
    bed = rng.uniform(-2.0, 2.0, (31, 35))
    h = rng.uniform(0.0, 2.0, bed.shape)
    sinks = np.zeros_like(h, bool)
    sinks[:, -2:] = True
    first = simulate(bed, h, 10.0, 15.0, sink=sinks, mu=0.1, xi=300.0)
    turned = simulate(np.rot90(bed), np.rot90(h), 10.0, 15.0, sink=np.rot90(sinks), mu=0.1, xi=300.0)
    assert first.h.min() >= 0
    assert first.h[sinks].max() == 0
    assert first.outflow_volume > 0
    assert first.h.sum() * 100 + first.outflow_volume == pytest.approx(first.initial_volume, rel=1e-12)
    np.testing.assert_allclose(np.rot90(first.h), turned.h, atol=1e-11)
    np.testing.assert_allclose(np.rot90(first.hv), turned.hu, atol=1e-10)
    np.testing.assert_allclose(np.rot90(first.hu), -turned.hv, atol=1e-10)


def test_closed_box_and_arrival():
    _, result = ritter(800)
    assert result.outflow_volume == 0
    assert result.h.sum() * 2.5**2 == pytest.approx(result.initial_volume, rel=1e-12)
    arrival = result.arrival_s[0]
    assert np.isinf(arrival[-1])
    assert (np.diff(arrival[np.isfinite(arrival)]) >= 0).all()
    assert (result.max_depth >= result.h).all()


def test_dry_work_rectangle_matches_full_flux_work(monkeypatch):
    from stranded_physics.solvers import depth_averaged as solver

    rows, cols = np.mgrid[:35, :41]
    bed = 0.02 * (rows - 17) ** 2 + 0.03 * (cols - 20) ** 2
    h = np.where((rows - 17) ** 2 + (cols - 20) ** 2 < 16, 2.0, 0.0)
    cropped = simulate(bed, h, 10.0, 4.0)
    monkeypatch.setattr(solver, "_rhs", solver._rhs_full)
    full = simulate(bed, h, 10.0, 4.0)
    np.testing.assert_allclose(cropped.h, full.h, atol=1e-13)
    np.testing.assert_allclose(cropped.hu, full.hu, atol=1e-12)
    np.testing.assert_allclose(cropped.hv, full.hv, atol=1e-12)


@pytest.mark.parametrize("kwargs", [{"dx": 0}, {"mu": -1}, {"xi": 0}, {"cfl": 0}])
def test_rejects_invalid_parameters(kwargs):
    settings = dict(dx=1.0, t_end=1.0)
    settings.update(kwargs)
    with pytest.raises(ValueError):
        simulate(np.zeros((2, 2)), np.ones((2, 2)), **settings)

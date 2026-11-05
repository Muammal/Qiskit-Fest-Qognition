"""Moving-flow controls independent of the island and its physical settings."""
import numpy as np
import pytest

from stranded_physics.solvers.depth_averaged import GRAVITY as G, _energy_reconstruct, simulate


def assert_budget(result, dx):
    assert result.h.min() >= 0
    assert np.isfinite(result.hu).all() and np.isfinite(result.hv).all()
    assert result.h.sum()*dx**2 + result.outflow_volume == pytest.approx(result.initial_volume, rel=1e-12)


@pytest.mark.parametrize("dx", [90., 45.])
@pytest.mark.parametrize("depth,speed,rise", [(1., 30., 5.), (.5, 25., 8.), (1.5, 40., 2.)])
def test_fast_shallow_pulse_crosses_hollow(dx, depth, speed, rise):
    slope, duration, far = np.tan(np.deg2rad(20)), 60., 7380.
    x = (np.arange(int(14400/dx))+.5)*dx
    bed = np.where((x >= 7200) & (x < far), (14400-far)*slope-rise, (14400-x)*slope)
    h = np.where((x >= 1800) & (x < 3600), depth, 0.)[None, :]
    result = simulate(bed[None, :], h, dx, duration, hu0=h*speed)
    assert result.h[0, x < far].sum()/h.sum() < .05
    wet = result.max_depth >= 1e-3
    characteristic_bound = speed + G*slope*duration + 2*np.sqrt(G*depth)
    assert result.max_speed[wet].max() < 1.15*characteristic_bound
    assert_budget(result, dx)


@pytest.mark.parametrize("speed,factor", [(4., 3.), (8., 6.)])
def test_insufficient_head_stops_at_barrier(speed, factor):
    dx = 90.
    x = (np.arange(200)+.5)*dx
    wall = factor*speed**2/(2*G) + 2.
    bed = np.where((x >= 9000) & (x < 9450), wall, 0.)[None, :]
    h = np.where((x >= 1800) & (x < 3600), 1., 0.)[None, :]
    result = simulate(bed, h, dx, 900., hu0=h*speed)
    assert result.h[0, x >= 9450].sum()/h.sum() < .02
    assert_budget(result, dx)


@pytest.mark.parametrize("speed", [2., 4.])
def test_slow_pulse_pools_in_pit(speed):
    dx = 90.
    x = (np.arange(200)+.5)*dx
    pit = (x >= 9000) & (x < 9900)
    bed = np.where(pit, -8., 0.)[None, :]
    h = np.where((x >= 8000) & (x < 8990), .2, 0.)[None, :]
    result = simulate(bed, h, dx, 900., hu0=h*speed)
    assert result.h[0, pit].sum()/h.sum() > .8
    assert_budget(result, dx)


def test_fast_flow_pays_for_each_uphill_step():
    dx = 90.
    x = (np.arange(160)+.5)*dx
    bed = 5.*np.clip(np.floor((x-5400)/450)+1, 0, 12)[None, :]
    h = np.where((x >= 1800) & (x < 3600), 1., 0.)[None, :]
    result = simulate(bed, h, dx, 450., hu0=h*20.)
    assert result.max_depth[0, x >= 10800].max() < 1e-3
    assert result.max_speed[result.max_depth >= 1e-3].max() < 20 + 2*np.sqrt(G)
    assert_budget(result, dx)


def test_fast_flow_crosses_uphill_step_in_both_directions():
    dx = 90.
    x = (np.arange(160)+.5)*dx
    bed = np.where(x >= 7200, 5., 0.)[None, :]
    h = np.where((x >= 1800) & (x < 3600), 1., 0.)[None, :]
    result = simulate(bed, h, dx, 250., hu0=h*30.)
    reverse = simulate(bed[:, ::-1], h[:, ::-1], dx, 250., hu0=-h[:, ::-1]*30.)
    assert result.h[0, x >= 7200].sum()/h.sum() > .95
    np.testing.assert_allclose(result.h[:, ::-1], reverse.h, atol=1e-12)
    np.testing.assert_allclose(-result.hu[:, ::-1], reverse.hu, atol=1e-10)
    assert_budget(result, dx)


def test_face_reconstruction_preserves_discharge_and_head():
    depth = np.array([1., 2., 4., 10.])
    speed = np.array([30., -20., .1, -.2])
    rise = np.array([5., 3., 1., 2.])
    face_h, face_u, _ = _energy_reconstruct(depth, speed, rise)
    np.testing.assert_allclose(face_h*face_u, depth*speed, rtol=2e-14)
    np.testing.assert_allclose(face_h + face_u**2/(2*G) + rise,
                               depth + speed**2/(2*G), rtol=2e-14)
    stopped_h, _, _ = _energy_reconstruct(np.ones(1), np.ones(1), np.full(1, 5.))
    assert stopped_h[0] == 0


def test_fast_flow_rotation_with_nonzero_initial_momentum():
    row, col = np.mgrid[:17, :23]
    bed = -.8*col + .4*row
    bed[7:10, 11:13] -= 4.
    h = np.where((row >= 5) & (row < 12) & (col >= 3) & (col < 8), 1., 0.)
    first = simulate(bed, h, 30., 10., hu0=20*h, hv0=-5*h)
    turned = simulate(np.rot90(bed), np.rot90(h), 30., 10.,
                      hu0=np.rot90(-5*h), hv0=np.rot90(-20*h))
    np.testing.assert_allclose(np.rot90(first.h), turned.h, atol=1e-11)
    np.testing.assert_allclose(np.rot90(first.hu), -turned.hv, atol=1e-9)
    np.testing.assert_allclose(np.rot90(first.hv), turned.hu, atol=1e-9)
    assert_budget(first, 30.)

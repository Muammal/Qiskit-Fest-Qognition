"""Conservative HLL shallow water scheme with hydrostatic/energy reconstruction.

Cell averages use eastward hu and southward hv. Bed pressure corrections
balance each face separately, including wet/dry lake shorelines.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

GRAVITY = 9.80665
DRY_DEPTH = 1e-12  # Only regularises velocity division; no water is discarded.
MAX_CFL = 0.45  # CFL safety cap; both RK stages also obey draining bounds.
WORK_HALO = 3  # Two reconstruction neighbours plus one empty guard cell.
DRAIN_SAFETY = .9  # Prevent roundoff from emptying a donor past zero.


def friction_deceleration(h, speed, mu, xi, g=GRAVITY):
    """Voellmy deceleration; xi=None removes the turbulent term."""
    h, speed = np.broadcast_arrays(np.asarray(h, float), np.asarray(speed, float))
    if xi is None:
        return np.full(h.shape, mu * g)
    drag = np.divide(g * speed**2, xi * h, out=np.zeros_like(h), where=h > 0)
    return mu * g + np.where((h <= 0) & (speed > 0), np.inf, drag)


@dataclass(frozen=True)
class FlowResult:
    h: np.ndarray
    hu: np.ndarray
    hv: np.ndarray
    arrival_s: np.ndarray
    max_depth: np.ndarray
    max_speed: np.ndarray
    time_s: float
    initial_volume: float
    outflow_volume: float
    steps: int


def _velocity(q, h):
    return np.divide(q, h, out=np.zeros_like(h), where=h > DRY_DEPTH)


def _slope(array, compressive=True):
    """Superbee for flow variables, MC for the fixed bed."""
    back = array[:, 1:-1] - array[:, :-2]
    forward = array[:, 2:] - array[:, 1:-1]
    if compressive:
        magnitude = np.maximum(np.minimum(2 * np.abs(back), np.abs(forward)),
                               np.minimum(np.abs(back), 2 * np.abs(forward)))
    else:
        magnitude = np.minimum(.5*np.abs(back+forward), 2*np.minimum(np.abs(back), np.abs(forward)))
    limited = np.where(back * forward > 0, np.sign(back) * magnitude, 0.)
    return np.pad(limited, ((0, 0), (1, 1)))


def _energy_reconstruct(h, u, rise):
    """Preserve discharge and Bernoulli head on an admissible steady branch."""
    hydro = np.maximum(0., h - rise)
    if not np.any((h > DRY_DEPTH) & (rise > 0)):
        return hydro, u, np.zeros_like(h)
    discharge = h * u
    critical = np.cbrt(discharge**2 / GRAVITY)
    energy = h + u**2 / (2 * GRAVITY) - rise
    admissible = (h > DRY_DEPTH) & (energy >= 1.5 * critical) & (energy > 0) & (rise > 0)
    ratio = np.divide(1.5 * critical, energy, out=np.zeros_like(h), where=admissible)
    angle = (2 / 3) * np.arcsin(np.minimum(1., ratio)**1.5)
    subcritical = energy / 3 * (1 + 2 * np.cos(angle))
    # This form avoids cancellation in the small supercritical cubic root.
    supercritical = energy / 3 * (2 * np.sin(angle / 2)**2 + np.sqrt(3.) * np.sin(angle))
    depth = np.where(admissible, np.where(h < critical, supercritical, subcritical), hydro)
    velocity = np.where(admissible, _velocity(discharge, depth), u)
    correction = np.where(admissible, depth * velocity**2 - h * u**2, 0.)
    return depth, velocity, correction


def _direction(h, q, transverse, bed):
    """Face flux divergence in the last array dimension, with reflecting walls."""
    hp = np.pad(h, ((0, 0), (1, 1)), mode="edge")
    zp = np.pad(bed, ((0, 0), (1, 1)), mode="edge")
    up = np.pad(_velocity(q, h), ((0, 0), (1, 1)), mode="edge")
    vp = np.pad(_velocity(transverse, h), ((0, 0), (1, 1)), mode="edge")
    up[:, 0] *= -1
    up[:, -1] *= -1
    left, right = np.s_[:, :-1], np.s_[:, 1:]
    es, zs = _slope(hp + zp), _slope(zp, compressive=False)
    hs = np.clip(es - zs, -2 * hp, 2 * hp)
    # At a downhill thinning front, limit the free surface rather than turning
    # the reconstructed bed into a barrier. At rest es=0 remains exact.
    preserve_bed = (es*zs > 0) & (np.abs(es) >= np.abs(zs))
    es = np.where(preserve_bed, zs + hs, es)
    # Beyond Fr=1 both characteristics move with the flow: limit depth, so
    # a bed-slope change cannot erase the outgoing layer before the step solve.
    supercritical = up**2 > GRAVITY * hp
    hs = np.where(supercritical, _slope(hp), hs)
    es = np.where(supercritical, zs + hs, es)
    hm = np.maximum(0., hp - .5*hs)
    hf = np.maximum(0., hp + .5*hs)
    em, ep = hp+zp-.5*es, hp+zp+.5*es
    vs = _slope(vp)
    zl, zr = ep[left]-hf[left], em[right]-hm[right]
    top = np.maximum(zl, zr)
    # Reconstruct the gravity-wave invariants. Near vacuum, u and sqrt(h)
    # vary linearly through a rarefaction even though h itself is quadratic.
    wave = np.sqrt(GRAVITY * hp)
    plus, minus = up + 2*wave, up - 2*wave
    ps, ms = _slope(plus, compressive=True), _slope(minus, compressive=True)
    weight = .5 * (1 + np.divide(up, np.hypot(up, wave), out=np.zeros_like(up), where=hp > 0))
    original_left = hf[left]
    original_right = hm[right]
    ul = (weight[left]*(plus[left]+.5*ps[left]-2*np.sqrt(GRAVITY*original_left))
          + (1-weight[left])*(minus[left]+.5*ms[left]+2*np.sqrt(GRAVITY*original_left)))
    ur = (weight[right]*(plus[right]-.5*ps[right]-2*np.sqrt(GRAVITY*original_right))
          + (1-weight[right])*(minus[right]-.5*ms[right]+2*np.sqrt(GRAVITY*original_right)))
    vl, vr = vp[left] + .5 * vs[left], vp[right] - .5 * vs[right]
    hl, ul, correction_l = _energy_reconstruct(original_left, ul, top - zl)
    hr, ur, correction_r = _energy_reconstruct(original_right, ur, top - zr)
    cl, cr = np.sqrt(GRAVITY * hl), np.sqrt(GRAVITY * hr)
    sl = np.minimum(np.minimum(ul - cl, ur - cr), 0.)
    sr = np.maximum(np.maximum(ul + cl, ur + cr), 0.)
    # Dry-bed rarefactions have edge speeds u +/- 2c (Ritter).
    sl = np.where(hl == 0, np.minimum(ur - 2 * cr, 0.), sl)
    sr = np.where(hr == 0, np.maximum(ul + 2 * cl, 0.), sr)
    denominator = sr - sl
    inverse = np.divide(1., denominator, out=np.zeros_like(denominator), where=denominator > 0)

    def hll(fl, fr, jump):
        return (sr * fl - sl * fr + sl * sr * jump) * inverse

    mass = hll(hl * ul, hr * ur, hr - hl)
    normal = hll(hl * ul**2 + .5 * GRAVITY * hl**2,
                 hr * ur**2 + .5 * GRAVITY * hr**2, hr * ur - hl * ul)
    tangent = hll(hl * ul * vl, hr * ur * vr, hr * vr - hl * vl)
    # Set wall transport to exactly zero, including floating-point residuals.
    mass[:, (0, -1)] = 0.
    tangent[:, (0, -1)] = 0.
    dh = mass[:, :-1] - mass[:, 1:]
    dq = ((normal[:, :-1] - .5 * GRAVITY * hr[:, :-1]**2)
          - (normal[:, 1:] - .5 * GRAVITY * hl[:, 1:]**2)
          - .5*GRAVITY*(hm[:, 1:-1]+hf[:, 1:-1])*es[:, 1:-1])
    # Moving reconstruction needs the advective part of the source as well.
    dq += correction_l[:, 1:] - correction_r[:, :-1]
    dtan = tangent[:, :-1] - tangent[:, 1:]
    drain = np.maximum(mass[:, 1:], 0.) + np.maximum(-mass[:, :-1], 0.)
    return dh, dq, dtan, drain


def _friction(h, hu, hv, dt, mu, xi):
    speed = np.hypot(_velocity(hu, h), _velocity(hv, h))
    remaining = np.maximum(0., speed - dt * mu * GRAVITY)
    if xi is not None:
        drag = np.divide(dt * GRAVITY, xi * h, out=np.zeros_like(h), where=h > DRY_DEPTH)
        # Positive root of v_new + dt*g*v_new^2/(xi*h) = v_star-dt*mu*g.
        remaining = 2 * remaining / (1 + np.sqrt(1 + 4 * drag * remaining))
    scale = np.divide(remaining, speed, out=np.zeros_like(h), where=speed > 0)
    return hu * scale, hv * scale


def _rhs_full(h, hu, hv, bed):
    dh, du, dv, drain = _direction(h, hu, hv, bed)
    if h.shape[0] == 1 and not hv.any():
        return dh, du, dv, drain
    yh, yv, yu, yd = _direction(h.T, hv.T, hu.T, bed.T)
    return dh + yh.T, du + yu.T, dv + yv.T, drain + yd.T


def _rhs(h, hu, hv, bed):
    wet = h > 0
    rows, cols = np.flatnonzero(wet.any(axis=1)), np.flatnonzero(wet.any(axis=0))
    if not rows.size:
        return tuple(np.zeros_like(h) for _ in range(4))
    r0, r1 = max(0, rows[0]-WORK_HALO), min(h.shape[0], rows[-1]+WORK_HALO+1)
    c0, c1 = max(0, cols[0]-WORK_HALO), min(h.shape[1], cols[-1]+WORK_HALO+1)
    if r0 == c0 == 0 and (r1, c1) == h.shape:
        return _rhs_full(h, hu, hv, bed)
    region = np.s_[r0:r1, c0:c1]
    local = _rhs_full(h[region], hu[region], hv[region], bed[region])
    result = tuple(np.zeros_like(h) for _ in range(4))
    for array, values in zip(result, local):
        array[region] = values
    return result


def simulate(elevation, h0, dx, t_end, mu=0., xi=None, cfl=0.4,
             sink=None, arrival_depth=1e-3, hu0=None, hv0=None) -> FlowResult:
    """Advance a pulse on a uniform grid with closed walls and optional sinks."""
    bed = np.asarray(elevation, dtype=float)
    h = np.array(h0, dtype=float, copy=True)
    if bed.ndim != 2 or bed.shape != h.shape or not h.size:
        raise ValueError("elevation and depth must be nonempty matching 2-D arrays")
    if not np.isfinite(bed).all() or not np.isfinite(h).all() or (h < 0).any():
        raise ValueError("finite terrain and nonnegative finite depths required")
    if not all(np.isfinite(x) for x in (dx, t_end, mu, cfl, arrival_depth)):
        raise ValueError("finite numerical and friction parameters required")
    if dx <= 0 or t_end < 0 or mu < 0 or not 0 < cfl <= 1 or arrival_depth <= 0:
        raise ValueError("invalid spacing, duration, friction, CFL or arrival depth")
    if xi is not None and (not np.isfinite(xi) or xi <= 0):
        raise ValueError("xi must be positive or None")
    hu = np.zeros_like(h) if hu0 is None else np.array(hu0, dtype=float, copy=True)
    hv = np.zeros_like(h) if hv0 is None else np.array(hv0, dtype=float, copy=True)
    if any(q.shape != h.shape or not np.isfinite(q).all() for q in (hu, hv)):
        raise ValueError("momenta must match depth and be finite")
    if ((h == 0) & ((hu != 0) | (hv != 0))).any():
        raise ValueError("dry cells cannot carry momentum")
    sinks = np.zeros_like(h, dtype=bool) if sink is None else np.asarray(sink, dtype=bool)
    if sinks.shape != h.shape:
        raise ValueError("sink must match depth")
    initial = float(h.sum() * dx**2)
    arrival = np.where(h >= arrival_depth, 0., np.inf)
    maximum = h.copy()
    max_speed = np.hypot(_velocity(hu, h), _velocity(hv, h))
    outflow = float(h[sinks].sum() * dx**2)
    h[sinks], hu[sinks], hv[sinks] = 0., 0., 0.
    t, steps = 0., 0
    while t < t_end:
        wave = np.sqrt(GRAVITY * h)
        rate = np.zeros_like(h)
        if h.shape[1] > 1 or hu.any():
            rate += np.abs(_velocity(hu, h)) + wave
        if h.shape[0] > 1 or hv.any():
            rate += np.abs(_velocity(hv, h)) + wave
        fastest = float(rate.max())
        dt = min(t_end - t, min(cfl, MAX_CFL) * dx / fastest) if fastest else t_end - t
        dh, du, dv, drain = _rhs(h, hu, hv, bed)
        draining_time = np.divide(h*dx, drain, out=np.full_like(h, np.inf), where=drain > 0)
        dt = min(dt, DRAIN_SAFETY * float(draining_time.min()))
        previous = h
        # SSPRK2 is a convex combination of positive Euler stages. Retry a
        # smaller step if the second stage has a tighter draining-time bound.
        while True:
            stage_h = h + (dt / dx) * dh
            stage_u = hu + (dt / dx) * du
            stage_v = hv + (dt / dx) * dv
            first_loss = float(stage_h[sinks].sum()*dx**2)
            stage_h[sinks], stage_u[sinks], stage_v[sinks] = 0., 0., 0.
            rh, ru, rv, stage_drain = _rhs(stage_h, stage_u, stage_v, bed)
            stage_limit = np.divide(stage_h*dx, stage_drain, out=np.full_like(h, np.inf), where=stage_drain > 0)
            if stage_h.min() >= 0 and dt <= DRAIN_SAFETY*float(stage_limit.min()):
                break
            dt *= .5
            if dt <= np.spacing(t):
                raise FloatingPointError("positive time step below floating-point resolution")
        end_h = stage_h + (dt / dx) * rh
        second_loss = float(end_h[sinks].sum()*dx**2)
        h = .5 * (h + end_h)
        hu = .5 * (hu + stage_u + (dt / dx) * ru)
        hv = .5 * (hv + stage_v + (dt / dx) * rv)
        hu, hv = _friction(h, hu, hv, dt, mu, xi)
        t += dt
        steps += 1
        crossed = np.isinf(arrival) & (h >= arrival_depth)
        fraction = np.divide(arrival_depth - previous, h - previous,
                             out=np.ones_like(h), where=crossed & (h > previous))
        arrival[crossed] = t - dt + dt * np.clip(fraction[crossed], 0., 1.)
        maximum = np.maximum(maximum, h)
        max_speed = np.maximum(max_speed, np.hypot(_velocity(hu, h), _velocity(hv, h)))
        outflow += .5*(first_loss + second_loss)
        h[sinks], hu[sinks], hv[sinks] = 0., 0., 0.
    return FlowResult(h, hu, hv, arrival, maximum, max_speed, t, initial, outflow, steps)

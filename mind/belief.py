"""Belief preparation, event gates and collapse (TECH_A_BUILD_PLAN.md Section 4.4).

Operates on the belief qubit alone, as a 2x2 density matrix: |0> = safe,
|1> = danger. EVENT_GATES and COLLAPSE_EVENTS now live in mind/config.py
(Stage 4 consolidation); re-exported here since mind/tests/test_belief.py
imports them from this module.
"""
import numpy as np

from mind.config import COLLAPSE_EVENTS, EVENT_GATES
from mind.decoherence import apply_phase_damping

_DANGER_PROJECTOR = np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex)


def _ry(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def _rx(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


def prepare_belief(safety):
    """R_y(theta0) on |0>, sin^2(theta0/2) = clamp(1-safety, 0.02, 0.98)."""
    p_danger = np.clip(1 - safety, 0.02, 0.98)
    theta0 = 2 * np.arcsin(np.sqrt(p_danger))
    psi = _ry(theta0) @ np.array([1.0, 0.0], dtype=complex)
    return np.outer(psi, psi.conj())


def apply_event(rho, event):
    """One event gate: a rotation, a collapse, or the identity ("none")."""
    if event == "none":
        return rho.copy()

    if event in COLLAPSE_EVENTS:
        collapsed = _DANGER_PROJECTOR @ rho @ _DANGER_PROJECTOR
        trace = collapsed.trace().real
        if trace <= 1e-12:
            # already fully |safe>; project onto |danger> directly rather
            # than divide by ~0
            return np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex)
        return collapsed / trace

    axis, angle = EVENT_GATES[event]
    U = _ry(angle) if axis == "ry" else _rx(angle)
    return U @ rho @ U.conj().T


def run_events(rho, events, lam):
    """Apply events in order, oldest first. Phase-damp after every slot,
    including when the event is "none" (Section 4.5)."""
    for event in events:
        rho = apply_event(rho, event)
        rho = apply_phase_damping(rho, lam)
    return rho

"""Belief preparation, event gates and collapse (TECH_A_BUILD_PLAN.md Section 4.4).

Operates on the belief qubit alone, as a 2x2 density matrix: |0> = safe,
|1> = danger. Rotation angles and collapse events will move to
mind/config.py in Stage 4, which consolidates every constant; they live
here for now since Stage 2 has no config.py dependency yet.
"""
import numpy as np

from mind.decoherence import apply_phase_damping

# event -> (rotation axis, angle). No angle is +-pi/2 (Section 4.4 "angle
# rule"): that would reset the belief to 50/50 under full decoherence.
EVENT_GATES = {
    "tremor": ("ry", np.pi / 3),
    "gas_plume": ("rx", 3 * np.pi / 5),
    "storm": ("ry", np.pi / 3),
    "animal": ("ry", np.pi / 3),
    "injury": ("rx", 2 * np.pi / 3),
    "cold_night": ("rx", np.pi / 6),
    "find_food": ("ry", -np.pi / 4),
}

COLLAPSE_EVENTS = {"eruption", "ash_fall"}

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

"""Gate-level circuits (TECH_A_BUILD_PLAN.md Section 6 / Stage 6).

build_decision_circuit covers only rotation-only event histories: a
collapse (eruption, ash_fall) is a non-unitary projection, not a gate, so
it cannot appear in a QuantumCircuit. This is a real limitation of the
circuit picture, not a bug - see 06-circuits-and-hardware.md.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from mind.config import COLLAPSE_EVENTS, EVENT_GATES, Q_CLAMP
from mind.model import build_U


def build_decision_circuit(safety, events, q_S, q_D, eta):
    """ry preparation, then each event's gate, then UnitaryGate(U), then
    a measurement of qubit 1 (the decision qubit)."""
    lo, hi = Q_CLAMP
    p_danger = np.clip(1 - safety, lo, hi)
    theta0 = 2 * np.arcsin(np.sqrt(p_danger))

    qc = QuantumCircuit(2, 1)
    qc.ry(theta0, 0)
    for event in events:
        if event == "none":
            continue
        if event in COLLAPSE_EVENTS:
            raise ValueError(
                f"{event!r} is a collapse event; it has no gate representation "
                "(see 06-circuits-and-hardware.md)"
            )
        axis, angle = EVENT_GATES[event]
        if axis == "ry":
            qc.ry(angle, 0)
        else:
            qc.rx(angle, 0)

    U = build_U(q_S, q_D, eta)
    qc.append(UnitaryGate(U, label="U"), [0, 1])
    qc.measure(1, 0)
    return qc


def build_coherence_probe_circuit(t_us):
    """Ramsey-style probe: |+> on the belief qubit, idle for t_us, rotate
    back and measure - isolates coherence decay from the decision-mixing
    unitary, for the delay experiment's T2 cross-check."""
    qc = QuantumCircuit(2, 1)
    qc.ry(np.pi / 2, 0)
    if t_us > 0:
        qc.delay(t_us, 0, unit="us")
    qc.ry(-np.pi / 2, 0)
    qc.measure(0, 0)
    return qc


def build_delay_circuit(t_us, q_S, q_D, eta):
    """Belief prepared at p=0.5 (x=1), idle for t_us, then U, then measure
    qubit 1 - the full decision pipeline under a scheduled delay."""
    qc = QuantumCircuit(2, 1)
    qc.ry(np.pi / 2, 0)
    if t_us > 0:
        qc.delay(t_us, 0, unit="us")
    U = build_U(q_S, q_D, eta)
    qc.append(UnitaryGate(U, label="U"), [0, 1])
    qc.measure(1, 0)
    return qc

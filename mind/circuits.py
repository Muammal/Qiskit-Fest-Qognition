"""Gate-level circuits (TECH_A_BUILD_PLAN.md Section 6 / Stage 6).

Includes:
- `build_decision_circuit`: 2-qubit deliberation circuit (supports both strict
  unitary-only mode and optional mid-circuit reset+X collapse mode for
  `eruption` / `ash_fall`).
- `build_busemeyer_hamiltonian_circuit`: 2-qubit circuit compiled from
  Busemeyer's dynamic Hamiltonian U(t) = exp(-i*t*(pi/2)*(H_a + H_c)).
- `build_luders_sequence_circuit`: Rotate-Measure-Rotate-Back Qiskit circuit
  (`WileQ/QCog` pattern) for sequential incompatible question projections.
- `build_coherence_probe_circuit` and `build_delay_circuit`: T2 Ramsey and
  delay-decoherence circuits.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from mind.cognition_models import busemeyer_hamiltonian_U
from mind.config import COLLAPSE_EVENTS, EVENT_GATES, Q_CLAMP
from mind.model import build_U


def build_decision_circuit(safety, events, q_S, q_D, eta, allow_collapse=False):
    """ry preparation, then each event's gate, then UnitaryGate(U), then
    a measurement of qubit 1 (the decision qubit).

    When `allow_collapse=False` (default), collapse events (`eruption`,
    `ash_fall`) raise `ValueError` per Stage 6 spec. When `allow_collapse=True`,
    collapse events are compiled as mid-circuit `qc.reset(0)` followed by
    `qc.x(0)` (projecting the belief qubit onto |1> = |danger>).
    """
    lo, hi = Q_CLAMP
    p_danger = np.clip(1 - safety, lo, hi)
    theta0 = 2 * np.arcsin(np.sqrt(p_danger))

    qc = QuantumCircuit(2, 1)
    qc.ry(theta0, 0)
    for event in events:
        if event == "none":
            continue
        if event in COLLAPSE_EVENTS:
            if not allow_collapse:
                raise ValueError(
                    f"{event!r} is a collapse event; it has no gate representation "
                    "(see 06-circuits-and-hardware.md)"
                )
            qc.reset(0)
            qc.x(0)
            continue
        axis, angle = EVENT_GATES[event]
        if axis == "ry":
            qc.ry(angle, 0)
        else:
            qc.rx(angle, 0)

    U = build_U(q_S, q_D, eta)
    qc.append(UnitaryGate(U, label="U"), [0, 1])
    qc.measure(1, 0)
    return qc


def build_busemeyer_hamiltonian_circuit(safety, events, q_S, q_D, gamma=0.65, t=1.0):
    """Compiles Busemeyer's 2-qubit Hamiltonian U(t) = exp(-i*t*(pi/2)*(H_a + H_c))
    into a gate-level Qiskit circuit (`jbusemey/ChoiceModeling`)."""
    lo, hi = Q_CLAMP
    p_danger = np.clip(1 - safety, lo, hi)
    theta0 = 2 * np.arcsin(np.sqrt(p_danger))

    qc = QuantumCircuit(2, 1)
    qc.ry(theta0, 0)
    for event in events:
        if event == "none" or event in COLLAPSE_EVENTS:
            continue
        axis, angle = EVENT_GATES[event]
        if axis == "ry":
            qc.ry(angle, 0)
        else:
            qc.rx(angle, 0)

    U_bus = busemeyer_hamiltonian_U(q_S, q_D, gamma=gamma, t=t)
    qc.append(UnitaryGate(U_bus, label="U_Busemeyer"), [0, 1])
    qc.measure(1, 0)
    return qc


def build_luders_sequence_circuit(theta_psi, question_angles):
    """Builds the Rotate-Measure-Rotate-Back sequential projection circuit
    (`WileQ/QCog` `src/qcog/circuits/builder.py`).

    For each question angle theta_i in `question_angles`:
      1. Rotate basis: R_y(-theta_i)
      2. Projective measurement in computational basis -> classical bit c_i
      3. Rotate back to cognitive reference frame: R_y(+theta_i)
    """
    n_q = len(question_angles)
    qc = QuantumCircuit(1, n_q)
    qc.ry(float(theta_psi), 0)
    for idx, theta_i in enumerate(question_angles):
        qc.ry(-float(theta_i), 0)
        qc.measure(0, idx)
        qc.ry(float(theta_i), 0)
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

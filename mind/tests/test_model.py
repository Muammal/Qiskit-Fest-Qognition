"""Stage 1: the deliberation unitary.

Tversky-Shafir calibration (q_S=0.69, q_D=0.59) was exactly solved offline
so that p_protect_closed_form(0.5, x=1, ...) reproduces the observed
"unknown" choice rate of 0.36 to double precision. ETA_TS below is that
exact solve; TECH_A_BUILD_PLAN.md Appendix A rounds it for display to
-0.7854. See docs/tech-a/DECISIONS.md D6.
"""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Statevector, random_density_matrix

from mind.model import kappa_max, build_U, p_protect_closed_form, bloch_vector

ETA_TS = -0.7853897988344999  # exact solve; rounds to -0.7854 (plan Appendix A)


def test_tversky_shafir_calibration():
    qS, qD = 0.69, 0.59

    kmax = kappa_max(qS, qD)
    assert kmax == pytest.approx(0.5588, abs=1e-4)
    kappa = ETA_TS * kmax
    assert kappa == pytest.approx(-0.4389, abs=1e-4)

    assert p_protect_closed_form(0.5, 1.0, qS, qD, ETA_TS) == pytest.approx(0.36, abs=1e-9)
    assert p_protect_closed_form(0.0, 0.0, qS, qD, ETA_TS) == pytest.approx(0.69, abs=1e-9)
    assert p_protect_closed_form(1.0, 0.0, qS, qD, ETA_TS) == pytest.approx(0.59, abs=1e-9)


def test_classical_limit_eta_zero():
    rng = np.random.default_rng(1)
    for _ in range(20):
        qS = rng.uniform(0.02, 0.98)
        qD = rng.uniform(0.02, 0.98)
        p = rng.uniform(0.0, 1.0)
        x = rng.uniform(-1.0, 1.0)
        got = p_protect_closed_form(p, x, qS, qD, 0.0)
        want = (1 - p) * qS + p * qD
        assert got == pytest.approx(want, abs=1e-12)


def test_U_validity_random_sweep():
    rng = np.random.default_rng(42)
    for _ in range(500):
        qS = rng.uniform(0.02, 0.98)
        qD = rng.uniform(0.02, 0.98)
        eta = rng.uniform(-1.0, 1.0)
        U = build_U(qS, qD, eta)

        assert np.max(np.abs(U.T @ U - np.eye(4))) < 1e-10
        assert np.linalg.det(U) == pytest.approx(1.0, abs=1e-9)

        probs = U ** 2
        assert np.all(probs >= -1e-12)
        assert np.all(probs <= 1 + 1e-12)
        # each column of a real orthogonal matrix is a valid probability
        # distribution over the 4 basis states under measurement
        assert np.allclose(probs.sum(axis=0), 1.0, atol=1e-10)


def test_circuit_equals_formula_random_mixed_beliefs():
    qS, qD, eta = 0.69, 0.59, ETA_TS
    U = build_U(qS, qD, eta)
    decision_rho = np.array([[1.0, 0.0], [0.0, 0.0]])  # decision qubit starts at |carry>

    max_diff = 0.0
    for s in range(200):
        belief_rho = random_density_matrix(2, seed=s).data
        x, _y, z = bloch_vector(belief_rho)
        p = (1 - z) / 2

        combined = np.kron(decision_rho, belief_rho)
        evolved = U @ combined @ U.T
        p_protect_sim = (evolved[2, 2] + evolved[3, 3]).real

        closed = p_protect_closed_form(p, x, qS, qD, eta)
        max_diff = max(max_diff, abs(p_protect_sim - closed))

    assert max_diff < 1e-12


def test_gate_circuit_matches_closed_form():
    qS, qD, eta = 0.69, 0.59, ETA_TS
    U = build_U(qS, qD, eta)

    theta0 = np.pi / 2  # pure belief at p=0.5, x=sin(theta0)=1, z=cos(theta0)=0
    qc = QuantumCircuit(2)
    qc.ry(theta0, 0)
    qc.append(UnitaryGate(U), [0, 1])

    p_protect_circuit = Statevector(qc).probabilities([1])[1]
    closed = p_protect_closed_form(0.5, 1.0, qS, qD, eta)
    assert p_protect_circuit == pytest.approx(closed, abs=1e-9)


def test_prisoners_dilemma_bound_cannot_be_fit():
    # q_S=0.97, q_D=0.84 (Prisoner's Dilemma disjunction numbers): the model's
    # most negative achievable P(protect) at eta=-1, x=1, p=0.5 is bounded
    # well above the observed ~0.63, documenting a real limitation.
    qS, qD, eta = 0.97, 0.84, -1.0
    bound = p_protect_closed_form(0.5, 1.0, qS, qD, eta)
    assert bound == pytest.approx(0.8357, abs=1e-3)

    observed = 0.63
    assert bound > observed

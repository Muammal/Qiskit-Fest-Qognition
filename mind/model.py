"""The deliberation unitary (TECH_A_BUILD_PLAN.md Section 4.3).

Two qubits: qubit 0 is belief (|0>=safe, |1>=danger), qubit 1 is decision
(|0>=carry on, |1>=protect). Basis index = belief + 2*decision, so the
decision qubit always starts at |carry>: only two input columns of U
matter, u = U|safe,carry> and w = U|danger,carry>.

Also exports research-paper-backed deliberation models from
`mind.cognition_models` (`busemeyer_hamiltonian`, `busemeyer_hamiltonian_U`,
`p_protect_busemeyer`, `belief_degree_huang`, `p_protect_qlbn`).
"""
import numpy as np

from mind.cognition_models import (
    belief_degree_huang,
    belief_distance_huang,
    busemeyer_hamiltonian,
    busemeyer_hamiltonian_U,
    p_protect_busemeyer,
    p_protect_qlbn,
)

__all__ = [
    "kappa_max",
    "p_protect_superposed",
    "build_U",
    "p_protect_closed_form",
    "bloch_vector",
    "busemeyer_hamiltonian",
    "busemeyer_hamiltonian_U",
    "p_protect_busemeyer",
    "belief_distance_huang",
    "belief_degree_huang",
    "p_protect_qlbn",
]


def kappa_max(q_S, q_D):
    """Largest |kappa| for which cos(beta) stays in [-1, 1]."""
    return min(1.0, np.sqrt((1 - q_S) * (1 - q_D) / (q_S * q_D)))


def build_U(q_S, q_D, eta):
    """Complete u, w to a 4x4 element of SO(4) via QR, columns 0,1 = u, w."""
    kappa = eta * kappa_max(q_S, q_D)

    cos_beta = -kappa * np.sqrt(q_S * q_D) / np.sqrt((1 - q_S) * (1 - q_D))
    cos_beta = np.clip(cos_beta, -1.0, 1.0)
    sin_beta = np.sqrt(max(0.0, 1 - cos_beta ** 2))

    # index: 0=(safe,carry) 1=(danger,carry) 2=(safe,protect) 3=(danger,protect)
    u = np.array([np.sqrt(1 - q_S), 0.0, np.sqrt(q_S), 0.0])
    w = np.array([
        np.sqrt(1 - q_D) * cos_beta,
        np.sqrt(1 - q_D) * sin_beta,
        np.sqrt(q_D) * kappa,
        np.sqrt(q_D) * np.sqrt(max(0.0, 1 - kappa ** 2)),
    ])

    seed = np.column_stack([u, w, np.eye(4)[:, 2], np.eye(4)[:, 3]])
    Q, _R = np.linalg.qr(seed)

    for i in range(2):
        if np.dot(Q[:, i], seed[:, i]) < 0:
            Q[:, i] *= -1
    if np.linalg.det(Q) < 0:
        Q[:, 3] *= -1

    return Q


def p_protect_closed_form(p, x, q_S, q_D, eta):
    """P(protect) for a belief with Bloch components (x, _, z), p=(1-z)/2."""
    kappa = eta * kappa_max(q_S, q_D)
    classical_total = (1 - p) * q_S + p * q_D
    interference = x * np.sqrt(q_S * q_D) * kappa
    return classical_total + interference


def _superposed_angle(x, phi=None):
    from mind.config import SUPERPOSED_PHI

    return abs(x) * (SUPERPOSED_PHI if phi is None else phi)


def p_protect_superposed(p, x, q_S, q_D, eta, phi=None):
    """P(protect) when the decision qubit starts at Ry(phi * |x|)|carry>.

    Why the start has to depend on the belief: with one fixed decision start,
    U|safe,s> and U|danger,s> stay orthogonal, so the Cauchy-Schwarz bound on
    the interference term is unchanged whatever s is. Tying the angle to belief
    coherence keeps q_S and q_D exact for a settled belief (x = 0), and lets an
    unsettled belief reach the columns of U that start at |protect>.

    Operates on a pure belief with the Bloch components of (p, x), scaled to
    the belief's length in the x-z plane, then mixed with the classical total
    for whatever length is missing, so dephasing still reaches the classical
    limit at x = 0.
    """
    U = build_U(q_S, q_D, eta)
    z = 1 - 2 * p
    length = float(np.hypot(x, z))
    classical_total = (1 - p) * q_S + p * q_D
    if length < 1e-12:
        return classical_total
    theta = np.arctan2(x, z)
    belief = np.array([np.cos(theta / 2), np.sin(theta / 2)])
    angle = _superposed_angle(x, phi)
    decision = np.array([np.cos(angle / 2), np.sin(angle / 2)])
    # index = belief + 2 * decision
    psi = U @ np.kron(decision, belief)
    pure = float(psi[2] ** 2 + psi[3] ** 2)
    pure_classical = (np.cos(theta / 2) ** 2) * q_S + (np.sin(theta / 2) ** 2) * q_D
    return float(np.clip(classical_total + length * (pure - pure_classical), 0.0, 1.0))


def bloch_vector(rho_1q):
    """(x, y, z) Bloch components of a single-qubit density matrix."""
    rho = np.asarray(rho_1q)
    x = 2 * rho[0, 1].real
    y = -2 * rho[0, 1].imag
    z = (rho[0, 0] - rho[1, 1]).real
    return x, y, z

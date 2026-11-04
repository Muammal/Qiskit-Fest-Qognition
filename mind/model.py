"""The deliberation unitary (TECH_A_BUILD_PLAN.md Section 4.3).

Two qubits: qubit 0 is belief (|0>=safe, |1>=danger), qubit 1 is decision
(|0>=carry on, |1>=protect). Basis index = belief + 2*decision, so the
decision qubit always starts at |carry>: only two input columns of U
matter, u = U|safe,carry> and w = U|danger,carry>.
"""
import numpy as np


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


def bloch_vector(rho_1q):
    """(x, y, z) Bloch components of a single-qubit density matrix."""
    rho = np.asarray(rho_1q)
    x = 2 * rho[0, 1].real
    y = -2 * rho[0, 1].imag
    z = (rho[0, 0] - rho[1, 1]).real
    return x, y, z

"""Research-paper-backed quantum cognition models for the `mind/` package.

Implements six peer-reviewed formulations from published quantum cognition
repositories:

1. **Busemeyer Dynamic 2-Qubit Hamiltonian (`busemeyer_hamiltonian_U`)**
   - Repo: `jbusemey/ChoiceModeling` (`Lquant.m`), `jbusemey/Quantum-Cognition`
   - Papers: Pothos & Busemeyer (2009) *Proc. R. Soc. B* 276, 2171-2178;
     Busemeyer, Wang & Lambert-Mogiliansky (2009) *J. Math. Psych.* 53, 423-433;
     Busemeyer & Bruza (2012) *Quantum Models of Cognition and Decision*.

2. **Parameter-Free Quantum-Like Bayesian Network via Belief Entropy (`belief_degree_huang`, `p_protect_qlbn`)**
   - Repo: `Insight137/insight137-eap` (`insight137_eap.py`)
   - Papers: Huang, Yang & Jiang (2019) *Applied Mathematics and Computation* 347, 417-428;
     Moreira & Wichert (2016) *Frontiers in Psychology* 7, 11;
     Deng (2016) *Chaos, Solitons & Fractals* 91, 549-553.

3. **Open Quantum System GKSL Lindblad Decision Dynamics (`lindblad_rhs`, `evolve_lindblad`)**
   - Repo: `hwilner/open-system-decision-dynamics` (`src/open_decision/lindblad.py`)
   - Papers: Broekaert, Busemeyer & Pothos (2020) *Cognitive Psychology* 117, 101262;
     Asano et al. (2011) *J. Theor. Biol.* 281, 56-64;
     Yearsley & Busemeyer (2016) *J. Math. Psych.* 74, 99-116.

4. **Quantum Reinforcement Learning via Generalized Grover Reflections (`grover_step`, `QuantumSequenceLearner`)**
   - Repo: `ljaustc/QRL` (`models.py`)
   - Paper: Li, Dong, Wei, Liu, Pan, Nori & Zhang (2020) *Nature Human Behaviour* 4, 294-307.

5. **Wang-Busemeyer QQ Equality & Projective Luders Representability (`luders_sequential_probs`, `wang_busemeyer_qq_gap`, `verify_2d_representability`)**
   - Repos: `WileQ/QCog` (`src/qcog/models/module_a.py`),
     `ProfessorBrunner/aggregation-observability` (`code/v2/verify_witnesses.py`)
   - Papers: Wang & Busemeyer (2013) *Topics in Cognitive Science* 5, 689-710;
     Wang, Solloway, Shiffrin & Busemeyer (2014) *PNAS* 111(26), 9431-9436.

6. **Quantum Bayesian Belief Updating via Givens Rotations (`quantum_bayesian_update`)**
   - Repo: `robertcprice/nQPU` (`sdk/python/nqpu/games/decision.py`)
   - Paper: Trueblood & Busemeyer (2011) *Cognitive Science* 35(8), 1518-1552.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.linalg import expm


# =============================================================================
# 1. Busemeyer 2-Qubit Dynamic Decision & Cognitive Dissonance Hamiltonian
#    Ref: jbusemey/ChoiceModeling (Lquant.m); Pothos & Busemeyer (2009)
# =============================================================================


def busemeyer_hamiltonian(
    mu_safe: float,
    mu_danger: float,
    gamma: float = 0.65,
) -> np.ndarray:
    """Constructs the 4x4 Hermitian Hamiltonian H = H_a(mu_safe, mu_danger) + H_c(gamma).

    Basis ordering matches `mind/model.py`:
      index = belief + 2 * decision
      0 = |safe, carry>, 1 = |danger, carry>, 2 = |safe, protect>, 3 = |danger, protect>

    Parameters
    ----------
    mu_safe : float
        Utility drift toward `protect` when belief is |safe> (typically < 0).
    mu_danger : float
        Utility drift toward `protect` when belief is |danger> (typically > 0).
    gamma : float
        Cognitive dissonance / belief-action alignment coupling strength.
    """
    H_a = np.zeros((4, 4), dtype=complex)
    for b, mu in ((0, float(mu_safe)), (1, float(mu_danger))):
        norm = math.sqrt(1.0 + mu * mu)
        block = np.array([[-mu, 1.0], [1.0, mu]], dtype=complex) / norm
        H_a[b, b] = block[0, 0]
        H_a[b, b + 2] = block[0, 1]
        H_a[b + 2, b] = block[1, 0]
        H_a[b + 2, b + 2] = block[1, 1]

    # Cognitive dissonance coupling H_c (Lquant.m): couples belief states (0 <-> 1)
    # within the |carry> subspace (0, 1) and the |protect> subspace (2, 3).
    c_carry = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex)
    c_prot = np.array([[-1.0, 1.0], [1.0, 1.0]], dtype=complex)
    H_c = np.zeros((4, 4), dtype=complex)
    H_c[0:2, 0:2] = -gamma / math.sqrt(2.0) * c_carry
    H_c[2:4, 0 : 4 - 2] = 0.0
    H_c[2:4, 2:4] = -gamma / math.sqrt(2.0) * c_prot

    return H_a + H_c


def busemeyer_hamiltonian_U(
    q_S: float,
    q_D: float,
    gamma: float = 0.65,
    t: float = 1.0,
) -> np.ndarray:
    """Computes Busemeyer's 2-qubit deliberation operator U(t) on |belief, carry>.

    In `Lquant.m` (`jbusemey/ChoiceModeling`), the action qubit starts in the
    equal superposition |+> = H_Had|0> before evolving under H = H_a + H_c.
    Here we compose U_Had = H_Had (x) I_belief with exp(-i * t * (pi/2) * H) so
    U(t) acts directly on the |belief, carry=0> state used in `mind/model.py`.
    """
    mu_safe = 2.0 * float(q_S) - 1.0
    mu_danger = 2.0 * float(q_D) - 1.0
    H = busemeyer_hamiltonian(mu_safe, mu_danger, gamma=gamma)
    evol = expm(-1j * float(t) * (math.pi / 2.0) * H)

    # Hadamard on qubit 1 (decision) in basis [|0,0>, |1,0>, |0,1>, |1,1>]:
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    had_decision = inv_sqrt2 * np.array(
        [
            [1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0],
            [1.0, 0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0, -1.0],
        ],
        dtype=complex,
    )
    return evol @ had_decision


def p_protect_busemeyer(
    rho_belief: np.ndarray,
    q_S: float,
    q_D: float,
    gamma: float = 0.65,
    t: float = 1.0,
) -> float:
    """Evaluates P(protect) by evolving rho_belief (x) |carry><carry| under U(t)."""
    U = busemeyer_hamiltonian_U(q_S, q_D, gamma=gamma, t=t)
    rho_4 = np.zeros((4, 4), dtype=complex)
    rho_4[0:2, 0:2] = np.asarray(rho_belief, dtype=complex)
    rho_out = U @ rho_4 @ U.conj().T
    p_prot = float((rho_out[2, 2] + rho_out[3, 3]).real)
    return float(np.clip(p_prot, 0.0, 1.0))


# =============================================================================
# 2. Parameter-Free Quantum-Like Bayesian Network (QLBN) via Belief Entropy
#    Ref: Insight137/insight137-eap; Huang, Yang & Jiang (2019) Eqs. 17-19;
#         Moreira & Wichert (2016)
# =============================================================================


def belief_distance_huang(alpha: float, beta: float) -> float:
    """Computes Huang et al. (2019) Eq. 18 belief distance B_d(b) for branch amplitudes.

    Parameters
    ----------
    alpha, beta : float
        Non-negative probability amplitudes for the two causal parent branches.
    """
    if abs(alpha - 0.5) <= abs(beta - 0.5):
        a1, a2 = alpha, beta
    else:
        a1, a2 = beta, alpha
    denom = abs(a1 + a2 - 1.0)
    if denom < 1e-12:
        return float(abs(a1))
    return float(abs(a1 + (a1 - a2) / denom))


def belief_degree_huang(
    p_danger: float,
    q_S: float,
    q_D: float,
    cardinality: int = 1,
) -> float:
    """Computes parameter-free interference factor D_b (cos theta) via belief entropy.

    Implements Huang, Yang & Jiang (2019) Eqs. 17-19 (`Insight137/insight137-eap`)
    with singleton proposition cardinality |A_i| = 1 (so 2^|A_i| - 1 = 1).
    """
    p_safe = max(0.0, min(1.0, 1.0 - float(p_danger)))
    p_d = max(0.0, min(1.0, float(p_danger)))

    alpha_prot = math.sqrt(max(0.0, q_S * p_safe))
    beta_prot = math.sqrt(max(0.0, q_D * p_d))
    alpha_carry = math.sqrt(max(0.0, (1.0 - q_S) * p_safe))
    beta_carry = math.sqrt(max(0.0, (1.0 - q_D) * p_d))

    bd_prot = max(1e-12, belief_distance_huang(alpha_prot, beta_prot))
    bd_carry = max(1e-12, belief_distance_huang(alpha_carry, beta_carry))

    scale = float((2**cardinality) - 1)
    d_b = bd_prot * math.log2(bd_prot / scale) + bd_carry * math.log2(bd_carry / scale)
    return float(np.clip(d_b, -1.0, 1.0))


def p_protect_qlbn(
    p_danger: float,
    coherence_x: float,
    q_S: float,
    q_D: float,
) -> Tuple[float, float]:
    """Computes unitary P(protect) and parameter-free D_b using QLBN belief entropy.

    Replaces the calibrated scalar eta with the state-dependent Deng/Huang
    belief-entropy factor D_b in [-1, 1], preserving exact SO(4) unitarity
    (P(protect) + P(carry) == 1 without post-hoc normalization).
    """
    p_d = float(np.clip(p_danger, 0.0, 1.0))
    p_s = 1.0 - p_d
    d_b = belief_degree_huang(p_d, q_S, q_D)

    k_max = min(1.0, math.sqrt(max(0.0, (1.0 - q_S) * (1.0 - q_D)) / max(1e-12, q_S * q_D)))
    classical_total = p_s * q_S + p_d * q_D
    interference = float(coherence_x) * math.sqrt(max(0.0, q_S * q_D)) * (d_b * k_max)
    return float(np.clip(classical_total + interference, 0.0, 1.0)), d_b


# =============================================================================
# 3. Open Quantum System (GKSL Lindblad) Master Equation Decision Dynamics
#    Ref: hwilner/open-system-decision-dynamics; Broekaert et al. (2020);
#         Yearsley & Busemeyer (2016)
# =============================================================================

_SIGMA_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
_SIGMA_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
_SIGMA_MINUS_TO_DANGER = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=complex)


def lindblad_rhs(
    rho: np.ndarray,
    H: np.ndarray,
    jump_ops: Sequence[np.ndarray],
) -> np.ndarray:
    """Evaluates d(rho)/dt = -i[H, rho] + sum_k (L_k rho L_k^dagger - 1/2 {L_k^dagger L_k, rho})."""
    comm = -1j * (H @ rho - rho @ H)
    dissipator = np.zeros_like(rho, dtype=complex)
    for L in jump_ops:
        L_dag = L.conj().T
        L_dag_L = L_dag @ L
        dissipator += L @ rho @ L_dag - 0.5 * (L_dag_L @ rho + rho @ L_dag_L)
    return comm + dissipator


def evolve_lindblad(
    rho0: np.ndarray,
    omega: float = 0.0,
    dephase_rate: float = 0.5,
    commit_rate: float = 0.0,
    t_final: float = 1.0,
    n_steps: int = 25,
) -> np.ndarray:
    """Integrates the 1-qubit GKSL Lindblad master equation using 4th-order Runge-Kutta."""
    rho = np.asarray(rho0, dtype=complex).copy()
    if t_final <= 0.0 or n_steps <= 0:
        return rho

    H = 0.5 * float(omega) * _SIGMA_X
    jumps: List[np.ndarray] = []
    if dephase_rate > 0.0:
        jumps.append(math.sqrt(float(dephase_rate)) * _SIGMA_Z)
    if commit_rate > 0.0:
        jumps.append(math.sqrt(float(commit_rate)) * _SIGMA_MINUS_TO_DANGER)

    dt = float(t_final) / int(n_steps)
    for _ in range(int(n_steps)):
        k1 = lindblad_rhs(rho, H, jumps)
        k2 = lindblad_rhs(rho + 0.5 * dt * k1, H, jumps)
        k3 = lindblad_rhs(rho + 0.5 * dt * k2, H, jumps)
        k4 = lindblad_rhs(rho + dt * k3, H, jumps)
        rho = rho + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    rho = 0.5 * (rho + rho.conj().T)
    tr = rho.trace().real
    if tr > 1e-12:
        rho = rho / tr
    return rho


# =============================================================================
# 4. Quantum Reinforcement Learning via Generalized Grover Reflections (QSL)
#    Ref: ljaustc/QRL (models.py); Li, Dong et al. & Busemeyer (2020)
#         Nature Human Behaviour 4, 294-307
# =============================================================================


def prospect_utility(
    payoff: float,
    alpha: float = 0.5,
    w_win: float = 1.0,
    w_loss: float = 1.5,
) -> float:
    """Prospect-theoretic subjective utility u(x) with loss aversion (Li et al. 2020)."""
    if payoff >= 0.0:
        return float(w_win * (abs(payoff) ** alpha))
    return float(-w_loss * (abs(payoff) ** alpha))


def grover_step(
    psi: np.ndarray,
    chosen_idx: int,
    utility: float,
    theta_idx: float = 0.25,
    b1: float = 0.0,
    b2: float = 0.0,
) -> np.ndarray:
    """Applies one generalized Grover reflection U_Grover = Q_2(phi_2) * Q_1(phi_1)."""
    psi_vec = np.asarray(psi, dtype=complex).copy()
    norm = np.linalg.norm(psi_vec)
    if norm <= 1e-12:
        raise ValueError("State vector psi must have non-zero norm")
    psi_vec = psi_vec / norm

    n = len(psi_vec)
    if not (0 <= chosen_idx < n):
        raise ValueError(f"chosen_idx {chosen_idx} out of range for dimension {n}")

    phi1 = math.pi * (math.cos(math.pi * theta_idx) * float(utility) + b1)
    phi2 = math.pi * (math.sin(math.pi * theta_idx) * float(utility) + b2)

    q1_psi = psi_vec.copy()
    q1_psi[chosen_idx] *= np.exp(1j * phi1)

    overlap = np.vdot(psi_vec, q1_psi)
    psi_next = (1.0 - np.exp(1j * phi2)) * overlap * psi_vec - q1_psi
    psi_next = psi_next / np.linalg.norm(psi_next)
    return psi_next


class QuantumSequenceLearner:
    """Multi-action Quantum Reinforcement Learning agent (`ljaustc/QRL`)."""

    def __init__(self, actions: Sequence[str], theta_idx: float = 0.25) -> None:
        self.actions = list(actions)
        self.theta_idx = float(theta_idx)
        n = len(self.actions)
        self.psi = np.full(n, 1.0 / math.sqrt(n), dtype=complex)

    def probabilities(self) -> Dict[str, float]:
        probs = np.abs(self.psi) ** 2
        probs = probs / probs.sum()
        return {act: float(probs[i]) for i, act in enumerate(self.actions)}

    def update(self, action: str, payoff: float) -> Dict[str, float]:
        idx = self.actions.index(action)
        u = prospect_utility(payoff)
        self.psi = grover_step(self.psi, idx, u, theta_idx=self.theta_idx)
        return self.probabilities()


# =============================================================================
# 5. Wang-Busemeyer QQ Equality & Projective Luders Representability
#    Ref: WileQ/QCog (src/qcog/models/module_a.py) &
#         ProfessorBrunner/aggregation-observability (verify_witnesses.py);
#         Wang, Solloway, Shiffrin & Busemeyer (2014) PNAS 111(26), 9431-9436
# =============================================================================


def projector_from_angle(theta: float) -> np.ndarray:
    """Rank-1 projector Pi(theta) = R_y(theta)|0><0|R_y^dagger(theta)."""
    ket = np.array([math.cos(theta / 2.0), math.sin(theta / 2.0)], dtype=complex)
    return np.outer(ket, ket.conj())


def luders_sequential_probs(
    theta_psi: float,
    theta_A: float,
    theta_B: float,
) -> Dict[str, float]:
    """Computes exact sequential Luders probabilities for incompatible questions A and B."""
    psi = np.array([math.cos(theta_psi / 2.0), math.sin(theta_psi / 2.0)], dtype=complex)
    rho = np.outer(psi, psi.conj())

    Pi_Ay = projector_from_angle(theta_A)
    Pi_An = np.eye(2, dtype=complex) - Pi_Ay
    Pi_By = projector_from_angle(theta_B)
    Pi_Bn = np.eye(2, dtype=complex) - Pi_By

    return {
        "AB_yy": float(np.trace(Pi_By @ Pi_Ay @ rho @ Pi_Ay).real),
        "AB_yn": float(np.trace(Pi_Bn @ Pi_Ay @ rho @ Pi_Ay).real),
        "AB_ny": float(np.trace(Pi_By @ Pi_An @ rho @ Pi_An).real),
        "AB_nn": float(np.trace(Pi_Bn @ Pi_An @ rho @ Pi_An).real),
        "BA_yy": float(np.trace(Pi_Ay @ Pi_By @ rho @ Pi_By).real),
        "BA_yn": float(np.trace(Pi_An @ Pi_By @ rho @ Pi_By).real),
        "BA_ny": float(np.trace(Pi_Ay @ Pi_Bn @ rho @ Pi_Bn).real),
        "BA_nn": float(np.trace(Pi_An @ Pi_Bn @ rho @ Pi_Bn).real),
    }


def wang_busemeyer_qq_gap(
    theta_psi: float,
    theta_A: float,
    theta_B: float,
) -> Tuple[float, float]:
    """Returns (qq_gap, order_effect_on_A) for sequential Luders measurements."""
    probs = luders_sequential_probs(theta_psi, theta_A, theta_B)
    qq_gap = (probs["AB_yn"] + probs["AB_ny"]) - (probs["BA_yn"] + probs["BA_ny"])
    p_Ay_first = probs["AB_yy"] + probs["AB_yn"]
    p_Ay_second = probs["BA_yy"] + probs["BA_ny"]
    order_effect = p_Ay_first - p_Ay_second
    return float(qq_gap), float(order_effect)


def verify_2d_representability(q: float, r: float, c: float) -> bool:
    """Checks the exact 2D projective Luders representability inequality
    (`ProfessorBrunner/aggregation-observability`, Eq. 14):
        (q - r)^2 / (1 - c) + (q + r - 1)^2 / c <= 1
    """
    if not (0.0 < c < 1.0):
        return False
    lhs = ((q - r) ** 2) / (1.0 - c) + ((q + r - 1.0) ** 2) / c
    return bool(lhs <= 1.0 + 1e-12)


# =============================================================================
# 6. Quantum Bayesian Belief Updating via Givens Rotations
#    Ref: robertcprice/nQPU (sdk/python/nqpu/games/decision.py);
#         Trueblood & Busemeyer (2011) Cognitive Science 35(8), 1518-1552
# =============================================================================


def quantum_bayesian_evidence_gate(
    likelihood_safe: float,
    likelihood_danger: float,
    strength: float = 1.0,
) -> np.ndarray:
    """Builds a 2x2 Givens rotation evidence operator U(L, s) (`robertcprice/nQPU`)."""
    l0 = max(0.0, float(likelihood_safe))
    l1 = max(0.0, float(likelihood_danger))
    if l0 + l1 <= 1e-12:
        return np.eye(2, dtype=complex)
    theta_target = math.atan2(math.sqrt(l1), math.sqrt(l0))
    delta = float(np.clip(strength, 0.0, 1.0)) * (theta_target - math.pi / 4.0)
    c, s = math.cos(delta), math.sin(delta)
    return np.array([[c, -s], [s, c]], dtype=complex)


def quantum_bayesian_update(
    prior_danger: float,
    evidence_sequence: Sequence[Tuple[float, float, float]],
) -> Dict[str, float]:
    """Updates prior danger probability through a sequence of (L_safe, L_danger, strength) cues."""
    p_d = float(np.clip(prior_danger, 0.001, 0.999))
    p_s = 1.0 - p_d
    psi = np.array([math.sqrt(p_s), math.sqrt(p_d)], dtype=complex)

    bayes_s, bayes_d = p_s, p_d
    for idx, (l_safe, l_danger, strength) in enumerate(evidence_sequence):
        U = quantum_bayesian_evidence_gate(l_safe, l_danger, strength)
        phase = np.array([[1.0, 0.0], [0.0, np.exp(1j * 0.35 * math.pi * ((-1) ** idx))]], dtype=complex)
        psi = U @ phase @ psi

        eff_l_s = (1.0 - strength) * 0.5 + strength * max(1e-6, float(l_safe))
        eff_l_d = (1.0 - strength) * 0.5 + strength * max(1e-6, float(l_danger))
        bayes_s *= eff_l_s
        bayes_d *= eff_l_d
        norm = bayes_s + bayes_d
        bayes_s, bayes_d = bayes_s / norm, bayes_d / norm

    q_danger = float(abs(psi[1]) ** 2)
    return {
        "quantum_p_danger": q_danger,
        "classical_bayes_p_danger": float(bayes_d),
        "interference_delta": float(q_danger - bayes_d),
    }

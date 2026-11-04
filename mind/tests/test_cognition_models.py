"""Tests for the 6 research-paper-backed quantum cognition models in `mind/cognition_models.py`."""
import math
import numpy as np
import pytest
from qiskit.quantum_info import Statevector

import contracts
from mind.belief import prepare_belief, run_events
from mind.circuits import (
    build_busemeyer_hamiltonian_circuit,
    build_decision_circuit,
    build_luders_sequence_circuit,
)
from mind.cognition_models import (
    QuantumSequenceLearner,
    belief_degree_huang,
    busemeyer_hamiltonian,
    busemeyer_hamiltonian_U,
    evolve_lindblad,
    luders_sequential_probs,
    p_protect_busemeyer,
    p_protect_qlbn,
    quantum_bayesian_update,
    verify_2d_representability,
    wang_busemeyer_qq_gap,
)
from mind.quantum_mind import quantum_decide


def _sample_state(safety=0.55, stress=0.25, events=None):
    return {
        "day": 1,
        "hour": 12,
        "pos": [20, 20],
        "needs": {
            "hunger": 0.8,
            "thirst": 0.8,
            "warmth": 0.8,
            "energy": 0.8,
            "safety": safety,
            "morale": 0.8,
        },
        "stress": stress,
        "injured": False,
        "inventory": {"wood": 2, "food": 1},
        "recent_events": events if events is not None else ["tremor", "gas_plume"],
    }


def test_busemeyer_hamiltonian_is_hermitian_and_unitary():
    """Verifies Busemeyer (2009/2012) 2-qubit Hamiltonian H = H_a + H_c (`jbusemey/ChoiceModeling`)."""
    H = busemeyer_hamiltonian(mu_safe=-0.6, mu_danger=0.7, gamma=0.65)
    assert H.shape == (4, 4)
    assert np.allclose(H, H.conj().T, atol=1e-12)

    U = busemeyer_hamiltonian_U(0.20, 0.85, gamma=0.65, t=1.0)
    assert np.allclose(U.conj().T @ U, np.eye(4), atol=1e-12)

    rho_safe = prepare_belief(0.95)
    rho_danger = prepare_belief(0.05)
    p_safe = p_protect_busemeyer(rho_safe, 0.15, 0.88, gamma=0.25, t=1.0)
    p_danger = p_protect_busemeyer(rho_danger, 0.15, 0.88, gamma=0.25, t=1.0)
    assert 0.0 <= p_safe < p_danger <= 1.0


def test_busemeyer_hamiltonian_circuit_matches_density_matrix():
    """Verifies the Qiskit circuit for Busemeyer's Hamiltonian matches p_protect_busemeyer."""
    safety = 0.75
    events = ["tremor", "gas_plume"]
    q_S, q_D = 0.22, 0.82
    qc = build_busemeyer_hamiltonian_circuit(safety, events, q_S, q_D, gamma=0.65, t=1.0)
    qc.remove_final_measurements()
    p_circuit = Statevector(qc).probabilities([1])[1]

    rho = run_events(prepare_belief(safety), events, lam=0.0)
    p_dm = p_protect_busemeyer(rho, q_S, q_D, gamma=0.65, t=1.0)
    assert p_circuit == pytest.approx(p_dm, abs=1e-9)


def test_huang_qlbn_belief_entropy_produces_parameter_free_disjunction_effect():
    """Verifies Huang et al. (2019) / `Insight137/insight137-eap` belief entropy interference."""
    # Tversky & Shafir (1992) / Pothos & Busemeyer (2009) disjunction rates:
    d_b_ts = belief_degree_huang(0.5, 0.69, 0.59)
    assert -1.0 < d_b_ts < -0.5

    # Under full coherence (x = 1.0 at p = 0.5), QLBN interference shifts P(protect)
    # below both conditional branch probabilities (0.59 and 0.69), violating the
    # classical Sure-Thing Principle without any tuned free parameter!
    p_q, _ = p_protect_qlbn(0.5, 1.0, 0.69, 0.59)
    p_cl, _ = p_protect_qlbn(0.5, 0.0, 0.69, 0.59)
    assert p_cl == pytest.approx(0.64, abs=1e-6)
    assert p_q < 0.59


def test_open_system_lindblad_preserves_positivity_and_damps_coherence():
    """Verifies GKSL Lindblad evolution (`hwilner/open-system-decision-dynamics`)."""
    rho0 = prepare_belief(0.5)  # pure |+> state with coherence x = 1
    rho_dephased = evolve_lindblad(rho0, omega=0.0, dephase_rate=1.0, commit_rate=0.0, t_final=1.0, n_steps=40)
    assert rho_dephased.trace().real == pytest.approx(1.0, abs=1e-12)
    eigvals = np.linalg.eigvalsh(rho_dephased)
    assert np.all(eigvals >= -1e-12)
    # Off-diagonal decays as exp(-2 * gamma * t) = exp(-2)
    assert abs(rho_dephased[0, 1]) == pytest.approx(0.5 * math.exp(-2.0), rel=1e-3)

    # Commitment amplitude damping drives population toward |danger> (rho[1,1] -> 1)
    rho_committed = evolve_lindblad(rho0, omega=0.0, dephase_rate=0.2, commit_rate=2.5, t_final=2.0, n_steps=60)
    assert rho_committed[1, 1].real > 0.95


def test_qrl_grover_sequence_learner_amplifies_rewarded_actions():
    """Verifies Li et al. & Busemeyer (2020) Grover Quantum RL (`ljaustc/QRL`)."""
    qrl = QuantumSequenceLearner(contracts.ACTIONS, theta_idx=0.25)
    p0 = qrl.probabilities()["hide"]
    assert p0 == pytest.approx(1.0 / len(contracts.ACTIONS), abs=1e-9)

    p_after_pos = qrl.update("hide", payoff=1.2)["hide"]
    assert p_after_pos > p0

    qrl_neg = QuantumSequenceLearner(contracts.ACTIONS, theta_idx=0.25)
    p_after_neg = qrl_neg.update("hide", payoff=-1.2)["hide"]
    assert p_after_pos != pytest.approx(p_after_neg)


def test_wang_busemeyer_qq_equality_and_2d_representability():
    """Verifies Wang & Busemeyer (2013/2014) QQ equality (`WileQ/QCog`) & Brunner witness."""
    for t_psi, t_a, t_b in [
        (0.15 * math.pi, 0.55 * math.pi, 0.20 * math.pi),
        (0.40 * math.pi, 0.10 * math.pi, 0.70 * math.pi),
        (0.75 * math.pi, 0.30 * math.pi, 0.85 * math.pi),
    ]:
        qq_gap, order_effect = wang_busemeyer_qq_gap(t_psi, t_a, t_b)
        assert qq_gap == pytest.approx(0.0, abs=1e-12)
        assert abs(order_effect) > 0.01

        probs = luders_sequential_probs(t_psi, t_a, t_b)
        q = probs["AB_yy"] + probs["AB_yn"]
        r = probs["BA_yy"] + probs["BA_yn"]
        c = math.cos((t_a - t_b) / 2.0) ** 2
        assert verify_2d_representability(q, r, c) is True

    # Impossible (non-quantum) triple violates 2D representability
    assert verify_2d_representability(0.95, 0.05, 0.95) is False


def test_luders_sequence_qiskit_circuit_and_collapse_circuit():
    """Verifies Rotate-Measure-Rotate-Back Qiskit circuit and collapse circuit support."""
    qc_seq = build_luders_sequence_circuit(0.3 * math.pi, [0.5 * math.pi, 0.2 * math.pi])
    assert qc_seq.num_qubits == 1 and qc_seq.num_clbits == 2

    # Collapse circuit with allow_collapse=True succeeds on eruption/ash_fall
    qc_col = build_decision_circuit(0.85, ["eruption"], 0.69, 0.59, -0.7853897988344999, allow_collapse=True)
    assert "reset" in qc_col.count_ops()


def test_quantum_bayesian_givens_order_sensitivity():
    """Verifies Trueblood & Busemeyer (2011) Givens belief updating (`robertcprice/nQPU`)."""
    cue_tremor = (0.25, 0.80, 0.75)
    cue_calm = (0.75, 0.30, 0.75)
    res_ab = quantum_bayesian_update(0.35, [cue_tremor, cue_calm])
    res_ba = quantum_bayesian_update(0.35, [cue_calm, cue_tremor])

    # Classical Bayes is order-invariant; Quantum Givens update is order-sensitive
    assert res_ab["classical_bayes_p_danger"] == pytest.approx(res_ba["classical_bayes_p_danger"], abs=1e-12)
    assert res_ab["quantum_p_danger"] != pytest.approx(res_ba["quantum_p_danger"], abs=1e-3)


@pytest.mark.parametrize(
    "model_name",
    ["default", "busemeyer_hamiltonian", "qlbn_entropy", "lindblad_open"],
)
def test_quantum_decide_supports_all_paper_backed_models(model_name):
    state = _sample_state()
    decision = quantum_decide(state, cognition_model=model_name)
    contracts.validate_decision(decision)
    assert decision["quantum"]["cognition_model"] == model_name
    assert "d_b_huang" in decision["quantum"]
    assert "p_protect_busemeyer" in decision["quantum"]

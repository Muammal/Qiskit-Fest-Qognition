"""Stage 4: the decision function.

Tests 2, 3, 5 use the real initial agent state / stub prior from this
repo (SurvivalAgent, contracts.get_prior); the plan's own numbers are from
a prototype run and may not match exactly (its Section 4.7 test 3 says to
assert inequalities, not equalities, for that reason).
"""

import time

import contracts
import pytest
from engine.agent import SurvivalAgent
from engine.simulation import SimulationEngine

from mind.quantum_mind import (
    classical_mixture_decide,
    decision_probs,
    quantum_decide,
)


def test_decision_probs_split():
    prior = {"forage": 0.1, "drink": 0.1, "build_shelter": 0.1, "rest": 0.1, "explore": 0.4, "craft": 0.1, "hide": 0.1}
    probs = decision_probs(0.4, prior)
    assert probs["hide"] == pytest.approx(0.4, abs=1e-9)
    carry_on_sum = sum(v for k, v in probs.items() if k != "hide")
    assert carry_on_sum == pytest.approx(0.6, abs=1e-9)
    assert probs["explore"] == pytest.approx(0.6 * 0.4 / 0.9, abs=1e-9)
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-9)


def test_contract_seven_actions_sum_to_one_and_diagnostics_present():
    state = SurvivalAgent().get_state()
    decision = quantum_decide(state)
    assert contracts.validate_decision(decision) is True
    assert set(decision["probs"]) == set(contracts.ACTIONS)
    assert sum(decision["probs"].values()) == pytest.approx(1.0, abs=1e-6)

    q = decision["quantum"]
    for key in ("p_danger", "p_protect", "p_classical", "lam", "q_safe", "q_danger", "order_gap", "reflex", "decision_rule"):
        assert key in q


@pytest.mark.parametrize(
    "test_name",
    [
        "test_contracts_stubs",
        "test_quantum_order_effect_in_contracts",
        "test_quantum_stress_decoherence",
        "test_volcanic_order_effect_and_lethal_overlay",
        "test_urgent_thirst_beats_warning_in_both_stubs",
        "test_simulation_engine_run",
        "test_demo_pack_validity",
    ],
)
def test_repo_compatibility(monkeypatch, test_name):
    import test_contracts_and_engine as repo_tests

    monkeypatch.setattr(contracts, "quantum_decide", quantum_decide)
    getattr(repo_tests, test_name)()


def test_volcano_order_demo():
    state = SurvivalAgent().get_state()

    state_a = dict(state, recent_events=["tremor", "gas_plume"])
    state_b = dict(state, recent_events=["gas_plume", "tremor"])
    dec_a = quantum_decide(state_a)
    dec_b = quantum_decide(state_b)

    assert dec_a["action"] != dec_b["action"]
    gap = dec_a["quantum"]["p_protect"] - dec_b["quantum"]["p_protect"]
    assert abs(gap) > 0.2


def test_after_eruption_no_interference():
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["tremor", "ash_fall", "eruption"]
    decision = quantum_decide(state)
    q = decision["quantum"]
    assert q["p_danger"] == pytest.approx(1.0, abs=1e-9)
    assert q["p_protect"] == pytest.approx(q["q_danger"], abs=1e-9)


def test_reflex_thirst_overrides():
    state = SurvivalAgent().get_state()
    state["needs"]["thirst"] = 0.1
    decision = quantum_decide(state)
    assert decision["action"] == "drink"
    assert decision["reason"].startswith("Reflex")


def test_classical_mixture_control():
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["tremor", "gas_plume"]
    decision = classical_mixture_decide(state)
    q = decision["quantum"]
    assert q["p_protect"] == pytest.approx(q["p_classical"], abs=1e-9)
    assert "Order effect" not in decision["reason"]


def test_determinism_seeded_run():
    timeline_1 = SimulationEngine(seed=7, decide_fn=quantum_decide).run()
    timeline_2 = SimulationEngine(seed=7, decide_fn=quantum_decide).run()
    actions_1 = [s["action"] for s in timeline_1["steps"]]
    actions_2 = [s["action"] for s in timeline_2["steps"]]
    assert actions_1 == actions_2


def test_speed_under_10ms_per_call():
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["tremor", "gas_plume"]
    n = 50
    start = time.perf_counter()
    for _ in range(n):
        quantum_decide(state)
    elapsed_ms_per_call = (time.perf_counter() - start) * 1000 / n
    assert elapsed_ms_per_call < 10.0

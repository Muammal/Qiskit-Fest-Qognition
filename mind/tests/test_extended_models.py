"""Phase 2 opt-in models and arms. None of them may touch the default path."""
import math

import numpy as np
import pytest

from engine.agent import SurvivalAgent
from engine.events import VOLCANIC
from engine.simulation import SimulationEngine
from engine.volcano import WARNING_SWEEP_ONSET_RANGE
from mind.config import ETA, MARKOV_HESITATION, SUPERPOSED_PHI
from mind.human_tests.extended import fit_markov, known_rows, markov_prediction, markov_split_half, study_eta
from mind.model import build_U, p_protect_closed_form, p_protect_superposed
from mind.quantum_mind import (
    _decide,
    classical_mixture_decide,
    classical_no_interference_decide,
    markov_hesitation_decide,
    markov_p_protect,
    quantum_decide,
)


def tremor_state():
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["none", "tremor", "gas_plume"]
    return state


# classical_no_interference ---------------------------------------------------

def test_no_interference_keeps_the_belief_and_drops_k():
    state = tremor_state()
    full = quantum_decide(state)["quantum"]
    plain = classical_no_interference_decide(state)["quantum"]
    assert plain["p_danger"] == pytest.approx(full["p_danger"])
    assert plain["coherence"] == pytest.approx(full["coherence"])
    assert plain["p_protect"] == pytest.approx(plain["p_classical"])
    assert plain["p_protect"] != pytest.approx(full["p_protect"])


def test_no_interference_still_has_an_order_effect_through_belief():
    forward = tremor_state()
    reverse = dict(forward, recent_events=["none", "gas_plume", "tremor"])
    a, b = (classical_no_interference_decide(s)["quantum"]["p_protect"] for s in (forward, reverse))
    assert abs(a - b) > 0.01


def test_no_interference_differs_from_the_mixture():
    state = tremor_state()
    assert classical_no_interference_decide(state)["quantum"]["p_danger"] != pytest.approx(
        classical_mixture_decide(state)["quantum"]["p_danger"])


# markov_hesitation -----------------------------------------------------------

def test_markov_settled_belief_never_hesitates():
    assert markov_p_protect(0.0, 0.7, 0.6, 0.5) == pytest.approx(0.7)
    assert markov_p_protect(1.0, 0.7, 0.6, 0.5) == pytest.approx(0.6)


def test_markov_can_hit_tversky_shafir():
    assert markov_p_protect(0.5, 0.69, 0.59, 1 - 0.36 / 0.64) == pytest.approx(0.36)


def test_markov_has_no_coherence_and_no_interference():
    state = tremor_state()
    q = markov_hesitation_decide(state)["quantum"]
    assert q["coherence"] == pytest.approx(0.0, abs=1e-12)
    assert q["p_protect"] == pytest.approx(markov_p_protect(q["p_danger"], q["q_safe"], q["q_danger"]))


def test_markov_fit_recovers_a_known_h():
    rows = [dict(a=a, b=b, seen=(1 - .3) * (a + b) / 2) for a, b in ((.8, .6), (.7, .4), (.9, .9))]
    assert fit_markov(rows) == pytest.approx(.3)


def test_markov_split_half_uses_every_split_and_never_scores_a_training_row():
    rows = [r for r in known_rows() if r["scored"]]
    result = markov_split_half(rows)
    assert result["splits"] == 70
    assert result["h_min"] <= MARKOV_HESITATION <= result["h_max"]
    assert MARKOV_HESITATION == pytest.approx(result["h_median"], abs=5e-4)
    assert set(result["prediction"]) == {r["study"] for r in rows}


def test_markov_prediction_formula():
    assert markov_prediction(dict(a=.8, b=.6), .5) == pytest.approx(.35)


# qr_unitary_superposed -------------------------------------------------------

@pytest.mark.parametrize("q_s, q_d", [(.69, .59), (.97, .84), (.3, .8)])
def test_superposed_keeps_known_rates_exact(q_s, q_d):
    assert p_protect_superposed(0.0, 0.0, q_s, q_d, ETA, phi=1.0) == pytest.approx(q_s)
    assert p_protect_superposed(1.0, 0.0, q_s, q_d, ETA, phi=1.0) == pytest.approx(q_d)


def test_superposed_at_phi_zero_is_the_default_model():
    for p, x in ((.5, 1.0), (.3, .4), (.8, -.2)):
        assert p_protect_superposed(p, x, .69, .59, ETA, phi=0.0) == pytest.approx(
            p_protect_closed_form(p, x, .69, .59, ETA), abs=1e-9)


def test_superposed_reaches_the_prisoners_dilemma_value():
    bound = (.97 + .84) / 2 - math.sqrt(.03 * .16)
    assert bound == pytest.approx(.836, abs=1e-3) and bound > .63
    values = [p_protect_superposed(.5, 1., .97, .84, ETA, phi=phi) for phi in np.linspace(-np.pi, np.pi, 361)]
    assert min(values) < .63 < max(values)


def test_superposed_is_classical_with_no_coherence():
    assert p_protect_superposed(.5, 0.0, .69, .59, ETA, phi=1.0) == pytest.approx(.64)


def test_a_fixed_superposed_start_cannot_escape_the_bound():
    """Why the angle depends on x. With one start in every condition, the bound follows the new rates."""
    rng = np.random.default_rng(3)
    for _ in range(200):
        q_s, q_d, phi = rng.uniform(.05, .95), rng.uniform(.05, .95), rng.uniform(-np.pi, np.pi)
        U = build_U(q_s, q_d, rng.uniform(-1, 1))
        start = np.array([np.cos(phi / 2), np.sin(phi / 2)])
        protect = lambda psi: psi[2] ** 2 + psi[3] ** 2
        safe = U @ np.kron(start, [1., 0.])
        danger = U @ np.kron(start, [0., 1.])
        unknown = U @ np.kron(start, np.array([1., 1.]) / math.sqrt(2))
        a, b = protect(safe), protect(danger)
        assert protect(unknown) >= (a + b) / 2 - math.sqrt((1 - a) * (1 - b)) - 1e-9
        assert np.dot(safe, danger) == pytest.approx(0.0, abs=1e-9)


def test_superposed_is_opt_in():
    state = tremor_state()
    assert quantum_decide(state)["quantum"]["p_protect"] == pytest.approx(
        quantum_decide(state, cognition_model="default")["quantum"]["p_protect"])
    chosen = quantum_decide(state, cognition_model="qr_unitary_superposed")
    assert chosen["quantum"]["cognition_model"] == "qr_unitary_superposed"
    if SUPERPOSED_PHI != 0:
        assert chosen["quantum"]["p_protect"] != pytest.approx(quantum_decide(state)["quantum"]["p_protect"])


# per-study eta ---------------------------------------------------------------

def test_study_eta_hits_a_reachable_study():
    row = dict(a=.69, b=.59, seen=.36)
    raw, usable = study_eta(row)
    assert raw == usable == pytest.approx(ETA, abs=1e-3)
    assert p_protect_closed_form(.5, 1., row["a"], row["b"], usable) == pytest.approx(.36, abs=1e-3)


def test_study_eta_flags_the_prisoners_dilemma_as_out_of_reach():
    raw, usable = study_eta(dict(a=.97, b=.84, seen=.63))
    assert raw < -1 and usable == -1


# engine hooks ----------------------------------------------------------------

@pytest.mark.parametrize("mind", ["classical_no_interference", "markov_hesitation"])
def test_engine_runs_the_new_arms(mind):
    sim = SimulationEngine(seed=3, mind_type=mind)
    assert sim.run()["world"]["mind"] == mind and sim.steps


def test_decide_eta_argument_defaults_to_config():
    state = tremor_state()
    assert _decide(state, eta=ETA)["quantum"]["p_protect"] == quantum_decide(state)["quantum"]["p_protect"]
    assert _decide(state, eta=0.0)["quantum"]["p_protect"] == pytest.approx(
        classical_no_interference_decide(state)["quantum"]["p_protect"])


@pytest.mark.parametrize("lead", [0, 2, 6, 12, 30])
def test_lead_override_sets_the_first_sign_exactly(lead):
    for seed in range(12):
        sim = SimulationEngine(seed=seed, mind_type="classical", warning_lead_override_hours=lead)
        timeline = sim.run()
        assert sim.volcano.erupts
        assert WARNING_SWEEP_ONSET_RANGE[0] <= sim.volcano.onset_step <= WARNING_SWEEP_ONSET_RANGE[1]
        assert sim.volcano.first_pdc_step == sim.volcano.onset_step
        sign = next(i for i, s in enumerate(sim.volcano.world_events) if s in VOLCANIC)
        assert (sim.volcano.first_pdc_step - sign) * 2 == lead
        assert timeline["evacuation"]["warning_lead_hours"] in (lead, None) or timeline["evacuation"]["first_sign_step"] is None


def test_lead_override_keeps_the_onset_across_leads():
    onsets = {SimulationEngine(seed=9, warning_lead_override_hours=h).volcano.onset_step for h in (0, 8, 30)}
    assert len(onsets) == 1


def test_lead_override_rejects_a_lead_that_cannot_fit():
    with pytest.raises(ValueError):
        SimulationEngine(seed=1, warning_lead_override_hours=100)


def test_default_volcano_is_unchanged_by_the_new_arguments():
    plain = SimulationEngine(seed=11).run()
    named = SimulationEngine(seed=11, warning_lead_override_hours=None, spawn_override=None, decision_seed=None).run()
    assert plain["steps"] == named["steps"] and plain["outcome"] == named["outcome"]


def test_decision_seed_only_changes_decisions():
    a = SimulationEngine(seed=2, decision_seed=100, mind_type="classical")
    b = SimulationEngine(seed=2, decision_seed=200, mind_type="classical")
    assert a.volcano.world_events == b.volcano.world_events


def test_spawn_override_moves_only_the_start():
    sim = SimulationEngine(seed=1, spawn_override=[26, 29])
    assert sim.agent.pos == [26, 29]

"""Phase 2d: dephasing that follows elapsed time. per_slot stays the default."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from engine.agent import SurvivalAgent
from engine.simulation import SimulationEngine
from mind.belief import apply_event, prepare_belief
from mind.config import DEPHASING_MODE, REFERENCE_SLOT_SECONDS
from mind.decoherence import apply_phase_damping, decoherence_strength, decoherence_time, lam_for_interval
from mind.model import bloch_vector
from mind.quantum_mind import quantum_decide

DELAY = Path(__file__).resolve().parents[1] / "results" / "delay_experiment.json"
STRESSES = (.1, .25, .4, .6, .85, .95)


def test_default_mode_is_per_slot():
    assert DEPHASING_MODE == "per_slot"


@pytest.mark.parametrize("stress", STRESSES)
def test_two_hours_reproduces_the_slot_lambda(stress):
    assert lam_for_interval(stress, REFERENCE_SLOT_SECONDS) == pytest.approx(decoherence_strength(stress))


@pytest.mark.parametrize("stress", STRESSES)
def test_two_short_slots_compose_into_one_long_one(stress):
    assert (1 - lam_for_interval(stress, 300)) ** 2 == pytest.approx(1 - lam_for_interval(stress, 600))


def test_shorter_intervals_dephase_less():
    assert lam_for_interval(.6, 300) < lam_for_interval(.6, 900) < lam_for_interval(.6, 7200)


def test_limits():
    assert decoherence_time(.1) == math.inf and lam_for_interval(.1, 7200) == 0.0
    assert decoherence_time(.95) == 0.0 and lam_for_interval(.95, 10) == 1.0


def test_per_time_at_two_hours_equals_per_slot():
    state = SurvivalAgent().get_state()
    state.update(stress=.6, recent_events=["storm", "tremor", "gas_plume"])
    assert state["dt_seconds"] == 7200
    assert quantum_decide(state, dephasing_mode="per_time")["quantum"]["p_protect"] == pytest.approx(
        quantum_decide(state)["quantum"]["p_protect"], abs=1e-12)


def test_per_time_needs_the_state_key_or_falls_back():
    state = SurvivalAgent().get_state()
    state.update(stress=.6, recent_events=["storm", "tremor", "gas_plume"])
    del state["dt_seconds"]
    assert quantum_decide(state, dephasing_mode="per_time")["quantum"]["lam"] == quantum_decide(state)["quantum"]["lam"]


def test_per_slot_ignores_dt_seconds():
    state = SurvivalAgent().get_state()
    state.update(stress=.6, recent_events=["storm", "tremor", "gas_plume"])
    short = dict(state, dt_seconds=300)
    assert quantum_decide(short)["quantum"]["p_protect"] == quantum_decide(state)["quantum"]["p_protect"]
    assert quantum_decide(short, dephasing_mode="per_time")["quantum"]["lam"] < quantum_decide(state)["quantum"]["lam"]


def test_engines_report_their_step_length():
    assert SimulationEngine(seed=1).agent.get_state()["dt_seconds"] == 7200
    from engine.pompeii import PompeiiSimulation
    from engine.titanic import TitanicSimulation
    from engine.waterloo import WaterlooSimulation

    assert TitanicSimulation(seed=1).agent.get_state()["dt_seconds"] == 300
    assert PompeiiSimulation(seed=1, population=200).agent.get_state()["dt_seconds"] == 900
    assert WaterlooSimulation(seed=1).agent.get_state()["dt_seconds"] == 60
    assert WaterlooSimulation(seed=1, decision_seconds=120).agent.get_state()["dt_seconds"] == 120


def test_repeated_slots_follow_the_same_exponential_as_the_delay_experiment():
    """Same form as e^(-t/T2): slots of length dt at tau = T2 give exactly that curve."""
    data = json.loads(DELAY.read_text(encoding="utf-8"))
    t2, rows = data["t2_us"], data["rows"]
    rho0 = apply_event(prepare_belief(.5), "none")
    x0 = bloch_vector(rho0)[0]
    for row in rows:
        lam_step = 1 - math.exp(-1.0 / t2)  # one microsecond per slot
        rho = rho0
        for _ in range(int(row["t_us"])):
            rho = apply_phase_damping(rho, lam_step)
        assert bloch_vector(rho)[0] / x0 == pytest.approx(row["coherence_theory_exp_t_over_t2"], rel=1e-9)


def test_measured_decay_matches_that_form_after_the_readout_offset():
    """The simulated measurement, divided by its t=0 value to remove readout error, tracks e^(-t/T2)."""
    data = json.loads(DELAY.read_text(encoding="utf-8"))
    rows = data["rows"]
    start = rows[0]["coherence_x_measured"]
    ratios = [r["coherence_x_measured"] / start / r["coherence_theory_exp_t_over_t2"] for r in rows if r["coherence_x_measured"] > .05]
    assert np.median(ratios) == pytest.approx(1.0, abs=.1)

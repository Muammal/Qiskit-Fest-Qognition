"""Phase 1 guards: opt-in flags stay off by default, and docs stop repeating fixed errors."""
import json
import re
from pathlib import Path

import pytest

import contracts
from engine.agent import SurvivalAgent
from engine.simulation import SimulationEngine
from mind.config import EVENT_GATES
from mind.quantum_mind import order_gap_at_lambda

ROOT = Path(__file__).resolve().parents[2]


def test_event_gates_are_only_ry_and_rx():
    assert {axis for axis, _ in EVENT_GATES.values()} == {"ry", "rx"}


@pytest.mark.parametrize("name", ["README.md", "docs/TECH_A_QUANTUM_MIND.md", "docs/FULL_SYSTEM_REPORT.md",
                                  "docs/PRESENTATION_SLIDES.md", "docs/TECH_A_B_C_INTEGRATION.md"])
def test_docs_do_not_claim_rz_event_gates(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert not re.search(r"R_z\(|Ry\*Rz|Ry\(θ\)Rz|R_y\(θ\)R_z", text)


def test_order_gap_helper_matches_a_direct_comparison():
    state = SurvivalAgent().get_state()
    assert order_gap_at_lambda(state, lam=0.0) == pytest.approx(-order_gap_at_lambda(state, "gas_plume", "tremor", 0.0))
    assert abs(order_gap_at_lambda(state, lam=0.0)) > abs(order_gap_at_lambda(state, lam=1.0))


def test_gui_order_line_uses_computed_numbers():
    from engine.gui import order_effect_hint

    state = SurvivalAgent().get_state()
    coherent, control = (abs(order_gap_at_lambda(state, lam=lam)) for lam in (0.0, 1.0))
    assert f"{coherent:.2f}" in order_effect_hint() and f"{control:.2f}" in order_effect_hint()


def test_faq_has_no_unfilled_placeholders_or_hardware_claims():
    faq = ROOT / "RISKS_AND_FAQ.md"
    if not faq.exists():  # .gitignore keeps this file out of a fresh checkout
        pytest.skip("RISKS_AND_FAQ.md is not tracked")
    text = faq.read_text(encoding="utf-8")
    assert not re.search(r"\[N\]|\[X\]|\[Backend name\]|\[date\]|\[library\]", text)
    assert "and we did" not in text
    assert "No IBM hardware job was submitted" in text


def test_priors_file_says_it_is_not_used():
    meta = json.loads((ROOT / "data" / "priors.json").read_text(encoding="utf-8"))
    assert meta["used_in_decisions"] is False and "NOT used" in meta["status"]


def test_priors_do_not_change_when_the_atus_hours_change(monkeypatch):
    state = SurvivalAgent().get_state()
    before = contracts.get_prior(state)
    monkeypatch.setitem(contracts.ATUS_PRIORS_META, "atus_daily_hours_reference", {"rest": 99.0})
    assert contracts.get_prior(state) == before


def _island_positions(walk, seed=4):
    sim = SimulationEngine(seed=seed, scenario="island", mind_type="classical", explore_walk=walk,
                           decide_fn=lambda state: dict(action="explore", probs={"explore": 1.0}, reason="test"))
    sim.run(max_steps=8)
    return [tuple(step["pos_after"]) for step in sim.steps]


def test_grover_walk_is_off_by_default():
    assert _island_positions("random") == [
        tuple(step["pos_after"]) for step in SimulationEngine(
            seed=4, scenario="island", mind_type="classical",
            decide_fn=lambda state: dict(action="explore", probs={"explore": 1.0}, reason="test")).run(max_steps=8)["steps"]]


def test_grover_walk_runs_through_explore_step(monkeypatch):
    calls = []
    original = contracts.explore_step

    def spy(pos, world, mode="quantum"):
        calls.append(mode)
        return original(pos, world, mode)

    monkeypatch.setattr(contracts, "explore_step", spy)
    positions = _island_positions("grover")
    assert calls and set(calls) == {"quantum"}
    assert len(set(positions)) > 1


def test_grover_walk_stays_on_walkable_land():
    sim = SimulationEngine(seed=7, scenario="island", mind_type="classical", explore_walk="grover",
                           decide_fn=lambda state: dict(action="explore", probs={"explore": 1.0}, reason="test"))
    sim.run(max_steps=8)
    assert all(sim.world.walkable(tuple(step["pos_after"])) for step in sim.steps)


def test_titanic_note_is_in_both_places():
    for name in ("workboard/ENGINE_STATUS.md", "docs/TITANIC_MODEL.md"):
        assert "Two different Titanics" in (ROOT / name).read_text(encoding="utf-8")

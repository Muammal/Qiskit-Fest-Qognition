"""
test_contracts_and_engine.py - Daily Integration Test Suite
Owned by Tech C (Integration, Contracts, Engine).
"""

import os
import glob
import json
import pytest
import contracts
from engine.world import IslandWorld
from engine.agent import SurvivalAgent
from engine.events import EventGenerator
from engine.simulation import SimulationEngine


def test_contracts_constants():
    assert len(contracts.ACTIONS) == 7
    assert "forage" in contracts.ACTIONS
    assert "drink" in contracts.ACTIONS
    assert "build_shelter" in contracts.ACTIONS
    assert len(contracts.EVENTS) == 6
    assert "storm" in contracts.EVENTS
    assert "injury" in contracts.EVENTS


def test_contracts_stubs():
    # Construct minimal valid state
    state = {
        "day": 1,
        "hour": 12,
        "pos": [15, 15],
        "needs": {
            "hunger": 0.5,
            "thirst": 0.2, # low thirst -> should prioritize drinking
            "warmth": 0.8,
            "energy": 0.7,
            "safety": 0.9,
            "morale": 0.8
        },
        "stress": 0.2,
        "injured": False,
        "inventory": {"wood": 1, "food": 0},
        "recent_events": ["none"]
    }
    assert contracts.validate_state(state) is True

    # 1. Test get_prior
    priors = contracts.get_prior(state)
    assert isinstance(priors, dict)
    assert sum(priors.values()) == pytest.approx(1.0, abs=0.02)
    assert priors["drink"] > priors["explore"]

    # 2. Test classical_decide
    c_dec = contracts.classical_decide(state)
    assert contracts.validate_decision(c_dec) is True
    assert c_dec["action"] == "drink"

    # 3. Test quantum_decide
    q_dec = contracts.quantum_decide(state)
    assert contracts.validate_decision(q_dec) is True
    assert "probs" in q_dec
    assert len(q_dec["reason"]) > 0


def test_quantum_order_effect_in_contracts():
    state_a = {
        "day": 1, "hour": 14, "pos": [10, 10],
        "needs": {"hunger": 0.5, "thirst": 0.5, "warmth": 0.5, "energy": 0.5, "safety": 0.5, "morale": 0.5},
        "stress": 0.3, "injured": True, "inventory": {},
        "recent_events": ["injury", "storm"] # Injury then Storm
    }
    state_b = {
        "day": 1, "hour": 14, "pos": [10, 10],
        "needs": {"hunger": 0.5, "thirst": 0.5, "warmth": 0.5, "energy": 0.5, "safety": 0.5, "morale": 0.5},
        "stress": 0.3, "injured": True, "inventory": {},
        "recent_events": ["storm", "injury"] # Storm then Injury
    }
    dec_a = contracts.quantum_decide(state_a)
    dec_b = contracts.quantum_decide(state_b)
    # Different order must produce distinct probability states / reasons
    assert dec_a["probs"] != dec_b["probs"]
    assert "Order effect" in dec_a["reason"] or "Order effect" in dec_b["reason"]


def test_world_generation():
    world = IslandWorld(width=40, height=40, seed=1234)
    assert world.width == 40
    assert world.height == 40
    assert len(world.tiles) == 40
    assert len(world.tiles[0]) == 40
    # Outer borders should be ocean water (0)
    assert world.tiles[0][0] == 0
    assert world.tiles[39][39] == 0
    # Interior should contain substantial land (plains, forest, mountains)
    land_tiles = sum(1 for row in world.tiles for tile in row if tile in (1, 2, 3, 4))
    assert land_tiles > 300


def test_simulation_engine_run():
    sim = SimulationEngine(seed=42, mind_type="quantum", noise_source="fake_backend")
    timeline = sim.run(max_steps=10)

    assert "world" in timeline
    assert "steps" in timeline
    assert len(timeline["steps"]) > 0
    assert timeline["outcome"] in ("survived", "died")

    # Verify that every logged step conforms to contracts
    for step in timeline["steps"]:
        contracts.validate_state(step["state"])
        contracts.validate_decision({
            "action": step["action"],
            "probs": step["probs"],
            "reason": step["reason"]
        })


def test_timeline_json_validity():
    with open("timeline.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "world" in data
    assert "steps" in data
    assert len(data["steps"]) >= 5
    for step in data["steps"]:
        contracts.validate_state(step["state"])


def test_quantum_stress_decoherence():
    state_stressed = {
        "day": 1, "hour": 14, "pos": [10, 10],
        "needs": {"hunger": 0.2, "thirst": 0.1, "warmth": 0.2, "energy": 0.2, "safety": 0.1, "morale": 0.2},
        "stress": 0.85, # High chronic stress
        "injured": True,
        "inventory": {},
        "recent_events": ["injury", "storm"]
    }
    decision = contracts.quantum_decide(state_stressed)
    assert contracts.validate_decision(decision) is True
    assert "Decoherence" in decision["reason"]


def test_demo_pack_validity():
    demo_files = glob.glob("demo-pack/*.json")
    assert len(demo_files) >= 5
    for path in demo_files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "world" in data
        assert "steps" in data
        assert "outcome" in data
        for step in data["steps"]:
            contracts.validate_state(step["state"])
            contracts.validate_decision({
                "action": step["action"],
                "probs": step["probs"],
                "reason": step["reason"]
            })


def test_gui_module():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    app = IslandVisualizerApp(seed=42, mind_type="quantum", start_screen="sim")
    assert app.world.width == 40
    assert app.agent.is_alive is True
    app.step_forward()
    assert app.step_idx == 1
    assert len(app.history) == 1
    app.draw()


def test_gui_home_and_end_screen():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    # 1. Initialize at Home Screen
    app = IslandVisualizerApp(seed=101, mind_type="quantum", start_screen="home")
    assert app.app_state == "home"
    assert app.show_debrief_modal is False

    # 2. Configure via Home Screen controls
    app.mind_type = "classical"
    app.seed = 202
    app.max_steps = 12
    app._init_simulation()
    app.app_state = "sim"
    assert app.app_state == "sim"
    assert app.mind_type == "classical"
    assert app.seed == 202

    # 3. Step forward until step horizon or termination
    for _ in range(12):
        if not app.agent.is_alive or app.step_idx >= app.max_steps:
            break
        app.step_forward()

    # 4. Debrief modal triggers at conclusion of event/horizon
    assert app.show_debrief_modal is True
    app.draw()


def test_gui_fullscreen_and_aspect_scaling():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    app = IslandVisualizerApp(seed=101, mind_type="quantum", start_screen="home")
    # Test initial windowed state
    assert app.is_fullscreen is False
    app.present()

    # Toggle to fullscreen
    app.toggle_fullscreen()
    assert app.is_fullscreen is True
    app.present()

    # Toggle back to windowed
    app.toggle_fullscreen()
    assert app.is_fullscreen is False
    app.present()

    # Verify virtual mouse coordinate mapping
    virt_pos = app.get_virtual_mouse_pos()
    assert len(virt_pos) == 2
    assert 0 <= virt_pos[0] <= app.canvas.get_width()
    assert 0 <= virt_pos[1] <= app.canvas.get_height()

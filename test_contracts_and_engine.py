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
    assert len(contracts.EVENTS) == 10
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
    app._handle_sim_click(app.btn_nav_mind.rect.center)
    assert app.engine.decide_fn is contracts.classical_decide
    assert app.engine.mind_type == 'classical'
    app.step_forward()
    assert app.history[-1]['action'] == contracts.classical_decide(app.engine.steps[-1]['state'])['action']


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


def test_gui_event_choice_and_scenarios():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    app = IslandVisualizerApp(start_screen="event_choice")
    assert app.app_state == "event_choice"
    app.draw()

    # Click island scenario
    app._handle_mouse_click(app.btn_choice_island.rect.center)
    assert app.app_state == "home"
    assert app.scenario == "island"
    assert app.world.scenario == "island"

    # Back to scenario hub
    app._handle_mouse_click(app.btn_home_back_scenario.rect.center)
    assert app.app_state == "event_choice"

    # Click volcano scenario
    app._handle_mouse_click(app.btn_choice_volcano.rect.center)
    assert app.app_state == "home"
    assert app.scenario == "volcano"
    assert app.world.scenario == "volcano"

    # Launch into sim
    app._handle_mouse_click(app.btn_hero_launch.rect.center)
    assert app.app_state == "sim"
    app.step_forward()
    assert app.step_idx == 1
    app.draw()


def test_fixed_map_and_evacuation_geometry():
    import math
    from engine.world import MAP_SEED
    a, b = SimulationEngine(seed=11), SimulationEngine(seed=17)
    w = a.world
    assert w.tiles == b.world.tiles
    assert w.seed == MAP_SEED
    assert w.get_tile(*w.spawn_pos) == 2
    assert w.zones[w.spawn_pos[1]][w.spawn_pos[0]] == 2
    assert min(math.dist(w.spawn_pos,p) for p in w.stream_tiles) <= 3
    assert w.get_tile(*w.vent) == 3
    for x,y in w.assembly_points:
        assert w.zones[y][x] == 0 and w.get_tile(x,y)
        assert min(math.dist((x,y),p) for p in w.clean_springs) <= 2
    assert tuple(w.route_from_spawn[0]) == tuple(w.spawn_pos)
    assert tuple(w.route_from_spawn[-1]) in w.assembly_points
    for p,q in zip(w.route_from_spawn,w.route_from_spawn[1:]):
        assert abs(p[0]-q[0])+abs(p[1]-q[1]) == 1
        assert w.walkable(q)
    assert not w.is_near_water(0,0)


def test_volcano_population_timing_and_policy_independence():
    from engine.volcano import VolcanoModel
    w = IslandWorld()
    models = [VolcanoModel(seed,w) for seed in range(90)]
    assert .5 < sum(v.erupts for v in models)/len(models) < .8
    assert any(v.first_pdc_step == v.onset_step for v in models if v.erupts)
    assert any(v.first_pdc_step > v.onset_step for v in models if v.erupts)
    for v in models:
        assert len(v.phases) == len(v.hazard_by_step) == 36
        if v.erupts:
            assert 4 <= v.onset_step <= 19
            assert v.onset_step <= v.first_pdc_step < 36
        else:
            assert v.onset_step is None and v.first_pdc_step is None
            assert all(not h['new_pdc'] and not h['new_lava'] for h in v.hazard_by_step)
    def policy(action):
        return lambda state: dict(action=action,probs={a:float(a==action) for a in contracts.ACTIONS},reason='test')
    a = SimulationEngine(seed=1,decide_fn=policy('hide')).run()
    b = SimulationEngine(seed=1,decide_fn=policy('rest')).run()
    assert a['world']['volcano'] == b['world']['volcano']
    assert a['world']['noise_source'] == 'stub'
    assert all('pos_after' in r and 'phase' in r for r in a['steps'])


def test_movement_warning_water_and_lava():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    start = list(a.pos)
    a.execute_action('hide',w)
    assert a.pos == start
    a.apply_event('tremor',False)
    route = w.path(a.pos,w.assembly_points)
    a.execute_action('hide',w)
    assert a.pos == list(route[8])
    a.execute_action('hide',w)
    a.execute_action('hide',w)
    assert w.zones[a.pos[1]][a.pos[0]] == 0
    a.needs['thirst'] = .1
    a.execute_action('drink',w)
    assert a.needs['thirst'] > .1
    assert w.zones[a.pos[1]][a.pos[0]] != 2
    a.pos = list(start)
    w.lava.add(tuple(route[1]))
    reroute = w.path(start,w.assembly_points)
    assert tuple(route[1]) not in reroute
    a.injured = True
    assert a.movement_budget(w) == 4
    a.hour = 22
    assert a.movement_budget(w) < 4


def test_contextual_events_and_three_day_physiology():
    from engine.volcano import VolcanoModel
    w = IslandWorld()
    e = EventGenerator(5)
    v = VolcanoModel(5,w)
    e.prepare(v)
    for t,event in enumerate(e.world_events):
        if event == 'cold_night':
            hour = (8+2*t)%24
            assert hour >= 20 or hour <= 6
    e.world_events = ['none']*36
    e.uniforms = [.1]*36
    assert e.step_event(1,12,w.spawn_pos,False,False,action='rest',world=w,t=0) != 'find_food'
    assert e.step_event(1,12,w.spawn_pos,False,False,action='forage',world=w,t=0) == 'find_food'
    a = SurvivalAgent()
    a.needs['hunger'] = 0
    for _ in range(28):
        a.step_decay(True)
    assert a.is_alive
    a.step_decay(True)
    assert a.cause_of_death == 'dehydration'


def test_volcanic_order_effect_and_lethal_overlay():
    state = SurvivalAgent().get_state()
    state['recent_events'] = ['tremor','gas_plume']
    a = contracts.quantum_decide(state)
    state['recent_events'].reverse()
    b = contracts.quantum_decide(state)
    assert a['probs'] != b['probs']
    sim = SimulationEngine(seed=1,decide_fn=lambda s: dict(action='rest',probs={'rest':1},reason='test'))
    sim.world.pdc.add(tuple(sim.agent.pos))
    sim.step()
    assert sim.agent.cause_of_death == 'pyroclastic_flow'


def test_arriving_flow_cannot_be_outrun_by_hide():
    sim = SimulationEngine(seed=1,decide_fn=lambda s: dict(action='hide',probs={'hide':1},reason='test'))
    sim.agent.volcanic_sign_seen = True
    start = list(sim.agent.pos)
    sim.volcano.hazard_by_step[0]['new_pdc'] = [tuple(start)]
    sim.step()
    assert sim.agent.pos == start
    assert sim.agent.cause_of_death == 'pyroclastic_flow'


def test_weather_persistence_and_shelter_independence():
    from engine.volcano import VolcanoModel
    a,b = EventGenerator(12),EventGenerator(12)
    w = IslandWorld()
    v = VolcanoModel(12,w)
    a.prepare(v)
    b.prepare(v)
    assert a.weather == b.weather
    assert sum(x==y for x,y in zip(a.weather,a.weather[1:])) > 12
    for t in range(36):
        kwargs = dict(day=1,hour=(8+2*t)%24,current_pos=w.spawn_pos,injured=False,world=w,t=t)
        assert a.step_event(in_shelter=True,**kwargs) == b.step_event(in_shelter=False,**kwargs)


def test_ashy_stream_is_unpalatable_not_poison():
    w = IslandWorld()
    w.clean_springs = []
    w.freshwater_tiles = list(w.stream_tiles)
    w.ash = .7
    a = SurvivalAgent(w.spawn_pos)
    a.needs['thirst'] = .1
    morale = a.needs['morale']
    a.execute_action('drink',w)
    assert a.needs['thirst'] == pytest.approx(.4)
    assert a.needs['morale'] < morale
    assert a.is_alive


def test_wood_requires_forest_and_building_can_use_plain():
    w = IslandWorld()
    plain = next((x,y) for y in range(w.height) for x in range(w.width) if w.get_tile(x,y)==1)
    a = SurvivalAgent(list(plain))
    a.execute_action('build_shelter',w)
    assert a.inventory['wood'] == 0
    a.inventory['wood'] = 2
    a.execute_action('build_shelter',w)
    assert w.is_in_shelter(*plain)


def test_timeline_preserves_built_shelters_and_initial_terrain():
    sim = SimulationEngine(seed=1)
    x, y = sim.world.spawn_pos
    original = sim.world.get_tile(x, y)
    sim.world.set_shelter(x, y)
    exported = sim.timeline()
    assert exported['world']['tiles'][y][x] == 4
    assert exported['world']['initial_tiles'][y][x] == original
    exported['world']['tiles'][y][x] = 0
    assert sim.world.is_in_shelter(x, y)


def test_urgent_thirst_beats_warning_in_both_stubs():
    state = SurvivalAgent().get_state()
    state['needs']['thirst'] = .1
    state['recent_events'] = ['tremor', 'ash_fall', 'eruption']
    for decide in (contracts.classical_decide, contracts.quantum_decide):
        assert decide(state)['action'] == 'drink'


def test_seeded_pulses_and_nonmonotone_ash():
    from engine.volcano import VolcanoModel
    w = IslandWorld()
    footprints = set()
    for seed in range(12):
        v = VolcanoModel(seed, w)
        if not v.erupts:
            continue
        assert v.world_events.count('ash_fall') <= .6*(36-v.onset_step)
        assert v.world_events.count('eruption') >= 2
        footprint = {tuple(p) for h in v.hazard_by_step for p in h['new_pdc']}
        assert all(w.zones[y][x] != 0 for x,y in footprint)
        footprints.add(frozenset(footprint))
        assert sum(len(h['new_lava']) for h in v.hazard_by_step) >= 15
    assert len(footprints) > 1


def test_integration_noise_label():
    assert SimulationEngine(noise_source='external_test').timeline()['world']['noise_source'] == 'external_test'


def test_shelter_limits_exposure_and_outdoor_rest_warming():
    bare = SimulationEngine(seed=1, decide_fn=lambda s: dict(action='rest',probs={'rest':1},reason='thermal control'))
    covered = SimulationEngine(seed=1, decide_fn=bare.decide_fn)
    covered.world.set_shelter(*covered.agent.pos)
    for sim in (bare, covered):
        sim.volcano.hazard_by_step[0]['ash'] = .8
        sim.agent.needs['warmth'] = .5
        sim.step()
    assert covered.agent.needs['warmth'] > bare.agent.needs['warmth'] + .08


def test_gathered_wood_builds_shelter_after_evacuation():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    a.execute_action('forage', w)
    a.execute_action('forage', w)
    assert a.inventory['wood'] == 2
    a.volcanic_sign_seen = True
    for _ in range(4):
        a.execute_action('hide', w)
    assert w.zones[a.pos[1]][a.pos[0]] == 0
    a.execute_action('build_shelter', w)
    assert w.is_in_shelter(*a.pos)
    assert a.inventory['wood'] == 0


def test_forest_canopy_does_not_replace_built_shelter():
    policy = lambda s: dict(action='hide', probs={'hide': 1}, reason='exposure control')
    bare, sheltered = (SimulationEngine(seed=1, decide_fn=policy) for _ in range(2))
    safe_forest = next((x, y) for y in range(bare.world.height) for x in range(bare.world.width)
                       if bare.world.get_tile(x, y) == 2 and bare.world.zones[y][x] == 0)
    sheltered.world.set_shelter(*safe_forest)
    for sim in (bare, sheltered):
        sim.agent.pos = list(safe_forest)
        sim.agent.needs['warmth'] = .8
        sim.event_gen.weather = ['rain'] * 36
        sim.event_gen.world_events = ['none'] * 36
        sim.event_gen.uniforms = [.99] * 36
        for hazard in sim.volcano.hazard_by_step:
            hazard.update(ash=1, new_pdc=[], new_lahar=[], new_lava=[])
        sim.run(12)
    assert sheltered.agent.is_alive
    assert sheltered.agent.needs['warmth'] > bare.agent.needs['warmth'] + .4


def test_pdc_runout_and_width_vary_reproducibly_across_seeds():
    from engine.volcano import VolcanoModel
    world = IslandWorld()
    footprints = set()
    erupting = 0
    for seed in range(120):
        model = VolcanoModel(seed, world)
        if not model.erupts:
            continue
        erupting += 1
        footprint = frozenset(tuple(p) for h in model.hazard_by_step for p in h['new_pdc'])
        assert footprint
        assert all(world.get_tile(x, y) and world.zones[y][x] != 0 for x, y in footprint)
        assert model.export_dict() == VolcanoModel(seed, world).export_dict()
        footprints.add(footprint)
    assert len(footprints) > erupting / 2


def test_island_agent_moves_and_explores():
    """Verify that agent in procedural island mode moves dynamically across the map."""
    sim = SimulationEngine(seed=42, scenario="island")
    tl = sim.run(max_steps=24)
    assert len(tl["steps"]) >= 20
    positions = [s["pos_after"] for s in tl["steps"]]
    distinct_positions = {tuple(p) for p in positions}
    # Agent should actively navigate, explore terrain, and not remain frozen
    assert len(distinct_positions) >= 8
    # Actions should encompass exploration, foraging, drinking, or resting
    actions_taken = {s["action"] for s in tl["steps"]}
    assert "explore" in actions_taken or "forage" in actions_taken


def test_gui_event_choice_card_click():
    """Verify clicking scenario cards directly selects the scenario."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    app = IslandVisualizerApp(start_screen="event_choice")
    assert app.app_state == "event_choice"

    # Click directly within card 1 rect
    app._handle_mouse_click((app.card1_rect.left + 50, app.card1_rect.top + 50))
    assert app.app_state == "home"
    assert app.scenario == "island"

    # Return and click within card 2 rect
    app.app_state = "event_choice"
    app._handle_mouse_click((app.card2_rect.left + 50, app.card2_rect.top + 50))
    assert app.app_state == "home"
    assert app.scenario == "volcano"

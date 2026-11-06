"""
test_contracts_and_engine.py - Daily Integration Test Suite
Owned by Tech C (Integration, Contracts, Engine).
"""

import os
import glob
import json
import math
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
    from mind.quantum_mind import classical_mixture_decide as _cmd
    assert app.engine.decide_fn is _cmd
    assert app.engine.mind_type == 'classical_mixture'
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
    assert tuple(a.pos) in route[1:]
    assert w.route_minutes(route[:route.index(tuple(a.pos))+1]) <= 120
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
    assert a.movement_budget(w) == 60
    a.hour = 22
    assert a.movement_budget(w) < 60


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
    assert sim.agent.is_alive and sim.agent.injured
    assert not sim.world.walkable(sim.agent.pos)


def test_arriving_flow_cannot_be_outrun_by_hide():
    sim = SimulationEngine(seed=1,decide_fn=lambda s: dict(action='hide',probs={'hide':1},reason='test'))
    sim.agent.volcanic_sign_seen = True
    start = list(sim.agent.pos)
    sim.volcano.hazard_by_step[0]['new_pdc'] = [tuple(start)]
    sim.volcano.hazard_by_step[0]['active_pdc'] = [tuple(start)]
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
            hazard.update(ash=1, ash_grid=['9'*40]*40, new_pdc=[], new_lahar=[], new_lava=[], active_pdc=[], active_lahar=[], surge=[])
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

def test_elevation_land_and_peak():
    w = IslandWorld()
    assert all((w.elevation[y][x]>0)==bool(w.get_tile(x,y)) for y in range(40) for x in range(40))
    peak=max((w.elevation[y][x],(x,y)) for y in range(40) for x in range(40))
    import math
    assert 950<peak[0]<1100 and math.dist(peak[1],w.vent)<=2


def test_drainage_descends_to_coast():
    w=IslandWorld()
    assert len(w.valleys)>=2 and w.stream_tiles==w.valleys[0][1:]
    for valley in w.valleys:
        assert all(w.elevation[b[1]][b[0]]<=w.elevation[a[1]][a[0]] for a,b in zip(valley,valley[1:]))
        assert any(w.get_tile(*q)==0 for q in w.neighbors(valley[-1]))
    for p,q in w.drainage.items():
        assert w.elevation[q[1]][q[0]]<w.elevation[p[1]][p[0]]


def test_assembly_separation_and_fastest_route():
    import math
    w=IslandWorld()
    angles=[math.atan2(y-w.vent[1],x-w.vent[0]) for x,y in w.assembly_points]
    assert math.acos(math.cos(angles[0]-angles[1]))>=math.pi/3
    assert len(w.routes_from_spawn)==len(w.assembly_points)
    assert w.route_minutes(w.route_from_spawn)==min(map(w.route_minutes,w.routes_from_spawn))


def test_tobler_flat_and_slopes():
    import math
    w=IslandWorld()
    a,b=(10,20),(11,20)
    w.tiles[20][11]=1
    w.elevation[20][10]=w.elevation[20][11]=100
    assert w.travel_minutes(a,b)==pytest.approx(.25/(6*math.exp(-3.5*.05)*.6)*60)
    w.elevation[20][11]=200
    assert w.travel_minutes(a,b)>w.travel_minutes(b,a)


def test_least_time_route_against_independent_relaxation():
    w=IslandWorld()
    start=tuple(w.spawn_pos)
    distances={start:0.}
    frontier=[start]
    while frontier:
        p=frontier.pop(0)
        for q in w.neighbors(p):
            if w.walkable(q):
                cost=distances[p]+w.travel_minutes(p,q)
                if cost<distances.get(q,float('inf'))-1e-10:
                    distances[q]=cost
                    frontier.append(q)
    assert w.route_minutes(w.path(start,w.assembly_points))==pytest.approx(min(distances[p] for p in w.assembly_points))


def test_minimum_movement_and_hot_start():
    w=IslandWorld()
    a=SurvivalAgent(w.spawn_pos)
    target=next(q for q in w.neighbors(tuple(a.pos)) if w.walkable(q))
    w.pdc.add(tuple(a.pos))
    a.movement_budget=lambda world:.0001
    a.walk_to(w,[target])
    assert tuple(a.pos)==target


def _controlled_engine(action='rest'):
    sim=SimulationEngine(seed=1,decide_fn=lambda s:dict(action=action,probs={action:1},reason='controlled'))
    sim.event_gen.world_events=['none']*36
    sim.event_gen.uniforms=[.99]*36
    return sim


def test_active_flow_start_and_end_lethality():
    sim=_controlled_engine()
    sim.volcano.hazard_by_step[0]['active_pdc']=[tuple(sim.agent.pos)]
    sim.step()
    assert sim.agent.cause_of_death=='pyroclastic_flow'
    sim=_controlled_engine('forage')
    target=sim.world.route_from_spawn[-1]
    sim.world.food_tiles=[target]
    sim.agent.pos=list(sim.world.route_from_spawn[-2])
    sim.volcano.hazard_by_step[0]['active_lahar']=[target]
    sim.step()
    assert sim.agent.cause_of_death=='lahar'


def test_dry_lahar_deposit_passable():
    sim=_controlled_engine()
    sim.world.lahar.add(tuple(sim.agent.pos))
    sim.step()
    assert sim.agent.is_alive and sim.world.walkable(sim.agent.pos)


def test_surge_injures_without_killing():
    sim=_controlled_engine()
    sim.volcano.hazard_by_step[0]['surge']=[tuple(sim.agent.pos)]
    sim.step()
    assert sim.agent.is_alive and sim.agent.injured and sim.agent.stress>.15


def test_rain_reactivates_lahars():
    from engine.volcano import VolcanoModel
    w=IslandWorld()
    weather=['rain' if i%2 else 'calm' for i in range(36)]
    model=VolcanoModel(1,w,weather=weather)
    wet=[h for t,h in enumerate(model.hazard_by_step) if h['active_lahar']]
    assert len(wet)>1 and any(not h['new_lahar'] for h in wet)
    assert all(not h['active_lahar'] for t,h in enumerate(model.hazard_by_step) if weather[t]=='calm')


def test_wind_ash_grid_and_pulse_recurrence():
    from engine.volcano import VolcanoModel
    import math
    w=IslandWorld()
    model=VolcanoModel(1,w)
    covered=set()
    repeated=False
    for t,h in enumerate(model.hazard_by_step):
        assert len(h['ash_grid'])==40 and all(len(row)==40 and set(row)<=set('0123456789') for row in h['ash_grid'])
        assert 0<=h['wind_deg']<360
        assert set(h['surge']).isdisjoint(h['active_pdc'])
        assert set(h['new_pdc'])==set(h['active_pdc'])-covered
        repeated |= bool(covered.intersection(h['active_pdc']))
        covered.update(h['new_pdc'])
        if t:
            assert abs((h['wind_deg']-model.hazard_by_step[t-1]['wind_deg']+180)%360-180)<=6.01
    h=model.hazard_by_step[-1]
    assert len(set(''.join(h['ash_grid'])))>3 and repeated
    angle=math.radians(h['wind_deg'])
    dx,dy=round(8*math.sin(angle)),round(-8*math.cos(angle))
    assert int(h['ash_grid'][20+dy][20+dx])>int(h['ash_grid'][20-dy][20-dx])


def test_lava_descends_and_is_rate_limited():
    from engine.volcano import VolcanoModel
    w=IslandWorld()
    lava=set()
    for h in VolcanoModel(1,w).hazard_by_step:
        assert len(h['new_lava'])<=2
        batch = set(h['new_lava'])
        for p in h['new_lava']:
            assert p==w.vent or any(q in lava | batch and w.elevation[p[1]][p[0]]<=w.elevation[q[1]][q[0]] for q in w.neighbors(p))
            lava.add(p)


def test_food_depletes_and_auto_eats_at_any_action():
    w=IslandWorld()
    a=SurvivalAgent(w.spawn_pos)
    w.food_tiles=[tuple(a.pos)]
    a.execute_action('forage',w)
    a.execute_action('forage',w)
    assert a.inventory['food']==1
    a.needs['hunger']=.1
    a.execute_action('hide',w)
    assert a.inventory['food']==0 and a.needs['hunger']==pytest.approx(.5)
    b=SurvivalAgent(w.spawn_pos)
    b.inventory['food']=4
    w.depleted_food.clear()
    b.execute_action('forage',w)
    assert b.inventory['food']==4 and not w.depleted_food


def test_rest_accelerates_healing():
    w=IslandWorld()
    a,b=SurvivalAgent(w.spawn_pos),SurvivalAgent(w.spawn_pos)
    for agent in (a,b):
        agent.injured=True
        agent.injury_cooldown=4
    for _ in range(2):
        a.execute_action('rest',w)
        b.execute_action('hide',w)
    assert not a.injured and b.injured and b.injury_cooldown==2


def test_existing_shelter_keeps_wood():
    w=IslandWorld()
    a=SurvivalAgent(w.spawn_pos)
    w.set_shelter(*a.pos)
    a.inventory['wood']=6
    a.execute_action('build_shelter',w)
    assert a.inventory['wood']==6


def test_boar_escape_depends_on_fatigue():
    a=SurvivalAgent()
    a.apply_event('animal',False)
    assert not a.injured
    a.needs['energy']=.2
    a.apply_event('animal',False)
    assert a.injured


def test_eruption_safety_stress_and_hidden_mind_state():
    sim=_controlled_engine('hide')
    sim.event_gen.world_events=['eruption']*36
    sim.step()
    zone=sim.world.zones[sim.agent.pos[1]][sim.agent.pos[0]]
    assert sim.agent.needs['safety']<=(.8,.5,.3)[zone]
    assert sim.agent.stress>=(.3,.45,.6)[zone]
    assert sim.agent.needs['morale']<.8
    assert set(sim.steps[0]['state'])==set(SurvivalAgent().get_state())


def test_evacuation_summary_matches_records():
    timeline=_controlled_engine('hide').run()
    e=timeline['evacuation']
    assert len(timeline['world']['weather'])==36
    for label,zone in [('left_danger_step',2),('reached_safe_step',0)]:
        matching=[r['t'] for r in timeline['steps'] if (timeline['world']['evacuation_map']['zones'][r['pos_after'][1]][r['pos_after'][0]]!=2 if zone==2 else timeline['world']['evacuation_map']['zones'][r['pos_after'][1]][r['pos_after'][0]]==0)]
        assert e[label]==(matching[0] if matching else None)
    if e['margin_hours'] is not None:
        assert e['margin_hours']==2*(e['first_pdc_step']-e['reached_safe_step'])


def test_gui_event_history_weather_and_replay_reset():
    os.environ['SDL_VIDEODRIVER']='dummy'
    import pygame
    from engine.gui import IslandVisualizerApp, TILE_SIZE
    app=IslandVisualizerApp(start_screen='sim')
    app.max_steps=36
    for _ in range(12):
        app.step_forward()
    app.show_debrief_modal=False
    app.show_history_overlay=True
    app.history_scroll=0
    app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=-2))
    assert app.history_scroll==2
    app.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    assert app.app_state=='sim' and not app.show_history_overlay
    assert app.current_weather==app.event_gen.weather[app.step_idx-1]
    app._init_simulation()
    assert app.char_screen_x==(app.agent.pos[0]+.5)*TILE_SIZE and not app.bubble_timer and not app.weather.particles
    assert app.handle_event(pygame.event.Event(pygame.QUIT)) is False


def test_world_mutations_are_isolated():
    a,b=IslandWorld(),IslandWorld()
    a.elevation[20][20]=1
    a.food_tiles.clear()
    a.pdc.add((20,20))
    assert b.elevation[20][20]>900 and b.food_tiles and not b.pdc


def test_forage_does_not_seek_distant_food():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    w.food_tiles = [w.assembly_points[0]]
    before = list(a.pos)
    a.execute_action('forage', w)
    assert a.pos == before
    assert not a.inventory['food']


def test_dirty_stream_does_not_force_remote_spring_trip():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    w.ash_grid = ['9'*40]*40
    before = list(a.pos)
    a.needs['thirst'] = .2
    a.execute_action('drink', w)
    assert a.pos == before
    assert a.needs['thirst'] == .5


def test_drink_is_not_a_hidden_evacuation():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    a.apply_event('tremor', False)
    assert a.volcanic_sign_seen
    before = list(a.pos)
    a.needs['thirst'] = .2
    a.execute_action('drink', w)
    # The stream is right beside camp, so a warning must not send the agent to a far spring.
    assert math.dist(a.pos, before) <= 3
    assert a.needs['thirst'] > .2


def test_warned_agent_outside_danger_still_takes_nearest_water():
    w = IslandWorld()
    a = SurvivalAgent(w.spawn_pos)
    a.apply_event('tremor', False)
    near_stream = next(p for p in w.stream_tiles[::-1] if w.zones[p[1]][p[0]] != 0)
    outside = next(((x, y) for y in range(40) for x in range(40)
                    if w.get_tile(x, y) and w.zones[y][x] == 1
                    and 2 < math.dist((x, y), near_stream) <= 4
                    and all(math.dist((x, y), s) > 8 for s in w.clean_springs)), None)
    assert outside is not None
    a.pos = list(outside)
    a.needs['thirst'] = .2
    a.execute_action('drink', w)
    assert min(math.dist(a.pos, p) for p in w.stream_tiles) <= 2
    assert min(math.dist(a.pos, p) for p in w.clean_springs) > 2


def test_springs_and_assembly_points_are_separate_tiles():
    w = IslandWorld()
    assert not set(w.clean_springs) & set(w.assembly_points)
    assert set(w.clean_springs) <= set(w.freshwater_tiles)
    for spring, point in zip(w.clean_springs, w.assembly_points):
        assert math.dist(spring, point) <= 2
        assert w.zones[spring[1]][spring[0]] == 0


def test_camp_is_down_the_valley_not_on_the_crater():
    w = IslandWorld()
    assert math.dist(w.spawn_pos, w.vent) >= 5
    assert w.zones[w.spawn_pos[1]][w.spawn_pos[0]] == 2
    assert w.get_tile(*w.spawn_pos) == 2


def test_food_concentrates_near_main_channels():
    w = IslandWorld()
    channels = [p for v in w.valleys for p in v]
    near = sum(any(math.dist(f, c) <= 3 for c in channels) for f in w.food_tiles)
    assert near >= .6 * len(w.food_tiles)


def test_morale_recovers_only_when_safe_fed_and_quiet():
    sim = _controlled_engine('rest')
    agent, world = sim.agent, sim.world
    agent.pos = list(world.assembly_points[0])
    agent.needs.update(morale=.5, hunger=.8, thirst=.8)
    agent.recent_events = ['none', 'none', 'none']
    sim._recover_morale()
    assert agent.needs['morale'] == pytest.approx(.53)
    agent.recent_events = ['none', 'none', 'eruption']
    sim._recover_morale()
    assert agent.needs['morale'] == pytest.approx(.53)
    agent.recent_events = ['none', 'none', 'none']
    agent.needs['thirst'] = .2
    sim._recover_morale()
    assert agent.needs['morale'] == pytest.approx(.53)
    agent.needs['thirst'] = .8
    agent.pos = list(world.spawn_pos)
    sim._recover_morale()
    assert agent.needs['morale'] == pytest.approx(.53)


def test_ignoring_the_volcano_is_usually_fatal_and_leaving_is_not():
    def decide(action):
        return {'action': action, 'probs': {action: 1.}, 'reason': 'test'}

    def stay(state):
        return decide('drink' if state['needs']['thirst'] < .6 else 'forage')

    def leave(state):
        return decide('hide')

    survived = {'stay': [], 'leave': []}
    for seed in range(60):
        for name, policy in (('stay', stay), ('leave', leave)):
            run = SimulationEngine(seed=seed, mind_type='classical', noise_source='stub', decide_fn=policy).run()
            if run['world']['volcano']['erupts']:
                survived[name].append(run['cause'] not in ('pyroclastic_flow', 'lahar', 'lava'))
    assert sum(survived['stay']) / len(survived['stay']) <= .3
    assert sum(survived['leave']) / len(survived['leave']) >= .85


def test_repeated_pulses_reactivate_old_deposits():
    from engine.volcano import VolcanoModel
    world = IslandWorld()
    for seed in range(12):
        model = VolcanoModel(seed, world)
        pulses = [set(map(tuple, h['active_pdc'])) for h in model.hazard_by_step
                  if h['active_pdc']]
        if pulses:
            assert all(pulses[0] <= pulse for pulse in pulses)
            deposited = set()
            for hazard in model.hazard_by_step:
                active = set(map(tuple, hazard['active_pdc']))
                new = set(map(tuple, hazard['new_pdc']))
                assert new == active - deposited
                deposited |= new


def test_pdc_first_pulse_covers_proximal_cone():
    from engine.volcano import VolcanoModel, PDC_APRON_RADIUS
    import math
    w = IslandWorld()
    proximal = {p for row in w.valleys for p in row if math.dist(p, w.vent) <= PDC_APRON_RADIUS}
    for seed in range(16):
        model = VolcanoModel(seed, w)
        if model.erupts:
            assert proximal <= set(model.hazard_by_step[model.first_pdc_step]['active_pdc'])


def test_tropical_ash_discomfort_is_not_hypothermia():
    sim = _controlled_engine()
    sim.agent.needs['warmth'] = 0
    sim.volcano.hazard_by_step[0].update(ash=1, ash_grid=['9'*40]*40)
    sim.step()
    assert sim.agent.is_alive and sim.agent.needs['warmth'] > 0


def test_st_vincent_physics_pack_and_simulation():
    from stranded_physics.scenarios import build_st_vincent_pack, st_vincent_scenario
    from stranded_physics.runtime.simulation import PackSimulation
    scen = st_vincent_scenario(erupts=True)
    assert scen.name == 'st_vincent_2021'
    pack = build_st_vincent_pack(seed=7)
    assert (pack.contract_grid.nx, pack.contract_grid.ny) == (40, 40)
    assert pack.time.n == 36
    sim = PackSimulation(pack, mind_type='quantum')
    step0 = sim.step()
    assert contracts.validate_state(step0['state']) is True
    assert step0['action'] in contracts.ACTIONS


def test_scripted_events_counterfactual_order_effect():
    from mind.quantum_mind import quantum_decide as qm_decide
    order_ab = {0: 'tremor', 1: 'gas_plume', 2: 'ash_fall'}
    order_ba = {0: 'gas_plume', 1: 'tremor', 2: 'ash_fall'}
    sim_ab = SimulationEngine(
        seed=12, mind_type='quantum', decide_fn=qm_decide,
        scripted_events=order_ab
    )
    sim_ba = SimulationEngine(
        seed=12, mind_type='quantum', decide_fn=qm_decide,
        scripted_events=order_ba
    )
    s0_ab = sim_ab.step()
    s1_ab = sim_ab.step()
    s0_ba = sim_ba.step()
    s1_ba = sim_ba.step()
    assert s0_ab['event'] == 'tremor' and s1_ab['event'] == 'gas_plume'
    assert s0_ba['event'] == 'gas_plume' and s1_ba['event'] == 'tremor'


def test_grover_dtqw_explore_step_and_atus_priors():
    assert 'source' in contracts.ATUS_PRIORS_META
    assert 'ATUS' in contracts.ATUS_PRIORS_META['source']
    w = IslandWorld()
    pos = [20, 20]
    new_pos_q = contracts.explore_step(pos, w, mode='quantum')
    new_pos_c = contracts.explore_step(pos, w, mode='classical')
    assert 0 <= abs(new_pos_q[0] - pos[0]) + abs(new_pos_q[1] - pos[1]) <= 4
    assert 0 <= abs(new_pos_c[0] - pos[0]) + abs(new_pos_c[1] - pos[1]) <= 4


def test_quantum_mind_alternative_cognition_models():
    from mind.quantum_mind import quantum_decide as qm_decide
    state = {
        'day': 1,
        'hour': 12,
        'pos': [15, 15],
        'needs': {
            'hunger': 0.5,
            'thirst': 0.5,
            'warmth': 0.8,
            'energy': 0.7,
            'safety': 0.6,
            'morale': 0.7,
        },
        'stress': 0.35,
        'injured': False,
        'inventory': {'wood': 1, 'food': 0},
        'recent_events': ['tremor', 'gas_plume'],
    }
    for model_name in ('default', 'busemeyer_hamiltonian', 'qlbn_entropy', 'lindblad_open'):
        d = qm_decide(state, cognition_model=model_name)
        assert contracts.validate_decision(d) is True
        assert d['quantum']['cognition_model'] == model_name
        assert 'p_protect_busemeyer' in d['quantum']
        assert 'd_b_huang' in d['quantum']
        assert 'order_gap' in d['quantum']


def test_slow_mo_fast_forward_and_exports(tmp_path):
    from engine.gui import IslandVisualizerApp
    from engine.exporter import export_evacuation_datasets, export_simulation_video
    app = IslandVisualizerApp(seed=101, start_screen="sim", scenario="volcano")
    assert app.speed_choices == [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    assert app.speed_multiplier == 1.0
    app._shift_speed(-1)
    assert app.speed_multiplier == 0.5
    app._shift_speed(-1)
    assert app.speed_multiplier == 0.25
    app._shift_speed(-1)
    assert app.speed_multiplier == 0.1
    app._shift_speed(4)
    assert app.speed_multiplier == 2.0

    vid_path = tmp_path / "test_sim.mp4"
    vid_info = export_simulation_video(
        scenario="volcano", seed=101, mind="quantum",
        output_path=str(vid_path), fps=12, frames_per_step=2,
        speed_multiplier=2.0, max_steps=4, include_debrief_frames=2
    )
    assert vid_path.exists() and vid_path.stat().st_size > 1000
    assert vid_info["steps_rendered"] == 4


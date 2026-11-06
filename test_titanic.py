"""Tests for the Titanic scenario: head-counts, shared mind, flood, boats, GUI hooks."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

import contracts
from engine.crowd import ROLE_NAMES, build_crowd
from engine.cutscenes import DURATION, SCENES, CutscenePlayer
from engine.flood import BRIDGE_UNDER_STEP, COLLISION_STEP, HORIZON, LOAD_STEP, SINK_STEP, FloodModel
from engine.gui import IslandVisualizerApp
from engine.lifeboats import BOAT_TABLE, FLOAT_OFF, TOTAL_SEATS
from engine.ship import BOAT, ShipWorld
from engine.titanic import EVENT_NAMES, TitanicSimulation
from engine.world import IslandWorld
from mind.config import COLLAPSE_EVENTS, EVENT_GATES
from mind.quantum_mind import quantum_decide


@pytest.fixture(scope="module")
def finished():
    sim = TitanicSimulation(seed=101)
    sim.run()
    return sim


def test_head_counts_match_the_casualty_table():
    people = build_crowd(ShipWorld(), 1)
    assert len(people) == 2208
    for cabin, expected in (("first", 324), ("second", 284), ("third", 709), ("crew", 891)):
        assert sum(p.cabin_class == cabin for p in people) == expected
    roles = {role: sum(p.role == role for p in people) for role in ROLE_NAMES}
    assert roles == dict(captain=1, officer=7, evac_worker=58, server=500, engine_worker=325, passenger=1317)


def test_everyone_starts_on_a_walkable_tile():
    world = ShipWorld()
    assert all(world.walkable(p.pos) for p in build_crowd(world, 3))


def test_every_deck_can_reach_the_boat_deck():
    world = ShipWorld()
    field = world.next_step_field(world.assembly_points)
    tiles = [(x, y) for y in range(40) for x in range(40) if world.get_tile(x, y)]
    assert [p for p in tiles if p not in field] == []


def test_ship_world_keeps_the_island_world_interface():
    public = [name for name in dir(IslandWorld) if not name.startswith("_")]
    assert all(callable(getattr(ShipWorld(), name)) for name in public)
    island = IslandWorld(scenario="island")
    assert set(island.__dict__) - set(ShipWorld().__dict__) == set()


def test_ship_events_are_all_names_the_mind_accepts():
    for event in EVENT_NAMES.values():
        assert event in contracts.EVENTS
        assert event in EVENT_GATES or event in COLLAPSE_EVENTS


def test_all_roles_use_the_same_unmodified_mind():
    seen = set()

    def spy(state):
        contracts.validate_state(state)
        assert "role" not in state and "group" not in state
        seen.add(state["pos"][1])
        return quantum_decide(state)

    sim = TitanicSimulation(seed=7, decide_fn=spy)
    sim.step()
    assert sim.decide_fn is spy and seen
    assert TitanicSimulation(seed=7).decide_fn is contracts.quantum_decide


def test_shared_decisions_equal_a_direct_mind_call():
    sim = TitanicSimulation(seed=11)
    for _ in range(12):
        sim.step()
    checked = 0
    for person in sim.people:
        if person.log and checked < 200:
            record = person.log[-1]
            assert record["action"] == quantum_decide(record["state"])["action"]
            checked += 1
    assert checked == 200


def test_flood_timing_and_independence_from_decisions():
    world = ShipWorld()
    flood = FloodModel(5, world)
    assert all(not h["new_flood"] for h in flood.hazard_by_step[:COLLISION_STEP])
    covered = {tuple(p) for h in flood.hazard_by_step[: BRIDGE_UNDER_STEP + 1] for p in h["new_flood"]}
    assert (30, BOAT) in covered
    covered = {tuple(p) for h in flood.hazard_by_step[: SINK_STEP + 1] for p in h["new_flood"]}
    assert all((x, y) in covered for y in range(40) for x in range(40) if world.get_tile(x, y))
    quantum = TitanicSimulation(seed=5, mind_type="quantum")
    classical = TitanicSimulation(seed=5, mind_type="classical")
    assert quantum.flood.hazard_by_step == classical.flood.hazard_by_step


def test_flood_rises_gradually_after_the_collision():
    flood = FloodModel(5, ShipWorld())
    first_step = len(flood.hazard_by_step[COLLISION_STEP]["new_flood"])
    total = len({tuple(p) for h in flood.hazard_by_step[: SINK_STEP + 1] for p in h["new_flood"]})
    assert first_step < total * 0.1


def test_boat_table_and_seats():
    assert len(BOAT_TABLE) + len(FLOAT_OFF) == 20
    assert TOTAL_SEATS == 1178


def test_boats_respect_seats_and_the_loading_order(finished):
    for boat in finished.boats.boats + finished.boats.floating:
        assert len(boat.aboard) <= boat.seats
    for person in finished.people:
        boarded = [r["t"] for r in person.log if r["status"] == "boat"]
        assert not boarded or boarded[0] >= LOAD_STEP


def test_nobody_is_lost_from_the_count(finished):
    for step in finished.steps:
        assert sum(step["counts"].values()) == 2208
    assert all(p.status == "boat" or not p.is_alive for p in finished.people)


def test_same_seed_repeats_and_other_seeds_differ():
    a, b, c = (TitanicSimulation(seed=s).run()["crowd"]["counts"] for s in (21, 21, 22))
    assert a == b and a != c


def test_timeline_matches_engine_shape_and_is_json(finished):
    timeline = finished.timeline()
    assert {"world", "steps", "evacuation", "outcome", "cause"} <= set(timeline)
    assert {"t", "state", "event", "action", "probs", "reason", "pos_after", "phase"} <= set(timeline["steps"][0])
    assert all(step["event"] in contracts.EVENTS for step in timeline["steps"])
    json.dumps(timeline)


def test_horizon_covers_the_sinking():
    assert SINK_STEP < HORIZON


@pytest.fixture
def app():
    return IslandVisualizerApp(seed=105, start_screen="event_choice")


def test_gui_opens_titanic_from_the_choice_screen(app):
    app._handle_mouse_click(app.btn_choice_titanic.rect.center)
    assert app.scenario == "titanic" and app.app_state == "home" and app.max_steps == HORIZON
    app._handle_mouse_click(app.btn_launch.rect.center)
    assert app.app_state == "sim" and isinstance(app.engine, TitanicSimulation)
    app.draw((5, 5))


def test_gui_choice_keeps_other_scenarios_working(app):
    app._handle_mouse_click(app.btn_choice_volcano.rect.center)
    assert app.scenario == "volcano" and not isinstance(app.engine, TitanicSimulation)
    assert app.max_steps == 36
    app.app_state = "event_choice"
    app._handle_mouse_click(app.btn_choice_island.rect.center)
    assert app.scenario == "island"


def test_gui_runs_a_whole_night_and_follows_people(app):
    app._handle_mouse_click(app.btn_choice_titanic.rect.center)
    app._handle_mouse_click(app.btn_launch.rect.center)
    app.cutscene.enabled = False
    for _ in range(HORIZON + 1):
        app.step_forward()
        app.draw((5, 5))
        if app.step_idx == 8:
            event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f, mod=0, unicode="f")
            before = app.agent
            app.handle_event(event, (5, 5))
            assert app.agent is app.engine.agent and app.agent is not before
    assert app.show_debrief_modal
    app.draw((5, 5))


def test_cutscene_pauses_and_skips(app):
    app._handle_mouse_click(app.btn_choice_titanic.rect.center)
    app._handle_mouse_click(app.btn_launch.rect.center)
    scene = dict(kind="jump_sea", t=30, caption="x", focus=True, side="port", role="server", count=4, trim_deg=9.0)
    app.cutscene.enqueue([scene])
    assert app.cutscene.active
    app.draw((5, 5))
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, mod=0, unicode="x"), (5, 5))
    assert not app.cutscene.active


def test_cutscene_ends_on_its_own_and_every_scene_draws():
    pygame.init()
    canvas = pygame.Surface((1600, 900))
    font = pygame.font.SysFont("arial", 14)
    for kind in SCENES:
        player = CutscenePlayer(font, font)
        player.enqueue([dict(kind=kind, t=20, caption=kind, focus=True, side="port", role="passenger", count=3, trim_deg=5.0)])
        for fraction in (0.0, 0.3, 0.6, 0.99):
            player.elapsed = fraction * DURATION
            player.draw(canvas)
        player.update(DURATION)
        assert not player.active


def test_crowd_jump_scenes_are_rate_limited_but_focus_scenes_are_not():
    pygame.init()
    font = pygame.font.SysFont("arial", 14)
    player = CutscenePlayer(font, font)
    crowd = dict(kind="jump_sea", caption="c", focus=False, side="port", role="passenger", count=3, trim_deg=5.0)
    player.enqueue([dict(crowd, t=10)])
    player.skip()
    player.enqueue([dict(crowd, t=11)])
    assert not player.active
    player.enqueue([dict(crowd, t=12, focus=True)])
    assert player.active


def test_disabling_cutscenes_queues_nothing():
    pygame.init()
    font = pygame.font.SysFont("arial", 14)
    player = CutscenePlayer(font, font)
    player.enabled = False
    player.enqueue([dict(kind="float_off", t=3, caption="c", focus=True, side="port", role="passenger", trim_deg=1.0)])
    assert not player.active


def test_gui_three_mind_cards_and_titanic_policy_mappings(app):
    app._handle_mouse_click(app.btn_choice_titanic.rect.center)
    app._handle_mouse_click(app.btn_mind_mixture.rect.center)
    assert app.mind_type == "classical_mixture"
    app._handle_mouse_click(app.btn_mind_classical.rect.center)
    assert app.mind_type == "classical"
    app._handle_mouse_click(app.btn_mind_quantum.rect.center)
    assert app.mind_type == "quantum"
    sim_amb = TitanicSimulation(seed=42, mind_type="quantum", event_mapping="ambiguous_rockets")
    sim_pa_open = TitanicSimulation(seed=42, mind_type="quantum", event_mapping="early_pa_alarm", allow_all_sides=True)
    sim_amb.run()
    sim_pa_open.run()
    assert sim_pa_open.counts()["boats"] > sim_amb.counts()["boats"]

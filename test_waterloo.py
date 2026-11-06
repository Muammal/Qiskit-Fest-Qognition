"""Tests for the Waterloo chlorine leak scenario."""
import json

import numpy as np
import pytest

import contracts
from engine.chlorine import LEAK_SITES, LEAK_START_STEP, ODOUR_PPM, SOURCE_PPM, STEP_SECONDS, ChlorineModel, exposure_level, wind_at
from engine.cutscenes import DURATION
from engine.patrons import POPULATION_SETTINGS, Patron, role_counts, smell_chance
from engine.scenes_waterloo import SCENES, WaterlooCutscenes
from engine.site import BUILDING, DOORS, POOL, POOL_GATES, PROVENANCE, SITE_M_PER_TILE, SiteWorld
from engine.waterloo import EVENT_MAPPINGS, WaterlooSimulation
from engine.world import IslandWorld


@pytest.fixture(scope="module")
def world():
    return SiteWorld()


def reach(world, start):
    seen, stack = {start}, [start]
    while stack:
        for q in world.neighbors(stack.pop()):
            if q not in seen and world.walkable(q):
                seen.add(q)
                stack.append(q)
    return seen


def polygon_area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2


def test_map_keeps_the_island_world_interface(world):
    assert isinstance(world, IslandWorld)
    assert (world.width, world.height) == (40, 40)
    json.dumps(world.export_dict(), default=list)


def test_building_and_pool_areas_match_their_outlines(world):
    tile = SITE_M_PER_TILE ** 2
    drawn = {(x, y) for y in range(40) for x in range(40) if (x, y) in world.areas["indoors"]} | set(DOORS.values())
    drawn |= {p for p in world.wall_tiles if p not in world.areas["pool_deck"]} - _fence(world)
    assert abs(len(drawn) * tile / polygon_area(BUILDING) - 1) < .05
    assert abs(len(world.pool_tiles) * tile / polygon_area(POOL) - 1) < .05


def _fence(world):
    return {p for p in world.wall_tiles if any(q in world.areas["pool"] | world.areas["pool_deck"] for q in world.neighbors(p)) and
            not any(q in world.areas["indoors"] for q in world.neighbors(p))}


def test_every_walkable_tile_can_reach_every_exit(world):
    everywhere = reach(world, tuple(world.spawn_pos))
    walkable = {(x, y) for y in range(40) for x in range(40) if world.walkable((x, y))}
    assert set(world.exits.values()) <= everywhere
    # Only the far bank of Laurel Creek is cut off; its other crossings lie beyond this map.
    assert all(x <= 4 and y <= 17 for x, y in walkable - everywhere)
    assert world.areas["indoors"] | world.pool_tiles <= everywhere


def test_exits_are_on_the_map_edge(world):
    assert len(world.exits) == 5
    for x, y in world.exits.values():
        assert x in (0, 39) or y in (0, 39)


def test_doors_are_the_only_ways_out_of_the_building(world):
    indoors = world.areas["indoors"]
    crossings = {q for p in indoors for q in world.neighbors(p) if q not in indoors and world.walkable(q)}
    assert crossings == set(DOORS.values())


def test_blocking_any_one_door_still_leaves_a_way_out(world):
    for door in DOORS.values():
        blocked = SiteWorld()
        x, y = door
        blocked.tiles[y][x] = 3
        assert set(blocked.exits.values()) <= reach(blocked, (18, 12))


def test_pool_deck_only_opens_through_the_door_and_gates(world):
    fenced = world.areas["pool"] | world.areas["pool_deck"]
    crossings = {q for p in fenced for q in world.neighbors(p) if q not in fenced and world.walkable(q)}
    assert crossings == set(POOL_GATES.values()) | {DOORS["pool_south"]}


def test_pool_is_walkable_but_slower(world):
    x, y = next(iter(world.pool_tiles))
    assert world.walkable((x, y))
    assert world.travel_minutes((0, 0), (x, y)) > world.travel_minutes((0, 0), (5, 5))


def test_creek_blocks_walking_except_at_the_crossing(world):
    assert world.creek_tiles
    assert not any(world.walkable(p) for p in world.creek_tiles)


def test_map_never_sets_risk_by_location(world):
    assert {z for row in world.zones for z in row} == {0}


def test_every_provenance_entry_has_a_status_and_sourced_ones_have_a_link():
    for entry in PROVENANCE.values():
        assert entry["status"] in {"sourced", "assumption", "unconfirmed"}
        if entry["status"] == "sourced":
            assert entry["url"].startswith("https://")


# --- Chlorine model ---

@pytest.fixture(scope="module")
def leak(world):
    return ChlorineModel(1, world)


def test_nothing_before_the_leak_and_a_two_hour_run(leak):
    assert leak.horizon == 721
    assert leak.ppm[:LEAK_START_STEP].max() == 0
    assert leak.world_events[LEAK_START_STEP] == "chlorine_leak"
    assert leak.world_events.count("chlorine_leak") == 1


def test_source_holds_its_level_only_while_leaking_then_fades(leak):
    x, y = leak.source
    assert leak.ppm[leak.leak_end_step - 1, y, x] == pytest.approx(SOURCE_PPM, rel=.15)
    assert leak.ppm[-1].max() < leak.ppm[leak.leak_end_step - 1].max() / 2


def test_forecast_never_depends_on_the_seed(world):
    assert (ChlorineModel(1, world).ppm == ChlorineModel(2, world).ppm).all()


def test_solid_walls_hold_no_gas(world, leak):
    for x, y in world.nearby_building_tiles:
        assert leak.ppm[:, y, x].max() == 0


def test_gas_only_gets_outside_through_doors(world):
    # A leak inside the north end: gas is always stronger in the doorway than just beyond it.
    model = ChlorineModel(1, world, leak_site="north_end")
    x, y = world.doors["north"]
    during = range(LEAK_START_STEP, model.leak_end_step)
    assert all(model.ppm[t, y - 1, x] < model.ppm[t, y, x] for t in during)
    # With no door nearby, the far side of the solid east wall stays almost clear.
    assert model.ppm[:, 12, 24].max() < .1 * model.ppm[:, 12, 22].max()


def test_outdoor_gas_drifts_downwind(world):
    # At 14:00 the wind comes from about 223 degrees, so gas should lean north-east of a deck leak.
    model = ChlorineModel(1, world, leak_site="deck")
    x, y = model.source
    t = model.leak_end_step - 1
    assert model.ppm[t, y - 3, x + 3] > model.ppm[t, y + 3, x - 3]


def test_level_scales_with_the_source(world):
    low, high = ChlorineModel(1, world), ChlorineModel(1, world, source_ppm=110.)
    assert high.ppm.max() == pytest.approx(low.ppm.max() * 5, rel=.05)


def test_all_leak_sites_are_settings_on_open_tiles(world):
    for name, p in LEAK_SITES.items():
        assert p not in world.wall_tiles
        assert ChlorineModel(1, world, leak_site=name).ppm.max() > 0


def test_exposure_levels_follow_the_epa_table():
    steps = lambda minutes: minutes * 6
    assert exposure_level([0.] * steps(60)) == 0
    assert exposure_level([.6] * steps(10)) == 1
    assert exposure_level([3.] * steps(10)) == 2
    assert exposure_level([2.1] * steps(60)) == 2
    assert exposure_level([60.] * steps(10)) == 3
    assert exposure_level([21.] * steps(60)) == 3


def test_brief_exposure_is_averaged_over_the_full_window():
    assert exposure_level([3.] * 6) == 0  # one minute at 3 ppm averages 0.3 ppm over ten minutes


def test_wind_table_uses_the_day_s_values():
    assert wind_at(0, 14) == pytest.approx((6.4 / 3.6, 223))


# --- People and simulation ---

@pytest.fixture(scope="module")
def run():
    sim = WaterlooSimulation(seed=3, event_mapping="B")
    sim.run()
    return sim


def test_role_counts_add_up_at_every_setting():
    for population in POPULATION_SETTINGS:
        counts = role_counts(population)
        assert sum(counts.values()) == population
        assert all(counts[role] >= 1 for role in counts)


def test_start_places_are_walkable_and_everyone_shares_one_mind(world):
    calls = []

    def spy(state):
        calls.append(sorted(state))
        return contracts.classical_decide(state)

    sim = WaterlooSimulation(seed=1, decide_fn=spy)
    assert all(world.walkable(tuple(p.pos)) for p in sim.people)
    sim.step()
    assert not any(key in {"role", "id", "status", "knows_danger"} for keys in calls for key in keys)


def test_runs_are_reproducible_with_a_seed():
    first, second = WaterlooSimulation(seed=4), WaterlooSimulation(seed=4)
    first.run(60), second.run(60)
    assert [p.pos for p in first.people] == [p.pos for p in second.people]


def test_gas_never_depends_on_the_mind(world):
    quantum = WaterlooSimulation(seed=4, mind_type="quantum")
    classical = WaterlooSimulation(seed=4, mind_type="classical")
    assert (quantum.chlorine.ppm == classical.chlorine.ppm).all()


def test_nobody_knows_before_the_leak():
    sim = WaterlooSimulation(seed=5)
    sim.run(LEAK_START_STEP)
    assert sim.counts()["knows"] == 0


def test_smelling_depends_only_on_level():
    assert smell_chance(ODOUR_PPM * .9) == 0
    assert smell_chance(ODOUR_PPM) == pytest.approx(.2)
    assert smell_chance(100.) == 1


def test_people_decide_once_per_interval():
    sim = WaterlooSimulation(seed=6, decision_seconds=60)
    sim.run(36)
    log = sim.logs[sim.agent.id]
    assert len(log) == 6
    assert all(b["t"] - a["t"] == 6 for a, b in zip(log, log[1:]))


def test_alarm_comes_only_after_a_staff_member_knows():
    sim = WaterlooSimulation(seed=7, scripted_events={})
    while sim.alarm_step is None and sim.t < sim.horizon and sim.step():
        pass
    assert sim.alarm_step is not None
    assert any(p.knows_danger and p.role in ("lifeguard", "desk") for p in sim.people)


def test_alarm_can_be_switched_off():
    sim = WaterlooSimulation(seed=7, alarm=False)
    sim.run()
    assert sim.alarm_step is None


def test_nobody_leaves_without_knowing_and_nobody_dies(run):
    assert all(p.knows_danger for p in run.people if p.status == "out")
    assert all(p.is_alive for p in run.people)


def test_exposure_is_reported_for_everyone(run):
    summary = run.exposure_summary()
    assert sum(summary.values()) == len(run.people)
    assert all(len(p.exposure) == run.t for p in run.people)


def test_every_mapping_uses_events_the_mind_accepts():
    for mapping in EVENT_MAPPINGS.values():
        assert set(mapping.values()) <= set(contracts.EVENTS)
        assert set(mapping) == {"smell", "word_of_mouth", "crowd_moving", "alarm"}


def test_timeline_is_json_ready(run):
    timeline = run.timeline()
    assert json.dumps(timeline["crowd"])
    assert set(timeline["evacuation"]) == {"first_knew", "alarm", "first_off_site", "half_off_site", "all_off_site"}


def test_population_setting_changes_the_count():
    assert len(WaterlooSimulation(seed=1, population=300).people) == 300


# --- Window ---

@pytest.fixture(scope="module")
def app():
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    from engine.gui import IslandVisualizerApp
    return IslandVisualizerApp(seed=105, start_screen="event_choice", scenario="volcano")


def test_window_opens_waterloo_runs_and_draws_every_screen(app):
    app.draw()
    app._handle_event_choice_click(app.btn_choice_waterloo.rect.center)
    assert (app.app_state, app.scenario, app.max_steps) == ("home", "waterloo", 721)
    app.draw()
    app._init_simulation()
    assert isinstance(app.engine, WaterlooSimulation)
    assert app.engine.event_mapping == "A" and len(app.engine.people) == 100
    app.app_state = "sim"
    for _ in range(12):
        app.step_forward()
        app._worker.join()
        app._pompeii_poll_step()
    app.draw()
    app.show_split_panels = False
    app.draw()
    app.show_split_panels = True
    app.show_debrief_modal = True
    app.draw()
    app.show_debrief_modal = False


def test_every_setting_button_cycles_and_reaches_the_simulation(app):
    app.scenario = "waterloo"
    app._build_home_buttons()
    for i in range(6):
        app._cycle_pompeii_setting(i)
    app._init_simulation()
    assert app.engine.event_mapping == "B"
    assert len(app.engine.people) == 40
    assert app.engine.chlorine.leak_site == "north_end"
    assert app.engine.alarm_enabled is False
    for i, count in enumerate((2, 2, 2, 2, 2, 1)):
        for _ in range(count):
            app._cycle_pompeii_setting(i)


def test_pompeii_settings_are_not_touched_by_waterloo_buttons(app):
    assert app.pompeii_settings["event_mapping"] == "B"
    assert app.pompeii_settings["population"] == 11_500


# --- Cutscenes ---

def _all_scenes(sim):
    scenes = []
    while sim.step() is not None:
        scenes += sim.scenes
    return scenes


def test_every_scene_kind_can_play_and_draws(world):
    pygame = pytest.importorskip("pygame")
    pygame.init()
    canvas = pygame.Surface((1600, 900))
    font = pygame.font.SysFont("arial", 14)
    scenes = _all_scenes(WaterlooSimulation(seed=3))
    kinds = {scene["kind"] for scene in scenes}
    assert kinds == set(SCENES)
    for scene in scenes:
        player = WaterlooCutscenes(font, font)
        player.enqueue([scene])
        player.elapsed = 1.
        player.draw(canvas)


def test_scenes_never_change_a_result():
    played, plain = WaterlooSimulation(seed=8), WaterlooSimulation(seed=8)
    played.run()
    plain._emit_scenes = lambda t, moving: None
    plain.run()
    assert [p.pos for p in played.people] == [p.pos for p in plain.people]
    assert played.exposure_summary() == plain.exposure_summary()
    assert played.timing() == plain.timing()


def test_only_the_alarm_scenes_play_once_per_run_and_only_with_an_alarm():
    with_alarm = [s["kind"] for s in _all_scenes(WaterlooSimulation(seed=3))]
    assert with_alarm.count("leak_start") == with_alarm.count("alarm_cutaway") == with_alarm.count("pool_exit") == 1
    without = [s["kind"] for s in _all_scenes(WaterlooSimulation(seed=3, alarm=False))]
    assert "alarm_cutaway" not in without and "alarm_pool" not in without


def test_closeup_text_agrees_with_the_moment_it_shows():
    sim = WaterlooSimulation(seed=3)
    scenes = _all_scenes(sim)
    learned = next(s for s in scenes if s["kind"] == "person_closeup" and "learns" in s["caption"])
    assert "noticed nothing new" not in learned["thought"]


def test_alarm_pool_scene_plays_when_the_alarm_starts():
    sim = WaterlooSimulation(seed=3)
    scenes = _all_scenes(sim)
    assert next(s for s in scenes if s["kind"] == "alarm_pool")["t"] == sim.alarm_step


# --- Walking speed ---

def _walk_metres(role, start, steps, world):
    patron = Patron(0, role, list(start), 0)
    field = world.next_step_field(world.exits.values())
    moved, position = 0., tuple(start)
    for _ in range(steps):
        patron.walk(world, field)
        while position != tuple(patron.pos):
            position = field[position]
            moved += SITE_M_PER_TILE
    return moved


def test_average_walking_speed_matches_the_sourced_values(world):
    # From the north end of the building, the route to an exit is long and stays out of the water.
    for role, speed in (("adult", 1.3), ("child", 1.5)):
        steps = 6
        assert _walk_metres(role, (20, 9), steps, world) == pytest.approx(speed * steps * STEP_SECONDS, abs=SITE_M_PER_TILE)


def test_slow_water_still_lets_people_move(world, monkeypatch):
    import engine.site as site_module
    monkeypatch.setattr(site_module, "WADE_M_PER_S", .25)
    start = max(world.pool_tiles, key=lambda p: p[0] + p[1])
    field = world.next_step_field(world.exits.values())
    patron = Patron(0, "adult", list(start), 0)
    for _ in range(6):
        patron.walk(world, field)
    assert tuple(patron.pos) != start


# --- Hub screen ---

def test_hub_gives_each_crowd_scenario_its_whole_timeline():
    from engine.flood import HORIZON as TITANIC
    from engine.gui import IslandVisualizerApp
    from engine.pompeii import HORIZON as POMPEII
    app = IslandVisualizerApp(seed=105, start_screen="event_choice", scenario="volcano")
    for choose, horizon in ((app._hub_choose_titanic, TITANIC), (app._hub_choose_pompeii, POMPEII), (app._hub_choose_waterloo, 721)):
        choose()
        assert app.max_steps == horizon
    assert app.app_state == "home" and len(app.step_buttons) == 6
    assert app.step_buttons[0].text == "Mapping: A" and app.btn_launch.text == "LAUNCH WATERLOO SIMULATION"


def test_titanic_defaults_stay_as_pulled_and_new_settings_are_opt_in():
    from engine.titanic import TitanicSimulation
    sim = TitanicSimulation(seed=1)
    assert sim.inputs == "original" and sim.crew_told and sim.boats.boarding_rule
    neutral = TitanicSimulation(seed=1, inputs="neutral")
    assert all(p.neutral_inputs for p in neutral.people)
    neutral.run(12)
    assert not any(p.status == "boat" and not p.knows_danger for p in neutral.people)


# --- Replay tool ---

def _finished_app(choose="waterloo", steps=60):
    from engine.gui import IslandVisualizerApp
    app = IslandVisualizerApp(seed=3, start_screen="event_choice", scenario="volcano")
    {"waterloo": app._hub_choose_waterloo, "pompeii": app._hub_choose_pompeii, "titanic": app._hub_choose_titanic}[choose]()
    app._init_simulation()
    app.app_state = "sim"
    return app


def _advance(app, steps):
    for _ in range(steps):
        app.step_forward()
        if app._worker is not None:
            app._worker.join()
            app._pompeii_poll_step()
        assert not app.cutscene.active  # nothing pops up during the run


def _press(app, key):
    pygame = pytest.importorskip("pygame")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""), (5, 5))


@pytest.mark.parametrize("scenario,steps", [("waterloo", 60), ("titanic", 30)])
def test_scenes_are_only_recorded_during_a_run(scenario, steps):
    app = _finished_app(scenario)
    _advance(app, steps)
    assert app.cutscene.library and not app.cutscene.queue


def test_summary_film_is_title_one_shot_per_moment_then_outcome():
    pygame = pytest.importorskip("pygame")
    app = _finished_app()
    while not app.show_debrief_modal:
        _advance(app, 1)
    app.draw((5, 5))
    app._handle_sim_click(app.btn_modal_scenes.rect.center)
    player = app.cutscene
    assert player.replaying
    kinds = [shot["kind"] for shot in player.reel.shots]
    assert kinds[0] == "title" and kinds[-1] == "end" and kinds.count("title") == kinds.count("end") == 1
    scenes = [shot["scene"] for shot in player.reel.shots if shot["kind"] == "scene"]
    assert [s["t"] for s in scenes] == sorted(s["t"] for s in scenes)
    assert len({player.reel_key(s) for s in scenes if s["kind"] != "person_closeup"}) == sum(s["kind"] != "person_closeup" for s in scenes)
    assert player.reel.total < 65
    app.draw((5, 5))
    _press(app, pygame.K_RIGHT)
    assert player.reel.index == 1
    app.draw((5, 5))
    _press(app, pygame.K_LEFT)
    assert player.reel.index == 0
    _press(app, pygame.K_SPACE)
    before = player.reel.time
    player.update(5.)
    assert player.reel.time == before
    _press(app, pygame.K_SPACE)
    for _ in player.reel.shots:
        player.update(10.)
    assert not player.replaying and not player.active and app.show_debrief_modal
    _press(app, pygame.K_c)
    assert player.replaying
    _press(app, pygame.K_ESCAPE)
    assert not player.replaying


@pytest.mark.parametrize("scenario,steps", [("titanic", 48), ("pompeii", 60)])
def test_every_shot_of_the_film_draws_in_other_scenarios(scenario, steps):
    app = _finished_app(scenario)
    if scenario == "pompeii":
        app.pompeii_settings["population"] = 1_500
        app._init_simulation()
    _advance(app, steps)
    app.show_debrief_modal = True
    app.cutscene.start_replay(app.engine, app.mind_type)
    reel = app.cutscene.reel
    for index in range(len(reel.shots)):
        reel.go(index)
        reel.time = reel.shots[index]["seconds"] * .5
        app.draw((5, 5))


def test_film_numbers_come_from_the_finished_run():
    app = _finished_app()
    while not app.show_debrief_modal:
        _advance(app, 1)
    stats = app.cutscene.reel_stats(app.engine)
    assert stats[0]["value"] == app.engine.counts()["off_site"]
    assert stats[1]["value"] == app.engine.timing()["half_off_site"]


def test_a_new_run_starts_with_an_empty_library():
    app = _finished_app()
    _advance(app, 20)
    assert app.cutscene.library
    app._init_simulation()
    assert not app.cutscene.library and not app._scenes_available()


def test_summary_film_plays_by_itself_once_when_a_run_ends():
    app = _finished_app()
    while not app.show_debrief_modal:
        _advance(app, 1)
    assert not app.cutscene.replaying
    app._autoplay_summary()
    assert app.cutscene.replaying
    app.cutscene.stop_replay()
    app._autoplay_summary()
    assert not app.cutscene.replaying and app.show_debrief_modal  # closing it returns to the results for good


def test_summary_film_does_not_play_during_a_run():
    app = _finished_app()
    _advance(app, 20)
    app._autoplay_summary()
    assert not app.cutscene.replaying


def test_every_shot_has_this_moment_s_numbers_and_a_named_source():
    app = _finished_app()
    while not app.show_debrief_modal:
        _advance(app, 1)
    app.cutscene.start_replay(app.engine, app.mind_type)
    for shot in app.cutscene.reel.shots:
        if shot["kind"] == "scene":
            snapshot = shot["scene"]["snapshot"]
            assert snapshot["rows"] and snapshot["actions"]
            assert abs(sum(share for _, share in snapshot["actions"]) - 1) < 1e-6
            assert shot["research"] and shot["research"][2]


def test_a_snapshot_records_that_moment_not_the_end_of_the_run():
    app = _finished_app()
    while not app.show_debrief_modal:
        _advance(app, 1)
    first = app.cutscene.library[0]["snapshot"]
    assert dict(first["rows"])["Off site"] == 0
    assert app.engine.counts()["off_site"] == len(app.engine.people)

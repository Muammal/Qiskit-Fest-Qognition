"""Tests for the Pompeii scenario: the two linked maps and the eruption timeline."""

import json
import math

import pytest

from engine.city import CITY_M_PER_TILE, GATE_TO_REGION, PROVENANCE, REGION_M_PER_TILE, REGION_ROADS, VESUVIUS, CityWorld, RegionWorld
from engine.eruption import (
    DEVASTATING_STEP,
    FALL_END_STEP,
    FIRST_CITY_WIDE_STEP,
    FIRST_FLOW_AT_TOWN_STEP,
    HORIZON,
    PLINIAN_STEP,
    PUMICE_TOTAL_M,
    QUAKE_STEP,
    BREAK_STEP,
    EruptionModel,
    clock_step,
)
from engine.eruption import PROVENANCE as ERUPTION_PROVENANCE
from engine.world import IslandWorld

GATES = {"marina", "ercolano", "vesuvio", "nola", "sarno", "nocera", "stabia"}


@pytest.fixture(scope="module")
def city():
    return CityWorld()


@pytest.fixture(scope="module")
def region():
    return RegionWorld()


def test_both_maps_keep_the_island_world_interface(city, region):
    island = IslandWorld(scenario="island")
    for world in (city, region):
        assert set(island.__dict__) - set(world.__dict__) == set()
        assert all(callable(getattr(world, name)) for name in dir(IslandWorld) if not name.startswith("_"))
        json.dumps(world.export_dict(), default=list)


def test_city_area_and_walls_are_near_the_sourced_figures(city):
    inside = sum(1 for y in range(40) for x in range(40) if 0 <= ((x - 20) / 17.5) ** 2 + ((y - 20) / 13.3) ** 2 <= 1)
    assert 660_000 * 0.95 <= inside * CITY_M_PER_TILE**2 <= 660_000 * 1.05
    # Ramanujan's ellipse perimeter. A smooth oval comes out about 9% under the sourced wall length.
    a, b = 17.5, 13.3
    perimeter = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b))) * CITY_M_PER_TILE
    assert perimeter == pytest.approx(3_200, rel=0.1)


def test_seven_gates_are_the_only_ways_through_the_wall(city):
    assert set(city.gates) == GATES
    gate_tiles = set(city.gates.values())
    assert gate_tiles <= city.wall_tiles
    assert all(city.get_tile(*p) == 0 for p in city.wall_tiles - gate_tiles)


def test_gates_sit_on_the_sides_the_sources_give(city):
    x, y = city.gates["marina"]
    assert x < 8
    x, y = city.gates["nocera"]
    assert x > 20 and y > 20
    x, y = city.gates["ercolano"]
    assert x < 20 and y < 20


def test_every_street_tile_can_reach_every_gate(city):
    tiles = [(x, y) for y in range(40) for x in range(40) if city.get_tile(x, y)]
    for gate in city.gates.values():
        field = city.next_step_field([gate])
        assert [p for p in tiles if p not in field] == []


def test_each_gate_road_reaches_the_map_edge(city):
    for name, edge in city.exits.items():
        assert edge[0] in (0, 39) or edge[1] in (0, 39)
        assert city.path(city.gates[name], [edge])


def test_vesuvius_is_eight_kilometres_from_the_town(region):
    metres = math.dist(VESUVIUS, (30, 30)) * REGION_M_PER_TILE
    assert metres == pytest.approx(8_000, rel=0.03)
    assert region.get_tile(*VESUVIUS) == 3
    assert region.elevation[VESUVIUS[1]][VESUVIUS[0]] > 1000


def test_every_city_gate_links_to_a_road_out_of_the_region(region):
    assert set(GATE_TO_REGION) == GATES == set(REGION_ROADS)
    for name, tile in GATE_TO_REGION.items():
        assert region.walkable(tile)
        assert region.path(tile, [REGION_ROADS[name]])


def test_roads_end_on_land_and_the_town_is_about_the_right_size(region):
    assert all(region.get_tile(*end) for end in REGION_ROADS.values())
    town = [(x, y) for y in range(40) for x in range(40) if region.get_tile(x, y) == 4]
    assert 660_000 * 0.7 <= len(town) * REGION_M_PER_TILE**2 <= 660_000 * 1.6


def test_naples_road_skirts_the_mountain_instead_of_crossing_it(region):
    route = region.path(GATE_TO_REGION["ercolano"], [REGION_ROADS["ercolano"]])
    assert route and max(region.elevation[y][x] for x, y in route) < 150
    assert region.route_minutes(route) < 240


def test_side_streets_do_not_swamp_the_town(city):
    inside = [(x, y) for y in range(40) for x in range(40) if ((x - 20) / 17.5) ** 2 + ((y - 20) / 13.3) ** 2 <= 1 and (x, y) not in city.wall_tiles]
    buildings = sum(city.get_tile(*p) in (2, 4) for p in inside)
    assert buildings / len(inside) > 0.55


def test_sarno_is_one_channel_broken_only_by_bridges(region):
    columns = {x for x, _ in region.river_tiles}
    assert len(columns) >= 10
    assert all(region.walkable(p) is False for p in region.river_tiles)
    assert region.path(GATE_TO_REGION["stabia"], [REGION_ROADS["stabia"]])
    assert region.path(GATE_TO_REGION["nocera"], [REGION_ROADS["nocera"]])


def test_maps_never_set_risk_by_location(city, region):
    for world in (city, region):
        assert all(zone == 0 for row in world.zones for zone in row)


def test_every_map_fact_declares_where_it_came_from():
    allowed = {"sourced", "excerpt", "school", "inferred", "unconfirmed", "assumption"}
    for name, fact in PROVENANCE.items():
        assert fact["status"] in allowed, name
        if fact["status"] in ("sourced", "excerpt", "school", "inferred"):
            assert fact["url"], name
    assert all(f"gate_{gate}" in PROVENANCE for gate in GATES)


def test_maps_repeat_exactly(city, region):
    assert CityWorld().tiles == city.tiles and RegionWorld().tiles == region.tiles
    assert CityWorld().tiles is not city.tiles


@pytest.fixture(scope="module")
def eruption(city, region):
    return EruptionModel(9, city, region=region)


def test_timeline_covers_about_32_hours_in_15_minute_steps(eruption):
    assert HORIZON == 129
    assert len(eruption.hazard_by_step) == HORIZON
    assert clock_step(2, 20) * 15 / 60 == 32


def test_sourced_clock_anchors_are_where_the_papers_put_them():
    assert PLINIAN_STEP == clock_step(1, 13)
    assert FALL_END_STEP == clock_step(2, 7)
    assert FIRST_CITY_WIDE_STEP == clock_step(2, 7, 30)
    assert DEVASTATING_STEP == clock_step(2, 8)


def test_pumice_grows_to_the_sourced_depth_and_then_stops(eruption):
    depths = [h["pumice_m"] for h in eruption.hazard_by_step]
    assert depths[PLINIAN_STEP] == 0 and depths == sorted(depths)
    assert depths[FALL_END_STEP] == pytest.approx(PUMICE_TOTAL_M)
    assert depths[-1] == pytest.approx(PUMICE_TOTAL_M)


def test_seventeen_flows_and_none_in_town_before_0630(eruption):
    assert len(eruption.flows) == 17
    assert all(step < HORIZON for step, _, _ in eruption.flows)
    assert all(not h["active_pdc"] for h in eruption.hazard_by_step[:FIRST_FLOW_AT_TOWN_STEP])


def test_first_flow_only_reaches_the_north_edge_and_later_ones_spread(eruption, city):
    edge = eruption.hazard_by_step[FIRST_FLOW_AT_TOWN_STEP]["active_pdc"]
    half = eruption.hazard_by_step[FIRST_CITY_WIDE_STEP]["active_pdc"]
    everywhere = eruption.hazard_by_step[DEVASTATING_STEP]["active_pdc"]
    top = min(y for _, y in city.wall_tiles)
    assert edge and max(y for _, y in edge) <= top + 7
    assert len(edge) < len(half) < len(everywhere)


def test_a_break_separates_the_two_morning_flows(eruption):
    assert eruption.hazard_by_step[BREAK_STEP]["active_pdc"] == []
    assert eruption.hazard_by_step[FIRST_CITY_WIDE_STEP]["active_pdc"]
    assert eruption.hazard_by_step[DEVASTATING_STEP]["active_pdc"]


def test_flows_on_the_region_map_stop_at_their_runout(eruption, region):
    for step, runout, _ in eruption.flows:
        tiles = eruption.hazard_by_step[step]["region_active_pdc"]
        assert tiles and all(math.dist(p, region.vent) * REGION_M_PER_TILE <= runout * 1000 for p in tiles)


def test_roofs_fail_gradually_and_never_twice(eruption, city):
    collapsed = [tuple(p) for h in eruption.hazard_by_step for p in h["new_collapse"]]
    assert len(collapsed) == len(set(collapsed))
    assert all(city.get_tile(*p) == 4 for p in collapsed)
    before_pumice = eruption.hazard_by_step[:PLINIAN_STEP]
    assert all(not h["new_collapse"] for h in before_pumice)


def test_quake_switch_only_changes_collapses_at_the_quake(city, region):
    on = EruptionModel(12, city, region=region, quake=True)
    off = EruptionModel(12, city, region=region, quake=False)
    assert on.hazard_by_step[QUAKE_STEP]["quake"] and not off.hazard_by_step[QUAKE_STEP]["quake"]
    assert len(on.hazard_by_step[QUAKE_STEP]["new_collapse"]) > len(off.hazard_by_step[QUAKE_STEP]["new_collapse"])
    for a, b in zip(on.hazard_by_step, off.hazard_by_step):
        assert a["active_pdc"] == b["active_pdc"] and a["pumice_m"] == b["pumice_m"]


def test_date_setting_only_changes_temperature(city, region):
    august = EruptionModel(12, city, region=region, date="august")
    autumn = EruptionModel(12, city, region=region, date="autumn")
    assert august.hazard_by_step[0]["temperature_c"] != autumn.hazard_by_step[0]["temperature_c"]
    for a, b in zip(august.hazard_by_step, autumn.hazard_by_step):
        assert {**a, "temperature_c": 0} == {**b, "temperature_c": 0}


def test_every_event_is_a_name_the_mind_accepts(eruption):
    import contracts
    from mind.config import COLLAPSE_EVENTS, EVENT_GATES

    for event in eruption.world_events:
        assert event in contracts.EVENTS
        assert event == "none" or event in EVENT_GATES or event in COLLAPSE_EVENTS


def test_same_seed_repeats_and_seeds_differ(city, region):
    a, b, c = (EruptionModel(s, city, region=region) for s in (31, 31, 32))
    assert a.hazard_by_step == b.hazard_by_step and a.flows != c.flows


def test_timeline_exports_to_json_and_declares_sources(eruption):
    json.dumps(eruption.export_dict())
    allowed = {"sourced", "excerpt", "news", "assumption"}
    assert all(fact["status"] in allowed for fact in ERUPTION_PROVENANCE.values())


# ---- Step 4: people, roles, households, news ----
import inspect
import random

import contracts
from engine.citizens import DEFAULT_POPULATION, HIGH_POPULATION, Citizen, build_citizens, notice_chance, relay_chance, role_counts, spread_household_news
from engine.citizens import PROVENANCE as CITIZEN_PROVENANCE


@pytest.fixture(scope="module")
def crowd(city):
    return build_citizens(city, 5)


def test_head_counts_are_the_agreed_numbers(crowd):
    people, _ = crowd
    assert len(people) == DEFAULT_POPULATION == 11_500
    expected = dict(resident=6826, enslaved=3450, merchant=1000, visitor=100, council=100, guard=20, magistrate=4)
    assert role_counts() == expected
    for role, count in expected.items():
        assert sum(p.role == role for p in people) == count


def test_higher_population_setting_keeps_shares_and_fixes_elected_bodies(city):
    counts = role_counts(HIGH_POPULATION)
    assert sum(counts.values()) == 20_000
    assert counts["enslaved"] == 6000 and counts["magistrate"] == 4 and counts["council"] == 100
    assert len(build_citizens(city, 5, HIGH_POPULATION)[0]) == 20_000


def test_everyone_starts_in_town_on_a_walkable_tile(crowd, city):
    people, _ = crowd
    assert all(p.status == "city" and city.walkable(p.pos) for p in people)
    assert all(city.get_tile(*p.home) == 4 for p in people)


def test_every_enslaved_person_belongs_to_a_free_household(crowd):
    people, households = crowd
    for person in people:
        if person.role == "enslaved":
            household = households[person.household]
            assert person.id in household["servants"]
            assert people[household["head"]].role != "enslaved"


def test_wealthier_households_hold_more_servants(crowd):
    people, households = crowd

    def mean_servants(role):
        rows = [h for h in households.values() if people[h["head"]].role == role]
        return sum(len(h["servants"]) for h in rows) / len(rows)

    assert mean_servants("magistrate") > mean_servants("council") > mean_servants("merchant")


def test_mind_receives_no_role_status_or_household(crowd):
    state = crowd[0][0].get_state()
    contracts.validate_state(state)
    assert not {"role", "household", "status", "knows_danger", "gate"} & set(state)
    assert not {"role", "household", "status"} & set(state["inventory"])


def test_noticing_takes_no_role_and_follows_distance_indoors_and_view():
    assert set(inspect.signature(notice_chance).parameters) == {"distance_tiles", "indoors", "visibility"}
    assert notice_chance(0, False, 1.0) > notice_chance(10, False, 1.0) > notice_chance(30, False, 1.0)
    assert notice_chance(5, True, 1.0) < notice_chance(5, False, 1.0)
    assert notice_chance(5, False, 0.25) < notice_chance(5, False, 1.0)
    assert relay_chance(0) > relay_chance(30)


def _news_rounds(servant_count, trials=400):
    """How often a head hears in one step, with this many knowing servants at one distance."""
    heard = 0
    for trial in range(trials):
        people = [Citizen(0, "resident", 0, (5, 5), (5, 5))]
        household = dict(head=0, servants=[], home=(5, 5), members=[0])
        for i in range(servant_count):
            servant = Citizen(i + 1, "enslaved", 0, (10, 5), (5, 5))
            servant.knows_danger = True
            people.append(servant)
            household["servants"].append(i + 1)
        rng = random.Random(trial)
        heard += bool(spread_household_news(people, {0: household}, lambda a, b: abs(a[0] - b[0]), rng))
    return heard / trials


def test_more_servants_means_sooner_news_with_no_role_bonus():
    assert _news_rounds(10) > _news_rounds(1) > _news_rounds(0) == 0
    resident = Citizen(0, "resident", 0, (5, 5), (5, 5))
    magistrate = Citizen(0, "magistrate", 0, (5, 5), (5, 5))
    assert (resident.get_state()["needs"] == magistrate.get_state()["needs"]) and resident.stress == magistrate.stress


def test_hide_walks_toward_a_gate_and_pumice_slows_it(city):
    field = city.next_step_field(city.gates.values())
    start = (21, 23)

    def walked(depth):
        person = Citizen(0, "resident", 0, start, start)
        person.knows_danger = True
        person.step_budget = lambda d, v, original=person.step_budget: original(depth, 1.0) / 12
        person.execute_town_action("hide", city, dict(leave=field), {}, random.Random(1), depth, 1.0)
        return math.dist(person.pos, start)

    assert walked(0) > walked(2.8) > 0


def test_restriction_switch_only_holds_back_enslaved_people(city):
    field = city.next_step_field(city.gates.values())
    home_field = city.next_step_field([(21, 23)])
    start, home = (21, 23), (21, 23)
    fields = dict(leave=field, home=home_field)

    def moved(role, restrict, head_in_town):
        person = Citizen(0, role, 0, start, home)
        person.knows_danger = True
        person.execute_town_action("hide", city, fields, {}, random.Random(1), 0.0, 1.0, restrict, head_in_town)
        return tuple(person.pos) != start

    assert moved("enslaved", False, True)
    assert not moved("enslaved", True, True)
    assert moved("enslaved", True, False)
    assert moved("resident", True, True)


def test_clock_runs_in_fifteen_minutes(crowd):
    person = Citizen(0, "resident", 0, (21, 23), (21, 23))
    person.step_decay(True)
    assert (person.hour, person.minute) == (12, 15)
    for _ in range(47):
        person.step_decay(True)
    assert (person.day, person.hour, person.minute) == (2, 0, 0)


def test_autumn_setting_only_chills_people_outdoors():
    warm = Citizen(0, "resident", 0, (21, 23), (21, 23))
    cold = Citizen(1, "resident", 0, (21, 23), (21, 23))
    sheltered = Citizen(2, "resident", 0, (21, 23), (21, 23))
    warm.step_decay(False, temperature_c=27.0)
    cold.step_decay(False, temperature_c=17.0)
    sheltered.step_decay(True, temperature_c=17.0)
    assert cold.needs["warmth"] < warm.needs["warmth"] == sheltered.needs["warmth"]


def test_people_repeat_by_seed(city):
    a, _ = build_citizens(city, 8)
    b, _ = build_citizens(city, 8)
    c, _ = build_citizens(city, 9)
    assert [tuple(p.pos) for p in a] == [tuple(p.pos) for p in b] != [tuple(p.pos) for p in c]


def test_every_people_fact_declares_where_it_came_from():
    allowed = {"sourced", "news", "school", "assumption"}
    assert all(fact["status"] in allowed for fact in CITIZEN_PROVENANCE.values())


# ---- Step 5: the full simulation ----
from engine.pompeii import DEFAULT_MAPPING, EVENT_MAPPINGS, EVENT_NAMES, PompeiiSimulation
from mind.quantum_mind import quantum_decide

SMALL = dict(population=1_500)


@pytest.fixture(scope="module")
def finished():
    sim = PompeiiSimulation(seed=3, **SMALL)
    sim.run()
    return sim


def test_full_population_is_the_default():
    assert len(PompeiiSimulation(seed=1).people) == 11_500


def test_every_mapping_uses_names_the_mind_accepts():
    from mind.config import COLLAPSE_EVENTS, EVENT_GATES

    assert DEFAULT_MAPPING == "B" and set(EVENT_MAPPINGS) == set("ABCD")
    for mapping in EVENT_MAPPINGS.values():
        for event in {**EVENT_NAMES, **mapping}.values():
            assert event in contracts.EVENTS and (event in EVENT_GATES or event in COLLAPSE_EVENTS)


def test_default_mapping_is_the_most_literal_one():
    sim = PompeiiSimulation(seed=1, **SMALL)
    assert sim.event_names["column_seen"] == "gas_plume" and sim.event_names["pumice_falling"] == "ash_fall"


def test_everyone_uses_the_same_mind_and_state_contract():
    def spy(state):
        contracts.validate_state(state)
        assert not {"role", "household", "status", "knows_danger"} & set(state)
        return quantum_decide(state)

    sim = PompeiiSimulation(seed=4, decide_fn=spy, **SMALL)
    sim.step()
    assert sim.decide_fn is spy
    assert PompeiiSimulation(seed=4, **SMALL).decide_fn is contracts.quantum_decide


def test_shared_decisions_equal_a_direct_mind_call_in_full():
    sim = PompeiiSimulation(seed=6, **SMALL)
    people = sim.people[:60]
    for person in people:
        sim.watch(person)
    for _ in range(10):
        sim.step()
    for person in people:
        for record in sim.logs[person.id]:
            direct = quantum_decide(record["state"])
            assert record["action"] == direct["action"] and record["probs"] == direct["probs"]


def test_nobody_is_lost_from_the_count(finished):
    assert all(sum(step["counts"].values()) == 1_500 for step in finished.steps)
    assert all(p.status == "escaped" or not p.is_alive or p.status in ("city", "road") for p in finished.people)


def test_nobody_moves_before_anything_could_be_noticed():
    sim = PompeiiSimulation(seed=7, **SMALL)
    start = [tuple(p.pos) for p in sim.people]
    while sim.t < 4:
        sim.step()
    leavers = sum(p.status != "city" for p in sim.people)
    assert leavers == 0 and sim.counts()["dead"] == 0
    assert len(start) == 1_500


def test_flows_kill_anyone_they_cover_indoors_or_out():
    sim = PompeiiSimulation(seed=8, **SMALL)
    for person in sim.people:
        person.pos, person.status = [21, 23], "city"
    from engine.eruption import DEVASTATING_STEP

    sim._apply_flows(DEVASTATING_STEP, sim.eruption.hazard_by_step[DEVASTATING_STEP])
    assert sim.counts()["dead"] == 1_500
    assert {p.cause_of_death for p in sim.people} == {"pyroclastic_flow"}


def test_collapse_kills_about_half_and_injures_the_rest():
    sim = PompeiiSimulation(seed=9, **SMALL)
    tile = next((x, y) for y in range(40) for x in range(40) if sim.world.get_tile(x, y) == 4)
    for person in sim.people:
        person.pos, person.status = list(tile), "city"
    hazard = dict(sim.eruption.hazard_by_step[0], new_collapse=[tile])
    _, hurt = sim._collapse_buildings(10, hazard)
    dead = sim.counts()["dead"]
    assert dead / 1_500 == pytest.approx(0.5, abs=0.06)
    assert len(hurt) == 1_500 - dead
    assert all(sim.people[i].injured for i in hurt)
    assert sim.world.get_tile(*tile) == 1


def test_quake_switch_and_date_reach_the_timeline():
    assert PompeiiSimulation(seed=1, quake=False, **SMALL).eruption.quake_enabled is False
    assert PompeiiSimulation(seed=1, date="autumn", **SMALL).eruption.date == "autumn"


def test_crowding_switch_slows_leaving():
    def in_town(crowding):
        sim = PompeiiSimulation(seed=2, population=11_500, crowding=crowding, event_mapping="A")
        for _ in range(6):
            sim.step()
        return sim.counts()["in_town"]

    assert in_town(True) > in_town(False)


def test_same_seed_repeats_and_timeline_is_json():
    a = PompeiiSimulation(seed=5, **SMALL).run()
    b = PompeiiSimulation(seed=5, **SMALL).run()
    assert a["crowd"]["counts"] == b["crowd"]["counts"]
    assert {"world", "steps", "evacuation", "outcome", "cause"} <= set(a)
    json.dumps(a, default=list)


# ---- Step 6: map views, cutscenes, split-screen panels ----
import pygame
from engine.cutscenes import DURATION
from engine.gui_city import CityView, SplitPanels, danger_phrase, mini_map, thought_text
from engine.scenes_pompeii import SCENES, PompeiiCutscenes


class FakeApp:
    def __init__(self, engine):
        pygame.init()
        self.canvas = pygame.Surface((1600, 900))
        self.font_small = pygame.font.SysFont("arial", 11)
        self.font_sub = pygame.font.SysFont("arial", 13, bold=True)
        self.engine, self.step_idx, self.show_evacuation_map = engine, 1, True


@pytest.fixture(scope="module")
def stepped():
    sim = PompeiiSimulation(seed=11, population=1_500)
    for _ in range(12):
        sim.step()
    return sim


def test_six_scene_kinds_from_different_cameras():
    assert set(SCENES) == {"column_street", "crowd_aerial", "bay_wide", "roof_cutaway", "person_closeup", "flow_arrival"}


def test_every_scene_draws_and_ends_on_its_own(stepped):
    app = FakeApp(stepped)
    base = dict(
        t=20,
        caption="c",
        focus=True,
        role="resident",
        world=stepped.world,
        field=stepped._city_leave,
        thought="Pumice is falling. Belief is unsure. Heads for a gate.",
        flow=True,
    )
    for kind in SCENES:
        player = PompeiiCutscenes(app.font_sub, app.font_small)
        player.enqueue([dict(base, kind=kind)])
        for fraction in (0.0, 0.3, 0.6, 0.99):
            player.elapsed = fraction * DURATION
            player.draw(app.canvas)
        player.update(DURATION)
        assert not player.active


def test_run_requests_the_scenes_the_user_chose():
    sim = PompeiiSimulation(seed=2)
    kinds = set()
    while True:
        record = sim.step()
        if record is None or sim.t > 40:
            break
        kinds |= {scene["kind"] for scene in sim.scenes}
    assert {"column_street", "bay_wide", "crowd_aerial", "person_closeup"} <= kinds


def test_scenes_never_change_results():
    a = PompeiiSimulation(seed=5, population=1_500).run()
    b = PompeiiSimulation(seed=5, population=1_500)
    while b.step() is not None:
        b.scenes.clear()
    assert a["crowd"]["counts"] == b.counts()


def test_panels_default_to_different_roles_chosen_by_seed(stepped):
    panels = SplitPanels(stepped)
    assert len(panels.people) == 3 and len({p.role for p in panels.people}) == 3
    assert [p.id for p in SplitPanels(stepped).people] == [p.id for p in panels.people]
    other = SplitPanels(PompeiiSimulation(seed=12, population=1_500))
    assert [p.id for p in other.people] != [p.id for p in panels.people]


def test_panels_replace_in_turn_and_start_logging(stepped):
    panels = SplitPanels(stepped)
    target = next(p for p in stepped.people if p not in panels.people)
    panels.replace(target)
    assert panels.people[0] is target and target.id in stepped.watched


def test_panels_draw(stepped):
    app = FakeApp(stepped)
    panels = SplitPanels(stepped)
    stepped.step()
    panels.draw(app.canvas, 916, 12, 668, 876, (app.font_sub, app.font_small, app.font_small))


def test_thoughts_only_use_model_values_and_never_mention_motives():
    person = Citizen(0, "enslaved", 0, (21, 23), (21, 23))
    record = dict(story="A servant brings news", action_label="Stays at their work", quantum=dict(p_danger=0.5))
    text = thought_text(person, record)
    assert text == "A servant brings news. Belief is unsure. Stays at their work."
    for word in ("master", "afraid", "fear", "owner", "family", "scared", "want"):
        assert word not in text.lower()
    assert danger_phrase(None) == "No belief value for this mind."
    person.is_alive, person.cause_of_death = False, "roof_collapse"
    assert thought_text(person, record) == "Died: roof collapse."


def test_views_draw_and_switch_maps_and_pick_people(stepped):
    app = FakeApp(stepped)
    app.step_idx = stepped.t
    view = CityView(app)
    view.draw(app)
    view.toggle()
    view.draw(app)
    assert view.show_region
    view.toggle()
    person = next(p for p in stepped.people if p.is_alive and p.status == "city")
    assert view.pick_person(stepped, view.person_xy(person)) is not None
    assert view.pick_person(stepped, (-500, -500)) is None
    assert mini_map(stepped.world, 300).get_width() == 300


# ---- Step 7: connected to the GUI ----
from engine.gui import IslandVisualizerApp


def _pompeii_app():
    app = IslandVisualizerApp(seed=105, start_screen="event_choice")
    app._handle_mouse_click(app.btn_choice_pompeii.rect.center)
    return app


def _finish_step(app):
    app._worker.join()
    app._pompeii_poll_step()


def test_gui_opens_pompeii_from_the_choice_screen():
    app = _pompeii_app()
    assert app.scenario == "pompeii" and app.app_state == "home" and app.max_steps == HORIZON
    app.draw((5, 5))
    app._handle_mouse_click(app.btn_launch.rect.center)
    assert app.app_state == "sim" and isinstance(app.engine, PompeiiSimulation)
    assert app.show_split_panels and len(app.split_panels.people) == 3
    app.draw((5, 5))


def test_home_settings_reach_the_simulation():
    app = _pompeii_app()
    assert app.pompeii_settings == dict(event_mapping="B", population=11_500, date="august", quake=True, restrict_enslaved=False, crowding=True)
    for key, value in dict(event_mapping="C", population=11_500, date="autumn", quake=False, restrict_enslaved=True, crowding=False).items():
        app.pompeii_settings[key] = value
    app._handle_mouse_click(app.btn_launch.rect.center)
    assert app.engine.event_mapping == "C" and app.engine.crowding is False and app.engine.restrict_enslaved is True
    assert app.engine.eruption.date == "autumn" and app.engine.eruption.quake_enabled is False


def test_setting_buttons_cycle():
    app = _pompeii_app()
    before = app.pompeii_settings["date"]
    app._cycle_pompeii_setting(2)
    assert app.pompeii_settings["date"] != before and "Date" in app.step_buttons[2].text


def test_background_step_gives_the_same_result_as_a_direct_run():
    direct = PompeiiSimulation(seed=105, population=1_500, event_mapping="C")
    for _ in range(12):
        direct.step()
    app = _pompeii_app()
    app.pompeii_settings.update(population=1_500, event_mapping="C")
    app._handle_mouse_click(app.btn_launch.rect.center)
    app.cutscene.enabled = False
    for _ in range(12):
        app.step_forward()
        _finish_step(app)
    assert app.step_idx == 12 and app.engine.counts() == direct.counts()


def test_keys_switch_map_panels_cutscenes_and_person():
    app = _pompeii_app()
    app.pompeii_settings["population"] = 1_500
    app._handle_mouse_click(app.btn_launch.rect.center)
    press = lambda key: app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""), (5, 5))
    app.cutscene.enabled = False
    app.step_forward()
    _finish_step(app)
    press(pygame.K_m)
    assert app.city_view.show_region
    app.draw((5, 5))
    press(pygame.K_m)
    press(pygame.K_p)
    assert not app.show_split_panels
    app.draw((5, 5))
    press(pygame.K_p)
    before = app.agent
    press(pygame.K_f)
    assert app.agent is app.engine.agent and app.agent is not before


def test_clicking_a_person_follows_them_and_fills_a_panel():
    app = _pompeii_app()
    app.pompeii_settings["population"] = 1_500
    app._handle_mouse_click(app.btn_launch.rect.center)
    target = next(p for p in app.engine.people if p.status == "city" and p not in app.split_panels.people and app.city_view.person_xy(p)[1] > 120)
    x, y = app.city_view.person_xy(target)
    app._handle_sim_click((x, y))
    assert app.agent in app.split_panels.people and app.agent is app.engine.agent


def test_whole_run_reaches_the_debrief_with_every_screen_drawn():
    app = _pompeii_app()
    app.pompeii_settings.update(population=1_500, event_mapping="C")
    app._handle_mouse_click(app.btn_launch.rect.center)
    app.cutscene.enabled = False
    app.show_split_panels = False
    for _ in range(HORIZON + 1):
        app.step_forward()
        if app._worker is not None:
            _finish_step(app)
        if app.show_debrief_modal:
            break
        if app.step_idx % 25 == 0:
            app.draw((5, 5))
    assert app.show_debrief_modal
    app.draw((5, 5))


def test_other_scenarios_keep_their_length_and_simulation():
    app = IslandVisualizerApp(seed=105, start_screen="event_choice")
    app._handle_mouse_click(app.btn_choice_island.rect.center)
    assert app.max_steps == 36 and not isinstance(app.engine, PompeiiSimulation) and app.city_view is None
    app.app_state = "event_choice"
    app._handle_mouse_click(app.btn_choice_pompeii.rect.center)
    app.app_state = "event_choice"
    app._handle_mouse_click(app.btn_choice_volcano.rect.center)
    app._config_on_start()  # the new configuration screen sets the length when a run starts
    assert app.scenario == "volcano" and app.max_steps == 36 and app.split_panels is None

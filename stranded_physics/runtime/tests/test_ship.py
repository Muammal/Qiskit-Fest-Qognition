"""Seats, boarding and the water, on a small ship with no records, so these don't depend on the Titanic's."""
from dataclasses import replace

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities.api import parse_scenario
from stranded_physics.entities.build import check_scenario, to_spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.body import STATE_KEYS
from stranded_physics.runtime.ship import ADULT_FEMALE, ADULT_MALE, BoatStation, CHILD, ShipSimulation, _board, passengers_of, play_ship, summary
from stranded_physics.runtime.simulation import Shared

WEATHER = {"kind": "weather", "source": "dials", "rain_mm_h": 0., "wind_m_s": 0., "wind_bearing_deg": 0., "temperature_c": 0., "upper_wind_m_s": 0., "upper_bearing_deg": 0.}
SHIP = {"kind": "ship", "source": "dials", "length_m": 100., "beam_m": 20., "draught_m": 5., "displacement_t": 8000., "compartments": 6, "bulkhead_top_m": 1., "boat_deck_m": 4.}
BREACH = {"kind": "breach", "source": "dials", "first_compartment": 0, "holed": 3, "area_m2": 4., "impact_minutes": 10., "alarm_minutes": 15.}
SEA = {"kind": "sea", "source": "dials", "temperature_c": 0.}


def boats(count=2, seats=5, **extra):
    return {"kind": "lifeboats", "source": "dials", "boats": count, "seats": seats, "first_launch_minutes": 10., "last_launch_minutes": 30., "women_first": 1, "port_women_only": 0, **extra}


def people(men=10, women=10, children=0, mind="classical", **extra):
    return {"kind": "passengers", "source": "dials", "name": "aboard", "mind": mind, "men": men, "women": women, "children": children, "deck_from": .3, "deck_to": .7, "reach_minutes": 0., "boat_crew": 0., **extra}


def scenario(*entities, hours=3):
    return parse_scenario({"id": "small_ship", "title": "A small ship", "place": "fictional", "start_utc": "2000-01-01T00:00:00+00:00", "hours": hours, "step_minutes": 10, "local_utc_offset": 0,
                           "entity": [SHIP, BREACH, SEA, WEATHER, *entities]})


def go(action):
    return lambda state: {"action": action, "probs": {action: 1.}, "reason": "test"}


def built(*entities):
    file = scenario(*entities)
    return file, build_pack(to_spec(file, 1), 1)


def test_a_small_ship_sinks_by_its_own_flooding_model():
    _, pack = built(boats(), people())
    assert pack.series("ship.afloat")[0] == 1 and pack.series("ship.afloat")[-1] == 0


def test_seats_are_never_exceeded():
    file, pack = built(boats(count=2, seats=3), people(men=30, women=30))
    result = play_ship(pack, file)
    assert sum(person.boat is not None for person in result) <= 6


def stations_and_people(pack, file, count=1):
    grid = pack.grid
    shared = Shared(pack)
    who = passengers_of(file, grid, 100., 20.)
    return [ShipSimulation(pack, passenger, index, shared, []) for index, passenger in enumerate(who)]


def place(people_here, xy):
    for person in people_here:
        person.agent.xy_m = xy


def test_women_and_children_board_first():
    file, pack = built(boats(), people(men=3, women=2, children=1))
    aboard = stations_and_people(pack, file)
    station = BoatStation(aboard[0].agent.xy_m, 3, 99999.)
    place(aboard, station.xy)
    _board(aboard, [station], 0., True, False, 5., 0.)
    assert sorted(p.passenger.group for p in aboard if p.boat) == [ADULT_FEMALE, ADULT_FEMALE, CHILD]


def test_men_board_when_no_women_or_children_are_waiting():
    file, pack = built(boats(), people(men=3, women=0))
    aboard = stations_and_people(pack, file)
    station = BoatStation(aboard[0].agent.xy_m, 2, 99999.)
    place(aboard, station.xy)
    _board(aboard, [station], 0., True, False, 5., 0.)
    assert sum(p.boat is not None for p in aboard) == 2


def test_a_port_boat_can_refuse_men_while_seats_stand_empty():
    file, pack = built(boats(), people(men=3, women=0))
    aboard = stations_and_people(pack, file)
    station = BoatStation((aboard[0].agent.xy_m[0], 999.), 3, 99999.)
    place(aboard, station.xy)
    _board(aboard, [station], 0., True, True, 5., 0.)
    assert not any(p.boat for p in aboard) and station.seats == 3


def test_seamen_board_first_whatever_the_rule():
    file, pack = built(boats(), people(men=5, women=2, boat_crew=.4))
    aboard = stations_and_people(pack, file)
    station = BoatStation(aboard[0].agent.xy_m, 2, 99999.)
    place(aboard, station.xy)
    _board(aboard, [station], 0., True, False, 5., 0.)
    assert all(p.passenger.boat_crew for p in aboard if p.boat) and sum(p.boat is not None for p in aboard) == 2


def test_a_boat_that_has_left_takes_nobody():
    file, pack = built(boats(), people(women=2, men=0))
    aboard = stations_and_people(pack, file)
    station = BoatStation(aboard[0].agent.xy_m, 2, 100.)
    place(aboard, station.xy)
    _board(aboard, [station], 200., True, False, 5., 0.)
    assert not any(p.boat for p in aboard) and station.seats == 2


def test_people_in_a_boat_survive_and_people_left_behind_do_not():
    file, pack = built(boats(count=1, seats=200), people(men=0, women=20))
    aboard = play_ship(pack, file)
    for person in aboard:
        assert person.agent.alive == (person.boat is not None) or person.in_water_since is not None
    assert all(person.agent.alive for person in aboard if person.boat is not None)


def test_nobody_leaves_before_reaching_the_boat_deck():
    file, pack = built(boats(), people(reach_minutes=120.))
    person = stations_and_people(pack, file)[0]
    person.warned = True
    assert person._walk_goal("hide") is None


def test_a_person_who_stays_put_ends_in_the_water():
    file, pack = built(boats(), people(men=1, women=0))
    person = stations_and_people(pack, file)[0]
    person.decide_fn = go("rest")
    for step in range(pack.time.n):
        person.step()
        person.after_step((step + 1) * pack.time.dt_s)
    assert person.in_water_since is not None


def test_a_longer_time_in_the_water_can_only_be_worse():
    file, pack = built(boats(), people(men=1, women=0))
    person = stations_and_people(pack, file)[0]
    person.in_water_since, person.fate = 0., .5
    person.after_step(60.)
    assert person.agent.alive
    person.after_step(100 * 3600.)
    assert not person.agent.alive and person.agent.cause == "immersion"


def test_the_same_seed_repeats():
    file, pack = built(boats(), people())
    assert [p.agent.alive for p in play_ship(pack, file)] == [p.agent.alive for p in play_ship(pack, file)]


def test_a_mind_sees_only_the_contract_and_only_whole_hours():
    file, pack = built(boats(), people(men=1, women=0))
    person = stations_and_people(pack, file)[0]
    seen = []

    def watching(state):
        seen.append(state)
        return go("rest")(state)

    person.decide_fn = watching
    for _ in range(5):
        person.step()
    assert all(set(state) == STATE_KEYS for state in seen)
    assert all(isinstance(state["hour"], int) for state in seen)


def test_short_steps_keep_the_clock_right():
    file, pack = built(boats(), people(men=1, women=0))
    person = stations_and_people(pack, file)[0]
    person.decide_fn = go("rest")
    start = person.agent.hour
    for _ in range(7):
        person.step()
    assert (person.agent.hour - start) % 24 == 1 and person.agent.minute == 10


def test_summary_groups():
    file, pack = built(boats(), people(men=2, women=2, children=2))
    result = summary(play_ship(pack, file))
    assert {"all", ADULT_MALE, ADULT_FEMALE, CHILD, "aboard", "in_boats"} <= set(result)


@pytest.mark.parametrize("extra, message", [({"kind": "person", "source": "dials", "start_lon": -61.2, "start_lat": 13.3}, "own map"), ({"kind": "terrain", "source": "replay", "event": "st_vincent"}, "own map")])
def test_a_ship_cannot_share_a_scenario_with_land(extra, message):
    with pytest.raises(InterfaceError, match=message):
        check_scenario(scenario(extra))


def test_a_breach_past_the_end_of_the_ship_is_refused():
    table = scenario(boats(), people())
    entities = tuple(replace(e, settings={**e.settings, "first_compartment": 5, "holed": 3}) if e.kind == "breach" else e for e in table.entities)
    with pytest.raises(InterfaceError, match="runs past"):
        to_spec(replace(table, entities=entities), 1)


def test_two_hour_scenarios_need_no_new_key():
    assert parse_scenario({"id": "x", "title": "x", "place": "fictional", "start_utc": "2000-01-01T00:00:00+00:00", "hours": 4, "step_hours": 2, "local_utc_offset": 0, "entity": [WEATHER]}).step_s == 7200.
    with pytest.raises(InterfaceError, match="one of step_hours"):
        parse_scenario({"id": "x", "title": "x", "place": "fictional", "start_utc": "2000-01-01T00:00:00+00:00", "hours": 4, "local_utc_offset": 0, "entity": [WEATHER]})
    assert np.isclose(scenario().step_s, 600.)

"""People, groups, resources and storm-only play, from scenario files."""
from __future__ import annotations

from pathlib import Path

import pytest

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities.api import parse_scenario
from stranded_physics.entities.build import check_scenario, people_of

ROOT = Path(__file__).resolve().parents[3]
HAS_RAW = (ROOT / "artifacts/physics/raw/atmos/weather_st_vincent.json").exists()
TERRAIN = {"kind": "terrain", "source": "replay", "event": "st_vincent"}
WEATHER = {"kind": "weather", "source": "replay", "event": "st_vincent"}
SHELTER = {"kind": "shelter", "source": "dials", "lon": -61.267, "lat": 13.233}


def person(**changes):
    return {"kind": "person", "source": "dials", "start_lon": -61.243, "start_lat": 13.283, **changes}


def group(**changes):
    return {"kind": "group", "source": "dials", "start_lon": -61.243, "start_lat": 13.283, "count": 5, "radius_km": 1., "name": "Village", **changes}


def scenario(*entities, start="2021-04-08T00:00:00+00:00", hours=24):
    return parse_scenario({"id": "people", "title": "People", "place": "real", "start_utc": start, "hours": hours, "step_hours": 2, "local_utc_offset": -4, "entity": list(entities)})


def test_a_group_becomes_that_many_people_inside_its_radius():
    people = people_of(scenario(TERRAIN, group(count=12, radius_km=2.)))
    assert len(people) == 12
    assert all(abs(p.start[0] + 61.243) <= 2. / 111. + 1e-9 and abs(p.start[1] - 13.283) <= 2. / 111. + 1e-9 for p in people)
    assert len({p.start for p in people}) == 12


def test_a_groups_spread_never_changes_between_runs():
    file = scenario(TERRAIN, group())
    assert people_of(file) == people_of(file)


def test_people_keep_the_mind_they_were_given():
    minds = [p.mind for p in people_of(scenario(TERRAIN, person(mind="classical"), group(count=2, mind="classical_mixture"), person()))]
    assert minds == ["classical", "classical_mixture", "classical_mixture", "quantum"]


def test_an_unknown_mind_or_resource_is_refused():
    with pytest.raises(InterfaceError, match="telepathy"):
        scenario(TERRAIN, person(mind="telepathy"))
    with pytest.raises(InterfaceError, match="what"):
        scenario(TERRAIN, {"kind": "resource", "source": "dials", "lon": 0., "lat": 0., "what": "gold"})


def test_a_group_of_too_many_is_refused_not_clamped():
    with pytest.raises(InterfaceError, match="outside"):
        check_scenario(scenario(TERRAIN, WEATHER, group(count=5000), SHELTER))


def test_people_need_a_shelter():
    with pytest.raises(InterfaceError, match="shelter"):
        check_scenario(scenario(TERRAIN, WEATHER, person()))


def test_a_scenario_without_an_eruption_is_now_allowed():
    check_scenario(scenario(TERRAIN, WEATHER, person(), SHELTER))


@pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
class TestPlaying:
    def play(self, file):
        from stranded_physics.entities.build import to_spec
        from stranded_physics.packs.builder import build_pack
        from stranded_physics.runtime.group import play_people
        pack = build_pack(to_spec(file), 1)
        return pack, play_people(pack, [p.mind for p in people_of(file)])

    def test_different_people_start_in_different_places(self):
        pack, runs = self.play(scenario(TERRAIN, WEATHER, person(), person(start_lon=-61.226, start_lat=13.317), SHELTER))
        assert runs[0]["steps"][0]["state"]["pos"] != runs[1]["steps"][0]["state"]["pos"]

    def test_all_three_minds_play_side_by_side_with_exact_contract_keys(self):
        from stranded_physics.runtime.body import NEED_KEYS, STATE_KEYS
        pack, runs = self.play(scenario(TERRAIN, WEATHER, person(mind="quantum"), person(mind="classical_mixture"), person(mind="classical"), SHELTER))
        assert len(runs) == 3
        assert all(set(s["state"]) == STATE_KEYS and set(s["state"]["needs"]) == NEED_KEYS for run in runs for s in run["steps"])

    def test_a_storm_only_scenario_plays_and_the_storm_is_noticed(self):
        storm = {"kind": "storm", "source": "replay", "event": "beryl_2024", "site_lon": -61.227, "site_lat": 13.158}
        file = scenario(TERRAIN, WEATHER, storm, person(), SHELTER, start="2024-06-30T00:00:00+00:00", hours=72)
        pack, runs = self.play(file)
        run = runs[0]
        assert len(run["steps"]) == 36 and not pack.has("eruption.phase")
        assert "storm" in {s["event"] for s in run["steps"]}
        assert {s["phase"] for s in run["steps"]} == {"none"}
        assert run["world"]["volcano"]["erupts"] is False

    def test_sharing_the_map_and_routes_changes_nobodys_result(self):
        from stranded_physics.runtime.simulation import PackSimulation
        pack, together = self.play(scenario(TERRAIN, WEATHER, person(mind="quantum"), person(mind="classical", start_lon=-61.226, start_lat=13.317), SHELTER))
        apart = [PackSimulation(pack, mind_type=mind, person=index).run() for index, mind in enumerate(("quantum", "classical"))]
        assert [run["steps"] for run in together] == [run["steps"] for run in apart]
        assert [run["outcome"] for run in together] == [run["outcome"] for run in apart]

    def test_food_near_a_person_lifts_hunger_when_they_forage(self):
        def forage(state):
            return {"action": "forage", "probs": {"forage": 1.}, "reason": "test"}
        from stranded_physics.entities.build import to_spec
        from stranded_physics.packs.builder import build_pack
        from stranded_physics.runtime.simulation import PackSimulation
        food = {"kind": "resource", "source": "dials", "what": "food", "lon": -61.243, "lat": 13.283}
        fed = PackSimulation(build_pack(to_spec(scenario(TERRAIN, WEATHER, person(), SHELTER, food)), 1), decide_fn=forage).run()
        hungry = PackSimulation(build_pack(to_spec(scenario(TERRAIN, WEATHER, person(), SHELTER)), 1), decide_fn=forage).run()
        assert fed["steps"][-1]["state"]["needs"]["hunger"] > hungry["steps"][-1]["state"]["needs"]["hunger"]

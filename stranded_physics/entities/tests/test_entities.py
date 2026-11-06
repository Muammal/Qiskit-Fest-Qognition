"""Scenario files must refuse what they can't honour, and must reproduce the hard-coded St Vincent scenario exactly."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities.api import dump_scenario, load_scenario, parse_scenario
from stranded_physics.entities.build import check_scenario

ROOT = Path(__file__).resolve().parents[3]
CARDS = ROOT / "stranded_physics/scenario_cards"
HAS_RAW = (ROOT / "artifacts/physics/raw/atmos/weather_st_vincent.json").exists()


def table(*entities, **changes):
    base = {
        "id": "x",
        "title": "x",
        "place": "real",
        "start_utc": "2021-04-08T00:00:00+00:00",
        "hours": 96,
        "step_hours": 2,
        "local_utc_offset": -4,
        "entity": list(entities),
    }
    return {**base, **changes}


TERRAIN = {"kind": "terrain", "source": "replay", "event": "st_vincent"}
WEATHER = {"kind": "weather", "source": "replay", "event": "st_vincent"}
ERUPTION = {"kind": "eruption", "source": "replay", "event": "st_vincent_2021"}
PERSON = {"kind": "person", "source": "dials", "start_lon": -61.2, "start_lat": 13.3}
SHELTER = {"kind": "shelter", "source": "dials", "lon": -61.267, "lat": 13.233}


def checked(*entities, **changes):
    check_scenario(parse_scenario(table(*entities, **changes)))


def test_a_complete_scenario_passes():
    checked(TERRAIN, WEATHER, ERUPTION, PERSON, SHELTER)


@pytest.mark.parametrize(
    "entity, message",
    [
        ({"kind": "dragon", "source": "dials"}, "dragon"),
        ({"kind": "storm", "source": "wishes"}, "wishes"),
        ({"source": "dials"}, "kind and a source"),
    ],
)
def test_unknown_kinds_and_sources_are_refused(entity, message):
    with pytest.raises(InterfaceError, match=message):
        checked(entity)


def test_a_source_not_built_yet_says_which_stage_builds_it():
    with pytest.raises(InterfaceError, match="supports"):
        checked(TERRAIN, {"kind": "shelter", "source": "catalogue", "lon": -61.2, "lat": 13.3})


def test_an_unknown_recorded_event_is_refused():
    with pytest.raises(InterfaceError, match="pinatubo"):
        checked(TERRAIN, {"kind": "eruption", "source": "replay", "event": "pinatubo"})


def test_a_typo_in_a_setting_is_refused_rather_than_ignored():
    with pytest.raises(InterfaceError, match="start_latt"):
        checked(TERRAIN, WEATHER, ERUPTION, {"kind": "person", "source": "dials", "start_lon": 0.0, "start_latt": 0.0}, SHELTER)


def test_a_missing_setting_is_refused():
    with pytest.raises(InterfaceError, match="start_lat"):
        checked(TERRAIN, WEATHER, ERUPTION, {"kind": "person", "source": "dials", "start_lon": 0.0}, SHELTER)


def test_a_setting_out_of_range_is_refused_not_clamped():
    with pytest.raises(InterfaceError, match="outside"):
        checked(TERRAIN, WEATHER, ERUPTION, {**PERSON, "start_lat": 123.0}, SHELTER)


def test_an_entity_missing_what_it_depends_on_is_refused():
    with pytest.raises(InterfaceError, match="eruption"):
        checked(TERRAIN, WEATHER, {"kind": "ash", "source": "replay"})


def test_a_person_needs_a_shelter():
    with pytest.raises(InterfaceError, match="shelter"):
        checked(TERRAIN, WEATHER, ERUPTION, PERSON)


@pytest.mark.parametrize(
    "changes, message", [({"place": "mars"}, "place"), ({"hours": 7}, "multiple"), ({"start_utc": "2021-04-08T00:00:00"}, "timezone"), ({"extra": 1}, "extra")]
)
def test_a_badly_formed_file_is_refused(changes, message):
    with pytest.raises(InterfaceError, match=message):
        parse_scenario(table(TERRAIN, **changes))


@pytest.mark.parametrize("name", ["st_vincent_2021.toml", "beryl_2024.toml"])
def test_saving_and_reloading_gives_the_same_scenario(name, tmp_path):
    scenario = load_scenario(CARDS / name)
    path = tmp_path / "again.toml"
    path.write_text(dump_scenario(scenario), encoding="utf-8")
    assert load_scenario(path) == scenario


def test_the_scenario_lists_its_categories_for_the_checker():
    assert load_scenario(CARDS / "st_vincent_2021.toml").uses() == ("terrain", "atmos", "eruption", "tephra", "exposure", "pdc", "lahar", "agent")


@pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
def test_st_vincent_from_a_file_matches_the_hard_coded_scenario_exactly():
    from stranded_physics.entities.build import to_spec
    from stranded_physics.packs.builder import build_pack
    from stranded_physics.packs.st_vincent_2021 import scenario as hard_coded

    from_file = build_pack(to_spec(load_scenario(CARDS / "st_vincent_2021.toml")), 3)
    original = build_pack(hard_coded("richmond"), 3)
    assert sorted(from_file.header["fields"]) == sorted(original.header["fields"])
    for name in original.header["fields"]:
        assert np.array_equal(from_file._arrays[name], original._arrays[name]), name
    assert np.array_equal(from_file.agent_uniforms, original.agent_uniforms)
    assert from_file.sites == original.sites
    assert from_file.t0_local_hour == original.t0_local_hour

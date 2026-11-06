"""Generated land and weather through the entity layer."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from stranded_physics.core.api import InterfaceError
from stranded_physics.domains.atmos.generator import ISLANDS
from stranded_physics.domains.terrain.drainage import route, share_draining_out
from stranded_physics.entities import draft as edit
from stranded_physics.entities.api import EntitySpec, load_scenario, parse_scenario
from stranded_physics.entities.build import check_scenario, to_spec
from stranded_physics.entities.kinds import WEATHER_ISLANDS, check_entity
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.simulation import PackSimulation

ROOT = Path(__file__).resolve().parents[3]
HAS_RAW = (ROOT / "artifacts/physics/raw/atmos/weather_st_vincent.json").exists()
needs_raw = pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
CARD = Path(__file__).resolve().parents[2] / "scenario_cards" / "generated_island.toml"


def test_the_island_list_matches_the_generator():
    assert WEATHER_ISLANDS == ISLANDS


@pytest.mark.parametrize(
    "entity, message",
    [
        (EntitySpec("terrain", "dials", settings={"summit_m": 500.0}), "area_km2"),
        (EntitySpec("terrain", "catalogue", settings={"summit_m": 9000.0}), "summit_m"),
        (EntitySpec("weather", "catalogue", what="atlantis"), "atlantis"),
        (EntitySpec("weather", "catalogue", what="la_palma", settings={"month": 13}), "month"),
        (EntitySpec("weather", "catalogue", what="la_palma", settings={"month": 2.5}), "whole"),
        (EntitySpec("weather", "dials", settings={"rain_mm_h": 1.0}), "wind_m_s"),
    ],
)
def test_bad_settings_are_refused(entity, message):
    with pytest.raises(InterfaceError, match=message):
        check_entity(entity)


def test_a_generated_island_cannot_claim_to_be_a_real_place():
    table = {
        "id": "t",
        "title": "t",
        "place": "real",
        "start_utc": "2023-06-01T00:00:00+00:00",
        "hours": 24,
        "step_hours": 2,
        "local_utc_offset": 0,
        "entity": [{"kind": "terrain", "source": "catalogue"}],
    }
    with pytest.raises(InterfaceError, match="real place"):
        check_scenario(parse_scenario(table))


def scenario():
    return load_scenario(CARD)


@needs_raw
def test_the_seed_changes_the_island_and_it_repeats():
    first, again, other = (build_pack(to_spec(scenario(), seed), seed) for seed in (1, 1, 2))
    assert first.content_hash == again.content_hash
    assert not np.array_equal(first.frame("terrain.elevation"), other.frame("terrain.elevation"))


@needs_raw
def test_a_whole_generated_scenario_plays_on_its_own_land():
    for seed in (1, 2, 3):
        pack = build_pack(to_spec(scenario(), seed), seed)
        land = pack.frame("terrain.land_mask") > 0
        assert share_draining_out(route(pack.frame("terrain.elevation"), land, pack.grid.dx_m), land) == 1.0
        for site in ("spawn", "assembly", "water"):
            for point in pack.sites[site]:
                assert pack.sample("terrain.land_mask", point) > 0
        assert PackSimulation(pack, mind_type="classical").run()["steps"]


@needs_raw
def test_dials_set_the_island():
    entities = tuple(replace(e, source="dials", settings={"summit_m": 800.0, "area_km2": 60.0}) if e.kind == "terrain" else e for e in scenario().entities)
    pack = build_pack(to_spec(replace(scenario(), entities=entities), 1), 1)
    land = pack.frame("terrain.land_mask") > 0
    assert abs(land.sum() * pack.grid.dx_m**2 / 1e6 - 60.0) <= 3.0
    assert abs(pack.frame("terrain.elevation")[land].max() - 800.0) <= 40.0


def test_hand_set_weather_is_used():
    settings = {"rain_mm_h": 3.0, "wind_m_s": 7.0, "wind_bearing_deg": 90.0, "temperature_c": 25.0, "upper_wind_m_s": 30.0, "upper_bearing_deg": 45.0}
    entities = tuple(replace(e, source="dials", what="", settings=settings) if e.kind == "weather" else e for e in scenario().entities)
    pack = build_pack(to_spec(replace(scenario(), entities=entities), 1), 1)
    assert np.allclose(pack.series("atmos.rain_rate"), 3.0) and np.allclose(pack.series("atmos.wind_speed_200hpa"), 30.0)


def test_weather_source_switching_in_the_builder():
    draft = edit.new_draft()
    index = next(i for i, e in enumerate(draft.entries) if e["kind"] == "weather")
    draft = edit.set_choice(draft, index, "source", "catalogue")
    assert draft.entries[index]["what"] == "st_vincent" and "event" not in draft.entries[index]
    assert edit.choices(draft.entries[index], "what") == ISLANDS
    draft = edit.set_choice(draft, index, "what", "stromboli")
    assert edit.problem(draft) is None
    draft = edit.set_choice(draft, index, "source", "dials")
    assert "what" not in draft.entries[index] and draft.entries[index]["wind_m_s"] == 6.0
    assert edit.problem(draft) is None
    draft = edit.set_choice(draft, index, "source", "replay")
    assert draft.entries[index]["event"] == "st_vincent" and "wind_m_s" not in draft.entries[index]


def test_terrain_source_switching_in_the_builder():
    draft = edit.new_draft()
    index = next(i for i, e in enumerate(draft.entries) if e["kind"] == "terrain")
    draft = edit.set_choice(draft, index, "source", "catalogue")
    assert "real place" in edit.problem(draft)
    draft = edit.set_header(draft, "place", "generated")
    assert edit.problem(draft) is None
    draft = edit.set_choice(draft, index, "source", "dials")
    assert draft.entries[index]["summit_m"] == 900.0 and edit.problem(draft) is None


def test_a_generated_scenario_saves_and_reloads(tmp_path):
    draft = edit.from_file(CARD)
    draft = edit.set_header(draft, "id", "my_island")
    path = edit.save_draft(draft, tmp_path)
    assert load_scenario(path) == edit.to_scenario(draft)

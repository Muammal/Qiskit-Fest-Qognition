"""Generated eruptions and storms through the entity layer: seeds, dials, refusals and evidence."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from stranded_physics.check import read_card, sort_gates
from stranded_physics.core.api import InterfaceError
from stranded_physics.domains.pdc.model import SETTINGS as PDC_SETTINGS
from stranded_physics.entities import draft as edit
from stranded_physics.entities.api import EntitySpec, load_scenario, parse_scenario
from stranded_physics.entities.build import check_scenario, to_spec
from stranded_physics.entities.kinds import check_entity
from stranded_physics.st_vincent import to_utm

ROOT = Path(__file__).resolve().parents[3]
HAS_RAW = (ROOT / "artifacts/physics/raw/atmos/weather_st_vincent.json").exists()
needs_raw = pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
CARDS = Path(__file__).resolve().parents[2] / "scenario_cards"
VENT = {"vent_lon": -61.18, "vent_lat": 13.33}
SITE = {"site_lon": -61.227, "site_lat": 13.158}


def eruption(source="catalogue", **settings):
    return EntitySpec("eruption", source, settings={**VENT, **settings})


def domains(card: str, seed: int) -> dict:
    return {domain.id: domain for domain in to_spec(load_scenario(CARDS / f"{card}.toml"), seed).domains}


@needs_raw
def test_a_catalogue_eruption_depends_on_the_seed_and_repeats():
    first, again, other = (domains("generated_eruption", seed)["eruption"].generated for seed in (1, 1, 2))
    assert first == again
    assert first != other


@needs_raw
def test_a_flow_follows_a_generated_eruption_not_the_published_date():
    built = domains("generated_eruption", 1)
    assert built["pdc"].first_collapse_s == pytest.approx(built["eruption"].generated.onset_s + 6 * 3600.)


@needs_raw
def test_a_flow_with_no_delay_set_uses_the_labelled_assumption():
    scenario = load_scenario(CARDS / "generated_eruption.toml")
    entities = tuple(replace(e, settings={}) if e.kind == "flow" else e for e in scenario.entities)
    built = {d.id: d for d in to_spec(replace(scenario, entities=entities), 1).domains}
    assert built["pdc"].first_collapse_s == pytest.approx(built["eruption"].generated.onset_s + PDC_SETTINGS["generated_collapse_delay"])


@needs_raw
def test_a_recorded_eruption_keeps_its_published_flow_time():
    built = {d.id: d for d in to_spec(load_scenario(CARDS / "st_vincent_2021.toml")).domains}
    assert built["pdc"].first_collapse_s == PDC_SETTINGS["first_collapse_after_axis_start"]


@needs_raw
def test_the_depth_averaged_model_can_be_chosen():
    scenario = load_scenario(CARDS / "st_vincent_2021.toml")
    entities = tuple(replace(e, event="depth_averaged") if e.kind == "flow" else e for e in scenario.entities)
    chosen = replace(scenario, entities=entities)
    assert next(d for d in to_spec(chosen).domains if d.id == "pdc").tier == "T2"
    assert chosen.variants() == {"pdc": "t2"}


@needs_raw
def test_dials_override_sampling():
    check_entity(eruption(size=3))
    scenario = load_scenario(CARDS / "generated_eruption.toml")
    entities = tuple(replace(e, settings={**e.settings, "size": 2, "lead_hours": 5., "onset_hours": 30., "column_m": 4000.}) if e.kind == "eruption" else e for e in scenario.entities)
    made = next(d for d in to_spec(replace(scenario, entities=entities), 4).domains if d.id == "eruption").generated
    assert (made.size, made.lead_s, made.onset_s) == (2, 5 * 3600., 30 * 3600.)
    assert {event.height_m for event in made.events} == {4000.}


@pytest.mark.parametrize("entity, message", [
    (eruption(size=9), "size"),
    (eruption(size=2.5), "whole"),
    (EntitySpec("eruption", "catalogue", settings={"size": 3}), "vent_lon"),
    (EntitySpec("eruption", "dials", settings=VENT), "column_m"),
    (EntitySpec("eruption", "catalogue", "st_vincent_2021", settings=VENT), "event"),
    (EntitySpec("storm", "dials", settings=SITE), "max_wind_m_s"),
    (EntitySpec("storm", "catalogue", settings={**SITE, "speed_m_s": 99.}), "speed_m_s"),
])
def test_bad_settings_are_refused(entity, message):
    with pytest.raises(InterfaceError, match=message):
        check_entity(entity)


def scenario_with(*entities, hours=96):
    table = {"id": "t", "title": "t", "place": "generated", "start_utc": "2021-04-08T00:00:00+00:00", "hours": hours, "step_hours": 2, "local_utc_offset": -4,
             "entity": [{"kind": "terrain", "source": "replay", "event": "st_vincent"}, *entities]}
    return parse_scenario(table)


def test_an_eruption_after_the_scenario_ends_is_refused():
    with pytest.raises(InterfaceError, match="after this 96-hour"):
        check_scenario(scenario_with({"kind": "eruption", "source": "catalogue", **VENT, "onset_hours": 200.}))


def test_a_warning_before_the_scenario_starts_is_refused():
    with pytest.raises(InterfaceError, match="before the scenario"):
        check_scenario(scenario_with({"kind": "eruption", "source": "catalogue", **VENT, "onset_hours": 10., "lead_hours": 20.}))


def test_a_vent_off_the_map_is_refused():
    with pytest.raises(InterfaceError, match="outside the map"):
        check_scenario(scenario_with({"kind": "eruption", "source": "catalogue", "vent_lon": -61.0, "vent_lat": 12.5}))


def test_a_delay_on_a_recorded_eruption_is_refused():
    with pytest.raises(InterfaceError, match="delay_hours"):
        check_scenario(scenario_with({"kind": "eruption", "source": "replay", "event": "st_vincent_2021"}, {"kind": "flow", "source": "replay", "delay_hours": 3.}))


def test_a_long_catalogue_warning_cannot_break_a_short_scenario():
    from stranded_physics.domains.eruption.generator import from_dials
    for seed in range(200):
        made = from_dials(np.random.default_rng(seed), 40 * 3600.)
        assert made.lead_s <= .75 * 40 * 3600.


@needs_raw
def test_a_catalogue_storm_depends_on_the_seed():
    first, other = (domains("generated_storm", seed)["storm"].generated for seed in (1, 2))
    assert first.max_wind_m_s != other.max_wind_m_s or first.closest_km != other.closest_km


@needs_raw
def test_each_generated_card_builds_a_pack_and_someone_can_play_it():
    from stranded_physics.entities.build import check_events_happen
    from stranded_physics.packs.builder import build_pack
    from stranded_physics.runtime.simulation import PackSimulation
    for card, seed in (("generated_eruption", 1), ("generated_storm", 1)):
        pack = build_pack(to_spec(load_scenario(CARDS / f"{card}.toml"), seed), seed)
        check_events_happen(pack)
        timeline = PackSimulation(pack, mind_type="classical").run()
        assert timeline["steps"]


def test_the_vent_moves_the_hazard_zones():
    scenario = scenario_with({"kind": "eruption", "source": "catalogue", "vent_lon": -61.2, "vent_lat": 13.3, "onset_hours": 40.})
    terrain = next(d for d in to_spec(scenario).domains if d.id == "terrain")
    assert terrain.vent == to_utm((-61.2, 13.3))


def test_switching_source_leaves_no_stale_settings():
    draft = edit.new_draft()
    draft = edit.add_entity(draft, "eruption")
    index = len(draft.entries) - 1
    draft = edit.set_choice(draft, index, "source", "catalogue")
    assert "event" not in draft.entries[index]
    assert not set(draft.entries[index]) & {"size", "lead_hours"}
    draft = edit.place(draft, index, (-61.18, 13.33))
    draft = edit.set_choice(draft, index, "source", "dials")
    assert draft.entries[index]["size"] == 4 and draft.entries[index]["vent_lon"] == -61.18
    assert edit.problem(draft) is None
    draft = edit.set_choice(draft, index, "source", "replay")
    assert draft.entries[index]["event"] == "st_vincent_2021"
    assert "vent_lon" not in draft.entries[index]
    assert edit.problem(draft) is None


def test_editing_a_sampled_dial_overrides_it_and_range_is_enforced():
    draft = edit.add_entity(edit.new_draft(), "eruption")
    index = len(draft.entries) - 1
    draft = edit.set_choice(draft, index, "source", "catalogue")
    draft = edit.place(draft, index, (-61.18, 13.33))
    draft = edit.set_dial(draft, index, "size", "5")
    assert draft.entries[index]["size"] == 5
    assert edit.problem(draft) is None
    with pytest.raises(InterfaceError, match="outside"):
        edit.set_dial(draft, index, "size", "9")


def test_generator_evidence_counts_only_for_scenarios_using_the_generator():
    card = read_card(CARDS / "generated_eruption.toml")
    assert "generated_eruption" in card.evidence
    assert "generated_eruption" not in read_card(CARDS / "st_vincent_2021.toml").evidence
    assert "generated_storm" in read_card(CARDS / "generated_storm.toml").evidence


def test_a_models_results_count_only_for_that_model():
    t1 = {"id": "a", "title": "first model", "kind": "validation", "scenario": "s", "role": "prediction", "split": "holdout"}
    t2 = {**t1, "id": "b", "title": "second model", "model": "t2"}
    rows = [(t1, "PASS"), (t2, "FAIL")]
    assert sort_gates(rows, "s")["agrees"] == ["first model"] and not sort_gates(rows, "s")["disagrees"]
    assert sort_gates(rows, "s", "t2")["disagrees"] == ["second model"] and not sort_gates(rows, "s", "t2")["agrees"]


def test_a_small_eruption_makes_small_flows():
    from stranded_physics.domains.pdc.model import size_scale
    assert size_scale(PDC_SETTINGS["reference_erupted_mass"]) == pytest.approx(1.)
    assert size_scale(PDC_SETTINGS["reference_erupted_mass"] / 1000.) == pytest.approx(.1)


@needs_raw
def test_flows_stay_within_their_reach_limit():
    from stranded_physics.domains.pdc.model import distance_from
    from stranded_physics.packs.builder import build_pack
    scenario = load_scenario(CARDS / "generated_eruption.toml")
    entities = tuple(replace(e, settings={**e.settings, "size": 1, "onset_hours": 30., "lead_hours": 2.}) if e.kind == "eruption" else e for e in scenario.entities)
    spec = to_spec(replace(scenario, entities=entities), 3)
    flow = next(d for d in spec.domains if d.id == "pdc")
    pack = build_pack(spec, 3)
    reached = np.isfinite(pack.frame("pdc.arrival"))
    assert flow.reach_limit_m < 3000.
    assert reached.any() and distance_from(spec.grid, flow.vent)[reached].max() <= flow.reach_limit_m


@needs_raw
def test_gas_and_lava_build_from_a_scenario_and_someone_can_play_it():
    from stranded_physics.packs.builder import build_pack
    from stranded_physics.runtime.group import play_people
    scenario = load_scenario(CARDS / "st_vincent_2021_full.toml")
    pack = build_pack(to_spec(scenario, 1), 1)
    assert pack.has("gas.so2_concentration") and pack.has("lava.footprint") and pack.has("exposure.roof_failure")
    assert pack.frame("lava.footprint", 0.).sum() > 0
    assert pack.frame("lava.footprint", 47 * 7200.).sum() == 0  # The explosions destroyed the dome.
    assert play_people(pack, ["classical"])[0]["steps"]
    assert {"gas", "lava", "exposure"} <= set(scenario.uses())

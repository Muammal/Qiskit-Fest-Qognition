"""The builder's rules, tested without a window: bad values are refused, and a save reloads as the identical file."""
from __future__ import annotations

from pathlib import Path

import pytest

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities.api import dump_scenario, load_scenario
from stranded_physics.entities.draft import (
    add_entity, choices, from_file, new_draft, place, problem, remove_entity, save_draft, set_choice, set_dial, set_header, set_name, to_scenario,
)

ROOT = Path(__file__).resolve().parents[3]
CARDS = ROOT / "stranded_physics/scenario_cards"
RICHMOND = (-61.226, 13.317)
BARROUALLIE = (-61.267, 13.233)


def with_person_and_shelter():
    draft = place(add_entity(new_draft(), "person"), 2, RICHMOND)
    return place(add_entity(draft, "shelter"), 3, BARROUALLIE)


def test_a_new_draft_holds_the_land_and_weather_and_nothing_else():
    assert [entry["kind"] for entry in new_draft().entries] == ["terrain", "weather"]


def test_adding_an_entity_uses_only_what_is_built_and_leaves_its_position_unset():
    entry = add_entity(new_draft(), "person").entries[-1]
    assert entry["source"] == "dials" and entry["mind"] == "quantum"
    assert "start_lon" not in entry and "start_lat" not in entry


def test_an_unplaced_entity_is_named_as_the_next_problem():
    assert "start_lat" in problem(add_entity(new_draft(), "person"))


def test_people_without_a_shelter_are_named_as_the_next_problem():
    assert "shelter" in problem(place(add_entity(new_draft(), "person"), 2, RICHMOND))


def test_a_complete_draft_has_no_problem():
    assert problem(with_person_and_shelter()) is None


def test_editing_never_changes_the_draft_it_was_given():
    draft = with_person_and_shelter()
    before = dump_scenario(to_scenario(draft))
    set_dial(draft, 2, "start_lon", "-61.2")
    remove_entity(draft, 2)
    set_name(draft, 2, "Asha")
    assert dump_scenario(to_scenario(draft)) == before


@pytest.mark.parametrize("text", ["200", "-181", "nan", "inf", "north", ""])
def test_a_bad_dial_value_is_refused_not_clamped(text):
    with pytest.raises(InterfaceError):
        set_dial(with_person_and_shelter(), 2, "start_lon", text)


def test_a_part_of_a_person_is_refused():
    draft = place(add_entity(new_draft(), "group"), 2, RICHMOND)
    assert set_dial(draft, 2, "count", "12").entries[2]["count"] == 12
    with pytest.raises(InterfaceError, match="whole"):
        set_dial(draft, 2, "count", "4.5")


def test_a_file_asking_for_part_of_a_person_is_refused_too():
    from stranded_physics.entities.api import EntitySpec
    from stranded_physics.entities.kinds import check_entity
    with pytest.raises(InterfaceError, match="whole"):
        check_entity(EntitySpec("group", "dials", settings={"start_lon": RICHMOND[0], "start_lat": RICHMOND[1], "count": 4.5, "radius_km": 1.}))


def test_a_person_placed_off_the_map_is_named_as_the_problem():
    draft = place(add_entity(new_draft(), "person"), 2, (-60., 13.3))
    draft = place(add_entity(draft, "shelter"), 3, BARROUALLIE)
    assert "outside the map" in problem(draft)


def test_people_need_weather_because_it_is_what_they_feel():
    draft = with_person_and_shelter()
    assert "weather" in problem(remove_entity(draft, 1))


def test_only_the_runtimes_two_hour_step_is_accepted():
    with pytest.raises(InterfaceError, match="2-hour"):
        set_header(with_person_and_shelter(), "step_hours", "1")


@pytest.mark.parametrize("key, text", [
    ("id", "../../evil"), ("id", "Has Spaces"), ("id", ""), ("title", ""), ("title", "two\nlines"), ("place", "mars"),
    ("hours", "7"), ("hours", "-2"), ("hours", "lots"), ("start_utc", "2021-04-08T00:00:00"), ("start_utc", "soon"), ("local_utc_offset", "99"),
])
def test_a_bad_scenario_setting_is_refused(key, text):
    with pytest.raises(InterfaceError):
        set_header(new_draft(), key, text)


def test_choices_offer_only_what_is_real():
    draft = add_entity(add_entity(new_draft(), "resource"), "person")
    assert choices(draft.entries[2], "what") == ("water", "food")
    assert choices(draft.entries[3], "mind") == ("quantum", "classical_mixture", "classical")
    assert choices(draft.entries[0], "event") == ("st_vincent",)
    assert set_choice(draft, 3, "mind", "classical").entries[3]["mind"] == "classical"
    with pytest.raises(InterfaceError):
        set_choice(draft, 3, "mind", "telepathy")


def test_placing_sets_a_groups_middle():
    entry = place(add_entity(new_draft(), "group"), 2, RICHMOND).entries[2]
    assert (entry["start_lon"], entry["start_lat"]) == RICHMOND


@pytest.mark.parametrize("title", ['Asha\'s "village"', "back\\slash", "Île à Vache, été"])
def test_saving_and_reloading_gives_the_identical_file(title, tmp_path):
    draft = set_header(with_person_and_shelter(), "title", title)
    path = save_draft(draft, tmp_path)
    first = path.read_bytes()
    again = save_draft(from_file(path), tmp_path)
    assert again == path and again.read_bytes() == first
    assert load_scenario(path).title == title


@pytest.mark.parametrize("name", ["st_vincent_2021.toml", "beryl_2024.toml", "example_village.toml"])
def test_every_shipped_scenario_opens_unchanged(name):
    path = CARDS / name
    assert to_scenario(from_file(path)) == load_scenario(path)
    assert problem(from_file(path)) is None


def test_a_draft_with_a_problem_is_not_saved(tmp_path):
    with pytest.raises(InterfaceError, match="shelter"):
        save_draft(place(add_entity(new_draft(), "person"), 2, RICHMOND), tmp_path)
    assert not list(tmp_path.iterdir())


def test_a_saved_scenario_cannot_take_a_shipped_scenarios_name(tmp_path):
    """Results are tied to a scenario's id, so a copy under the same name would borrow evidence it hasn't earned."""
    with pytest.raises(InterfaceError, match="new id"):
        save_draft(from_file(CARDS / "st_vincent_2021.toml"), tmp_path)
    assert not list(tmp_path.iterdir())


def test_a_changed_copy_of_a_shipped_scenario_is_told_apart_from_the_original():
    from stranded_physics.entities.draft import borrows_evidence
    original = from_file(CARDS / "st_vincent_2021.toml")
    assert not borrows_evidence(original)
    changed = set_dial(original, 6, "start_lat", "13.32")
    assert borrows_evidence(changed)
    assert not borrows_evidence(set_header(changed, "id", "my_copy"))
    assert borrows_evidence(set_header(with_person_and_shelter(), "id", "st_vincent_2021"))


@pytest.mark.parametrize("name", ["nul", "con", "aux", "prn", "com1", "lpt9"])
def test_a_device_name_is_refused_as_an_id(name):
    with pytest.raises(InterfaceError, match="device"):
        set_header(new_draft(), "id", name)


def test_a_save_that_fails_its_check_keeps_the_previous_file(tmp_path, monkeypatch):
    from stranded_physics.entities import draft as module
    draft = with_person_and_shelter()
    path = save_draft(draft, tmp_path)
    first = path.read_bytes()
    changed = set_header(draft, "title", "Changed")
    monkeypatch.setattr(module, "dump_scenario", lambda scenario, real=module.dump_scenario, calls=[]: calls.append(1) or real(scenario) + "#" * len(calls))
    with pytest.raises(InterfaceError, match="identically"):
        save_draft(changed, tmp_path)
    assert path.read_bytes() == first and [p.name for p in tmp_path.iterdir()] == [path.name]


def test_a_file_that_cannot_be_read_is_refused_clearly(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("id = \n", encoding="utf-8")
    with pytest.raises(InterfaceError, match="bad.toml"):
        from_file(bad)

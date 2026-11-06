"""Drives the real game window with real clicks and keys, with no display. Stage 5 is done when a save reloads identically and the game runs it."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from stranded_physics.entities.api import load_scenario  # noqa: E402
from stranded_physics.entities.draft import from_file, place, set_header  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HAS_RAW = (ROOT / "artifacts/physics/raw/atmos/weather_st_vincent.json").exists()
needs_raw = pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
RICHMOND_ON_MAP = (0.38, 0.42)
BUILD_LIMIT_S = 120.0


@pytest.fixture
def app(tmp_path):
    from engine.gui import IslandVisualizerApp
    from main import open_builder

    window = IslandVisualizerApp(seed=101, start_screen="event_choice", builder_factory=open_builder)
    window._open_builder()
    window.builder.save_folder = tmp_path
    window.builder.sim_folder = tmp_path
    window.builder.guided, window.builder.start_open = False, False
    window.draw((0, 0))
    yield window
    pygame.quit()


def click_at(window, pos):
    window.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos), pos)
    window.draw((0, 0))


def press(window, label):
    window.draw((0, 0))
    hot = next(h for h in reversed(window.builder.hot) if h.label == label)
    click_at(window, hot.rect.center)


def tap(window, key, text=""):
    window.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text), (0, 0))
    window.draw((0, 0))


def type_into(window, label, text):
    press(window, label)
    window.builder.editing = (window.builder.editing[0], "", window.builder.editing[2])
    for letter in text:
        tap(window, ord(letter) if ord(letter) < 128 else 0, letter)
    tap(window, pygame.K_RETURN, "\r")


def on_map(window, fx, fy):
    from stranded_physics.builder_screen import MAP_RECT

    click_at(window, (MAP_RECT.x + int(fx * MAP_RECT.width), MAP_RECT.y + int(fy * MAP_RECT.height)))


def add_person_and_shelter(window):
    press(window, "add:person")
    on_map(window, *RICHMOND_ON_MAP)
    press(window, "add:shelter")
    on_map(window, 0.25, 0.85)


def wait_for_game(window):
    started = time.time()
    while window.app_state == "builder" and window.builder.building and time.time() - started < BUILD_LIMIT_S:
        window.draw((0, 0))
        time.sleep(0.05)
    window.draw((0, 0))


def test_the_game_says_so_when_it_was_started_without_the_builder():
    from engine.gui import IslandVisualizerApp

    window = IslandVisualizerApp(seed=101, start_screen="event_choice")
    window.draw((0, 0))
    window.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=window.btn_choice_build.rect.center), window.btn_choice_build.rect.center)
    assert window.app_state == "event_choice" and "main.py" in window.notice
    window.draw((0, 0))
    pygame.quit()


def test_the_menu_button_opens_the_builder():
    from engine.gui import IslandVisualizerApp
    from main import open_builder

    window = IslandVisualizerApp(seed=101, start_screen="event_choice", builder_factory=open_builder)
    window.draw((0, 0))
    window.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=window.btn_choice_build.rect.center), window.btn_choice_build.rect.center)
    assert window.app_state == "builder"
    pygame.quit()


def test_clicking_the_map_places_what_is_selected(app):
    press(app, "add:person")
    assert "start_lat" in app.builder.problem
    on_map(app, *RICHMOND_ON_MAP)
    entry = app.builder.draft.entries[-1]
    assert -61.4 < entry["start_lon"] < -61.0 and 13.2 < entry["start_lat"] < 13.4


def test_a_typed_value_out_of_range_is_refused_and_the_old_value_stays(app):
    press(app, "add:person")
    on_map(app, *RICHMOND_ON_MAP)
    before = app.builder.draft
    type_into(app, "field:dial:2:start_lat", "123")
    assert app.builder.draft is before
    assert app.builder.message.startswith("Refused") and "outside" in app.builder.message


def test_a_step_past_the_end_of_a_range_is_refused_not_clamped(app):
    press(app, "add:group")
    on_map(app, *RICHMOND_ON_MAP)
    assert app.builder.draft.entries[-1]["count"] == 1
    press(app, "minus:count")
    assert app.builder.draft.entries[-1]["count"] == 1 and "outside" in app.builder.message
    press(app, "plus:count")
    assert app.builder.draft.entries[-1]["count"] == 2


def test_the_problem_is_shown_until_it_is_fixed_and_play_is_off_until_then(app):
    press(app, "add:person")
    on_map(app, *RICHMOND_ON_MAP)
    assert "shelter" in app.builder.problem
    assert not [h for h in app.builder.hot if h.label == "PLAY THIS SCENARIO"]
    press(app, "add:shelter")
    on_map(app, 0.25, 0.85)
    assert app.builder.problem is None
    assert [h for h in app.builder.hot if h.label == "PLAY THIS SCENARIO"]


def test_removing_an_entity_takes_it_out(app):
    press(app, "add:person")
    press(app, "remove:2")
    assert [e["kind"] for e in app.builder.draft.entries] == ["terrain", "weather"]


def test_unsaved_changes_need_a_second_click_to_discard(app):
    press(app, "add:person")
    press(app, "New")
    assert len(app.builder.draft.entries) == 3 and "unsaved" in app.builder.message
    press(app, "New")
    assert len(app.builder.draft.entries) == 2


def test_saving_on_screen_then_reopening_gives_the_identical_file(app, tmp_path):
    add_person_and_shelter(app)
    type_into(app, "field:title", 'Asha\'s "village"')
    type_into(app, "field:id", "ashas_village")
    press(app, "Save")
    path = tmp_path / "ashas_village.toml"
    first = path.read_bytes()
    assert "identical" in app.builder.message
    press(app, "New")
    press(app, "Open")
    press(app, "open:ashas_village")
    assert app.builder.draft.header["title"] == 'Asha\'s "village"'
    press(app, "Save")
    assert path.read_bytes() == first
    assert load_scenario(path).title == 'Asha\'s "village"'


def test_a_changed_shipped_scenario_does_not_show_the_originals_results(app):
    press(app, "Open")
    press(app, "open:st_vincent_2021")
    assert not any("Its results don't apply" in line for line, _ in app.builder.claims)
    press(app, "add:person")
    on_map(app, *RICHMOND_ON_MAP)
    shown = " ".join(line for line, _ in app.builder.claims)
    assert "Its results don't apply" in shown and "agree with reality" not in shown
    type_into(app, "field:id", "my_copy")
    assert "0 agree with reality, 0 disagree" in " ".join(line for line, _ in app.builder.claims)


def test_a_strange_seed_is_refused_not_fatal(app):
    type_into(app, "field:seed", "\u00b2")
    assert app.builder.seed == 101 and "whole number" in app.builder.message
    type_into(app, "field:seed", "7")
    assert app.builder.seed == 7


def test_every_saved_scenario_can_be_reached_in_the_open_list(app, tmp_path):
    from stranded_physics.entities.draft import add_entity, new_draft, save_draft

    for number in range(14):
        save_draft(
            set_header(
                place(place(add_entity(add_entity(new_draft(), "person"), "shelter"), 2, (-61.226, 13.317)), 3, (-61.267, 13.233)), "id", f"saved_{number:02d}"
            ),
            tmp_path,
        )
    press(app, "Open")
    assert not [h for h in app.builder.hot if h.label == "open:saved_13"]
    app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-30), (0, 0))
    press(app, "open:saved_13")
    assert app.builder.draft.header["id"] == "saved_13"


def test_a_builder_that_cannot_start_leaves_the_original_game_playable(monkeypatch):
    from engine.gui import IslandVisualizerApp
    from main import open_builder
    from stranded_physics.entities import draft as module

    window = IslandVisualizerApp(seed=101, start_screen="event_choice", builder_factory=open_builder)
    monkeypatch.setattr(module, "new_draft", lambda: (_ for _ in ()).throw(FileNotFoundError("no template")))
    window._open_builder()
    assert window.app_state == "event_choice" and "no template" in window.notice
    window.draw((0, 0))
    pygame.quit()


def test_a_shipped_scenario_cannot_be_saved_over_its_evidence(app, tmp_path):
    press(app, "Open")
    press(app, "open:st_vincent_2021")
    press(app, "Save")
    assert "new id" in app.builder.message and not list(tmp_path.iterdir())


def test_a_build_that_fails_is_reported_not_fatal(app, monkeypatch):
    import stranded_physics.builder_screen as screen

    monkeypatch.setattr(screen, "build_game", lambda scenario, seed: (_ for _ in ()).throw(ValueError("broken on purpose")))
    monkeypatch.setattr(screen.simfile, "data_pack_present", lambda: True)
    add_person_and_shelter(app)
    press(app, "PLAY THIS SCENARIO")
    wait_for_game(app)
    assert app.app_state == "builder" and "broken on purpose" in app.builder.message


def test_a_map_that_cannot_load_is_reported_not_fatal(app):
    app.builder.picture, app.builder.picture_surface, app.builder.map_error = None, None, "The map needs the raw terrain data"
    app.draw((0, 0))
    press(app, "add:person")
    on_map(app, *RICHMOND_ON_MAP)
    assert "start_lon" in app.builder.draft.entries[-1]


def play_to_the_end(window):
    window.is_paused = True
    guard = 0
    while not window.show_debrief_modal and guard < 200:
        window.step_forward()
        window.draw((0, 0))
        guard += 1
    assert window.show_debrief_modal


@needs_raw
def test_the_game_runs_what_was_saved_and_the_same_file_plays_the_same(app, tmp_path):
    add_person_and_shelter(app)
    type_into(app, "field:id", "saved_then_played")
    type_into(app, "field:hours", "24")
    press(app, "Save")
    press(app, "PLAY THIS SCENARIO")
    wait_for_game(app)
    assert app.app_state == "sim" and app.max_steps == 12
    play_to_the_end(app)
    played = [(r["action"], r["pos_after"]) for r in app.engine.steps]
    assert len(played) == app.step_idx

    from stranded_physics.runtime.game import build_game

    again = build_game(load_scenario(tmp_path / "saved_then_played.toml"), app.seed).simulation(app.mind_type)
    assert [(r["action"], r["pos_after"]) for r in again.run()["steps"]] == played


@needs_raw
def test_every_screen_draws_with_a_full_eruption_and_several_people(app):
    press(app, "Open")
    press(app, "open:example_village")
    press(app, "PLAY THIS SCENARIO")
    wait_for_game(app)
    assert app.app_state == "sim" and len(app.custom_game.people) == 12
    assert app.mind_type == "quantum" and app.world.vent
    play_to_the_end(app)
    assert app.world.pdc or app.agent.is_alive
    tap(app, pygame.K_ESCAPE, "")
    first = app.custom_game.person
    tap(app, pygame.K_p, "p")
    assert app.custom_game.person != first and app.step_idx == 0
    for _ in range(4):
        tap(app, pygame.K_p, "p")
    assert app.mind_type == "classical_mixture"
    app.step_forward()
    app.show_history_overlay = True
    app.draw((0, 0))
    app.show_history_overlay = False
    tap(app, pygame.K_h, "h")
    assert app.app_state == "builder"


@needs_raw
def test_a_storm_without_an_eruption_plays_in_the_window(app):
    press(app, "Open")
    press(app, "open:beryl_2024")
    press(app, "PLAY THIS SCENARIO")
    wait_for_game(app)
    assert app.app_state == "sim" and app.world.vent is None
    play_to_the_end(app)
    assert "storm" in {r["event"] for r in app.engine.steps}


@needs_raw
def test_leaving_for_the_original_scenarios_puts_them_back(app):
    add_person_and_shelter(app)
    type_into(app, "field:hours", "24")
    press(app, "PLAY THIS SCENARIO")
    wait_for_game(app)
    app.seed = 999
    app.app_state = "event_choice"
    app._handle_event_choice_click(app.btn_choice_volcano.rect.center)
    from engine.gui import DEFAULT_STEPS
    from engine.simulation import SimulationEngine

    assert app.custom_game is None and app.max_steps == DEFAULT_STEPS and isinstance(app.engine, SimulationEngine)
    assert app.seed == 101 and app.mind_type == "quantum" and app.btn_nav_mind.text == "Quantum"


@needs_raw
@pytest.mark.parametrize(
    "entity, message",
    [
        ({"kind": "storm", "source": "replay", "event": "beryl_2024", "site_lon": -61.227, "site_lat": 13.158}, "storm"),
    ],
)
def test_a_recorded_event_outside_the_scenarios_dates_is_refused(entity, message, tmp_path):
    from stranded_physics.core.api import InterfaceError
    from stranded_physics.entities.draft import add_entity, new_draft, to_scenario
    from dataclasses import replace
    from stranded_physics.runtime.game import build_game

    draft = place(add_entity(new_draft(), "person"), 2, (-61.226, 13.317))
    draft = place(add_entity(draft, "shelter"), 3, (-61.267, 13.233))
    draft = set_header(replace(draft, entries=(*draft.entries, entity)), "hours", "24")
    with pytest.raises(InterfaceError, match=message):
        build_game(to_scenario(draft), 1)


def test_opening_a_draft_keeps_from_file_in_step_with_the_screen(app):
    press(app, "Open")
    press(app, "open:beryl_2024")
    assert app.builder.draft == from_file(ROOT / "stranded_physics/scenario_cards/beryl_2024.toml")


def test_every_kind_can_be_added_and_no_button_sits_under_the_footer(app):
    from stranded_physics.entities.kinds import KINDS

    app.draw((0, 0))
    labels = {h.label: h.rect for h in app.builder.hot}
    footer_top = min(rect.top for label, rect in labels.items() if label in ("New", "Open", "Save"))
    for kind in KINDS:
        assert labels[f"add:{kind}"].bottom < footer_top, kind

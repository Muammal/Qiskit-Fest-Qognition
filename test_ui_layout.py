"""Phase 3 UI checks: sharp text, legibility, layout at three window sizes, and the new panels."""

import contracts  # noqa: F401  (must load before mind)
import pygame
import pytest

from engine.debrief import MODEL_FOOTER, control_for, paired_text, run_title
from engine.gui import (
    ACTION_NAMES,
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_PANEL_ALT,
    COLOR_PANEL_BG,
    COLOR_RED,
    COLOR_TEXT_HINT,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_YELLOW,
    CUE_TRANSLATIONS,
    IslandVisualizerApp,
)
from engine.gui_quantum import QuantumPanel, order_swap_delta, swap_last_two
from engine.hidpi import ScaledFont, TextSurface, UICanvas, compose, scale_sprite, window_fit
from engine.agent import SurvivalAgent
from engine.pompeii import EVENT_MAPPINGS as POMPEII_MAPPINGS
from engine.titanic import EVENT_MAPPINGS as TITANIC_MAPPINGS
from engine.waterloo import EVENT_MAPPINGS as WATERLOO_MAPPINGS

WINDOWS = ((1280, 720), (1920, 1080), (2560, 1440))
TEXT_COLORS = (COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_TEXT_HINT, COLOR_GOLD, COLOR_YELLOW, COLOR_CYAN, COLOR_RED)


def make_app(window, scenario="volcano", start="event_choice"):
    app = IslandVisualizerApp(seed=42, mind_type="quantum", start_screen=start, scenario=scenario)
    app.screen = pygame.display.set_mode(window)
    return app


def luminance(color):
    channels = [c / 255 for c in color]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def overlaps(rects):
    found = []
    for i, (text_a, a) in enumerate(rects):
        for text_b, b in rects[i + 1 :]:
            if a.inflate(-2, -2).colliderect(b.inflate(-2, -2)):
                found.append((text_a, text_b))
    return found


# Text and resolution ---------------------------------------------------------


def test_text_colors_read_on_both_panels():
    for color in TEXT_COLORS:
        for background in (COLOR_PANEL_BG, COLOR_PANEL_ALT):
            assert contrast(color, background) >= 4.5, (color, background)


def test_body_text_is_at_least_16px_at_1080p():
    app = make_app((1920, 1080))
    scale = window_fit(1920, 1080)[0]
    assert app.font_body.pixel_size(scale) >= 16


def test_fonts_are_created_at_the_scaled_size():
    pygame.font.init()
    font = ScaledFont("arial", 14)
    surface = font.render("Sharp", True, (0, 0, 0))
    assert isinstance(surface, TextSurface)
    assert font.pixel_size(2.0) == 28
    assert font.hires(surface, 2.0).get_height() > 1.7 * surface.get_height()


def test_integer_sprite_scaling_keeps_hard_edges():
    pygame.display.set_mode((16, 16))
    sprite = pygame.Surface((2, 1))
    sprite.set_at((0, 0), (255, 0, 0))
    sprite.set_at((1, 0), (0, 0, 255))
    big = scale_sprite(sprite, 3)
    assert big.get_size() == (6, 3)
    assert big.get_at((2, 1))[:3] == (255, 0, 0) and big.get_at((3, 1))[:3] == (0, 0, 255)


def test_text_is_recorded_then_rendered_at_final_size():
    pygame.font.init()
    pygame.display.set_mode((16, 16))
    canvas = UICanvas((1600, 900))
    canvas.begin_frame(1.2)
    canvas.blit(ScaledFont("arial", 14).render("Hello", True, (255, 255, 255)), (100, 100))
    assert len(canvas.text_layer) == 1
    target = pygame.Surface((1920, 1080))
    compose(canvas, target)
    assert any(target.get_at((x, y))[:3] != (5, 8, 15) and sum(target.get_at((x, y))[:3]) > 300 for x in range(120, 170) for y in range(120, 145))


def test_a_shape_drawn_over_text_hides_it():
    pygame.font.init()
    canvas = UICanvas((1600, 900))
    canvas.begin_frame(1.5)
    canvas.blit(ScaledFont("arial", 14).render("Under", True, (0, 0, 0)), (100, 100))
    canvas.cover(pygame.Rect(90, 90, 300, 100))
    assert canvas.text_layer == []


def test_screen_text_never_uses_the_recorder_without_text():
    app = make_app((1280, 720))
    app.draw((0, 0))
    assert app.canvas.text_layer
    frame = app.recording_frame()
    assert frame.get_size() == (1600, 900)


# Layout at three sizes -------------------------------------------------------


@pytest.mark.parametrize("window", WINDOWS)
def test_hub_text_has_no_collisions_and_stays_above_buttons(window):
    app = make_app(window)
    app.draw((0, 0))
    scale = window_fit(*window)[0]
    rects = app.canvas.text_rects(scale)
    assert overlaps(rects) == []
    for rect, button in (
        (app.card1_rect, app.btn_choice_island),
        (app.card2_rect, app.btn_choice_volcano),
        (app.card3_rect, app.btn_choice_titanic),
        (app.card4_rect, app.btn_choice_pompeii),
    ):
        top = round(button.rect.y * scale)
        left, right = round(rect.x * scale), round(rect.right * scale)
        card_top = round(rect.y * scale)
        inside = [r for text, r in rects if left <= r.x < right and text != button.text and card_top <= r.y < top]
        assert inside and max(r.bottom for r in inside) <= top
        assert all(r.right <= right for r in inside)


@pytest.mark.parametrize("window", WINDOWS)
@pytest.mark.parametrize("scenario", ["volcano", "titanic", "pompeii", "waterloo"])
def test_config_text_has_no_collisions(window, scenario):
    app = make_app(window, scenario, "home")
    app.draw((0, 0))
    assert overlaps(app.canvas.text_rects(window_fit(*window)[0])) == []


@pytest.mark.parametrize("window", WINDOWS)
def test_section_headings_clear_the_buttons_above_them(window):
    app = make_app(window, "titanic", "home")
    app.draw((0, 0))
    scale = window_fit(*window)[0]
    rects = dict(app.canvas.text_rects(scale))
    heading = rects["2. Select Scenario Preset or Custom Seed"]
    assert heading.top >= round(app.btn_mind_quantum.rect.bottom * scale)
    assert heading.bottom <= round(app.preset_buttons[0].rect.top * scale)


# Cue translation -------------------------------------------------------------


@pytest.mark.parametrize("scenario, mappings", [("titanic", TITANIC_MAPPINGS), ("pompeii", POMPEII_MAPPINGS), ("waterloo", WATERLOO_MAPPINGS)])
def test_each_translation_is_a_real_mapping(scenario, mappings):
    values = [value for _, value, _ in CUE_TRANSLATIONS[scenario]]
    assert set(values) == set(mappings)


@pytest.mark.parametrize("scenario", ["titanic", "pompeii", "waterloo"])
def test_clicking_a_translation_reaches_the_engine(scenario):
    app = make_app((1280, 720), scenario, "home")
    if scenario == "pompeii":
        app.pompeii_settings["population"] = 1_500
    button = app.cue_buttons[1]
    app._handle_home_click(button.rect.center)
    app._init_simulation()
    assert app.engine.event_mapping == button.mapping_value


def test_the_selector_labels_its_choice_an_assumption():
    app = make_app((1920, 1080), "titanic", "home")
    app.draw((0, 0))
    assert any(text.startswith("Assumption:") for text, _ in app.canvas.text_rects(1.2))


# Quantum panel ---------------------------------------------------------------


def test_swap_last_two_ignores_none():
    assert swap_last_two(["none", "tremor", "gas_plume"]) == ["none", "gas_plume", "tremor"]
    assert swap_last_two(["storm", "none", "tremor"]) == ["tremor", "none", "storm"]
    assert swap_last_two(["none", "none", "tremor"]) is None


def test_order_swap_delta_is_the_order_gap():
    from mind.quantum_mind import order_gap_at_lambda

    state = SurvivalAgent().get_state()
    state["recent_events"] = ["none", "tremor", "gas_plume"]
    swapped, delta = order_swap_delta(state)
    assert swapped == ["none", "gas_plume", "tremor"]
    assert delta == pytest.approx(order_gap_at_lambda(dict(state, stress=0.1), "gas_plume", "tremor", 0.0), abs=1e-9)


def test_panel_records_quantum_and_control_on_one_state():
    panel = QuantumPanel()
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["storm", "tremor", "gas_plume"]
    panel.record(state)
    quantum, control = panel.series[-1]
    assert quantum != control and len(panel.path) == 1


def test_swap_button_reports_when_it_cannot_swap():
    panel = QuantumPanel()
    assert panel.swap() == "No cues yet"
    state = SurvivalAgent().get_state()
    panel.record(state)
    assert panel.swap() == "Needs two different cues"


def test_swap_button_click_runs_the_swap():
    app = make_app((1280, 720), "volcano", "sim")
    state = SurvivalAgent().get_state()
    state["recent_events"] = ["none", "tremor", "gas_plume"]
    app.quantum_panel.record(state)
    app._handle_sim_click(app.btn_order_swap.rect.center)
    assert "ΔP" in app.quantum_panel.swap_result


def test_order_swap_button_sits_in_its_widget():
    app = make_app((1280, 720), "volcano", "sim")
    box = pygame.Rect(916 + 16 + 520, 401 + 204, 116, 158)
    assert box.contains(app.btn_order_swap.rect)


# Scenario panels -------------------------------------------------------------


@pytest.mark.parametrize("scenario", ["titanic", "pompeii", "waterloo"])
def test_crowd_panels_have_no_island_vitals_or_actions(scenario):
    app = make_app((1280, 720), scenario, "sim")
    labels = [name for name, _, _ in app._vitals()]
    assert "Hunger" not in labels and "Thirst" not in labels and len(labels) == 6
    names = " ".join(ACTION_NAMES[scenario].values()).lower()
    assert "forage" not in names and "craft" not in names and "shelter" not in names


def test_island_keeps_its_own_vitals():
    app = make_app((1280, 720), "island", "sim")
    assert app._vitals()[0][0] == "Hunger"


def test_no_empty_person_cards():
    from engine.gui_city import thought_text as pompeii_text
    from engine.gui_site import thought_text as waterloo_text
    from engine.citizens import Citizen

    person = Citizen(0, "resident", 0, (5, 5), (5, 5))
    person.recent_events = ["none", "quake", "word_of_mouth"]
    assert "Not yet recorded" not in pompeii_text(person, None) and "quake" in pompeii_text(person, None)

    class Patron:
        status, recent_events = "site", ["none", "none", "smell"]

    assert "smell" in waterloo_text(Patron, None, 0.4) and "0.40 ppm" in waterloo_text(Patron, None, 0.4)


# Debrief ---------------------------------------------------------------------


def test_title_follows_steps_endured():
    assert run_title(True, 5, 36, None, "volcano") == "RUN STOPPED AT 10 h, STILL ALIVE"
    assert run_title(True, 36, 36, None, "volcano") == "SURVIVED THE FULL 72 h"
    assert "PYROCLASTIC FLOW" in run_title(False, 9, 36, "pyroclastic_flow", "volcano")
    assert run_title(True, 6, 48, None, "titanic") == "RUN STOPPED AT 30 min, STILL ALIVE"


def test_no_mission_complete_text_left():
    import inspect
    import engine.gui as gui

    assert "MISSION COMPLETE" not in inspect.getsource(gui)


def test_steps_do_not_queue_mid_run_cutscenes():
    app = make_app((1280, 720), "titanic", "sim")
    for _ in range(14):
        app.step_forward()
    assert not app.cutscene.active


def test_paired_text_compares_the_other_mind():
    assert control_for("quantum") == "classical_mixture" and control_for("classical_mixture") == "quantum"
    assert paired_text(None, None).endswith("computing...")
    text = paired_text(None, dict(mind="classical_mixture", survived=True, steps=36, hide_after_sign=1))
    assert "Mixture control" in text and "hid 1 step after" in text
    text = paired_text(dict(survivors=578, deaths=1630, total=2208), dict(mind="classical_mixture", survivors=536, deaths=1672, total=2208))
    assert "536" in text and "578" in text


@pytest.mark.parametrize("scenario", ["volcano", "titanic"])
def test_debrief_shows_the_footer(scenario):
    app = make_app((1920, 1080), scenario, "sim")
    app.step_forward()
    app.show_debrief_modal = True
    app.draw((0, 0))
    assert MODEL_FOOTER in dict(app.canvas.text_rects(1.2))


# Naming ----------------------------------------------------------------------


def test_window_caption_is_qognition():
    make_app((1280, 720))
    assert pygame.display.get_caption()[0] == "Qognition"

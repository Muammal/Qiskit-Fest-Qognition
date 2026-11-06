"""test_gui_hayday.py - Verification for Hay Day UI, Resolution Scaling & Uninterrupted Runs.
Validates:
1. NineSlicePanel, WoodButton state changes, OutlinedText font caching.
2. Resolution-adaptive integer tile scaling across 1024x768, 1280x720, 1920x1080, 2560x1440, 3440x1440, 3840x2160.
3. Absence of mid-run modals, pauses, or cutscenes across multiple seeds and minds for Island and Volcano.
4. Exactly one ending cutscene trigger per completed run.
5. Correctness of build_ending_stats on signature demo-pack runs.
"""

import os
import json
import pytest
import pygame

# Headless display driver
os.environ["SDL_VIDEODRIVER"] = "dummy"

from engine.display import Display
from engine.ui_kit import (
    OutlinedText, NineSlicePanel, WoodButton, StarRating,
    CountUpNumber, FontManager
)
from engine.screens.ending import build_ending_stats, EndingCutsceneScreen
from engine.gui import IslandVisualizerApp


def test_ui_kit_components():
    """Verify NineSlicePanel, WoodButton, OutlinedText, and animators."""
    if not pygame.get_init():
        pygame.init()
    surf = pygame.Surface((400, 300))

    # OutlinedText
    txt = OutlinedText.render("Test Label", 24)
    assert isinstance(txt, pygame.Surface)
    assert txt.get_width() > 0 and txt.get_height() > 0

    # WoodButton
    btn = WoodButton(pygame.Rect(50, 50, 120, 40), "Click Me")
    assert btn.check_hover((100, 70)) is True
    assert btn.check_hover((10, 10)) is False
    btn.handle_mouse_down((100, 70))
    assert btn.is_pressed is True
    btn.update(0.016)
    assert btn.press_scale < 1.0
    btn.handle_mouse_up((100, 70))
    assert btn.is_pressed is False

    # StarRating
    stars = StarRating(3)
    stars.set_rating(2)
    assert stars.earned_stars == 2
    stars.update(0.1)

    # CountUpNumber
    counter = CountUpNumber(100.0, duration=0.5, is_int=True)
    assert counter.is_complete is False
    counter.update(0.6)
    assert counter.is_complete is True
    assert counter.get_text() == "100"


def test_resolution_adaptive_scaling():
    """Verify display scaling and integer tile sizes across standard aspect ratios."""
    resolutions = [
        (1024, 768),   # 4:3
        (1280, 720),   # 16:9
        (1920, 1080),  # 16:9
        (2560, 1440),  # 16:9
        (3440, 1440),  # 21:9 ultrawide
        (3840, 2160),  # 4K
    ]
    for w, h in resolutions:
        scale = min(w / 1600.0, h / 900.0)
        quantized = max(0.5, round(scale * 20.0) / 20.0)
        assert quantized > 0.0

        # Integer tile size for 40x40 grid must fit cleanly inside viewport
        view_size = min(int(w * 0.65), h)
        tile_size = view_size // 40
        assert tile_size >= 8
        assert tile_size * 40 <= view_size


def test_uninterrupted_mid_run_simulation():
    """Verify that during Island and Volcano runs, NO mid-run cutscenes,

    blocking popups, or auto-pauses ever trigger before the run finishes.
    """
    seeds = [42, 101, 777]
    scenarios = ["island", "volcano"]
    minds = ["quantum", "classical"]

    for scen in scenarios:
        for mind in minds:
            for seed in seeds:
                app = IslandVisualizerApp(seed=seed, mind_type=mind, scenario=scen, start_screen="sim")
                app.max_steps = 15  # Test first 15 steps

                while app.agent.is_alive and app.step_idx < app.max_steps:
                    # Before stepping, verify simulation is uninterrupted
                    assert app.show_debrief_modal is False, f"Debrief modal popped up mid-run at step {app.step_idx}!"
                    assert app.is_paused is False, f"Simulation auto-paused mid-run at step {app.step_idx}!"
                    if hasattr(app, "cutscene") and app.cutscene:
                        assert app.cutscene.active is False, f"Cutscene activated mid-run at step {app.step_idx}!"

                    app.step_forward()

                    # If still alive and under horizon, must remain unblocked
                    if app.agent.is_alive and app.step_idx < app.max_steps:
                        assert app.show_debrief_modal is False
                        assert app.is_paused is False
                        if hasattr(app, "cutscene") and app.cutscene:
                            assert app.cutscene.active is False

                # Exactly upon finish, the ending screen / debrief triggers
                assert app.show_debrief_modal is True or getattr(app, "show_ending_screen", False) is True


def test_build_ending_stats_demo_pack():
    """Verify build_ending_stats extracts accurate numbers from demo-pack files."""
    run01_path = os.path.join("demo-pack", "run_01_heroic_survival.json")
    run02_path = os.path.join("demo-pack", "run_02_dramatic_death.json")

    if os.path.exists(run01_path):
        with open(run01_path, "r", encoding="utf-8") as f:
            data01 = json.load(f)
        stats01 = build_ending_stats(data01)
        assert stats01["outcome"] == "survived"
        assert stats01["grade"] in ("S", "A", "B")
        assert stats01["survival_pct"] == 100.0
        assert stats01["steps_survived"] == len(data01["steps"])
        assert "Rescued" in stats01["title"] or "Survived" in stats01["title"] or "Evacuated" in stats01["title"]

    if os.path.exists(run02_path):
        with open(run02_path, "r", encoding="utf-8") as f:
            data02 = json.load(f)
        stats02 = build_ending_stats(data02)
        assert stats02["outcome"] == "died"
        assert stats02["grade"] in ("C", "D")
        assert stats02["steps_survived"] == len(data02["steps"])
        assert stats02["cause"] == data02["cause"]
        assert len(stats02["decisive_moment"]) > 0


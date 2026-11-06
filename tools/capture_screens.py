"""Saves the screenshots in docs/images/ from the real GUI, without opening a window.

    SDL_VIDEODRIVER=dummy python tools/capture_screens.py [--width 1920 --height 1080] [--out docs/images]
"""
import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

import contracts  # noqa: E402,F401  (must load before mind; see conftest.py)
from engine.gui import IslandVisualizerApp  # noqa: E402
from engine.hidpi import compose  # noqa: E402

SEED = 42
RUN_STEPS = {"island": 8, "volcano": 12, "titanic": 22, "pompeii": 16, "waterloo": 60}


def shot(app, path):
    app.draw((0, 0))
    compose(app.canvas, app.screen)
    pygame.image.save(app.screen, str(path))
    print("wrote", path)


def finish_worker(app):
    worker = app._worker
    if worker is not None:
        worker.join()
        app._pompeii_poll_step()


def advance(app, steps):
    for _ in range(steps):
        app.step_forward()
        finish_worker(app)


def make_app(width, height, scenario, start_screen):
    app = IslandVisualizerApp(seed=SEED, mind_type="quantum", start_screen=start_screen, scenario=scenario)
    app.screen = pygame.display.set_mode((width, height))
    app.window_w, app.window_h = width, height
    app.is_paused = True
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--out", default=str(ROOT / "docs" / "images"))
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, args.only.split(",")))

    if not only or "hub" in only:
        shot(make_app(args.width, args.height, "volcano", "event_choice"), out / "01_event_choice_hub.png")
    if not only or "config" in only:
        shot(make_app(args.width, args.height, "volcano", "home"), out / "02_home_configuration.png")
        shot(make_app(args.width, args.height, "titanic", "home"), out / "02b_titanic_configuration.png")

    names = dict(island="03_island_survival_sim.png", volcano="04_volcano_evacuation_sim.png", titanic="06_titanic_evacuation_sim.png",
                 pompeii="07_pompeii_evacuation_sim.png", waterloo="08_waterloo_chlorine_sim.png")
    for scenario, name in names.items():
        if only and scenario not in only:
            continue
        app = make_app(args.width, args.height, scenario, "sim")
        if scenario == "pompeii":
            app.pompeii_settings.update(population=1500)
            app._init_simulation()
        advance(app, RUN_STEPS[scenario])
        app.show_debrief_modal = False
        if scenario == "waterloo":
            app.waterloo_panels = True
        shot(app, out / name)

    if not only or "debrief" in only:
        app = make_app(args.width, args.height, "volcano", "sim")
        advance(app, 36)
        app.show_debrief_modal = True
        app.draw((0, 0))
        if app.paired.thread is not None:
            app.paired.thread.join()
        shot(app, out / "05_mission_debrief.png")
    if "debrief_titanic" in only:
        app = make_app(args.width, args.height, "titanic", "sim")
        advance(app, 48)
        app.show_debrief_modal = True
        app.draw((0, 0))
        app.paired.thread.join()
        shot(app, out / "05b_titanic_debrief.png")


if __name__ == "__main__":
    main()

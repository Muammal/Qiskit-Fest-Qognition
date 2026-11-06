"""The in-game scenario builder. It draws a Draft and turns clicks into Draft changes. Every rule lives in entities/draft.py. main.py hands this to the game window, because engine/ never imports the physics engine."""
from __future__ import annotations

import re
import threading
import time
import webbrowser
from pathlib import Path
from typing import Callable, NamedTuple

import pygame

from engine.gui import (
    COLOR_BG, COLOR_BLUE, COLOR_CARD_BORDER, COLOR_CYAN, COLOR_GOLD, COLOR_GREEN, COLOR_GREEN_DARK, COLOR_ORANGE, COLOR_PANEL_ALT, COLOR_PANEL_BG, COLOR_PURPLE,
    COLOR_RED, COLOR_TEXT_HINT, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, WINDOW_HEIGHT, WINDOW_WIDTH, wrap_text,
)
from stranded_physics import check
from stranded_physics.core.api import InterfaceError
from stranded_physics.entities import draft as edit
from stranded_physics.entities import simfile
from stranded_physics.entities.api import MINDS, PLACES, RESOURCES, SOURCES
from stranded_physics.entities.api import EntitySpec
from stranded_physics.entities.kinds import ERUPTION_EVENTS, KINDS, NOT_BUILT, terrain_domain
from stranded_physics.runtime.game import SEA, build_game, lonlat_to_map, map_to_lonlat, terrain_picture

KIND_TEXT = {"terrain": "The land", "weather": "Wind, rain, temperature", "eruption": "Timeline, column, mass", "ash": "Fallout from an eruption",
             "flow": "Hot flows from an eruption", "mudflow": "Rain on ash", "gas": "SO2 downwind", "lava": "A growing dome", "storm": "Wind from a cyclone", "person": "A body and a mind",
             "group": "Many people, one mind", "shelter": "Somewhere to evacuate to", "resource": "Food, water or wood",
             "ship": "Hull and compartments", "breach": "Where it's holed", "lifeboats": "Seats, launch times", "sea": "Water temperature", "passengers": "People aboard"}
KIND_GROUPS = (("WORLD", ("terrain", "weather")), ("HAZARDS", ("eruption", "ash", "flow", "mudflow", "gas", "lava", "storm")),
               ("AT SEA", ("ship", "breach", "lifeboats", "sea", "passengers")), ("PEOPLE AND PLACES", ("person", "group", "shelter", "resource")))
KIND_COLORS = {"person": COLOR_PURPLE, "group": COLOR_PURPLE, "shelter": COLOR_GREEN, "resource": COLOR_CYAN, "storm": COLOR_BLUE}
MODEL_KINDS = ("ash", "flow", "mudflow", "gas", "lava")
BUILT_IN = "Built-in model"
SOURCE_TEXT = {"replay": "Real record", "catalogue": "Sampled from records", "dials": "Set by hand"}
MIND_TEXT = {"quantum": "Quantum", "classical_mixture": "Control", "classical": "Classical"}
WHAT_TEXT = {"water": "Water", "food": "Food", "wood": "Wood"}
ROW_H, VISIBLE_ROWS = 32, 8
OPEN_ROWS = 12
DETAIL_BOTTOM = 824
CHOICES_PER_ROW = 3
MAP_RECT = pygame.Rect(286, 112, 520, 520)
MAP_KM = 20.
PIN_REACH_PX = 10
LONLAT_STEP = .005  # About 500 m, one tile of the game's map.
STEPS_ACROSS_RANGE = 40
ON_LAND_KINDS = ("person", "group", "shelter", "resource")
EDIT_LIMIT = 300
UNDO_LIMIT = 100
SHADE = (214, 192, 150)
FIELD_BG = (255, 250, 236)


def kind_is_model(entry, source: str) -> bool:
    """Ash, flows and the like have one source, which is a model and not a record of anything."""
    return source == "replay" and entry["kind"] in MODEL_KINDS


class Hot(NamedTuple):
    rect: pygame.Rect
    action: Callable[[], None]
    label: str


class BuilderScreen:
    def __init__(self, app, save_folder: Path = edit.SAVED, start_open: bool = False, sim_folder: Path = simfile.EXPORTS) -> None:
        self.app, self.canvas = app, app.canvas
        self.sim_folder = Path(sim_folder)
        self.guided, self.start_open = start_open, start_open  # Guided hides what most people never need. Advanced shows it all.
        self.undo_stack: list[edit.Draft] = []
        self.share_open = False
        self.author, self.description = "", ""
        self.sim_note = ""
        self.link = ""
        self.gallery: list[dict] | None = None
        self.net_thread: threading.Thread | None = None
        self.net_result: object = None
        self.save_folder = Path(save_folder)
        self.draft = edit.new_draft()
        self.clean = self.draft  # The draft as last opened or saved, to warn before discarding changes.
        self.selected: int | None = None
        self.scroll = 0
        self.editing: tuple[str, str, Callable[[str], edit.Draft]] | None = None
        self.message, self.message_bad = "", False
        self.armed, self.was_armed = "", ""
        self.open_rows: list[tuple[Path, str]] | None = None
        self.open_scroll = 0
        self.seed = app.seed
        self.builder_thread: threading.Thread | None = None
        self.build_result: object = None
        self.build_started = 0.
        self.hot: list[Hot] = []
        self.click_pos = (0, 0)
        self.mouse = (0, 0)
        self._seen: edit.Draft | None = None
        self.problem: str | None = None
        self.pins: list[tuple[int, int, int]] = []
        self.claims: list[tuple[str, tuple[int, int, int]]] = []
        self._claims_for: tuple | None = None
        self.picture = None
        self.picture_surface: pygame.Surface | None = None
        self.map_error = ""
        self.picture_for = None
        self._refresh_picture()

    # ---- Background work ----
    def _picture_key(self) -> tuple:
        """What the map shows depends on the land entity, and on the seed when that land is generated."""
        land = edit.terrain_entry(self.draft)
        if land is None or land["source"] == "replay":
            return ("replay",)
        return (land["source"], land.get("summit_m"), land.get("area_km2"), self.seed)

    def _refresh_picture(self) -> None:
        key = self._picture_key()
        if key == self.picture_for:
            return
        self.picture_for, self.picture, self.picture_surface, self.map_error = key, None, None, ""
        threading.Thread(target=self._load_picture, args=(key,), daemon=True).start()

    def _load_picture(self, key: tuple) -> None:
        try:
            land = edit.terrain_entry(self.draft)
            domain = None
            if land is not None and land["source"] != "replay":
                domain = terrain_domain(EntitySpec("terrain", str(land["source"]), settings={k: float(land[k]) for k in ("summit_m", "area_km2") if k in land}), self.seed)
            picture = terrain_picture(domain=domain, seed=self.seed)
            if key == self.picture_for:  # A newer choice replaces a slower, older one.
                self.picture = picture
        except Exception as error:  # A window must report this, not crash: teammates may not hold the raw data.
            self.map_error = f"The map needs the raw terrain data, which this copy doesn't hold ({type(error).__name__}). You can still type positions."

    def _build(self, scenario, seed: int) -> None:
        try:
            self.build_result = build_game(scenario, seed)
        except FileNotFoundError as error:
            self.build_result = InterfaceError(f"This copy doesn't hold the raw data it needs: {error}")
        except Exception as error:  # Shown on screen. Anything else here would kill the thread silently.
            self.build_result = InterfaceError(simfile.DATA_PACK_HELP) if simfile.needs_data_pack(scenario) and not simfile.data_pack_present() else error

    def _poll_build(self) -> None:
        if self.builder_thread is None or self.builder_thread.is_alive():
            return
        result, self.builder_thread, self.build_result = self.build_result, None, None
        if isinstance(result, Exception):
            self._say(f"Couldn't build it: {result}", bad=True)
        else:
            self.app.start_custom_game(result)

    def _in_background(self, work: Callable[[], object], finish: Callable[[object], None]) -> None:
        """Network work on a thread, so the window keeps drawing. `finish` runs on the window's thread."""
        def run() -> None:
            try:
                self.net_result = work()
            except InterfaceError as error:
                self.net_result = error
        self.net_finish = finish
        self.net_thread = threading.Thread(target=run, daemon=True)
        self.net_thread.start()
        self._say("Connecting...")

    def _poll_network(self) -> None:
        if self.net_thread is None or self.net_thread.is_alive():
            return
        result, self.net_thread, self.net_result = self.net_result, None, None
        if isinstance(result, InterfaceError):
            self._say(str(result), bad=True)
        else:
            self._say("")
            self.net_finish(result)

    @property
    def building(self) -> bool:
        return self.builder_thread is not None

    # ---- Changing the draft ----
    def _say(self, text: str, bad: bool = False) -> None:
        self.message, self.message_bad = text, bad

    def _remember(self) -> None:
        self.undo_stack = [*self.undo_stack[-(UNDO_LIMIT - 1):], self.draft]

    def _undo(self) -> None:
        if not self.undo_stack:
            self._say("Nothing to undo.")
            return
        self.draft, self.undo_stack = self.undo_stack[-1], self.undo_stack[:-1]
        self.selected = None
        self._say("Undone.")

    def _apply(self, change: Callable[[], edit.Draft]) -> bool:
        before = self.draft
        try:
            self.draft = change()
        except InterfaceError as error:
            self._say(f"Refused: {error}", bad=True)
            return False
        if self.draft is not before:
            self.undo_stack = [*self.undo_stack[-(UNDO_LIMIT - 1):], before]
        self._say("")
        return True

    def _add(self, kind: str) -> None:
        self._remember()
        self.draft = edit.add_portable(self.draft, kind) if self.guided else edit.add_entity(self.draft, kind)
        self.selected = len(self.draft.entries) - 1
        self.scroll = max(0, len(self.draft.entries) - VISIBLE_ROWS)
        needs_placing = any(dial.unit == "degree" for dial in edit.dials_of(self.draft.entries[self.selected]))
        self._say(f"Click the map to place this {kind}." if needs_placing else "")

    def _add_step(self, kinds: tuple[str, ...]) -> None:
        """A checklist step, which may need several kinds. The one that needs placing is selected last."""
        present = {entry["kind"] for entry in self.draft.entries}
        for kind in reversed([kind for kind in kinds if kind not in present]):
            self._add(kind)

    def _remove(self, index: int) -> None:
        self._remember()
        self.draft = edit.remove_entity(self.draft, index)
        self.selected = None
        self.scroll = max(0, min(self.scroll, len(self.draft.entries) - VISIBLE_ROWS))

    def _click_map(self) -> None:
        x, y = self.click_pos
        for index, pin_x, pin_y in self.pins:
            if index != self.selected and abs(pin_x - x) <= PIN_REACH_PX and abs(pin_y - y) <= PIN_REACH_PX:
                self.selected = index
                return
        if self.selected is None or not any(dial.unit == "degree" for dial in edit.dials_of(self.draft.entries[self.selected])):
            self._say("Select something that has a position first, then click the map.")
            return
        fraction = (x - MAP_RECT.x) / MAP_RECT.width, (y - MAP_RECT.y) / MAP_RECT.height
        if self.draft.entries[self.selected]["kind"] in ON_LAND_KINDS and self._is_sea(*fraction):
            self._say("That's the sea. Click on the land.", bad=True)
            return
        lonlat = map_to_lonlat(*fraction)
        self._apply(lambda: edit.place(self.draft, self.selected, lonlat))

    def _is_sea(self, fraction_x: float, fraction_y: float) -> bool:
        if self.picture is None:
            return False
        height, width = self.picture.shape[:2]
        return tuple(self.picture[min(height - 1, int(fraction_y * height)), min(width - 1, int(fraction_x * width))]) == SEA

    def _set_seed(self, text: str) -> edit.Draft:
        if not (text.isascii() and text.isdigit()):
            raise InterfaceError(f"The seed has to be a whole number, not {text!r}")
        self.seed = int(text)
        return self.draft

    def _step_dial(self, index: int, dial, sign: int) -> None:
        value = self.draft.entries[index].get(dial.name)
        if value is None:
            self._say("Click the map to place it first.")
            return
        step = LONLAT_STEP if dial.unit == "degree" else 1 if dial.whole else (dial.high - dial.low) / STEPS_ACROSS_RANGE
        self._apply(lambda: edit.set_dial(self.draft, index, dial.name, repr(round(value + sign * step, 6))))

    def _guarded(self, name: str, action: Callable[[], None]) -> None:
        """Asks for a second click before discarding unsaved changes."""
        if self.draft is self.clean or self.was_armed == name:
            action()
        else:
            self.armed = name
            self._say(f"You have unsaved changes. Click {name} again to discard them.", bad=True)

    def _new(self) -> None:
        if self.guided:
            self.start_open = True
            return
        self.draft = self.clean = edit.new_draft()
        self.selected, self.scroll = None, 0
        self._say("")

    def _start_from(self, name: str) -> None:
        self.draft = self.clean = edit.template_draft(name)
        self.selected, self.scroll, self.start_open, self.undo_stack, self.sim_note = None, 0, False, [], ""
        self._say("")

    # ---- Sim files ----
    def _take_sim(self, sim: simfile.Sim, origin: str) -> None:
        self.draft = self.clean = sim.draft
        self.seed, self.selected, self.scroll, self.undo_stack = sim.seed, None, 0, []
        self.start_open, self.open_rows, self.gallery = False, None, None
        self.author, self.description = sim.author, sim.description
        self.sim_note = f"\"{sim.title}\" by {sim.author or 'someone anonymous'}, from {origin}. Nobody has checked it. Treat it as a model, not as advice."
        self._say(simfile.DATA_PACK_HELP, bad=True) if sim.needs_data_pack and not simfile.data_pack_present() else self._say("Opened. Press PLAY to run it.")

    def open_source(self, source: str) -> None:
        """A sim from a path or a link, from dropping a file on the window, the Open box, or --open."""
        source = str(source).strip()
        if source.lower().startswith(("https://", "http://")):
            self._in_background(lambda: simfile.fetch_sim(source), lambda sim: self._take_sim(sim, "a link"))
            return
        try:
            self._take_sim(simfile.read_path(Path(source)), Path(source).name)
        except InterfaceError as error:
            self.start_open = False
            self._say(str(error), bad=True)

    def _open_gallery(self) -> None:
        self._in_background(simfile.fetch_gallery, lambda rows: setattr(self, "gallery", rows))

    def _open_gallery_row(self, row: dict) -> None:
        self._in_background(lambda: simfile.fetch_gallery_sim(row), lambda sim: self._take_sim(sim, "the community gallery"))

    def _set_link(self, text: str) -> edit.Draft:
        self.link = text
        return self.draft

    def _set_author(self, text: str) -> edit.Draft:
        self.author = text
        return self.draft

    def _set_description(self, text: str) -> edit.Draft:
        self.description = text
        return self.draft

    def _export(self) -> Path | None:
        try:
            path = simfile.export_sim(self.draft, self.seed, self.author, self.description, self.sim_folder)
        except (InterfaceError, OSError) as error:
            self._say(f"Not exported: {error}", bad=True)
            return None
        self._say(f"Saved {path}. Send that file to anyone with the app.")
        return path

    def _publish(self) -> None:
        """Nothing is uploaded from here. The person sees GitHub's own page and chooses to submit."""
        if self.was_armed != "Publish":
            self.armed = "Publish"
            self._say("Your file, title, name and description will be public, for anyone to download. Click Publish online again to go ahead.", bad=True)
            return
        path = self._export()
        if path is not None:
            webbrowser.open(simfile.UPLOAD_PAGE)
            self._say(f"Opened GitHub in your browser. Drop {path} on that page, then submit it. It goes live once it is reviewed.")

    def _list_files(self) -> None:
        rows = []
        for path in edit.saved_scenarios(self.save_folder):
            try:
                rows.append((path, str(edit.from_file(path).header["title"])))
            except InterfaceError:
                rows.append((path, "(can't be read)"))
        for path in sorted(self.sim_folder.glob(f"*{simfile.SUFFIX}")):
            try:
                rows.append((path, simfile.read_path(path).title))
            except InterfaceError:
                rows.append((path, "(can't be read)"))
        self.open_rows, self.open_scroll, self.gallery = rows, 0, None

    def _open(self, path: Path) -> None:
        if path.suffix == simfile.SUFFIX:
            self.open_source(str(path))
            return
        self.open_rows = None
        try:
            self.draft = self.clean = edit.from_file(path)
        except InterfaceError as error:
            self._say(str(error), bad=True)
            return
        self.selected, self.scroll = None, 0
        self._say(f"Opened {path.name}.")

    def _save(self) -> None:
        try:
            path = edit.save_draft(self.draft, self.save_folder)
        except (InterfaceError, OSError) as error:
            self._say(f"Not saved: {error}", bad=True)
            return
        self.clean = self.draft
        self._say(f"Saved as {path.name}. It reloads as the identical file.")

    def _play(self) -> None:
        if self.problem:
            self._say("Fix the problem below before playing.", bad=True)
            return
        scenario = edit.to_scenario(self.draft)
        if simfile.needs_data_pack(scenario) and not simfile.data_pack_present():
            self._say(simfile.DATA_PACK_HELP, bad=True)
            return
        self.build_result, self.build_started = None, time.time()
        self.builder_thread = threading.Thread(target=self._build, args=(scenario, self.seed), daemon=True)
        self.builder_thread.start()

    def _back(self) -> None:
        self.app.app_state = "event_choice"

    # ---- Input ----
    def hover(self, pos: tuple[int, int]) -> bool:
        return any(hot.rect.collidepoint(pos) for hot in self.hot)

    def handle_event(self, event, pos: tuple[int, int]) -> None:
        if self.building:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._click(pos)
        elif event.type == pygame.MOUSEWHEEL and self.gallery is not None:
            self.open_scroll = max(0, min(max(0, len(self.gallery) - OPEN_ROWS), self.open_scroll - event.y))
        elif event.type == pygame.MOUSEWHEEL and self.open_rows is not None:
            self.open_scroll = max(0, min(max(0, len(self.open_rows) - OPEN_ROWS), self.open_scroll - event.y))
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max(0, len(self.draft.entries) - VISIBLE_ROWS), self.scroll - event.y))
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _click(self, pos: tuple[int, int]) -> None:
        if self.editing:
            self._finish_edit()
        self.click_pos = pos
        self.was_armed, self.armed = self.armed, ""
        for hot in reversed(self.hot):
            if hot.rect.collidepoint(pos):
                hot.action()
                return

    def _finish_edit(self) -> None:
        _, text, commit = self.editing
        self.editing = None
        self._apply(lambda: commit(text))

    @staticmethod
    def _clipboard() -> str:
        try:
            return (pygame.scrap.get_text() or "").strip()
        except (pygame.error, AttributeError, NotImplementedError):
            return ""

    def _key(self, event) -> None:
        if self.editing:
            key, text, commit = self.editing
            if event.key == pygame.K_v and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                self.editing = (key, (text + self._clipboard())[:EDIT_LIMIT], commit)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self._finish_edit()
            elif event.key == pygame.K_ESCAPE:
                self.editing = None
            elif event.key == pygame.K_BACKSPACE:
                self.editing = (key, text[:-1], commit)
            elif event.unicode and event.unicode.isprintable() and len(text) < EDIT_LIMIT:
                self.editing = (key, text + event.unicode, commit)
        elif event.key == pygame.K_z and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
            self._undo()
        elif event.key == pygame.K_ESCAPE:
            if self.share_open:
                self.share_open = False
            elif self.gallery is not None:
                self.gallery = None
            elif self.open_rows is not None:
                self.open_rows = None
            elif self.start_open:
                self.start_open = False
            else:
                self._back()

    # ---- Small drawing pieces ----
    def _text(self, text: str, x: int, y: int, font=None, color=COLOR_TEXT_MAIN) -> None:
        self.canvas.blit((font or self.app.font_body).render(text, True, color), (x, y))

    def _fit(self, text: str, font, width: int) -> str:
        if font.size(text)[0] <= width:
            return text
        while text and font.size(text + "...")[0] > width:
            text = text[:-1]
        return text + "..."

    def _button(self, rect, label: str, action: Callable[[], None], active: bool = False, enabled: bool = True, color=COLOR_PANEL_ALT, ink=COLOR_TEXT_MAIN, font=None) -> None:
        rect = pygame.Rect(rect)
        font = font or self.app.font_sub
        if enabled:
            self.hot.append(Hot(rect, action, label))
        fill = COLOR_GOLD if active else SHADE if enabled and rect.collidepoint(self.mouse) and color == COLOR_PANEL_ALT else color
        ink = COLOR_PANEL_BG if active else ink if enabled else COLOR_TEXT_HINT
        pygame.draw.rect(self.canvas, fill, rect, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER if enabled else COLOR_TEXT_HINT, rect, 1, border_radius=6)
        shown = font.render(self._fit(label, font, rect.width - 10), True, ink)
        self.canvas.blit(shown, shown.get_rect(center=rect.center))

    def _field(self, rect, key: str, value: object, commit: Callable[[str], edit.Draft], empty: str = "") -> None:
        rect = pygame.Rect(rect)
        now_editing = bool(self.editing) and self.editing[0] == key
        text = self.editing[1] + "|" if now_editing else str(value) if value not in (None, "") else empty
        font = self.app.font_body
        pygame.draw.rect(self.canvas, FIELD_BG, rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_GOLD if now_editing else COLOR_CARD_BORDER, rect, 2 if now_editing else 1, border_radius=4)
        ink = COLOR_TEXT_MAIN if now_editing or value not in (None, "") else COLOR_TEXT_HINT
        shown = font.render(self._fit(text, font, rect.width - 12), True, ink)
        self.canvas.blit(shown, shown.get_rect(midleft=(rect.x + 6, rect.centery)))
        self.hot.append(Hot(rect, lambda: self._begin_edit(key, value, commit), f"field:{key}"))

    def _begin_edit(self, key: str, value: object, commit: Callable[[str], edit.Draft]) -> None:
        self.editing = (key, "" if value is None else str(value), commit)

    def _wrapped(self, text: str, x: int, y: int, width: int, color, lines: int) -> int:
        font = self.app.font_body
        for line in wrap_text(text, font, width)[:lines]:
            self._text(line, x, y, font, color)
            y += font.get_linesize()
        return y

    # ---- Keeping derived facts current ----
    def _refresh(self) -> None:
        if self._seen is self.draft:
            return
        self._seen = self.draft
        self.problem = edit.problem(self.draft)
        self.pins = []
        for index, entry in enumerate(self.draft.entries):
            position = edit.position(entry)
            if position:
                fx, fy = lonlat_to_map(position)
                if 0 <= fx <= 1 and 0 <= fy <= 1:
                    self.pins.append((index, MAP_RECT.x + int(fx * MAP_RECT.width), MAP_RECT.y + int(fy * MAP_RECT.height)))
        self._refresh_claims()

    def _refresh_claims(self) -> None:
        """What the checker says this scenario can claim. Evidence belongs to a scenario's id, and never carries over."""
        try:
            scenario = edit.to_scenario(self.draft)
        except InterfaceError:
            self.claims = []
            return
        if edit.borrows_evidence(self.draft):
            self._claims_for = None
            self.claims = [("Result: none yet.", COLOR_TEXT_MAIN), (f"{scenario.id} is a shipped scenario, and this has been changed from it. Its results don't apply here. Give this a new id.", COLOR_RED)]
            return
        wanted = (scenario.id, scenario.place, scenario.uses())
        if wanted == self._claims_for:
            return
        self._claims_for = wanted
        parts = [check.assess(category, scenario.id) for category in scenario.uses()]
        agrees, disagrees = sum(len(p.agrees) for p in parts), sum(len(p.disagrees) for p in parts)
        self.claims = [(f"Result: {check.overall(parts)}", COLOR_TEXT_MAIN)]
        waiting = [part.category for part in parts if part.verification != "PASS"]
        if waiting:
            self.claims.append((f"Own tests not all passing yet: {', '.join(waiting)}.", COLOR_RED))
        self.claims.append((f"Blind checks under this id: {agrees} agree with reality, {disagrees} disagree.", COLOR_TEXT_MUTED))
        if not agrees and not disagrees:
            self.claims.append(("Nothing here has been compared with reality under this id.", COLOR_TEXT_MUTED))
        if scenario.place == "fictional":
            self.claims.append(("This place is fictional, so no result can be compared with reality.", COLOR_TEXT_MUTED))

    # ---- The screen ----
    def draw(self, mouse: tuple[int, int]) -> None:
        self._poll_build()
        self._poll_network()
        if self.app.app_state != "builder":
            return
        self.mouse, self.hot = mouse, []
        self._refresh()
        self.canvas.fill(COLOR_BG)
        self._draw_header()
        self._draw_palette()
        self._draw_map()
        self._draw_status()
        self._draw_list()
        self._draw_detail()
        self._draw_footer()
        if self.start_open:
            self._draw_start()
        if self.open_rows is not None:
            self._draw_open_list()
        if self.share_open:
            self._draw_share()
        if self.building:
            self._draw_building()

    def _draw_header(self) -> None:
        self.app.draw_card(12, 12, WINDOW_WIDTH - 24, 62)
        self._button((24, 26, 80, 34), "< Menu", self._back)
        header = self.draft.header
        if self.guided:
            self._text("Name your scenario", 118, 18, self.app.font_small, COLOR_TEXT_MUTED)
            self._field((118, 36, 560, 30), "title", header["title"], lambda text: edit.set_title(self.draft, text))
            self._text("Hours", 696, 18, self.app.font_small, COLOR_TEXT_MUTED)
            self._field((696, 36, 80, 30), "hours", header["hours"], lambda text: edit.set_header(self.draft, "hours", text))
            self._button((1420, 26, 150, 34), "Advanced", lambda: setattr(self, "guided", False))
            return
        fields = (("Title", "title", 118, 380), ("Id (results belong to this)", "id", 510, 200), ("Start, with timezone", "start_utc", 834, 260), ("Hours", "hours", 1106, 70), ("UTC offset", "local_utc_offset", 1188, 70))
        for label, key, x, width in fields:
            self._text(label, x, 18, self.app.font_small, COLOR_TEXT_MUTED)
            self._field((x, 36, width, 30), key, header[key], lambda text, k=key: edit.set_header(self.draft, k, text))
        self._text("Place", 722, 18, self.app.font_small, COLOR_TEXT_MUTED)
        following = PLACES[(PLACES.index(header["place"]) + 1) % len(PLACES)]
        self._button((722, 36, 100, 30), str(header["place"]).capitalize(), lambda: self._apply(lambda: edit.set_header(self.draft, "place", following)))
        self._text(f"{header['step_hours']} h steps" if "step_hours" in header else f"{header['step_minutes']} min steps", 1272, 42, self.app.font_small, COLOR_TEXT_MUTED)
        self._text(f"{int(header['hours']) * 60 // (int(header['step_hours']) * 60 if 'step_hours' in header else int(header['step_minutes']))} steps", 1272, 24, self.app.font_small, COLOR_TEXT_MUTED)
        self._button((1490, 26, 84, 34), "Simple", lambda: setattr(self, "guided", True))

    def _draw_palette(self) -> None:
        self.app.draw_card(12, 84, 250, 744)
        self._text("ADD TO THE SCENARIO", 26, 96, self.app.font_sub, COLOR_GOLD)
        y = 122
        for group, kinds in KIND_GROUPS:
            if self.guided and group == "AT SEA":
                continue
            self._text(group, 26, y, self.app.font_small, COLOR_TEXT_HINT)
            y += 18
            for kind in kinds:
                rect = pygame.Rect(24, y, 226, 28)
                self._button(rect, "", lambda k=kind: self._add(k))
                self.hot[-1] = Hot(rect, self.hot[-1].action, f"add:{kind}")
                self._text(f"+ {kind.capitalize()}", rect.x + 6, rect.y + 5, self.app.font_small)
                self._text(self._fit(KIND_TEXT[kind], self.app.font_small, 128), rect.x + 88, rect.y + 6, self.app.font_small, COLOR_TEXT_MUTED)
                y += 31
            y += 4

    def _draw_map(self) -> None:
        self.app.draw_card(274, 84, 544, 560)
        land = edit.terrain_entry(self.draft)
        where = "LA SOUFRIERE" if land is None or land["source"] == "replay" else "YOUR ISLAND"
        self._text(f"MAP: 20 KM AROUND {where}. CLICK TO PLACE WHAT'S SELECTED.", 288, 94, self.app.font_small, COLOR_GOLD)
        self._refresh_picture()
        if self.picture_surface is None and self.picture is not None:
            flipped = pygame.surfarray.make_surface(self.picture.swapaxes(0, 1))
            self.picture_surface = pygame.transform.smoothscale(flipped, MAP_RECT.size)
        if self.picture_surface is not None:
            self.canvas.blit(self.picture_surface, MAP_RECT)
        else:
            pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, MAP_RECT)
            self._wrapped(self.map_error or "Loading the island...", MAP_RECT.x + 30, MAP_RECT.y + 240, MAP_RECT.width - 60, COLOR_TEXT_MUTED, 4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, MAP_RECT, 2)
        self.hot.append(Hot(MAP_RECT, self._click_map, "map"))
        self._draw_vents()
        self._draw_pins()

    def _draw_vents(self) -> None:
        for entry in self.draft.entries:
            if entry["kind"] == "eruption" and entry.get("event") in ERUPTION_EVENTS:
                fx, fy = lonlat_to_map(ERUPTION_EVENTS[entry["event"]])
                centre = (MAP_RECT.x + int(fx * MAP_RECT.width), MAP_RECT.y + int(fy * MAP_RECT.height))
                pygame.draw.circle(self.canvas, COLOR_RED, centre, 7)
                pygame.draw.circle(self.canvas, COLOR_PANEL_BG, centre, 7, 2)

    def _draw_pins(self) -> None:
        for index, x, y in self.pins:
            entry = self.draft.entries[index]
            color = KIND_COLORS.get(str(entry["kind"]), COLOR_ORANGE)
            if entry["kind"] == "group":
                radius = int(float(entry.get("radius_km", 0.)) / MAP_KM * MAP_RECT.width)
                if radius > 1:
                    pygame.draw.circle(self.canvas, color, (x, y), radius, 1)
            if index == self.selected:
                pygame.draw.circle(self.canvas, COLOR_GOLD, (x, y), 10, 3)
            pygame.draw.circle(self.canvas, color, (x, y), 6)
            pygame.draw.circle(self.canvas, COLOR_PANEL_BG, (x, y), 6, 1)
            self._text(str(index + 1), x + 9, y - 8, self.app.font_small, COLOR_PANEL_BG)

    def _draw_status(self) -> None:
        self.app.draw_card(274, 652, 544, 176)
        x, width = 288, 516
        y = 660
        if self.guided:
            y = self._draw_steps(x, y)
        if self.message:
            y = self._wrapped(self.message, x, y, width, COLOR_RED if self.message_bad else COLOR_BLUE, 2)
        if self.sim_note and not self.message:
            y = self._wrapped(self.sim_note, x, y, width, COLOR_TEXT_MUTED, 2)
        if self.problem:
            y = self._wrapped(f"Fix next: {self._plain_problem(self.problem)}", x, y, width, COLOR_RED, 2)
        else:
            y = self._wrapped("Ready: this scenario can be built.", x, y, width, COLOR_GREEN_DARK, 1)
        y += 4
        self._text("WHAT IT CAN HONESTLY CLAIM", x, y, self.app.font_small, COLOR_GOLD)
        y += 16
        for line, color in self.claims:
            if y > DETAIL_BOTTOM - 22:
                break
            y = self._wrapped(line, x, y, width, color, 2)

    @staticmethod
    def _plain_problem(text: str) -> str:
        """The engine's message, with the commonest one in everyday words."""
        match = re.fullmatch(r"(\w+): unknown settings \[\], missing settings \[.*(?:lon|lat).*\]", text)
        return f"click the map to place the {match[1]}." if match else text

    def _draw_steps(self, x: int, y: int) -> int:
        """The checklist: what's done, and one click to add what isn't."""
        for number, (label, done, kinds) in enumerate(edit.next_steps(self.draft)):
            rect = (x + number * 104, y, 98, 26)
            self._button(rect, f"{'OK' if done else '+'} {label}", (lambda: None) if done else (lambda k=kinds: self._add_step(k)), active=done, font=self.app.font_small)
            self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"step:{label}")
        return y + 32

    @staticmethod
    def _source_text(entry) -> str:
        return BUILT_IN if kind_is_model(entry, str(entry["source"])) else SOURCE_TEXT[str(entry["source"])]

    def _entry_summary(self, entry) -> str:
        kind = str(entry["kind"])
        name = f" \"{entry['name']}\"" if entry.get("name") else ""
        count = entry.get("count")
        detail = {"person": MIND_TEXT.get(str(entry.get("mind")), ""), "group": f"{count} {'person' if count == 1 else 'people'}, {MIND_TEXT.get(str(entry.get('mind')), '')}",
                  "resource": WHAT_TEXT.get(str(entry.get("what")), "")}.get(kind, str(entry.get("event") or ""))
        return f"{kind.capitalize()}{name}" + (f": {detail}" if detail else "")

    def _draw_list(self) -> None:
        self.app.draw_card(830, 84, 758, 300)
        entries = self.draft.entries
        self._text(f"IN THIS SCENARIO ({len(entries)})", 844, 94, self.app.font_sub, COLOR_GOLD)
        if len(entries) > VISIBLE_ROWS:
            self._text(f"Scroll to see more: showing {self.scroll + 1} to {min(len(entries), self.scroll + VISIBLE_ROWS)}", 1250, 96, self.app.font_small, COLOR_TEXT_MUTED)
        for row, index in enumerate(range(self.scroll, min(len(entries), self.scroll + VISIBLE_ROWS))):
            self._draw_row(index, 120 + row * ROW_H)

    def _draw_row(self, index: int, y: int) -> None:
        entry = self.draft.entries[index]
        rect = pygame.Rect(842, y, 734, ROW_H - 4)
        chosen = index == self.selected
        pygame.draw.rect(self.canvas, SHADE if chosen or rect.collidepoint(self.mouse) else COLOR_PANEL_ALT, rect, border_radius=4)
        if chosen:
            pygame.draw.rect(self.canvas, COLOR_GOLD, rect, 2, border_radius=4)
        self.hot.append(Hot(rect, lambda: setattr(self, "selected", index), f"row:{index}"))
        font = self.app.font_body
        self._text(f"{index + 1}.", rect.x + 8, y + 6, font, COLOR_TEXT_MUTED)
        self._text(self._fit(self._entry_summary(entry), font, 340), rect.x + 34, y + 6, font)
        self._text(self._source_text(entry), rect.x + 390, y + 7, self.app.font_small, COLOR_TEXT_MUTED)
        has_position = any(dial.unit == "degree" for dial in edit.dials_of(entry))
        position = edit.position(entry)
        if has_position:
            label, color = (f"{position[0]:.4f}, {position[1]:.4f}", COLOR_TEXT_MUTED) if position else ("not placed yet", COLOR_RED)
            self._text(label, rect.x + 530, y + 7, self.app.font_small, color)
        self._button((rect.right - 30, y + 3, 24, ROW_H - 10), "x", lambda: self._remove(index), font=self.app.font_small)
        self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"remove:{index}")

    def _draw_detail(self) -> None:
        self.app.draw_card(830, 392, 758, 436)
        if self.selected is None or self.selected >= len(self.draft.entries):
            self._text("SETTINGS", 844, 402, self.app.font_sub, COLOR_GOLD)
            self._wrapped("Add something from the left, or pick it from the list above, to change its settings here.", 844, 430, 720, COLOR_TEXT_MUTED, 2)
            return
        index, entry = self.selected, self.draft.entries[self.selected]
        kind = str(entry["kind"])
        self._text(f"{kind.upper()} SETTINGS", 844, 402, self.app.font_sub, COLOR_GOLD)
        self._text(KIND_TEXT[kind], 844, 420, self.app.font_small, COLOR_TEXT_MUTED)
        y = self._draw_sources(index, entry, 442)
        for key, label, names in (("event", "Model" if kind == "flow" else "Recorded event", None), ("mind", "Mind", MIND_TEXT), ("what", "Island" if kind == "weather" else "What it is", WHAT_TEXT)):
            options = edit.choices(entry, key)
            if options:
                y = self._draw_choice(index, entry, key, label, options, names, y)
        self._text("Name (optional)", 844, y + 8, self.app.font_body, COLOR_TEXT_MUTED)
        self._field((1000, y + 2, 300, 30), f"name:{index}", entry.get("name", ""), lambda text: edit.set_name(self.draft, index, text), empty="No name")
        y += 42
        dials = edit.dials_of(entry)
        spacing = min(50, (DETAIL_BOTTOM - y) // max(1, len(dials)))  # A storm has eight dials, and they all have to fit.
        for dial in dials:
            self._draw_dial(index, entry, dial, y)
            y += spacing

    def _draw_sources(self, index: int, entry, y: int) -> int:
        self._text("Numbers come from", 844, y + 8, self.app.font_body, COLOR_TEXT_MUTED)
        for number, source in enumerate(SOURCES):
            available = source in edit.choices(entry, "source")
            stage = NOT_BUILT.get((entry["kind"], source))
            label = (BUILT_IN if kind_is_model(entry, source) else SOURCE_TEXT[source]) + (f" (stage {stage})" if stage and not available else "")
            self._button((1000 + number * 190, y + 2, 182, 30), label, lambda s=source: self._apply(lambda: edit.set_choice(self.draft, index, "source", s)),
                         active=entry["source"] == source, enabled=available, font=self.app.font_small)
        return y + 38

    def _draw_choice(self, index: int, entry, key: str, label: str, options: tuple[str, ...], names, y: int) -> int:
        self._text(label, 844, y + 8, self.app.font_body, COLOR_TEXT_MUTED)
        for number, option in enumerate(options):
            text = names.get(option, option) if names else option
            row, column = divmod(number, CHOICES_PER_ROW)  # Five islands don't fit on one row.
            self._button((1000 + column * 190, y + 2 + row * 38, 182, 30), text, lambda o=option: self._apply(lambda: edit.set_choice(self.draft, index, key, o)),
                         active=entry.get(key) == option, font=self.app.font_small)
        return y + 38 * (1 + (len(options) - 1) // CHOICES_PER_ROW)

    def _draw_dial(self, index: int, entry, dial, y: int) -> None:
        self._text(dial.note, 844, y, self.app.font_body)
        self._text(f"{dial.name}, {dial.unit}, from {dial.low:g} to {dial.high:g}", 844, y + 18, self.app.font_small, COLOR_TEXT_MUTED)
        value = entry.get(dial.name)
        self._button((1300, y + 2, 34, 32), "-", lambda: self._step_dial(index, dial, -1))
        self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"minus:{dial.name}")
        self._field((1340, y + 2, 180, 32), f"dial:{index}:{dial.name}", value, lambda text: edit.set_dial(self.draft, index, dial.name, text), empty="Not set")
        self._button((1526, y + 2, 34, 32), "+", lambda: self._step_dial(index, dial, 1))
        self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"plus:{dial.name}")

    def _draw_footer(self) -> None:
        y = 838
        self._button((12, y, 90, 50), "New", lambda: self._guarded("New", self._new))
        self._button((110, y, 90, 50), "Open", lambda: self._guarded("Open", self._list_files))
        self._button((208, y, 90, 50), "Save", self._save)
        self._button((306, y, 90, 50), "Undo", self._undo)
        self._button((404, y, 110, 50), "Share", lambda: setattr(self, "share_open", True), color=COLOR_BLUE, ink=COLOR_PANEL_BG)
        self._text("Seed", 538, y + 16, self.app.font_sub, COLOR_PANEL_BG)
        self._field((582, y + 10, 90, 30), "seed", self.seed, self._set_seed)
        self._text("Same file and seed, same world. In play, one person is followed at a time.", 690, y + 16, self.app.font_small, COLOR_PANEL_ALT)
        self._button((1340, y, 248, 50), "PLAY THIS SCENARIO", self._play, color=COLOR_GREEN, ink=COLOR_PANEL_BG, font=self.app.font_title, enabled=not self.problem)

    def _draw_modal(self, width: int, height: int) -> pygame.Rect:
        self.hot = []
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 15, 26, 190))
        self.canvas.blit(dim, (0, 0))
        rect = pygame.Rect((WINDOW_WIDTH - width) // 2, (WINDOW_HEIGHT - height) // 2, width, height)
        self.app.draw_card(rect.x, rect.y, rect.width, rect.height)
        return rect

    def _draw_open_list(self) -> None:
        rect = self._draw_modal(760, 680)
        community = self.gallery is not None
        self._text("COMMUNITY SIMS" if community else "OPEN A SCENARIO", rect.x + 20, rect.y + 16, self.app.font_title, COLOR_GOLD)
        self._button((rect.right - 104, rect.y + 12, 90, 30), "Back" if community else "Close",
                     (lambda: setattr(self, "gallery", None)) if community else (lambda: setattr(self, "open_rows", None)))
        if community:
            self._text("Made by the public, and not checked by anyone. Each one is a model, not advice.", rect.x + 20, rect.y + 52, self.app.font_body, COLOR_TEXT_MUTED)
        else:
            self._text("Paste a link to a .qsim file, or drop a file on this window", rect.x + 20, rect.y + 48, self.app.font_small, COLOR_TEXT_MUTED)
            self._field((rect.x + 20, rect.y + 68, 460, 32), "link", self.link, self._set_link, empty="https://")
            self._button((rect.x + 488, rect.y + 68, 110, 32), "Open link", lambda: self.open_source(self.link), enabled=bool(self.link))
            self._button((rect.x + 606, rect.y + 68, 134, 32), "Community", self._open_gallery, color=COLOR_BLUE, ink=COLOR_PANEL_BG)
        rows = self.gallery if community else self.open_rows
        if len(rows) > OPEN_ROWS:
            self._text(f"Scroll to see more: showing {self.open_scroll + 1} to {min(len(rows), self.open_scroll + OPEN_ROWS)} of {len(rows)}", rect.x + 240, rect.y + 22, self.app.font_small, COLOR_TEXT_MUTED)
        y = rect.y + 112
        for row in rows[self.open_scroll:self.open_scroll + OPEN_ROWS]:
            if community:
                suffix = ", needs the data pack" if row["needs_data_pack"] else ""
                self._button((rect.x + 20, y, rect.width - 40, 40), f"{row['title']}  (by {row['author'] or 'anonymous'}{suffix})", lambda r=row: self._open_gallery_row(r), font=self.app.font_body)
                self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"community:{row['file']}")
            else:
                path, title = row
                self._button((rect.x + 20, y, rect.width - 40, 40), f"{title}  ({path.name if path.suffix == simfile.SUFFIX else path.stem})", lambda p=path: self._open(p), font=self.app.font_body)
                self.hot[-1] = Hot(self.hot[-1].rect, self.hot[-1].action, f"open:{path.stem}")
            y += 46
        if self.message:
            self._wrapped(self.message, rect.x + 20, rect.bottom - 44, rect.width - 40, COLOR_RED if self.message_bad else COLOR_BLUE, 2)

    def _draw_start(self) -> None:
        rect = self._draw_modal(820, 560)
        self._text("WHAT DO YOU WANT TO SIMULATE?", rect.x + 24, rect.y + 18, self.app.font_title, COLOR_GOLD)
        self._text("Pick a starting point. It plays straight away, and you can change anything in it.", rect.x + 24, rect.y + 50, self.app.font_body, COLOR_TEXT_MUTED)
        y = rect.y + 84
        for name, title, text, needs_pack in edit.TEMPLATES:
            box = pygame.Rect(rect.x + 24, y, rect.width - 48, 66)
            usable = not needs_pack or simfile.data_pack_present()
            self._button(box, "", lambda n=name: self._start_from(n), enabled=usable)
            self.hot[-1] = Hot(box, self.hot[-1].action, f"template:{name}") if usable else self.hot[-1]
            self._text(title, box.x + 14, box.y + 11, self.app.font_sub, COLOR_TEXT_MAIN if usable else COLOR_TEXT_HINT)
            self._text(text, box.x + 14, box.y + 36, self.app.font_small, COLOR_TEXT_MUTED)
            y += 74
        self._button((rect.x + 24, y + 4, 300, 40), "Open a file or community sim", self._list_files, color=COLOR_BLUE, ink=COLOR_PANEL_BG)
        self._button((rect.right - 144, y + 4, 120, 40), "Close", lambda: setattr(self, "start_open", False))

    def _draw_share(self) -> None:
        rect = self._draw_modal(700, 470)
        self._text("SHARE THIS SIM", rect.x + 24, rect.y + 18, self.app.font_title, COLOR_GOLD)
        self._text("Your name (optional)", rect.x + 24, rect.y + 62, self.app.font_small, COLOR_TEXT_MUTED)
        self._field((rect.x + 24, rect.y + 82, rect.width - 48, 32), "author", self.author, self._set_author, empty="Anonymous")
        self._text("What is it? One or two sentences", rect.x + 24, rect.y + 126, self.app.font_small, COLOR_TEXT_MUTED)
        self._field((rect.x + 24, rect.y + 146, rect.width - 48, 32), "description", self.description, self._set_description, empty="No description")
        y = rect.y + 196
        scenario = None if self.problem else edit.to_scenario(self.draft)
        if scenario is None:
            y = self._wrapped(f"Not ready: {self.problem}", rect.x + 24, y, rect.width - 48, COLOR_RED, 3)
        elif simfile.needs_data_pack(scenario):
            y = self._wrapped("This needs the 230 MB data pack, so it won't open on every copy of the app.", rect.x + 24, y, rect.width - 48, COLOR_RED, 2)
        else:
            y = self._wrapped("Runs anywhere: it needs nothing but the app. Same file and seed give the same world.", rect.x + 24, y, rect.width - 48, COLOR_GREEN_DARK, 2)
        self._wrapped("The file holds your scenario, seed, name and description, and nothing else from this computer.", rect.x + 24, y + 6, rect.width - 48, COLOR_TEXT_MUTED, 2)
        if self.message:
            self._wrapped(self.message, rect.x + 24, rect.bottom - 142, rect.width - 48, COLOR_RED if self.message_bad else COLOR_BLUE, 3)
        ready = scenario is not None
        self._button((rect.x + 24, rect.bottom - 62, 220, 44), "Save .qsim file", self._export, enabled=ready, color=COLOR_GREEN, ink=COLOR_PANEL_BG)
        self._button((rect.x + 254, rect.bottom - 62, 220, 44), "Publish online", self._publish, enabled=ready, color=COLOR_BLUE, ink=COLOR_PANEL_BG)
        self._button((rect.right - 144, rect.bottom - 62, 120, 44), "Close", lambda: setattr(self, "share_open", False))

    def _draw_building(self) -> None:
        rect = self._draw_modal(520, 130)
        self._text("Building this scenario...", rect.x + 24, rect.y + 24, self.app.font_title, COLOR_GOLD)
        self._text(f"{time.time() - self.build_started:.0f} s so far. A full eruption takes about 20 s.", rect.x + 24, rect.y + 64, self.app.font_body, COLOR_TEXT_MUTED)

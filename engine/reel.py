"""One summary film for a finished run, in the look of the simulation and the project's site.

Each moment plays at its scene's own camera angle, builds, then freezes on a card of what was true
at that moment in the run and what the published results say. Headlines dramatize; every number comes
from this run or a named published source. Display only: nothing here can change a result.
"""
import math
from pathlib import Path

import numpy as np
import pygame

WIDTH, HEIGHT = 1600, 900
TITLE_SECONDS, SHOT_SECONDS, END_SECONDS = 3.5, 6., 10.
FREEZE_AT = .52  # share of a shot before it freezes and the data card arrives
FADE_SECONDS = .5
PUSH_IN = .1
PIXEL = 3  # blocks the film into the simulation's pixel look

# The site's colour tokens.
WOOD, WOOD_DEEP, WOOD_BAR, WALNUT = (62, 40, 22), (38, 22, 10), (78, 48, 24), (106, 64, 28)
RIBBON, RIBBON_EDGE, TRIM = (244, 188, 58), (118, 68, 24), (232, 184, 72)
PARCHMENT, SAND, TROUGH = (250, 239, 212), (234, 216, 178), (68, 42, 22)
INK, MUTED, GOLD = (54, 32, 14), (78, 48, 20), (132, 76, 4)
GREEN, RED, BLUE, PURPLE, ON_DARK, ON_WOOD = (42, 122, 20), (172, 34, 26), (28, 84, 148), (146, 58, 196), (255, 250, 238), (234, 223, 196)
EMBER = (184, 74, 16)

# How each moment feels: colour multiplied over the shot, shake strength and when it peaks, and an edge pulse.
MOODS = {
    "leak_start": dict(grade=(236, 240, 196), rise=.5), "alarm_cutaway": dict(pulse=RED, shake=2.),
    "alarm_pool": dict(pulse=RED, shake=1.5), "pool_exit": dict(grade=(255, 244, 226)), "site_aerial": dict(grade=(255, 244, 226)),
    "column_street": dict(grade=(226, 208, 190), shake=2.5, rise=.7), "bay_wide": dict(grade=(240, 214, 190)),
    "crowd_aerial": dict(grade=(238, 222, 200)), "roof_cutaway": dict(grade=(234, 214, 192), shake=9., peak=.6),
    "flow_arrival": dict(grade=(226, 190, 164), shake=8., rise=1., end=.62), "person_closeup": dict(grade=(255, 244, 226)),
    "boat_lowered": dict(grade=(206, 218, 246)), "jump_boat": dict(grade=(206, 218, 246), shake=1.5, peak=.6),
    "jump_sea": dict(grade=(186, 208, 246), shake=4., peak=.5), "float_off": dict(grade=(192, 208, 246), shake=2., rise=.6),
}
ACTION_NAMES = {"hide": "Heading out", "explore": "Looking around", "rest": "Staying put", "forage": "Gathering things",
                "build_shelter": "Going indoors", "craft": "Helping others", "drink": "Getting water"}

FONT_DIR = Path(__file__).parent / "assets" / "fonts" / "barlow"
_fonts = {}


def _font(name, size):
    """Barlow, as on the site, falling back to a system font if the file is missing."""
    key = name, size
    if key not in _fonts:
        path = FONT_DIR / f"Barlow-{name}.ttf"
        _fonts[key] = pygame.font.Font(str(path), size) if path.exists() else pygame.font.SysFont("arial", size, bold=name != "Medium")
    return _fonts[key]


def _mono(size):
    key = "mono", size
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("cascadiamono,consolas,couriernew,courier", size)
    return _fonts[key]


def _ease(u):
    u = max(0., min(1., u))
    return 1 - (1 - u) ** 3


def _smooth(u):
    u = max(0., min(1., u))
    return u * u * (3 - 2 * u)


def _wrap(text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def _card(surface, rect, alpha=255):
    """The simulation's parchment card: shadow, oak edge, gold trim, rivets."""
    x, y, w, h = rect
    layer = pygame.Surface((w + 6, h + 8), pygame.SRCALPHA)
    pygame.draw.rect(layer, (*WOOD_DEEP, 255), (2, 4, w, h), border_radius=12)
    pygame.draw.rect(layer, (*WALNUT, 255), (0, 0, w, h), border_radius=12)
    pygame.draw.rect(layer, (*TRIM, 255), (3, 3, w - 6, h - 6), border_radius=10)
    pygame.draw.rect(layer, (*PARCHMENT, 255), (5, 5, w - 10, h - 10), border_radius=8)
    for cx, cy in ((10, 10), (w - 10, 10), (10, h - 10), (w - 10, h - 10)):
        pygame.draw.circle(layer, (124, 76, 30, 255), (cx, cy), 3)
        pygame.draw.circle(layer, (244, 198, 76, 255), (cx - 1, cy - 1), 2)
    layer.set_alpha(alpha)
    surface.blit(layer, (x, y))


def _pill(surface, x, y, text, color, alpha=255):
    label = _font("Bold", 16).render(text, True, ON_DARK)
    width = label.get_width() + 24
    layer = pygame.Surface((width, 28), pygame.SRCALPHA)
    pygame.draw.rect(layer, (*color, 255), (0, 0, width, 28), border_radius=14)
    layer.blit(label, (12, 14 - label.get_height() // 2))
    layer.set_alpha(alpha)
    surface.blit(layer, (x, y))
    return width


def _bar(surface, x, y, width, height, share, shown, name, font):
    """A purple choice bar. The label moves beside the fill when the fill is too short to hold it."""
    pygame.draw.rect(surface, SAND, (x, y, width, height), border_radius=4)
    fill = int(width * share * shown)
    if fill:
        pygame.draw.rect(surface, PURPLE, (x, y, max(fill, 6), height), border_radius=4)
    text = f"{name}  {share:.0%}"
    inside = font.size(text)[0] + 16 < fill
    label = font.render(text, True, ON_DARK if inside else INK)
    surface.blit(label, (x + 8 if inside else x + max(fill, 6) + 8, y + height // 2 - label.get_height() // 2))


def _lines(surface, text, font, color, x, y, width, spacing, alpha=255, limit=9):
    for line in _wrap(text, font, width)[:limit]:
        rendered = font.render(line, True, color)
        rendered.set_alpha(alpha)
        surface.blit(rendered, (x, y))
        y += spacing
    return y


class Reel:
    """Plays an opening card, one shot per moment, and the outcome. `render_scene` draws a scene at its own angle."""

    def __init__(self, render_scene, title, chapters, stats, closing, clock_text, table=None, shares=None):
        _fonts.clear()  # fonts don't survive pygame restarting, so each film loads its own
        self.render_scene, self.title, self.stats, self.closing = render_scene, title, stats, closing
        self.clock_text, self.table, self.shares = clock_text, table, shares or []
        self.shots = [dict(kind="title", seconds=TITLE_SECONDS, label="Start")]
        self.shots += [dict(kind="scene", seconds=SHOT_SECONDS, number=i + 1, **chapter) for i, chapter in enumerate(chapters)]
        self.shots.append(dict(kind="end", seconds=END_SECONDS, label="Outcome"))
        self.total = sum(shot["seconds"] for shot in self.shots)
        self.index, self.time, self.paused, self.finished = 0, 0., False, False
        self.frame = pygame.Surface((WIDTH, HEIGHT))
        self.buffer = pygame.Surface((WIDTH, HEIGHT))
        self.small = pygame.Surface((WIDTH // PIXEL, HEIGHT // PIXEL))
        self.previous = None
        self.backdrop = self._wood_backdrop()
        ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
        distance = np.hypot((xs - WIDTH / 2) / (WIDTH / 2), (ys - HEIGHT / 2) / (HEIGHT / 2))
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.vignette.fill((*WOOD_DEEP, 255))
        pygame.surfarray.pixels_alpha(self.vignette)[:] = np.clip((distance.T - .62) * 240, 0, 210).astype(np.uint8)
        self.edge = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.edge.fill((*RED, 255))
        pygame.surfarray.pixels_alpha(self.edge)[:] = np.clip((distance.T - .75) * 420, 0, 200).astype(np.uint8)

    @staticmethod
    def _wood_backdrop():
        surface = pygame.Surface((WIDTH, HEIGHT))
        surface.fill(WOOD)
        for y in range(0, HEIGHT, 24):
            pygame.draw.line(surface, (54, 34, 18), (0, y), (WIDTH, y))
        for x in range(0, WIDTH, 24):
            pygame.draw.line(surface, (54, 34, 18), (x, 0), (x, HEIGHT))
        return surface

    # --- Controls ---

    def update(self, dt):
        if self.paused or self.finished:
            return
        self.time += dt
        if self.time >= self.shots[self.index]["seconds"]:
            self.go(self.index + 1)

    def go(self, index):
        if index >= len(self.shots):
            self.finished = True
            return
        self.previous = self.frame.copy()
        self.index, self.time = max(0, index), 0.

    @property
    def elapsed_total(self):
        return sum(shot["seconds"] for shot in self.shots[:self.index]) + self.time

    # --- Drawing ---

    def draw(self, canvas):
        shot = self.shots[self.index]
        {"title": self._draw_title, "scene": self._draw_scene, "end": self._draw_end}[shot["kind"]](self.frame, shot)
        self._draw_chrome(self.frame, shot)
        canvas.blit(self.frame, (0, 0))
        if self.previous is not None and self.time < FADE_SECONDS:
            self.previous.set_alpha(int(255 * (1 - _smooth(self.time / FADE_SECONDS))))
            canvas.blit(self.previous, (0, 0))
            self.frame.blit(canvas, (0, 0))

    def _draw_scene(self, frame, shot):
        u = self.time / shot["seconds"]
        scene = shot["scene"]
        mood = MOODS.get(scene["kind"], {})
        action = min(1., u / FREEZE_AT)
        # The action slows as it nears the freeze; the camera keeps creeping in until then.
        self.render_scene(self.buffer, scene, .06 + (mood.get("end", .9) - .06) * _ease(action))
        zoom = 1 + PUSH_IN * _smooth(action)
        width, height = int(WIDTH / zoom), int(HEIGHT / zoom)
        side = 1 if shot["number"] % 2 else -1
        x, y = (WIDTH - width) / 2 + side * (WIDTH - width) * .3 * (action - .5), (HEIGHT - height) / 2
        shake = self._shake(mood, action)
        x = max(0, min(WIDTH - width, x + shake[0]))
        y = max(0, min(HEIGHT - height, y + shake[1]))
        pygame.transform.smoothscale(self.buffer.subsurface((int(x), int(y), width, height)), self.small.get_size(), self.small)
        pygame.transform.scale(self.small, (WIDTH, HEIGHT), frame)
        if "grade" in mood:
            frame.fill(mood["grade"], special_flags=pygame.BLEND_RGB_MULT)
        frame.blit(self.vignette, (0, 0))
        if mood.get("pulse") and u < FREEZE_AT:
            self.edge.set_alpha(int(150 * abs(math.sin(self.time * 6))))
            frame.blit(self.edge, (0, 0))
        freeze = _smooth((u - FREEZE_AT) / .1)
        if freeze:
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((*WOOD_DEEP, int(135 * freeze)))
            frame.blit(dim, (0, 0))
        self._draw_story(frame, shot, scene, u)
        if u > FREEZE_AT:
            self._draw_data(frame, shot, scene, (u - FREEZE_AT) / (1 - FREEZE_AT))

    def _shake(self, mood, action):
        strength = mood.get("shake", 0.)
        if not strength or action >= 1:
            return 0., 0.
        if "peak" in mood:
            strength *= max(0., 1 - abs(action - mood["peak"]) / .22)
        elif "rise" in mood:
            strength *= action
        return strength * math.sin(self.time * 47), strength * math.sin(self.time * 61)

    def _draw_story(self, frame, shot, scene, u):
        """The site's story card: a numbered pill, a short heavy line, one plain sentence."""
        alpha = int(255 * min(1., u * 8))
        slide = int((1 - _ease(u * 7)) * 40)
        font = _font("ExtraBold", 50)
        lines = _wrap(shot["headline"], font, 480)[:3]
        sub = _wrap(shot["sub"], _font("Medium", 19), 480)[:4]
        note = _wrap(scene.get("note", ""), _mono(13), 480)[:3] if scene.get("note") else []
        height = 78 + len(lines) * 52 + len(sub) * 25 + (len(note) * 18 + 10 if note else 0) + 22
        x, y = 40, HEIGHT - 92 - height + slide
        _card(frame, (x, y, 530, height), alpha)
        _pill(frame, x + 25, y + 22, f"{shot['number']:02d} / {shot['label'].upper()}", GREEN, alpha)
        clock = _mono(15).render(self.clock_text(scene["t"]), True, GOLD)
        clock.set_alpha(alpha)
        frame.blit(clock, (x + 505 - clock.get_width(), y + 28))
        text_y = _lines(frame, shot["headline"], font, INK, x + 25, y + 60, 480, 52, alpha, 3)
        text_y = _lines(frame, shot["sub"], _font("Medium", 19), MUTED, x + 25, text_y + 10, 480, 25, alpha, 4)
        if note:
            _lines(frame, scene["note"], _mono(13), GOLD, x + 25, text_y + 6, 480, 18, alpha, 3)

    def _draw_data(self, frame, shot, scene, u):
        """What was true at this moment, what people were choosing, and what the published results say."""
        snapshot = scene.get("snapshot") or {}
        research = shot.get("research")
        width = 610
        head_lines = len(_wrap(research[0], _font("Bold", 21), width - 56)[:2]) if research else 0
        body_lines = len(_wrap(research[1], _font("Medium", 17), width - 56)[:4]) if research else 0
        belief_lines = len(_wrap(snapshot["belief"], _mono(13), width - 56)[:2]) if snapshot.get("belief") else 0
        height = 186 + 29 * len(snapshot.get("actions", [])[:4]) + 17 * belief_lines + (92 + 26 * head_lines + 22 * body_lines if research else 0)
        x = WIDTH - width - 40 + int((1 - _ease(u * 5)) * (width + 60))
        y = max(90, (HEIGHT - 92 - height) // 2 + 30)
        _card(frame, (x, y, width, height))
        inner = x + 28
        _pill(frame, inner, y + 22, f"AT {self.clock_text(scene['t'])}", WOOD_BAR)
        rows = snapshot.get("rows", [])
        cell = (width - 56) // max(1, len(rows))
        for i, (label, value) in enumerate(rows):
            danger = "dead" in label.lower() or "lost" in label.lower() or "died" in label.lower()
            shown = round(value * _ease((u - .08 - i * .03) * 5)) if isinstance(value, int) else value
            number = _font("ExtraBold", 46).render(f"{shown:,}" if isinstance(shown, int) else str(shown), True, RED if danger and value else INK)
            frame.blit(number, (inner + i * cell, y + 58))
            frame.blit(_font("Medium", 15).render(label, True, MUTED), (inner + i * cell, y + 112))
        row_y = y + 150
        pygame.draw.line(frame, SAND, (inner, row_y - 8), (x + width - 28, row_y - 8), 2)
        frame.blit(_font("Bold", 17).render("WHAT PEOPLE WERE DECIDING", True, GOLD), (inner, row_y))
        row_y += 28
        for i, (name, share) in enumerate(snapshot.get("actions", [])[:4]):
            _bar(frame, inner, row_y, width - 56, 24, share, _ease((u - .1 - i * .04) * 4), name, _font("Bold", 15))
            row_y += 29
        belief = snapshot.get("belief")
        if belief:
            row_y = _lines(frame, belief, _mono(13), MUTED, inner, row_y + 4, width - 56, 17, 255, 2)
        if research:
            row_y += 10
            pygame.draw.line(frame, SAND, (inner, row_y), (x + width - 28, row_y), 2)
            alpha = int(255 * min(1., max(0., (u - .22) * 5)))
            _pill(frame, inner, row_y + 12, "PUBLISHED RESULT", BLUE, alpha)
            text_y = _lines(frame, research[0], _font("Bold", 21), INK, inner, row_y + 48, width - 56, 26, alpha, 2)
            text_y = _lines(frame, research[1], _font("Medium", 17), MUTED, inner, text_y + 2, width - 56, 22, alpha, 4)
            _lines(frame, research[2], _mono(12), GOLD, inner, text_y + 6, width - 56, 16, alpha, 1)

    def _draw_title(self, frame, shot):
        u = self.time / shot["seconds"]
        frame.blit(self.backdrop, (0, 0))
        width, height = 760, 280
        x, y = (WIDTH - width) // 2, (HEIGHT - height) // 2 + int((1 - _ease(u * 3)) * 40)
        _card(frame, (x, y, width, height), int(255 * min(1., u * 4)))
        _pill(frame, x + 34, y + 30, self.title["place"].upper(), EMBER, int(255 * min(1., u * 4)))
        _lines(frame, self.title["heading"], _font("ExtraBold", 66), INK, x + 34, y + 72, width - 68, 68, int(255 * min(1., u * 4)), 1)
        _lines(frame, self.title["sub"], _font("Medium", 21), MUTED, x + 34, y + 152, width - 68, 28, int(255 * min(1., (u - .15) * 4)), 4)

    def _draw_end(self, frame, shot):
        u = self.time / shot["seconds"]
        frame.blit(self.backdrop, (0, 0))
        left, top, width, height = 40, 112, 930, 640
        _card(frame, (left, top, width, height))
        inner = left + 34
        _pill(frame, inner, top + 24, "HOW THIS RUN ENDED", GREEN)
        cell = (width - 68) // max(1, len(self.stats))
        for i, stat in enumerate(self.stats):
            x = inner + i * cell
            value = stat["value"]
            shown = "n/a" if value is None else f"{round(value * _ease((u - .04 - i * .03) * 4)):,}" + stat.get("suffix", "")
            color = RED if stat.get("danger") and value else INK
            frame.blit(_font("ExtraBold", 58).render(shown, True, color), (x, top + 64))
            frame.blit(_font("Bold", 17).render(stat["label"], True, GOLD), (x, top + 134))
            _lines(frame, stat.get("detail", ""), _font("Medium", 15), MUTED, x, top + 158, cell - 16, 19, 255, 4)
        y = top + 252
        pygame.draw.line(frame, SAND, (inner, y - 8), (left + width - 34, y - 8), 2)
        frame.blit(_font("Bold", 18).render("WHAT PEOPLE SPENT THE RUN DECIDING", True, GOLD), (inner, y))
        y += 32
        for i, (name, share) in enumerate(self.shares[:5]):
            _bar(frame, inner, y, width - 68, 26, share, _ease((u - .1 - i * .03) * 4), name, _font("Bold", 16))
            y += 32
        y += 10
        pygame.draw.line(frame, SAND, (inner, y), (left + width - 34, y), 2)
        y = _lines(frame, self.closing["headline"], _font("ExtraBold", 28), INK, inner, y + 12, width - 68, 32, int(255 * min(1., max(0., (u - .15) * 5))), 2)
        _lines(frame, self.closing["limits"], _font("Medium", 17), MUTED, inner, y + 6, width - 68, 22, int(255 * min(1., max(0., (u - .2) * 5))), 3)
        if self.table:
            self._draw_table(frame, u)

    def _draw_table(self, frame, u):
        x, top, width, height = 990, 112, 570, 640
        _card(frame, (x + int((1 - _ease(u * 5)) * 200), top, width, height))
        inner = x + 30 + int((1 - _ease(u * 5)) * 200)
        _pill(frame, inner, top + 24, "PUBLISHED RESULTS", BLUE)
        y = _lines(frame, self.table["title"], _font("ExtraBold", 27), INK, inner, top + 62, width - 60, 31, 255, 2)
        y += 8
        columns = self.table["columns"]
        offsets = [0, 196, 300, 400]
        for col, name in enumerate(columns):
            frame.blit(_font("Bold", 15).render(name, True, GOLD), (inner + offsets[col], y))
        y += 26
        for row in self.table["rows"]:
            pygame.draw.line(frame, SAND, (inner, y - 3), (inner + width - 60, y - 3))
            for col, value in enumerate(row):
                frame.blit(_font("Bold" if col else "Medium", 17).render(str(value), True, INK), (inner + offsets[col], y + 2))
            y += 30
        y += 14
        for head, body in self.table["findings"][:3]:
            y = _lines(frame, head, _font("Bold", 18), INK, inner, y, width - 60, 23, 255, 2)
            y = _lines(frame, body, _font("Medium", 15), MUTED, inner, y, width - 60, 19, 255, 3) + 9
        _lines(frame, self.table["source"], _mono(12), GOLD, inner, top + height - 48, width - 60, 16, 255, 2)

    def _draw_chrome(self, frame, shot):
        """The gold ribbon and chapter buttons from the site."""
        ribbon = pygame.Rect((WIDTH - 340) // 2, 14, 340, 62)
        pygame.draw.rect(frame, WOOD_DEEP, ribbon.move(0, 3), border_radius=10)
        pygame.draw.rect(frame, RIBBON, ribbon, border_radius=10)
        pygame.draw.rect(frame, RIBBON_EDGE, ribbon, 2, border_radius=10)
        name = _font("ExtraBold", 25).render("QOGNITION", True, INK)
        frame.blit(name, name.get_rect(center=(WIDTH // 2, 34)))
        line = _font("Medium", 15).render(self.title["ribbon"], True, MUTED)
        frame.blit(line, line.get_rect(center=(WIDTH // 2, 60)))
        count = len(self.shots)
        button = min(112, (WIDTH - 120) // count - 6)
        x = (WIDTH - count * (button + 6)) // 2
        y = HEIGHT - 58
        for i, item in enumerate(self.shots):
            rect = pygame.Rect(x + i * (button + 6), y, button, 44)
            active = i == self.index
            pygame.draw.rect(frame, RIBBON if active else SAND, rect, border_radius=7)
            pygame.draw.rect(frame, RIBBON_EDGE, rect, 2, border_radius=7)
            top = _font("Bold", 13).render(f"{i:02d}" if 0 < i < count - 1 else "•", True, INK)
            frame.blit(top, top.get_rect(center=(rect.centerx, y + 13)))
            text = item["label"].upper()
            while _font("Medium", 12).size(text)[0] > button - 8 and len(text) > 3:
                text = text[:-1]
            label = _font("Medium", 12).render(text, True, INK)
            frame.blit(label, label.get_rect(center=(rect.centerx, y + 30)))
        state = "PAUSED   •   " if self.paused else ""
        hint = _font("Medium", 14).render(f"{state}LEFT / RIGHT CHAPTER   •   SPACE PAUSE   •   ESC CLOSE", True, INK)
        box = hint.get_rect(center=(WIDTH // 2, y - 20)).inflate(24, 10)
        pygame.draw.rect(frame, SAND, box, border_radius=5)
        pygame.draw.rect(frame, RIBBON_EDGE, box, 1, border_radius=5)
        frame.blit(hint, hint.get_rect(center=box.center))


def choose_chapters(library, key_of):
    """The first scene for each kind of moment, in the order they happened. Close-ups keep first and last."""
    seen = {}
    closeups = [scene for scene in library if scene["kind"] == "person_closeup"]
    for scene in library:
        if scene["kind"] != "person_closeup":
            seen.setdefault(key_of(scene), scene)
    picked = list(seen.items())
    if closeups:
        picked.append(("person_first", closeups[0]))
        if len(closeups) > 1:
            picked.append(("person_last", closeups[-1]))
    picked.sort(key=lambda item: item[1]["t"])
    return picked


def action_shares(counter):
    """Named shares of a Counter of actions, largest first."""
    total = sum(counter.values()) or 1
    return [(ACTION_NAMES.get(action, action), count / total) for action, count in counter.most_common()]

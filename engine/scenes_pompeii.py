"""Pompeii cutscenes, each from a different camera. Display only: they never change a result.

Street level looking up, aerial over the crowds, a wide shot from the bay, a side-on house
cutaway, a close-up on one person, and a flow arriving down a street. Drawn from pygame
primitives, like the rest of the GUI.
"""
import math

import pygame

from engine.citizens import ROLE_COLORS
from engine.cutscenes import DURATION, CutscenePlayer
from engine.eruption import START_HOUR, STEP_MINUTES

WIDTH, HEIGHT = 1600, 900
BAR = 76
ASH = (92, 84, 80)
DUSK_TOP, DUSK_LOW = (40, 36, 44), (150, 110, 84)
STONE, ROOF, PLASTER = (168, 150, 126), (154, 78, 52), (212, 190, 150)
SEA_FAR, SEA_NEAR = (64, 92, 110), (18, 42, 60)
PUMICE = (214, 206, 188)
SKIN, DARK = (226, 190, 154), (30, 26, 24)


def _gradient(surface, top, low, y0=0, y1=HEIGHT):
    for y in range(y0, y1):
        f = (y - y0) / max(1, y1 - y0)
        pygame.draw.line(surface, tuple(int(a + (b - a) * f) for a, b in zip(top, low)), (0, y), (WIDTH, y))


def _column(surface, base_x, base_y, height, width, seed=7, color=(70, 64, 62)):
    """Eruption column: stacked billows, with an umbrella cloud once it is tall."""
    pygame.draw.polygon(surface, color, [(base_x - width * .12, base_y), (base_x + width * .12, base_y),
                                         (base_x + width * .26, base_y - height), (base_x - width * .26, base_y - height)])
    for i in range(22):
        f = i / 21
        wobble = math.sin(i * 1.7 + seed) * width * .1 * f
        radius = int(width * (.09 + .2 * f))
        pygame.draw.circle(surface, tuple(min(255, c + (i % 3) * 8) for c in color),
                           (int(base_x + wobble), int(base_y - height * f)), radius)
    if height > 250:
        top = base_y - height
        for i in range(12):
            a = -1 + 2 * i / 11
            pygame.draw.circle(surface, tuple(min(255, c + (i % 3) * 10) for c in color),
                               (int(base_x + a * width * 1.2), int(top + abs(a) * 40)), int(width * .26))


def _pumice(surface, f, count, seed=3):
    """Falling stones; speeds differ so the fall reads as depth."""
    for i in range(count):
        rate = 1.2 + (i * 37 % 9) * .22
        x = (i * 211 + seed * 97) % WIDTH
        y = BAR + ((i * 131 + f * 900 * rate) % (HEIGHT - 2 * BAR))
        size = 1 + i % 3
        pygame.draw.line(surface, PUMICE, (x, y), (x - 1, y + 3 + size * 3), size)


def _person(surface, x, y, size, color, pose="stand", look_up=False):
    head = max(3, int(size * .12))
    width = max(2, int(size * .08))
    swing = {"walk": .16, "run": .28}.get(pose, .08)
    hip, neck = (x, y - size * .46), (x, y - size * .84)
    pygame.draw.line(surface, DARK, hip, (x - size * swing, y), width)
    pygame.draw.line(surface, DARK, hip, (x + size * swing, y), width)
    pygame.draw.line(surface, color, hip, neck, width + 3)
    if look_up:
        pygame.draw.line(surface, color, neck, (x + size * .26, y - size * 1.06), width)
        pygame.draw.line(surface, color, neck, (x - size * .24, y - size * .56), width)
    else:
        pygame.draw.line(surface, color, neck, (x + size * .24, y - size * .52), width)
        pygame.draw.line(surface, color, neck, (x - size * .24, y - size * .52), width)
    pygame.draw.circle(surface, SKIN, (int(x), int(neck[1] - head)), head)


def scene_column_street(surface, f, scene):
    """Low in a street, looking up as the column climbs over the rooftops."""
    _gradient(surface, DUSK_TOP, (180, 158, 132))
    vanish_x, horizon = 800, 500
    _column(surface, vanish_x + 40, horizon - 60, 80 + 340 * min(1., f * 1.4), 230)
    for side in (-1, 1):
        for i in range(5):
            near, far = 1 - i / 5, 1 - (i + 1) / 5
            xa, xb = vanish_x + side * (70 + 760 * near), vanish_x + side * (70 + 760 * far)
            top_a, top_b = horizon - 400 * near - 40, horizon - 400 * far - 40
            bottom_a, bottom_b = horizon + 330 * near, horizon + 330 * far
            pygame.draw.polygon(surface, PLASTER if i % 2 else STONE,
                                [(xa, top_a), (xb, top_b), (xb, bottom_b), (xa, bottom_a)])
            pygame.draw.polygon(surface, ROOF, [(xa, top_a), (xb, top_b), (xb, top_b - 16 * far - 4), (xa, top_a - 30 * near)])
            door_x = (xa + xb) / 2
            pygame.draw.rect(surface, DARK, (door_x - 26 * near, bottom_a - 150 * near - 10, 52 * near + 4, 150 * near + 10))
    road = [(vanish_x - 70, horizon), (vanish_x + 70, horizon), (vanish_x + 830, HEIGHT), (vanish_x - 830, HEIGHT)]
    pygame.draw.polygon(surface, (118, 108, 96), road)
    for i in range(3):
        x = vanish_x + (-260 + i * 240)
        _person(surface, x, 760 - i * 30, 210 - i * 40, (120, 200, 255) if i % 2 else (240, 236, 224), look_up=True)
    _pumice(surface, f, int(30 + 170 * f))


def scene_crowd_aerial(surface, f, scene):
    """From high overhead, crowds stream along the real street grid toward the gates."""
    surface.fill((70, 78, 62))
    world, size = scene["world"], 21
    ox, oy = (WIDTH - 40 * size) // 2, 36
    streets = []
    for y in range(40):
        for x in range(40):
            tile = world.get_tile(x, y)
            rect = (ox + x * size, oy + y * size, size, size)
            if (x, y) in world.wall_tiles and not tile:
                pygame.draw.rect(surface, (62, 54, 46), rect)
            elif tile == 4:
                pygame.draw.rect(surface, ROOF, rect)
                pygame.draw.rect(surface, (122, 58, 40), rect, 1)
            elif tile == 2:
                pygame.draw.rect(surface, (98, 132, 74), rect)
            elif tile:
                pygame.draw.rect(surface, (204, 190, 164), rect)
                streets.append((x, y))
    field = scene["field"]
    for i in range(700):
        x, y = streets[(i * 53) % len(streets)]
        for _ in range(int(f * 16 + (i % 7))):
            following = field.get((x, y))
            if following is None:
                break
            x, y = following
        color = (24, 24, 44) if i % 3 else (150, 30, 30)
        jitter_x, jitter_y = (i * 13) % 15, (i * 29) % 15
        pygame.draw.circle(surface, color, (ox + x * size + jitter_x + 3, oy + y * size + jitter_y + 3), 4)
    tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    tint.fill((*ASH, 70))
    surface.blit(tint, (0, 0))
    _pumice(surface, f, 90)


def scene_bay_wide(surface, f, scene):
    """A wide shot from a boat, with Vesuvius behind the town and the column above it."""
    _gradient(surface, (34, 32, 38), (168, 124, 96), 0, 520)
    vent_x, vent_y = 520, 250
    _column(surface, vent_x, vent_y, 130 + 150 * min(1., f * 1.5), 150)
    pygame.draw.polygon(surface, (62, 56, 56), [(40, 520), (vent_x - 40, vent_y), (vent_x + 40, vent_y), (1100, 520)])
    if scene.get("flow"):
        spread = min(1., f * 1.3)
        cloud_x = vent_x + (900 - vent_x) * spread
        for i in range(16):
            g = i / 15 * spread
            pygame.draw.circle(surface, (146, 132, 122), (int(vent_x + (cloud_x - vent_x) * g),
                                                          int(vent_y + (500 - vent_y) * g)), int(26 + 44 * g))
    pygame.draw.rect(surface, (116, 104, 84), (0, 508, WIDTH, 22))
    for i in range(16):
        x = 780 + i * 22
        pygame.draw.rect(surface, ROOF if i % 2 else PLASTER, (x, 492 - (i * 7) % 16, 19, 22 + (i * 7) % 16))
    _gradient(surface, SEA_FAR, SEA_NEAR, 530, HEIGHT)
    for i in range(40):
        y = 540 + (i * 53) % (HEIGHT - 540 - BAR)
        pygame.draw.line(surface, (92, 124, 140), ((i * 197 + f * 30) % WIDTH, y), ((i * 197 + f * 30) % WIDTH + 18, y), 1)
    bob = math.sin(f * 12) * 6
    pygame.draw.polygon(surface, (52, 38, 28), [(1120, 700 + bob), (1500, 690 + bob), (1440, 760 + bob), (1170, 765 + bob)])
    pygame.draw.line(surface, (40, 30, 24), (1310, 695 + bob), (1310, 560 + bob), 6)
    pygame.draw.polygon(surface, (196, 182, 160), [(1314, 565 + bob), (1314, 670 + bob), (1420, 670 + bob)])
    _pumice(surface, f, 50)


def scene_roof_cutaway(surface, f, scene):
    """A house in section: pumice piles on the roof until it gives way."""
    surface.fill((58, 50, 48))
    left, right, floor = 300, 1300, 730
    pygame.draw.rect(surface, (70, 58, 50), (0, floor, WIDTH, HEIGHT - floor))
    pygame.draw.rect(surface, PLASTER, (left, 360, right - left, floor - 360))
    pygame.draw.rect(surface, STONE, (left - 30, 330, 30, floor - 330))
    pygame.draw.rect(surface, STONE, (right, 330, 30, floor - 330))
    pygame.draw.rect(surface, STONE, ((left + right) // 2 - 12, 360, 24, floor - 360))
    pygame.draw.rect(surface, (120, 86, 54), (left + 90, floor - 90, 200, 16))
    pygame.draw.rect(surface, (120, 86, 54), (right - 280, floor - 150, 26, 150))
    fail = min(1., max(0., (f - .55) / .2))
    pile = 40 + 150 * min(1., f / .55)
    sag = 110 * fail
    middle = (left + right) // 2
    roof_y = 330
    if fail < 1:
        pygame.draw.polygon(surface, ROOF, [(left - 40, roof_y), (middle, roof_y - 40 + sag), (right + 40, roof_y),
                                            (right + 40, roof_y + 20), (middle, roof_y - 20 + sag), (left - 40, roof_y + 20)])
        def roof_line(x):
            return roof_y - 40 + sag + abs(x - middle) * 40 / ((right - left) / 2)
        points = [(left - 40, roof_line(left - 40))]
        for x in range(left - 40, right + 60, 60):
            points.append((x, roof_line(x) - pile * (.75 + .25 * math.sin(x * .05))))
        points.append((right + 40, roof_line(right + 40)))
        pygame.draw.polygon(surface, PUMICE, points)
        for i in range(90):  # stones on the surface of the pile
            x = left - 20 + (i * 47) % (right - left + 40)
            height = pile * (.75 + .25 * math.sin(x * .05)) * ((i * 17 % 34) / 34)
            pygame.draw.circle(surface, (190, 180, 160), (x, int(roof_line(x) - height)), 3 + i % 3)
    else:
        for i in range(70):
            x = left + (i * 67) % (right - left)
            pygame.draw.circle(surface, PUMICE, (x, floor - (i * 13) % 110), 4 + i % 4)
        for i in range(14):
            x = left + (i * 131) % (right - left)
            pygame.draw.line(surface, ROOF, (x, floor - (i * 23) % 70), (x + 60, floor - (i * 47) % 90), 8)
    if .55 < f < .95:
        dust = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dust.fill((186, 170, 150, int(180 * math.sin((f - .55) / .4 * math.pi))))
        surface.blit(dust, (0, 0))
    if fail < 1:
        color = ROLE_COLORS.get(scene.get("role"), ROLE_COLORS["resident"])
        _person(surface, left + 420, floor, 190, color, look_up=True)
        _person(surface, right - 200, floor, 170, (240, 236, 224))
    _pumice(surface, f, 80)


def scene_person_closeup(surface, f, scene):
    """Zooms in on one person: the camera closes on their face and shows what they heard."""
    _gradient(surface, (66, 58, 58), (150, 122, 100))
    zoom = .7 + .55 * min(1., f * 2)
    for i, side in enumerate((-1, 1)):
        pygame.draw.rect(surface, PLASTER if i else STONE, (800 + side * 760 * zoom - 200, 120, 400, 700))
    color = ROLE_COLORS.get(scene.get("role"), ROLE_COLORS["resident"])
    center_x, center_y = 620, 470
    head = int(92 * zoom)
    shoulders = int(220 * zoom)
    pygame.draw.ellipse(surface, color, (center_x - shoulders, center_y + head // 2, shoulders * 2, 700))
    pygame.draw.circle(surface, SKIN, (center_x, center_y - head // 3), head)
    pygame.draw.circle(surface, DARK, (center_x, center_y - head // 3), head, 2)
    eye = int(head * .38)
    pygame.draw.circle(surface, DARK, (center_x - eye, center_y - head // 2), max(3, int(8 * zoom)))
    pygame.draw.circle(surface, DARK, (center_x + eye, center_y - head // 2), max(3, int(8 * zoom)))
    # A level mouth: the model has no emotions, so the face shows none.
    pygame.draw.line(surface, DARK, (center_x - eye // 2, center_y - head // 12), (center_x + eye // 2, center_y - head // 12), 3)
    box = pygame.Surface((560, 280), pygame.SRCALPHA)
    box.fill((14, 12, 12, 200))
    surface.blit(box, (960, 250))
    font = scene.get("font")
    if font:
        for i, line in enumerate(_wrap(scene.get("thought", ""), font, 520)):
            surface.blit(font.render(line, True, (246, 238, 220)), (980, 270 + i * 34))
        tag = font.render("Illustration, written from model values", True, (190, 180, 160))
        surface.blit(tag, (980, 490))
    _pumice(surface, f, 70)


def scene_flow_arrival(surface, f, scene):
    """Eye level in a street as a pyroclastic flow comes down it."""
    _gradient(surface, (46, 40, 40), (130, 108, 90))
    for side in (-1, 1):
        for i in range(4):
            near = 1 - i / 4
            x = 800 + side * (120 + 650 * near)
            pygame.draw.rect(surface, STONE if i % 2 else PLASTER, (x - 110 * near, 720 - 560 * near, 220 * near, 560 * near + 120))
    pygame.draw.polygon(surface, (118, 108, 96), [(720, 480), (880, 480), (1500, HEIGHT), (100, HEIGHT)])
    _person(surface, 560 + 190 * f, 760, 180, ROLE_COLORS.get(scene.get("role"), ROLE_COLORS["resident"]), pose="run")
    _person(surface, 1020 - 120 * f, 720, 150, (240, 236, 224), pose="run")
    front = 200 + 900 * f
    for i in range(60):
        a = i / 59
        x = a * WIDTH
        y = front - 40 * math.sin(i * 1.1 + f * 8) - 30
        radius = int((90 + (i * 7) % 60) * (.5 + f))
        pygame.draw.circle(surface, tuple(max(0, c - (i % 4) * 12) for c in (126, 112, 100)), (int(x), int(y - 260 * (1 - f))), radius)
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((38, 32, 30, int(255 * max(0., (f - .55) / .45))))
    surface.blit(veil, (0, 0))


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


SCENES = {
    "column_street": scene_column_street, "crowd_aerial": scene_crowd_aerial, "bay_wide": scene_bay_wide,
    "roof_cutaway": scene_roof_cutaway, "person_closeup": scene_person_closeup, "flow_arrival": scene_flow_arrival,
}


class PompeiiCutscenes(CutscenePlayer):
    """The shared player, with Pompeii's scenes and clock."""

    def draw(self, canvas):
        if self.current is None:
            return
        scene = self.current
        scene.setdefault("font", self.font_title)
        SCENES[scene["kind"]](canvas, min(1., self.elapsed / DURATION), scene)
        self._draw_frame(canvas, scene)

    def _draw_frame(self, canvas, scene):
        pygame.draw.rect(canvas, (6, 5, 5), (0, 0, WIDTH, BAR))
        pygame.draw.rect(canvas, (6, 5, 5), (0, HEIGHT - BAR, WIDTH, BAR))
        minutes = START_HOUR * 60 + scene["t"] * STEP_MINUTES
        clock = self.font_small.render(f"{minutes // 60 % 24:02d}:{minutes % 60:02d}", True, (196, 188, 172))
        canvas.blit(clock, (28, 30))
        title = self.font_title.render(scene["caption"], True, (250, 240, 216))
        canvas.blit(title, ((WIDTH - title.get_width()) // 2, HEIGHT - BAR + 16))
        hint = self.font_small.render("Click or press any key to skip", True, (150, 142, 130))
        canvas.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - BAR + 46))
        pygame.draw.rect(canvas, (226, 170, 90), (0, HEIGHT - 4, int(WIDTH * min(1., self.elapsed / DURATION)), 4))

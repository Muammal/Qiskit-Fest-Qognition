"""Waterloo cutscenes, each from a different camera. Display only: they never change a result.

A close view of the assumed leak, a side-on cutaway of the building, a shot across the pool, a low angle
at the water's edge, an aerial view from real positions and a close-up on one person. Layouts are
illustrations, because no floor plan was found. Drawn from pygame primitives, like the rest of the GUI.
"""
import math

import pygame

from engine.chlorine import START_HOUR, STEP_SECONDS
from engine.cutscenes import DURATION, CutscenePlayer
from engine.gui_site import GAS, _tile_color
from engine.patrons import ROLE_COLORS
from engine.scenes_pompeii import BAR, HEIGHT, WIDTH, _gradient, _person, _wrap

SKY_TOP, SKY_LOW = (112, 176, 226), (206, 230, 240)
WATER, WATER_DEEP = (96, 190, 232), (44, 138, 196)
CONCRETE, BRICK, STEEL = (206, 200, 186), (150, 96, 76), (132, 140, 146)
GRASS, DARK, SKIN = (136, 178, 104), (30, 26, 24), (226, 190, 154)
ALARM = (226, 44, 40)
CROWD = ((255, 214, 64), (120, 200, 255), (224, 80, 60), (240, 236, 224))


def _gas(surface, x, y, spread, alpha, seed=3):
    """Gas haze. Colour and density are exaggerated so it can be seen."""
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(46):
        angle = i * 2.399 + seed
        distance = spread * ((i * 37 % 46) / 46) ** .6
        radius = int(26 + spread * .12 + (i * 11) % 30)
        px, py = x + math.cos(angle) * distance, y + math.sin(angle) * distance * .55
        pygame.draw.circle(layer, (*GAS, alpha), (int(px), int(py)), radius)
    surface.blit(layer, (0, 0))


def _tag(surface, scene, text, x=28, y=BAR + 14):
    font = scene.get("small")
    if font:
        label = font.render(text, True, (250, 244, 224))
        box = pygame.Surface((label.get_width() + 20, label.get_height() + 10), pygame.SRCALPHA)
        box.fill((14, 12, 12, 190))
        surface.blit(box, (x, y))
        surface.blit(label, (x + 10, y + 5))


def _water(surface, y0, y1, f):
    _gradient(surface, WATER, WATER_DEEP, y0, y1)
    for i in range(70):
        y = y0 + (i * 41) % max(1, y1 - y0)
        x = (i * 173 + f * 60 * (1 + i % 3)) % WIDTH
        pygame.draw.line(surface, (190, 232, 246), (x, y), (x + 14 + (y - y0) * .08, y), 1)


def _swimmer(surface, x, y, size, color):
    pygame.draw.circle(surface, SKIN, (int(x), int(y - size * .34)), max(4, int(size * .2)))
    pygame.draw.ellipse(surface, color, (x - size * .3, y - size * .18, size * .6, size * .3))
    pygame.draw.line(surface, WATER_DEEP, (x - size * .6, y + size * .1), (x + size * .6, y + size * .1), 2)


def scene_leak_start(surface, f, scene):
    """Up close at the assumed spot: a chemical line starts to leak and gas fills the small room."""
    surface.fill((186, 182, 170))
    pygame.draw.rect(surface, (120, 116, 106), (0, 700, WIDTH, HEIGHT - 700))
    for i in range(8):
        pygame.draw.line(surface, (166, 162, 150), (0, 130 + i * 80), (WIDTH, 130 + i * 80), 2)
    for i, x in enumerate((260, 560)):
        pygame.draw.rect(surface, (64, 104, 150), (x, 330, 210, 380), border_radius=30)
        pygame.draw.rect(surface, (40, 72, 110), (x, 330, 210, 380), 4, border_radius=30)
        pygame.draw.rect(surface, (240, 226, 90), (x + 40, 470, 130, 74))
        pygame.draw.rect(surface, DARK, (x + 40, 470, 130, 74), 3)
    pygame.draw.rect(surface, STEEL, (470, 240, 880, 36))
    pygame.draw.rect(surface, STEEL, (350, 240, 36, 100))
    pygame.draw.rect(surface, STEEL, (350, 240, 150, 36))
    pygame.draw.rect(surface, (80, 86, 92), (980, 222, 66, 72), border_radius=6)
    pygame.draw.circle(surface, ALARM, (1013, 208), 20)
    leak_x, leak_y = 1013, 286
    _gas(surface, leak_x, leak_y + 180 * f, 60 + 660 * f, int(40 + 60 * f))
    for i in range(30):
        g = (i / 30 + f * 2) % 1
        pygame.draw.circle(surface, (*GAS, ), (int(leak_x + math.sin(i * 1.9) * 80 * g), int(leak_y + 300 * g)), 3 + int(8 * g))
    _tag(surface, scene, "Illustration. The real place and cause are unknown, and the gas colour is exaggerated.")


def scene_alarm_cutaway(surface, f, scene):
    """The building in section as the alarm starts, with the arena on one side and the pool door on the other."""
    _gradient(surface, SKY_TOP, SKY_LOW, 0, 700)
    pygame.draw.rect(surface, GRASS, (0, 700, WIDTH, HEIGHT - 700))
    left, right, floor, top = 180, 1420, 720, 230
    pygame.draw.rect(surface, (238, 230, 212), (left, top, right - left, floor - top))
    pygame.draw.polygon(surface, BRICK, [(left - 40, top), ((left + right) // 2, top - 90), (right + 40, top)])
    pygame.draw.rect(surface, (206, 234, 248), (left + 40, floor - 18, 760, 18))
    pygame.draw.rect(surface, BRICK, (left + 810, top, 16, floor - top - 150))
    pygame.draw.rect(surface, BRICK, (left, top, 16, floor - top))
    pygame.draw.rect(surface, BRICK, (right - 16, top, 16, floor - top))
    pygame.draw.rect(surface, (226, 44, 40), (right - 16, floor - 130, 16, 130))
    for i, x in enumerate((360, 540, 760, 1040, 1180, 1300)):
        _person(surface, x + 40 * f * (1 if i > 2 else -1), floor - 4, 120, CROWD[i % 4], pose="walk" if f > .4 else "stand")
    for i, x in enumerate((420, 800, 1180)):
        pulse = abs(math.sin(f * 18 + i))
        pygame.draw.circle(surface, ALARM, (x, top + 26), 16)
        ring = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for r in range(3):
            pygame.draw.circle(ring, (*ALARM, int(150 * pulse / (r + 1))), (x, top + 26), 36 + r * 34, 4)
        surface.blit(ring, (0, 0))
    _tag(surface, scene, "Illustration. Whether the centre had an alarm in 2012 is unknown; here a staff member triggers it.")


def scene_alarm_pool(surface, f, scene):
    """Across the pool from the far side: the sound reaches the people in the water and on the deck."""
    _gradient(surface, SKY_TOP, SKY_LOW, 0, 330)
    pygame.draw.rect(surface, BRICK, (260, 170, 1080, 160))
    pygame.draw.rect(surface, (238, 230, 212), (260, 170, 1080, 22))
    for i in range(6):
        pygame.draw.rect(surface, (120, 170, 196), (320 + i * 170, 220, 110, 70))
    pygame.draw.polygon(surface, CONCRETE, [(0, 330), (WIDTH, 330), (WIDTH, 400), (0, 400)])
    _water(surface, 400, HEIGHT, f)
    for lane in range(1, 8):
        top_x, low_x = 800 + (lane - 4) * 130, 800 + (lane - 4) * 310
        for i in range(14):
            g = i / 14
            x, y = top_x + (low_x - top_x) * g, 400 + (HEIGHT - 400) * g
            pygame.draw.circle(surface, (226, 66, 54) if i % 2 else (246, 244, 236), (int(x), int(y)), 2 + int(g * 6))
    for i in range(10):
        _person(surface, 120 + i * 150, 372 + (i % 2) * 14, 64, CROWD[i % 4], pose="walk" if f > .5 else "stand")
    for i in range(12):
        x, y = 130 + (i * 383) % 1340, 450 + (i * 97) % 340
        depth = (y - 400) / 500
        _swimmer(surface, x, y + math.sin(f * 9 + i) * 4, 44 + 90 * depth, CROWD[i % 4])
    pulse = abs(math.sin(f * 18))
    pygame.draw.circle(surface, ALARM, (800, 196), 15)
    ring = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for r in range(4):
        pygame.draw.circle(ring, (*ALARM, int(120 * pulse / (r + 1))), (800, 196), 40 + r * 60, 4)
    surface.blit(ring, (0, 0))
    _tag(surface, scene, "Illustration. Hearing it is a chance in the model, and lower outdoors.")


def scene_pool_exit(surface, f, scene):
    """Low at the water's edge as people climb out and cross the deck."""
    _gradient(surface, SKY_TOP, SKY_LOW, 0, 420)
    pygame.draw.rect(surface, GRASS, (0, 360, WIDTH, 80))
    pygame.draw.rect(surface, DARK, (0, 330, WIDTH, 6))
    for i in range(40):
        pygame.draw.line(surface, DARK, (i * 42, 330), (i * 42, 440), 2)
    pygame.draw.polygon(surface, CONCRETE, [(0, 440), (WIDTH, 440), (WIDTH, 640), (0, 640)])
    _water(surface, 640, HEIGHT, f)
    pygame.draw.rect(surface, (246, 244, 236), (0, 632, WIDTH, 10))
    count = min(7, scene.get("count", 7))
    for i in range(count):
        phase = min(1., max(0., f * 1.8 - i * .1))
        x = 800 + (i - (count - 1) / 2) * 200
        if phase < .35:
            _swimmer(surface, x, 720 - 70 * phase, 150, CROWD[i % 4])
        else:
            walk = (phase - .35) / .65
            y = 640 - 150 * walk
            _person(surface, x + 90 * walk, y, 300 - 170 * walk, CROWD[i % 4], pose="walk")
    _tag(surface, scene, "Illustration. Only the number in the caption comes from this run, and at most 7 are drawn.")


def scene_site_aerial(surface, f, scene):
    """From overhead on the real outlines, with each person at their position in this run, heading for an exit."""
    world, size = scene["world"], 21
    ox, oy = (WIDTH - 40 * size) // 2, 26
    surface.fill((64, 88, 56))
    for y in range(40):
        for x in range(40):
            pygame.draw.rect(surface, _tile_color(world, x, y), (ox + x * size, oy + y * size, size, size))
    field = scene["field"]
    for pos, role, leaving in scene["people"]:
        p = tuple(pos)
        if leaving:
            for _ in range(int(f * 10)):
                following = field.get(p)
                if following is None:
                    break
                p = following
        pygame.draw.circle(surface, ROLE_COLORS[role], (ox + p[0] * size + 10, oy + p[1] * size + 10), 5)
        pygame.draw.circle(surface, DARK, (ox + p[0] * size + 10, oy + p[1] * size + 10), 5, 1)
    _tag(surface, scene, "Real outlines; doors, inside assumed.")


def scene_person_closeup(surface, f, scene):
    """Zooms in on one person with what the model says they noticed."""
    _gradient(surface, SKY_TOP, SKY_LOW, 0, 620)
    pygame.draw.rect(surface, CONCRETE, (0, 620, WIDTH, HEIGHT - 620))
    pygame.draw.rect(surface, BRICK, (0, 300, 700, 320))
    zoom = .7 + .55 * min(1., f * 2)
    color = ROLE_COLORS.get(scene.get("role"), ROLE_COLORS["adult"])
    center_x, center_y = 560, 470
    head, shoulders = int(92 * zoom), int(220 * zoom)
    pygame.draw.ellipse(surface, color, (center_x - shoulders, center_y + head // 2, shoulders * 2, 700))
    pygame.draw.circle(surface, SKIN, (center_x, center_y - head // 3), head)
    pygame.draw.circle(surface, DARK, (center_x, center_y - head // 3), head, 2)
    eye = int(head * .38)
    pygame.draw.circle(surface, DARK, (center_x - eye, center_y - head // 2), max(3, int(8 * zoom)))
    pygame.draw.circle(surface, DARK, (center_x + eye, center_y - head // 2), max(3, int(8 * zoom)))
    # A level mouth: the model has no emotions, so the face shows none.
    pygame.draw.line(surface, DARK, (center_x - eye // 2, center_y - head // 12), (center_x + eye // 2, center_y - head // 12), 3)
    box = pygame.Surface((600, 300), pygame.SRCALPHA)
    box.fill((14, 12, 12, 205))
    surface.blit(box, (920, 240))
    font = scene.get("font")
    if font:
        for i, line in enumerate(_wrap(scene.get("thought", ""), font, 560)):
            surface.blit(font.render(line, True, (246, 238, 220)), (940, 260 + i * 34))
        surface.blit(font.render("Illustration, written from model values", True, (190, 180, 160)), (940, 496))


SCENES = {
    "leak_start": scene_leak_start, "alarm_cutaway": scene_alarm_cutaway, "alarm_pool": scene_alarm_pool,
    "pool_exit": scene_pool_exit, "site_aerial": scene_site_aerial, "person_closeup": scene_person_closeup,
}


class WaterlooCutscenes(CutscenePlayer):
    """The shared player, with Waterloo's scenes and clock."""

    def draw(self, canvas):
        if self.current is None:
            return
        scene = self.current
        scene.setdefault("font", self.font_title)
        scene.setdefault("small", self.font_small)
        SCENES[scene["kind"]](canvas, min(1., self.elapsed / DURATION), scene)
        self._draw_frame(canvas, scene)

    def _draw_frame(self, canvas, scene):
        pygame.draw.rect(canvas, (6, 5, 5), (0, 0, WIDTH, BAR - 62))
        pygame.draw.rect(canvas, (6, 5, 5), (0, HEIGHT - BAR, WIDTH, BAR))
        seconds = START_HOUR * 3600 + scene["t"] * STEP_SECONDS
        clock = self.font_small.render(f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}", True, (196, 188, 172))
        canvas.blit(clock, (28, HEIGHT - BAR + 30))
        title = self.font_title.render(scene["caption"], True, (250, 240, 216))
        canvas.blit(title, ((WIDTH - title.get_width()) // 2, HEIGHT - BAR + 16))
        hint = self.font_small.render(self.hint_text(), True, (150, 142, 130))
        canvas.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - BAR + 46))
        pygame.draw.rect(canvas, (226, 170, 90), (0, HEIGHT - 4, int(WIDTH * min(1., self.elapsed / DURATION)), 4))

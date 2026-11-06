"""Pompeii map views and split-screen panels.

Two linked maps (city and region, switched with a key) and up to three side-by-side
panels showing individuals. The written thoughts are templates built only from values
the model computed: what a person heard, their danger belief and their action. They are
labelled as illustration on screen and invent no feelings or motives.
"""
import random

import pygame

from engine.citizens import ROLE_COLORS, ROLE_NAMES
from engine.eruption import START_HOUR, STEP_MINUTES

MAP_SIZE, GRID_DIM = 900, 40
TILE = MAP_SIZE / GRID_DIM
CITY_COLORS = {0: (92, 104, 76), 1: (206, 192, 164), 2: (112, 142, 84), 3: (120, 110, 100), 4: (160, 88, 62)}
WALL = (66, 56, 48)
SEA = (44, 88, 122)
REGION_COLORS = {1: (178, 170, 128), 2: (118, 148, 92), 3: (106, 96, 88), 4: (160, 88, 62)}
FLOW = (214, 204, 192)
PANEL_BG, PANEL_LINE = (250, 239, 212), (106, 64, 28)
INK, MUTED = (54, 32, 14), (108, 72, 36)
PANEL_ROLES_DEFAULT = 3


def clock_text(t):
    minutes = START_HOUR * 60 + t * STEP_MINUTES
    day = 1 + minutes // (24 * 60)
    return f"Day {day} {minutes // 60 % 24:02d}:{minutes % 60:02d}"


def danger_phrase(p_danger):
    """Plain words for the mind's own belief value. Nothing is added to it."""
    if p_danger is None:
        return "No belief value for this mind."
    if p_danger < .35:
        return "Belief leans safe."
    if p_danger < .7:
        return "Belief is unsure."
    return "Belief leans to danger."


def thought_text(person, record):
    """A sentence built only from model values: what was heard, belief, action. No invented motives."""
    if not person.is_alive:
        return f"Died: {str(person.cause_of_death).replace('_', ' ')}."
    if person.status == "escaped":
        return "Reached a road out of the region."
    if record is None:
        return "Not yet recorded."
    quantum = record.get("quantum") or {}
    parts = []
    if record.get("story") and record["story"] != "Nothing new":
        parts.append(f"{record['story']}.")
    else:
        parts.append("Has noticed nothing new.")
    parts.append(danger_phrase(quantum.get("p_danger")))
    parts.append(f"{record['action_label']}.")
    return " ".join(parts)


def wrap(text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


class SplitPanels:
    """Up to three people side by side. Default: seeded random people from different roles, never hand-picked."""

    def __init__(self, sim, count=PANEL_ROLES_DEFAULT):
        self.sim = sim
        rng = random.Random(sim.seed + 31)
        roles = list(ROLE_NAMES)
        rng.shuffle(roles)
        self.people = []
        for role in roles:
            if len(self.people) == count:
                break
            options = [p for p in sim.people if p.role == role]
            self.people.append(rng.choice(options))
        for person in self.people:
            sim.watch(person)
        self.next_slot = 0

    def replace(self, person):
        """A clicked person takes the next slot in turn."""
        self.people[self.next_slot] = person
        self.sim.watch(person)
        self.next_slot = (self.next_slot + 1) % len(self.people)

    def draw(self, surface, x, y, width, height, fonts):
        gap = 10
        panel_h = (height - gap * (len(self.people) - 1)) // len(self.people)
        for i, person in enumerate(self.people):
            self._draw_panel(surface, person, x, y + i * (panel_h + gap), width, panel_h, fonts)

    def _draw_panel(self, surface, person, x, y, width, height, fonts):
        title, body, small = fonts
        pygame.draw.rect(surface, PANEL_BG, (x, y, width, height), border_radius=8)
        pygame.draw.rect(surface, PANEL_LINE, (x, y, width, height), 2, border_radius=8)
        pygame.draw.circle(surface, ROLE_COLORS[person.role], (x + 22, y + 22), 9)
        pygame.draw.circle(surface, INK, (x + 22, y + 22), 9, 1)
        surface.blit(title.render(person.label, True, INK), (x + 40, y + 12))
        log = self.sim.logs.get(person.id) or []
        record = log[-1] if log else None
        where = {"city": "In town", "road": "On the roads", "escaped": "Escaped"}[person.status]
        if not person.is_alive:
            where = "Dead"
        surface.blit(small.render(where, True, MUTED), (x + width - 110, y + 16))
        row = y + 44
        events = [e.replace("_", " ") for e in person.recent_events if e != "none"] or ["none"]
        surface.blit(small.render("Mind inputs, in order: " + " > ".join(events), True, MUTED), (x + 16, row))
        row += 22
        quantum = (record or {}).get("quantum") or {}
        if quantum:
            values = (f"Danger belief {quantum.get('p_danger', 0):.2f}    P(protect) {quantum.get('p_protect', 0):.2f}"
                      f"    Stress {person.stress:.2f}")
        else:
            values = f"Stress {person.stress:.2f}"
        surface.blit(small.render(values, True, INK), (x + 16, row))
        row += 22
        if height > 110 and record:
            bar_w = width - 32
            for action, value in sorted(record["probs"].items(), key=lambda item: -item[1])[:2]:
                pygame.draw.rect(surface, (234, 216, 178), (x + 16, row, bar_w, 14), border_radius=3)
                pygame.draw.rect(surface, (146, 58, 196), (x + 16, row, int(bar_w * min(1., value)), 14), border_radius=3)
                surface.blit(small.render(f"{action} {value:.0%}", True, INK), (x + 22, row))
                row += 18
        row += 4
        for line in wrap(thought_text(person, record), body, width - 32)[:3]:
            surface.blit(body.render(line, True, INK), (x + 16, row))
            row += 19
        surface.blit(small.render("Illustration, written from model values", True, MUTED), (x + 16, y + height - 20))


class CityView:
    """The city map and region map, with everyone drawn on whichever map they are on."""

    def __init__(self, app):
        self.app = app
        self.show_region = False
        self.font, self.font_sub = app.font_small, app.font_sub
        self.region_surface = self._build_region(app.engine.region)
        self.city_surface = None
        self._city_fingerprint = None

    def toggle(self):
        self.show_region = not self.show_region

    @staticmethod
    def _build_region(region):
        surface = pygame.Surface((MAP_SIZE, MAP_SIZE))
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = region.get_tile(x, y)
                color = REGION_COLORS.get(tile, SEA)
                pygame.draw.rect(surface, color, (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))
        vx, vy = region.vent
        pygame.draw.circle(surface, (60, 40, 36), (int((vx + .5) * TILE), int((vy + .5) * TILE)), 16)
        pygame.draw.circle(surface, (220, 90, 40), (int((vx + .5) * TILE), int((vy + .5) * TILE)), 7)
        return surface

    def _build_city(self, world):
        surface = pygame.Surface((MAP_SIZE, MAP_SIZE))
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = world.get_tile(x, y)
                color = CITY_COLORS.get(tile, CITY_COLORS[0])
                if (x, y) in world.wall_tiles and not tile:
                    color = WALL
                pygame.draw.rect(surface, color, (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))
        return surface

    def person_xy(self, person):
        jx = ((person.id * 7919) % 19 - 9) * 1.
        jy = ((person.id * 104729) % 19 - 9) * 1.
        x, y = person.pos
        return (x + .5) * TILE + jx, (y + .5) * TILE + jy

    def focus_xy(self, engine):
        return self.person_xy(engine.agent)

    def _overlay(self, canvas, tiles, color, alpha):
        layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
        for x, y in tiles:
            pygame.draw.rect(layer, (*color, alpha), (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))
        canvas.blit(layer, (0, 0))

    def _ash_tint(self, canvas, amount):
        if amount > 0:
            layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            layer.fill((196, 188, 170, int(150 * min(1., amount))))
            canvas.blit(layer, (0, 0))

    def draw(self, app):
        canvas, engine = app.canvas, app.engine
        t = max(0, app.step_idx - 1)
        hazard = engine.eruption.hazard_by_step[t]
        if self.show_region:
            canvas.blit(self.region_surface, (0, 0))
            self._draw_region_ash(canvas, hazard)
            self._overlay(canvas, map(tuple, hazard["region_active_pdc"]), FLOW, 200)
            self._draw_people(canvas, engine, "road")
        else:
            fingerprint = sum(map(sum, engine.world.tiles))
            if fingerprint != self._city_fingerprint:
                self.city_surface = self._build_city(engine.world)
                self._city_fingerprint = fingerprint
            canvas.blit(self.city_surface, (0, 0))
            self._ash_tint(canvas, hazard["ash"])
            self._overlay(canvas, map(tuple, hazard["active_pdc"]), FLOW, 215)
            self._draw_people(canvas, engine, "city")
            self._draw_gate_labels(canvas, engine.world)
        self._draw_header(canvas, app, t)
        if app.show_evacuation_map:
            self._draw_legend(canvas, engine)

    def _draw_region_ash(self, canvas, hazard):
        layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
        for y, row in enumerate(hazard["region_ash_grid"]):
            for x, digit in enumerate(row):
                if digit != "0":
                    pygame.draw.rect(layer, (196, 188, 170, int(digit) * 16),
                                     (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))
        canvas.blit(layer, (0, 0))

    def _draw_people(self, canvas, engine, status):
        for person in engine.people:
            if person.is_alive and person.status == status:
                x, y = self.person_xy(person)
                canvas.fill(ROLE_COLORS[person.role], (int(x), int(y), 2, 2))

    def _draw_gate_labels(self, canvas, world):
        for name, (x, y) in world.gates.items():
            pygame.draw.rect(canvas, (250, 214, 96), (round(x * TILE), round(y * TILE), TILE, TILE), 2)
            canvas.blit(self.font.render(name.capitalize(), True, (255, 248, 224)), (x * TILE + 2, y * TILE + 4))

    def _draw_header(self, canvas, app, t):
        engine = app.engine
        counts = engine.counts()
        hazard = engine.eruption.hazard_by_step[t]
        band = pygame.Surface((MAP_SIZE, 48), pygame.SRCALPHA)
        band.fill((20, 14, 12, 190))
        canvas.blit(band, (0, 52))
        map_name = "REGION" if self.show_region else "CITY"
        text = (f"{clock_text(t)}  {engine.eruption.phases[t].replace('_', ' ').upper()}  {map_name}   "
                f"Town {counts['in_town']}   Roads {counts['on_roads']}   Escaped {counts['escaped']}   "
                f"Dead {counts['dead']}   Pumice {hazard['pumice_m']:.1f} m")
        canvas.blit(self.font_sub.render(text, True, (246, 240, 226)), (14, 56))
        mapping = engine.event_mapping
        line = (f"Following {engine.agent.label}.  Click a person to follow them.  M region map, P panels, "
                f"Scenes replay at the end.  Event mapping {mapping}.")
        canvas.blit(self.font.render(line, True, (214, 204, 186)), (14, 78))

    def _draw_legend(self, canvas, engine):
        x, y = 12, MAP_SIZE - 26
        for role, name in ROLE_NAMES.items():
            count = sum(p.role == role for p in engine.people)
            pygame.draw.circle(canvas, ROLE_COLORS[role], (x + 5, y + 8), 4)
            label = self.font.render(f"{name} {count:,}", True, (240, 234, 220))
            canvas.blit(label, (x + 13, y + 1))
            x += label.get_width() + 22

    def pick_person(self, engine, pos):
        """Nearest living person on the map being shown, or None if nobody is close."""
        status = "road" if self.show_region else "city"
        best, best_distance = None, 14.
        for person in engine.people:
            if person.is_alive and person.status == status:
                x, y = self.person_xy(person)
                distance = (x - pos[0]) ** 2 + (y - pos[1]) ** 2
                if distance < best_distance ** 2:
                    best, best_distance = person, distance ** .5
        return best


def next_role_citizen(engine):
    """The next role's first living person who has not escaped; used by the F key."""
    roles = list(ROLE_NAMES)
    start = roles.index(engine.agent.role)
    for offset in range(1, len(roles) + 1):
        role = roles[(start + offset) % len(roles)]
        for person in engine.people:
            if person.role == role and person.is_alive and person.status != "escaped":
                return person
    return engine.agent


def mini_map(world, size):
    surface = pygame.Surface((size, size))
    tile = size / GRID_DIM
    for y in range(GRID_DIM):
        for x in range(GRID_DIM):
            color = CITY_COLORS.get(world.get_tile(x, y), CITY_COLORS[0])
            if (x, y) in world.wall_tiles and not world.get_tile(x, y):
                color = WALL
            pygame.draw.rect(surface, color, (int(x * tile), int(y * tile), tile + 1, tile + 1))
    return surface

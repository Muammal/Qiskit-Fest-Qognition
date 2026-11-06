"""Waterloo map view and split-screen panels.

One 40x40 site map with a chlorine overlay. The written thoughts are templates built only from values the
model computed: what a person noticed, their danger belief, their action and the gas where they stand.
They are labelled as illustration on screen and invent no feelings or motives.
"""

import random

import pygame

from engine.chlorine import AEGL_MEANING, START_HOUR, STEP_SECONDS, exposure_level
from engine.gui_city import INK, MAP_SIZE, MUTED, PANEL_BG, PANEL_LINE, TILE, GRID_DIM, SplitPanels, danger_phrase, wrap
from engine.patrons import ROLE_COLORS, ROLE_NAMES

GRASS, ROAD, PARKING, WALL = (176, 202, 146), (150, 148, 142), (172, 172, 188), (58, 52, 46)
FLOOR, POOL, DECK, CREEK = (232, 222, 200), (92, 182, 232), (224, 214, 188), (42, 92, 170)
AREA_COLORS = dict(ice_pad=(206, 234, 248), lobby=(244, 206, 152), community_room=(234, 182, 190), change_rooms=(202, 192, 238))
GAS = (168, 214, 40)
GAS_FULL_PPM = 10.0  # display only: the overlay is fully opaque from here up, at NIOSH's IDLH


def clock_text(t):
    seconds = START_HOUR * 3600 + t * STEP_SECONDS
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def thought_text(person, record, ppm):
    """A sentence built only from model values. No invented motives."""
    if person.status == "out":
        return "Has left the site."
    if record is None:
        cues = [e.replace("_", " ") for e in person.recent_events if e != "none"]
        heard = f"Has noticed: {', '.join(cues)}." if cues else "Has noticed nothing yet."
        return f"{heard} No decision yet. Gas here: {ppm:.2f} ppm."
    quantum = record.get("quantum") or {}
    story = record.get("story")
    parts = [f"{story}." if story and story != "Nothing new" else "Has noticed nothing new."]
    parts.append(danger_phrase(quantum.get("p_danger")))
    parts.append(f"{record['action_label']}.")
    parts.append(f"Gas here: {ppm:.2f} ppm.")
    return " ".join(parts)


class SitePanels(SplitPanels):
    """Up to three people side by side: seeded random people from different roles, never hand-picked."""

    def __init__(self, sim, count=3):
        self.sim = sim
        rng = random.Random(sim.seed + 31)
        roles = list(ROLE_NAMES)
        rng.shuffle(roles)
        self.people = [rng.choice([p for p in sim.people if p.role == role]) for role in roles[:count]]
        for person in self.people:
            sim.watch(person)
        self.next_slot = 0

    def _draw_panel(self, surface, person, x, y, width, height, fonts):
        title, body, small = fonts
        pygame.draw.rect(surface, PANEL_BG, (x, y, width, height), border_radius=8)
        pygame.draw.rect(surface, PANEL_LINE, (x, y, width, height), 2, border_radius=8)
        pygame.draw.circle(surface, ROLE_COLORS[person.role], (x + 22, y + 22), 9)
        pygame.draw.circle(surface, INK, (x + 22, y + 22), 9, 1)
        surface.blit(title.render(person.label, True, INK), (x + 40, y + 12))
        log = self.sim.logs.get(person.id) or []
        record = log[-1] if log else None
        where = "Off the site" if person.status == "out" else "Indoors" if tuple(person.pos) in self.sim.world.areas["indoors"] else "Outdoors"
        surface.blit(small.render(where, True, MUTED), (x + width - 110, y + 16))
        row = y + 44
        events = [e.replace("_", " ") for e in person.recent_events if e != "none"] or ["none"]
        surface.blit(small.render("Mind inputs, in order: " + " > ".join(events), True, MUTED), (x + 16, row))
        row += 22
        quantum = (record or {}).get("quantum") or {}
        values = f"Stress {person.stress:.2f}"
        if quantum:
            values = f"Danger belief {quantum.get('p_danger', 0):.2f}    P(protect) {quantum.get('p_protect', 0):.2f}    " + values
        surface.blit(small.render(values, True, INK), (x + 16, row))
        row += 22
        if height > 110 and record:
            bar_w = width - 32
            for action, value in sorted(record["probs"].items(), key=lambda item: -item[1])[:2]:
                pygame.draw.rect(surface, (234, 216, 178), (x + 16, row, bar_w, 17), border_radius=3)
                pygame.draw.rect(surface, (182, 128, 214), (x + 16, row, int(bar_w * min(1.0, value)), 17), border_radius=3)
                surface.blit(small.render(f"{person.action_label(action)} {value:.0%}", True, INK), (x + 22, row))
                row += 20
        row += 4
        t = max(0, self.sim.t - 1)
        for line in wrap(thought_text(person, record, self.sim.chlorine.ppm_at(t, tuple(person.pos))), body, width - 32)[:3]:
            surface.blit(body.render(line, True, INK), (x + 16, row))
            row += 19
        level = AEGL_MEANING[exposure_level(person.exposure)]
        surface.blit(small.render(f"Exposure so far: {level}", True, INK), (x + 16, y + height - 40))
        surface.blit(small.render("Illustration, written from model values", True, MUTED), (x + 16, y + height - 20))


def _tile_color(world, x, y):
    p, areas = (x, y), world.areas
    if p in world.wall_tiles:
        return WALL
    if p in world.pool_tiles:
        return POOL
    if p in areas["pool_deck"]:
        return DECK
    if p in areas["indoors"]:
        return next((color for name, color in AREA_COLORS.items() if p in areas[name]), FLOOR)
    if p in world.nearby_building_tiles:
        return (118, 108, 98)
    if p in world.creek_tiles:
        return CREEK
    if p in areas["parking_north"] or p in areas["parking_south"]:
        return PARKING
    return ROAD if p in world.road_tiles else GRASS


class SiteView:
    """The site, the gas and everyone still on it."""

    def __init__(self, app):
        self.app = app
        self.show_region = False  # the shared GUI code asks; this scenario has one map
        self.font, self.font_sub = app.font_small, app.font_sub
        self.surface = pygame.Surface((MAP_SIZE, MAP_SIZE))
        world = app.engine.world
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                pygame.draw.rect(self.surface, _tile_color(world, x, y), (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))

    def toggle(self):
        pass

    def person_xy(self, person):
        jx = ((person.id * 7919) % 15 - 7) * 1.0
        jy = ((person.id * 104729) % 15 - 7) * 1.0
        x, y = person.pos
        return (x + 0.5) * TILE + jx, (y + 0.5) * TILE + jy

    def focus_xy(self, engine):
        return self.person_xy(engine.agent)

    def draw(self, app):
        canvas, engine = app.canvas, app.engine
        t = max(0, app.step_idx - 1)
        canvas.blit(self.surface, (0, 0))
        self._draw_gas(canvas, engine.chlorine.ppm[t])
        self._draw_labels(canvas, engine)
        for person in engine.people:
            if person.status == "site":
                x, y = self.person_xy(person)
                pygame.draw.circle(canvas, ROLE_COLORS[person.role], (int(x), int(y)), 4)
                pygame.draw.circle(canvas, INK, (int(x), int(y)), 4, 1)
        self._draw_header(canvas, app, t)
        if app.show_evacuation_map:
            self._draw_legend(canvas, engine)

    def _draw_gas(self, canvas, grid):
        layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                ppm = float(grid[y, x])
                if ppm >= 0.05:  # display only: below this the overlay would be invisible
                    alpha = int(50 + 180 * min(1.0, ppm / GAS_FULL_PPM))
                    pygame.draw.rect(layer, (*GAS, alpha), (round(x * TILE), round(y * TILE), TILE + 1, TILE + 1))
        canvas.blit(layer, (0, 0))

    def _draw_labels(self, canvas, engine):
        world = engine.world
        for x, y in world.doors.values():
            pygame.draw.rect(canvas, (226, 44, 40), (round(x * TILE), round(y * TILE), TILE, TILE))
        for x, y in world.gates.values():
            pygame.draw.rect(canvas, (240, 150, 20), (round(x * TILE), round(y * TILE), TILE, TILE))
        for x, y in world.exits.values():
            pygame.draw.rect(canvas, (24, 170, 64), (round(x * TILE), round(y * TILE), TILE, TILE))
        x, y = engine.chlorine.source
        pygame.draw.rect(canvas, (20, 20, 20), (round(x * TILE), round(y * TILE), TILE, TILE), 3)

    def _draw_header(self, canvas, app, t):
        engine = app.engine
        counts = engine.counts()
        band = pygame.Surface((MAP_SIZE, 48), pygame.SRCALPHA)
        band.fill((20, 14, 12, 190))
        canvas.blit(band, (0, 52))
        text = (
            f"{clock_text(t)}  {engine.chlorine.phases[t].upper()}   On site {counts['on_site']}   Off site {counts['off_site']}   "
            f"Know {counts['knows']}   Alarm {'on' if engine.alarm_step is not None and t >= engine.alarm_step else 'off'}   "
            f"Highest gas {engine.chlorine.hazard_by_step[t]['peak_ppm']:.1f} ppm"
        )
        canvas.blit(self.font_sub.render(text, True, (246, 240, 226)), (14, 56))
        line = (
            f"Following {engine.agent.label}.  Click a person to follow them.  P panels.  "
            f"Mapping {engine.event_mapping}.  Green is chlorine, black box is the assumed leak."
        )
        canvas.blit(self.font.render(line, True, (214, 204, 186)), (14, 78))

    def _draw_legend(self, canvas, engine):
        x, y = 12, MAP_SIZE - 26
        band = pygame.Surface((MAP_SIZE, 26), pygame.SRCALPHA)
        band.fill((20, 14, 12, 170))
        canvas.blit(band, (0, y))
        for role, name in ROLE_NAMES.items():
            count = sum(p.role == role for p in engine.people)
            pygame.draw.circle(canvas, ROLE_COLORS[role], (x + 5, y + 12), 4)
            label = self.font.render(f"{name} {count}", True, (240, 234, 220))
            canvas.blit(label, (x + 13, y + 5))
            x += label.get_width() + 22

    def pick_person(self, engine, pos):
        best, best_distance = None, 14.0
        for person in engine.people:
            if person.status == "site":
                x, y = self.person_xy(person)
                distance = ((x - pos[0]) ** 2 + (y - pos[1]) ** 2) ** 0.5
                if distance < best_distance:
                    best, best_distance = person, distance
        return best


def next_role_patron(engine):
    """The next role's first person still on site; used by the F key."""
    roles = list(ROLE_NAMES)
    start = roles.index(engine.agent.role)
    for offset in range(1, len(roles) + 1):
        role = roles[(start + offset) % len(roles)]
        for person in engine.people:
            if person.role == role and person.status == "site":
                return person
    return engine.agent


def mini_map(world, size):
    surface = pygame.Surface((size, size))
    tile = size / GRID_DIM
    for y in range(GRID_DIM):
        for x in range(GRID_DIM):
            pygame.draw.rect(surface, _tile_color(world, x, y), (int(x * tile), int(y * tile), tile + 1, tile + 1))
    return surface

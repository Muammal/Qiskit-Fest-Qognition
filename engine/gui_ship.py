"""Side-cutaway map view of the ship and everyone aboard, for the Titanic scenario."""
import math
import time

import pygame

from engine.crowd import ROLE_COLORS, ROLE_NAMES
from engine.flood import water_row_at
from engine.ship import BOAT, BULKHEADS, DECK_ROWS, DECK_SPANS, WATERLINE_ROW

MAP_SIZE, GRID_DIM = 900, 40
TILE = MAP_SIZE / GRID_DIM
SKY_TOP, SKY_LOW = (6, 10, 28), (22, 34, 66)
SEA_TOP, SEA_LOW = (24, 62, 104), (6, 20, 44)
HULL, HULL_RED = (20, 22, 28), (120, 38, 30)
CABIN = {1: (178, 142, 92), 3: (92, 84, 78), 4: (226, 214, 186)}
STEEL = (64, 70, 80)
SURFACE_AFTER_SINKING = 13.  # assumption: row of the calm sea drawn once the ship has gone
BOAT_ROW_OUT_STEPS = 12  # display only: an hour for a boat to reach its spot on the map


def _lerp(a, b, f):
    return tuple(int(x + (y - x) * f) for x, y in zip(a, b))


def build_ship_surface(world, size=MAP_SIZE):
    """The hull, decks, stairs and funnels. Static, so it is drawn once and cached."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    tile = size / GRID_DIM

    def rect(x, y, w=1., h=1.):
        return pygame.Rect(round(x * tile), round(y * tile), math.ceil(w * tile), math.ceil(h * tile))

    # Funnels and masts rise behind the superstructure.
    for x in (12.5, 17, 21.5, 26):
        pygame.draw.polygon(surface, (196, 124, 46), [(x * tile, 9.4 * tile), ((x + 1.6) * tile, 9.4 * tile),
                                                      ((x + 1.2) * tile, 4.2 * tile), ((x - .4) * tile, 4.2 * tile)])
        pygame.draw.polygon(surface, (18, 18, 22), [((x + 1.27) * tile, 5.4 * tile), ((x - .27) * tile, 5.4 * tile),
                                                    ((x - .4) * tile, 4.2 * tile), ((x + 1.2) * tile, 4.2 * tile)])
    for x, height in ((5, 3.5), (34, 3)):
        pygame.draw.line(surface, (120, 104, 84), (x * tile, height * tile), (x * tile, 15.6 * tile), max(1, int(tile / 8)))

    hull = [(0.8, 15.6), (39.2, 15.6), (38.8, 21.5), (37.6, 25), (35.5, 27.8), (5, 27.8), (2.2, 25), (1, 21)]
    pygame.draw.polygon(surface, HULL, [(x * tile, y * tile) for x, y in hull])
    red = [(p[0], max(p[1], WATERLINE_ROW + .3)) for p in hull]
    pygame.draw.polygon(surface, HULL_RED, [(x * tile, y * tile) for x, y in red])
    upper = [(6, 13.6), (34, 13.6), (34, 15.7), (6, 15.7)]
    pygame.draw.polygon(surface, (232, 228, 214), [(x * tile, y * tile) for x, y in upper])
    pygame.draw.rect(surface, (238, 234, 222), rect(8.8, 9.6, 23.4, 4.2))

    for y, (start, end) in DECK_SPANS.items():
        for x in range(start, end + 1):
            kind = world.get_tile(x, y)
            if kind:
                pygame.draw.rect(surface, CABIN[kind], rect(x, y))
        pygame.draw.line(surface, STEEL, (start * tile, (y + 1) * tile), ((end + 1) * tile, (y + 1) * tile), 1)
    for y in range(world.height):
        for x in range(world.width):
            if world.get_tile(x, y) == 3:
                r = rect(x, y)
                pygame.draw.rect(surface, CABIN[3], r)
                for i in range(0, r.height, max(2, r.height // 4)):
                    pygame.draw.line(surface, (150, 142, 128), (r.x, r.y + i), (r.right, r.y + i), 1)
    for x in BULKHEADS:
        pygame.draw.line(surface, (150, 60, 50), (x * tile, 20 * tile), (x * tile, 27.6 * tile), 1)
    return surface


class ShipView:
    def __init__(self, app):
        self.world = app.world
        self.ship = build_ship_surface(self.world)
        self.sky = pygame.Surface((MAP_SIZE, MAP_SIZE))
        for y in range(MAP_SIZE):
            pygame.draw.line(self.sky, _lerp(SKY_TOP, SKY_LOW, y / MAP_SIZE), (0, y), (MAP_SIZE, y))
        for i in range(140):
            pygame.draw.circle(self.sky, (200, 210, 235), ((i * 149) % MAP_SIZE, 50 + (i * 83) % 420), 1)
        self.flood_layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
        self.flood_count = -1
        self.font = app.font_small
        self.font_sub = app.font_sub

    def surface_row(self, x, engine, t):
        if t >= engine.flood.sink_step:
            return SURFACE_AFTER_SINKING
        bow, stern = engine.flood.hazard_by_step[t]["waterline"]
        return max(3.2, water_row_at(x, bow, stern))

    def person_xy(self, person, engine, t):
        """Screen position, jittered by id so a crowd on one tile spreads out."""
        jx = ((person.id * 7919) % 19 - 9) * .9
        jy = ((person.id * 104729) % 11 - 5) * .9
        x, y = person.pos
        if person.status == "aboard":
            return (x + .5) * TILE + jx, (y + .5) * TILE + jy
        if person.status == "water":
            return (x + .5) * TILE + jx * 2, (self.surface_row(x, engine, t) + .3) * TILE + abs(jy) * 2
        boat = self._boat_by_id(engine, person.boat_id)
        bx, by = self.boat_xy(boat, engine, t)
        return bx + jx, by - 4

    @staticmethod
    def _boat_by_id(engine, boat_id):
        return next(b for b in engine.boats.boats + engine.boats.floating if b.id == boat_id)

    def boat_xy(self, boat, engine, t):
        if boat.state in ("stowed", "loading"):
            return (boat.station[0] + .5) * TILE, (BOAT - .35) * TILE
        # Each boat rows from its station toward its own spot, so they spread across the sea.
        fleet = engine.boats.boats + engine.boats.floating
        index = fleet.index(boat)
        spot = 1.5 + index * 36 / (len(fleet) - 1)
        progress = min(1., max(0, t - boat.launch_step) / BOAT_ROW_OUT_STEPS)
        x = boat.station[0] + (spot - boat.station[0]) * progress
        row = self.surface_row(x, engine, t)
        return (x + .5) * TILE, (row + .1) * TILE + (index % 3) * 22 * progress

    def focus_xy(self, engine):
        return self.person_xy(engine.agent, engine, max(0, engine.t - 1))

    def _refresh_flood(self, world):
        if len(world.flooded) == self.flood_count:
            return
        self.flood_count = len(world.flooded)
        self.flood_layer.fill((0, 0, 0, 0))
        for x, y in world.flooded:
            pygame.draw.rect(self.flood_layer, (34, 110, 190, 215),
                             (round(x * TILE), round(y * TILE), math.ceil(TILE), math.ceil(TILE)))

    def draw(self, app):
        canvas, engine = app.canvas, app.engine
        t = max(0, app.step_idx - 1)
        canvas.blit(self.sky, (0, 0))
        sunk = t >= engine.flood.sink_step
        if not sunk:
            canvas.blit(self.ship, (0, 0))
            self._refresh_flood(engine.world)
            canvas.blit(self.flood_layer, (0, 0))
            self._draw_stowed_boats(canvas, engine)
        self._draw_sea(canvas, engine, t)
        self._draw_people(canvas, engine, t)
        self._draw_lowered_boats(canvas, engine, t)
        self._draw_header(canvas, app, t)
        if app.show_evacuation_map:
            self._draw_legend(canvas, engine)

    def _draw_sea(self, canvas, engine, t):
        phase = time.time() * 2
        points = []
        for px in range(0, MAP_SIZE + 30, 30):
            wave = math.sin(px * .03 + phase) * 2
            points.append((px, self.surface_row(px / TILE, engine, t) * TILE + wave))
        layer = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (*SEA_TOP, 150), points + [(MAP_SIZE, MAP_SIZE), (0, MAP_SIZE)])
        canvas.blit(layer, (0, 0))
        pygame.draw.lines(canvas, (170, 210, 235), False, points, 2)

    def _draw_stowed_boats(self, canvas, engine):
        for boat in engine.boats.boats + engine.boats.floating:
            if boat.state in ("stowed", "loading"):
                x, y = self.boat_xy(boat, engine, 0)
                offset = -3 if boat.side == "starboard" else 3
                color = (250, 248, 238) if boat.state == "stowed" else (255, 214, 96)
                pygame.draw.ellipse(canvas, color, (x - 9, y - 4 + offset, 18, 7))
                pygame.draw.ellipse(canvas, (40, 40, 44), (x - 9, y - 4 + offset, 18, 7), 1)

    def _draw_lowered_boats(self, canvas, engine, t):
        for boat in engine.boats.boats + engine.boats.floating:
            if boat.state in ("lowered", "floated"):
                x, y = self.boat_xy(boat, engine, t)
                pygame.draw.ellipse(canvas, (250, 248, 238), (x - 13, y - 4, 26, 9))
                pygame.draw.ellipse(canvas, (30, 34, 44), (x - 13, y - 4, 26, 9), 1)
                label = self.font.render(f"#{boat.id} ({len(boat.aboard)})", True, (255, 244, 200))
                canvas.blit(label, (x - label.get_width() / 2, y + 6))

    def _draw_people(self, canvas, engine, t):
        for person in engine.people:
            if not person.is_alive or person.status == "boat":
                continue
            x, y = self.person_xy(person, engine, t)
            pygame.draw.circle(canvas, ROLE_COLORS[person.role], (int(x), int(y)), 2)

    def _draw_header(self, canvas, app, t):
        engine = app.engine
        focus = engine.agent
        counts = engine.counts()
        minutes = 23 * 60 + 30 + t * 5
        clock = f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"
        phase = engine.flood.phases[t].upper()
        text = (f"{clock}  {phase}   Aboard {counts['aboard']}   In boats {counts['boats']}   "
                f"In water {counts['water']}   Dead {counts['dead']}")
        band = pygame.Surface((MAP_SIZE, 48), pygame.SRCALPHA)
        band.fill((6, 12, 30, 190))
        canvas.blit(band, (0, 52))
        canvas.blit(self.font_sub.render(text, True, (240, 244, 255)), (14, 56))
        state = {"boat": "in a lifeboat", "water": "in the water"}.get(focus.status, "aboard")
        if not focus.is_alive:
            state = f"dead ({focus.cause_of_death})"
        line = f"Following {focus.label}: {state}.  Click a person to follow them, F for the next role.  Scenes replay at the end."
        canvas.blit(self.font.render(line, True, (196, 208, 232)), (14, 78))

    def _draw_legend(self, canvas, engine):
        roles = [(role, sum(p.role == role for p in engine.people)) for role in ROLE_NAMES]
        x, y = 12, MAP_SIZE - 28
        for role, count in roles:
            pygame.draw.circle(canvas, ROLE_COLORS[role], (x + 5, y + 8), 4)
            label = self.font.render(f"{ROLE_NAMES[role]} {count}", True, (226, 232, 246))
            canvas.blit(label, (x + 13, y + 1))
            x += label.get_width() + 26
        for name, row in DECK_ROWS.items():
            canvas.blit(self.font.render(name.upper(), True, (160, 176, 204)), (2, row * TILE + 3))

    def pick_person(self, engine, pos, t):
        """Nearest living person to a map click, or None if nobody is close."""
        best, best_distance = None, 14.
        for person in engine.people:
            if not person.is_alive:
                continue
            x, y = self.person_xy(person, engine, t)
            distance = math.hypot(x - pos[0], y - pos[1])
            if distance < best_distance:
                best, best_distance = person, distance
        return best


def next_role_person(engine):
    """The next role's first living person; used by the F key."""
    roles = list(ROLE_NAMES)
    start = roles.index(engine.agent.role)
    for offset in range(1, len(roles) + 1):
        role = roles[(start + offset) % len(roles)]
        for person in engine.people:
            if person.role == role and person.is_alive:
                return person
    return engine.agent


def mini_map(world, size):
    surface = pygame.Surface((size, size))
    surface.fill(SEA_LOW)
    surface.blit(build_ship_surface(world, size), (0, 0))
    return surface

"""Dual-scenario island world geography:
- Volcano Evacuation Scenario (fixed 40x40 topography with evacuation zoning, 250m scale)
- Island Wilderness Survival Scenario (procedural island generation per seed)
"""
import math
import random
from collections import deque

MAP_SEED = 42  # assumption: shared scenario terrain seed
SCALE_M_PER_TILE = 250  # assumption: scenario spatial scale


class IslandWorld:
    def __init__(self, width=40, height=40, seed=MAP_SEED, scenario="volcano"):
        self.width, self.height, self.seed = width, height, seed
        self.scenario = scenario
        rng = random.Random(seed)
        cx, cy = width // 2, height // 2
        self.vent = (cx, cy)
        self.tiles = [[0] * width for _ in range(height)]

        if scenario == "island":
            # Procedural Wilderness Island Generation
            max_radius = 16.0
            for y in range(height):
                for x in range(width):
                    dist = math.hypot(x - cx, y - cy)
                    noise = (
                        math.sin(x * 0.4 + seed % 10) * 1.8 +
                        math.cos(y * 0.4 + seed % 7) * 1.8 +
                        math.sin((x + y) * 0.3) * 1.2
                    )
                    effective_dist = dist + noise
                    if effective_dist > max_radius:
                        self.tiles[y][x] = 0
                    elif effective_dist > max_radius - 3.5:
                        self.tiles[y][x] = 1
                    elif effective_dist > max_radius - 8.5:
                        self.tiles[y][x] = 2
                    else:
                        self.tiles[y][x] = 3 if rng.random() > 0.35 else 2

            self.valleys = [[self.vent]]
            self.stream_tiles = []
            stream_x, stream_y = int(cx), int(cy)
            stream_dir = rng.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
            for _ in range(15):
                if 0 <= stream_x < self.width and 0 <= stream_y < self.height:
                    self.tiles[stream_y][stream_x] = 0
                    self.stream_tiles.append((stream_x, stream_y))
                stream_x += stream_dir[0] + rng.choice([0, rng.choice([-1, 1])])
                stream_y += stream_dir[1] + rng.choice([0, rng.choice([-1, 1])])

            self.clean_springs = list(self.stream_tiles[:3]) if self.stream_tiles else [(cx, cy)]
            self.freshwater_tiles = self.stream_tiles + self.clean_springs

            candidates = []
            for y in range(8, height - 8):
                for x in range(8, width - 8):
                    if self.tiles[y][x] == 1:
                        candidates.append([x, y])
            self.spawn_pos = rng.choice(candidates) if candidates else [cx, cy + 4]
            self.food_tiles = [(x, y) for y in range(height) for x in range(width)
                               if self.tiles[y][x] == 2 and rng.random() < 0.3]
            if self.tiles[self.spawn_pos[1]][self.spawn_pos[0]] == 2:
                self.food_tiles.append(tuple(self.spawn_pos))
            self.shelter_tiles = []
            self.lava, self.pdc, self.lahar = set(), set(), set()
            self.ash = 0.0
            self.volcanic_sign_seen = False
            self.zones = [[0 for _ in range(width)] for _ in range(height)]
            self.pdc_footprint = set()
            self.lahar_footprint = set()
            self.assembly_points = [(cx - 9, cy + 7)]
            self.route_from_spawn = self.path(self.spawn_pos, self.assembly_points)

        else:
            # Fixed Volcano Geography Scenario
            # assumption: angular coast harmonics make bays/headlands; terrain edges are noisy.
            for y in range(height):
                for x in range(width):
                    angle = math.atan2(y - cy, x - cx)
                    r = math.hypot((x - cx) / width, (y - cy) / height)
                    coast = .40 + .065 * math.sin(3 * angle + .7) + .045 * math.sin(7 * angle + seed)
                    noise = .018 * math.sin(.7 * x + .3 * y) + .012 * math.cos(.5 * y - .4 * x)
                    if r < coast:
                        self.tiles[y][x] = 3 if r < .12 + noise else (2 if r < coast - .065 + noise else 1)
            # assumption: three radial drainage valleys, cardinal connected, with bends.
            self.valleys = []
            for direction in (math.pi / 2, -.55, 3.6):
                valley = [self.vent]
                for distance in range(1, max(width, height)):
                    bend = .28 * math.sin(distance * .55)
                    target = (round(cx + distance * math.cos(direction + bend)),
                              round(cy + distance * math.sin(direction + bend)))
                    while valley[-1] != target:
                        x, y = valley[-1]
                        q = (x + (1 if target[0] > x else -1), y) if x != target[0] else (x, y + (1 if target[1] > y else -1))
                        if not self.get_tile(*q):
                            break
                        valley.append(q)
                    if valley[-1] != target:
                        break
                self.valleys.append(valley)
            self.stream_tiles = self.valleys[0][1:]
            self.clean_springs = [(cx - 10, cy + 7)]
            self.freshwater_tiles = self.stream_tiles + self.clean_springs
            self.spawn_pos = [cx, cy + 4]
            self.tiles[cy + 4][cx] = 2
            self.food_tiles = [(x, y) for y in range(height) for x in range(width)
                               if self.tiles[y][x] == 2 and rng.random() < .3]
            self.food_tiles.append(tuple(self.spawn_pos))
            self.shelter_tiles = []
            self.lava, self.pdc, self.lahar = set(), set(), set()
            self.ash = 0.0
            self.volcanic_sign_seen = False
            self.zones = [[self._zone(x, y) for x in range(width)] for y in range(height)]
            # assumption: valley corridors are 500 m (PDC) and 250 m (lahar) wide per side.
            land = [(x, y) for y in range(height) for x in range(width) if self.get_tile(x, y)]
            self.pdc_footprint = {p for p in land if math.dist(p, self.vent) <= 4 or
                                  any(math.dist(p, q) <= 2 for q in self.stream_tiles)}
            self.lahar_footprint = {p for p in land if any(math.dist(p, q) <= 1 for q in self.stream_tiles)}
            self.assembly_points = [(cx - 9, cy + 7)]
            self.route_from_spawn = self.path(self.spawn_pos, self.assembly_points)

    def _zone(self, x, y):
        d = math.dist((x, y), self.vent)
        valley = min((math.dist((x, y), p) for valley in self.valleys for p in valley), default=100)
        return 2 if d <= 4 or valley <= 2 else (1 if d <= 7 or valley <= 4 else 0)

    def get_tile(self, x, y):
        return self.tiles[y][x] if 0 <= x < self.width and 0 <= y < self.height else 0

    def walkable(self, p):
        return self.get_tile(*p) != 0 and tuple(p) not in self.lava

    def path(self, start, goals, avoid_danger=False):
        start = tuple(start)
        goals = {tuple(p) for p in goals}
        queue, previous = deque([start]), {start: None}
        while queue:
            p = queue.popleft()
            if p in goals:
                route = []
                while p is not None:
                    route.append(p)
                    p = previous[p]
                return route[::-1]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (p[0] + dx, p[1] + dy)
                if q not in previous and self.walkable(q):
                    if avoid_danger and self.zones[q[1]][q[0]] == 2:
                        continue
                    previous[q] = p
                    queue.append(q)
        return []

    def set_shelter(self, x, y):
        if self.get_tile(x, y):
            self.tiles[y][x] = 4
            if (x, y) not in self.shelter_tiles:
                self.shelter_tiles.append((x, y))

    def is_near_water(self, x, y, radius=2):
        return any(math.dist((x, y), p) <= radius for p in self.freshwater_tiles
                   if p not in self.lava)

    def is_in_shelter(self, x, y):
        return self.get_tile(x, y) == 4

    def export_dict(self):
        return dict(width=self.width, height=self.height, tiles=self.tiles, seed=self.seed,
                    map_seed=self.seed, scenario=self.scenario, scale_m_per_tile=SCALE_M_PER_TILE,
                    evacuation_map=dict(zones=self.zones, assembly_points=[list(p) for p in self.assembly_points],
                                        route_from_spawn=[list(p) for p in self.route_from_spawn]))

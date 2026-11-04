"""Seeded terrain, priority-flood drainage and least walking-time routes.
Supports both Volcano Evacuation (default) and Island Wilderness scenarios.
"""
import copy
import heapq
import math
import random
from functools import lru_cache

MAP_SEED = 42  # assumption: shared terrain across event seeds
SCALE_M_PER_TILE = 250  # assumption: scenario resolution
NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))  # assumption: cardinal walking/routing
TERRAIN_SPEED = {0: 1, 1: 1, 2: .8, 3: .65, 4: 1}  # assumption: forest/mountain obstruction
SPAWN_MIN_VENT_TILES = 6  # assumption: 1.5 km from the vent
FOOD_VALLEY_TILES = 3  # assumption: moist valley bottoms reach 750 m from a main channel
FOOD_VALLEY_ELEVATION = (30, 650)  # assumption: metres; little grows on the upper cone or at the shore
FOOD_VALLEY_DENSITY = .45  # assumption: one-ration patches per valley tile
FOOD_UPLAND_DENSITY = .03  # assumption: one-ration patches per drier forest tile


class IslandWorld:
    def __init__(self, width=40, height=40, seed=MAP_SEED, scenario="volcano"):
        self.scenario = scenario
        if scenario == "island":
            self.__dict__.update(copy.deepcopy(_island_terrain(width, height, seed)))
        else:
            self.__dict__.update(copy.deepcopy(_terrain(width, height, seed)))
        self.scenario = scenario
        self.lava, self.pdc, self.lahar = set(), set(), set()
        self.active_pdc, self.active_lahar, self.surge = set(), set(), set()
        self.ash, self.ash_grid = 0., None
        self.volcanic_sign_seen = False
        self.shelter_tiles = []
        self.depleted_food = set()

    def neighbors(self, p):
        for dx, dy in NEIGHBORS:
            q = p[0] + dx, p[1] + dy
            if 0 <= q[0] < self.width and 0 <= q[1] < self.height:
                yield q

    def get_tile(self, x, y):
        return self.tiles[y][x] if 0 <= x < self.width and 0 <= y < self.height else 0

    def ash_at(self, x, y):
        return int(self.ash_grid[y][x]) / 9 if self.ash_grid is not None else self.ash

    def stream_ash(self):
        return sum(self.ash_at(*p) for p in self.stream_tiles) / max(1, len(self.stream_tiles))

    def walkable(self, p):
        p = tuple(p)
        return bool(self.get_tile(*p)) and p not in self.lava and p not in self.pdc

    def travel_minutes(self, a, b):
        slope = (self.elevation[b[1]][b[0]] - self.elevation[a[1]][a[0]]) / SCALE_M_PER_TILE
        speed = 6 * math.exp(-3.5 * abs(slope + .05)) * .6  # Tobler hiking function; off-path factor
        return .25 / speed * 60 / TERRAIN_SPEED[self.get_tile(*b)]

    def route_minutes(self, route):
        return sum(self.travel_minutes(a, b) for a, b in zip(route, route[1:])) if route else math.inf

    def path(self, start, goals, avoid_danger=False):
        start, goals = tuple(start), {tuple(p) for p in goals}
        queue, costs, previous = [(0., start)], {start: 0.}, {start: None}
        while queue:
            cost, p = heapq.heappop(queue)
            if cost != costs[p]:
                continue
            if p in goals:
                route = []
                while p is not None:
                    route.append(p)
                    p = previous[p]
                return route[::-1]
            for q in self.neighbors(p):
                if not self.walkable(q) or (avoid_danger and self.zones[q[1]][q[0]] == 2):
                    continue
                candidate = cost + self.travel_minutes(p, q)
                if candidate < costs.get(q, math.inf):
                    costs[q], previous[q] = candidate, p
                    heapq.heappush(queue, (candidate, q))
        return []

    def set_shelter(self, x, y):
        if self.get_tile(x, y):
            self.tiles[y][x] = 4
            if (x, y) not in self.shelter_tiles:
                self.shelter_tiles.append((x, y))

    def is_near_water(self, x, y, radius=2):
        return any(math.dist((x, y), p) <= radius for p in self.freshwater_tiles if p not in self.lava)

    def is_in_shelter(self, x, y):
        return self.get_tile(x, y) == 4

    def export_dict(self):
        return dict(
            width=self.width,
            height=self.height,
            tiles=self.tiles,
            seed=self.seed,
            map_seed=self.seed,
            scale_m_per_tile=SCALE_M_PER_TILE,
            elevation=[[round(v) for v in row] for row in self.elevation],
            evacuation_map=dict(
                zones=self.zones,
                assembly_points=[list(p) for p in self.assembly_points],
                route_from_spawn=[list(p) for p in self.route_from_spawn],
                routes_from_spawn=[[list(p) for p in route] for route in self.routes_from_spawn],
            ),
        )


@lru_cache(maxsize=16)  # assumption: bounded cache for terrain variants
def _terrain(width, height, seed):
    return _build_terrain(width, height, seed)


@lru_cache(maxsize=16)
def _island_terrain(width, height, seed):
    rng = random.Random(seed)
    cx, cy = width // 2, height // 2
    max_radius = 16.0
    tiles = [[0] * width for _ in range(height)]
    elevation = [[0.0] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - cx, y - cy)
            noise = (
                math.sin(x * 0.4 + seed % 10) * 1.8
                + math.cos(y * 0.4 + seed % 7) * 1.8
                + math.sin((x + y) * 0.3) * 1.2
            )
            effective_dist = dist + noise
            if effective_dist > max_radius:
                tiles[y][x] = 0
                elevation[y][x] = -20.0 - 5.0 * (effective_dist - max_radius)
            elif effective_dist > max_radius - 3.5:
                tiles[y][x] = 1
                elevation[y][x] = max(5.0, 60.0 * (max_radius - effective_dist) / 3.5)
            elif effective_dist > max_radius - 8.5:
                tiles[y][x] = 2
                elevation[y][x] = 120.0 + 300.0 * (max_radius - 3.5 - effective_dist) / 5.0
            else:
                is_mtn = rng.random() > 0.35
                tiles[y][x] = 3 if is_mtn else 2
                elevation[y][x] = 800.0 if is_mtn else 450.0

    stream_tiles = []
    sx, sy = int(cx), int(cy)
    sdir = rng.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
    for _ in range(12):
        if 0 <= sx < width and 0 <= sy < height and tiles[sy][sx] != 0:
            stream_tiles.append((sx, sy))
        sx += sdir[0] + rng.choice([0, rng.choice([-1, 1])])
        sy += sdir[1] + rng.choice([0, rng.choice([-1, 1])])
    if not stream_tiles:
        stream_tiles = [(cx, cy + 2)]

    valleys = [[(cx, cy)] + stream_tiles]
    clean_springs = list(stream_tiles[:2])
    freshwater_tiles = list(dict.fromkeys(stream_tiles + clean_springs))

    candidates = [
        [x, y]
        for y in range(8, height - 8)
        for x in range(8, width - 8)
        if tiles[y][x] in (1, 2)
    ]
    spawn = rng.choice(candidates) if candidates else [cx, cy + 4]
    tiles[spawn[1]][spawn[0]] = 2
    elevation[spawn[1]][spawn[0]] = max(120.0, elevation[spawn[1]][spawn[0]])

    food = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if tiles[y][x] == 2 and rng.random() < 0.35
    ]
    if tuple(spawn) not in food:
        food.append(tuple(spawn))

    zones = [[0 for _ in range(width)] for _ in range(height)]
    assembly = [tuple(spawn), clean_springs[0]]

    result = dict(
        width=width,
        height=height,
        seed=seed,
        vent=(cx, cy),
        elevation=elevation,
        drainage={},
        tiles=tiles,
        zones=zones,
        valleys=valleys,
        stream_tiles=stream_tiles,
        clean_springs=clean_springs,
        freshwater_tiles=freshwater_tiles,
        spawn_pos=spawn,
        food_tiles=food,
        assembly_points=assembly,
        pdc_footprint=set(),
        lahar_footprint=set(),
    )
    routing_world = object.__new__(IslandWorld)
    routing_world.__dict__.update(result)
    routing_world.lava, routing_world.pdc = set(), set()
    result["routes_from_spawn"] = [routing_world.path(spawn, [p]) for p in assembly]
    result["route_from_spawn"] = result["routes_from_spawn"][0] if result["routes_from_spawn"] else [tuple(spawn)]
    return result


def _build_terrain(width, height, seed):
    rng = random.Random(seed)
    cx, cy = width // 2, height // 2
    elevation = []
    for y in range(height):
        row = []
        for x in range(width):
            dx, dy = (x - cx) * 40 / width, (y - cy) * 40 / height
            r, angle = math.hypot(dx, dy), math.atan2(dy, dx)
            radius = 16 + 2.6 * math.sin(3 * angle + .7) + 1.8 * math.sin(7 * angle + seed)  # assumption: irregular coast
            fraction = max(0, 1 - r / radius)
            carving = 1 - .42 * math.exp(-.5 * (math.sin(3 * angle + .4 + .45 * math.sin(r * .55)) / .25) ** 2) * min(1, r / 3)  # assumption: winding erosional gullies
            h = 1030 * fraction ** 1.6 * carving + rng.uniform(-18, 18) * fraction if r < radius else -20 - 8 * (r - radius)
            row.append(max(1., h) if r < radius else h)
        elevation.append(row)

    def neighbors(p):
        for dx, dy in NEIGHBORS:
            x, y = p[0] + dx, p[1] + dy
            if 0 <= x < width and 0 <= y < height:
                yield x, y

    # Priority flood fills enclosed pits; epsilon gives flats an unambiguous outlet.
    heap, seen = [], set()
    for y in range(height):
        for x in range(width):
            if elevation[y][x] <= 0 or x in (0, width - 1) or y in (0, height - 1):
                heapq.heappush(heap, (elevation[y][x], (x, y)))
                seen.add((x, y))
    while heap:
        level, p = heapq.heappop(heap)
        for x, y in neighbors(p):
            if (x, y) in seen:
                continue
            seen.add((x, y))
            elevation[y][x] = max(elevation[y][x], level + .001)  # assumption: numerical flat gradient
            heapq.heappush(heap, (elevation[y][x], (x, y)))
    drainage = {}
    for y in range(height):
        for x in range(width):
            if elevation[y][x] > 0:
                q = min(neighbors((x, y)), key=lambda q: elevation[q[1]][q[0]], default=(x, y))
                if elevation[q[1]][q[0]] < elevation[y][x]:
                    drainage[(x, y)] = q
    valleys = []
    for start in ((cx, cy + 1), (cx - 1, cy), (cx + 1, cy), (cx, cy - 1)):
        route = [(cx, cy), start]
        while route[-1] in drainage:
            q = drainage[route[-1]]
            if elevation[q[1]][q[0]] <= 0:
                break
            route.append(q)
        if len(route) > 4 and not any(route[-1] in v for v in valleys):
            valleys.append(route)
    channels = set(p for v in valleys for p in v)
    zones, tiles = [], []
    for y in range(height):
        zr, tr = [], []
        for x in range(width):
            h = elevation[y][x]
            q = min(channels, key=lambda p: math.dist((x, y), p))
            d, above = math.dist((x, y), q), h - elevation[q[1]][q[0]]
            radial = math.dist((x, y), (cx, cy))
            zr.append(
                2 if radial <= 4.5 or (d <= 1.6 and above < 100) else
                1 if radial <= 7 or (d <= 3 and above < 180) else 0
            )  # assumption: terrain exposure thresholds
            tr.append(0 if h <= 0 else 3 if h > 750 else 2 if h > 100 else 1)  # assumption: vegetation bands
        zones.append(zr)
        tiles.append(tr)
    land = [(x, y) for y in range(height) for x in range(width) if tiles[y][x]]
    safe = [p for p in land if zones[p[1]][p[0]] == 0 and 80 < elevation[p[1]][p[0]] < 300]
    first = min(safe, key=lambda p: math.dist(p, (cx - 9, cy + 7)))
    angle = math.atan2(first[1] - cy, first[0] - cx)
    second = max(safe, key=lambda p: math.cos(math.atan2(p[1] - cy, p[0] - cx) - angle + math.pi))
    assembly = [first, second]
    # assumption: a spring rises on higher ground within 500 m of each assembly point.
    springs = []
    for ax, ay in assembly:
        nearby = [p for p in land if p not in assembly and zones[p[1]][p[0]] == 0 and math.dist(p, (ax, ay)) <= 2]
        springs.append(max(nearby, key=lambda p: (elevation[p[1]][p[0]], p)))
    stream = valleys[0][1:]
    # assumption: camp 1.5 km down the stream valley, not on the crater rim.
    spawn = list(next(p for p in stream if math.dist(p, (cx, cy)) >= SPAWN_MIN_VENT_TILES))
    tiles[spawn[1]][spawn[0]] = 2  # assumption: forest clearing near the stream

    def forage_chance(p):
        h = elevation[p[1]][p[0]]
        moist = any(math.dist(p, q) <= FOOD_VALLEY_TILES for q in channels) and FOOD_VALLEY_ELEVATION[0] < h < FOOD_VALLEY_ELEVATION[1]
        return FOOD_VALLEY_DENSITY if moist else FOOD_UPLAND_DENSITY if tiles[p[1]][p[0]] == 2 else 0.

    food = [p for p in land if rng.random() < forage_chance(p)]
    if tuple(spawn) not in food:
        food.append(tuple(spawn))
    result = dict(
        width=width,
        height=height,
        seed=seed,
        vent=(cx, cy),
        elevation=elevation,
        drainage=drainage,
        tiles=tiles,
        zones=zones,
        valleys=valleys,
        stream_tiles=stream,
        clean_springs=springs,
        freshwater_tiles=stream + springs,
        spawn_pos=spawn,
        food_tiles=food,
        assembly_points=assembly,
        pdc_footprint={p for p in land if zones[p[1]][p[0]] == 2},
        lahar_footprint={p for p in channels if zones[p[1]][p[0]] != 0},
    )

    routing_world = object.__new__(IslandWorld)
    routing_world.__dict__.update(result)
    routing_world.lava, routing_world.pdc = set(), set()
    result["routes_from_spawn"] = [routing_world.path(spawn, [p]) for p in assembly]
    result["route_from_spawn"] = min(result["routes_from_spawn"], key=routing_world.route_minutes)
    return result

"""Pompeii as two linked 40x40 maps with the same interface as IslandWorld.

CityWorld is the walled town at street scale. RegionWorld is the land from the
town to Vesuvius and the coast. A person leaving a city gate continues from that
gate's tile on the region map (see GATE_TO_REGION).

Both are labelled schematics for an evacuation demonstration, not surveys. The
layout follows the sources in PROVENANCE; individual blocks are simplified.
Numerical choices are assumptions unless a source is cited.
"""
import copy
import math
from functools import lru_cache

from engine.ship import ShipWorld
from engine.world import IslandWorld, SCALE_M_PER_TILE

CITY_M_PER_TILE = 30  # assumption: leaves room for exit roads around a 1,050 x 800 m town
REGION_M_PER_TILE = SCALE_M_PER_TILE  # assumption: same 250 m as the volcano scenario
WALK_M_PER_S = 1.0  # assumption: walking pace in a street crowd, before any pumice

GUIDE = "https://pompeiisites.org/wp-content/uploads/A-Guide-to-the-Pompeii-Excavations-2.pdf"
NARRABEEN = "https://sites.google.com/narrabeenhs.com/pompeiiandherculaneum/1-2-plans-and-streetscapes"
POMPEIONLINE = "https://www.pompeionline.net/pompeii/map.htm"
ROMAN_PORTS = "https://www.romanports.org/en/articles/ports-in-focus/625-the-port-of-pompeii.html"
MADAIN_ERCOLANO = "https://madainproject.com/porta_ercolano"
MADAIN_ABBONDANZA = "https://madainproject.com/via_dell_abbondanza"

# status: sourced = read on the page; excerpt = search excerpt only; school = school page only;
# inferred = reasoned from a source; unconfirmed = from memory; assumption = a modelling choice.
PROVENANCE = {
    "city_area": dict(value="66 hectares", status="sourced", url=GUIDE, note="p. 9"),
    "wall_length": dict(value="over 3,200 m", status="sourced", url=GUIDE, note="p. 81"),
    "city_outline": dict(value="oval", status="assumption", url=None, note="sources disagree: irregular or rectangular"),
    "city_slope": dict(value="10-40 m above sea level", status="school", url=NARRABEEN, note="rising north is an assumption"),
    "gate_marina": dict(value="west", status="sourced", url=GUIDE, note="p. 81"),
    "gate_ercolano": dict(value="northwest; road to Naples", status="excerpt", url=MADAIN_ERCOLANO, note="road from guide p. 75"),
    "gate_nocera": dict(value="southeast", status="sourced", url=GUIDE, note="p. 38"),
    "gate_vesuvio": dict(value="north", status="unconfirmed", url=None, note="position from memory"),
    "gate_nola": dict(value="northeast; road to Nola", status="unconfirmed", url=GUIDE, note="road name p. 44; position from memory"),
    "gate_sarno": dict(value="east", status="excerpt", url=MADAIN_ABBONDANZA, note="end of Via dell'Abbondanza"),
    "gate_stabia": dict(value="south", status="unconfirmed", url=ROMAN_PORTS, note="named gate; position from memory"),
    "via_dell_abbondanza": dict(value="Forum to Porta Sarno", status="excerpt", url=MADAIN_ABBONDANZA, note="about 900 m"),
    "via_stabiana": dict(value="main north-south street", status="school", url=NARRABEEN, note="gate ends from memory"),
    "via_di_nola": dict(value="major east-west street", status="sourced", url=POMPEIONLINE, note="sources disagree on which is main"),
    "via_di_nocera": dict(value="meets Via dell'Abbondanza", status="excerpt", url=MADAIN_ABBONDANZA, note=""),
    "via_marina": dict(value="up to the Forum from Porta Marina", status="sourced", url=GUIDE, note="p. 83"),
    "via_consolare": dict(value="from Porta Ercolano", status="sourced", url=GUIDE, note="named on guide maps; path simplified"),
    "forum": dict(value="near Porta Marina", status="sourced", url=POMPEIONLINE, note=""),
    "amphitheatre": dict(value="southeast", status="inferred", url=GUIDE, note="Region II with Porta Nocera, pp. 34, 38; one school page says southwest"),
    "palaestra": dict(value="next to the amphitheatre", status="school", url=NARRABEEN, note=""),
    "block_size": dict(value="850-5,500 sq m", status="school", url=NARRABEEN,
                       note="drawn blocks of 18,000 sq m stand for several real blocks; a 30 m tile cannot show a 6 m lane"),
    "vesuvius_distance": dict(value="8 km", status="sourced", url=ROMAN_PORTS, note="northwest bearing from memory"),
    "vesuvius_height": dict(value="1,200 m", status="assumption", url=None, note="height in 79 CE is unknown"),
    "coast_and_sarno": dict(value="coast west of town; Sarno to the south", status="assumption", url=ROMAN_PORTS,
                            note="town bordered the Sarno; ancient coast and port position are uncertain"),
}

CITY_CENTER = (20., 20.)
CITY_SEMI_AXES = (17.5, 13.3)  # assumption: oval of 66 ha at 30 m per tile
BLOCK_X, BLOCK_Y, LANE_OFFSET = 6, 5, 3  # assumption: lanes every 180 x 150 m, so streets do not swamp the town
ELEVATION_LOW, ELEVATION_HIGH = 10., 40.  # metres; rising north is an assumption

ABBONDANZA_Y, NOLA_Y, MARINA_Y = 23, 13, 21  # assumption: schematic street lines
STABIANA_X, NOCERA_X, ERCOLANO_X = 21, 31, 9  # assumption: schematic street lines
FORUM = (10, 19, 13, 25)  # x0, y0, x1, y1
AMPHITHEATRE = (30, 25, 33, 28)
PALAESTRA = (26, 25, 28, 28)
LANDMARKS = {"forum": FORUM, "amphitheatre": AMPHITHEATRE, "palaestra": PALAESTRA}

REGION_CITY_CENTER = (30, 30)  # assumption: places Vesuvius 8 km to the northwest
VESUVIUS = (7, 7)  # 8 km at 250 m per tile, about 22.6 tiles along each axis
VESUVIUS_HEIGHT = 1200.
GATE_TO_REGION = {  # city gate -> region tile just outside the town
    "ercolano": (28, 28), "vesuvio": (30, 28), "nola": (32, 28), "sarno": (33, 30),
    "nocera": (32, 32), "stabia": (30, 32), "marina": (27, 30),
}
REGION_ROADS = {  # gate -> where its road leaves the region map
    "ercolano": (0, 17),  # toward Naples, along the shore below the mountain
    "vesuvio": (17, 0),   # assumption: farm tracks north
    "nola": (39, 8),      # toward Nola
    "sarno": (39, 28),    # assumption: along the river plain
    "nocera": (39, 37),   # toward Nocera
    "stabia": (33, 39),   # assumption: south to Stabiae
    "marina": (24, 30),   # to the shore
}
ROAD_WAYPOINTS = {"ercolano": [(9, 21), (3, 18)]}  # assumption: the coast road stays on the low shore
SARNO_COURSE = ((39, 35), (34, 34), (26, 34))  # assumption: the town borders the river; its ancient course is uncertain


def coast_x(y):
    """Sea lies west of this x, leaving a low shore below the mountain. The ancient shoreline is uncertain."""
    return 22 + (y - 30) * (1.11 if y >= 30 else 1.83)


class CityWorld(IslandWorld):
    next_step_field = ShipWorld.next_step_field

    def __init__(self, width=40, height=40, seed=0, scenario="pompeii"):
        self.__dict__.update(copy.deepcopy(_city_terrain(width, height)))
        self.seed, self.scenario = seed, scenario
        _init_hazards(self)

    def travel_minutes(self, a, b):
        slope = abs(self.elevation[b[1]][b[0]] - self.elevation[a[1]][a[0]]) / CITY_M_PER_TILE
        return CITY_M_PER_TILE / WALK_M_PER_S / 60 * (1 + slope)

    def export_dict(self):
        exported = super().export_dict()
        exported.update(scale_m_per_tile=CITY_M_PER_TILE, gates={k: list(v) for k, v in self.gates.items()},
                        landmarks={k: list(v) for k, v in LANDMARKS.items()}, provenance=PROVENANCE)
        return exported


class RegionWorld(IslandWorld):
    next_step_field = ShipWorld.next_step_field

    def __init__(self, width=40, height=40, seed=0, scenario="pompeii_region"):
        self.__dict__.update(copy.deepcopy(_region_terrain(width, height)))
        self.seed, self.scenario = seed, scenario
        _init_hazards(self)

    def export_dict(self):
        exported = super().export_dict()
        exported.update(scale_m_per_tile=REGION_M_PER_TILE, road_ends={k: list(v) for k, v in self.road_ends.items()},
                        gate_to_region={k: list(v) for k, v in GATE_TO_REGION.items()}, provenance=PROVENANCE)
        return exported


def _init_hazards(world):
    world.lava, world.pdc, world.lahar = set(), set(), set()
    world.active_pdc, world.active_lahar, world.surge = set(), set(), set()
    world.ash, world.ash_grid = 0., None
    world.volcanic_sign_seen = False
    world.shelter_tiles = []
    world.depleted_food = set()


def _inside_city(x, y):
    dx, dy = (x - CITY_CENTER[0]) / CITY_SEMI_AXES[0], (y - CITY_CENTER[1]) / CITY_SEMI_AXES[1]
    return dx * dx + dy * dy <= 1


def _carve_line(tiles, start, end, value=1):
    """Cardinal staircase between two tiles, so every step is walkable."""
    x, y = start
    tiles[y][x] = value
    while (x, y) != tuple(end):
        if abs(end[0] - x) >= abs(end[1] - y):
            x += 1 if end[0] > x else -1
        else:
            y += 1 if end[1] > y else -1
        tiles[y][x] = value


def _base(width, height, tiles, elevation, zones, spawn, assembly, extra):
    result = dict(width=width, height=height, seed=0, elevation=elevation, drainage={}, tiles=tiles, zones=zones,
                  valleys=[], stream_tiles=[], clean_springs=[], food_tiles=[], spawn_pos=list(spawn),
                  assembly_points=assembly, pdc_footprint=set(), lahar_footprint=set(), **extra)
    return result


def _add_routes(cls, result):
    routing_world = object.__new__(cls)
    routing_world.__dict__.update(result)
    routing_world.lava, routing_world.pdc = set(), set()
    routes = [routing_world.path(result["spawn_pos"], [p]) for p in result["assembly_points"]]
    result["routes_from_spawn"] = routes
    result["route_from_spawn"] = min(routes, key=routing_world.route_minutes)
    return result


@lru_cache(maxsize=4)
def _city_terrain(width, height):
    inside = {(x, y) for y in range(height) for x in range(width) if _inside_city(x, y)}
    walls = {p for p in inside if any((p[0] + dx, p[1] + dy) not in inside
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    tiles = [[0] * width for _ in range(height)]
    for x, y in inside - walls:
        tiles[y][x] = 4  # buildings until a street or open space is cut through them
    interior = inside - walls
    # Lanes first, so named streets and landmarks draw over them.
    for x, y in interior:
        if x % BLOCK_X == LANE_OFFSET or y % BLOCK_Y == LANE_OFFSET:
            tiles[y][x] = 1
        elif x >= 24 and (x * 3 + y * 5) % 7 == 0:
            tiles[y][x] = 2  # assumption: more gardens in the eastern quarter

    def wall_on_line(x, y, dx, dy):
        """First wall tile reached walking from (x, y) in direction (dx, dy)."""
        while (x, y) not in walls:
            x, y = x + dx, y + dy
        return x, y

    gates = {
        "marina": wall_on_line(10, MARINA_Y, -1, 0), "sarno": wall_on_line(30, ABBONDANZA_Y, 1, 0),
        "nola": wall_on_line(30, NOLA_Y, 1, 0), "vesuvio": wall_on_line(STABIANA_X, 15, 0, -1),
        "stabia": wall_on_line(STABIANA_X, 25, 0, 1), "nocera": wall_on_line(NOCERA_X, 25, 0, 1),
        "ercolano": wall_on_line(ERCOLANO_X, 15, 0, -1),
    }
    streets = {
        "via_dell_abbondanza": ((FORUM[2], ABBONDANZA_Y), gates["sarno"]),
        "via_di_nola": ((ERCOLANO_X, NOLA_Y), gates["nola"]),
        "via_stabiana": (gates["vesuvio"], gates["stabia"]),
        "via_di_nocera": ((NOCERA_X, ABBONDANZA_Y), gates["nocera"]),
        "via_marina": (gates["marina"], (FORUM[0], MARINA_Y)),
        "via_consolare": (gates["ercolano"], (FORUM[0], FORUM[1])),
    }
    for start, end in streets.values():
        _carve_line(tiles, start, end)
    for x0, y0, x1, y1 in LANDMARKS.values():
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (x, y) in interior:
                    tiles[y][x] = 1
    for x, y in gates.values():
        tiles[y][x] = 1
    # Each gate's road runs straight out to the map edge, where a person crosses to the region map.
    exits = {}
    exit_roads = set()
    for name, (x, y) in gates.items():
        dx, dy = (x - CITY_CENTER[0]), (y - CITY_CENTER[1])
        edge = (0 if dx < 0 else width - 1, y) if abs(dx) * .76 > abs(dy) else (x, 0 if dy < 0 else height - 1)
        _carve_line(tiles, (x, y), edge)
        exits[name] = edge
        step_x = (edge[0] > x) - (edge[0] < x)
        step_y = (edge[1] > y) - (edge[1] < y)
        px, py = x + step_x, y + step_y
        while (px, py) != edge:
            exit_roads.add((px, py))
            px, py = px + step_x, py + step_y
        exit_roads.add(edge)

    elevation = [[round(ELEVATION_HIGH - (ELEVATION_HIGH - ELEVATION_LOW) * y / (height - 1), 1)
                  for _ in range(width)] for y in range(height)]
    # Every zone is 0: a person's perceived risk is not set by where the map says they live.
    zones = [[0] * width for _ in range(height)]
    fountains = [(x, y) for y in range(height) for x in range(width)
                 if tiles[y][x] == 1 and (x, y) in interior and x % (BLOCK_X * 2) == LANE_OFFSET and y % (BLOCK_Y * 2) == LANE_OFFSET]  # assumption
    result = _base(width, height, tiles, elevation, zones, (STABIANA_X, ABBONDANZA_Y), list(exits.values()), dict(
        vent=(0, 0),  # Vesuvius lies off this map to the northwest; see RegionWorld.vent
        freshwater_tiles=fountains, gates=gates, exits=exits, exit_road_tiles=exit_roads, wall_tiles=walls, street_lines=streets,
    ))
    return _add_routes(CityWorld, result)


@lru_cache(maxsize=4)
def _region_terrain(width, height):
    tiles, elevation = [], []
    for y in range(height):
        tile_row, height_row = [], []
        for x in range(width):
            distance = math.dist((x, y), VESUVIUS)
            metres = VESUVIUS_HEIGHT * math.exp(-(distance / 7) ** 2) + 15  # assumption: smooth cone on a low plain
            if x < coast_x(y):
                tile_row.append(0)
                height_row.append(-5.)
            else:
                tile_row.append(3 if metres > 400 else 2 if metres > 60 or (x + y) % 3 == 0 else 1)  # assumption
                height_row.append(round(metres, 1))
        tiles.append(tile_row)
        elevation.append(height_row)
    # The Sarno runs west to the sea south of the town, crossed only where roads meet it.
    for start, stop in zip(SARNO_COURSE, SARNO_COURSE[1:]):
        _carve_line(tiles, start, stop, value=0)
    river = [(x, y) for y in range(33, 37) for x in range(width)
             if tiles[y][x] == 0 and x >= coast_x(y)]
    for name, end in REGION_ROADS.items():
        stops = [GATE_TO_REGION[name], *ROAD_WAYPOINTS.get(name, []), end]
        for start, stop in zip(stops, stops[1:]):
            _carve_line(tiles, start, stop)
    for y in range(29, 32):  # the town, about 1,050 x 800 m at 250 m per tile
        for x in range(28, 33):
            tiles[y][x] = 4
    for name, tile in GATE_TO_REGION.items():
        tiles[tile[1]][tile[0]] = 1
    river = [p for p in river if tiles[p[1]][p[0]] == 0]  # bridges are road, not river
    zones = [[0] * width for _ in range(height)]
    result = _base(width, height, tiles, elevation, zones, REGION_CITY_CENTER, list(REGION_ROADS.values()), dict(
        vent=VESUVIUS, freshwater_tiles=river, river_tiles=river, road_ends=dict(REGION_ROADS),
    ))
    return _add_routes(RegionWorld, result)

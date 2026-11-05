"""Moses Springer Community Centre, Waterloo, Ontario, as a 40x40 map with the IslandWorld interface.

A labelled schematic. Outlines come from OpenStreetMap as it is now, not as it was in 2012.
No floor plan was found, so doors, the fence and everything inside the building are assumptions.
Coordinates are metres east and north of 43.474, -80.5111. Map data (c) OpenStreetMap contributors, ODbL.
See docs/WATERLOO_SOURCES.md.
"""
import copy
from functools import lru_cache

from engine.city import _add_routes, _base, _carve_line, _init_hazards
from engine.ship import ShipWorld
from engine.world import IslandWorld

SITE_M_PER_TILE = 5  # assumption: fits the building, parking and both ends of the road; too coarse for inner walls
WEST_M, NORTH_M = -100., 75.  # assumption: map frame chosen to hold the site and its exits
WALK_M_PER_S = 1.3  # median adult walking speed, Rinne et al. (2010), section 4.4.1
WADE_M_PER_S = .5  # assumption: no source found for leaving a pool

OSM = "https://www.openstreetmap.org/way/"
CITY_PAGE = "https://www.waterloo.ca/recreation-and-sports/find-a-community-or-rec-centre/moses-springer-community-centre/"
VTT = "https://sarjaweb.vtt.fi/pdf/tiedotteet/2010/T2562.pdf"

# status: sourced = read on the page; assumption = a modelling choice; unconfirmed = from memory.
PROVENANCE = {
    "building_outline": dict(value="about 3,250 sq m", status="sourced", url=OSM + "143670515", note="current map; area calculated"),
    "pool_outline": dict(value="about 1,230 sq m", status="sourced", url=OSM + "39945836", note="current map; area calculated"),
    "pool_length": dict(value="50 m, 8 lanes, outdoor", status="sourced", url=CITY_PAGE, note="map outline also measures about 50 m"),
    "site_outline": dict(value="about 6,190 sq m", status="sourced", url=OSM + "790831831", note="current map; area calculated"),
    "indoor_spaces": dict(value="1 ice pad, 4 change rooms, 1 community room", status="sourced", url=CITY_PAGE, note="positions are assumptions"),
    "pool_change_rooms": dict(value="2", status="sourced", url=CITY_PAGE, note="position is an assumption"),
    "roads_and_paths": dict(value="Lincoln Road, Laurel Trail, service roads", status="sourced", url=OSM + "193912296", note="current map"),
    "nearby_buildings": dict(value="outlines of 100 sq m or more", status="sourced", url="https://www.openstreetmap.org/#map=18/43.4737/-80.5115", note="current map"),
    "walking_speed": dict(value="1.3 m/s", status="sourced", url=VTT, note="section 4.4.1; median, adults in corridors"),
    "doors": dict(value="4", status="assumption", url=None, note="no plan found; number and places are guesses"),
    "pool_fence": dict(value="fence with 2 gates around the deck", status="assumption", url=None, note="no source for the fence or gates"),
    "interior_layout": dict(value="zones with no inner walls", status="assumption", url=None, note="a 5 m tile cannot show them, so indoor escape is too easy"),
    "single_level": dict(value="one level", status="assumption", url=None, note="the City lists an elevator; floor count not found"),
    "arena_floor": dict(value="walkable", status="assumption", url=None, note="whether there was ice in July 2012 is unknown"),
    "wading_speed": dict(value="0.5 m/s", status="assumption", url=None, note="no source found"),
    "exit_points": dict(value="5 places the roads and paths leave the map", status="assumption", url=None, note="where people really gathered is unknown"),
}

BUILDING = [(-33.7, -29.6), (-26.5, -30.6), (-27.5, -37.9), (9.8, -43.0), (11.8, -28.6), (15.8, -29.1), (24.0, 30.8),
            (-9.0, 35.3), (-14.6, 39.7), (-20.3, 30.6), (-24.4, 1.0), (-23.1, .9), (-23.4, -1.4), (-28.2, -.8),
            (-29.5, -10.3), (-21.6, -11.3), (-22.5, -18.2), (-30.0, -24.2), (-33.0, -24.0), (-33.3, -26.4)]
POOL = [(-27.5, -77.1), (-38.1, -75.8), (-34.2, -44.3), (15.4, -50.5), (12.6, -72.9), (-26.4, -68.1), (-26.7, -70.2), (-27.3, -74.9)]
SITE = [(-25.1, 38.0), (-35.7, -37.0), (-41.4, -78.1), (3.8, -84.2), (17.2, -73.9), (22.9, -29.5), (15.8, -29.1),
        (24.0, 30.8), (-9.0, 35.3), (-14.6, 39.7)]
PARKING = {
    "parking_north": [(-54.3, 58.7), (-64.5, -16.3), (-45.0, -19.2), (-38.8, 35.1), (-43.5, 35.9), (-39.8, 57.4)],
    "parking_south": [(-49.1, -32.5), (-56.0, -81.9), (-59.8, -81.4), (-70.7, -70.7), (-70.5, -65.1), (-88.4, -61.7),
                      (-84.1, -28.4), (-66.7, -31.4), (-66.0, -29.1)],
}
NEARBY_BUILDINGS = {  # OSM way id: outline
    795828764: [(44.8, 53.7), (49.0, 68.8), (42.8, 70.5), (45.3, 79.9), (61.1, 75.6), (59.3, 69.2), (60.4, 68.9), (57.1, 57.0), (58.4, 56.6), (56.7, 50.5)],
}
CREEK = [(-214.0, -197.0), (-96.8, -16.6), (-76.4, 18.4), (-77.5, 39.0), (-86.0, 55.8), (-99.9, 73.4), (-126.7, 85.6)]
ROADS = {
    "lincoln_road": [(102.6, 63.1), (100.5, 55.5), (92.3, 28.5), (86.3, .5), (64.2, -74.7), (54.7, -100.2), (48.9, -114.2), (38.2, -132.9)],
    "service_north": [(-21.0, 40.3), (-30.2, 48.8), (-45.7, 49.7), (-55.3, -19.0), (-56.0, -23.6)],
    "service_south": [(-51.9, -94.1), (-43.6, -35.1), (-45.4, -29.2), (-50.1, -25.0), (-56.0, -23.6), (-63.9, -22.8),
                      (-69.6, -24.9), (-73.7, -29.1), (-78.7, -64.5), (-77.5, -69.4), (-64.4, -81.7), (-51.9, -94.1)],
    "laurel_trail": [(-88.9, 105.3), (-75.1, 73.2), (-69.7, 56.0), (-66.7, 40.2), (-65.2, 19.5), (-69.6, 2.0), (-76.1, -15.6),
                     (-80.6, -21.7), (-85.2, -26.1), (-106.0, -12.3)],
    "footway_east": [(84.0, 31.4), (63.6, 23.8), (49.5, 6.0), (29.8, -9.3), (23.9, -27.7), (18.8, -74.2), (13.6, -79.9),
                     (5.1, -84.2), (-15.1, -89.4), (-21.6, -95.0), (-35.6, -120.7)],
    "path_south": [(-36.9, -177.0), (-35.6, -120.7), (-36.2, -108.9), (-39.1, -102.1), (-44.6, -89.9), (-44.5, -82.5), (-38.0, -35.8),
                   (-39.0, -29.1), (-43.2, -22.3), (-51.1, -19.6), (-76.1, -15.6)],
}
# Named roads and the point where each leaves the map.
EXIT_ROADS = {"lincoln_north": ("lincoln_road", 0), "lincoln_south": ("lincoln_road", -1), "trail_north": ("laurel_trail", 0),
              "trail_west": ("laurel_trail", -1), "path_south": ("path_south", 0)}

# Every value below is an assumption: tiles chosen to fit the listed spaces inside the real outline.
DOORS = {"main_west": (14, 15), "pool_south": (18, 22), "east": (23, 15), "north": (20, 8)}
POOL_GATES = {"gate_west": (11, 26), "gate_south": (19, 32)}
INDOOR_AREAS = {  # x0, y0, x1, y1
    "ice_pad": (17, 9, 21, 20),  # 25 x 60 m
    "lobby": (15, 13, 16, 17),
    "community_room": (14, 19, 16, 20),
    "change_rooms": (16, 21, 20, 21),
}


class SiteWorld(IslandWorld):
    next_step_field = ShipWorld.next_step_field

    def __init__(self, width=40, height=40, seed=0, scenario="waterloo"):
        self.__dict__.update(copy.deepcopy(_site_terrain(width, height)))
        self.seed, self.scenario = seed, scenario
        _init_hazards(self)

    def walkable(self, p):
        p = tuple(p)
        return p in self.pool_tiles or bool(self.get_tile(*p)) and self.get_tile(*p) != 3

    def travel_minutes(self, a, b):
        speed = WADE_M_PER_S if tuple(b) in self.pool_tiles else WALK_M_PER_S
        return SITE_M_PER_TILE / speed / 60

    def export_dict(self):
        exported = super().export_dict()
        exported.update(scale_m_per_tile=SITE_M_PER_TILE, doors={k: list(v) for k, v in self.doors.items()},
                        gates={k: list(v) for k, v in self.gates.items()}, exits={k: list(v) for k, v in self.exits.items()},
                        provenance=PROVENANCE)
        return exported


def _inside(x, y, polygon):
    result = False
    for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            result = not result
    return result


def _center_m(x, y):
    return WEST_M + SITE_M_PER_TILE * (x + .5), NORTH_M - SITE_M_PER_TILE * (y + .5)


def _rasterize(polygon, width, height):
    return {(x, y) for y in range(height) for x in range(width) if _inside(*_center_m(x, y), polygon)}


def _line_tiles(points, width, height):
    """Tiles along a polyline, kept in order and clipped to the map."""
    tiles = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        samples = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
        for i in range(samples + 1):
            x = int((x0 + (x1 - x0) * i / samples - WEST_M) // SITE_M_PER_TILE)
            y = int((NORTH_M - (y0 + (y1 - y0) * i / samples)) // SITE_M_PER_TILE)
            if 0 <= x < width and 0 <= y < height and (not tiles or tiles[-1] != (x, y)):
                tiles.append((x, y))
    return tiles


def _carve(tiles, path, value):
    for a, b in zip(path, path[1:]):
        _carve_line(tiles, a, b, value)
    return {p for a, b in zip(path, path[1:]) for p in _staircase(a, b)} | set(path)


def _staircase(a, b):
    x, y = a
    result = [a]
    while (x, y) != tuple(b):
        if abs(b[0] - x) >= abs(b[1] - y):
            x += 1 if b[0] > x else -1
        else:
            y += 1 if b[1] > y else -1
        result.append((x, y))
    return result


def _reach_edge(point, width, height):
    """A path from a clipped road end to the nearest map edge."""
    x, y = point
    distances = {(0, y): x, (width - 1, y): width - 1 - x, (x, 0): y, (x, height - 1): height - 1 - y}
    return min(distances, key=distances.get)


@lru_cache(maxsize=4)
def _site_terrain(width, height):
    tiles = [[1] * width for _ in range(height)]
    creek = _carve(tiles, _line_tiles(CREEK, width, height), 0)
    roads, paths = set(), {}
    for name, points in ROADS.items():
        path = _line_tiles(points, width, height)
        roads |= _carve(tiles, path, 1)
        paths[name] = path
    exits = {}
    for name, (road, end) in EXIT_ROADS.items():
        edge = _reach_edge(paths[road][end], width, height)
        roads |= _carve(tiles, [paths[road][end], edge], 1)
        exits[name] = edge

    nearby = set().union(*(_rasterize(p, width, height) for p in NEARBY_BUILDINGS.values()))
    for x, y in nearby - set(exits.values()):
        tiles[y][x] = 3
    parking = {name: _rasterize(p, width, height) for name, p in PARKING.items()}

    building = _rasterize(BUILDING, width, height)
    building_walls = {p for p in building if any((p[0] + dx, p[1] + dy) not in building for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for x, y in building:
        tiles[y][x] = 4
    for x, y in building_walls - set(DOORS.values()):
        tiles[y][x] = 3

    pool = _rasterize(POOL, width, height) - building
    site = _rasterize(SITE, width, height)
    deck = {p for p in site - building - pool if p[1] >= 23 or (p[1] >= 21 and p[0] >= 22)}  # assumption: the fenced part
    fenced = pool | deck
    fence = {(x + dx, y + dy) for x, y in fenced for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - fenced - building
    for x, y in pool | deck:
        tiles[y][x] = 0 if (x, y) in pool else 1
    for x, y in fence - set(POOL_GATES.values()):
        tiles[y][x] = 3
    for x, y in POOL_GATES.values():
        tiles[y][x] = 1

    areas = {name: {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)} & (building - building_walls)
             for name, (x0, y0, x1, y1) in INDOOR_AREAS.items()}
    areas.update(pool=pool, pool_deck=deck, indoors=building - building_walls, **parking)
    elevation = [[0.] * width for _ in range(height)]  # assumption: flat site
    zones = [[0] * width for _ in range(height)]  # every zone is 0: location never sets perceived risk
    result = _base(width, height, tiles, elevation, zones, (19, 15), list(exits.values()), dict(
        vent=(0, 0),  # no volcano here; the field is kept for the shared interface
        freshwater_tiles=[], doors=dict(DOORS), gates=dict(POOL_GATES), exits=exits, areas=areas, pool_tiles=pool,
        creek_tiles=creek - roads, road_tiles=roads - building - pool - fence, wall_tiles=(building_walls - set(DOORS.values())) | (fence - set(POOL_GATES.values())),
        nearby_building_tiles=nearby,
    ))
    return _add_routes(SiteWorld, result)

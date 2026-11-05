"""RMS Titanic as a 40x40 cutaway grid with the same interface as IslandWorld.

The map is a side section: x runs stern (0) to bow (39), y runs top to bottom,
so rising water is visible and "walking uphill" means climbing a staircase.
It is a schematic for an evacuation demonstration, not a deck plan.
Numerical choices are assumptions unless a source is cited.
"""
import copy
import heapq
import math
from functools import lru_cache

from engine.world import IslandWorld

SHIP_MAP_SEED = 1912  # assumption: one fixed ship across event seeds
SHIP_LENGTH_M = 269  # Wikipedia, RMS Titanic: overall length
SHIP_M_PER_TILE = 7  # assumption: 269 m drawn across 38 tiles
ROW_M = 1.4  # assumption: two rows per 2.8 m deck; vertical is not to horizontal scale
WALK_M_PER_S = 1.0  # assumption: unhurried crowded corridor walking
STAIR_MINUTES_PER_ROW = .25  # assumption: fifteen seconds per stair row in a crowd

# Contract tile meanings on the ship: 1 open deck, 3 stairs, 4 interior, 0 blocked or sea.
OPEN_DECK, STAIRS, INTERIOR = 1, 3, 4
TERRAIN_MINUTES = {OPEN_DECK: 1., INTERIOR: 1.15, STAIRS: 1.}  # assumption: interior corridors slow walkers

BOAT, A, B, C, D, E, F, G, TANK = 10, 12, 14, 16, 18, 20, 22, 24, 26  # assumption: one row per deck, spaced by two
DECK_ROWS = dict(boat=BOAT, a=A, b=B, c=C, d=D, e=E, f=F, g=G, tank=TANK)
WATERLINE_ROW = 21.5  # assumption: resting waterline sits between E and F decks
DECK_SPANS = {
    BOAT: (9, 31), A: (9, 31), B: (6, 33), C: (2, 37),
    D: (2, 37), E: (1, 38), F: (2, 37), G: (3, 36), TANK: (5, 34),
}  # assumption: schematic hull and superstructure outline
OPEN_SPANS = {BOAT: [(9, 31)], C: [(2, 6), (33, 37)]}  # assumption: boat deck plus aft and forward well decks
STAIR_COLUMNS = {
    6: (C, G), 12: (BOAT, G), 17: (BOAT, E), 24: (BOAT, E),
    28: (BOAT, G), 35: (C, G), 10: (G, TANK), 20: (G, TANK), 30: (G, TANK),
}  # assumption: schematic main stairs, crew routes and engine-room ladders
# Six of sixteen compartments open to the sea; Wikipedia, Sinking of the Titanic.
BULKHEADS = (35, 33, 31, 29, 27, 25, 22, 20, 17, 15, 13, 10, 8, 6, 4)  # assumption: x positions of 15 bulkheads
BULKHEAD_TOP_ROW = E  # assumption: watertight bulkheads end near E deck
BREACHED_FROM_X = 25  # the six opened compartments, forward of this bulkhead


class ShipWorld(IslandWorld):
    def __init__(self, width=40, height=40, seed=SHIP_MAP_SEED, scenario="titanic"):
        self.__dict__.update(copy.deepcopy(_ship_terrain(width, height)))
        self.seed, self.scenario = seed, scenario
        self.lava, self.pdc, self.lahar = set(), set(), set()
        self.active_pdc, self.active_lahar, self.surge = set(), set(), set()
        self.ash, self.ash_grid = 0., None
        self.volcanic_sign_seen = False
        self.shelter_tiles = []
        self.depleted_food = set()
        self.flooded, self.rising = set(), set()

    def walkable(self, p):
        p = tuple(p)
        return bool(self.get_tile(*p)) and p not in self.flooded

    def travel_minutes(self, a, b):
        tile = self.get_tile(*b)
        if a[1] != b[1]:
            return STAIR_MINUTES_PER_ROW
        return SHIP_M_PER_TILE / WALK_M_PER_S / 60 * TERRAIN_MINUTES.get(tile, 1.)

    def next_step_field(self, goals):
        """Multi-source least-time field: each tile maps to its next tile toward a goal."""
        queue, costs, following = [], {}, {}
        for goal in goals:
            goal = tuple(goal)
            if self.walkable(goal):
                costs[goal] = 0.
                following[goal] = None
                queue.append((0., goal))
        heapq.heapify(queue)
        while queue:
            cost, p = heapq.heappop(queue)
            if cost != costs[p]:
                continue
            for q in self.neighbors(p):
                if not self.walkable(q):
                    continue
                candidate = cost + self.travel_minutes(q, p)
                if candidate < costs.get(q, math.inf):
                    costs[q], following[q] = candidate, p
                    heapq.heappush(queue, (candidate, q))
        return following

    def export_dict(self):
        exported = super().export_dict()
        exported.update(scale_m_per_tile=SHIP_M_PER_TILE, deck_rows=dict(DECK_ROWS),
                        bulkheads=list(BULKHEADS), breached_from_x=BREACHED_FROM_X)
        return exported


@lru_cache(maxsize=4)
def _ship_terrain(width, height):
    tiles = [[0] * width for _ in range(height)]
    for row, (start, end) in DECK_SPANS.items():
        for x in range(start, end + 1):
            tiles[row][x] = INTERIOR
    for row, spans in OPEN_SPANS.items():
        for start, end in spans:
            for x in range(start, end + 1):
                tiles[row][x] = OPEN_DECK
    for x, (top, bottom) in STAIR_COLUMNS.items():
        for y in range(top, bottom + 1):
            tiles[y][x] = STAIRS

    elevation = [[round((WATERLINE_ROW - y) * ROW_M, 2) for _ in range(width)] for y in range(height)]
    # assumption: lower decks carry the highest perceived risk; never uses future flood state.
    zones = [[2 if y >= F else 1 if y >= D else 0 for _ in range(width)] for y in range(height)]

    assembly = boat_stations()
    spawn = [24, A]  # assumption: default view starts beside the forward grand staircase
    interior = [(x, y) for y in range(height) for x in range(width) if tiles[y][x] == INTERIOR]
    result = dict(
        width=width,
        height=height,
        seed=SHIP_MAP_SEED,
        vent=(36, G),  # iceberg contact point, kept under the world's hazard-origin name
        elevation=elevation,
        drainage={},
        tiles=tiles,
        zones=zones,
        valleys=[],
        stream_tiles=[],
        clean_springs=[],
        freshwater_tiles=[],
        spawn_pos=spawn,
        food_tiles=[],
        lifebelt_tiles=interior,  # assumption: lifebelts are stowed throughout the accommodation
        assembly_points=assembly,
        pdc_footprint=set(),
        lahar_footprint=set(),
    )
    routing_world = object.__new__(ShipWorld)
    routing_world.__dict__.update(result)
    routing_world.flooded = set()
    result["routes_from_spawn"] = [routing_world.path(spawn, [p]) for p in assembly[:2]]
    result["route_from_spawn"] = result["routes_from_spawn"][0]
    return result


def boat_stations():
    """Boat-deck tiles for the two davit groups, forward and aft, one entry per tile."""
    from engine.lifeboats import BOAT_TABLE
    return list(dict.fromkeys((row["x"], BOAT) for row in BOAT_TABLE))


def compartment_open(x, water_top_row):
    """A compartment admits water if breached, or once the sea overtops its bulkhead."""
    return x >= BREACHED_FROM_X or water_top_row <= BULKHEAD_TOP_ROW

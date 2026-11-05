"""Seeded progressive flooding, independent of decisions. Mirrors VolcanoModel.

Timing anchors come from sources cited below. The waterline shape between them
is an assumption chosen to meet those anchors on the schematic cutaway; it is
not a naval-architecture calculation.
"""
import copy
import random
from collections import OrderedDict

from engine.ship import BREACHED_FROM_X, BULKHEAD_TOP_ROW

HORIZON = 48  # assumption: 23:30 to 03:30 in five-minute steps; Carpathia's lights seen near 03:30
STEP_MINUTES = 5  # assumption: resolves a 160-minute sinking in 32 steps
START_HOUR, START_MINUTE = 23, 30


def clock_step(hour, minute):
    """Step index for a ship's-time clock reading on the night of 14-15 April."""
    elapsed = ((hour - START_HOUR) % 24) * 60 + minute - START_MINUTE
    return elapsed // STEP_MINUTES


COLLISION_STEP = clock_step(23, 40)  # Wikipedia, Sinking of the Titanic: 23:40 ship's time
UNCOVER_STEP = clock_step(0, 5)  # Wikipedia, Sinking of the Titanic: boats ordered uncovered 00:05
LOAD_STEP = clock_step(0, 25)  # assumption: widely repeated 00:25 loading order, not checked against the inquiry
ROCKET_STEPS = range(clock_step(0, 50), clock_step(1, 20) + 1)  # Wormstedt: rockets first fired 12:47; eight fired by 01:20
BOAT_DECK_AWASH_STEP = clock_step(2, 5)  # Wikipedia: water at the boat deck when collapsible D left
BRIDGE_UNDER_STEP = clock_step(2, 15)  # Wormstedt revised table: A and B float off as the bridge goes under
SINK_STEP = clock_step(2, 20)  # Wikipedia: gone from view at 02:20 ship's time

# (minutes after 23:30, water row at the bow, water row at the stern). Smaller row = higher water.
WATERLINE_KEYS = (
    (0, 21.5, 21.5), (10, 21.5, 21.5), (30, 19.5, 22.), (60, 18., 22.2), (90, 16.5, 22.5),
    (120, 14.5, 22.5), (150, 11., 22.), (155, 7.2, 21.), (165, -3., 17.), (170, -30., -8.),
)  # assumption: shaped to reach boat deck at the bridge by 02:05, bridge under 02:15, all gone 02:20
# (minutes after 23:30, degrees down by the head). Wikipedia summary: ~2 early, ~4.5 first hour,
# ~5 second hour, witnesses 30-45 near the end. Used for perception and cutscenes only.
TRIM_KEYS = ((0, 0.), (10, 0.), (20, 2.), (70, 4.5), (130, 5.), (150, 10.), (165, 35.), (170, 45.))
WATERLINE_JITTER = .2  # assumption: seeded row offset so seeds differ slightly; anchors hold within one step
KEEL_ROW = 27  # assumption: water enters a compartment at the bottom and climbs
FILL_ROWS_PER_STEP = .3  # assumption: rows climbed per step in the aftmost flooding compartment
FILL_BOW_FACTOR = 2.5  # assumption: the bow compartments, with the longest gash per volume, fill this much faster

_FORECAST_CACHE = OrderedDict()  # assumption: retain at most 16 immutable forecasts


def _interpolate(keys, minute):
    for before, after in zip(keys, keys[1:]):
        if before[0] <= minute <= after[0]:
            f = (minute - before[0]) / (after[0] - before[0])
            return [a + (b - a) * f for a, b in zip(before[1:], after[1:])]
    return list(keys[-1][1:])


def world_bow_x():
    return 38  # the last hull tile on the E deck


def water_row_at(x, bow_row, stern_row):
    return stern_row + (bow_row - stern_row) * (x - 1) / 37


class FloodModel:
    def __init__(self, seed, world, horizon=HORIZON, weather=None):
        key = (seed, horizon, world.width, world.height)
        if key in _FORECAST_CACHE:
            _FORECAST_CACHE.move_to_end(key)
            self.__dict__.update(copy.deepcopy(_FORECAST_CACHE[key]))
            return
        self._generate(seed, world, horizon)
        _FORECAST_CACHE[key] = copy.deepcopy(self.__dict__)
        if len(_FORECAST_CACHE) > 16:
            _FORECAST_CACHE.popitem(last=False)

    def _generate(self, seed, world, horizon):
        rng = random.Random(seed)
        offset = rng.uniform(-WATERLINE_JITTER, WATERLINE_JITTER)
        self.onset_step, self.sink_step = COLLISION_STEP, SINK_STEP
        self.phases, self.world_events, self.hazard_by_step = [], [], []
        walkable = [(x, y) for y in range(world.height) for x in range(world.width) if world.get_tile(x, y)]
        flooded = set()
        filling_since = {x: COLLISION_STEP for x in range(BREACHED_FROM_X, world.width)}
        for t in range(horizon):
            minute = t * STEP_MINUTES
            bow, stern = _interpolate(WATERLINE_KEYS, minute)
            if t >= COLLISION_STEP and t < SINK_STEP:
                bow, stern = bow + offset, stern + offset
            trim = _interpolate(TRIM_KEYS, minute)[0]
            top_row = min(bow, stern)
            new_flood = set()
            if t >= COLLISION_STEP:
                for x in range(world.width):  # later compartments start filling once the sea overtops them
                    if water_row_at(x, bow, stern) <= BULKHEAD_TOP_ROW:
                        filling_since.setdefault(x, t)
                for x, y in walkable:
                    if (x, y) in flooded or y < water_row_at(x, bow, stern):
                        continue
                    if y <= BULKHEAD_TOP_ROW or (x in filling_since and y >= self._fill_row(x, t, filling_since[x])):
                        new_flood.add((x, y))
            if t == SINK_STEP:  # whatever has not flooded yet goes down with the ship
                new_flood.update(p for p in walkable if p not in flooded)
            flooded |= new_flood
            rising = {q for p in flooded for q in world.neighbors(p)
                      if world.get_tile(*q) and q not in flooded}
            self.phases.append(self._phase(t))
            self.world_events.append(self._event(t))
            self.hazard_by_step.append(dict(
                new_flood=sorted(new_flood), rising=sorted(rising), waterline=[round(bow, 2), round(stern, 2)],
                top_row=round(top_row, 2), trim_deg=round(trim, 2), ash=0., wind_deg=0.,
            ))

    @staticmethod
    def _fill_row(x, t, since):
        forwardness = max(0., (x - BREACHED_FROM_X) / (world_bow_x() - BREACHED_FROM_X))
        rate = FILL_ROWS_PER_STEP * (1 + (FILL_BOW_FACTOR - 1) * forwardness)
        return KEEL_ROW - rate * (t - since)

    @staticmethod
    def _phase(t):
        if t < COLLISION_STEP:
            return "afloat"
        if t < LOAD_STEP:
            return "damage"
        if t < BOAT_DECK_AWASH_STEP:
            return "flooding"
        return "foundering" if t < SINK_STEP else "sunk"

    @staticmethod
    def _event(t):
        if t == COLLISION_STEP:
            return "tremor"
        if t in (UNCOVER_STEP, LOAD_STEP):
            return "gas_plume"
        if t in ROCKET_STEPS:
            return "ash_fall"
        return "eruption" if t in (BOAT_DECK_AWASH_STEP, BRIDGE_UNDER_STEP, SINK_STEP) else "none"

    def export_dict(self):
        return dict(onset_step=self.onset_step, sink_step=self.sink_step, phases=self.phases,
                    world_events=self.world_events,
                    hazard_by_step=[{**h, **{key: [list(p) for p in h[key]] for key in ("new_flood", "rising")}}
                                    for h in self.hazard_by_step])

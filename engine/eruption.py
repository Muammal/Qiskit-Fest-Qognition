"""Seeded AD 79 eruption timeline, independent of decisions. Mirrors VolcanoModel and FloodModel.

Combined chronology, about 32 hours: Plinian fall from Sparice et al. 2024, the two
short breaks from Scarpati et al. 2020, and a post-Plinian phase of about 12 hours
from search excerpts of the 2025 Journal of the Geological Society papers, which
could not be opened. Numerical choices are assumptions unless a source is cited.
"""

import copy
import math
import random
from collections import OrderedDict

from engine.city import GATE_TO_REGION, REGION_M_PER_TILE, RegionWorld

STEP_MINUTES = 15  # assumption: user's decision; a flow crossing the city happens inside one step
START_HOUR = 12  # about noon on day 1; the main phase follows at 13:00


def clock_step(day, hour, minute=0):
    """Step index for a clock reading on day 1 or day 2 of the eruption."""
    return ((day - 1) * 24 * 60 + (hour - START_HOUR) * 60 + minute) // STEP_MINUTES


SPARICE = "https://www.frontiersin.org/articles/10.3389/feart.2024.1386960/full"
SCARPATI_2020 = (
    "https://www.cambridge.org/core/journals/geological-magazine/article/pompeian-hiatuses-new-stratigraphic-"
    "data-highlight-pauses-in-the-course-of-the-ad-79-eruption-at-pompeii/0D717E1C9BBDFD4C10AE34A0F2B86ADF"
)
JGS_FLOWS = "https://www.lyellcollection.org/doi/abs/10.1144/jgs2024-072"
JPOST = "https://www.jpost.com/archaeology/archaeology-around-the-world/article-839410"
MTU = "https://geo.mtu.edu/volcanoes/boris/mirror/mirrored_html/VESUVIO_79.html"

HORIZON = clock_step(2, 20) + 1  # noon on day 1 to 20:00 on day 2
PLINIAN_STEP = clock_step(1, 13)  # Sparice 2024, around 1 p.m.
GREY_PUMICE_STEP = clock_step(1, 20)  # Sparice 2024, white pumice for 7 h
FALL_END_STEP = clock_step(2, 7)  # Sparice 2024, around 7 a.m. on the second day
QUAKE_STEP = clock_step(2, 7)  # assumption: paper orders it after the fall and before the strongest flow, no clock time
FIRST_FLOW_AT_TOWN_STEP = clock_step(2, 6, 30)  # Michigan Tech summary of Sigurdsson 1985; matches Scarpati's layer C1
FIRST_CITY_WIDE_STEP = clock_step(2, 7, 30)  # Scarpati 2020, layer C2 at 07:30
BREAK_STEP = clock_step(2, 7, 45)  # Scarpati 2020, two breaks in half an hour; this grid resolves them as one
DEVASTATING_STEP = clock_step(2, 8)  # Scarpati 2020, layer E at 08:00
PUMICE_TOTAL_M = 2.8  # Sparice 2024, maximum total thickness 2.8-2.9 m
FIRST_FLOW_REACH_TILES = 7  # Scarpati 2020, about 200 m past the north wall at 30 m per tile
TOWN_KM = 8.0  # Roman Ports: Vesuvius is 8 km away

# Seventeen flows in all: excerpt of the 2025 flows paper. The times are not in anything readable
# except where cited. Each entry is (step, runout in km, how much of the walled town it covers).
FIXED_FLOWS = (
    (clock_step(1, 15), 3.0, "none"),  # assumption: small flow during the Plinian phase
    (clock_step(1, 21), 3.0, "none"),  # assumption
    (clock_step(1, 23), 3.5, "none"),  # assumption
    (clock_step(2, 1), 4.0, "none"),  # Michigan Tech: first surge around 01:00, runout is an assumption
    (clock_step(2, 3), 5.0, "none"),  # assumption
    (FIRST_FLOW_AT_TOWN_STEP, TOWN_KM, "north_edge"),  # nearly reached Pompeii; Scarpati's C1 passed the north wall
    (FIRST_CITY_WIDE_STEP, 9.0, "north_half"),  # assumption: half the town, so a later break lets survivors move
    (DEVASTATING_STEP, 11.0, "all"),  # Scarpati 2020: "more devastating", overpassed Pompeii
)
LATER_FLOW_INTERVAL = 80 // STEP_MINUTES  # Jerusalem Post only: about 80 minutes between flows; weak
LATER_FLOW_COUNT = 9  # makes seventeen with FIXED_FLOWS
LATER_FLOW_RUNOUT_KM = (9.0, 13.0)  # assumption: Scarpati lists many flow deposits at Pompeii after layer E

COLLAPSE_START_M, COLLAPSE_SPAN_M = 1.0, 3.6  # assumption: half of roofs fail by 2.8 m; no source gives a rate
QUAKE_COLLAPSE_FRACTION = 0.3  # assumption: share of standing buildings the quake brings down
QUAKE_FELT_STEPS = (clock_step(1, 22), clock_step(2, 2))  # assumption: times; Sparice cites shaking that night
TEMPERATURE_C = {"august": 27.0, "autumn": 17.0}  # assumption: no reading exists for either date
DEBRIS_AXIS_DEG = 135  # assumption: fall carried southeast from Vesuvius; sources say south of the volcano
FALL_WIDTH_TILES, FALL_LENGTH_TILES = 9.0, 60.0  # assumption: plume shape on the region map
DARK_VISIBILITY, NIGHT_VISIBILITY = 0.4, 0.25  # assumption: pumice and ash cut the view; Pliny describes darkness

_FORECAST_CACHE = OrderedDict()  # assumption: retain at most 16 immutable forecasts

PROVENANCE = {
    "plinian_start": dict(value="about 13:00", status="sourced", url=SPARICE),
    "white_to_grey": dict(value="after 7 h", status="sourced", url=SPARICE),
    "fall_end": dict(value="about 07:00 day 2", status="sourced", url=SPARICE),
    "pumice_total": dict(value="2.8-2.9 m", status="sourced", url=SPARICE),
    "quake_magnitude": dict(value="M 6, not used directly", status="sourced", url=SPARICE),
    "quake_time": dict(value="07:00 day 2", status="assumption", url=SPARICE, note="order from the paper, time assumed"),
    "first_flow_at_town": dict(
        value="06:30, 200 m into town", status="sourced", url=SCARPATI_2020, note="time from Michigan Tech summary of Sigurdsson 1985: " + MTU
    ),
    "flows_c2_and_e": dict(value="07:30 and 08:00", status="sourced", url=SCARPATI_2020),
    "break": dict(value="30 minutes in total", status="sourced", url=SCARPATI_2020),
    "flow_count": dict(value="17", status="excerpt", url=JGS_FLOWS),
    "post_plinian_length": dict(value="about 12 h", status="excerpt", url=JGS_FLOWS),
    "flow_interval": dict(value="about 80 minutes", status="news", url=JPOST),
    "end_time": dict(value="about 20:00 day 2", status="news", url=JPOST, note="also 32 h from noon, by arithmetic"),
    "collapse_rate": dict(value="half of roofs by 2.8 m", status="assumption", url=None),
    "temperature": dict(value="27 C or 17 C", status="assumption", url=None),
}


def pumice_depth(t):
    """Metres of pumice in Pompeii at step t, falling evenly between the sourced start and end."""
    fraction = (t - PLINIAN_STEP) / (FALL_END_STEP - PLINIAN_STEP)
    return PUMICE_TOTAL_M * min(1.0, max(0.0, fraction))


def _region_fall_share(x, y, vent):
    """Share of Pompeii's pumice depth at a region tile: a plume carried along DEBRIS_AXIS_DEG."""
    axis = math.radians(DEBRIS_AXIS_DEG)
    ax, ay = math.sin(axis), -math.cos(axis)
    dx, dy = x - vent[0], y - vent[1]
    along, across = dx * ax + dy * ay, abs(dx * ay - dy * ax)
    if along <= 0:
        return 0.0
    return math.exp(-0.5 * (across / FALL_WIDTH_TILES) ** 2) * math.exp(-along / FALL_LENGTH_TILES)


class EruptionModel:
    def __init__(self, seed, world, horizon=HORIZON, weather=None, region=None, date="august", quake=True):
        key = (seed, horizon, date, quake)
        if key in _FORECAST_CACHE:
            _FORECAST_CACHE.move_to_end(key)
            self.__dict__.update(copy.deepcopy(_FORECAST_CACHE[key]))
            return
        self._generate(seed, world, region or RegionWorld(), horizon, date, quake)
        _FORECAST_CACHE[key] = copy.deepcopy(self.__dict__)
        if len(_FORECAST_CACHE) > 16:
            _FORECAST_CACHE.popitem(last=False)

    def _flows(self, rng):
        later = [(DEVASTATING_STEP + (i + 1) * LATER_FLOW_INTERVAL, rng.uniform(*LATER_FLOW_RUNOUT_KM), "all") for i in range(LATER_FLOW_COUNT)]
        return list(FIXED_FLOWS) + later

    def _generate(self, seed, world, region, horizon, date, quake):
        rng = random.Random(seed + 79)
        self.date, self.quake_enabled = date, quake
        self.onset_step, self.first_city_flow_step = PLINIAN_STEP, FIRST_CITY_WIDE_STEP
        self.vent = region.vent
        self.flows = self._flows(rng)
        flows_by_step = {step: (runout, reach) for step, runout, reach in self.flows}
        self.phases, self.world_events, self.hazard_by_step = [], [], []
        buildings = [(x, y) for y in range(world.height) for x in range(world.width) if world.get_tile(x, y) == 4]
        # A roof's strength is fixed in advance, so which roofs fail never depends on anyone's choice.
        roof_limit = {p: rng.uniform(COLLAPSE_START_M, COLLAPSE_START_M + COLLAPSE_SPAN_M) for p in buildings}
        quake_order = rng.sample(buildings, len(buildings))
        standing = set(buildings)
        town_tiles = [(x, y) for y in range(world.height) for x in range(world.width) if world.get_tile(x, y) and (x, y) not in world.exit_road_tiles]
        walls_top = min(y for _, y in world.wall_tiles)
        region_land = [(x, y) for y in range(region.height) for x in range(region.width) if region.get_tile(x, y)]
        for t in range(horizon):
            depth = pumice_depth(t)
            new_collapse = {p for p in standing if roof_limit[p] <= depth}
            quake_now = quake and t == QUAKE_STEP
            if quake_now:
                keep = standing - new_collapse
                count = round(len(keep) * QUAKE_COLLAPSE_FRACTION)
                new_collapse |= set([p for p in quake_order if p in keep][:count])
            standing -= new_collapse
            runout, reach = flows_by_step.get(t, (0.0, "none"))
            if reach == "all":
                active = set(town_tiles)
            elif reach == "north_half":
                active = {p for p in town_tiles if p[1] <= world.height // 2}
            elif reach == "north_edge":
                active = {p for p in town_tiles if p[1] <= walls_top + FIRST_FLOW_REACH_TILES}
            else:
                active = set()
            region_flow = {p for p in region_land if runout and math.dist(p, region.vent) * REGION_M_PER_TILE <= runout * 1000}
            digit = str(min(9, round(depth / PUMICE_TOTAL_M * 9)))
            self.phases.append(self._phase(t))
            self.world_events.append(self._event(t, runout, quake_now))
            self.hazard_by_step.append(
                dict(
                    pumice_m=round(depth, 3),
                    new_collapse=sorted(new_collapse),
                    active_pdc=sorted(active),
                    region_active_pdc=sorted(region_flow),
                    flow_runout_km=round(runout, 2),
                    quake=quake_now,
                    ash=round(min(1.0, depth / PUMICE_TOTAL_M), 3),
                    ash_grid=[digit * world.width] * world.height,
                    region_ash_grid=self._region_ash_grid(region, depth),
                    visibility=self._visibility(t),
                    temperature_c=TEMPERATURE_C[date],
                    wind_deg=float(DEBRIS_AXIS_DEG),
                )
            )

    @staticmethod
    def _region_ash_grid(region, depth):
        home = _region_fall_share(*GATE_TO_REGION["nocera"], region.vent) or 1.0
        rows = []
        for y in range(region.height):
            row = ""
            for x in range(region.width):
                share = _region_fall_share(x, y, region.vent) / home
                row += str(min(9, round(share * depth / PUMICE_TOTAL_M * 9)))
            rows.append(row)
        return rows

    @staticmethod
    def _visibility(t):
        if PLINIAN_STEP <= t < clock_step(1, 19):
            return DARK_VISIBILITY
        if clock_step(1, 19) <= t <= clock_step(2, 6):
            return NIGHT_VISIBILITY
        return DARK_VISIBILITY if t >= PLINIAN_STEP else 1.0

    @staticmethod
    def _phase(t):
        if t < PLINIAN_STEP:
            return "opening"
        if t < GREY_PUMICE_STEP:
            return "white_pumice"
        if t < FALL_END_STEP:
            return "grey_pumice"
        return "flows"

    @staticmethod
    def _event(t, runout, quake_now):
        """What could be noticed in town this step, under the mind's event names."""
        if quake_now or t in QUAKE_FELT_STEPS:
            return "tremor"
        if t == PLINIAN_STEP or runout:
            return "eruption"
        if PLINIAN_STEP < t < FALL_END_STEP:
            return "ash_fall"
        return "none"

    def export_dict(self):
        return dict(
            date=self.date,
            quake_enabled=self.quake_enabled,
            onset_step=self.onset_step,
            first_city_flow_step=self.first_city_flow_step,
            vent=list(self.vent),
            flows=[list(flow) for flow in self.flows],
            phases=self.phases,
            world_events=self.world_events,
            hazard_by_step=[
                {**h, **{key: [list(p) for p in h[key]] for key in ("new_collapse", "active_pdc", "region_active_pdc")}} for h in self.hazard_by_step
            ],
            provenance=PROVENANCE,
        )

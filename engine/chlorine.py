"""Chlorine leak at the Waterloo site, precomputed so it never depends on anyone's decision.

A demonstration, not a validated dispersion model. Gas moves tile to tile, is blocked by solid walls,
drifts with the wind outdoors and thins out over time. The leak's place, size and length are unknown,
so each is a setting. See docs/WATERLOO_SOURCES.md.
"""

from collections import OrderedDict

import numpy as np

from engine.site import SITE_M_PER_TILE

STEP_SECONDS = 10  # user's decision
HORIZON = 2 * 3600 // STEP_SECONDS + 1  # user's decision: 2 hours, about Edmonton's closure
SUBSTEPS = 8  # numerical: keeps the wind and spread calculation stable
LEAK_START_STEP = 6  # assumption: one minute in, so the run opens before the leak
LEAK_MINUTES = 15.0  # assumption: length unknown; a setting
SOURCE_PPM = 22.0  # Edmonton 2018, Global News; where it was measured is not stated
START_HOUR = 14  # assumption: time of day unknown
LEAK_SITES = {  # assumption: no source gives the place or the chlorine storage
    "pool_side": (20, 21),
    "north_end": (18, 9),
    "deck": (20, 23),
}
DEFAULT_LEAK_SITE = "pool_side"
INDOOR_SPREAD_M2_S = 0.25  # assumption
OUTDOOR_SPREAD_M2_S = 2.0  # assumption
INDOOR_LOSS_PER_S = 4 / 3600  # assumption: 4 air changes per hour
OUTDOOR_LOSS_PER_S = 0.02  # assumption: mixing upward into open air

# Modelled weather, Open-Meteo archive for 43.47, -80.51, 30 July 2012: hour: (km/h, degrees wind comes from).
WIND_BY_HOUR = {
    9: (5.1, 278),
    10: (6.3, 283),
    11: (6.2, 277),
    12: (5.2, 254),
    13: (5.7, 235),
    14: (6.4, 223),
    15: (7.4, 219),
    16: (8.2, 221),
    17: (9.9, 224),
    18: (12.4, 216),
    19: (11.9, 215),
    20: (9.7, 211),
    21: (8.3, 198),
}
ODOUR_PPM = 0.31  # EPA technical support document, section 1, citing Amoore and Hautala 1983
AEGL_PPM = {  # EPA, final values, ppm
    1: {10: 0.5, 30: 0.5, 60: 0.5},
    2: {10: 2.8, 30: 2.8, 60: 2.0},
    3: {10: 50.0, 30: 28.0, 60: 20.0},
}
AEGL_MEANING = {0: "below AEGL-1", 1: "above AEGL-1, discomfort", 2: "above AEGL-2, serious or lasting effects", 3: "above AEGL-3, risk to life"}

EPA_AEGL = "https://www.epa.gov/aegl/chlorine-results-aegl-program"
EPA_TSD = "https://www.epa.gov/sites/default/files/2014-11/documents/tsd56.pdf"
GLOBAL = "https://globalnews.ca/news/4060660/chlorine-leak-forces-evacuation-of-edmonton-rec-centre"
WEATHER = (
    "https://archive-api.open-meteo.com/v1/archive?latitude=43.47&longitude=-80.51&start_date=2012-07-30"
    "&end_date=2012-07-30&hourly=temperature_2m,wind_speed_10m,wind_direction_10m,precipitation&timezone=America%2FToronto"
)
PROVENANCE = {
    "aegl_values": dict(value="see AEGL_PPM", status="sourced", url=EPA_AEGL, note="final values; planning limits, not predictions"),
    "odour": dict(value="0.31 ppm", status="sourced", url=EPA_TSD, note="range 0.2-0.4; people differ and it fades"),
    "source_level": dict(value="22 ppm", status="sourced", url=GLOBAL, note="another building; a modelling choice to reuse it"),
    "wind": dict(value="hourly", status="sourced", url=WEATHER, note="reanalysis estimate, not a station reading"),
    "spread_model": dict(value="tile-to-tile", status="assumption", url=None, note="not validated; ignores heavy-gas sinking"),
    "spread_rates": dict(value="0.25 and 2 sq m/s", status="assumption", url=None, note=""),
    "losses": dict(value="4 air changes per hour; 0.02 per s outdoors", status="assumption", url=None, note=""),
    "leak_site": dict(value="pool side", status="assumption", url=None, note="setting; real place unknown"),
    "leak_length": dict(value="15 minutes", status="assumption", url=None, note="setting; real length unknown"),
    "start_time": dict(value="14:00", status="assumption", url=None, note="real time unknown"),
    "open_doors": dict(value="doors always pass gas", status="assumption", url=None, note="likely overstates outdoor gas early on"),
}
_CACHE = OrderedDict()


def wind_at(seconds, start_hour=START_HOUR):
    """Wind speed in m/s and the degrees it comes from, interpolated between hourly values."""
    hour = start_hour + seconds / 3600
    low = min(max(WIND_BY_HOUR), max(min(WIND_BY_HOUR), int(hour)))
    high = min(max(WIND_BY_HOUR), low + 1)
    share = min(1.0, max(0.0, hour - low))
    speed = WIND_BY_HOUR[low][0] + (WIND_BY_HOUR[high][0] - WIND_BY_HOUR[low][0]) * share
    degrees = WIND_BY_HOUR[low][1] + (WIND_BY_HOUR[high][1] - WIND_BY_HOUR[low][1]) * share
    return speed / 3.6, degrees


def exposure_level(ppm_series, step_seconds=STEP_SECONDS):
    """Highest AEGL level exceeded by the average over any 10, 30 or 60 minute window."""
    series = np.asarray(ppm_series, dtype=float)
    if not len(series):
        return 0
    totals = np.concatenate(([0.0], np.cumsum(series)))
    level = 0
    for candidate, limits in AEGL_PPM.items():
        for minutes, limit in limits.items():
            window = minutes * 60 // step_seconds
            count = min(window, len(series))
            # A shorter stay still counts over the full window, as zero exposure for the remainder.
            if (totals[count:] - totals[:-count]).max() / window >= limit:
                level = max(level, candidate)
    return level


class ChlorineModel:
    def __init__(self, seed, world, horizon=HORIZON, leak_site=DEFAULT_LEAK_SITE, source_ppm=SOURCE_PPM, leak_minutes=LEAK_MINUTES, start_hour=START_HOUR):
        key = (horizon, leak_site, source_ppm, leak_minutes, start_hour)
        if key not in _CACHE:
            _CACHE[key] = self._generate(world, horizon, leak_site, source_ppm, leak_minutes, start_hour)
            if len(_CACHE) > 16:
                _CACHE.popitem(last=False)
        self.ppm = _CACHE[key]  # shared and read-only
        self.seed, self.horizon, self.leak_site, self.source_ppm = seed, horizon, leak_site, source_ppm
        self.leak_minutes, self.start_hour = leak_minutes, start_hour
        self.source = LEAK_SITES[leak_site]
        self.leak_end_step = LEAK_START_STEP + round(leak_minutes * 60 / STEP_SECONDS)
        self.phases = [self._phase(t) for t in range(horizon)]
        self.world_events = ["chlorine_leak" if t == LEAK_START_STEP else "none" for t in range(horizon)]
        self.hazard_by_step = [
            dict(
                peak_ppm=round(float(self.ppm[t].max()), 3),
                wind_m_s=round(wind_at(t * STEP_SECONDS, start_hour)[0], 2),
                wind_deg=round(wind_at(t * STEP_SECONDS, start_hour)[1], 1),
            )
            for t in range(horizon)
        ]

    def _phase(self, t):
        if t < LEAK_START_STEP:
            return "before"
        return "leaking" if t < self.leak_end_step else "after"

    def ppm_at(self, t, p):
        return float(self.ppm[min(t, self.horizon - 1), p[1], p[0]])

    @staticmethod
    def _generate(world, horizon, leak_site, source_ppm, leak_minutes, start_hour):
        height, width = world.height, world.width
        solid = np.zeros((height, width), dtype=bool)
        building_walls = {p for p in world.wall_tiles if any(q in world.areas["indoors"] for q in world.neighbors(p))}
        for x, y in building_walls | set(world.nearby_building_tiles):
            solid[y, x] = True
        indoors = np.zeros((height, width), dtype=bool)
        for x, y in world.areas["indoors"]:
            indoors[y, x] = True
        for x, y in world.doors.values():
            solid[y, x], indoors[y, x] = False, True
        outdoors = ~solid & ~indoors
        spread = np.where(indoors, INDOOR_SPREAD_M2_S, OUTDOOR_SPREAD_M2_S)
        spread[solid] = 0.0
        delta = STEP_SECONDS / SUBSTEPS
        loss = 1 - delta * np.where(indoors, INDOOR_LOSS_PER_S, OUTDOOR_LOSS_PER_S)
        east_rate = np.minimum(spread[:, :-1], spread[:, 1:]) * delta / SITE_M_PER_TILE**2
        south_rate = np.minimum(spread[:-1, :], spread[1:, :]) * delta / SITE_M_PER_TILE**2
        source = LEAK_SITES[leak_site]
        leak_end = LEAK_START_STEP + round(leak_minutes * 60 / STEP_SECONDS)
        grid = np.zeros((height, width))
        result = np.zeros((horizon, height, width), dtype=np.float32)
        for t in range(horizon):
            speed, degrees = wind_at(t * STEP_SECONDS, start_hour)
            toward = np.radians(degrees + 180)
            east, south = speed * np.sin(toward), -speed * np.cos(toward)
            for _ in range(SUBSTEPS):
                if LEAK_START_STEP <= t < leak_end:
                    grid[source[1], source[0]] = source_ppm
                east_flux = (grid[:, 1:] - grid[:, :-1]) * east_rate
                south_flux = (grid[1:, :] - grid[:-1, :]) * south_rate
                change = np.zeros_like(grid)
                change[:, :-1] += east_flux
                change[:, 1:] -= east_flux
                change[:-1, :] += south_flux
                change[1:, :] -= south_flux
                change += _drift(grid, outdoors, east * delta / SITE_M_PER_TILE, south * delta / SITE_M_PER_TILE)
                grid = np.clip((grid + change) * loss, 0.0, None)
                grid[solid] = 0.0
            result[t] = grid
        result.setflags(write=False)
        return result

    def export_dict(self):
        minutes = range(0, self.horizon, 6)
        return dict(
            leak_site=self.leak_site,
            source=list(self.source),
            source_ppm=self.source_ppm,
            leak_minutes=self.leak_minutes,
            start_hour=self.start_hour,
            leak_start_step=LEAK_START_STEP,
            leak_end_step=self.leak_end_step,
            step_seconds=STEP_SECONDS,
            phases=self.phases,
            world_events=self.world_events,
            hazard_by_step=self.hazard_by_step,
            ppm_by_minute=[np.round(self.ppm[t], 3).tolist() for t in minutes],
            provenance=PROVENANCE,
        )


def _drift(grid, outdoors, east, south):
    """Upwind movement of outdoor gas. East and south are shares of a tile per substep."""
    change = np.zeros_like(grid)
    if east:
        flow = grid * abs(east) * outdoors
        if east > 0:
            moved = flow[:, :-1] * outdoors[:, 1:]
            change[:, :-1] -= moved
            change[:, 1:] += moved
            change[:, -1] -= flow[:, -1]
        else:
            moved = flow[:, 1:] * outdoors[:, :-1]
            change[:, 1:] -= moved
            change[:, :-1] += moved
            change[:, 0] -= flow[:, 0]
    if south:
        flow = grid * abs(south) * outdoors
        if south > 0:
            moved = flow[:-1, :] * outdoors[1:, :]
            change[:-1, :] -= moved
            change[1:, :] += moved
            change[-1, :] -= flow[-1, :]
        else:
            moved = flow[1:, :] * outdoors[:-1, :]
            change[1:, :] -= moved
            change[:-1, :] += moved
            change[0, :] -= flow[0, :]
    return change

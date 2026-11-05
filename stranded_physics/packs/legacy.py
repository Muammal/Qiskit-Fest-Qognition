"""Offline adapter for the fictional volcano island's unchanged hazards.

PackSimulation uses its own body model, so survival differs from the old engine.
No agent is constructed or read when building this pack.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from engine.events import EventGenerator
from engine.simulation import DEFAULT_STEPS
from engine.volcano import VolcanoModel
from engine.world import IslandWorld, MAP_SEED, SCALE_M_PER_TILE
from stranded_physics.core.api import GridSpec, InterfaceError, ScenarioSpec, TimeAxis
from stranded_physics.core.fields import spec
from stranded_physics.packs.builder import Pack, build_pack

LEGACY_RAIN_MM_H = 2.  # assumption: representative T0 rain, below the runtime's storm threshold.
LEGACY_STORM_MM_H = 10.  # assumption: representative T0 storm, at least 5 mm/h for runtime labelling.
LEGACY_LAHAR_M = 1.  # assumption: binary old lahar becomes positive depth; any positive depth is lethal in the runtime.
LEGACY_ASH_FULL_KG_M2 = 1.  # assumption: old full-scale ash maps to one kg/m²; affects perceived ash, not a measured load.
LEGACY_DT_S = 7200.  # assumption: old two-hour frames are held constant until the next frame.
LEGACY_LOCAL_HOUR = 8  # assumption: old simulation's local start hour.
LEGACY_T0 = datetime(2000, 1, 1, 8, tzinfo=timezone.utc)  # assumption: arbitrary epoch, with local time equal to UTC.
LEGACY_CRS = "LOCAL:legacy"  # assumption: fictional Cartesian metres; no geographic registration.
PHASE_CODES = {"unrest": 0, "escalating": 1, "erupting": 2, "fading": 3}
ASH_DIGIT_FULL = 9  # assumption: old ash encoding's full-scale digit.


OUTPUTS = ("terrain.elevation", "terrain.land_mask", "terrain.land_cover", "terrain.zone", "atmos.rain_rate", "eruption.phase", "eruption.tremor",
           "eruption.gas", "eruption.explosion", "pdc.active", "pdc.arrival", "lahar.depth", "lava.footprint", "tephra.deposit_load")


def _forecast_arrays(grid: GridSpec, time: TimeAxis, world, volcano, weather) -> dict[str, np.ndarray]:
    """The old forecast, translated without resampling."""
    if (grid.nx, grid.ny, grid.dx_m) != (world.width, world.height, SCALE_M_PER_TILE):
        raise InterfaceError("legacy grid must preserve the old tiles and scale")
    if time.dt_s != LEGACY_DT_S or time.n != DEFAULT_STEPS:
        raise InterfaceError("legacy time must preserve the old two-hour horizon")
    if any(len(values) != time.n for values in (weather, volcano.phases, volcano.world_events, volcano.hazard_by_step)):
        raise InterfaceError("legacy forecast does not match the time axis")
    arrays = {
        "terrain.elevation": np.asarray(world.elevation),
        "terrain.land_mask": np.asarray(world.elevation) > 0,
        "terrain.land_cover": np.asarray(world.tiles),
        "terrain.zone": np.asarray(world.zones),
        "atmos.rain_rate": np.array([{"calm": 0., "rain": LEGACY_RAIN_MM_H, "storm": LEGACY_STORM_MM_H}[w] for w in weather]),
        "eruption.phase": np.array([PHASE_CODES[p] for p in volcano.phases]),
    }
    for name, event in (("tremor", "tremor"), ("gas", "gas_plume"), ("explosion", "eruption")):
        arrays[f"eruption.{name}"] = np.array([e == event for e in volcano.world_events])
    shape = (time.n, grid.ny, grid.nx)
    for name in ("pdc.active", "lahar.depth", "lava.footprint", "tephra.deposit_load"):
        arrays[name] = np.zeros(shape)
    arrival = np.full(shape[1:], np.inf)
    lava = np.zeros(shape[1:])
    for k, hazard in enumerate(volcano.hazard_by_step):
        for x, y in hazard["active_pdc"]:
            arrays["pdc.active"][k, y, x] = 1.
            if np.isinf(arrival[y, x]):
                arrival[y, x] = k * time.dt_s
        for x, y in hazard["active_lahar"]:
            arrays["lahar.depth"][k, y, x] = LEGACY_LAHAR_M
        for x, y in hazard["new_lava"]:
            lava[y, x] = 1.
        arrays["lava.footprint"][k] = lava
        arrays["tephra.deposit_load"][k] = np.array([[int(digit) for digit in row] for row in hazard["ash_grid"]]) / ASH_DIGIT_FULL * LEGACY_ASH_FULL_KG_M2
    arrays["pdc.arrival"] = arrival
    return arrays


class LegacyPart:
    """One category's share of the old forecast. Each category writes only its own fields, the same rule as every other model."""

    tier = "T0"
    inputs = ()
    parameters = ()

    def __init__(self, category: str, arrays: dict[str, np.ndarray], grid: GridSpec, time: TimeAxis) -> None:
        self.id, self.arrays, self.grid, self.time = category, arrays, grid, time
        self.outputs = tuple(spec(name) for name in OUTPUTS if name.startswith(f"{category}."))

    def check_validity(self, fields) -> list[str]:
        return []

    def run(self, fields, rng: np.random.Generator) -> dict[str, float]:
        for output in self.outputs:
            fields.put(output.name, self.arrays[output.name], output.unit, None if output.kind == "series" else self.grid, self.time if output.kind in ("series", "frames") else None)
        return {}


def legacy_scenario(seed: int) -> ScenarioSpec:
    world = IslandWorld(seed=MAP_SEED, scenario="volcano")
    weather = EventGenerator(seed).weather
    volcano = VolcanoModel(seed, world, weather=weather)
    # assumption: arbitrary origin at the north-west corner, with north-up rows.
    grid = GridSpec(LEGACY_CRS, 0., 0., SCALE_M_PER_TILE, world.width, world.height)
    time = TimeAxis(LEGACY_T0, LEGACY_DT_S, DEFAULT_STEPS)
    sites = {name: [grid.centre(y, x) for x, y in tiles] for name, tiles in (
        ("spawn", [world.spawn_pos]), ("vent", [world.vent]),
        ("assembly", world.assembly_points), ("water", world.freshwater_tiles), ("food", world.food_tiles),
    )}
    arrays = _forecast_arrays(grid, time, world, volcano, tuple(weather))
    parts = tuple(LegacyPart(category, arrays, grid, time) for category in sorted({name.split(".")[0] for name in OUTPUTS}))
    return ScenarioSpec("legacy_island", grid, grid, time, LEGACY_LOCAL_HOUR, parts, sites)


def build_legacy_pack(seed: int) -> Pack:
    return build_pack(legacy_scenario(seed), seed)

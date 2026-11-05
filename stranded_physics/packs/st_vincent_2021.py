"""The real April 2021 St Vincent scenario: each category's T1 model, on the real island."""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from stranded_physics.core.api import GridSpec, InterfaceError, ScenarioSpec, XY
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.atmos.model import Atmos
from stranded_physics.domains.eruption.model import Eruption
from stranded_physics.domains.exposure.model import Exposure
from stranded_physics.domains.lahar.model import Lahar
from stranded_physics.domains.pdc.model import Pdc
from stranded_physics.domains.tephra.model import Tephra
from stranded_physics.domains.terrain.model import SETTINGS as TERRAIN, ST_VINCENT_GRID as GRID, Terrain
from stranded_physics.packs.builder import Pack, build_pack
from stranded_physics.st_vincent import TIME, UTM, VENT_XY, to_utm

SCENARIO_TIME = replace(TIME, n=48)  # 96 hours, so the published first flow, 21:30 UTC on 10 April, is followed by a night of activity.
CONTRACT_GRID = GridSpec(UTM, 687000., 1481000., 500., 40, 40)  # The contract's 40 x 40 tiles, on the northern 20 km of the island.
LOCAL_HOUR_AT_START = 20  # 00:00 UTC on 8 April is 20:00 the evening before, at UTC-4.
# Village positions are from memory, to about 500 m, and every site is snapped to land below. Check these against a gazetteer.
SPAWNS = {"chateaubelair": (-61.243, 13.283), "richmond": (-61.226, 13.317)}  # West-coast villages in the 2021 red zone. Richmond lies by the Wallibou valley.
ASSEMBLY_LONLAT = ((-61.267, 13.233), (-61.140, 13.240))  # Barrouallie to the south-west, Colonarie to the south-east.
MOST_SNAP_M = 1500.


def _nearest(mask: np.ndarray, point: XY) -> XY:
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        raise InterfaceError("no cell qualifies for this site")
    xs, ys = GRID.x0_m + (cols + .5) * GRID.dx_m, GRID.y0_m - (rows + .5) * GRID.dx_m
    best = int(np.argmin(np.hypot(xs - point[0], ys - point[1])))
    return float(xs[best]), float(ys[best])


def place_sites(starts_lonlat: list[tuple[float, float]], assembly_lonlat: list[tuple[float, float]], vent: XY | None) -> dict[str, list[XY]]:
    """Sites from the real surface: people on land, and water at the nearest real channel, not at a chosen spot."""
    domain = Terrain()
    store = FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    land = store.get("terrain.land_mask", "dimensionless") > 0
    channels = land & (store.get("terrain.flow_accumulation", "m**2") >= TERRAIN["channel_area"])
    wanted = [*[to_utm(p) for p in starts_lonlat], *[to_utm(p) for p in assembly_lonlat]]
    placed = [_nearest(land, point) for point in wanted]
    for point, site in zip(wanted, placed):
        if math.dist(point, site) > MOST_SNAP_M:
            raise InterfaceError(f"site {point} is {math.dist(point, site):.0f} m from land; check its coordinates")
    return {"spawn": placed[:len(starts_lonlat)], "vent": [vent] if vent else [], "assembly": placed[len(starts_lonlat):], "water": [_nearest(channels, point) for point in placed]}


def sites(spawn: str = "chateaubelair") -> dict[str, list[XY]]:
    return place_sites([SPAWNS[spawn]], list(ASSEMBLY_LONLAT), VENT_XY)


def scenario(spawn: str = "chateaubelair") -> ScenarioSpec:
    domains = (Terrain(), Atmos(SCENARIO_TIME), Eruption(SCENARIO_TIME), Tephra(GRID, SCENARIO_TIME, VENT_XY), Exposure(GRID, SCENARIO_TIME),
               Pdc(GRID, SCENARIO_TIME, VENT_XY), Lahar(GRID, SCENARIO_TIME, VENT_XY))
    return ScenarioSpec(f"st_vincent_2021_{spawn}", GRID, CONTRACT_GRID, SCENARIO_TIME, LOCAL_HOUR_AT_START, domains, sites(spawn))


def build(seed: int, spawn: str = "chateaubelair") -> Pack:
    return build_pack(scenario(spawn), seed)

"""Compares the flow model on real St Vincent terrain with what Cole et al. report. Each mode ends with a JSON line for the gates.

    python -m stranded_physics.validation.st_vincent_flows west_sea|sea_off_west|southeast_reach_km|first_flow_h|lahar_frames|sensitivity
"""
from __future__ import annotations

import json
import sys

import numpy as np
from scipy.ndimage import binary_dilation

from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.pdc import model as pdc_model
from stranded_physics.domains.pdc.model import Pdc, flow_footprint
from stranded_physics.domains.terrain.model import ST_VINCENT_GRID as GRID, Terrain
from stranded_physics.st_vincent import TIME, VENT_XY

WEST_FLANK = (225., 315.)  # The paper says "West flank" without bearings, so this sector is an assumption, set with the target.
SOUTHEAST = (112., 157.)


def terrain_store() -> FieldStore:
    domain = Terrain()
    problems = domain.check_validity(None)
    if problems:
        raise SystemExit("; ".join(problems))
    store = FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    return store


def bearings_and_distance() -> tuple[np.ndarray, np.ndarray]:
    xs = GRID.x0_m + (np.arange(GRID.nx) + .5) * GRID.dx_m - VENT_XY[0]
    ys = GRID.y0_m - (np.arange(GRID.ny) + .5) * GRID.dx_m - VENT_XY[1]
    x, y = np.meshgrid(xs, ys)
    return (np.degrees(np.arctan2(x, y)) + 360.) % 360., np.hypot(x, y)


def in_sector(bearing: np.ndarray, sector: tuple[float, float]) -> np.ndarray:
    return (bearing >= sector[0]) & (bearing <= sector[1])


def footprint_summary(store: FieldStore) -> dict[str, float]:
    land = store.get("terrain.land_mask", "dimensionless") > 0
    travel = flow_footprint(store.get("terrain.elevation", "m"), land, store.get("terrain.height_above_drainage", "m"), GRID, VENT_XY)
    reached = np.isfinite(travel)
    bearing, distance = bearings_and_distance()
    at_sea = reached & binary_dilation(~land, structure=np.ones((3, 3)))
    west = in_sector(bearing, WEST_FLANK)
    southeast = reached & in_sector(bearing, SOUTHEAST)
    return {"west_sea": float((at_sea & west).any()),
            "sea_off_west": float((at_sea & ~west).sum() / max(at_sea.sum(), 1)),
            "southeast_reach_km": float(distance[southeast].max() / 1000.) if southeast.any() else 0.,
            "reached_km2": float(reached.sum() * GRID.dx_m ** 2 / 1e6), "max_reach_km": float(distance[reached].max() / 1000.),
            "sea_cells": int(at_sea.sum()), "slowest_arrival_min": float(travel[reached].max() / 60.)}


def first_flow_hours(store: FieldStore) -> float:
    store.put("eruption.explosion", np.zeros(48), "dimensionless", time=_axis())
    domain = Pdc(GRID, _axis(), VENT_XY)
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    return float(store.stored("pdc.arrival").data.min() / 3600.)


def _axis():
    from dataclasses import replace
    return replace(TIME, n=48)


def lahar_frames() -> dict[str, float]:
    from stranded_physics.packs.st_vincent_2021 import build
    pack = build(1)
    depth = np.asarray([pack.frame("lahar.depth", t * pack.time.dt_s) for t in range(pack.time.n)])
    rain = pack.series("atmos.rain_rate")
    return {"lahar_frames": int((depth.reshape(pack.time.n, -1).max(axis=1) > 0).sum()), "max_rain_mm_h": float(rain.max())}


def sensitivity(store: FieldStore) -> dict[str, dict[str, float]]:
    """Reach under other assumed settings, to show how much the verdicts hang on them. For reporting, never for tuning."""
    table = {}
    original = dict(pdc_model.SETTINGS)
    for ratio in (.1, .2, .3):
        for height in (500., 1000., 1500.):
            pdc_model.SETTINGS.update(height_over_length=ratio, collapse_height=height)
            summary = footprint_summary(store)
            table[f"HL{ratio}_Hc{int(height)}"] = {k: round(summary[k], 2) for k in ("west_sea", "sea_off_west", "southeast_reach_km", "reached_km2")}
    pdc_model.SETTINGS.update(original)
    return table


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    mode = argv[0]
    if mode == "lahar_frames":
        print(json.dumps(lahar_frames()))
        return 0
    store = terrain_store()
    if mode in ("west_sea", "sea_off_west", "southeast_reach_km"):
        summary = footprint_summary(store)
        print(json.dumps({**summary, "value": summary[mode]}))
    elif mode == "first_flow_h":
        print(json.dumps({"value": first_flow_hours(store)}))
    elif mode == "sensitivity":
        print(json.dumps(sensitivity(store), indent=1))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

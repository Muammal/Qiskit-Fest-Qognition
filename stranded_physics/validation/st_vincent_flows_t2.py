"""Report the fixed T2 pulse on St Vincent; final lines are gate JSON."""

from dataclasses import replace
import json
import sys
from time import perf_counter

import numpy as np
from scipy.ndimage import binary_dilation

from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.pdc.model_t2 import PdcT2
from stranded_physics.validation.st_vincent_flows import (
    GRID,
    TIME,
    VENT_XY,
    WEST_FLANK,
    SOUTHEAST,
    bearings_and_distance,
    in_sector,
    terrain_store,
)

COARSENING = 2  # Paired 180 m sensitivity grid averages each 2 x 2 block.
LAND_FRACTION = 0.5  # Majority of the four fine land cells defines coarse land; ties are land.
TRACE_DEPTH = 1e-3  # Diagnostic reach below the locked 0.1 m footprint threshold.


def run_pulse(store, grid=GRID):
    axis = replace(TIME, n=48)
    store.put("eruption.explosion", np.zeros(axis.n), "dimensionless", time=axis)
    domain = PdcT2(grid, axis, VENT_XY)
    started = perf_counter()
    budget = domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    print(f"{grid.dx_m:g} m pulse: {perf_counter() - started:.3f} s, {domain.result.steps} steps", file=sys.stderr)
    return domain, budget


def footprint_summary(store, domain):
    land = store.get("terrain.land_mask", "dimensionless") > 0
    travel = domain.result.arrival_s
    reached = np.isfinite(travel)
    bearing, distance = bearings_and_distance()
    at_sea = reached & binary_dilation(~land, structure=np.ones((3, 3)))
    west = in_sector(bearing, WEST_FLANK)
    southeast = reached & in_sector(bearing, SOUTHEAST)
    release = domain._release(land)
    trace = domain.result.max_depth >= TRACE_DEPTH
    return {
        "west_sea": float((at_sea & west).any()),
        "sea_off_west": float((at_sea & ~west).sum() / max(at_sea.sum(), 1)),
        "southeast_reach_km": float(distance[southeast].max() / 1000.0) if southeast.any() else 0.0,
        "reached_km2": float(reached.sum() * GRID.dx_m**2 / 1e6),
        "max_reach_km": float(distance[reached].max() / 1000.0) if reached.any() else 0.0,
        "sea_cells": int(at_sea.sum()),
        "slowest_arrival_min": float(travel[reached].max() / 60.0) if reached.any() else 0.0,
        "release_ring_volume_share": float(domain.result.h[release].sum() * GRID.dx_m**2 / domain.result.initial_volume),
        "outflow_volume_m3": domain.result.outflow_volume,
        "max_reach_1mm_km": float(distance[trace].max() / 1000.0) if trace.any() else 0.0,
    }


def coarse_store(store):
    ny, nx = GRID.ny // COARSENING, GRID.nx // COARSENING
    grid = replace(GRID, nx=nx, ny=ny, dx_m=GRID.dx_m * COARSENING)

    def average(array):
        # A trailing unmatched southern row is outside the common block extent.
        return array[: ny * COARSENING, : nx * COARSENING].reshape(ny, COARSENING, nx, COARSENING).mean(axis=(1, 3))

    result = FieldStore()
    result.put("terrain.elevation", average(store.get("terrain.elevation", "m")), "m", grid)
    land = average(store.get("terrain.land_mask", "dimensionless")) >= LAND_FRACTION
    result.put("terrain.land_mask", land, "dimensionless", grid)
    return result, grid


def grid_sensitivity(store, fine):
    coarse, grid = coarse_store(store)
    domain, _ = run_pulse(coarse, grid)
    xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m - VENT_XY[0]
    ys = grid.y0_m - (np.arange(grid.ny) + 0.5) * grid.dx_m - VENT_XY[1]
    distance = np.hypot(xs[None, :], ys[:, None])
    reached = np.isfinite(domain.result.arrival_s)
    summary = footprint_summary(store, fine)
    return {
        "reach_km_90m": summary["max_reach_km"],
        "reach_km_180m": float(distance[reached].max() / 1000.0) if reached.any() else 0.0,
        "reached_km2_90m": summary["reached_km2"],
        "reached_km2_180m": float(reached.sum() * grid.dx_m**2 / 1e6),
    }


def main(argv):
    modes = ("west_sea", "sea_off_west", "southeast_reach_km", "volume_error", "grid_sensitivity")
    if len(argv) != 1 or argv[0] not in modes:
        print("usage: " + "|".join(modes), file=sys.stderr)
        return 2
    store = terrain_store()
    domain, budget = run_pulse(store)
    mode = argv[0]
    if mode == "volume_error":
        measured = {"value": abs(budget["volume"])}
    elif mode == "grid_sensitivity":
        measured = grid_sensitivity(store, domain)
    else:
        measured = footprint_summary(store, domain)
        measured["value"] = measured[mode]
    print(json.dumps(measured))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

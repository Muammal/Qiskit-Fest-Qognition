"""Measurements behind the terrain gates. Each prints a final JSON line that the gate runner reads.

    python -m stranded_physics.domains.terrain.measure summit_height|summit_location|island_area|canopy|drains_to_sea|channels_vs_bare_earth
"""
from __future__ import annotations

import json
import sys

import numpy as np
from rasterio.warp import transform as warp_transform
from scipy.ndimage import binary_dilation, uniform_filter

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import FieldStore
from stranded_physics.core.records import load_datasets
from stranded_physics.domains.terrain.drainage import flow_accumulation, route, share_draining_out
from stranded_physics.domains.terrain.model import HERE, SETTINGS, ST_VINCENT_GRID, Terrain, land_area_km2, raw_path, read_elevation

GVP_SUMMIT_LONLAT = (-61.18, 13.33)  # Smithsonian GVP volcano 360150, as held in disaster_data/catalog/volcanoes.csv.
WORLDCOVER_TREE = 10  # ESA WorldCover class code for tree cover.
FABDEM_MEMBER = "N13W062_FABDEM_V1-2.tif"


def load_surface() -> FieldStore:
    domain = Terrain()
    reasons = domain.check_validity(None)
    if reasons:
        raise InterfaceError("; ".join(reasons))
    store = FieldStore()
    domain.run(store, np.random.default_rng(0))
    return store


def summit(store: FieldStore) -> tuple[float, float]:
    """Height of the highest land cell, and its distance from the catalogued summit."""
    grid = ST_VINCENT_GRID
    elevation = store.get("terrain.elevation", "m") * store.get("terrain.land_mask", "dimensionless")
    row, col = np.unravel_index(elevation.argmax(), elevation.shape)
    x, y = grid.centre(int(row), int(col))
    gvp_x, gvp_y = warp_transform("EPSG:4326", grid.crs, [GVP_SUMMIT_LONLAT[0]], [GVP_SUMMIT_LONLAT[1]])
    return float(elevation[row, col]), float(np.hypot(x - gvp_x[0], y - gvp_y[0]))


def canopy_bias(surface: np.ndarray, bare: np.ndarray, cover: np.ndarray, land: np.ndarray, window_cells: int, depth_m: float) -> dict[str, float]:
    """Surface minus bare earth on valley floors, split by forest. Valleys are found on the bare-earth model,
    so the canopy being measured can't affect which cells are chosen."""
    usable = land & np.isfinite(bare)
    floor = usable & (bare - uniform_filter(np.nan_to_num(bare), size=window_cells) <= -depth_m)
    forest = cover == WORLDCOVER_TREE
    difference = surface - bare

    def summarise(name: str, cells: np.ndarray) -> dict[str, float]:
        values = difference[cells]
        if values.size == 0:
            return {f"{name}_cells": 0}
        return {f"{name}_cells": int(values.size), f"{name}_mean_m": float(values.mean()), f"{name}_median_m": float(np.median(values)),
                f"{name}_p90_m": float(np.percentile(values, 90))}

    return {**summarise("forest_valley", floor & forest), **summarise("open_valley", floor & ~forest),
            **summarise("forest_all", usable & forest), **summarise("open_all", usable & ~forest)}


def read_bare_earth() -> np.ndarray:
    records = {r.id: r for r in load_datasets(HERE / "datasets.toml", "terrain")}
    archive = raw_path(records["fabdem_v1_2_n10w070"].url)
    return read_elevation(f"zip://{archive.as_posix()}!{FABDEM_MEMBER}", ST_VINCENT_GRID)


def drains_to_sea(store: FieldStore) -> float:
    land = store.get("terrain.land_mask", "dimensionless") > 0
    return share_draining_out(route(store.get("terrain.elevation", "m"), land, ST_VINCENT_GRID.dx_m), land)


def channels_vs_bare_earth(store: FieldStore) -> dict[str, float]:
    """How much canopy moves the channels: the share of surface-model channel cells within one cell of a bare-earth channel."""
    land = store.get("terrain.land_mask", "dimensionless") > 0
    threshold, dx = SETTINGS["channel_area"], ST_VINCENT_GRID.dx_m
    surface = store.get("terrain.flow_accumulation", "m**2") >= threshold
    bare = flow_accumulation(route(np.where(land, read_bare_earth(), 0.), land, dx), land, dx) >= threshold
    shared = surface & binary_dilation(bare, structure=np.ones((3, 3)))
    return {"surface_channel_cells": int(surface.sum()), "bare_earth_channel_cells": int(bare.sum()), "shared_share": float(shared.sum() / max(surface.sum(), 1))}


def measure_canopy(store: FieldStore) -> dict[str, float]:
    """FABDEM is a published machine-learned estimate of bare earth, not a survey, so this sizes the bias only roughly."""
    bare = read_bare_earth()
    return canopy_bias(store.get("terrain.elevation", "m"), bare, store.get("terrain.land_cover", "dimensionless"),
                       store.get("terrain.land_mask", "dimensionless") > 0, int(SETTINGS["valley_window"]), SETTINGS["valley_depth"])


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    store = load_surface()
    if argv[0] == "summit_height":
        print(json.dumps({"value": summit(store)[0]}))
    elif argv[0] == "summit_location":
        print(json.dumps({"value": summit(store)[1]}))
    elif argv[0] == "island_area":
        print(json.dumps({"value": land_area_km2(store.get("terrain.land_mask", "dimensionless"), ST_VINCENT_GRID)}))
    elif argv[0] == "canopy":
        print(json.dumps(measure_canopy(store)))
    elif argv[0] == "drains_to_sea":
        print(json.dumps({"value": drains_to_sea(store)}))
    elif argv[0] == "channels_vs_bare_earth":
        print(json.dumps(channels_vs_bare_earth(store)))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

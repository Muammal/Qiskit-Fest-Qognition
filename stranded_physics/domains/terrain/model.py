"""terrain T1: the real St Vincent surface, resampled from GLO-30 and WorldCover onto one grid.

GLO-30 is a surface model, so forest canopy raises narrow valley floors. `measure.canopy_bias` sizes that error;
this model does not correct it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

from stranded_physics.core.api import GridSpec, InterfaceError, Parameter
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_datasets, load_parameters

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / "artifacts" / "physics" / "raw" / "terrain"
PARAMETERS = load_parameters(HERE / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: p.value.magnitude for p in PARAMETERS}
ST_VINCENT_GRID = GridSpec("EPSG:32620", SETTINGS["grid_x0"], SETTINGS["grid_y0"], SETTINGS["grid_dx"],
                           int(SETTINGS["grid_nx"]), int(SETTINGS["grid_ny"]))
FILE_ROLES = {"dem": "copernicus_glo30_n13w062", "cover": "esa_worldcover_2021_n12w063"}


def raw_path(url: str) -> Path:
    return RAW / url.rsplit("/", 1)[1]


def default_files() -> dict[str, tuple[Path, str]]:
    records = {r.id: r for r in load_datasets(HERE / "datasets.toml", "terrain")}
    return {role: (raw_path(records[dataset].url), records[dataset].sha256) for role, dataset in FILE_ROLES.items()}


def _warp(source, source_transform, source_crs, source_nodata, grid: GridSpec, resampling: Resampling) -> np.ndarray:
    target = np.full((grid.ny, grid.nx), np.nan, dtype="float64")
    reproject(source, target, src_transform=source_transform, src_crs=source_crs, src_nodata=source_nodata,
              dst_transform=from_origin(grid.x0_m, grid.y0_m, grid.dx_m, grid.dx_m), dst_crs=grid.crs, dst_nodata=np.nan,
              resampling=resampling, init_dest_nodata=True)
    if np.isnan(target).any():
        raise InterfaceError(f"{int(np.isnan(target).sum())} grid cells fall outside the source raster")
    return target


def read_elevation(path: Path | str, grid: GridSpec) -> np.ndarray:
    """Area-average heights, so coarser cells keep the surface's mean height."""
    with rasterio.open(path) as source:
        return _warp(rasterio.band(source, 1), source.transform, source.crs, source.nodata, grid, Resampling.average)


def read_land_mask(path: Path, grid: GridSpec) -> np.ndarray:
    """1 where at least the set share of source cells stands above sea level. GLO-30 stores open sea as exactly 0."""
    with rasterio.open(path) as source:
        above_sea = (source.read(1) > 0).astype("float32")
        fraction = _warp(above_sea, source.transform, source.crs, None, grid, Resampling.average)
    return (fraction >= SETTINGS["land_fraction"]).astype(float)


def read_land_cover(path: Path, grid: GridSpec) -> np.ndarray:
    """The commonest class in each cell. Class codes are labels, so they are never averaged."""
    with rasterio.open(path) as source:
        return _warp(rasterio.band(source, 1), source.transform, source.crs, source.nodata, grid, Resampling.mode)


def land_area_km2(mask: np.ndarray, grid: GridSpec) -> float:
    return float(mask.sum()) * grid.dx_m ** 2 / 1e6


class Terrain:
    """Static land surface for one grid. Raw files are pinned by hash, so a changed download can't pass unnoticed."""

    id = "terrain"
    tier = "T1"
    inputs = ()
    outputs = (spec("terrain.elevation"), spec("terrain.land_mask"), spec("terrain.land_cover"))
    parameters: tuple[Parameter, ...] = PARAMETERS

    def __init__(self, grid: GridSpec = ST_VINCENT_GRID, files: dict[str, tuple[Path, str]] | None = None) -> None:
        self.grid = grid
        self.files = default_files() if files is None else files

    def check_validity(self, fields) -> list[str]:
        reasons = []
        for role, (path, expected) in self.files.items():
            if not path.exists():
                reasons.append(f"{role}: {path.name} is missing; run python -m stranded_physics.domains.terrain.fetch")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                reasons.append(f"{role}: {path.name} does not match its recorded sha256")
        return reasons

    def run(self, fields, rng: np.random.Generator) -> dict[str, float]:
        dem, cover = self.files["dem"][0], self.files["cover"][0]
        fields.put("terrain.elevation", read_elevation(dem, self.grid), "m", self.grid)
        fields.put("terrain.land_mask", read_land_mask(dem, self.grid), "dimensionless", self.grid)
        fields.put("terrain.land_cover", read_land_cover(cover, self.grid), "dimensionless", self.grid)
        return {}

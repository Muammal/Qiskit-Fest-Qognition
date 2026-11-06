"""terrain T1 checks on small synthetic rasters whose right answers are known exactly."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform

from stranded_physics.core.api import GridSpec, InterfaceError
from stranded_physics.core.fields import FieldStore
from stranded_physics.domains.terrain.measure import canopy_bias
from stranded_physics.domains.terrain.model import Terrain, land_area_km2, read_elevation, read_land_cover, read_land_mask

WEST, NORTH, ARC = -61.30, 13.42, 1 / 3600  # One-arcsecond cells, like GLO-30 at this latitude.
SIZE = 1000


def write_tif(path, data, nodata=None):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=from_origin(WEST, NORTH, ARC, ARC),
        nodata=nodata,
    ) as out:
        out.write(data, 1)
    return path


def cell_lonlat(grid):
    xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m
    ys = grid.y0_m - (np.arange(grid.ny) + 0.5) * grid.dx_m
    x, y = np.meshgrid(xs, ys)
    lon, lat = warp_transform(grid.crs, "EPSG:4326", x.ravel().tolist(), y.ravel().tolist())
    return np.reshape(lon, x.shape), np.reshape(lat, x.shape)


def source_axes():
    return WEST + (np.arange(SIZE) + 0.5) * ARC, NORTH - (np.arange(SIZE) + 0.5) * ARC


def covering_grid():
    """A grid fully inside the synthetic tile."""
    lon, lat = source_axes()
    x, y = warp_transform("EPSG:4326", "EPSG:32620", [float(lon[300])], [float(lat[300])])
    return GridSpec("EPSG:32620", round(x[0]), round(y[0]), 90.0, 20, 20)


def test_a_plane_keeps_its_height_at_every_cell_centre(tmp_path):
    lon, lat = source_axes()
    plane = (5000.0 * (lon[None, :] - WEST) + 9000.0 * (NORTH - lat[:, None])).astype("float32")
    grid = covering_grid()
    result = read_elevation(write_tif(tmp_path / "plane.tif", plane), grid)
    cell_lon, cell_lat = cell_lonlat(grid)
    expected = 5000.0 * (cell_lon - WEST) + 9000.0 * (NORTH - cell_lat)
    # A half-cell registration error would show as nearly 2 m on this plane, which rises 1.4 and 2.5 m per source cell.
    assert np.abs(result - expected).max() < 1.0


def test_a_known_block_lands_in_the_right_cell(tmp_path):
    grid = covering_grid()
    cell_lon, cell_lat = cell_lonlat(grid)
    lon, lat = source_axes()
    target = (7, 13)
    data = np.zeros((SIZE, SIZE), dtype="float32")
    row, col = np.abs(lat - cell_lat[target]).argmin(), np.abs(lon - cell_lon[target]).argmin()
    data[row - 1 : row + 2, col - 1 : col + 2] = 1000.0
    result = read_elevation(write_tif(tmp_path / "block.tif", data), grid)
    assert np.unravel_index(result.argmax(), result.shape) == target


def test_land_mask_splits_at_half_land_and_area_follows(tmp_path):
    grid = covering_grid()
    _, cell_lat = cell_lonlat(grid)
    _, lat = source_axes()
    split = cell_lat[10, 0]
    data = np.where(lat[:, None] > split, 100.0, 0.0) * np.ones((1, SIZE))
    mask = read_land_mask(write_tif(tmp_path / "half.tif", data.astype("float32")), grid)
    assert set(np.unique(mask)) == {0.0, 1.0}
    assert abs(land_area_km2(mask, grid) - grid.nx * 10 * 0.0081) <= grid.nx * 0.0081 * 1.5


def test_land_cover_stays_a_class_never_an_average(tmp_path):
    grid = covering_grid()
    lon, _ = source_axes()
    data = np.where(lon[None, :] < cell_lonlat(grid)[0][0, 10], 10, 40) * np.ones((SIZE, 1), dtype="uint8")
    cover = read_land_cover(write_tif(tmp_path / "cover.tif", data.astype("uint8")), grid)
    assert set(np.unique(cover)) <= {10.0, 40.0}
    assert cover[0, 0] == 10.0 and cover[0, -1] == 40.0


def test_a_grid_past_the_tile_edge_is_refused(tmp_path):
    data = np.ones((SIZE, SIZE), dtype="float32")
    far = GridSpec("EPSG:32620", 600000.0, 1475000.0, 90.0, 5, 5)
    with pytest.raises(InterfaceError, match="outside"):
        read_elevation(write_tif(tmp_path / "small.tif", data), far)


def make_domain(tmp_path, tamper=False):
    data = np.full((SIZE, SIZE), 50.0, dtype="float32")
    dem = write_tif(tmp_path / "dem.tif", data)
    cover = write_tif(tmp_path / "cover.tif", np.full((SIZE, SIZE), 10, dtype="uint8"))
    files = {"dem": (dem, hashlib.sha256(dem.read_bytes()).hexdigest()), "cover": (cover, hashlib.sha256(cover.read_bytes()).hexdigest())}
    if tamper:
        files["dem"] = (dem, "0" * 64)
    return Terrain(covering_grid(), files)


def test_domain_writes_declared_fields_through_the_store(tmp_path):
    domain = make_domain(tmp_path)
    store = FieldStore()
    assert domain.check_validity(store) == []
    domain.run(store, np.random.default_rng(1))
    assert store.get("terrain.elevation", "m").shape == (domain.grid.ny, domain.grid.nx)
    assert store.get("terrain.land_mask", "dimensionless").min() == 1.0
    assert store.get("terrain.land_cover", "dimensionless").max() == 10.0
    assert abs(store.get("terrain.elevation", "km").mean() - 0.05) < 1e-6


def test_changed_or_missing_raw_data_is_out_of_domain(tmp_path):
    assert any("sha256" in reason for reason in make_domain(tmp_path, tamper=True).check_validity(FieldStore()))
    domain = make_domain(tmp_path)
    domain.files["cover"][0].unlink()
    assert any("missing" in reason for reason in domain.check_validity(FieldStore()))


def test_canopy_bias_separates_forest_from_open_ground():
    bare = np.tile(np.abs(np.arange(60.0) - 30.0) * 10.0, (60, 1))  # A V-shaped valley running north to south.
    surface = bare.copy()
    cover = np.full(bare.shape, 40.0)
    cover[:30] = 10.0  # The northern half is forest.
    surface[:30] += 12.0
    land = np.ones(bare.shape, dtype=bool)
    result = canopy_bias(surface, bare, cover, land, window_cells=11, depth_m=15.0)
    assert result["forest_valley_cells"] > 0 and result["open_valley_cells"] > 0
    assert result["forest_valley_mean_m"] == pytest.approx(12.0)
    assert result["open_valley_mean_m"] == pytest.approx(0.0)

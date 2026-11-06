"""Where water goes on the surface: pit filling (Barnes et al. 2014, priority flood), steepest-descent routing, and height above drainage."""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np

FILL_RISE_M = 1e-3  # Keeps filled pits sloping, so every cell has a lower neighbour. A numerical device, not a physical value.
NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
OUTLET = -1


@dataclass(frozen=True)
class Drainage:
    filled: np.ndarray
    receivers: np.ndarray  # Flat index of the cell each cell drains into; OUTLET at the sea or the grid edge.


def fill_depressions(elevation: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Raise every pit just enough to spill. Non-land cells and the grid edge are where water leaves."""
    ny, nx = elevation.shape
    filled = elevation.astype(float).copy()
    visited = np.zeros(elevation.shape, dtype=bool)
    heap: list[tuple[float, int, int]] = []
    for row in range(ny):
        for col in range(nx):
            if not land[row, col] or row in (0, ny - 1) or col in (0, nx - 1):
                visited[row, col] = True
                heapq.heappush(heap, (float(filled[row, col]), row, col))
    while heap:
        height, row, col = heapq.heappop(heap)
        for d_row, d_col in NEIGHBOURS:
            r, c = row + d_row, col + d_col
            if 0 <= r < ny and 0 <= c < nx and not visited[r, c]:
                visited[r, c] = True
                filled[r, c] = max(filled[r, c], height + FILL_RISE_M)
                heapq.heappush(heap, (float(filled[r, c]), r, c))
    return filled


def route(elevation: np.ndarray, land: np.ndarray, dx_m: float) -> Drainage:
    """Each land cell drains to its steepest lower neighbour on the filled surface."""
    filled = fill_depressions(elevation, land)
    ny, nx = filled.shape
    receivers = np.full(filled.size, OUTLET, dtype=int)
    best = np.zeros(filled.shape)
    for d_row, d_col in NEIGHBOURS:
        distance = dx_m * (2**0.5 if d_row and d_col else 1.0)
        source_rows, target_rows = (
            (slice(1, ny), slice(0, ny - 1)) if d_row < 0 else (slice(0, ny - 1), slice(1, ny)) if d_row > 0 else (slice(None), slice(None))
        )
        source_cols, target_cols = (
            (slice(1, nx), slice(0, nx - 1)) if d_col < 0 else (slice(0, nx - 1), slice(1, nx)) if d_col > 0 else (slice(None), slice(None))
        )
        slope = np.zeros(filled.shape)
        slope[source_rows, source_cols] = (filled[source_rows, source_cols] - filled[target_rows, target_cols]) / distance
        steeper = slope > best
        best[steeper] = slope[steeper]
        rows, cols = np.nonzero(steeper)
        receivers[rows * nx + cols] = (rows + d_row) * nx + (cols + d_col)
    edge = ~land.copy()
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    receivers[edge.ravel()] = OUTLET
    return Drainage(filled, receivers)


def flow_accumulation(drainage: Drainage, land: np.ndarray, dx_m: float) -> np.ndarray:
    """Upslope area of each land cell, itself included. Visits high ground first, so every upstream share has arrived."""
    area = (land.astype(float) * dx_m**2).ravel()
    for index in np.argsort(-drainage.filled, axis=None):
        target = drainage.receivers[index]
        if target != OUTLET:
            area[target] += area[index]
    return area.reshape(land.shape)


def height_above_drainage(elevation: np.ndarray, drainage: Drainage, accumulation: np.ndarray, channel_area_m2: float) -> np.ndarray:
    """Height above the channel a cell drains into. Cells that reach the sea without meeting a channel measure from their outlet."""
    channel = (accumulation >= channel_area_m2).ravel()
    flat = elevation.ravel()
    base = flat.astype(float).copy()
    for index in np.argsort(drainage.filled, axis=None):
        target = drainage.receivers[index]
        if not channel[index] and target != OUTLET:
            base[index] = base[target]
    return np.clip(flat - base, 0.0, None).reshape(elevation.shape)


def share_draining_out(drainage: Drainage, land: np.ndarray) -> float:
    """Share of land cells whose path ends at an outlet. Filling should make this exactly 1."""
    reached = np.zeros(land.size, dtype=bool)
    reached[drainage.receivers == OUTLET] = True
    for index in np.argsort(drainage.filled, axis=None):
        target = drainage.receivers[index]
        if target != OUTLET and reached[target]:
            reached[index] = True
    return float(reached[land.ravel()].mean())

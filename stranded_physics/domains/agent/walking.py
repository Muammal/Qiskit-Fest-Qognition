"""Walking on real terrain: Tobler's hiking function, with the best route from everywhere to a goal found by Dijkstra."""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).resolve().parent / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: p.value.to_base_units().magnitude for p in PARAMETERS}
NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
TOBLER_KM_H, TOBLER_DECAY, TOBLER_SHIFT = 6., 3.5, .05  # Tobler 1993. From memory, so check in T-104.


def tobler_speed_m_s(slope: float) -> float:
    """Walking speed for a rise over run. Fastest on a slight downhill, at slope -0.05."""
    return TOBLER_KM_H * math.exp(-TOBLER_DECAY * abs(slope + TOBLER_SHIFT)) / 3.6 * SETTINGS["off_trail_factor"]


def step_seconds(rise_m: float, run_m: float) -> float:
    return run_m / tobler_speed_m_s(rise_m / run_m)


@dataclass(frozen=True)
class TravelField:
    seconds: np.ndarray  # Best walking time to the goal, infinity where it can't be reached.
    next_cell: np.ndarray  # Flat index of the next cell on the best route, -1 at the goal and where unreachable.


def travel_field(elevation: np.ndarray, land: np.ndarray, goal: tuple[int, int], dx_m: float) -> TravelField:
    """Dijkstra outward from the goal. Each step is priced in the direction it would be walked, toward the goal."""
    ny, nx = elevation.shape
    seconds = np.full(elevation.shape, np.inf)
    next_cell = np.full(elevation.size, -1, dtype=int)
    seconds[goal] = 0.
    heap = [(0., goal)]
    while heap:
        spent, (row, col) = heapq.heappop(heap)
        if spent > seconds[row, col]:
            continue
        for d_row, d_col in NEIGHBOURS:
            r, c = row + d_row, col + d_col
            if not (0 <= r < ny and 0 <= c < nx) or not land[r, c]:
                continue
            run = dx_m * (math.sqrt(2.) if d_row and d_col else 1.)
            total = spent + step_seconds(float(elevation[row, col] - elevation[r, c]), run)
            if total < seconds[r, c]:
                seconds[r, c] = total
                next_cell[r * nx + c] = row * nx + col
                heapq.heappush(heap, (total, (r, c)))
    return TravelField(seconds, next_cell)


def walk(field: TravelField, cell: tuple[int, int], budget_s: float, shape: tuple[int, int]) -> tuple[tuple[int, int], float]:
    """Follow the best route for up to `budget_s`. Returns the cell reached and the unused time, kept for the next stretch."""
    row, col = cell
    remaining = budget_s
    while True:
        target = field.next_cell[row * shape[1] + col]
        if target < 0:
            return (row, col), 0.
        next_row, next_col = int(target) // shape[1], int(target) % shape[1]
        cost = float(field.seconds[row, col] - field.seconds[next_row, next_col])
        if cost > remaining:
            return (row, col), remaining
        remaining -= cost
        row, col = next_row, next_col

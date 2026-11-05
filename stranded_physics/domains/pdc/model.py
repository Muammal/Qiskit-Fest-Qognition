"""pdc T1: where dense flows can reach, by an energy line followed along the terrain, and when.

An energy cone, after Malin and Sheridan 1982, but measured along connected paths, so high ground blocks a flow.
It has no flow physics beyond that: no mass, no entrainment and no dilute surge. T2 is the depth-averaged solver.
"""
from __future__ import annotations

import heapq
import math
from pathlib import Path

import numpy as np

from stranded_physics.core.api import GridSpec, Parameter, TimeAxis, XY
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).resolve().parent / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: p.value.to_base_units().magnitude for p in PARAMETERS}
GRAVITY_M_S2 = 9.80665
NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def energy_reach(elevation: np.ndarray, passable: np.ndarray, start: tuple[int, int], start_energy_m: float, ratio: float, dx_m: float, min_speed: float) -> np.ndarray:
    """Seconds for a flow to reach each cell from `start`, infinity where it never does.

    The energy height falls by `ratio` per metre travelled, along the shortest connected path. A cell is reached only
    while the energy line stands above its ground. Speed comes from the energy above ground, v = sqrt(2 g (E - z)).
    """
    arrival = np.full(elevation.shape, np.inf)
    length = np.full(elevation.shape, np.inf)
    length[start], arrival[start] = 0., 0.
    heap = [(0., start)]
    while heap:
        travelled, (row, col) = heapq.heappop(heap)
        if travelled > length[row, col]:
            continue
        for d_row, d_col in NEIGHBOURS:
            r, c = row + d_row, col + d_col
            if not (0 <= r < elevation.shape[0] and 0 <= c < elevation.shape[1]) or not passable[r, c]:
                continue
            step = dx_m * (math.sqrt(2.) if d_row and d_col else 1.)
            total = travelled + step
            height_above = start_energy_m - ratio * total - elevation[r, c]
            if height_above <= 0 or total >= length[r, c]:
                continue
            length[r, c] = total
            arrival[r, c] = arrival[row, col] + step / max(math.sqrt(2 * GRAVITY_M_S2 * height_above), min_speed)
            heapq.heappush(heap, (total, (r, c)))
    return arrival


def distance_from(grid: GridSpec, point: XY) -> np.ndarray:
    xs = grid.x0_m + (np.arange(grid.nx) + .5) * grid.dx_m - point[0]
    ys = grid.y0_m - (np.arange(grid.ny) + .5) * grid.dx_m - point[1]
    return np.hypot(*np.meshgrid(xs, ys))


def size_scale(erupted_kg: float) -> float:
    """How far a generated eruption's flows reach, relative to St Vincent's. Runout length goes as volume to the 1/3, as area goes as volume to the 2/3."""
    return (erupted_kg / SETTINGS["reference_erupted_mass"]) ** (1 / 3)


def flow_footprint(elevation: np.ndarray, land: np.ndarray, height_above_channel: np.ndarray, grid: GridSpec, vent: XY) -> np.ndarray:
    """Travel seconds from collapse to each cell. Dense flows keep to valleys, except close to the vent."""
    start = grid.locate(vent)
    passable = land & ((height_above_channel <= SETTINGS["valley_confinement"]) | (distance_from(grid, vent) <= SETTINGS["proximal_radius"]))
    passable[start] = True
    return energy_reach(elevation, passable, start, float(elevation[start]) + SETTINGS["collapse_height"], SETTINGS["height_over_length"], grid.dx_m, SETTINGS["min_speed"])


class Pdc:
    """A flow starts at the published first collapse, then again with each later explosion."""

    id = "pdc"
    tier = "T1"
    inputs = (spec("eruption.explosion"), spec("terrain.elevation"), spec("terrain.land_mask"), spec("terrain.height_above_drainage"))
    outputs = (spec("pdc.arrival"), spec("pdc.active"))
    parameters: tuple[Parameter, ...] = PARAMETERS

    def __init__(self, grid: GridSpec, time: TimeAxis, vent: XY, first_collapse_s: float | None = None, reach_limit_m: float | None = None) -> None:
        """Both settings are for a generated eruption. Left out, St Vincent's published date applies, and only the energy line limits reach."""
        self.grid, self.time, self.vent = grid, time, vent
        self.reach_limit_m = reach_limit_m
        self.first_collapse_s = SETTINGS["first_collapse_after_axis_start"] if first_collapse_s is None else first_collapse_s

    def check_validity(self, fields) -> list[str]:
        return [] if self.grid.locate(self.vent) is not None else ["the vent is outside the flow grid"]

    def run(self, fields, rng: np.random.Generator) -> dict[str, float]:
        travel = flow_footprint(fields.get("terrain.elevation", "m", self.grid), fields.get("terrain.land_mask", "dimensionless", self.grid) > 0,
                                fields.get("terrain.height_above_drainage", "m", self.grid), self.grid, self.vent)
        if self.reach_limit_m is not None:
            travel = np.where(distance_from(self.grid, self.vent) <= self.reach_limit_m, travel, np.inf)
        reached = np.isfinite(travel)
        first = self.first_collapse_s
        frame_times = np.arange(self.time.n) * self.time.dt_s
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        explosion = fields.get("eruption.explosion", "dimensionless") > 0
        collapses = explosion & (frame_times >= first)
        if first <= frame_times[-1]:
            collapses[int(np.searchsorted(frame_times, first))] = True  # A frame only shows a flow that has already begun.
        frames[collapses] = reached.astype(float)
        arrival = np.where(reached, first + travel, np.inf) if collapses.any() else np.full(travel.shape, np.inf)
        fields.put("pdc.arrival", arrival, "s", self.grid)
        fields.put("pdc.active", frames, "dimensionless", self.grid, self.time)
        return {}

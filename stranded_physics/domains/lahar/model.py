"""lahar T1: mudflows only while enough rain falls on enough fresh ash, sized by LAHARZ scaling (Iverson et al. 1998)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from stranded_physics.core.api import GridSpec, Parameter, TimeAxis, XY
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).resolve().parent / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: p.value.to_base_units().magnitude for p in PARAMETERS}
SETTINGS["rain_threshold_mm_h"] = next(p for p in PARAMETERS if p.id == "lahar.rain_threshold").value.to("mm/h").magnitude
PLANIMETRIC_COEFFICIENT = 200.0  # B = 200 V^(2/3), Iverson, Schilling and Vallance 1998. From memory, so check in T-104.


def planimetric_area_m2(volume_m3: float) -> float:
    return PLANIMETRIC_COEFFICIENT * volume_m3 ** (2 / 3)


def inundate(height_above_channel: np.ndarray, candidates: np.ndarray, volume_m3: float, dx_m: float) -> np.ndarray:
    """Depth on the lowest cells above their channels, filled until the LAHARZ area is met. The volume is conserved."""
    available = np.flatnonzero(candidates.ravel())
    count = min(int(round(planimetric_area_m2(volume_m3) / dx_m**2)), available.size)
    depth = np.zeros(height_above_channel.shape)
    if count == 0:
        return depth
    chosen = available[np.argsort(height_above_channel.ravel()[available], kind="stable")[:count]]
    depth.flat[chosen] = volume_m3 / (count * dx_m**2)
    return depth


class Lahar:
    id = "lahar"
    tier = "T1"
    inputs = (
        spec("atmos.rain_rate"),
        spec("tephra.deposit_load"),
        spec("terrain.land_mask"),
        spec("terrain.flow_accumulation"),
        spec("terrain.height_above_drainage"),
    )
    outputs = (spec("lahar.depth"),)
    parameters: tuple[Parameter, ...] = PARAMETERS

    def __init__(self, grid: GridSpec, time: TimeAxis, vent: XY) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def check_validity(self, fields) -> list[str]:
        return [] if self.grid.locate(self.vent) is not None else ["the vent is outside the lahar grid"]

    def run(self, fields, rng: np.random.Generator) -> dict[str, float]:
        grid = self.grid
        xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m - self.vent[0]
        ys = grid.y0_m - (np.arange(grid.ny) + 0.5) * grid.dx_m - self.vent[1]
        distance = np.hypot(*np.meshgrid(xs, ys))
        land = fields.get("terrain.land_mask", "dimensionless", grid) > 0
        height = fields.get("terrain.height_above_drainage", "m", grid)
        area = fields.get("terrain.flow_accumulation", "m**2", grid)
        source = land & (distance <= SETTINGS["source_radius"])
        rain = fields.get("atmos.rain_rate", "mm/h")
        loads = fields.get("tephra.deposit_load", "kg/m**2", grid)
        catchment = float(area[source].max()) if source.any() else 0.0
        frames = np.zeros((self.time.n, grid.ny, grid.nx))
        placed = wanted = 0.0
        candidates = land & (distance <= SETTINGS["reach_radius"])
        for frame in range(self.time.n):
            ash = float(loads[frame][source].mean()) if source.any() else 0.0
            if rain[frame] < SETTINGS["rain_threshold_mm_h"] or ash < SETTINGS["ash_threshold"]:
                continue
            water = rain[frame] / 1000.0 * self.time.dt_s / 3600.0 * catchment
            volume = water * SETTINGS["bulking"]
            frames[frame] = inundate(height, candidates, volume, grid.dx_m)
            wanted += volume
            placed += float(frames[frame].sum()) * grid.dx_m**2
        fields.put("lahar.depth", frames, "m", grid, self.time)
        return {"volume_m3": abs(wanted - placed) / wanted if wanted else 0.0}

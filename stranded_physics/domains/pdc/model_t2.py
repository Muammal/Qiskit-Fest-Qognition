"""A single depth-averaged dense-flow pulse, with the T1 event-time contract."""

from pathlib import Path

import numpy as np

from stranded_physics.core.api import GridSpec, InterfaceError, TimeAxis, XY
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters
from stranded_physics.solvers.depth_averaged import simulate

PARAMETERS = load_parameters(Path(__file__).with_name("params_t2.toml"))
SETTINGS = {p.id.split(".", 1)[1]: p.value.to_base_units().magnitude for p in PARAMETERS}


class PdcT2:
    """Terrain and Voellmy friction determine the pulse footprint."""

    id = "pdc"
    tier = "T2"
    inputs = (spec("eruption.explosion"), spec("terrain.elevation"), spec("terrain.land_mask"))
    outputs = (spec("pdc.arrival"), spec("pdc.active"))
    parameters = PARAMETERS

    def __init__(self, grid: GridSpec, time: TimeAxis, vent: XY, first_collapse_s: float | None = None, volume_scale: float = 1.0) -> None:
        """Both settings are for a generated eruption. Left out, St Vincent's published date and pulse volume apply."""
        self.grid, self.time, self.vent = grid, time, vent
        self.volume_scale = volume_scale
        self.first_collapse_s = SETTINGS["first_collapse_after_axis_start"] if first_collapse_s is None else first_collapse_s

    def _release(self, land):
        xs = self.grid.x0_m + (np.arange(self.grid.nx) + 0.5) * self.grid.dx_m - self.vent[0]
        ys = self.grid.y0_m - (np.arange(self.grid.ny) + 0.5) * self.grid.dx_m - self.vent[1]
        radius = np.hypot(xs[None, :], ys[:, None])
        return land & (radius >= SETTINGS["release_inner_radius"]) & (radius <= SETTINGS["release_outer_radius"])

    def check_validity(self, fields) -> list[str]:
        if self.grid.locate(self.vent) is None:
            return ["the vent is outside the flow grid"]
        land = fields.get("terrain.land_mask", "dimensionless", self.grid) > 0
        return [] if self._release(land).any() else ["the release area contains no land"]

    def run(self, fields, rng: np.random.Generator) -> dict[str, float]:
        problems = self.check_validity(fields)
        if problems:
            raise InterfaceError("; ".join(problems))
        land = fields.get("terrain.land_mask", "dimensionless", self.grid) > 0
        release = self._release(land)
        h0 = release.astype(float) * SETTINGS["pulse_volume"] * self.volume_scale / (release.sum() * self.grid.dx_m**2)
        result = simulate(
            fields.get("terrain.elevation", "m", self.grid),
            h0,
            self.grid.dx_m,
            SETTINGS["duration"],
            mu=SETTINGS["coulomb_friction"],
            xi=SETTINGS["turbulent_friction"],
            cfl=SETTINGS["cfl"],
            sink=~land,
            arrival_depth=SETTINGS["arrival_depth"],
        )
        self.result = result
        first = self.first_collapse_s
        frame_times = np.arange(self.time.n) * self.time.dt_s
        collapses = (fields.get("eruption.explosion", "dimensionless") == 1) & (frame_times >= first)
        if self.time.n and first <= frame_times[-1]:
            collapses[np.searchsorted(frame_times, first)] = True
        reached = np.isfinite(result.arrival_s)
        frames = collapses[:, None, None] * reached[None, :, :]
        arrival = first + result.arrival_s if collapses.any() else np.full(reached.shape, np.inf)
        fields.put("pdc.arrival", arrival, "s", self.grid)
        fields.put("pdc.active", frames, "dimensionless", self.grid, self.time)
        error = (result.h.sum() * self.grid.dx_m**2 + result.outflow_volume - result.initial_volume) / result.initial_volume
        return {"volume": float(error)}

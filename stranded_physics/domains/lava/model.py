from pathlib import Path
import numpy as np
from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).with_name("params.toml"))
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}


def _nonnegative(value, name):
    value = np.asarray(value, dtype=float)
    if not np.isfinite(value).all() or (value < 0).any():
        raise InterfaceError(f"{name} must be finite and nonnegative")
    return value


def _axis(time):
    if time.n < 1 or not np.isfinite(time.dt_s) or time.dt_s <= 0:
        raise InterfaceError("positive finite time axis required")


def huppert_radius_m(flux_m3_s, viscosity_m2_s, t_s, g=9.80665):
    q = _nonnegative(flux_m3_s, "flux")
    nu = _nonnegative(viscosity_m2_s, "viscosity")
    t = _nonnegative(t_s, "growth time")
    _nonnegative(g, "gravity")
    if np.any(nu <= 0) or np.any(np.asarray(g) <= 0):
        raise InterfaceError("positive viscosity and gravity required")
    return SETTINGS["huppert_coefficient"] * (g * q**3 / (3 * nu)) ** (1 / 8) * np.sqrt(t)


def dome_volume_m3(flux_m3_s, t_s):
    return _nonnegative(flux_m3_s, "flux") * _nonnegative(t_s, "growth time")


def dome_radius_m(flux_m3_s, viscosity_m2_s, t_s):
    return np.minimum(huppert_radius_m(flux_m3_s, viscosity_m2_s, t_s, SETTINGS["gravity"]), SETTINGS["max_dome_radius"])


class Lava:
    id, tier = "lava", "T1"
    inputs = (spec("eruption.explosion"),)
    outputs = (spec("lava.footprint"),)
    parameters = PARAMETERS

    def __init__(self, grid, time, vent, grown_before_s=None):
        _axis(time)
        self.grid, self.time, self.vent = grid, time, vent
        self.grown_before_s = SETTINGS["growth_before_axis"] if grown_before_s is None else float(grown_before_s)
        _nonnegative(self.grown_before_s, "prior growth")
        if self.grown_before_s > next(p.valid[1].magnitude for p in PARAMETERS if p.id == "lava.growth_before_axis"):
            raise InterfaceError("prior growth outside parameter range")

    def check_validity(self, fields):
        try:
            _nonnegative(fields.get("eruption.explosion", "dimensionless"), "explosion")
        except ValueError as error:
            return [str(error)]
        return []

    def run(self, fields, rng):
        x = self.grid.x0_m + (np.arange(self.grid.nx) + 0.5) * self.grid.dx_m - self.vent[0]
        y = self.grid.y0_m - (np.arange(self.grid.ny) + 0.5) * self.grid.dx_m - self.vent[1]
        distance = np.hypot(*np.meshgrid(x, y))
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        destroyed = False
        for k in range(self.time.n):
            explosion = _nonnegative(fields.get("eruption.explosion", "dimensionless", t_s=k * self.time.dt_s), "explosion")
            destroyed = destroyed or bool(np.any(explosion > 0))
            if not destroyed:
                radius = dome_radius_m(SETTINGS["flux"], SETTINGS["viscosity"], self.grown_before_s + k * self.time.dt_s)
                frames[k] = (distance <= radius) & (radius > 0)
        fields.put("lava.footprint", frames, "dimensionless", self.grid, self.time)
        return {}

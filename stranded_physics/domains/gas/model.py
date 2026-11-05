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


KG_TO_UG = 1e9


def briggs_sigmas_m(downwind_m):
    x = _nonnegative(downwind_m, "downwind distance")
    return (SETTINGS["sigma_y_coefficient"] * x / np.sqrt(1 + SETTINGS["sigma_y_decay"] * x),
            SETTINGS["sigma_z_coefficient"] * x / np.sqrt(1 + SETTINGS["sigma_z_decay"] * x))


def ground_concentration_ug_m3(rate_kg_s, downwind_m, crosswind_m, release_m, wind_m_s):
    q, x, y, h, u = np.broadcast_arrays(rate_kg_s, downwind_m, crosswind_m, release_m, wind_m_s)
    for value, name in ((q, "rate"), (h, "release height"), (u, "wind")):
        _nonnegative(value, name)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (u <= 0).any():
        raise InterfaceError("finite coordinates and positive wind required")
    result = np.zeros(x.shape)
    active = x > 0
    sy, sz = briggs_sigmas_m(x[active])
    result[active] = (q[active] * KG_TO_UG / (np.pi * u[active] * sy * sz)
                      * np.exp(-.5 * (y[active] / sy)**2 - .5 * (h[active] / sz)**2))
    return result.item() if result.ndim == 0 else result


def so2_rate_kg_s(phase, mass_rate_kg_s):
    phase, mass = np.broadcast_arrays(_nonnegative(phase, "phase"), _nonnegative(mass_rate_kg_s, "mass rate"))
    if (phase > 3).any():
        raise InterfaceError("phase outside [0, 3]")
    return np.where(phase >= 1, SETTINGS["peak_so2_flux"] + SETTINGS["so2_mass_fraction"] * mass, 0.)


class Gas:
    id, tier = "gas", "T1"
    inputs = tuple(spec(n) for n in ("eruption.phase", "eruption.mass_rate", "atmos.wind_speed", "atmos.wind_bearing"))
    outputs = (spec("gas.so2_concentration"),)
    parameters = PARAMETERS

    def __init__(self, grid, time, vent):
        _axis(time)
        self.grid, self.time, self.vent = grid, time, vent

    def check_validity(self, fields):
        try:
            for k in range(self.time.n):
                self._frame(fields, k)
        except (ValueError, IndexError) as error:
            return [str(error)]
        return []

    def _frame(self, fields, k):
        t = k * self.time.dt_s
        phase, mass, wind, bearing = [fields.get(s.name, s.unit, t_s=t) for s in self.inputs]
        _nonnegative(wind, "wind")
        if not np.isfinite(bearing).all() or np.any((bearing < 0) | (bearing > 360)):
            raise InterfaceError("bearing outside [0, 360]")
        angle = np.deg2rad(bearing)
        x = self.grid.x0_m + (np.arange(self.grid.nx) + .5) * self.grid.dx_m - self.vent[0]
        y = self.grid.y0_m - (np.arange(self.grid.ny) + .5) * self.grid.dx_m - self.vent[1]
        east, north = np.meshgrid(x, y)
        return ground_concentration_ug_m3(so2_rate_kg_s(phase, mass), east*np.sin(angle)+north*np.cos(angle),
            east*np.cos(angle)-north*np.sin(angle), SETTINGS["release_height"], np.maximum(wind, SETTINGS["min_wind"]))

    def run(self, fields, rng):
        frames = np.array([self._frame(fields, k) for k in range(self.time.n)])
        fields.put(self.outputs[0].name, frames, self.outputs[0].unit, self.grid, self.time)
        return {}

from pathlib import Path
import numpy as np
from scipy.special import ndtr
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


def roof_failure_fraction(load_kg_m2):
    load = _nonnegative(load_kg_m2, "ash load")
    result = np.zeros(load.shape)
    positive = load > 0
    result[positive] = ndtr(np.log(load[positive]/SETTINGS["roof_collapse_load"])/SETTINGS["roof_fragility_beta"])
    return result.item() if result.ndim == 0 else result


def flow_death_probability(sheltered: bool) -> float:
    return SETTINGS["flow_death_sheltered" if sheltered else "flow_death_outdoors"]


def ash_energy_cost_per_hour(load_kg_m2, sheltered: bool) -> float:
    load = _nonnegative(load_kg_m2, "ash load")
    result = SETTINGS["ash_fatigue_per_hour"] * np.minimum(1., load/SETTINGS["ash_fatigue_load"])
    return result * (SETTINGS["shelter_ash_factor"] if sheltered else 1.)


class Exposure:
    id, tier = "exposure", "T1"
    inputs = (spec("tephra.deposit_load"),)
    outputs = (spec("exposure.roof_failure"),)
    parameters = PARAMETERS

    def __init__(self, grid, time):
        _axis(time)
        self.grid, self.time = grid, time

    def check_validity(self, fields):
        try:
            _nonnegative(fields.get("tephra.deposit_load", "kg/m**2", self.grid), "ash load")
        except ValueError as error:
            return [str(error)]
        return []

    def run(self, fields, rng):
        frames = [roof_failure_fraction(fields.get("tephra.deposit_load", "kg/m**2", self.grid, k*self.time.dt_s))
                  for k in range(self.time.n)]
        fields.put("exposure.roof_failure", np.asarray(frames), "dimensionless", self.grid, self.time)
        return {}

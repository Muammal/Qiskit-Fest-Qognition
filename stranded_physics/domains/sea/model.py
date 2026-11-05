"""T1 immersion proxy; a lognormal incapacitation CDF, not clinical survival data.

Cold shock is an early threat. The task brief quotes Tipton: "Humans don't
become hypothermic in less than 30 minutes", and gives 10–40 minutes for swim
failure. No published 0 C distribution is in hand. All curve choices are
labelled assumptions in params.toml, not fits to Titanic deaths.
"""
from math import erf, exp, isfinite, log, sqrt
from pathlib import Path

import numpy as np

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).with_name("params.toml"))
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}
_PARAMS = {p.id.split(".", 1)[1]: p for p in PARAMETERS}


def _value(value, name):
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise InterfaceError(f"{name} must be a finite number") from error
    low, high = _PARAMS[name].valid
    if not isfinite(value) or not low.magnitude <= value <= high.magnitude:
        raise InterfaceError(f"{name} outside [{low.magnitude}, {high.magnitude}]")
    return value


def incapacitation_median_minutes(temperature_c) -> float:
    temperature = _value(temperature_c, "temperature")
    return SETTINGS["incapacitation_median_at_freezing"] * exp(
        SETTINGS["incapacitation_warming_rate"] * (temperature - SETTINGS["freezing_point"]))


def immersion_death_probability(minutes, temperature_c, lifebelt=True) -> float:
    minutes = _value(minutes, "immersion_minutes")
    median = incapacitation_median_minutes(temperature_c)
    if not isinstance(lifebelt, (bool, np.bool_)):
        raise InterfaceError("lifebelt must be boolean")
    if minutes == 0:
        return 0.
    if lifebelt:
        median *= SETTINGS["lifebelt_factor"]
    z = (log(minutes) - log(median)) / SETTINGS["incapacitation_spread"]
    return .5 * (1. + erf(z / sqrt(2.)))


def titanic_sea_temperature_c() -> float:
    # -2 C is from memory. The report's 33/32 F weather passage is not a
    # clearly identified water observation, so it is not cited as one.
    return SETTINGS["titanic_temperature"]


class Sea:
    id, tier = "sea", "T1"
    inputs = ()
    outputs = (spec("sea.temperature"),)
    parameters = PARAMETERS

    def __init__(self, time, temperature_c):
        if (not isinstance(time.n, int) or time.n < 1
                or not isfinite(time.dt_s) or time.dt_s <= 0):
            raise InterfaceError("positive finite time axis required")
        self.time = time
        self.temperature_c = _value(temperature_c, "temperature")

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        fields.put("sea.temperature", np.full(self.time.n, self.temperature_c),
                   "degC", time=self.time)
        return {}

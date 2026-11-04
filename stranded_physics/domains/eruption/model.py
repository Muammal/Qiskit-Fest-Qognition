"""Evidence-backed event times with explicit unresolved column assumptions."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import numpy as np

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

METRES_PER_KM = 1000.

HERE = Path(__file__).resolve().parent
PARAMETERS = load_parameters(HERE / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}


def mastin_mass_rate_kg_s(height_m):
    height = np.asarray(height_m, dtype=float)
    if not np.isfinite(height).all() or (height < 0).any():
        raise InterfaceError("Mastin height must be finite and nonnegative")
    result = SETTINGS["dre_density"] * (height / METRES_PER_KM / SETTINGS["mastin_coefficient"]) ** (1 / SETTINGS["mastin_exponent"])
    return float(result) if result.ndim == 0 else result


def mtt_height_m(buoyancy_flux, brunt_vaisala):
    if not np.isfinite([buoyancy_flux, brunt_vaisala]).all() or buoyancy_flux < 0 or brunt_vaisala <= 0:
        raise InterfaceError("MTT needs nonnegative buoyancy flux and positive stratification")
    return SETTINGS["mtt_coefficient"] * buoyancy_flux ** SETTINGS["mtt_flux_power"] * brunt_vaisala ** SETTINGS["mtt_frequency_power"]


def read_events():
    with (HERE / "facts.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    events = []
    for row in rows:
        epoch = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00")).timestamp()
        if epoch != SETTINGS[row["id"] + "_epoch"]:
            raise InterfaceError(f"{row['id']}: facts and parameter time disagree")
        first = not events
        height = float(row["column_height_m"]) if row["column_height_m"] else SETTINGS["first_height" if first else "default_height"]
        duration = float(row["duration_s"]) if row["duration_s"] else SETTINGS["first_duration" if first else "default_duration"]
        if height <= 0 or duration <= 0:
            raise InterfaceError(f"{row['id']}: column height and duration must be positive")
        events.append((epoch, height, duration))
    if not events or any(b[0] <= a[0] for a, b in zip(events, events[1:])):
        raise InterfaceError("events must be present and strictly chronological")
    return events


class Eruption:
    id = "eruption"
    tier = "T1"
    inputs = ()
    outputs = tuple(spec("eruption." + name) for name in ("phase", "tremor", "gas", "explosion", "mass_rate", "column_height"))
    parameters = PARAMETERS

    def __init__(self, time):
        self.time = time

    def check_validity(self, fields):
        if self.time.n < 1 or self.time.dt_s <= 0 or not np.isfinite(self.time.dt_s) or self.time.t0_utc.utcoffset() is None:
            return ["eruption needs a positive time axis with timezone-aware instants"]
        try:
            read_events()
        except (OSError, ValueError, KeyError) as error:
            return [str(error)]
        return []

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        events = read_events()
        moments = self.time.t0_utc.timestamp() + np.arange(self.time.n) * self.time.dt_s
        first = events[0][0]
        phase = np.where(moments >= first, 2., np.where(moments >= SETTINGS["escalation_epoch"], 1., 0.))
        run_up = phase == 1
        tremor, gas = np.zeros(self.time.n), np.zeros(self.time.n)
        draws = rng.random((int(run_up.sum()), 2))
        tremor[run_up] = draws[:, 0] < SETTINGS["tremor_probability"]
        gas[run_up] = draws[:, 1] < SETTINGS["gas_probability"]
        explosion, column, rate = (np.zeros(self.time.n) for _ in range(3))
        for start, height, duration in events:
            # Frame zero has no preceding frame; record only an onset exactly at axis start.
            began = (start > moments - self.time.dt_s) & (start <= moments)
            began[0] = start == moments[0]
            explosion[began] = 1.
            overlap = np.maximum(0., np.minimum(moments, start + duration)
                                 - np.maximum(moments - self.time.dt_s, start))
            overlap[0] = 0.
            rate += mastin_mass_rate_kg_s(height) * overlap / self.time.dt_s
            column[overlap > 0] = np.maximum(column[overlap > 0], height)
        values = (phase, tremor, gas, explosion, rate, column)
        for output, value in zip(self.outputs, values):
            fields.put(output.name, value, output.unit, time=self.time)
        return {}

"""Hourly UTC weather replay; rain uses completed hours only."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_datasets, load_parameters

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / "artifacts/physics/raw/atmos"
PARAMETERS = load_parameters(HERE / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}
SECONDS_PER_HOUR = 3600.0
KMH_PER_MS = 3.6
FROM_TO_ROTATION = 180.0
FULL_TURN = 360.0

COLUMNS = {
    "wind_speed": ("surface", "wind_speed_10m"),
    "wind_bearing": ("surface", "wind_direction_10m"),
    "air_temperature": ("surface", "temperature_2m"),
    "wind_speed_500hpa": ("upper", "wind_speed_500hPa"),
    "wind_bearing_500hpa": ("upper", "wind_direction_500hPa"),
    "wind_speed_200hpa": ("upper", "wind_speed_200hPa"),
    "wind_bearing_200hpa": ("upper", "wind_direction_200hPa"),
    "rain_rate": ("surface", "precipitation"),
}


def default_files():
    records = {r.id: r for r in load_datasets(HERE / "datasets.toml", "atmos")}
    return {role: (RAW / (name + ".json"), records[name].sha256) for role, name in (("upper", "upper_wind_st_vincent"), ("surface", "weather_st_vincent"))}


@lru_cache(maxsize=int(SETTINGS["cache_files"]))
def _read(path: Path, modified: int):
    data = json.loads(path.read_text(encoding="utf-8"))
    hourly = data["hourly"]
    times = hourly["time"]
    if len(set(times)) != len(times) or times != sorted(times):
        raise InterfaceError(f"{path.name}: unordered or duplicate hours")
    return hourly, {t: i for i, t in enumerate(times)}


class Atmos:
    id = "atmos"
    tier = "T1"
    inputs = ()
    outputs = tuple(spec("atmos." + name) for name in COLUMNS)
    parameters = PARAMETERS

    def __init__(self, time: TimeAxis, files=None):
        self.time = time
        self.files = default_files() if files is None else files

    def _moments(self):
        return [self.time.t0_utc.astimezone(timezone.utc) + timedelta(seconds=k * self.time.dt_s) for k in range(self.time.n)]

    def check_validity(self, fields):
        reasons = []
        if self.time.n < 1 or not np.isfinite(self.time.dt_s) or self.time.dt_s <= 0 or self.time.t0_utc.utcoffset() is None:
            return ["weather replay needs a positive time axis with timezone-aware UTC instants"]
        hour = SECONDS_PER_HOUR
        if self.time.dt_s % hour or any((m.minute or m.second or m.microsecond) for m in self._moments()):
            return ["weather replay needs exact hourly instants and whole-hour steps"]
        for role in {source for source, _ in COLUMNS.values()}:
            if role not in self.files:
                reasons.append(f"{role}: missing file record")
                continue
            path, expected = self.files[role]
            path = Path(path)
            if not path.exists():
                reasons.append(f"{role}: {path.name} is missing")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                reasons.append(f"{role}: {path.name} does not match its recorded sha256")
                continue
            try:
                hourly, index = _read(path, path.stat().st_mtime_ns)
                moments = self._moments()
                needed = {m.strftime("%Y-%m-%dT%H:%M") for m in moments}
                for moment in moments[1:]:
                    needed.update((moment - timedelta(seconds=j * hour)).strftime("%Y-%m-%dT%H:%M") for j in range(int(self.time.dt_s / hour)))
                if not needed <= index.keys():
                    reasons.append(f"{role}: data does not cover the requested time axis")
                    continue
                for source, column in COLUMNS.values():
                    if source != role:
                        continue
                    values = [hourly[column][index[t]] for t in needed]
                    if not np.isfinite(np.asarray(values, dtype=float)).all():
                        reasons.append(f"{role}.{column}: missing or non-finite values")
            except (ValueError, KeyError, TypeError, IndexError) as error:
                reasons.append(f"{role}: invalid hourly data: {error}")
        return reasons

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        moments = self._moments()
        for name, (role, column) in COLUMNS.items():
            path = Path(self.files[role][0])
            hourly, index = _read(path, path.stat().st_mtime_ns)
            values = []
            for k, moment in enumerate(moments):
                hours = 1 if k == 0 or name != "rain_rate" else int(self.time.dt_s / SECONDS_PER_HOUR)
                values.append(
                    np.mean([hourly[column][index[(moment - timedelta(seconds=j * SECONDS_PER_HOUR)).strftime("%Y-%m-%dT%H:%M")]] for j in range(hours)])
                )
            data = np.asarray(values)
            if name.startswith("wind_speed"):
                data = data / KMH_PER_MS
            elif name.startswith("wind_bearing"):
                data = (data + FROM_TO_ROTATION) % FULL_TURN
            fields.put("atmos." + name, data, spec("atmos." + name).unit, time=self.time)
        return {}

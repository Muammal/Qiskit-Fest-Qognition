"""Best-track interpolation and symmetric Holland cyclostrophic winds."""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_datasets, load_parameters

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / "artifacts/physics/raw/storm"
PARAMETERS = load_parameters(HERE / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}
KNOTS_TO_MS = 0.514444
NAUTICAL_MILES_TO_M = 1852.0
METRES_PER_KM = 1000.0
SECONDS_PER_HOUR = 3600.0


def default_files():
    records = {r.id: r for r in load_datasets(HERE / "datasets.toml", "storm")}
    return {"track": (RAW / "beryl_2024.csv", records["ibtracs_beryl_2024"].sha256)}


def holland_wind_m_s(r_m, vmax, rmax, b):
    """Holland (1980) cyclostrophic profile; citation from memory in params."""
    r = np.asarray(r_m, dtype=float)
    if not np.isfinite(r).all() or (r < 0).any() or not np.isfinite([vmax, rmax, b]).all() or vmax < 0 or rmax <= 0 or b <= 0:
        raise InterfaceError("Holland winds need nonnegative radius/wind and positive rmax/b")
    result = np.zeros_like(r)
    positive = r > 0
    log_q = b * (np.log(rmax) - np.log(r[positive]))
    # Once q is this large the exponential is below floating-point support.
    supported = log_q < np.log(np.finfo(float).max)
    speed = np.zeros_like(log_q)
    q = np.exp(log_q[supported])
    speed[supported] = vmax * np.exp(0.5 * (log_q[supported] + 1 - q))
    result[positive] = speed
    return float(result) if result.ndim == 0 else result


def great_circle_m(site_lonlat, lon, lat):
    site_lon, site_lat = np.deg2rad(site_lonlat)
    lon, lat = np.deg2rad(lon), np.deg2rad(lat)
    haversine = np.sin((lat - site_lat) / 2) ** 2 + np.cos(site_lat) * np.cos(lat) * np.sin((lon - site_lon) / 2) ** 2
    return 2 * SETTINGS["earth_radius"] * np.arcsin(np.sqrt(np.clip(haversine, 0.0, 1.0)))


def read_track(path):
    fixes = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        needed = {"ISO_TIME", "LAT", "LON", "USA_WIND", "USA_RMW"}
        if not needed <= set(reader.fieldnames or ()):
            raise InterfaceError("track lacks required IBTrACS columns")
        for row in reader:
            if not row["USA_WIND"].strip() or not row["USA_RMW"].strip():
                continue
            instant = datetime.fromisoformat(row["ISO_TIME"].strip().replace("Z", "+00:00"))
            if instant.utcoffset() is None:
                instant = instant.replace(tzinfo=timezone.utc)
            fixes.append(
                (instant.timestamp(), float(row["LAT"]), float(row["LON"]), float(row["USA_WIND"]) * KNOTS_TO_MS, float(row["USA_RMW"]) * NAUTICAL_MILES_TO_M)
            )
    data = np.asarray(fixes, dtype=float)
    if data.ndim != 2 or len(data) < 2 or not np.isfinite(data).all():
        raise InterfaceError("track needs at least two finite complete fixes")
    if (
        (np.diff(data[:, 0]) <= 0).any()
        or (np.abs(data[:, 1]) > 90).any()
        or (np.abs(data[:, 2]) > 180).any()
        or (data[:, 3] < 0).any()
        or (data[:, 4] <= 0).any()
    ):
        raise InterfaceError("track fixes must be chronological with valid coordinates, wind and radius")
    return data


class Storm:
    id = "storm"
    tier = "T1"
    inputs = ()
    outputs = (spec("storm.max_wind"),)
    parameters = PARAMETERS

    def __init__(self, time, site_lonlat, files=None, generated=None):
        self.time, self.site_lonlat = time, site_lonlat
        self.generated = generated
        self.files = default_files() if files is None and generated is None else files

    def check_validity(self, fields):
        if self.time.n < 1 or not np.isfinite(self.time.dt_s) or self.time.dt_s <= 0 or self.time.t0_utc.utcoffset() is None:
            return ["storm needs a positive timezone-aware time axis"]
        if len(self.site_lonlat) != 2 or not np.isfinite(self.site_lonlat).all() or abs(self.site_lonlat[0]) > 180 or abs(self.site_lonlat[1]) > 90:
            return ["storm site needs finite longitude/latitude in degrees"]
        if self.generated is not None:
            try:
                from .generator import validate_generated

                validate_generated(self.generated)
            except (ValueError, TypeError, AttributeError) as error:
                return [str(error)]
            return []
        if len(self.files) != 1:
            return ["storm needs exactly one track file record"]
        path, expected = next(iter(self.files.values()))
        path = Path(path)
        if not path.is_file():
            return [f"track: {path.name} is missing"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return [f"track: {path.name} does not match its recorded sha256"]
        try:
            read_track(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return [f"invalid track: {error}"]
        return []

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        if self.generated is None:
            track = read_track(next(iter(self.files.values()))[0])
            moments = self.time.t0_utc.timestamp() + np.arange(self.time.n) * self.time.dt_s
            lat, lon, vmax, rmax = [np.interp(moments, track[:, 0], track[:, col]) for col in range(1, 5)]
        else:
            from .generator import interpolate_track

            track = self.generated.track
            moments = np.arange(self.time.n) * self.time.dt_s
            lat, lon, vmax, rmax = interpolate_track(track, moments)
        distance = great_circle_m(self.site_lonlat, lon, lat)
        winds = np.zeros(self.time.n)
        inside = (moments >= track[0, 0]) & (moments <= track[-1, 0])
        for k in np.flatnonzero(inside):
            winds[k] = holland_wind_m_s(distance[k], vmax[k], rmax[k], SETTINGS["holland_b"])
        self.distance_m = distance
        fields.put("storm.max_wind", winds, "m/s", time=self.time)
        return {}

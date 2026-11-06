"""Training-catalogue storms following constant-speed spherical tracks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from stranded_physics.core.api import InterfaceError
from .model import HERE, KNOTS_TO_MS, METRES_PER_KM, PARAMETERS, SETTINGS

CATALOG = HERE.parents[2] / "disaster_data/catalog/cyclones_near_study_islands.csv"
BOUNDS = {p.id.split(".", 1)[1]: tuple(float(q.magnitude) for q in p.valid) for p in PARAMETERS}


@dataclass(frozen=True)
class GeneratedStorm:
    max_wind_m_s: float
    rmax_m: float
    closest_km: float
    bearing_deg: float
    speed_m_s: float
    closest_s: float
    track: np.ndarray


def checked(name, value):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise InterfaceError(f"{name} must be a finite number") from error
    low, high = BOUNDS[name]
    if not np.isfinite(value) or not low <= value <= high:
        raise InterfaceError(f"{name} outside [{low}, {high}]")
    return value


def axis_end(axis_seconds):
    try:
        axis = np.asarray(axis_seconds, dtype=float)
    except (TypeError, ValueError) as error:
        raise InterfaceError("axis_seconds must be a duration or increasing seconds from zero") from error
    if axis.ndim == 0:
        end = float(axis)
    elif axis.ndim == 1 and len(axis) >= 2 and np.isfinite(axis).all() and axis[0] == 0 and (np.diff(axis) > 0).all():
        end = float(axis[-1])
    else:
        raise InterfaceError("axis_seconds must be a duration or increasing seconds from zero")
    return checked("generator_axis_s", end)


def checked_site(site_lonlat):
    try:
        site = np.asarray(site_lonlat, dtype=float)
    except (TypeError, ValueError) as error:
        raise InterfaceError("site needs longitude and latitude") from error
    if site.shape != (2,):
        raise InterfaceError("site needs longitude and latitude")
    checked("generated_site_lon", site[0])
    checked("generated_site_lat", site[1])
    return site


@lru_cache(maxsize=None)
def training_catalog(before_season):
    cutoff = checked("wind_before_season", before_season)
    if cutoff != int(cutoff):
        raise InterfaceError("before_season must be an integer")
    rows = []
    with CATALOG.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            # Neither wind nor distance is inspected until the training split is checked.
            if not row["season"].strip() or float(row["season"]) >= cutoff:
                continue
            wind = checked("generated_max_wind_m_s", float(row["max_wind_kt"]) * KNOTS_TO_MS) if row["max_wind_kt"].strip() else None
            distance = checked("generated_closest_km", row["closest_km"]) if row["closest_km"].strip() else None
            rows.append((wind, distance))
    if not rows:
        raise InterfaceError("no training storms before the requested season")
    return tuple(rows)


def sample_max_wind_m_s(rng, before_season=2005) -> float:
    winds = wind_catalog(before_season)
    return float(winds[rng.integers(len(winds))])


@lru_cache(maxsize=None)
def wind_catalog(before_season):
    winds = tuple(wind for wind, _ in training_catalog(before_season) if wind is not None)
    if not winds:
        raise InterfaceError("no training winds before the requested season")
    return winds


def track_positions(site_lonlat, times, closest_km, bearing_deg, speed_m_s, closest_s):
    lon, lat = np.deg2rad(site_lonlat)
    radial = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.cross(radial, east)
    bearing = np.deg2rad(bearing_deg)
    tangent = np.cos(bearing) * north + np.sin(bearing) * east
    right = np.cross(tangent, radial)
    offset = closest_km * METRES_PER_KM / SETTINGS["earth_radius"]
    foot = np.cos(offset) * radial + np.sin(offset) * right
    angle = (np.asarray(times) - closest_s) * speed_m_s / SETTINGS["earth_radius"]
    xyz = np.cos(angle)[..., None] * foot + np.sin(angle)[..., None] * tangent
    lats = np.rad2deg(np.arctan2(xyz[..., 2], np.hypot(xyz[..., 0], xyz[..., 1])))
    lons = np.rad2deg(np.arctan2(xyz[..., 1], xyz[..., 0]))
    return lats, lons


def generate(
    rng, site_lonlat, axis_seconds, max_wind_m_s=None, closest_km=None, bearing_deg=None, speed_m_s=None, rmax_m=None, closest_s=None
) -> GeneratedStorm:
    site = checked_site(site_lonlat)
    end = axis_end(axis_seconds)
    wind = sample_max_wind_m_s(rng) if max_wind_m_s is None else checked("generated_max_wind_m_s", max_wind_m_s)
    if closest_km is None:
        distances = tuple(d for _, d in training_catalog(SETTINGS["wind_before_season"]) if d is not None)
        if not distances:
            raise InterfaceError("no training closest distances")
        distance = float(distances[rng.integers(len(distances))])
    else:
        distance = checked("generated_closest_km", closest_km)
    bearing = float(rng.uniform(*BOUNDS["generated_bearing_deg"])) if bearing_deg is None else checked("generated_bearing_deg", bearing_deg)
    speed = float(rng.uniform(*BOUNDS["generated_speed_m_s"])) if speed_m_s is None else checked("generated_speed_m_s", speed_m_s)
    radius = float(rng.uniform(*BOUNDS["generated_rmax_m"])) if rmax_m is None else checked("generated_rmax_m", rmax_m)
    closest = (
        float(rng.uniform(SETTINGS["onset_fraction_min"] * end, SETTINGS["onset_fraction_max"] * end))
        if closest_s is None
        else checked("generated_closest_s", closest_s)
    )
    if closest > end:
        raise InterfaceError("closest_s must be on the axis")
    step = SETTINGS["generator_fix_s"]
    # Anchor hourly fixes on the exact closest pass, with one fix beyond both axis ends.
    times = closest + np.arange(-int(np.ceil(closest / step)) - 1, int(np.ceil((end - closest) / step)) + 2) * step
    lat, lon = track_positions(site, times, distance, bearing, speed, closest)
    track = np.column_stack((times, lat, lon, np.full(len(times), wind), np.full(len(times), radius)))
    track.setflags(write=False)
    return GeneratedStorm(wind, radius, distance, bearing, speed, closest, track)


def validate_generated(generated):
    for name in ("max_wind_m_s", "rmax_m", "closest_km", "bearing_deg", "speed_m_s", "closest_s"):
        checked("generated_" + name, getattr(generated, name))
    track = np.asarray(generated.track)
    if track.ndim != 2 or track.shape[1] != 5 or len(track) < 2 or not np.isfinite(track).all():
        raise InterfaceError("generated storm needs at least two finite five-column fixes")
    if (np.diff(track[:, 0]) <= 0).any() or (np.abs(track[:, 1]) > 90).any() or (np.abs(track[:, 2]) > 180).any():
        raise InterfaceError("generated track must be chronological with valid coordinates")
    for name, col in (("generated_max_wind_m_s", 3), ("generated_rmax_m", 4)):
        low, high = BOUNDS[name]
        if ((track[:, col] < low) | (track[:, col] > high)).any():
            raise InterfaceError(f"track {name} outside [{low}, {high}]")


def interpolate_track(track, moments):
    """Interpolate along great circles, including across the dateline and poles."""
    times = track[:, 0]
    left = np.searchsorted(times, moments, side="right") - 1
    left = np.clip(left, 0, len(times) - 2)
    fraction = (moments - times[left]) / (times[left + 1] - times[left])
    lat, lon = np.deg2rad(track[:, 1]), np.deg2rad(track[:, 2])
    xyz = np.column_stack((np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))
    a, b = xyz[left], xyz[left + 1]
    omega = np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), np.einsum("ij,ij->i", a, b))
    # sinc remains well-defined for coincident fixes.
    wa = (1 - fraction) * np.sinc((1 - fraction) * omega / np.pi) / np.sinc(omega / np.pi)
    wb = fraction * np.sinc(fraction * omega / np.pi) / np.sinc(omega / np.pi)
    points = wa[:, None] * a + wb[:, None] * b
    lat = np.rad2deg(np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1])))
    lon = np.rad2deg(np.arctan2(points[:, 1], points[:, 0]))
    wind, radius = (np.interp(moments, times, track[:, col]) for col in (3, 4))
    return lat, lon, wind, radius

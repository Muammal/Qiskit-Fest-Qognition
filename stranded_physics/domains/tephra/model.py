"""Suzuki release and delayed Gaussian fallout, with frozen release-time winds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec
from stranded_physics.core.records import load_parameters

MILLIMETRES_TO_METRES = 1e-3
FULL_TURN = 360.0

HERE = Path(__file__).resolve().parent
PARAMETERS = load_parameters(HERE / "params.toml")
SETTINGS = {p.id.split(".", 1)[1]: float(p.value.magnitude) for p in PARAMETERS}


def stokes_settling_m_s(diameter_m, rho_particle, rho_air, viscosity):
    if not np.isfinite([diameter_m, rho_particle, rho_air, viscosity]).all() or diameter_m <= 0 or rho_air <= 0 or rho_particle <= rho_air or viscosity <= 0:
        raise InterfaceError("Stokes settling requires positive diameter, viscosity and density contrast")
    speed = (rho_particle - rho_air) * SETTINGS["gravity"] * diameter_m**2 / (18 * viscosity)
    reynolds = rho_air * speed * diameter_m / viscosity
    if reynolds > SETTINGS["stokes_re_limit"]:
        raise InterfaceError(f"particle Reynolds number {reynolds:g} exceeds the Stokes limit")
    return speed


def settling_speed_m_s(diameter_m, rho_particle, rho_air, viscosity):
    """Sphere terminal speed with task-specified Schiller-Naumann drag."""
    if not np.isfinite([diameter_m, rho_particle, rho_air, viscosity]).all() or diameter_m <= 0 or rho_air <= 0 or rho_particle <= rho_air or viscosity <= 0:
        raise InterfaceError("settling requires positive diameter, viscosity and density contrast")
    target = 4 * diameter_m**3 * rho_air * (rho_particle - rho_air) * SETTINGS["gravity"] / (3 * viscosity**2)

    def drag_balance(re):
        if re <= SETTINGS["drag_transition_re"]:
            return 24 * re * (1 + SETTINGS["drag_coefficient"] * re ** SETTINGS["drag_exponent"])
        return SETTINGS["newton_drag"] * re**2

    transition = SETTINGS["drag_transition_re"]
    # The rounded two-branch law has a small upward jump at Re=1000.
    if drag_balance(transition) < target < SETTINGS["newton_drag"] * transition**2:
        reynolds = transition
    else:
        upper = max(transition, np.sqrt(target / SETTINGS["newton_drag"])) * 2
        reynolds = brentq(lambda re: drag_balance(re) - target, 0.0, upper, xtol=SETTINGS["settling_tolerance"])
    return reynolds * viscosity / (rho_air * diameter_m)


def grain_classes(count):
    """Truncated normal mass density in phi, on equally spaced phi nodes."""
    if isinstance(count, bool) or int(count) != count or count < 2:
        raise InterfaceError("grain count must be an integer of at least two")
    phi = np.linspace(SETTINGS["grain_phi_min"], SETTINGS["grain_phi_max"], int(count))
    log_weights = -0.5 * ((phi - SETTINGS["grain_median_phi"]) / SETTINGS["grain_spread_phi"]) ** 2
    fractions = np.exp(log_weights - log_weights.max())
    fractions[[0, -1]] *= 0.5
    return MILLIMETRES_TO_METRES * 2.0 ** (-phi), fractions / fractions.sum()


def gaussian_load_kg_m2(mass_kg, dx_m, dy_m, release_m, wind_speed, bearing_deg, settling, diffusivity):
    if (
        not np.isfinite([mass_kg, release_m, wind_speed, bearing_deg, settling, diffusivity]).all()
        or mass_kg < 0
        or release_m <= 0
        or wind_speed < 0
        or settling <= 0
        or diffusivity <= 0
    ):
        raise InterfaceError("Gaussian fallout needs finite nonnegative mass/wind and positive release, settling and diffusion")
    x, y = np.asarray(dx_m, dtype=float), np.asarray(dy_m, dtype=float)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise InterfaceError("Gaussian coordinates must be finite")
    fall = release_m / settling
    bearing = np.deg2rad(bearing_deg)
    cx, cy = wind_speed * fall * np.sin(bearing), wind_speed * fall * np.cos(bearing)
    variance = 2 * diffusivity * fall
    return mass_kg / (2 * np.pi * variance) * np.exp(-((x - cx) ** 2) / (2 * variance)) * np.exp(-((y - cy) ** 2) / (2 * variance))


def suzuki_weights(heights_m, column_m, a, lam):
    heights = np.asarray(heights_m, dtype=float)
    if (
        heights.ndim != 1
        or not heights.size
        or not np.isfinite(heights).all()
        or not np.isfinite([column_m, a, lam]).all()
        or column_m <= 0
        or a < 0
        or lam <= 0
    ):
        raise InterfaceError("Suzuki release needs a positive column, lambda and finite heights")
    inside = (heights >= 0) & (heights < column_m)
    weights = np.zeros_like(heights)
    if not inside.any():
        raise InterfaceError("Suzuki samples have no support inside the column")
    relative = heights[inside] / column_m
    log_weights = lam * (np.log1p(-relative) + a * (relative - 1))
    weights[inside] = np.exp(log_weights - log_weights.max())
    return weights / weights.sum()


def wind_at_height(height_m, speed_10m, bearing_10m, speed_500, bearing_500, speed_200, bearing_200):
    speeds = np.array([speed_10m, speed_500, speed_200], dtype=float)
    bearings = np.array([bearing_10m, bearing_500, bearing_200], dtype=float)
    if not np.isfinite(height_m) or not np.isfinite(speeds).all() or not np.isfinite(bearings).all() or (speeds < 0).any():
        raise InterfaceError("wind profile requires finite height, bearings and nonnegative speeds")
    levels = [SETTINGS["wind_height_10m"], SETTINGS["wind_height_500"], SETTINGS["wind_height_200"]]
    angles = np.deg2rad(bearings)
    east = np.interp(height_m, levels, speeds * np.sin(angles))
    north = np.interp(height_m, levels, speeds * np.cos(angles))
    speed = float(np.hypot(east, north))
    bearing = float(np.rad2deg(np.arctan2(east, north)) % FULL_TURN) if speed else 0.0
    return speed, bearing


@dataclass(frozen=True)
class Packet:
    mass_kg: float
    release_s: float
    height_m: float
    wind_speed: float
    bearing_deg: float
    settling: float
    diffusivity: float

    @property
    def arrival_s(self):
        return self.release_s + self.height_m / self.settling

    def load(self, x, y):
        return gaussian_load_kg_m2(self.mass_kg, x, y, self.height_m, self.wind_speed, self.bearing_deg, self.settling, self.diffusivity)


def integrated_packet_mass(packet):
    """Midpoint quadrature on a separate wide grid centred on this packet."""
    sigma = np.sqrt(2 * packet.diffusivity * packet.height_m / packet.settling)
    n = int(SETTINGS["budget_points"])
    spacing = 2 * SETTINGS["budget_sigma"] * sigma / n
    offset = (np.arange(n) + 0.5) * spacing - SETTINGS["budget_sigma"] * sigma
    along = packet.wind_speed * packet.height_m / packet.settling
    angle = np.deg2rad(packet.bearing_deg)
    cx, cy = along * np.sin(angle), along * np.cos(angle)
    peak = float(packet.load(cx, cy))
    if not peak:
        return 0.0
    return float(packet.load(cx + offset, cy).sum() * packet.load(cx, cy + offset).sum() * spacing**2 / peak)


class Tephra:
    id = "tephra"
    tier = "T1"
    inputs = tuple(
        spec(name)
        for name in (
            "eruption.mass_rate",
            "eruption.column_height",
            "atmos.wind_speed",
            "atmos.wind_bearing",
            "atmos.wind_speed_500hpa",
            "atmos.wind_bearing_500hpa",
            "atmos.wind_speed_200hpa",
            "atmos.wind_bearing_200hpa",
        )
    )
    outputs = (spec("tephra.deposit_load"),)
    parameters = PARAMETERS

    def __init__(self, grid, time, vent, grain_count=int(SETTINGS["grain_count"])):
        self.grid, self.time, self.vent = grid, time, vent
        grain_classes(grain_count)
        self.grain_count = int(grain_count)
        self._packets = None

    def _read(self, fields):
        return [np.asarray(fields.get(f.name, f.unit), dtype=float) for f in self.inputs]

    def check_validity(self, fields):
        if (
            self.time.n < 1
            or not np.isfinite(self.time.dt_s)
            or self.time.dt_s <= 0
            or self.grid.nx < 1
            or self.grid.ny < 1
            or not np.isfinite(self.grid.dx_m)
            or self.grid.dx_m <= 0
            or not np.isfinite(self.vent).all()
        ):
            return ["tephra needs finite geometry and a positive grid and time axis"]
        try:
            arrays = self._read(fields)
        except (InterfaceError, KeyError) as error:
            return [str(error)]
        if any(a.shape != (self.time.n,) or not np.isfinite(a).all() for a in arrays):
            return ["all tephra forcing fields must be finite series on the requested time axis"]
        rate, height, *winds = arrays
        if (rate < 0).any() or (height < 0).any() or any((s < 0).any() for s in winds[::2]):
            return ["mass rate, height and wind speeds cannot be negative"]
        if ((rate > 0) & (height <= 0)).any():
            return ["positive erupted mass needs a positive release column"]
        return []

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        rate, height, *winds = self._read(fields)
        diameters, fractions = grain_classes(self.grain_count)
        settling = [settling_speed_m_s(d, SETTINGS["particle_density"], SETTINGS["air_density"], SETTINGS["air_viscosity"]) for d in diameters]
        bins = int(SETTINGS["release_bins"])
        packets = []
        released = 0.0
        integrated = 0.0
        for k, mass_rate in enumerate(rate):
            if mass_rate == 0:
                continue
            mass = float(mass_rate * self.time.dt_s)
            released += mass
            levels = (np.arange(bins) + 0.5) / bins * height[k]
            weights = suzuki_weights(levels, height[k], SETTINGS["suzuki_a"], SETTINGS["suzuki_lambda"])
            for level, weight in zip(levels, weights):
                speed, bearing = wind_at_height(level, *(wind[k] for wind in winds))
                for fraction, speed_fall in zip(fractions, settling):
                    packet = Packet(float(mass * weight * fraction), k * self.time.dt_s, float(level), speed, bearing, speed_fall, SETTINGS["diffusivity"])
                    packets.append(packet)
                    integrated += integrated_packet_mass(packet)
        packets.sort(key=lambda p: p.arrival_s)
        x = self.grid.x0_m + (np.arange(self.grid.nx) + 0.5) * self.grid.dx_m - self.vent[0]
        y = self.grid.y0_m - (np.arange(self.grid.ny) + 0.5) * self.grid.dx_m - self.vent[1]
        frames = np.empty((self.time.n, self.grid.ny, self.grid.nx))
        cumulative = np.zeros((self.grid.ny, self.grid.nx))
        next_packet = 0
        for k in range(self.time.n):
            while next_packet < len(packets) and packets[next_packet].arrival_s <= k * self.time.dt_s:
                cumulative += packets[next_packet].load(x[None, :], y[:, None])
                next_packet += 1
            frames[k] = cumulative
        self._packets = tuple(packets)
        fields.put("tephra.deposit_load", frames, "kg/m**2", self.grid, self.time)
        self.released_mass_kg = released
        self.integrated_mass_kg = integrated
        # This is ultimate deposition, including packets still airborne at the final scenario frame.
        return {"mass_kg": abs(integrated - released) / released if released else 0.0}

    def load_at(self, xy_m, t_s):
        if self._packets is None:
            raise InterfaceError("run tephra before querying loads")
        if not np.isfinite([*xy_m, t_s]).all() or t_s < 0:
            raise InterfaceError("load query needs finite coordinates and nonnegative elapsed time")
        x, y = xy_m[0] - self.vent[0], xy_m[1] - self.vent[1]
        return float(sum(p.load(x, y) for p in self._packets if p.arrival_s <= t_s))

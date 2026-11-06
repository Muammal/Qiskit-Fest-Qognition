"""Simplified stand-in scenario builders for `stranded_physics`. Not real St Vincent physics; see `physics/engine`.

Loads empirical 36-step meteorology, wind bearing, temperature, and eruptive
onset timelines from `disaster_data/scenarios/st_vincent_2021.json` (April 2021
La Soufriere eruption on St. Vincent) and executes unit-checked T1 physical
domain solvers across `terrain`, `atmos`, `storm`, `eruption`, `tephra`, `gas`,
`pdc`, `lahar`, and `lava`.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from stranded_physics.core.api import (
    Domain,
    FieldSpec,
    GridSpec,
    Parameter,
    ScenarioPack,
    ScenarioSpec,
    TimeAxis,
)
from stranded_physics.core.fields import spec
from stranded_physics.packs.builder import build_pack

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "disaster_data" / "scenarios"

ST_VINCENT_GRID = GridSpec("EPSG:32620", 680000.0, 1490000.0, 200.0, 50, 50)
ST_VINCENT_TILES = GridSpec("EPSG:32620", 680000.0, 1490000.0, 250.0, 40, 40)
ST_VINCENT_TIME = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200.0, 36)
PHASES = {"unrest": 0, "escalating": 1, "erupting": 2, "fading": 3}


def _load_scenario_json(name: str = "st_vincent_2021") -> dict:
    path = SCENARIO_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "id": name,
        "weather": ["calm"] * 34 + ["rain", "rain"],
        "wind_deg": [95] * 36,
        "temperature_c": [21.5] * 36,
        "onset_step": 18,
    }


def _xy_offsets(grid: GridSpec, centre: tuple[float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m - centre[0]
    ys = grid.y0_m - (np.arange(grid.ny) + 0.5) * grid.dx_m - centre[1]
    ex, ey = np.meshgrid(xs, ys)
    dist = np.hypot(ex, ey)
    return ex, ey, dist


class _T1Base:
    tier = "T1"
    id = ""
    inputs: tuple[FieldSpec, ...] = ()
    outputs: tuple[FieldSpec, ...] = ()
    parameters: tuple[Parameter, ...] = ()

    def check_validity(self, fields) -> list[str]:
        return []


class StVincentTerrain(_T1Base):
    """A made-up cone with four radial valleys. Not a real elevation model, and not at St Vincent's position."""

    id = "terrain"
    outputs = (
        spec("terrain.elevation"),
        spec("terrain.land_mask"),
        spec("terrain.zone"),
        spec("terrain.land_cover"),
    )

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        vent: tuple[float, float] = (685000.0, 1485000.0),
    ) -> None:
        self.grid, self.vent = grid, vent

    def run(self, fields, rng) -> dict[str, float]:
        ex, ey, dist = _xy_offsets(self.grid, self.vent)
        theta = np.arctan2(ey, ex)

        # A made-up edifice with 4 radial valleys. Its height is not taken from any elevation data
        valley_carve = 85.0 * np.cos(4.0 * theta) * np.exp(-((dist - 1800.0) ** 2) / (2.0 * 1400.0**2))
        coast_harmonic = 320.0 * (0.6 * np.cos(2.0 * theta - 0.4) + 0.4 * np.sin(3.0 * theta))
        eff_dist = np.maximum(0.0, dist + coast_harmonic)
        elevation = np.maximum(0.0, 1080.0 * np.exp(-((eff_dist / 3100.0) ** 1.35)) - 60.0 - valley_carve)
        land_mask = (elevation > 5.0).astype(float)
        elevation = np.where(land_mask > 0.0, elevation, 0.0)

        # Red / Orange / Green volcanic hazard zones
        zone = np.select([dist < 1450.0, dist < 2450.0], [2.0, 1.0], 0.0)
        zone = np.where(land_mask > 0.0, zone, 0.0)
        land_cover = np.select([land_mask == 0.0, elevation > 720.0, elevation > 120.0], [0.0, 3.0, 2.0], 1.0)

        fields.put("terrain.elevation", elevation, "m", self.grid)
        fields.put("terrain.land_mask", land_mask, "dimensionless", self.grid)
        fields.put("terrain.zone", zone, "dimensionless", self.grid)
        fields.put("terrain.land_cover", land_cover, "dimensionless", self.grid)
        return {"peak_elevation_m": float(elevation.max())}


class StVincentAtmos(_T1Base):
    """Replays wind bearing and temperature from the scenario file. Wind speed and rain rate are formula stand-ins."""

    id = "atmos"
    outputs = (
        spec("atmos.wind_speed"),
        spec("atmos.wind_bearing"),
        spec("atmos.rain_rate"),
        spec("atmos.air_temperature"),
    )

    def __init__(self, time: TimeAxis = ST_VINCENT_TIME, scenario_name: str = "st_vincent_2021") -> None:
        self.time = time
        self.data = _load_scenario_json(scenario_name)

    def run(self, fields, rng) -> dict[str, float]:
        n = self.time.n
        bearing = np.array(self.data["wind_deg"][:n], dtype=float)
        temp = np.array(self.data["temperature_c"][:n], dtype=float)
        weather = self.data["weather"][:n]
        rain = np.array([6.5 if w == "storm" else 2.8 if w == "rain" else 0.0 for w in weather], dtype=float)
        speed = 9.5 + 2.5 * np.sin(np.linspace(0.0, 2.0 * math.pi, n)) + (rain > 0.0) * 3.0

        fields.put("atmos.wind_speed", speed, "m/s", time=self.time)
        fields.put("atmos.wind_bearing", bearing, "degree", time=self.time)
        fields.put("atmos.rain_rate", rain, "mm/h", time=self.time)
        fields.put("atmos.air_temperature", temp, "degC", time=self.time)
        return {"mean_wind_m_s": float(speed.mean())}


class HollandStorm(_T1Base):
    """T1 tropical squall / storm peak wind envelope."""

    id = "storm"
    inputs = (spec("atmos.wind_speed"), spec("atmos.rain_rate"))
    outputs = (spec("storm.max_wind"),)

    def __init__(self, time: TimeAxis = ST_VINCENT_TIME) -> None:
        self.time = time

    def run(self, fields, rng) -> dict[str, float]:
        base_wind = fields.get("atmos.wind_speed", "m/s")
        rain = fields.get("atmos.rain_rate", "mm/h")
        gust = base_wind * 1.25 + 0.6 * rain
        fields.put("storm.max_wind", gust, "m/s", time=self.time)
        return {"peak_gust_m_s": float(gust.max())}


class SoufriereEruption(_T1Base):
    """A randomised stand-in timeline around the 2021 onset step, with a constant mass rate. Not the published event sequence."""

    id = "eruption"
    outputs = (
        spec("eruption.phase"),
        spec("eruption.tremor"),
        spec("eruption.gas"),
        spec("eruption.explosion"),
        spec("eruption.mass_rate"),
    )

    def __init__(
        self,
        time: TimeAxis = ST_VINCENT_TIME,
        erupts: bool | None = True,
        scenario_name: str = "st_vincent_2021",
    ) -> None:
        self.time, self.erupts = time, erupts
        self.data = _load_scenario_json(scenario_name)

    def run(self, fields, rng) -> dict[str, float]:
        erupts = bool(rng.random() < 0.75) if self.erupts is None else self.erupts
        base_onset = int(self.data.get("onset_step") or 18)
        onset = max(6, min(self.time.n - 6, base_onset + int(rng.integers(-3, 4))))
        steps = np.arange(self.time.n)

        phase = np.where(steps < onset // 2, PHASES["unrest"], PHASES["escalating"] if erupts else PHASES["unrest"])
        phase = np.where(steps >= onset, PHASES["erupting"] if erupts else PHASES["fading"], phase).astype(float)

        draws = rng.random((2, self.time.n))
        rising = np.where(steps < onset, 0.25 + 0.65 * steps / max(1, onset), 0.15 if erupts else 0.0)
        tremor = (draws[0] < rising).astype(float)
        gas = (draws[1] < rising * 0.75).astype(float)
        tremor[0] = 1.0  # Precursory seismic swarm at step 0 per IPGP report

        explosion = ((phase == PHASES["erupting"]) & ((steps - onset) % 3 == 0)).astype(float)
        mass_rate = np.where(phase == PHASES["erupting"], 1.5e6 * (0.6 + 0.4 * explosion), 0.0)

        fields.put("eruption.phase", phase, "dimensionless", time=self.time)
        fields.put("eruption.tremor", tremor, "dimensionless", time=self.time)
        fields.put("eruption.gas", gas, "dimensionless", time=self.time)
        fields.put("eruption.explosion", explosion, "dimensionless", time=self.time)
        fields.put("eruption.mass_rate", mass_rate, "kg/s", time=self.time)
        return {"onset_step": float(onset if erupts else -1)}


class SuzukiTephra(_T1Base):
    """T1 advection-diffusion tephra fallout model driven by mass eruption rate and wind."""

    id = "tephra"
    inputs = (spec("eruption.mass_rate"), spec("atmos.wind_bearing"), spec("atmos.wind_speed"))
    outputs = (spec("tephra.deposit_load"),)

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        time: TimeAxis = ST_VINCENT_TIME,
        vent: tuple[float, float] = (685000.0, 1485000.0),
    ) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def run(self, fields, rng) -> dict[str, float]:
        mer = fields.get("eruption.mass_rate", "kg/s")
        bearing = np.radians(fields.get("atmos.wind_bearing", "degree"))
        wind_u = fields.get("atmos.wind_speed", "m/s")

        ex, ey, dist = _xy_offsets(self.grid, self.vent)
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        cumulative = np.zeros_like(dist)

        for t in range(self.time.n):
            if mer[t] > 0.0:
                ux = math.sin(bearing[t])
                uy = math.cos(bearing[t])
                along = np.maximum(0.0, ex * ux + ey * uy)
                cross = np.abs(ex * uy - ey * ux)
                sigma = 650.0 + 0.22 * along
                plume_kernel = np.exp(-(cross**2) / (2.0 * sigma**2)) * np.exp(-dist / (2200.0 + 90.0 * wind_u[t]))
                proximal = np.exp(-((dist / 950.0) ** 2))
                step_load = (mer[t] / 1.5e6) * (3.8 * plume_kernel + 2.2 * proximal)
                cumulative = cumulative + step_load
            frames[t] = cumulative

        fields.put("tephra.deposit_load", frames, "kg/m**2", self.grid, self.time)
        return {"max_tephra_kg_m2": float(cumulative.max())}


class GaussianGas(_T1Base):
    """T1 downwind SO2 plume dispersion model."""

    id = "gas"
    inputs = (spec("eruption.gas"), spec("eruption.mass_rate"), spec("atmos.wind_bearing"))
    outputs = (spec("gas.so2_concentration"),)

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        time: TimeAxis = ST_VINCENT_TIME,
        vent: tuple[float, float] = (685000.0, 1485000.0),
    ) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def run(self, fields, rng) -> dict[str, float]:
        gas_flag = fields.get("eruption.gas", "dimensionless")
        mer = fields.get("eruption.mass_rate", "kg/s")
        bearing = np.radians(fields.get("atmos.wind_bearing", "degree"))
        ex, ey, dist = _xy_offsets(self.grid, self.vent)

        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        for t in range(self.time.n):
            source_strength = 450.0 * gas_flag[t] + (1200.0 if mer[t] > 0 else 0.0)
            if source_strength > 0.0:
                ux, uy = math.sin(bearing[t]), math.cos(bearing[t])
                along = np.maximum(0.0, ex * ux + ey * uy)
                cross = np.abs(ex * uy - ey * ux)
                sigma = 500.0 + 0.25 * along
                frames[t] = source_strength * np.exp(-(cross**2) / (2.0 * sigma**2)) * np.exp(-dist / 3200.0)

        fields.put("gas.so2_concentration", frames, "ug/m**3", self.grid, self.time)
        return {"max_so2_ug_m3": float(frames.max())}


class EnergyConePDC(_T1Base):
    """T1 energy-cone (H/L) pyroclastic density current runout model."""

    id = "pdc"
    inputs = (spec("terrain.elevation"), spec("terrain.land_mask"), spec("eruption.phase"))
    outputs = (spec("pdc.arrival"), spec("pdc.active"))

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        time: TimeAxis = ST_VINCENT_TIME,
        vent: tuple[float, float] = (685000.0, 1485000.0),
        hl_ratio: float = 0.38,
    ) -> None:
        self.grid, self.time, self.vent, self.hl_ratio = grid, time, vent, hl_ratio

    def run(self, fields, rng) -> dict[str, float]:
        elev = fields.get("terrain.elevation", "m", self.grid)
        land = fields.get("terrain.land_mask", "dimensionless", self.grid) > 0.0
        phase = fields.get("eruption.phase", "dimensionless")
        erupting = np.flatnonzero(phase == PHASES["erupting"])

        _ex, _ey, dist = _xy_offsets(self.grid, self.vent)
        h_collapse = float(elev.max()) + 220.0
        energy_line = h_collapse - self.hl_ratio * dist - elev
        reachable = land & ((energy_line > 0.0) | (dist <= 1550.0))

        arrival = np.full((self.grid.ny, self.grid.nx), np.inf)
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        if erupting.size:
            first = int(erupting[0]) + int(rng.integers(1, 3))
            if first < self.time.n:
                arrival[reachable] = first * self.time.dt_s
                frames[first:][:, reachable] = 1.0

        fields.put("pdc.arrival", arrival, "s", self.grid)
        fields.put("pdc.active", frames, "dimensionless", self.grid, self.time)
        return {"pdc_area_cells": float(reachable.sum())}


class LaharzLahar(_T1Base):
    """T1 rain-triggered lahar inundation in low-elevation radial drainage valleys."""

    id = "lahar"
    inputs = (spec("terrain.elevation"), spec("terrain.land_mask"), spec("tephra.deposit_load"), spec("atmos.rain_rate"))
    outputs = (spec("lahar.depth"),)

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        time: TimeAxis = ST_VINCENT_TIME,
        vent: tuple[float, float] = (685000.0, 1485000.0),
    ) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def run(self, fields, rng) -> dict[str, float]:
        elev = fields.get("terrain.elevation", "m", self.grid)
        land = fields.get("terrain.land_mask", "dimensionless", self.grid) > 0.0
        tephra = fields.get("tephra.deposit_load", "kg/m**2", self.grid)
        rain = fields.get("atmos.rain_rate", "mm/h")

        ex, ey, dist = _xy_offsets(self.grid, self.vent)
        theta = np.arctan2(ey, ex)
        in_channel = land & (dist > 600.0) & (np.cos(4.0 * theta) > 0.82) & (elev < 650.0)

        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        for t in range(self.time.n):
            if rain[t] > 1.0 and tephra[t].max() > 1.5:
                frames[t] = np.where(in_channel, 0.45 * (rain[t] / 3.0), 0.0)

        fields.put("lahar.depth", frames, "m", self.grid, self.time)
        return {"max_lahar_depth_m": float(frames.max())}


class DomeLava(_T1Base):
    """T1 proximal summit dome & effusive lava lobe footprint."""

    id = "lava"
    inputs = (spec("terrain.elevation"), spec("eruption.phase"))
    outputs = (spec("lava.footprint"),)

    def __init__(
        self,
        grid: GridSpec = ST_VINCENT_GRID,
        time: TimeAxis = ST_VINCENT_TIME,
        vent: tuple[float, float] = (685000.0, 1485000.0),
    ) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def run(self, fields, rng) -> dict[str, float]:
        phase = fields.get("eruption.phase", "dimensionless")
        _ex, _ey, dist = _xy_offsets(self.grid, self.vent)
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        radius = 0.0
        for t in range(self.time.n):
            if phase[t] == PHASES["erupting"]:
                radius = min(550.0, radius + 45.0)
            if radius > 0.0:
                frames[t] = (dist <= radius).astype(float)

        fields.put("lava.footprint", frames, "dimensionless", self.grid, self.time)
        return {"max_lava_radius_m": float(radius)}


def st_vincent_domains(erupts: bool | None = True) -> tuple[Domain, ...]:
    """Returns the complete T1 domain stack for April 2021 La Soufriere (St. Vincent)."""
    return (
        StVincentTerrain(),
        StVincentAtmos(),
        HollandStorm(),
        SoufriereEruption(erupts=erupts),
        SuzukiTephra(),
        GaussianGas(),
        EnergyConePDC(),
        LaharzLahar(),
        DomeLava(),
    )


def st_vincent_scenario(erupts: bool | None = True) -> ScenarioSpec:
    """Builds the T1 `st_vincent_2021` ScenarioSpec."""
    return ScenarioSpec(
        "st_vincent_2021",
        ST_VINCENT_GRID,
        ST_VINCENT_TILES,
        ST_VINCENT_TIME,
        8,
        st_vincent_domains(erupts),
        {
            "spawn": [(685000.0 + 1000.0, 1485000.0 - 300.0)],
            "vent": [(685000.0, 1485000.0)],
            "assembly": [
                (685000.0 - 3100.0, 1485000.0 + 400.0),
                (685000.0 + 3100.0, 1485000.0 - 400.0),
            ],
            "water": [
                (685000.0 + 800.0, 1485000.0 - 300.0),
                (685000.0 - 2900.0, 1485000.0 + 400.0),
            ],
        },
    )


def build_st_vincent_pack(seed: int = 1, erupts: bool | None = True) -> ScenarioPack:
    """Builds and returns a SHA-256 content-hashed ScenarioPack for St. Vincent 2021."""
    return build_pack(st_vincent_scenario(erupts=erupts), seed=seed)

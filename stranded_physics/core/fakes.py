"""T0 stand-ins, so every stream can start at once. Deliberately unphysical. Never cite these."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from stranded_physics.core.api import Domain, FieldSpec, GridSpec, Parameter, ScenarioSpec, TimeAxis
from stranded_physics.core.fields import spec

HORIZON_STEPS = 36
STEP_S = 7200.0
FAKE_GRID = GridSpec("EPSG:32620", 680000.0, 1490000.0, 200.0, 50, 50)
FAKE_TILES = GridSpec("EPSG:32620", 680000.0, 1490000.0, 250.0, 40, 40)
FAKE_TIME = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), STEP_S, HORIZON_STEPS)
PHASES = {"unrest": 0, "escalating": 1, "erupting": 2, "fading": 3}


class _Fake:
    tier = "T0"
    id = ""
    inputs: tuple[FieldSpec, ...] = ()
    outputs: tuple[FieldSpec, ...] = ()
    parameters: tuple[Parameter, ...] = ()

    def check_validity(self, fields) -> list[str]:
        return []


def _distance_grid(grid: GridSpec, centre: tuple[float, float]) -> np.ndarray:
    xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m
    ys = grid.y0_m - (np.arange(grid.ny) + 0.5) * grid.dx_m
    return np.hypot(*np.meshgrid(xs - centre[0], ys - centre[1]))


class ConeTerrain(_Fake):
    """A smooth cone in the sea, standing in for `terrain` until the real DEM arrives."""

    id = "terrain"
    outputs = (spec("terrain.elevation"), spec("terrain.land_mask"), spec("terrain.zone"))

    def __init__(self, grid: GridSpec = FAKE_GRID, vent: tuple[float, float] = (685000.0, 1485000.0)) -> None:
        self.grid, self.vent = grid, vent

    def run(self, fields, rng) -> dict[str, float]:
        distance = _distance_grid(self.grid, self.vent)
        elevation = 1000.0 - 0.25 * distance
        fields.put("terrain.elevation", elevation, "m", self.grid)
        fields.put("terrain.land_mask", (elevation > 0).astype(float), "dimensionless", self.grid)
        fields.put("terrain.zone", np.select([distance < 1200, distance < 2000], [2.0, 1.0], 0.0), "dimensionless", self.grid)
        return {}


class UniformWind(_Fake):
    id = "atmos"
    outputs = (spec("atmos.wind_speed"), spec("atmos.wind_bearing"), spec("atmos.rain_rate"), spec("atmos.air_temperature"))

    def __init__(self, time: TimeAxis = FAKE_TIME, speed: float = 10.0, bearing: float = 90.0, rain: float = 0.0, temperature: float = 25.0) -> None:
        self.time, self.speed, self.bearing, self.rain, self.temperature = time, speed, bearing, rain, temperature

    def run(self, fields, rng) -> dict[str, float]:
        for name, value, unit in (
            ("wind_speed", self.speed, "m/s"),
            ("wind_bearing", self.bearing, "degree"),
            ("rain_rate", self.rain, "mm/h"),
            ("air_temperature", self.temperature, "degC"),
        ):
            fields.put(f"atmos.{name}", np.full(self.time.n, value), unit, time=self.time)
        return {}


class ConstantRain(UniformWind):
    """Same forcing, always raining, for testing lahar triggers."""

    def __init__(self, time: TimeAxis = FAKE_TIME, rain: float = 10.0) -> None:
        super().__init__(time, rain=rain)


class BoxEruption(_Fake):
    """Signs rise, then the eruption starts at a seeded step. Some seeds fade, for false alarms."""

    id = "eruption"
    outputs = (spec("eruption.phase"), spec("eruption.tremor"), spec("eruption.gas"), spec("eruption.explosion"), spec("eruption.mass_rate"))

    def __init__(self, time: TimeAxis = FAKE_TIME, erupts: bool | None = None) -> None:
        self.time, self.erupts = time, erupts

    def run(self, fields, rng) -> dict[str, float]:
        erupts = bool(rng.random() < 2 / 3) if self.erupts is None else self.erupts
        onset = int(rng.integers(6, 18))
        steps = np.arange(self.time.n)
        phase = np.where(steps < onset // 2, PHASES["unrest"], PHASES["escalating"] if erupts else PHASES["unrest"])
        phase = np.where(steps >= onset, PHASES["erupting"] if erupts else PHASES["fading"], phase).astype(float)
        draws = rng.random((2, self.time.n))
        rising = np.where(steps < onset, 0.15 + 0.6 * steps / onset, 0.05 if erupts else 0.0)
        explosion = ((phase == PHASES["erupting"]) & ((steps - onset) % 4 == 0)).astype(float)
        fields.put("eruption.phase", phase, "dimensionless", time=self.time)
        fields.put("eruption.tremor", (draws[0] < rising).astype(float), "dimensionless", time=self.time)
        fields.put("eruption.gas", (draws[1] < rising * 0.7).astype(float), "dimensionless", time=self.time)
        fields.put("eruption.explosion", explosion, "dimensionless", time=self.time)
        fields.put("eruption.mass_rate", (phase == PHASES["erupting"]) * 1e6, "kg/s", time=self.time)
        return {}


class BoxTephra(_Fake):
    """Ash piles up steadily downwind while erupting."""

    id = "tephra"
    inputs = (spec("eruption.mass_rate"), spec("atmos.wind_bearing"))
    outputs = (spec("tephra.deposit_load"),)

    def __init__(self, grid: GridSpec = FAKE_GRID, time: TimeAxis = FAKE_TIME, vent: tuple[float, float] = (685000.0, 1485000.0)) -> None:
        self.grid, self.time, self.vent = grid, time, vent

    def run(self, fields, rng) -> dict[str, float]:
        active = fields.get("eruption.mass_rate", "kg/s") > 0
        bearing = np.radians(fields.get("atmos.wind_bearing", "degree"))
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        distance = _distance_grid(self.grid, self.vent)
        xs = self.grid.x0_m + (np.arange(self.grid.nx) + 0.5) * self.grid.dx_m - self.vent[0]
        ys = self.grid.y0_m - (np.arange(self.grid.ny) + 0.5) * self.grid.dx_m - self.vent[1]
        ex, ey = np.meshgrid(xs, ys)
        total = np.zeros_like(distance)
        for t in range(self.time.n):
            if active[t]:
                downwind = ex * np.sin(bearing[t]) + ey * np.cos(bearing[t])
                total = total + np.where(downwind > 0, 5.0, 1.0) * np.exp(-distance / 3000.0)
            frames[t] = total
        fields.put("tephra.deposit_load", frames, "kg/m**2", self.grid, self.time)
        return {}


class BoxPdc(_Fake):
    """A circle of flow around the vent, some steps after onset."""

    id = "pdc"
    inputs = (spec("eruption.phase"),)
    outputs = (spec("pdc.arrival"), spec("pdc.active"))

    def __init__(
        self, grid: GridSpec = FAKE_GRID, time: TimeAxis = FAKE_TIME, vent: tuple[float, float] = (685000.0, 1485000.0), radius_m: float = 1500.0
    ) -> None:
        self.grid, self.time, self.vent, self.radius = grid, time, vent, radius_m

    def run(self, fields, rng) -> dict[str, float]:
        phase = fields.get("eruption.phase", "dimensionless")
        erupting = np.flatnonzero(phase == PHASES["erupting"])
        inside = _distance_grid(self.grid, self.vent) <= self.radius
        arrival = np.full((self.grid.ny, self.grid.nx), np.inf)
        frames = np.zeros((self.time.n, self.grid.ny, self.grid.nx))
        if erupting.size:
            first = int(erupting[0]) + int(rng.integers(0, 4))
            if first < self.time.n:
                arrival[inside] = first * self.time.dt_s
                frames[first:][:, inside] = 1.0
        fields.put("pdc.arrival", arrival, "s", self.grid)
        fields.put("pdc.active", frames, "dimensionless", self.grid, self.time)
        return {}


def fake_domains(erupts: bool | None = None) -> tuple[Domain, ...]:
    return ConeTerrain(), UniformWind(), BoxEruption(erupts=erupts), BoxTephra(), BoxPdc()


def fake_scenario(erupts: bool | None = None) -> ScenarioSpec:
    return ScenarioSpec(
        "fake_cone",
        FAKE_GRID,
        FAKE_TILES,
        FAKE_TIME,
        8,
        fake_domains(erupts),
        {
            "spawn": [(685000.0 + 1000.0, 1485000.0 - 300.0)],
            "vent": [(685000.0, 1485000.0)],
            "assembly": [(685000.0 - 3500.0, 1485000.0 + 500.0), (685000.0 + 3500.0, 1485000.0 - 500.0)],
            "water": [(685000.0 + 800.0, 1485000.0 - 300.0), (685000.0 - 3200.0, 1485000.0 + 500.0)],
        },
    )

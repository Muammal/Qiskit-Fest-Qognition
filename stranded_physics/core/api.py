"""Frozen interfaces for the physics engine. Change only through workboard/changes/.

Categories share data only through `Fields`. They never import each other.
Every value carries its own source, valid range and role, so a claim can be traced to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Mapping, Protocol, Sequence, get_args

import numpy as np
import pint

INTERFACE_VERSION = "0.1.0"
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity

Role = Literal["input", "calibrated", "anchor", "prediction", "convention"]
Status = Literal["measured", "derived", "literature", "assumption"]
Verdict = Literal["PASS", "FAIL", "INSUFFICIENT_DATA", "NO_TARGET", "NOT_RUN", "OUT_OF_DOMAIN"]
Split = Literal["calibration", "holdout", "reference"]
Kind = Literal["static", "frames", "arrival", "series"]
XY = tuple[float, float]


class InterfaceError(ValueError):
    """A record or field breaks the interface. Never caught silently."""


@dataclass(frozen=True)
class Parameter:
    """One value, with its own source. Never one citation for a whole file."""

    id: str
    value: pint.Quantity
    valid: tuple[pint.Quantity, pint.Quantity]
    role: Role
    status: Status
    source: str | None = None  # DOI or URL plus table, row or page. None only for assumptions.
    sd: pint.Quantity | None = None

    def __post_init__(self) -> None:
        if self.role not in get_args(Role):
            raise InterfaceError(f"{self.id}: unknown role {self.role!r}")
        if self.status not in get_args(Status):
            raise InterfaceError(f"{self.id}: unknown status {self.status!r}")
        if self.status != "assumption" and not self.source:
            raise InterfaceError(f"{self.id}: status {self.status!r} needs a source locator")
        low, high = self.valid
        try:
            inside = low <= self.value <= high
        except pint.DimensionalityError as error:
            raise InterfaceError(f"{self.id}: value and valid range have different units") from error
        if not inside:
            raise InterfaceError(f"{self.id}: value {self.value} outside its valid range")


@dataclass(frozen=True)
class DatasetRecord:
    """How new data accumulates. Add a record; never hide setup details in a script or filename."""

    id: str
    category: str
    kind: str
    url: str
    retrieved_utc: str
    sha256: str
    licence: str
    licence_confirmed: bool
    citation: str
    split: Split
    content_check: str  # A rule that rejects bot pages, e.g. "min_bytes:1000" or "json_key:hourly".
    notes: str = ""

    def __post_init__(self) -> None:
        if self.split not in get_args(Split):
            raise InterfaceError(f"{self.id}: unknown split {self.split!r}")
        if len(self.sha256) != 64:
            raise InterfaceError(f"{self.id}: sha256 must be 64 hex characters")
        if not self.content_check:
            raise InterfaceError(f"{self.id}: content_check is required; bot pages have fooled us before")


@dataclass(frozen=True)
class GridSpec:
    """North-up grid. Row 0 is the northern edge. Arrays are [row, column] at cell centres."""

    crs: str
    x0_m: float  # Western edge.
    y0_m: float  # Northern edge.
    dx_m: float
    nx: int
    ny: int

    def centre(self, row: int, col: int) -> XY:
        return self.x0_m + (col + 0.5) * self.dx_m, self.y0_m - (row + 0.5) * self.dx_m

    def locate(self, xy: XY) -> tuple[int, int] | None:
        """The (row, col) containing a point, or None outside the grid."""
        col = int(np.floor((xy[0] - self.x0_m) / self.dx_m))
        row = int(np.floor((self.y0_m - xy[1]) / self.dx_m))
        return (row, col) if 0 <= row < self.ny and 0 <= col < self.nx else None


@dataclass(frozen=True)
class TimeAxis:
    t0_utc: datetime
    dt_s: float
    n: int

    def index_at(self, t_s: float) -> int:
        """Latest frame at or before t_s. Never a future frame, so a mind cannot see ahead."""
        if t_s < 0:
            raise InterfaceError(f"time {t_s} is before the start of the axis")
        return min(int(t_s // self.dt_s), self.n - 1)


@dataclass(frozen=True)
class FieldSpec:
    name: str  # "category.quantity", and listed in core/fields.py
    unit: str
    kind: Kind


class Fields(Protocol):
    """The only channel between categories. Converts units and regrids, and rejects undeclared use."""

    def get(self, name: str, unit: str, grid: GridSpec | None = None, t_s: float | None = None) -> np.ndarray: ...
    def put(self, name: str, data: np.ndarray, unit: str, grid: GridSpec | None = None, time: TimeAxis | None = None) -> None: ...


class Domain(Protocol):
    """One implementation of one category at one fidelity tier."""

    id: str
    tier: str  # T0 fake or legacy, T1 reduced-order, T2 in-house solver, TX external code.
    inputs: tuple[FieldSpec, ...]
    outputs: tuple[FieldSpec, ...]
    parameters: tuple[Parameter, ...]

    def check_validity(self, fields: Fields) -> list[str]:
        """Reasons the inputs are outside this model's valid range. Non-empty means OUT_OF_DOMAIN."""
        ...

    def run(self, fields: Fields, rng: np.random.Generator) -> dict[str, float]:
        """Write outputs and return budget residuals, e.g. {"mass_kg": 3.1e-6}."""
        ...


@dataclass(frozen=True)
class ScenarioSpec:
    """Which categories, at which tiers, make up a map and its conditions."""

    name: str
    grid: GridSpec
    contract_grid: GridSpec  # The tile grid minds see through state["pos"].
    time: TimeAxis
    t0_local_hour: int
    domains: tuple[Domain, ...]
    sites: Mapping[str, Sequence[XY]] = field(default_factory=dict)  # spawn, assembly, water, vent.


class ScenarioPack(Protocol):
    """Precomputed, immutable hazards for one scenario and seed. The runtime only reads this."""

    scenario: str
    seed: int
    content_hash: str
    verdicts: Mapping[str, Verdict]
    grid: GridSpec
    contract_grid: GridSpec
    time: TimeAxis
    agent_uniforms: np.ndarray  # [step, draw]
    sites: Mapping[str, Sequence[XY]]
    t0_local_hour: int

    def sample(self, name: str, xy_m: XY, t_s: float | None = None) -> float: ...
    def series(self, name: str) -> np.ndarray: ...  # Hidden state. Never handed to a mind.
    def frame(self, name: str, t_s: float | None = None) -> np.ndarray: ...  # For replay and the GUI.


@dataclass(frozen=True)
class Percept:
    """What a person could notice at their own position, up to now. Minds learn only through this."""

    t_s: float
    felt_tremor: bool
    gas_smell: bool
    explosion_heard: bool
    ash_kg_m2: float
    rain_mm_h: float
    flow_visible: bool
    wind_m_s: float = 0.0  # Added by change note 002. Storm wind where a storm is in the scenario.

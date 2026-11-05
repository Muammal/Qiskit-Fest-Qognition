"""Names, units and kinds of everything categories exchange, and the store that enforces them."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pint

from stranded_physics.core.api import FieldSpec, GridSpec, InterfaceError, Q_, TimeAxis

# Adding a name is additive, and needs only a change note. Renaming is breaking.
CANONICAL: dict[str, tuple[str, str]] = {
    "terrain.elevation": ("m", "static"),
    "terrain.land_mask": ("dimensionless", "static"),
    "terrain.zone": ("dimensionless", "static"),  # 0 safe, 1 caution, 2 danger. Static, never from future hazards.
    "terrain.land_cover": ("dimensionless", "static"),
    "terrain.flow_accumulation": ("m**2", "static"),  # Upslope contributing area of each cell.
    "terrain.height_above_drainage": ("m", "static"),
    "atmos.rain_rate": ("mm/h", "series"),
    "atmos.wind_speed": ("m/s", "series"),  # At 10 m.
    "atmos.wind_bearing": ("degree", "series"),  # The bearing air moves toward. 0 north, 90 east.
    "atmos.wind_speed_500hpa": ("m/s", "series"),
    "atmos.wind_bearing_500hpa": ("degree", "series"),
    "atmos.wind_speed_200hpa": ("m/s", "series"),
    "atmos.wind_bearing_200hpa": ("degree", "series"),
    "atmos.air_temperature": ("degC", "series"),
    "storm.max_wind": ("m/s", "series"),
    "eruption.phase": ("dimensionless", "series"),  # 0 unrest, 1 escalating, 2 erupting, 3 fading.
    "eruption.tremor": ("dimensionless", "series"),
    "eruption.gas": ("dimensionless", "series"),
    "eruption.explosion": ("dimensionless", "series"),
    "eruption.mass_rate": ("kg/s", "series"),
    "eruption.column_height": ("m", "series"),  # Above the vent.
    "tephra.deposit_load": ("kg/m**2", "frames"),
    "pdc.arrival": ("s", "arrival"),  # First arrival time. Infinity where a flow never reaches.
    "pdc.active": ("dimensionless", "frames"),
    "lahar.depth": ("m", "frames"),
    "lava.footprint": ("dimensionless", "frames"),
    "gas.so2_concentration": ("ug/m**3", "frames"),
    "exposure.roof_failure": ("dimensionless", "frames"),  # Share of ordinary roofs that would have failed under the ash so far.
}


def spec(name: str) -> FieldSpec:
    """The FieldSpec for a canonical name. Unknown names are an error, never a new field by accident."""
    if name not in CANONICAL:
        raise InterfaceError(f"{name!r} is not in core/fields.py; add it through workboard/changes/")
    unit, kind = CANONICAL[name]
    return FieldSpec(name, unit, kind)  # type: ignore[arg-type]


@dataclass(frozen=True)
class _Stored:
    data: np.ndarray
    unit: str
    kind: str
    grid: GridSpec | None
    time: TimeAxis | None


def _convert(data: np.ndarray, source: str, target: str) -> np.ndarray:
    if source == target:
        return data
    try:
        return Q_(data, source).to(target).magnitude
    except pint.DimensionalityError as error:
        raise InterfaceError(f"cannot convert {source!r} to {target!r}") from error


def _regrid(data: np.ndarray, source: GridSpec, target: GridSpec) -> np.ndarray:
    """Nearest-neighbour regridding, per frame. Higher-order schemes come with the tiers that need them."""
    if source == target:
        return data
    if source.crs != target.crs:
        raise InterfaceError(f"grids use different CRS: {source.crs} and {target.crs}")
    columns = np.clip(np.floor((target.x0_m + (np.arange(target.nx) + .5) * target.dx_m - source.x0_m) / source.dx_m).astype(int), 0, source.nx - 1)
    rows = np.clip(np.floor((source.y0_m - (target.y0_m - (np.arange(target.ny) + .5) * target.dx_m)) / source.dx_m).astype(int), 0, source.ny - 1)
    return data[..., rows[:, None], columns[None, :]]


class FieldStore:
    """Holds every field for one build. Each stored array is read-only."""

    def __init__(self) -> None:
        self._fields: dict[str, _Stored] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._fields

    def names(self) -> list[str]:
        return sorted(self._fields)

    def stored(self, name: str) -> _Stored:
        return self._fields[name]

    def put(self, name: str, data: np.ndarray, unit: str, grid: GridSpec | None = None, time: TimeAxis | None = None) -> None:
        declared = spec(name)
        if name in self._fields:
            raise InterfaceError(f"{name} was already written; a field has exactly one producer")
        array = np.array(_convert(np.asarray(data, dtype=float), unit, declared.unit), dtype=float)
        if np.isnan(array).any():
            raise InterfaceError(f"{name} contains NaN; a missing value must be handled explicitly")
        expected = _expected_shape(declared.kind, grid, time)
        if array.shape != expected:
            raise InterfaceError(f"{name} has shape {array.shape}; {declared.kind} needs {expected}")
        array.setflags(write=False)
        self._fields[name] = _Stored(array, declared.unit, declared.kind, grid, time)

    def get(self, name: str, unit: str, grid: GridSpec | None = None, t_s: float | None = None) -> np.ndarray:
        if name not in self._fields:
            raise InterfaceError(f"{name} has not been produced")
        stored = self._fields[name]
        data = stored.data
        if t_s is not None and stored.time is not None:
            data = data[stored.time.index_at(t_s)]
        if grid is not None and stored.grid is not None:
            data = _regrid(data, stored.grid, grid)
        return _convert(data, stored.unit, unit)


def _expected_shape(kind: str, grid: GridSpec | None, time: TimeAxis | None) -> tuple[int, ...]:
    if kind in ("static", "arrival"):
        if grid is None:
            raise InterfaceError(f"{kind} fields need a grid")
        return grid.ny, grid.nx
    if time is None:
        raise InterfaceError(f"{kind} fields need a time axis")
    if kind == "series":
        return (time.n,)
    if grid is None:
        raise InterfaceError("frames need a grid")
    return time.n, grid.ny, grid.nx


class ScopedFields:
    """What a category sees: only the inputs and outputs it declared. Coupling stays visible."""

    def __init__(self, store: FieldStore, domain_id: str, inputs: tuple[FieldSpec, ...], outputs: tuple[FieldSpec, ...]) -> None:
        self._store, self._id = store, domain_id
        self._inputs = {f.name for f in inputs}
        self._outputs = {f.name for f in outputs}

    def get(self, name: str, unit: str, grid: GridSpec | None = None, t_s: float | None = None) -> np.ndarray:
        if name not in self._inputs:
            raise InterfaceError(f"{self._id} read {name} without declaring it as an input")
        return self._store.get(name, unit, grid, t_s)

    def put(self, name: str, data: np.ndarray, unit: str, grid: GridSpec | None = None, time: TimeAxis | None = None) -> None:
        if name not in self._outputs:
            raise InterfaceError(f"{self._id} wrote {name} without declaring it as an output")
        if not name.startswith(self._id + "."):
            raise InterfaceError(f"{self._id} may only write its own fields, not {name}")
        self._store.put(name, data, unit, grid, time)

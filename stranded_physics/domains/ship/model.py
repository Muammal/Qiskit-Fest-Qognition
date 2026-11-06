"""T1 wall-sided box hull: orifice ingress, hydrostatic sink/trim and overflow.

Flood storage starts at the breach datum, at the specified depth below the
initial waterline. A compartment has a horizontal internal free surface.
No pumps, longitudinal doors, waves, hull breakup or free-surface stability
correction are resolved. Titanic is a record set, not a solver special case.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from math import isfinite, sqrt
from pathlib import Path

import numpy as np

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import spec as field_spec
from stranded_physics.core.records import load_parameters

METRES_PER_FOOT = 0.3048
KG_PER_TONNE = 1000.0
KG_PER_LONG_TON = 1016.05
SECONDS_PER_MINUTE = 60.0
PARAMETERS = load_parameters(Path(__file__).with_name("params.toml"))
_PARAMS = {p.id.split(".", 1)[1]: p for p in PARAMETERS}
SETTINGS = {name: float(p.value.magnitude) for name, p in _PARAMS.items()}
SETTINGS["hole_depth_below_waterline"] = float(_PARAMS["hole_depth_below_waterline"].value.to("m").magnitude)


def _value(value, name):
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise InterfaceError(f"{name} must be a finite number") from error
    low, high = _PARAMS[name].valid
    if not isfinite(value) or not low.magnitude <= value <= high.magnitude:
        raise InterfaceError(f"{name} outside [{low.magnitude}, {high.magnitude}]")
    return value


def _integer(value, name):
    checked = _value(value, name)
    if checked != int(checked):
        raise InterfaceError(f"{name} must be an integer")
    return int(checked)


@dataclass(frozen=True)
class Compartment:
    name: str
    length_m: float
    top_above_waterline_m: float

    def __post_init__(self):
        _value(self.length_m, "length")
        _value(self.top_above_waterline_m, "bulkhead_top")


@dataclass(frozen=True)
class ShipSpec:
    name: str
    length_m: float
    beam_m: float
    draught_m: float
    displacement_t: float
    boat_deck_above_waterline_m: float
    compartments: tuple[Compartment, ...]

    def __post_init__(self):
        for name, value in (
            ("length", self.length_m),
            ("beam", self.beam_m),
            ("draught", self.draught_m),
            ("displacement", self.displacement_t),
            ("boat_deck", self.boat_deck_above_waterline_m),
        ):
            _value(value, name)
        _integer(len(self.compartments), "compartment_count")
        if not all(isinstance(c, Compartment) for c in self.compartments):
            raise InterfaceError("compartments must contain Compartment records")
        if not np.isclose(sum(c.length_m for c in self.compartments), self.length_m, rtol=1e-12, atol=0.0):
            raise InterfaceError("compartment lengths must sum to ship length")


@dataclass(frozen=True)
class Breach:
    areas_m2: tuple[float, ...]

    def __post_init__(self):
        for area in self.areas_m2:
            _value(area, "breach_area")


@dataclass(frozen=True)
class Boat:
    name: str
    capacity: int
    launch_minutes: float
    from_record: bool

    def __post_init__(self):
        _integer(self.capacity, "boat_capacity")
        _value(self.launch_minutes * SECONDS_PER_MINUTE, "event_time")
        if not isinstance(self.from_record, bool):
            raise InterfaceError("from_record must be boolean")


@dataclass(frozen=True)
class FloodResult:
    times_s: np.ndarray
    water_t: np.ndarray
    draught_bow_m: np.ndarray
    draught_stern_m: np.ndarray
    foundered_s: float | None


def titanic_ship() -> ShipSpec:
    with Path(__file__).with_name("compartments.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    compartments = []
    for i, row in enumerate(rows):
        length_ft = _value(row["length_ft"], f"compartment_{i}_length_ft")
        if length_ft != SETTINGS[f"compartment_{i}_length_ft"]:
            raise InterfaceError("compartment CSV disagrees with parameter record")
        deck = "D" if SETTINGS[f"compartment_{i}_deck"] else "E"
        if row["watertight_to"] != deck:
            raise InterfaceError("compartment deck disagrees with parameter record")
        compartments.append(Compartment(row["name"], length_ft * METRES_PER_FOOT, SETTINGS[f"deck_{deck.lower()}_ft"] * METRES_PER_FOOT))
    return ShipSpec(
        "Titanic",
        SETTINGS["titanic_length_ft"] * METRES_PER_FOOT,
        SETTINGS["titanic_beam_ft"] * METRES_PER_FOOT,
        SETTINGS["titanic_draught_ft"] * METRES_PER_FOOT,
        SETTINGS["titanic_displacement_long_tons"] * KG_PER_LONG_TON / KG_PER_TONNE,
        SETTINGS["titanic_boat_deck_ft"] * METRES_PER_FOOT,
        tuple(compartments),
    )


def titanic_breach() -> Breach:
    ship = titanic_ship()
    damaged = {"Bow to A", "A-B", "B-C", "C-D", "D-E", "E-F"}
    weights = np.array([c.length_m ** SETTINGS["breach_split_exponent"] if c.name in damaged else 0.0 for c in ship.compartments])
    return Breach(tuple(SETTINGS["titanic_breach_ft2"] * METRES_PER_FOOT**2 * weights / weights.sum()))


def titanic_recorded_sinking() -> tuple[float, float]:
    """Replay milestones in minutes after collision; convert for an axis in seconds."""
    # British report, "Final effect of the damage": "getting close down to the
    # water, about half an hour before she disappeared (1.50 a. m.)" and
    # "The ship disappeared at 2.20 a. m." Linear deck advance is a simplification.
    return SETTINGS["titanic_bow_awash_min"], SETTINGS["titanic_foundered_min"]


def titanic_boats_revised() -> tuple[Boat, ...]:
    """The same boats, at the times in Wormstedt, Fitch and Behe's revised table. It re-examines the 1912 inquiry's table, and all its times are approximate."""
    with Path(__file__).with_name("boats_revised.csv").open(encoding="utf-8", newline="") as stream:
        minutes = {row["name"]: float(row["launch_after_impact_min"]) for row in csv.DictReader(stream)}
    return tuple(Boat(boat.name, boat.capacity, minutes[boat.name], True) for boat in titanic_boats())


def titanic_boats() -> tuple[Boat, ...]:
    with Path(__file__).with_name("boats.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    boats = []
    for row in rows:
        tag = row["name"].removeprefix("No. ").lower()
        capacity = _integer(row["capacity"], f"boat_{tag}_capacity")
        minutes = _value(row["launch_after_impact_min"], f"boat_{tag}_launch_min")
        if capacity != SETTINGS[f"boat_{tag}_capacity"] or minutes != SETTINGS[f"boat_{tag}_launch_min"]:
            raise InterfaceError("boat CSV disagrees with parameter record")
        if row["from_record"] not in ("true", "false"):
            raise InterfaceError("boat record flag must be true or false")
        boats.append(Boat(row["name"], capacity, minutes, row["from_record"] == "true"))
    return tuple(boats)


def make_ship(length_m, beam_m, draught_m, displacement_t, compartments, bulkhead_top_m, boat_deck_m) -> ShipSpec:
    count = _integer(compartments, "compartment_count")
    length = _value(length_m, "length")
    return ShipSpec(
        "Box ship",
        length,
        _value(beam_m, "beam"),
        _value(draught_m, "draught"),
        _value(displacement_t, "displacement"),
        _value(boat_deck_m, "boat_deck"),
        tuple(Compartment(str(i), length / count, bulkhead_top_m) for i in range(count)),
    )


def even_breach(ship, first, count, area_m2) -> Breach:
    first = _integer(first, "boat_capacity")
    count = _integer(count, "compartment_count")
    area = _value(area_m2, "breach_area")
    if first + count > len(ship.compartments):
        raise InterfaceError("breach interval outside compartments")
    return Breach(tuple(area / count if first <= i < first + count else 0.0 for i in range(len(ship.compartments))))


def inflow_m3_s(area_m2, head_m) -> float:
    area = _value(area_m2, "breach_area")
    try:
        head = float(head_m)
    except (ValueError, TypeError, OverflowError) as error:
        raise InterfaceError("head must be finite") from error
    if not isfinite(head):
        raise InterfaceError("head must be finite")
    return SETTINGS["discharge_coefficient"] * area * sqrt(2.0 * SETTINGS["gravity"] * head) if head > 0 else 0.0


def _geometry(ship):
    lengths = np.array([c.length_m for c in ship.compartments])
    edges = np.r_[0.0, lengths.cumsum()] - ship.length_m / 2.0
    centres = (edges[:-1] + edges[1:]) / 2.0
    storage = lengths * ship.beam_m * SETTINGS["permeability"]
    return edges, centres, storage


def _attitude(ship, volumes, centres):
    water_t = volumes * SETTINGS["water_density"] / KG_PER_TONNE
    sink = volumes.sum() / (ship.length_m * ship.beam_m)
    displaced_t = ship.displacement_t + water_t.sum()
    gml = ship.length_m**2 / (12.0 * ship.draught_m)
    # Dry displacement may be zero; an empty hull has no flood moment.
    slope = float(water_t @ centres) / (displaced_t * gml) if displaced_t > 0 else 0.0
    return float(sink), slope


def _overflow(ship, volumes, edges, centres, storage):
    """Redistribute reservoirs directly, with attitude held during the spill."""
    if len(volumes) < 2:
        return
    sink, slope = _attitude(ship, volumes, centres)
    offsets = -SETTINGS["hole_depth_below_waterline"] - sink - slope * centres
    crests = np.array([c.top_above_waterline_m for c in ship.compartments[:-1]]) - sink - slope * edges[1:-1]
    _spill_reservoirs(volumes, storage, offsets, crests)


def _spill_reservoirs(volumes, storage, offsets, crests):
    levels = offsets + volumes / storage
    high = np.maximum(levels[:-1], levels[1:])
    low = np.minimum(levels[:-1], levels[1:])
    if not np.any((high > crests) & (high > low)):
        return
    # An emerged storage floor is also a barrier. Split at the highest barrier;
    # each child can hold a common surface up to its parent's spill elevation.
    barriers = np.maximum(crests, np.maximum(offsets[:-1], offsets[1:]))
    pending = [(0, len(volumes))]
    while pending:
        start, end = pending.pop()
        if end - start < 2:
            continue
        split = start + int(np.argmax(barriers[start : end - 1])) + 1
        crest = barriers[split - 1]
        sl = slice(start, end)
        capacity = storage[sl] * (crest - offsets[sl])
        total = float(volumes[sl].sum())
        surplus = total - float(capacity.sum())
        if surplus >= 0:
            volumes[sl] = capacity + storage[sl] * (surplus / storage[sl].sum())
            continue
        left, right = slice(start, split), slice(split, end)
        left_excess = float(volumes[left].sum() - capacity[: split - start].sum())
        right_excess = float(volumes[right].sum() - capacity[split - start :].sum())
        if left_excess > 0:
            volumes[left] = capacity[: split - start]
            volumes[split] += left_excess
        elif right_excess > 0:
            volumes[right] = capacity[split - start :]
            volumes[split - 1] += right_excess
        pending.extend(((start, split), (split, end)))


def _is_foundered(ship, volumes, centres):
    sink, slope = _attitude(ship, volumes, centres)
    bow_immersion = sink - slope * ship.length_m / 2.0
    full_box_t = SETTINGS["water_density"] * ship.length_m * ship.beam_m * (ship.draught_m + ship.boat_deck_above_waterline_m) / KG_PER_TONNE
    return bow_immersion >= ship.boat_deck_above_waterline_m or ship.displacement_t + volumes.sum() * SETTINGS["water_density"] / KG_PER_TONNE >= full_box_t


def flood(ship, breach, t_end_s, dt_s=10.0) -> FloodResult:
    end = _value(t_end_s, "duration")
    step = _value(dt_s, "output_step")
    times = np.arange(int(end // step) + 1, dtype=float) * step
    if times[-1] < end:
        times = np.r_[times, end]
    return _solve(ship, breach, times)


def _solve(ship, breach, times):
    if len(breach.areas_m2) != len(ship.compartments):
        raise InterfaceError("one breach area per compartment required")
    edges, centres, storage = _geometry(ship)
    areas = np.array(breach.areas_m2, dtype=float)
    water = np.zeros((len(times), len(storage)))
    bow, stern = np.zeros(len(times)), np.zeros(len(times))
    volumes = np.zeros(len(storage))
    foundered = 0.0 if _is_foundered(ship, volumes, centres) else None
    clock = 0.0
    for k, target in enumerate(times):
        while clock < target:
            h = min(SETTINGS["integration_step"], target - clock)
            sink, slope = _attitude(ship, volumes, centres)
            initial = _ingress(volumes, storage, areas, sink + slope * centres, h)
            mid_sink, mid_slope = _attitude(ship, volumes + initial / 2.0, centres)
            volumes += _ingress(volumes, storage, areas, mid_sink + mid_slope * centres, h)
            _overflow(ship, volumes, edges, centres, storage)
            clock = target if h == target - clock else clock + h
            if foundered is None and _is_foundered(ship, volumes, centres):
                foundered = float(clock)
        water[k] = volumes * SETTINGS["water_density"] / KG_PER_TONNE
        sink, slope = _attitude(ship, volumes, centres)
        bow[k] = ship.draught_m + sink - slope * ship.length_m / 2.0
        stern[k] = ship.draught_m + sink + slope * ship.length_m / 2.0
    return FloodResult(times, water, bow, stern, foundered)


def _ingress(volumes, storage, areas, exterior, duration):
    # Exact orifice update for a held exterior. Predicting its midpoint above
    # accounts for hydrostatic feedback without Euler overshoot at equilibrium.
    head = SETTINGS["hole_depth_below_waterline"] + exterior - volumes / storage
    root = np.sqrt(np.maximum(head, 0.0))
    decrease = SETTINGS["discharge_coefficient"] * areas * sqrt(2.0 * SETTINGS["gravity"]) * duration / (2.0 * storage)
    consumed = np.minimum(decrease, root)
    return storage * consumed * (2.0 * root - consumed)


def _axis(time):
    if not isinstance(time.n, int) or time.n < 1 or not isfinite(time.dt_s) or time.dt_s <= 0:
        raise InterfaceError("positive finite time axis required")


def _grid(grid):
    if not all(isfinite(v) for v in (grid.x0_m, grid.y0_m, grid.dx_m)) or grid.dx_m <= 0 or grid.nx < 1 or grid.ny < 1:
        raise InterfaceError("positive finite grid required")


def _deck(grid, ship):
    _grid(grid)
    x = (np.arange(grid.nx) + 0.5 - grid.nx / 2.0) * grid.dx_m
    y = (grid.ny / 2.0 - np.arange(grid.ny) - 0.5) * grid.dx_m
    return (abs(y[:, None]) <= ship.beam_m / 2.0) & (abs(x[None, :]) <= ship.length_m / 2.0), x


class Ship:
    id, tier = "ship", "T1"
    inputs = ()
    outputs = tuple(field_spec("ship." + name) for name in ("water_mass", "afloat", "impact", "alarm", "submerged"))
    parameters = PARAMETERS

    def __init__(self, grid, time, spec, breach, impact_s, alarm_s, recorded_sinking=None):
        _axis(time)
        _grid(grid)
        if len(breach.areas_m2) != len(spec.compartments):
            raise InterfaceError("one breach area per compartment required")
        self.grid, self.time, self.spec, self.breach = grid, time, spec, breach
        self.impact_s = _value(impact_s, "event_time")
        self.alarm_s = _value(alarm_s, "event_time")
        self.recorded_sinking = None
        if recorded_sinking is not None:
            try:
                awash, foundered = recorded_sinking
            except (ValueError, TypeError) as error:
                raise InterfaceError("recorded sinking needs bow-awash and foundered times") from error
            awash, foundered = (_value(awash, "event_time"), _value(foundered, "event_time"))
            if foundered <= awash:
                raise InterfaceError("recorded foundering must be after bow awash")
            self.recorded_sinking = awash, foundered

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        time, ship = self.time, self.spec
        frame_times = np.arange(time.n) * time.dt_s
        deck, x = _deck(self.grid, ship)
        water, afloat, impact = np.zeros(time.n), np.ones(time.n), np.zeros(time.n)
        submerged = np.zeros((time.n, self.grid.ny, self.grid.nx))
        active = np.flatnonzero(frame_times >= self.impact_s)
        if len(active):
            impact[active[0]] = 1.0
            # Align every requested state to its own elapsed collision time.
            # Off-grid impact offsets are integrated before the first frame.
            elapsed = frame_times[active] - self.impact_s
            result = _flood_at_times(ship, self.breach, elapsed)
            for j, k in enumerate(active):
                water[k] = result.water_t[j].sum() * KG_PER_TONNE
                lost = result.foundered_s is not None and elapsed[j] >= result.foundered_s
                afloat[k] = float(not lost)
                if lost:
                    submerged[k] = 1.0
                else:
                    bow = result.draught_bow_m[j] - ship.draught_m
                    stern = result.draught_stern_m[j] - ship.draught_m
                    local = (bow + stern) / 2.0 + (stern - bow) * x / ship.length_m
                    submerged[k] = deck & (local[None, :] >= ship.boat_deck_above_waterline_m)
        if self.recorded_sinking is not None:
            awash, foundered = self.recorded_sinking
            afloat = (frame_times < foundered).astype(float)
            submerged.fill(0.0)
            # Simplified replay: a front advances linearly from west to east.
            for k in np.flatnonzero((frame_times >= awash) & (frame_times < foundered)):
                fraction = (frame_times[k] - awash) / (foundered - awash)
                submerged[k] = deck & (x[None, :] <= ship.length_m * (fraction - 0.5))
            submerged[frame_times >= foundered] = 1.0
        alarm = (frame_times >= self.alarm_s).astype(float)
        for name, values in (("water_mass", water), ("afloat", afloat), ("impact", impact), ("alarm", alarm)):
            fields.put("ship." + name, values, field_spec("ship." + name).unit, time=time)
        fields.put("ship.submerged", submerged, "dimensionless", self.grid, time)
        return {}


def _flood_at_times(ship, breach, times):
    # Integrate exactly to each frame's collision-relative time. The initial
    # integration interval may be shorter when impact is between frames.
    _value(times[-1], "duration")
    return _solve(ship, breach, np.asarray(times))


class ShipDeck:
    id, tier = "terrain", "T1"
    inputs = ()
    outputs = tuple(field_spec("terrain." + name) for name in ("elevation", "land_mask", "land_cover", "zone", "flow_accumulation", "height_above_drainage"))
    parameters = PARAMETERS

    def __init__(self, grid, spec):
        _grid(grid)
        self.grid, self.spec = grid, spec

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        deck, _ = _deck(self.grid, self.spec)
        zero = np.zeros(deck.shape)
        for output in self.outputs:
            data = deck * SETTINGS["deck_elevation"] if output.name == "terrain.elevation" else deck if output.name == "terrain.land_mask" else zero
            fields.put(output.name, data, output.unit, self.grid)
        return {}


class Boats:
    id, tier = "boats", "T1"
    inputs = ()
    outputs = (field_spec("boats.capacity"), field_spec("boats.launch"))
    parameters = PARAMETERS

    def __init__(self, grid, stations):
        _grid(grid)
        self.grid = grid
        self.stations = []
        for xy, capacity, launch_s in stations:
            if len(xy) != 2 or not all(isfinite(v) for v in xy) or grid.locate(xy) is None:
                raise InterfaceError("boat station must be a finite point inside grid")
            self.stations.append((tuple(xy), _integer(capacity, "boat_capacity"), _value(launch_s, "event_time")))

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        capacity = np.zeros((self.grid.ny, self.grid.nx))
        launch = np.full(capacity.shape, np.inf)
        for xy, seats, event in self.stations:
            cell = self.grid.locate(xy)
            capacity[cell] += seats
            launch[cell] = min(launch[cell], event)
        fields.put("boats.capacity", capacity, "dimensionless", self.grid)
        fields.put("boats.launch", launch, "s", self.grid)
        return {}

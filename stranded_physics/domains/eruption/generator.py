"""Catalogue sampling and explicit, uncalibrated eruption timing."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from math import fsum

import numpy as np

from stranded_physics.core.api import InterfaceError
from .model import HERE, PARAMETERS, SETTINGS, mastin_mass_rate_kg_s

CATALOG = HERE.parents[2] / "disaster_data/catalog"
BOUNDS = {p.id.split(".", 1)[1]: tuple(float(q.magnitude) for q in p.valid) for p in PARAMETERS}
SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class Event:
    start_s: float
    height_m: float
    duration_s: float


@dataclass(frozen=True)
class GeneratedEruption:
    size: int
    onset_s: float
    lead_s: float
    events: tuple[Event, ...]
    total_mass_kg: float


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


@lru_cache(maxsize=None)
def size_catalog(before_year):
    cutoff = checked("size_before_year", before_year)
    if cutoff != int(cutoff):
        raise InterfaceError("before_year must be an integer")
    values = []
    with (CATALOG / "eruptions.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            # Check the split before inspecting the size.
            if not row["start_year"].strip() or float(row["start_year"]) >= cutoff:
                continue
            if row["vei"].strip():
                size = checked("generated_size", row["vei"])
                if size != int(size):
                    raise InterfaceError("catalogue VEI must be an integer")
                values.append(int(size))
    if not values:
        raise InterfaceError("no recorded sizes before the requested year")
    return tuple(values)


def sample_size(rng, before_year=2000) -> int:
    values = size_catalog(before_year)
    return int(values[rng.integers(len(values))])


@lru_cache(maxsize=1)
def lead_catalog():
    with (CATALOG / "precursor_lead_times.csv").open(encoding="utf-8-sig", newline="") as stream:
        values = tuple(checked("generated_lead_s", float(row["lead_hours"]) * SECONDS_PER_HOUR) for row in csv.DictReader(stream) if row["lead_hours"].strip())
    if not values:
        raise InterfaceError("no recorded precursor lead times")
    return values


def sample_lead_s(rng) -> float:
    return float(rng.choice(lead_catalog()))


def generate(rng, axis_seconds, size=None, lead_s=None, onset_s=None, column_m=None) -> GeneratedEruption:
    end = axis_end(axis_seconds)
    size = sample_size(rng) if size is None else checked("generated_size", size)
    if size != int(size):
        raise InterfaceError("size must be an integer")
    size = int(size)
    lead = sample_lead_s(rng) if lead_s is None else checked("generated_lead_s", lead_s)
    if onset_s is None:
        low = max(SETTINGS["onset_fraction_min"] * end, lead)
        high = SETTINGS["onset_fraction_max"] * end
        if low > high:
            raise InterfaceError("warning does not fit before onset in the middle half of the axis")
        onset = float(rng.uniform(low, high))
    else:
        onset = checked("generated_onset_s", onset_s)
    if onset < lead or onset > end:
        raise InterfaceError("onset must lie on the axis and warning cannot precede its start")
    height = (
        float(rng.uniform(SETTINGS[f"size_{size}_height_min"], SETTINGS[f"size_{size}_height_max"]))
        if column_m is None
        else checked("generated_column_m", column_m)
    )
    volume = float(np.exp(rng.uniform(np.log(SETTINGS[f"size_{size}_volume_min"]), np.log(SETTINGS[f"size_{size}_volume_max"]))))
    mass = volume * SETTINGS["bulk_density"]
    rate = mastin_mass_rate_kg_s(height)
    active_s = mass / rate
    events, emitted, start = [], 0.0, onset
    while emitted < mass:
        duration = active_s * rng.uniform(SETTINGS["pulse_fraction_min"], SETTINGS["pulse_fraction_max"])
        remaining = mass - emitted
        last = rate * duration >= remaining
        if last:
            duration = remaining / rate
        events.append(Event(float(start), height, float(duration)))
        if last:
            break
        emitted = fsum(rate * event.duration_s for event in events)
        start += duration + rng.uniform(SETTINGS["gap_min_s"], SETTINGS["gap_max_s"])
    return GeneratedEruption(size, onset, lead, tuple(events), mass)


def from_dials(rng, axis_seconds, size=None, lead_s=None, onset_s=None, column_m=None) -> GeneratedEruption:
    """As `generate`, for a scenario that has to run. An unset warning is drawn only from catalogue warnings that fit its axis,
    so a 312-hour case can't make a 96-hour scenario impossible on some seeds. A warning set by hand is never changed."""
    end = axis_end(axis_seconds)
    if lead_s is None:
        latest = SETTINGS["onset_fraction_max"] * end if onset_s is None else onset_s
        fitting = [lead for lead in lead_catalog() if lead <= latest]
        if not fitting:
            raise InterfaceError(f"no catalogue warning fits before {latest / SECONDS_PER_HOUR:g} hours")
        lead_s = float(rng.choice(fitting))
    return generate(rng, end, size=size, lead_s=lead_s, onset_s=onset_s, column_m=column_m)


def validate_generated(generated):
    size = checked("generated_size", generated.size)
    if size != int(size):
        raise InterfaceError("size must be an integer")
    checked("generated_onset_s", generated.onset_s)
    checked("generated_lead_s", generated.lead_s)
    if generated.onset_s < generated.lead_s or not generated.events:
        raise InterfaceError("generated eruption needs events and a warning starting on the axis")
    if generated.events[0].start_s != generated.onset_s:
        raise InterfaceError("onset must equal the first event start")
    previous_end = generated.onset_s
    for event in generated.events:
        checked("generated_column_m", event.height_m)
        if not np.isfinite([event.start_s, event.duration_s]).all() or event.start_s < previous_end or event.duration_s <= 0:
            raise InterfaceError("generated events must be finite, positive and nonoverlapping")
        previous_end = event.start_s + event.duration_s
    actual = fsum(mastin_mass_rate_kg_s(e.height_m) * e.duration_s for e in generated.events)
    if (
        not np.isfinite(generated.total_mass_kg)
        or generated.total_mass_kg <= 0
        or not np.isclose(actual, generated.total_mass_kg, rtol=SETTINGS["mass_relative_tolerance"], atol=0)
    ):
        raise InterfaceError("generated event mass does not match total_mass_kg")

"""Standalone storm diagnostics, without imports from other categories."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import ks_2samp

from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from .model import HERE, METRES_PER_KM, SECONDS_PER_HOUR, SETTINGS, Storm


def wind_holdout():
    from .generator import CATALOG, KNOTS_TO_MS, sample_max_wind_m_s

    rng = np.random.default_rng(int(SETTINGS["generator_measure_seed"]))
    samples = [sample_max_wind_m_s(rng, before_season=2005) for _ in range(int(SETTINGS["wind_sample_count"]))]
    with CATALOG.open(encoding="utf-8-sig", newline="") as stream:
        held = [
            float(row["max_wind_kt"]) * KNOTS_TO_MS
            for row in csv.DictReader(stream)
            if row["season"].strip() and float(row["season"]) >= SETTINGS["wind_before_season"] and row["max_wind_kt"].strip()
        ]
    if not held:
        raise InterfaceError("no holdout storm winds")
    return {"value": float(ks_2samp(samples, held).statistic)}


def cyclone_rate(path=None):
    path = HERE.parents[2] / "disaster_data/catalog/cyclones_near_study_islands.csv" if path is None else Path(path)
    first, last = int(SETTINGS["catalog_first_year"]), int(SETTINGS["catalog_last_year"])
    radius = SETTINGS["catalog_radius_km"]
    storms = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"island", "sid", "season", "name", "closest_km"} <= set(reader.fieldnames or ()):
            raise InterfaceError("catalog cannot supply named storm counts with season and distance")
        for row in reader:
            if row["island"] != "st_vincent":
                continue
            name = row["name"].strip().upper()
            if first <= int(row["season"]) <= last and float(row["closest_km"]) <= radius and name not in ("", "UNNAMED", "NOT_NAMED", "NONAME"):
                storms.add(row["sid"])
    return {"storms_per_year": len(storms) / (last - first + 1), "first_year": first, "last_year": last, "radius_km": radius, "named_storms": len(storms)}


def beryl_peak():
    axis = TimeAxis(datetime.fromtimestamp(SETTINGS["peak_axis_epoch"], timezone.utc), SECONDS_PER_HOUR, int(SETTINGS["peak_axis_frames"]))
    model = Storm(axis, (SETTINGS["kingstown_lon"], SETTINGS["kingstown_lat"]))
    store = FieldStore()
    model.run(ScopedFields(store, model.id, model.inputs, model.outputs), np.random.default_rng(int(SETTINGS["validation_seed"])))
    winds = store.get("storm.max_wind", "m/s")
    k = int(np.argmax(winds))
    return {
        "peak_m_s": float(winds[k]),
        "time_utc": (axis.t0_utc + timedelta(seconds=k * axis.dt_s)).isoformat().replace("+00:00", "Z"),
        "closest_km": float(model.distance_m.min() / METRES_PER_KM),
    }


def main(argv):
    if len(argv) != 1 or argv[0] not in ("beryl_peak", "cyclone_rate", "wind_holdout"):
        return 2
    try:
        measure = {"beryl_peak": beryl_peak, "cyclone_rate": cyclone_rate, "wind_holdout": wind_holdout}
        print(json.dumps(measure[argv[0]]()))
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Log-log height versus mass-rate exponent of the implemented Mastin relation."""

import csv
import json
import sys

import numpy as np
from scipy.optimize import brentq

from datetime import datetime, timezone

from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from .model import Eruption, SETTINGS, mastin_mass_rate_kg_s


def generator_measure(name):
    from .generator import BOUNDS, CATALOG, generate, lead_catalog, sample_lead_s, sample_size

    rng = np.random.default_rng(int(SETTINGS["generator_measure_seed"]))
    if name == "size_holdout":
        samples = np.array([sample_size(rng, before_year=2000) for _ in range(int(SETTINGS["size_sample_count"]))])
        with (CATALOG / "eruptions.csv").open(encoding="utf-8-sig", newline="") as stream:
            held = [
                int(row["vei"])
                for row in csv.DictReader(stream)
                if row["start_year"].strip() and float(row["start_year"]) >= SETTINGS["size_before_year"] and row["vei"].strip()
            ]
        if not held:
            raise ValueError("no holdout eruption sizes")
        size_count = int(BOUNDS["generated_size"][1]) + 1
        empirical = np.bincount(samples, minlength=size_count) / len(samples)
        observed = np.bincount(held, minlength=size_count) / len(held)
        return {"value": float(np.abs(empirical - observed).sum() / 2)}
    if name == "lead_time_distribution":
        samples = np.sort([sample_lead_s(rng) for _ in range(int(SETTINGS["lead_sample_count"]))])
        catalogue = np.sort(lead_catalog())
        sampled = np.searchsorted(samples, catalogue, side="right") / len(samples)
        recorded = np.searchsorted(catalogue, catalogue, side="right") / len(catalogue)
        return {"value": float(np.abs(sampled - recorded).max()), "sample_count": len(samples), "catalogue_count": len(catalogue)}
    if name == "lead_time_ratio":
        samples = [sample_lead_s(rng) for _ in range(int(SETTINGS["lead_sample_count"]))]
        sample_median = float(np.median(samples))
        catalogue = lead_catalog()
        catalogue_median = float(np.median(catalogue))
        return {
            "value": sample_median / catalogue_median,
            "sample_median_s": sample_median,
            "catalogue_median_s": catalogue_median,
            "sample_count": len(samples),
            "catalogue_count": len(catalogue),
        }
    masses = [
        generate(rng, SETTINGS["generator_measure_axis_s"], size=int(SETTINGS["mass_sample_size"])).total_mass_kg
        for _ in range(int(SETTINGS["mass_sample_count"]))
    ]
    return {"value": float(np.log10(np.median(masses)))}


def main(argv):
    if len(argv) == 1 and argv[0] in ("size_holdout", "lead_time_ratio", "lead_time_distribution", "size_4_log_mass"):
        print(json.dumps(generator_measure(argv[0])))
        return 0
    if argv == ["total_mass"]:
        start = datetime.fromtimestamp(SETTINGS["mass_axis_start_epoch"], timezone.utc)
        end = datetime.fromtimestamp(SETTINGS["mass_axis_end_epoch"], timezone.utc)
        frames = int(SETTINGS["mass_axis_frames"])
        axis = TimeAxis(start, (end - start).total_seconds() / (frames - 1), frames)
        model, store = Eruption(axis), FieldStore()
        model.run(ScopedFields(store, model.id, model.inputs, model.outputs), np.random.default_rng(1))
        print(
            json.dumps(
                {
                    "model_kg": float(store.get("eruption.mass_rate", "kg/s").sum() * axis.dt_s),
                    "cole_whole_eruption_kg": SETTINGS["cole_whole_eruption_kg"],
                    "axis_end_utc": end.strftime("%Y-%m-%dT%H:%MZ"),
                }
            )
        )
        return 0
    if argv != ["mastin_slope"]:
        return 2
    rates = np.array([1e6, 1e8])
    heights = [brentq(lambda h, target=rate: mastin_mass_rate_kg_s(h) - target, 0.0, 100000.0) for rate in rates]
    print(json.dumps({"value": float(np.log(heights[1] / heights[0]) / np.log(rates[1] / rates[0]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

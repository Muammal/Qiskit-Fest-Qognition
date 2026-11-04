"""Log-log height versus mass-rate exponent of the implemented Mastin relation."""
import json
import sys

import numpy as np
from scipy.optimize import brentq

from datetime import datetime, timezone

from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from .model import Eruption, SETTINGS, mastin_mass_rate_kg_s


def main(argv):
    if argv == ["total_mass"]:
        start = datetime.fromtimestamp(SETTINGS["mass_axis_start_epoch"], timezone.utc)
        end = datetime.fromtimestamp(SETTINGS["mass_axis_end_epoch"], timezone.utc)
        frames = int(SETTINGS["mass_axis_frames"])
        axis = TimeAxis(start, (end - start).total_seconds() / (frames - 1), frames)
        model, store = Eruption(axis), FieldStore()
        model.run(ScopedFields(store, model.id, model.inputs, model.outputs), np.random.default_rng(1))
        print(json.dumps({"model_kg": float(store.get("eruption.mass_rate", "kg/s").sum() * axis.dt_s),
                          "cole_whole_eruption_kg": SETTINGS["cole_whole_eruption_kg"],
                          "axis_end_utc": end.strftime("%Y-%m-%dT%H:%MZ")}))
        return 0
    if argv != ["mastin_slope"]:
        return 2
    rates = np.array([1e6, 1e8])
    heights = [brentq(lambda h: mastin_mass_rate_kg_s(h) - rate, 0., 100000.) for rate in rates]
    print(json.dumps({"value": float(np.log(heights[1] / heights[0]) / np.log(rates[1] / rates[0]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

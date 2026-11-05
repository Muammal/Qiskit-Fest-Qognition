import json
import sys
from datetime import datetime, timezone
import numpy as np
from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
# Measurement glue is the task-authorized exception to category independence.
from ..eruption.model import Eruption
from .model import SETTINGS, so2_rate_kg_s

KG_PER_KILOTONNE = 1e6


def main():
    if sys.argv[1:] != ["total_so2_kt"]:
        return 2
    step = SETTINGS["measure_step"]
    frames = int((SETTINGS["measure_axis_end"]-SETTINGS["measure_axis_start"])/step)+1
    axis = TimeAxis(datetime.fromtimestamp(SETTINGS["measure_axis_start"], timezone.utc), step, frames)
    eruption, store = Eruption(axis), FieldStore()
    eruption.run(ScopedFields(store, eruption.id, eruption.inputs, eruption.outputs), np.random.default_rng(int(SETTINGS["measure_seed"])))
    phase = store.get("eruption.phase", "dimensionless")
    mass = store.get("eruption.mass_rate", "kg/s")
    # Eruption mass rates average the preceding interval; phase at the left edge controls passive gas.
    passive = so2_rate_kg_s(phase[:-1], np.zeros(axis.n-1))
    eruptive = so2_rate_kg_s(phase[1:], mass[1:]) - so2_rate_kg_s(phase[1:], np.zeros(axis.n-1))
    print(json.dumps({"value": float((passive+eruptive).sum()*axis.dt_s/KG_PER_KILOTONNE)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

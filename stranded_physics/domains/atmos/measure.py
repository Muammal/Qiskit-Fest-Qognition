"""Read the requested upper-wind replay anchor."""

import json
import sys
from datetime import datetime, timezone

import numpy as np

from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from .model import Atmos


def main(argv):
    names = {"wind_200hpa_speed": "atmos.wind_speed_200hpa", "wind_200hpa_bearing": "atmos.wind_bearing_200hpa"}
    if len(argv) != 1 or argv[0] not in names:
        return 2
    domain = Atmos(TimeAxis(datetime(2021, 4, 9, 12, tzinfo=timezone.utc), 3600.0, 1))
    store = FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(1))
    field = store.stored(names[argv[0]])
    print(json.dumps({"value": float(field.data[0])}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

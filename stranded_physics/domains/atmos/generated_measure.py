"""Compare sampled outputs with independent raw-file indexing."""

import json
from datetime import datetime, timedelta, timezone
import numpy as np
from stranded_physics.core.api import TimeAxis
from stranded_physics.core.fields import FieldStore, ScopedFields
from .generator import WeatherWindow, ISLANDS, P
from .model import COLUMNS


def window_difference():
    worst = 0.0
    for island in ISLANDS:
        for seed in range(int(P["samples"].value.magnitude)):
            axis = TimeAxis(datetime(2000, 1, 1, tzinfo=timezone.utc), 10800.0, 17)
            model = WeatherWindow(axis, island)
            store = FieldStore()
            model.run(ScopedFields(store, model.id, model.inputs, model.outputs), np.random.default_rng(seed))
            raw = {role: json.loads(path.read_text(encoding="utf-8"))["hourly"] for role, (path, _) in model.files.items()}
            indices = {role: {t: i for i, t in enumerate(data["time"])} for role, data in raw.items()}
            for name, (role, column) in COLUMNS.items():
                expected = []
                for k in range(axis.n):
                    moment = model.window_start_utc + timedelta(seconds=k * axis.dt_s)
                    hours = int(axis.dt_s / 3600) if name == "rain_rate" and k else 1
                    value = sum(raw[role][column][indices[role][(moment - timedelta(hours=j)).strftime("%Y-%m-%dT%H:%M")]] for j in range(hours)) / hours
                    if name.startswith("wind_speed"):
                        value /= 3.6
                    if name.startswith("wind_bearing"):
                        value = (value + 180) % 360
                    expected.append(value)
                worst = max(
                    worst, float(np.max(np.abs(store.get("atmos." + name, next(o.unit for o in model.outputs if o.name == "atmos." + name)) - expected)))
                )
    return worst


if __name__ == "__main__":
    print(json.dumps({"value": window_difference()}))

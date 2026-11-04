"""Reproducible St Vincent ash measurements on the shared scenario axis."""
from __future__ import annotations

import json
import sys

import numpy as np

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.atmos.model import Atmos
from stranded_physics.domains.eruption.model import Eruption
from stranded_physics.domains.tephra.model import SETTINGS, Tephra
from stranded_physics.domains.terrain.model import ST_VINCENT_GRID, default_files, read_land_mask
from stranded_physics.packs.builder import dependency_order
from stranded_physics.st_vincent import BARBADOS_XY, TIME, VENT_XY


def build():
    store = FieldStore()
    ash = Tephra(ST_VINCENT_GRID, TIME, VENT_XY)
    residual = None
    for domain in dependency_order((ash, Eruption(TIME), Atmos(TIME))):
        fields = ScopedFields(store, domain.id, domain.inputs, domain.outputs)
        reasons = domain.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        result = domain.run(fields, np.random.default_rng(int(SETTINGS["validation_seed"])))
        if domain.id == ash.id:
            residual = result["mass_kg"]
    return store, ash, residual


def main(argv):
    if len(argv) != 1 or argv[0] not in ("barbados_first_ash_h", "island_cover", "mass_balance"):
        return 2
    try:
        land = None
        if argv[0] == "island_cover":
            path = default_files()["dem"][0]
            if not path.exists():
                print(f"Missing terrain file: {path}", file=sys.stderr)
                return 1
            land = read_land_mask(path, ST_VINCENT_GRID) > 0
            if not land.any():
                raise InterfaceError("terrain has no St Vincent land cells")
        store, ash, residual = build()
        if argv[0] == "mass_balance":
            value = abs(residual)
        elif argv[0] == "island_cover":
            final = store.get("tephra.deposit_load", "kg/m**2")[-1]
            value = float(np.mean(final[land] >= SETTINGS["island_threshold"]))
        else:
            value = next((k * TIME.dt_s / 3600 for k in range(TIME.n)
                          if ash.load_at(BARBADOS_XY, k * TIME.dt_s) >= SETTINGS["barbados_threshold"]), None)
            if value is None:
                return 0
        print(json.dumps({"value": value}))
    except (InterfaceError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

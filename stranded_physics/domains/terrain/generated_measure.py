"""Fixed-seed worst-case geometry and drainage checks."""
import json
import sys
import numpy as np
from stranded_physics.core.fields import FieldStore, ScopedFields
from .generator import GeneratedTerrain, sample_island, S
from .model import ST_VINCENT_GRID
from .drainage import route, share_draining_out


def measure():
    results = dict(drains=1.,area_error=0.,summit_error=0.)
    for seed in range(int(S["samples"])):
        rng = np.random.default_rng(seed)
        summit,area = sample_island(rng)
        model = GeneratedTerrain(ST_VINCENT_GRID,(S["measure_x"],S["measure_y"]),summit,area)
        store = FieldStore()
        model.run(ScopedFields(store,model.id,model.inputs,model.outputs),rng)
        land = store.get("terrain.land_mask","dimensionless")>0
        elevation = store.get("terrain.elevation","m")
        results["drains"] = min(results["drains"],share_draining_out(route(elevation,land,ST_VINCENT_GRID.dx_m),land))
        results["area_error"] = max(results["area_error"],abs(land.sum()*ST_VINCENT_GRID.dx_m**2/1e6/area-1))
        results["summit_error"] = max(results["summit_error"],abs(elevation.max()/summit-1))
    return results

if __name__ == "__main__":
    print(json.dumps({"value":measure()[sys.argv[1]]}))

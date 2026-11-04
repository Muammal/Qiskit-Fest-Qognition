"""The whole path on the real scenario: the pack builds, both minds play it, and neither can see the future.

    python -m stranded_physics.validation.st_vincent_end_to_end             exits nonzero on any broken rule
    python -m stranded_physics.validation.st_vincent_end_to_end route_hours walking time on real terrain
"""
from __future__ import annotations

import json
import sys

import numpy as np

import contracts
from stranded_physics.domains.agent.walking import travel_field
from stranded_physics.domains.terrain.model import ST_VINCENT_GRID as GRID
from stranded_physics.packs.builder import Pack
from stranded_physics.packs.st_vincent_2021 import build, sites
from stranded_physics.runtime.body import NEED_KEYS, STATE_KEYS
from stranded_physics.runtime.simulation import PackSimulation

CUT_FRAME = 24
BLANKED = ("pdc.active", "tephra.deposit_load", "lahar.depth", "eruption.explosion", "eruption.phase", "eruption.mass_rate", "atmos.rain_rate")


def future_blanked(pack: Pack) -> Pack:
    """The same pack with everything after CUT_FRAME wiped, to prove that nothing earlier depends on it."""
    arrays = {name: np.array(values) for name, values in pack._arrays.items()}
    for name in BLANKED:
        if name in arrays:
            arrays[name][CUT_FRAME + 1:] = 0.
    arrays["pdc.arrival"] = np.where(arrays["pdc.arrival"] > CUT_FRAME * pack.time.dt_s, np.inf, arrays["pdc.arrival"])
    return Pack(pack.header, arrays)


def route_hours() -> float:
    placed = sites()
    from stranded_physics.domains.terrain.model import read_elevation, read_land_mask, default_files
    dem = default_files()["dem"][0]
    elevation, land = read_elevation(dem, GRID), read_land_mask(dem, GRID) > 0
    field = travel_field(elevation, land, GRID.locate(placed["assembly"][0]), GRID.dx_m)
    return float(field.seconds[GRID.locate(placed["spawn"][0])] / 3600.)


def check() -> dict:
    results: dict[str, bool] = {}
    pack = build(1)
    results["same_seed_same_hash"] = build(1).content_hash == pack.content_hash
    other = build(2)
    moved = [n for n in pack.header["fields"] if not np.array_equal(pack._arrays[n], other._arrays[n])]
    results["seed_only_moves_noticed_signs"] = set(moved) <= {"eruption.tremor", "eruption.gas"}
    results["no_model_out_of_domain"] = not [k for k, v in pack.verdicts.items() if v == "OUT_OF_DOMAIN"]
    results["all_real_categories"] = {row["id"]: row["tier"] for row in pack.header["domains"]} == {k: "T1" for k in ("terrain", "atmos", "eruption", "tephra", "pdc", "lahar")}
    outcomes = {}
    for mind in ("quantum", "classical"):
        simulation = PackSimulation(pack, mind_type=mind)
        timeline = simulation.run()
        outcomes[mind] = {"outcome": timeline["outcome"], "cause": timeline["cause"], "steps": len(timeline["steps"]),
                          "events": sorted({s["event"] for s in timeline["steps"]}), "final_tile": timeline["steps"][-1]["pos_after"]}
        results[f"{mind}_state_keys_exact"] = all(set(s["state"]) == STATE_KEYS and set(s["state"]["needs"]) == NEED_KEYS for s in timeline["steps"])
        contracts.validate_state(timeline["steps"][0]["state"])
        results[f"{mind}_in_tile_range"] = all(0 <= v < 40 for s in timeline["steps"] for v in s["pos_after"])
        wiped = PackSimulation(future_blanked(pack), mind_type=mind)
        for _ in range(CUT_FRAME + 1):
            wiped.step()
        results[f"{mind}_no_future_leak"] = [s["state"] for s in wiped.steps[:CUT_FRAME + 1]] == [s["state"] for s in timeline["steps"][:CUT_FRAME + 1]]
    return {"results": results, "outcomes": outcomes, "hash": pack.content_hash, "budgets": pack.header["budgets"]}


def main(argv: list[str]) -> int:
    if argv == ["route_hours"]:
        print(json.dumps({"value": route_hours()}))
        return 0
    report = check()
    print(json.dumps(report, indent=1))
    print(json.dumps({"failed": [k for k, v in report["results"].items() if not v]}))
    return 0 if all(report["results"].values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

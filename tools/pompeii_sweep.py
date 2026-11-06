"""Pompeii sweep: four event mappings x three minds x ten seeds.

Reads the simulation only; changes nothing in it. Raw results used in
docs/POMPEII_SOURCES.md are in tools/pompeii_results/sweep.json.

Run from the project root:
    PYTHONPATH=. python tools/pompeii_sweep.py out.json
"""

import sys
import json

sys.path.insert(0, ".")
from multiprocessing import Pool
from collections import Counter
from statistics import mean
from engine.pompeii import PompeiiSimulation


def one(a):
    m, mind, seed = a
    s = PompeiiSimulation(seed=seed, mind_type=mind, event_mapping=m)
    acts = Counter()
    t1 = t2 = None
    while True:
        r = s.step()
        if r is None:
            break
        if r["t"] == 20:
            t1 = r["counts"]["in_town"]
        if r["t"] == 52:
            t2 = r["counts"]["in_town"]
        for p in s.people:
            if p.is_alive and p.status != "escaped":
                acts[p.last_action] += 1
    d = s.death_breakdown()
    tb = s.outcome_table()
    tot = sum(acts.values()) or 1
    return dict(
        m=m,
        mind=mind,
        seed=seed,
        dead=len(s.deaths),
        pum=d["share_in_pumice_phase"],
        road=d["share_of_flow_deaths_on_roads"],
        causes=d["causes"],
        hide=acts["hide"] / tot,
        rest=acts["rest"] / tot,
        town17=t1,
        town01=t2,
        by={k: v["survived"] / v["total"] for k, v in tb.items()},
    )


if __name__ == "__main__":
    jobs = [(m, mi, s) for m in "ABCD" for mi in ("quantum", "classical_mixture", "classical") for s in range(1, 11)]
    with Pool(6) as p:
        rows = p.map(one, jobs)
    json.dump(rows, open(sys.argv[1], "w"))
    for m in "ABCD":
        for mi in ("quantum", "classical_mixture", "classical"):
            R = [r for r in rows if r["m"] == m and r["mind"] == mi]
            print(
                m,
                mi,
                "dead mean",
                round(mean(r["dead"] for r in R)),
                "range",
                min(r["dead"] for r in R),
                max(r["dead"] for r in R),
                "roof",
                round(mean(r["causes"].get("roof_collapse", 0) for r in R)),
                "flow",
                round(mean(r["causes"].get("pyroclastic_flow", 0) for r in R)),
                "hide%",
                round(100 * mean(r["hide"] for r in R)),
                "rest%",
                round(100 * mean(r["rest"] for r in R)),
                "town17",
                round(mean(r["town17"] or 0 for r in R)),
                "town01",
                round(mean(r["town01"] or 0 for r in R)),
            )

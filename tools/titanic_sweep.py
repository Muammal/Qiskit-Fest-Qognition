"""Titanic side-by-side test: input versions x event mappings x three minds x ten seeds.

Reads the simulation only; changes nothing in it. The mind is never touched.

Run from the project root:
    PYTHONPATH=. python tools/titanic_sweep.py out.json
"""
import json
import sys
from collections import Counter
from multiprocessing import Pool
from statistics import mean

from engine.titanic import TitanicSimulation

MINDS = ("quantum", "classical_mixture", "classical")
GROUPS = ("first", "second", "third", "crew")


def one(job):
    inputs, mapping, mind, seed = job
    sim = TitanicSimulation(seed=seed, mind_type=mind, inputs=inputs, event_mapping=mapping)
    sim.run()
    saved = Counter()
    for person in sim.people:
        if person.status == "boat" and person.is_alive:
            saved[person.cabin_class] += 1
    return dict(inputs=inputs, mapping=mapping, mind=mind, seed=seed, saved=sum(saved.values()), by_class=dict(saved),
                seats=sum(len(b.aboard) for b in sim.boats.boats), dead=sim.counts()["dead"])


if __name__ == "__main__":
    # early_pa_alarm is left out: it is a teammate's policy intervention, not a reading of the night's events.
    readings = ("default", "ambiguous_rockets", "only_water_certain")
    combos = [("original", "default", mi) for mi in MINDS] + [("neutral", m, mi) for m in readings for mi in MINDS]
    jobs = [(i, m, mi, seed) for i, m, mi in combos for seed in range(1, 11)]
    with Pool(6) as pool:
        rows = pool.map(one, jobs)
    json.dump(rows, open(sys.argv[1], "w"))
    for i, m, mi in combos:
        R = [r for r in rows if (r["inputs"], r["mapping"], r["mind"]) == (i, m, mi)]
        print(f"{i:9s}{m:19s} {mi:18s} saved {round(mean(r['saved'] for r in R)):4d} ({min(r['saved'] for r in R)}-{max(r['saved'] for r in R)}) "
              + " ".join(f"{g} {round(mean(r['by_class'].get(g, 0) for r in R)):3d}" for g in GROUPS))

"""Waterloo side-by-side test: three event mappings x three minds x three leak places x ten seeds.

Reads the simulation only; changes nothing in it. The mind is never touched.

Run from the project root:
    PYTHONPATH=. python tools/waterloo_sweep.py out.json
"""
import json
import sys
from multiprocessing import Pool
from statistics import mean

from engine.waterloo import EVENT_MAPPINGS, WaterlooSimulation

MINDS = ("quantum", "classical_mixture", "classical")
SITES = ("pool_side", "north_end", "deck")


def one(job):
    mapping, mind, site, seed = job
    sim = WaterlooSimulation(seed=seed, mind_type=mind, event_mapping=mapping, leak_site=site)
    timeline = sim.run()
    return dict(mapping=mapping, mind=mind, site=site, seed=seed, off=timeline["crowd"]["counts"]["off_site"], knows=timeline["crowd"]["counts"]["knows"],
                exposure=list(sim.exposure_summary().values()), timing=sim.timing(), ended=sim.t)


if __name__ == "__main__":
    jobs = [(m, mi, s, seed) for m in EVENT_MAPPINGS for mi in MINDS for s in SITES for seed in range(1, 11)]
    with Pool(6) as pool:
        rows = pool.map(one, jobs)
    json.dump(rows, open(sys.argv[1], "w"))
    print("mapping mind              site       off_site(range) knows  half_off_s  above AEGL-1/2/3")
    for m in EVENT_MAPPINGS:
        for mi in MINDS:
            for s in SITES:
                R = [r for r in rows if (r["mapping"], r["mind"], r["site"]) == (m, mi, s)]
                half = [r["timing"]["half_off_site"] for r in R if r["timing"]["half_off_site"] is not None]
                print(f"{m:7s} {mi:17s} {s:10s} {mean(r['off'] for r in R):5.1f} ({min(r['off'] for r in R)}-{max(r['off'] for r in R)})"
                      f" {mean(r['knows'] for r in R):6.1f}  {round(mean(half)) if half else '-':>6}  "
                      f"{mean(r['exposure'][1] for r in R):5.1f} {mean(r['exposure'][2] for r in R):5.1f} {mean(r['exposure'][3] for r in R):5.1f}")

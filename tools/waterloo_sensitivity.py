"""Waterloo assumption tests: change one assumption at a time, ten seeds each.

Settings are changed only in the worker running that job, which exits afterward.
The mind is never touched. Raw results are in tools/waterloo_results/sensitivity.json.

Run from the project root:
    PYTHONPATH=. python tools/waterloo_sensitivity.py out.json
"""

import json
import sys
from multiprocessing import Pool
from statistics import mean

import engine.chlorine as C
import engine.patrons as P
import engine.site as T
import engine.waterloo as W

CONFIGS = {
    "baseline": {},
    "40 people": {"kw.population": 40},
    "300 people": {"kw.population": 300},
    "source 11 ppm": {"kw.source_ppm": 11.0},
    "source 110 ppm": {"kw.source_ppm": 110.0},
    "leak 5 min": {"kw.leak_minutes": 5.0},
    "leak 60 min": {"kw.leak_minutes": 60.0},
    "leak at north end": {"kw.leak_site": "north_end"},
    "leak on deck": {"kw.leak_site": "deck"},
    "decide every 30 s": {"kw.decision_seconds": 30},
    "decide every 2 min": {"kw.decision_seconds": 120},
    "alarm off": {"kw.alarm": False},
    "alarm delay 0 s": {"W.ALARM_DELAY_STEPS": 0},
    "alarm delay 2 min": {"W.ALARM_DELAY_STEPS": 12},
    "alarm heard half as often": {"W.ALARM_HEAR_CHANCE": dict(indoors=0.25, outdoors=0.125)},
    "smell chance x0.5": {"P.SMELL_CHANCE": 0.1},
    "smell chance x2": {"P.SMELL_CHANCE": 0.4},
    "word chance x0.5": {"W.WORD_CHANCE": 0.05},
    "word chance x2": {"W.WORD_CHANCE": 0.2},
    "indoor spread x0.2": {"C.INDOOR_SPREAD_M2_S": 0.05},
    "indoor spread x2": {"C.INDOOR_SPREAD_M2_S": 0.5},
    "ventilation 1 per hour": {"C.INDOOR_LOSS_PER_S": 1 / 3600},
    "ventilation 10 per hour": {"C.INDOOR_LOSS_PER_S": 10 / 3600},
    "outdoor thinning x0.25": {"C.OUTDOOR_LOSS_PER_S": 0.005},
    "wading 0.25 m/s": {"T.WADE_M_PER_S": 0.25},
    "children walk at adult speed": {"P.ROLE_SPEED_M_S": dict(child=1.3, adult=1.3, lifeguard=1.3, desk=1.3)},
}
RUNS = (("A", "quantum"), ("A", "classical_mixture"), ("B", "quantum"))
MODULES = dict(C=C, P=P, T=T, W=W)


def one(job):
    name, mapping, mind, seed = job
    kw = {}
    for key, value in CONFIGS[name].items():
        module, attribute = key.split(".")
        if module == "kw":
            kw[attribute] = value
        else:
            setattr(MODULES[module], attribute, value)
    C._CACHE.clear()
    sim = W.WaterlooSimulation(seed=seed, mind_type=mind, event_mapping=mapping, **kw)
    sim.run()
    total = len(sim.people)
    return dict(
        name=name,
        mapping=mapping,
        mind=mind,
        seed=seed,
        total=total,
        off=sim.counts()["off_site"],
        knows=sim.counts()["knows"],
        exposure=list(sim.exposure_summary().values()),
        timing=sim.timing(),
        peak=float(sim.chlorine.ppm.max()),
    )


if __name__ == "__main__":
    jobs = [(n, m, mi, s) for n in CONFIGS for m, mi in RUNS for s in range(1, 11)]
    with Pool(6, maxtasksperchild=1) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    json.dump(rows, open(sys.argv[1], "w"))
    for n in CONFIGS:
        for m, mi in RUNS:
            R = [r for r in rows if (r["name"], r["mapping"], r["mind"]) == (n, m, mi)]
            half = [r["timing"]["half_off_site"] for r in R if r["timing"]["half_off_site"] is not None]
            print(
                f"{n:30s} {m} {mi:18s} off {mean(r['off'] for r in R):6.1f}/{R[0]['total']:3d} ({min(r['off'] for r in R)}-{max(r['off'] for r in R)}) "
                f"half {round(mean(half)) if half else '-':>5} [{len(half)}/10] AEGL1+ {mean(sum(r['exposure'][1:]) for r in R):5.1f} AEGL2+ {mean(sum(r['exposure'][2:]) for r in R):5.1f} AEGL3 {mean(r['exposure'][3] for r in R):4.1f}"
            )

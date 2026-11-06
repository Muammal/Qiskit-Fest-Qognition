"""per_slot against per_time dephasing. Protocol: docs/protocols/2d_time_aware_decoherence.md.

    python -m mind.experiments.time_aware

Writes mind/results/time_aware.json. The crowd scenarios decide every step, or every
`decision_seconds` at Waterloo, so one slot is 2 h, 5 min, 15 min or 1 min.
"""

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import contracts  # noqa: F401  (must load before mind; see conftest.py)
from engine.events import VOLCANIC
from engine.pompeii import PompeiiSimulation
from engine.simulation import SimulationEngine
from engine.titanic import TitanicSimulation
from engine.waterloo import WaterlooSimulation
from mind.experiments.validate import evacuation_delay
from mind.quantum_mind import quantum_decide

OUT = Path(__file__).resolve().parents[1] / "results" / "time_aware.json"
AEGL2_OR_WORSE = ("above AEGL-2, serious or lasting effects", "above AEGL-3, risk to life")
SEED = 42


def per_time_decide(state):
    return quantum_decide(state, dephasing_mode="per_time")


def deciders():
    return dict(per_slot=None, per_time=per_time_decide)


def titanic(mode):
    sim = TitanicSimulation(seed=SEED, decide_fn=deciders()[mode])
    sim.run()
    return dict(saved=sim.counts()["boats"], total=len(sim.people))


def pompeii(mode):
    sim = PompeiiSimulation(seed=SEED, decide_fn=deciders()[mode])
    sim.run()
    return dict(dead=sim.counts()["dead"], total=len(sim.people))


def waterloo(mode):
    sim = WaterlooSimulation(seed=SEED, decide_fn=deciders()[mode])
    exposure = sim.run()["crowd"]["exposure"]
    return dict(aegl2_or_worse=sum(exposure[name] for name in AEGL2_OR_WORSE), off_site=sim.counts()["off_site"], total=len(sim.people))


def volcano_seed(seed):
    out = {}
    for mode, fn in deciders().items():
        timeline = SimulationEngine(seed=seed, decide_fn=fn).run()
        out[mode] = dict(
            survived=timeline["outcome"] == "survived", delay=evacuation_delay(timeline["steps"], VOLCANIC), actions=[s["action"] for s in timeline["steps"]]
        )
    return out


def _job(name_mode):
    name, mode = name_mode
    return name, mode, dict(titanic=titanic, pompeii=pompeii, waterloo=waterloo)[name](mode)


def main():
    with ProcessPoolExecutor() as pool:
        volcano = list(pool.map(volcano_seed, range(200), chunksize=4))
        scenario_rows = list(pool.map(_job, [(n, m) for n in ("titanic", "pompeii", "waterloo") for m in deciders()]))
    identical = all(r["per_slot"]["actions"] == r["per_time"]["actions"] for r in volcano)
    result = dict(
        volcano=dict(seeds=200, identical_actions=identical, survival={m: sum(r[m]["survived"] for r in volcano) / 200 for m in deciders()}), scenarios={}
    )
    for name, mode, row in scenario_rows:
        result["scenarios"].setdefault(name, {})[mode] = row
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()

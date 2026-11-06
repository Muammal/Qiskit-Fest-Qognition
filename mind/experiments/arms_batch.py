"""All arms on the default volcano, paired seeds. Protocol: docs/protocols/2b_control_arms.md.

    python -m mind.experiments.arms_batch

Writes mind/results/arms_batch.json. Uses the default argmax rule and the default
start, so the quantum, mixture and classical rows are the paper's batch.
"""
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import contracts  # noqa: F401  (must load before mind; see conftest.py)
from engine.events import VOLCANIC
from engine.simulation import SimulationEngine
from mind.experiments.validate import evacuation_delay

ARMS = ("quantum", "classical_no_interference", "markov_hesitation", "classical_mixture", "classical")
OUT = Path(__file__).resolve().parents[1] / "results" / "arms_batch.json"


def run_seed(seed):
    out = {}
    for arm in ARMS:
        timeline = SimulationEngine(seed=seed, mind_type=arm).run()
        out[arm] = dict(survived=timeline["outcome"] == "survived", delay=evacuation_delay(timeline["steps"], VOLCANIC))
    return out


def summarise(records):
    table = {}
    for arm in ARMS:
        diffs = [r[arm]["delay"] - r["classical_mixture"]["delay"] for r in records
                 if r[arm]["delay"] is not None and r["classical_mixture"]["delay"] is not None]
        n = len(diffs)
        mean = sum(diffs) / n if n else None
        se = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1) / n) if n > 1 else None
        table[arm] = dict(survival=sum(r[arm]["survived"] for r in records) / len(records), paired_n=n, delay_vs_mixture=mean, se=se,
                          later=sum(d > 0 for d in diffs), earlier=sum(d < 0 for d in diffs), same=sum(d == 0 for d in diffs))
    return table


def main(seeds=range(200)):
    with ProcessPoolExecutor() as pool:
        records = list(pool.map(run_seed, seeds, chunksize=4))
    table = summarise(records)
    OUT.write_text(json.dumps(dict(seeds=[seeds[0], seeds[-1]], arms=table), indent=1), encoding="utf-8")
    print(json.dumps(table, indent=1))


if __name__ == "__main__":
    main()

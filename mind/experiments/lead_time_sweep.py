"""Does the quantum mind's hesitation cost lives when warning time is short?

Protocol: docs/protocols/2a_lead_time_sweep.md (arms: 2b_control_arms.md).

    python -m mind.experiments.lead_time_sweep          # full run, all cores
    python -m mind.experiments.lead_time_sweep --pilot  # seeds outside the main run

The default volcano leaves about 25 h of margin against about 1.1 h of delay, so
survival sits at its ceiling. Here the first sign comes a set time before the
first flow, the person starts a set distance down the valley every pulse uses,
and each step's action is sampled. Each person has their own trait stress and
eta, drawn identically in every arm, so arms are paired on seed and replicate.

Outputs go to mind/results/lead_time/.
"""
import argparse
import csv
import json
import math
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import contracts  # noqa: F401  (must load before mind; see conftest.py)
from engine.events import VOLCANIC
from engine.simulation import DEFAULT_STEPS, SimulationEngine
from engine.world import MAP_SEED, IslandWorld
from mind.config import ETA, MARKOV_HESITATION
from mind.quantum_mind import _decide

OUT_DIR = Path(__file__).resolve().parents[1] / "results" / "lead_time"
CATALOG = Path(__file__).resolve().parents[2] / "disaster_data" / "catalog" / "precursor_lead_times.csv"

# Fixed by the protocol.
LEADS_HOURS = (0, 2, 4, 6, 8, 12, 24, 30)  # catalogue quartiles and 90th percentile, on 2 h steps
DISTANCES_TILES = (4.2, 6.4, 8.9, 10.8)  # nearest tile on the perennial valley; a tile is 250 m
SEEDS = range(60)
PILOT_SEEDS = range(5000, 5005)
REPLICATES = 30
STRESS_OFFSET_SD = 0.10  # trait stress, added to the state's stress at each decision
ETA_SD = 0.15  # person's eta, clipped to [-1, 0]
TS_HESITATION = 1 - 0.36 / 0.64  # hits Tversky & Shafir's 0.36 at p=0.5, the row ETA was solved from
ARMS = ("quantum", "classical_mixture", "classical_no_interference", "markov_hesitation", "markov_hesitation_ts")
CONTROLS = ARMS[1:]
BOOTSTRAPS = 2000


def person(seed, replicate):
    """Trait stress offset and eta. A pure function of seed and replicate, so every arm gets the same person."""
    rng = random.Random(f"person-{seed}-{replicate}")
    return rng.gauss(0.0, STRESS_OFFSET_SD), min(0.0, max(-1.0, rng.gauss(ETA, ETA_SD)))


def make_decider(arm, stress_offset, eta):
    common = dict(decision_rule="sample", suppress_order_gap=True)
    options = {
        "quantum": dict(eta=eta),
        "classical_mixture": dict(force_lam=1.0),
        "classical_no_interference": dict(cognition_model="no_interference"),
        "markov_hesitation": dict(force_lam=1.0, hesitation=MARKOV_HESITATION),
        "markov_hesitation_ts": dict(force_lam=1.0, hesitation=TS_HESITATION),
    }[arm]

    def decide(state):
        shifted = dict(state, stress=min(1.0, max(0.0, state["stress"] + stress_offset)))
        return _decide(shifted, **common, **options)

    return decide


def start_tiles():
    """For each distance, the tile on the perennial valley nearest that distance from the vent."""
    world = IslandWorld(seed=MAP_SEED, scenario="volcano")
    valley = world.valleys[0]
    return {d: min(valley, key=lambda p: abs(math.dist(p, world.vent) - d)) for d in DISTANCES_TILES}


def run_once(seed, replicate, arm, lead_hours, start):
    stress_offset, eta = person(seed, replicate)
    sim = SimulationEngine(seed=seed, mind_type="classical", decide_fn=make_decider(arm, stress_offset, eta),
                           warning_lead_override_hours=lead_hours, spawn_override=start,
                           decision_seed=seed * 1009 + replicate)
    alive_after_flow = None
    flow = sim.volcano.first_pdc_step
    while len(sim.steps) < DEFAULT_STEPS:
        record = sim.step()
        if record is None:
            break
        if record["t"] == flow:
            alive_after_flow = sim.agent.is_alive
    if alive_after_flow is None:  # died before the first flow
        alive_after_flow = False
    sign = next((s["t"] for s in sim.steps if s["event"] in VOLCANIC), None)
    hide = next((s["t"] for s in sim.steps if s["action"] == "hide" and sign is not None and s["t"] >= sign), None)
    return dict(survived=sim.agent.is_alive, survived_first_flow=alive_after_flow,
                delay_steps=None if hide is None else hide - sign, cause=sim.agent.cause_of_death)


def _seed_cell(args):
    """One seed, one lead, one distance, one arm, averaged over replicates."""
    seed, arm, lead, distance, start, replicates = args
    rows = [run_once(seed, r, arm, lead, start) for r in range(replicates)]
    delays = [r["delay_steps"] for r in rows if r["delay_steps"] is not None]
    return dict(seed=seed, arm=arm, lead_hours=lead, distance_tiles=distance, replicates=replicates,
                survived=float(np.mean([r["survived"] for r in rows])),
                survived_first_flow=float(np.mean([r["survived_first_flow"] for r in rows])),
                delay_steps=float(np.mean(delays)) if delays else float("nan"),
                never_hid=float(np.mean([r["delay_steps"] is None for r in rows])))


def catalog_quartiles():
    with CATALOG.open(encoding="utf-8", newline="") as stream:
        values = [float(r["lead_hours"]) for r in csv.DictReader(stream) if r["lead_hours"]]
    return dict(n=len(values), q25=float(np.percentile(values, 25)), median=float(np.median(values)),
                q75=float(np.percentile(values, 75)), q90=float(np.percentile(values, 90)))


def bootstrap_ci(by_seed, rng):
    """Percentile 95% interval, resampling seeds. by_seed is one value per seed."""
    by_seed = np.asarray(by_seed, dtype=float)
    by_seed = by_seed[~np.isnan(by_seed)]
    if len(by_seed) == 0:
        return float("nan"), float("nan")
    draws = rng.integers(0, len(by_seed), size=(BOOTSTRAPS, len(by_seed)))
    means = by_seed[draws].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def holm(p_values):
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values))
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted.tolist()


def bootstrap_p(by_seed, rng):
    """Two-sided p that the mean is 0, from a sign-flip test over seeds."""
    by_seed = np.asarray(by_seed, dtype=float)
    by_seed = by_seed[~np.isnan(by_seed)]
    if len(by_seed) == 0 or np.allclose(by_seed, 0):
        return 1.0
    observed = abs(by_seed.mean())
    flips = rng.choice((-1.0, 1.0), size=(BOOTSTRAPS, len(by_seed)))
    null = np.abs((flips * by_seed).mean(axis=1))
    return float((1 + np.sum(null >= observed - 1e-12)) / (BOOTSTRAPS + 1))


def summarise(cells):
    rng = np.random.default_rng(20261106)
    table = {}
    for cell in cells:
        table[(cell["seed"], cell["arm"], cell["lead_hours"], cell["distance_tiles"])] = cell
    seeds = sorted({c["seed"] for c in cells})
    leads = sorted({c["lead_hours"] for c in cells})
    distances = sorted({c["distance_tiles"] for c in cells})
    arms = [a for a in ARMS if any(c["arm"] == a for c in cells)]

    def seed_mean(arm, lead, metric, seed, only_distance=None):
        values = [table[(seed, arm, lead, d)][metric] for d in distances if only_distance in (None, d)]
        return float(np.nanmean(values)) if not all(math.isnan(v) for v in values) else float("nan")

    curves = []
    for arm in arms:
        for lead in leads:
            for only in (None, *distances):
                row = dict(arm=arm, lead_hours=lead, distance_tiles="all" if only is None else only)
                for metric in ("survived", "survived_first_flow", "delay_steps", "never_hid"):
                    by_seed = [seed_mean(arm, lead, metric, s, only) for s in seeds]
                    low, high = bootstrap_ci(by_seed, rng)
                    row[metric] = float(np.nanmean(by_seed)) if not all(math.isnan(v) for v in by_seed) else float("nan")
                    row[metric + "_low"], row[metric + "_high"] = low, high
                curves.append(row)

    contrasts = []
    for control in [a for a in arms if a != "quantum"]:
        rows = []
        for lead in leads:
            row = dict(control=control, lead_hours=lead)
            for metric in ("survived", "survived_first_flow", "delay_steps"):
                diffs = [seed_mean("quantum", lead, metric, s) - seed_mean(control, lead, metric, s) for s in seeds]
                low, high = bootstrap_ci(diffs, rng)
                row[metric + "_diff"] = float(np.nanmean(diffs))
                row[metric + "_low"], row[metric + "_high"] = low, high
                row[metric + "_p"] = bootstrap_p(diffs, rng)
            rows.append(row)
        for metric in ("survived", "survived_first_flow", "delay_steps"):
            for row, adjusted in zip(rows, holm([r[metric + "_p"] for r in rows])):
                row[metric + "_p_holm"] = adjusted
        contrasts += rows
    return curves, contrasts


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(seeds=SEEDS, replicates=REPLICATES, arms=ARMS, leads=LEADS_HOURS, workers=None, out_dir=OUT_DIR):
    starts = start_tiles()
    jobs = [(seed, arm, lead, d, starts[d], replicates) for seed in seeds for arm in arms for lead in leads for d in DISTANCES_TILES]
    began = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        cells = list(pool.map(_seed_cell, jobs, chunksize=4))
    curves, contrasts = summarise(cells)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "cells.csv", cells)
    write_csv(out_dir / "curves.csv", curves)
    write_csv(out_dir / "contrasts.csv", contrasts)
    meta = dict(seeds=[seeds[0], seeds[-1]], replicates=replicates, arms=list(arms), leads_hours=list(leads),
                distances_tiles=list(DISTANCES_TILES), start_tiles={str(k): list(v) for k, v in starts.items()},
                stress_offset_sd=STRESS_OFFSET_SD, eta_sd=ETA_SD, eta_mean=ETA, markov_hesitation=MARKOV_HESITATION,
                ts_hesitation=TS_HESITATION, catalog=catalog_quartiles(), runs=len(jobs) * replicates,
                seconds=round(time.time() - began, 1))
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return cells, curves, contrasts, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if args.pilot:
        _cells, curves, contrasts, meta = run(seeds=PILOT_SEEDS, replicates=8, out_dir=OUT_DIR.parent / "lead_time_pilot")
    else:
        _cells, curves, contrasts, meta = run()
    print(json.dumps(meta, indent=1))
    for row in curves:
        if row["distance_tiles"] == "all":
            print(row["arm"].ljust(28), row["lead_hours"], *(f"{row[k]:.3f}" for k in ("survived", "survived_first_flow", "delay_steps", "never_hid")))


if __name__ == "__main__":
    main()

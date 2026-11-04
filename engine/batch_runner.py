"""
engine/batch_runner.py - Batch Simulation Runner & Divergence Analysis
Owned by Tech C (Integration, Engine, Batch Analysis).
"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.simulation import SimulationEngine, DEFAULT_STEPS


def run_batch_comparison(num_seeds: int = 20, max_steps: int = DEFAULT_STEPS) -> Dict[str, Any]:
    """Compare synthetic heuristic stubs on paired event seeds."""
    records = []
    divergence_steps = 0
    total_steps = 0

    print(f"[BatchRunner] Synthetic heuristic-stub comparison: {num_seeds} paired seeds "
          "(quantum-labelled vs classical-labelled stubs; no quantum or hardware results).")

    for seed in range(100, 100 + num_seeds):
        # 1. Run Quantum Mind
        sim_q = SimulationEngine(seed=seed, mind_type="quantum", noise_source="stub")
        res_q = sim_q.run(max_steps=max_steps)

        # 2. Run Classical Mind on identical seed
        sim_c = SimulationEngine(seed=seed, mind_type="classical", noise_source="stub")
        res_c = sim_c.run(max_steps=max_steps)

        steps_q = len(res_q["steps"])
        steps_c = len(res_c["steps"])

        # Compare step-by-step actions
        min_steps = min(steps_q, steps_c)
        seed_divergences = 0
        for i in range(min_steps):
            act_q = res_q["steps"][i]["action"]
            act_c = res_c["steps"][i]["action"]
            if act_q != act_c:
                divergence_steps += 1
                seed_divergences += 1
            total_steps += 1

        records.append({
            "seed": seed,
            "q_outcome": res_q["outcome"],
            "q_cause": res_q["cause"],
            "q_steps": steps_q,
            "c_outcome": res_c["outcome"],
            "c_cause": res_c["cause"],
            "c_steps": steps_c,
            "divergences": seed_divergences,
            "divergence_pct": round(seed_divergences / max(1, min_steps) * 100.0, 1)
        })

    df = pd.DataFrame(records)
    divergence_rate = round(divergence_steps / max(1, total_steps) * 100.0, 2)
    q_survival_rate = round((df["q_outcome"] == "survived").mean() * 100.0, 1)
    c_survival_rate = round((df["c_outcome"] == "survived").mean() * 100.0, 1)

    summary = {
        "noise_source": "stub",
        "provenance": {
            "result_type": "synthetic_heuristic_stub",
            "quantum_policy": "contracts.quantum_decide",
            "classical_policy": "contracts.classical_decide",
            "disclosure": "Synthetic heuristic-stub results; no quantum circuits or hardware runs.",
        },
        "num_seeds": num_seeds,
        "total_evaluated_steps": total_steps,
        "total_divergences": divergence_steps,
        "divergence_rate_pct": divergence_rate,
        "quantum_survival_rate_pct": q_survival_rate,
        "classical_survival_rate_pct": c_survival_rate,
        "records": records
    }
    return summary


def curate_demo_pack(output_dir="demo-pack"):
    """Search ordinary seeds for truthful illustrative stub runs."""
    os.makedirs(output_dir, exist_ok=True)
    found = {}
    for seed in range(2000):
        q = SimulationEngine(seed=seed).run()
        if not q["world"]["volcano"]["erupts"]:
            continue
        if q["outcome"] == "survived":
            found.setdefault("run_01_heroic_survival", q)
        if q["cause"] in ("pyroclastic_flow", "lahar", "lava"):
            found.setdefault("run_02_dramatic_death", q)
        if "run_03_order_effect_quantum" not in found:
            c = SimulationEngine(seed=seed, mind_type="classical").run()
            if any(a["action"] != b["action"] for a,b in zip(q["steps"],c["steps"])) and any("Order effect" in r["reason"] for r in q["steps"]):
                found["run_03_order_effect_quantum"] = q
                found["run_04_order_effect_classical"] = c
        used = {timeline["world"]["seed"] for timeline in found.values()}
        if seed not in used and any(r["state"]["stress"] > .4 and "Decoherence" in r["reason"] for r in q["steps"]):
            found.setdefault("run_05_stress_decoherence", q)
        if len(found) == 5:
            break
    if len(found) != 5:
        raise RuntimeError(f"Seed search incomplete: {sorted(found)}")
    for name, timeline in found.items():
        with open(os.path.join(output_dir, name+".json"), "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2)
    print("[DemoPack] Five searched stub runs exported:", {k:v["world"]["seed"] for k,v in found.items()})


if __name__ == "__main__":
    print(run_batch_comparison())
    curate_demo_pack()

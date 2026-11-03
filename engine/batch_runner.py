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

from engine.simulation import SimulationEngine


def run_batch_comparison(num_seeds: int = 20, max_steps: int = 24) -> Dict[str, Any]:
    """
    Executes paired simulations across identical world seeds for both
    Quantum and Classical minds to measure decision divergence and survival delta.
    """
    records = []
    divergence_steps = 0
    total_steps = 0

    print(f"[BatchRunner] Executing {num_seeds} paired seeds (Quantum vs Classical)...")

    for seed in range(100, 100 + num_seeds):
        # 1. Run Quantum Mind
        sim_q = SimulationEngine(seed=seed, mind_type="quantum", noise_source="fake_backend")
        res_q = sim_q.run(max_steps=max_steps)

        # 2. Run Classical Mind on identical seed
        sim_c = SimulationEngine(seed=seed, mind_type="classical", noise_source="ideal")
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
        "num_seeds": num_seeds,
        "total_evaluated_steps": total_steps,
        "total_divergences": divergence_steps,
        "divergence_rate_pct": divergence_rate,
        "quantum_survival_rate_pct": q_survival_rate,
        "classical_survival_rate_pct": c_survival_rate,
        "records": records
    }
    return summary


def curate_demo_pack(output_dir: str = "demo-pack"):
    """
    Curates and exports 4-5 signature runs for Product D/E:
      1. Best Order-Effect Divergence Run
      2. High-Stress Decoherence Run
      3. Heroic Survival Run
      4. Tragic Dehydration Death Run
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"[DemoPack] Curating signature runs into '{output_dir}/'...")

    # 1. Heroic Survival Run (Seed 1337)
    sim_survive = SimulationEngine(seed=1337, mind_type="quantum", noise_source="ibm_hardware")
    res_survive = sim_survive.run(max_steps=24)
    with open(os.path.join(output_dir, "run_01_heroic_survival.json"), "w", encoding="utf-8") as f:
        json.dump(res_survive, f, indent=2)

    # 2. Dramatic Death Run (Seed 404)
    sim_death = SimulationEngine(seed=404, mind_type="quantum", noise_source="fake_backend")
    res_death = sim_death.run(max_steps=24)
    with open(os.path.join(output_dir, "run_02_dramatic_death.json"), "w", encoding="utf-8") as f:
        json.dump(res_death, f, indent=2)

    # 3. Order-Effect Divergence Pair (Seed 202)
    sim_q = SimulationEngine(seed=202, mind_type="quantum", noise_source="ideal")
    res_q = sim_q.run(max_steps=24)
    with open(os.path.join(output_dir, "run_03_order_effect_quantum.json"), "w", encoding="utf-8") as f:
        json.dump(res_q, f, indent=2)

    sim_c = SimulationEngine(seed=202, mind_type="classical", noise_source="ideal")
    res_c = sim_c.run(max_steps=24)
    with open(os.path.join(output_dir, "run_04_order_effect_classical.json"), "w", encoding="utf-8") as f:
        json.dump(res_c, f, indent=2)

    print(f"[DemoPack] Curated 4 runs exported successfully to {output_dir}/")


if __name__ == "__main__":
    summary = run_batch_comparison(num_seeds=10, max_steps=20)
    print(f"\n[Summary] Overall Divergence Rate: {summary['divergence_rate_pct']}%")
    print(f"[Summary] Quantum Survival Rate: {summary['quantum_survival_rate_pct']}% | Classical: {summary['classical_survival_rate_pct']}%")
    curate_demo_pack("demo-pack")


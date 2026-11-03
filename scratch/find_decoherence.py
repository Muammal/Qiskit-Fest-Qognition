import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.simulation import SimulationEngine

for s in range(100, 120):
    sim = SimulationEngine(seed=s, mind_type="quantum", noise_source="fake_backend")
    res = sim.run(24)
    decoh_steps = [st["t"] for st in res["steps"] if "Decoherence" in st.get("reason", "")]
    if len(decoh_steps) >= 3:
        print(f"Seed {s}: {len(decoh_steps)} decoherence steps: {decoh_steps}, outcome={res['outcome']}")

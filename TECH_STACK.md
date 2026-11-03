# Tech Stack

## Tools

| Area | Tool |
|---|---|
| Language | Python 3.11 (check compatibility with chosen libraries on Tuesday) |
| Quantum | Qiskit 2.x, Qiskit Aer (simulator), `qiskit-ibm-runtime` (real hardware + fake backends) |
| Cognition validation | One of `quantum-mind` or `qcog` (Q-Cog), evaluated Tuesday (see below) |
| Data | pandas (ATUS published summary tables only) |
| Plots | matplotlib |
| Website | Static HTML/CSS/JS reading JSON; GitHub Pages or Netlify |
| Collaboration | GitHub, one folder + branch per person |

**Pin exact versions in `requirements.txt` on Tuesday.** Qiskit's APIs changed a lot between versions, and everyone must use the same environment.

## Repo layout

```
stranded/
├── contracts.py          # frozen interfaces + stubs (Tech C)
├── requirements.txt      # pinned versions (Tech C)
├── mind/                 # Tech A
├── data/  baseline/  hardware/   # Tech B
├── engine/               # Tech C
├── demo-pack/            # shared hand-off folder (Thursday 6pm)
├── site/                 # Product D (site/content/ = Product E's markdown)
└── pitch/                # Product E
```

## Frozen interfaces (`contracts.py`)

Agreed Tuesday. Each function ships with a stub that returns valid fake output.

```python
ACTIONS = ["forage", "drink", "build_shelter", "rest", "explore", "craft", "hide"]
EVENTS  = ["storm", "injury", "find_food", "animal", "cold_night", "none"]

# state: plain dict passed everywhere
# {
#   "day": int, "hour": int, "pos": [x, y],
#   "needs": {"hunger","thirst","warmth","energy","safety","morale": float 0-1},
#   "stress": float 0-1, "injured": bool,
#   "inventory": {item: count}, "recent_events": [str, ...]   # last 3, in order
# }

def get_prior(state) -> dict:        # Tech B. Stub: uniform over ACTIONS
def classical_decide(state) -> dict: # Tech B. Stub: argmax of get_prior
def quantum_decide(state) -> dict:   # Tech A. Stub: random choice
# both decide functions return:
#   {"action": str, "probs": {action: float}, "reason": str}

def explore_step(pos, world, mode) -> list:  # OPTIONAL, Tech B. mode = "quantum" | "random"
```

## Timeline format (`timeline.json`)

Tech C writes it, Product D reads it.

```json
{
  "world": {"width": 40, "height": 40, "tiles": [[0, 1, 2]], "seed": 123, "mind": "quantum",
            "noise_source": "ibm_hardware | fake_backend | ideal"},
  "steps": [
    {"t": 0, "state": {}, "event": "storm", "action": "hide",
     "probs": {"hide": 0.6, "rest": 0.3, "forage": 0.1},
     "reason": "storm right after injury → safety first"}
  ],
  "outcome": "survived | died",
  "cause": "dehydration"
}
```

## The quantum mind (Tech A)

- **2 qubits** encode the belief state for the current decision.
- `get_prior()` probabilities → initial rotation angles (so the baseline matches real human habits).
- Each event in `recent_events` applies a rotation, **in order**. Because the rotations don't commute, order changes the outcome.
- Measurement → action. Probabilities come from the circuit and are logged as `probs`.
- **Stress:** more stress → more decoherence (hardware idle delay, or a noise model as fallback), which washes out interference effects.

### Existing libraries (validation, not the core)

- **`quantum-mind` (PyPI):** quantum probability models of judgement and decision for Qiskit 2.x, with classical baselines, order-effect models, and a QQ-equality test.
- **`qcog` (Q-Cog):** Qiskit-native quantum cognition models; order-effect reports, runs exactly / on Aer / with a decoherence parameter.

Plan: Tech A installs both in a throwaway environment Tuesday and keeps whichever works with the pinned Qiskit. Use it to **validate** our circuit and supply **classical baselines**. Our own circuit remains the core (so we can explain every gate and send it to hardware). Credit the library in the README and slides. If it conflicts, drop it.

**Reading:** "Quantum cognition and decision theories: A tutorial" (order effects + QQ equality, written for beginners).

## IBM hardware workflow (Tech B)

**The sim never calls hardware live.** We run a batch ahead of time and the sim loads the saved results.

1. **Access (Tuesday):** each member creates a free Open Plan account on IBM Quantum Platform (about 10 minutes of quantum time per month), saves credentials with `QiskitRuntimeService.save_account(...)` (check the current docs for the `channel` value), and **never commits keys**. Run a 2-qubit Bell test job to confirm access.
2. **Experiments (one batched job, Wednesday):**
   - **A. Decision table:** 20–40 representative situations × ~2,000 shots
   - **B. Order effect:** the same event pairs in both orders, compared against ideal Aer
   - **C. Stress = decoherence:** the same decision circuit with increasing `qc.delay(...)` idle times; delay length maps to stress level
3. **Fallback first:** run everything on a fake backend from `qiskit_ibm_runtime.fake_provider` and save it, *before* the hardware job. Label as "simulated device noise." Never present simulated results as real hardware.

```python
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

service = QiskitRuntimeService()
backend = service.least_busy(operational=True, simulator=False)

circuits = [build_mind_circuit(s) for s in scenarios]   # from Tech A, ending in measure_all()
pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
isa_circuits = pm.run(circuits)

job = Sampler(mode=backend).run(isa_circuits, shots=2000)   # ONE job, Open Plan = job mode
print("SAVE THIS:", job.job_id())

# later:
result = service.job(job_id).result()
counts = [r.data.meas.get_counts() for r in result]
# write hardware_results.json with backend name + date + counts
```

## Data (Tech B)

- **Source:** American Time Use Survey (US Bureau of Labor Statistics), **published summary tables** only.
- **Output:** `priors.json`, average tendencies by context (time of day, fatigue, hunger) → action probabilities.
- No scraping, no model training, nothing personal. Time-box: half a day.

# Quantum Cognition Simulation: Decision-Making & Multi-Scenario Survival

[![Integration Tests](https://img.shields.io/badge/tests-29%20passed-brightgreen.svg)](#daily-integration--testing)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x-6929C4.svg)](https://qiskit.org/)
[![Status](https://img.shields.io/badge/Multi--Scenario-Integrated-success.svg)](#tech-c-deliverables)

> **"Can quantum probability explain why humans make counterintuitive survival decisions under extreme environmental stress?"**

**Quantum Cognition Simulation** is an interactive multi-scenario cognitive modeling sandbox built for an advanced quantum hackathon. Players can choose between two distinct simulation horizons right from launch:

1. **Island Wilderness Survival**: Stranded across a procedural 40x40 archipelago. Manage hunger, hydration, hypothermia, fatigue, and morale while foraging timber/rations, building shelters, and surviving stochastic maritime storms and territorial boars.
2. **Volcano Eruption Evacuation**: Evacuate a calibrated 40x40 volcanic topography under accelerating seismic unrest. Decipher precursory tremors and gas plumes, navigate around lethal lava meanders and lahars, endure toxic ash fall, and follow BFS routes to safe assembly points.

The agent's decision engine supports both a **2-qubit quantum cognition circuit** (exhibiting non-commuting order effects, constructive interference, and physiological stress decoherence) and an empirical **classical baseline** (derived from ATUS utility priors).

> **Current status:** the minds in `contracts.py` are placeholder stubs, not quantum circuits or real data. Runs from them are labelled `noise_source: "stub"`, and comparisons between them are not results. See [the volcano model notes](docs/VOLCANO_MODEL.md) for sources, assumptions and the JSON format.

---

## Architecture & Team Boundaries

The project is structured around **3 tech + 2 product** roles with frozen interfaces and file-based hand-offs (`ROLES.md`):

```
stranded/
├── contracts.py              # Frozen interfaces + working stubs (Tech C)
├── requirements.txt          # Pinned dependency environment (Tech C)
├── main.py                   # Interactive CLI demo & benchmark runner (Tech C)
├── docs/VOLCANO_MODEL.md     # Sources, assumptions, constants, JSON format (Tech C)
├── engine/                   # World, volcano, agents, survival loop (Tech C)
│   ├── world.py              # One fixed island, valleys, evacuation zones
│   ├── volcano.py            # Seeded hidden unrest, eruption and hazard model
│   ├── agent.py              # Movement, physiology & lethal checks
│   ├── events.py             # Weather and activity-linked event models
│   ├── simulation.py         # Turn-based loop emitting timeline.json
│   └── batch_runner.py       # Paired mind comparison & demo curation
├── demo-pack/                # Curated signature runs for frontend replay (Tech C)
│   ├── run_01_heroic_survival.json
│   ├── run_02_dramatic_death.json
│   ├── run_03_order_effect_quantum.json
│   ├── run_04_order_effect_classical.json
│   └── run_05_stress_decoherence.json
├── timeline.json             # Day 1 sample timeline handed to Product D
├── test_contracts_and_engine.py # Daily integration test suite
├── mind/                     # 2-qubit quantum mind circuits (Tech A)
├── data/ baseline/ hardware/ # ATUS priors, classical baseline, IBM hardware jobs (Tech B)
├── site/                     # Replay viewer & "Why did he do that?" UI (Product D)
└── pitch/                    # Pitch deck, demo video script, judge FAQ (Product E)
```

---

## Frozen Contracts (`contracts.py`)

All tech roles code against `contracts.py`. Stubs guarantee that nobody is blocked while real quantum circuits and ATUS tables are being constructed.

### Primitive Constants
- **`ACTIONS`**: `["forage", "drink", "build_shelter", "rest", "explore", "craft", "hide"]`
- **`EVENTS`**: `["storm", "injury", "find_food", "animal", "cold_night", "none", "tremor", "gas_plume", "eruption", "ash_fall"]`
- **`TILE_TYPES`**: `{0: "water", 1: "plains", 2: "forest", 3: "mountain", 4: "shelter"}`

### Interface Signatures
```python
def get_prior(state: dict) -> dict:
    """Tech B: Baseline human habit distribution from published ATUS summary tables."""

def classical_decide(state: dict) -> dict:
    """Tech B: Rational classical decision baseline (deterministic prior argmax)."""

def quantum_decide(state: dict) -> dict:
    """Tech A: 2-Qubit quantum cognition decision engine (Qiskit 2.x)."""

def explore_step(pos: list, world: Any, mode: str = "quantum") -> list:
    """Tech B (Optional): Map traversal via quantum walk vs brownian random walk."""

def load_seeds() -> list:
    """Tech B: Seed list. Stub returns placeholder integers."""
```

### Decision Contract Schema
Every decision strictly validates against:
```json
{
  "action": "hide",
  "probs": {
    "forage": 0.05,
    "drink": 0.05,
    "build_shelter": 0.15,
    "rest": 0.10,
    "explore": 0.05,
    "craft": 0.05,
    "hide": 0.55
  },
  "reason": "Order effect: injury followed by storm induces constructive fear interference -> prioritizing safety"
}
```

---

## The Quantum Cognition Model

### 1. Non-Commuting Order Effects
Classical Bayesian inference satisfies commutativity:
$$P(A \cap B) = P(B \cap A)$$
In human cognition and quantum mechanics, operators do not commute ($[U_A, U_B] \neq 0$). Experiencing an **injury followed by a storm** collapses the agent's belief state into defensive constructive interference favoring `hide` and `build_shelter`. In contrast, experiencing a **storm followed by an injury** produces a distinct cognitive trajectory favoring physical recuperation (`rest`).

### 2. Stress as Physical Decoherence
In physics, open quantum systems undergo decoherence ($T_1$ relaxation and $T_2$ dephasing) when coupled to an ambient thermal bath. In **Stranded**, an agent experiencing critical physiological stress (hunger, hypothermia, predator threat) experiences high decoherence:
- Interference patterns between decision states wash out.
- The off-diagonal density matrix terms decay, relaxing the pure quantum state into a noisy mixed classical distribution.
- This accurately mirrors cognitive "tunnel vision" and decision paralysis under trauma.

---

## What's Real vs. What's Metaphor?

| Component | Status | Reality vs Metaphor |
|---|---|---|
| **Quantum Circuits** | Planned | 2-qubit Qiskit 2.x circuits on the Aer simulator and fake backends, then IBM Quantum hardware. Not done yet: current runs use stubs. |
| **Decoherence Delay** | Planned | Circuits with `qc.delay(...)` idling to measure physical qubit decoherence as a function of simulated stress. Not done yet: the stub only mixes probabilities. |
| **Volcano & Events** | Synthetic model | Mechanisms informed by published sources, with assumed rates and compressed timing. Not a forecast or a real evacuation tool. See `docs/VOLCANO_MODEL.md`. |
| **Cognitive Interference** | Mathematical Model | Human decision-making modeled using Hilbert space geometry (Hilbert space projection postulate) rather than classical Kolmogorov probability. |
| **Biological Substrate** | Metaphor | The human brain is warm and wet, not a cryogenic 15mK dilution refrigerator. Quantum probability here is an algebraic theory of decision, not quantum biology. |

---

## Quickstart & Launch Commands

### Single Launch Command (Interactive GUI with Home Screen)
Simply run `python main.py` to launch the full graphical simulation with the interactive Home Screen:
```bash
python main.py
```
From the **Home Screen**, you can interactively:
1. **Choose the Decision Mind**: `[Quantum-labelled Stub]` vs `[Classical Heuristic Stub]`.
2. **Select Event Seed**: The island never changes. The seed changes weather, events and the volcano. Pick a preset or use the steppers / randomizer.
3. **Set Simulation Horizon**: Choose duration (`12`, `24`, or `36` steps).
4. **Launch**: Click `[LAUNCH SURVIVAL SIMULATION]`.
5. **End-of-Event Debrief**: At the conclusion of the event (or upon fatality), a mission debrief modal appears with replay options, mind comparison, and return-to-home navigation.

---

### Fullscreen & Interactive Controls

| Control | Action |
|---|---|
| `F11` or `[⛶ Fullscreen]` Button | **Toggle Fullscreen / Windowed Mode** (Aspect-ratio scaled with letterboxing) |
| `ENTER` / `SPACE` (Home Screen) | **Launch Survival Simulation** |
| `SPACE` (In Simulation) | **Play / Pause** auto-stepping |
| `RIGHT ARROW` or `N` | **Step Forward** single 2-hour turn |
| `Q` or `[⚛ Mind Toggle]` Button | **Toggle Mind Live** (Quantum Mind $\leftrightarrow$ Classical Baseline) |
| `1` / `2` / `3` or `[⚡ Speed]` Button | **Cycle Speed** (1.0x normal, 2.5x fast, 6.0x instant) |
| `E` | **Toggle Evacuation Map** (zones, assembly point, route from spawn) |
| `TAB` or `[Action Log]` Button | **Toggle Chronological Action History Overlay** |
| `R` | **Reset Current Run** |
| `ESC` or `H` or `[🏠 Menu]` Button | **Return to Home Configuration Screen** |

---

### Alternative CLI Modes
```bash
# Launch GUI directly into a specific seed
python main.py --seed 101 --mind quantum

# Terminal ASCII visual demo
python main.py --demo --seed 101

# Multi-seed batch divergence benchmark (Quantum vs Classical)
python main.py --batch

# Regenerate curated demo-pack/
python main.py --curate

# Run the integration test suite
python main.py --test
```

---

## Citations & Acknowledgments

1. **Busemeyer, J. R., & Wang, Z. (2014).** *Quantum model of cognition and decision.* Current Directions in Psychological Science.
2. **Pothos, E. M., & Busemeyer, J. R. (2022).** *Quantum cognition.* Annual Review of Psychology.
3. **Qiskit Development Team (2025).** *Qiskit: An Open-source Framework for Quantum Computing.*
4. **Bureau of Labor Statistics (BLS).** *American Time Use Survey (ATUS) Summary Tables.*

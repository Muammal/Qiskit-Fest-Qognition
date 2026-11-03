# Stranded: Quantum Cognition Decision-Making & Survival Simulation

[![Integration Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)](#daily-integration--testing)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x-6929C4.svg)](https://qiskit.org/)
[![Status](https://img.shields.io/badge/Day%201%20Deliverable-Complete-success.svg)](#tech-c-deliverables)

> **"Can quantum probability explain why humans make counterintuitive survival decisions under extreme environmental stress?"**

**Stranded** is a quantum cognition survival simulation built for a week-long hackathon. An autonomous agent is stranded on a procedurally generated $40 \times 40$ wilderness island. Rather than using classical Markov Decision Processes (MDP) or deterministic utility maximization, the agent's mind is governed by **2-qubit quantum circuits** whose belief states exhibit non-commuting order effects, contextual interference, and hardware-modeled decoherence under physiological stress.

---

## Architecture & Team Boundaries

The project is structured around **3 tech + 2 product** roles with frozen interfaces and file-based hand-offs (`ROLES.md`):

```
stranded/
├── contracts.py              # Frozen interfaces + working stubs (Tech C)
├── requirements.txt          # Pinned dependency environment (Tech C)
├── main.py                   # Interactive CLI demo & benchmark runner (Tech C)
├── engine/                   # World generation, agents, survival loop (Tech C)
│   ├── world.py              # 40x40 procedural terrain & freshwater hydrology
│   ├── agent.py              # Physiological decay & lethal threshold checks
│   ├── events.py             # Stochastic environmental hazard generator
│   ├── simulation.py         # Turn-based loop emitting timeline.json
│   └── batch_runner.py       # Quantum vs Classical divergence benchmark
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
- **`EVENTS`**: `["storm", "injury", "find_food", "animal", "cold_night", "none"]`
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
| **Quantum Circuits** | Real | Genuine 2-qubit Qiskit 2.x circuits executed on Aer simulator and IBM Quantum superconducting hardware (`ibm_hardware` / fake backends). |
| **Decoherence Delay** | Real | Circuit execution with calibrated `qc.delay(...)` idling to measure real physical transmon qubit decoherence as a function of simulated stress. |
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
1. **Choose the Decision Mind**: `[⚛ 2-Qubit Quantum Mind]` vs `[🧠 Classical Baseline]`.
2. **Select Map & Seed**: Pick presets (*Archipelago*, *Arid Crag*, *Interference Lab*, *Heroic Haven*) or tune seed with numeric steppers / randomizer.
3. **Set Simulation Horizon**: Choose duration (`12`, `24`, `36`, or `48` steps).
4. **Launch**: Click `[🚀 LAUNCH SURVIVAL SIMULATION]`.
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
| `TAB` or `[📋 Action Log]` Button | **Toggle Chronological Action History Overlay** |
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

# Run complete 11-test integration test suite
python main.py --test
```

---

## Citations & Acknowledgments

1. **Busemeyer, J. R., & Wang, Z. (2014).** *Quantum model of cognition and decision.* Current Directions in Psychological Science.
2. **Pothos, E. M., & Busemeyer, J. R. (2022).** *Quantum cognition.* Annual Review of Psychology.
3. **Qiskit Development Team (2025).** *Qiskit: An Open-source Framework for Quantum Computing.*
4. **Bureau of Labor Statistics (BLS).** *American Time Use Survey (ATUS) Summary Tables.*

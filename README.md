# Quantum Cognition Simulation: Decision-Making & Multi-Scenario Survival

[![Integration Tests](https://img.shields.io/badge/tests-31%20passed-brightgreen.svg)](#daily-integration--testing)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x-6929C4.svg)](https://qiskit.org/)
[![Status](https://img.shields.io/badge/Multi--Scenario-Integrated-success.svg)](#architecture--team-boundaries)
[![Resolution](https://img.shields.io/badge/Resolution-1600%C3%97900%20(Fullscreen%20Scaled)-blueviolet.svg)](#fullscreen--interactive-controls)

> **"Can quantum probability explain why humans make counterintuitive survival decisions under extreme environmental stress?"**

**Quantum Cognition Simulation** is an interactive multi-scenario cognitive modeling sandbox built for an advanced quantum hackathon. The system simulates human decision-making under existential pressure by contrasting a **2-qubit quantum cognition circuit** (exhibiting non-commuting order effects, constructive interference, and physiological stress decoherence) against an empirical **classical rational baseline** (derived from American Time Use Survey utility priors).

---

## Visual Interface & Simulation Showcase

The application features a modern 1600×900 visualizer with dynamic vector graphics, atmospheric particle systems, aspect-scaled fullscreen scaling, and real-time cognitive telemetry.

### 1. Scenario Selection Hub (`Screen 0`)
The initial screen presented on launch allows players to choose their survival environment: **Island Wilderness** or **Volcano Evacuation**. Features interactive hover glows, metadata pill badges, and direct keyboard navigation (`[1]` / `[2]`).

![Scenario Selection Hub](docs/images/01_event_choice_hub.png)

---

### 2. Scenario Configuration & Seed Hub (`Screen 1`)
An interactive pre-flight dashboard equipped with real-time procedural minimap generation, seed steppers (±1, ±10, ±100, randomize), cognitive architecture toggles (**2-Qubit Quantum Mind** vs **Classical Rational Mind**), scenario presets, and configurable simulation horizons (12, 24, 36 steps).

![Scenario Configuration & Seed Hub](docs/images/02_home_configuration.png)

---

### 3. Island Wilderness Survival Simulation (`Screen 2 - Island Mode`)
Real-time 40×40 procedural island simulation. Features animated survival agent movement (smooth lerp interpolation with idle bobbing), vital physiological telemetry bars (hunger, thirst, warmth, energy, safety, morale), quantum probability breakdown, inventory tracking, and dynamic weather particle effects.

![Island Wilderness Survival](docs/images/03_island_survival_sim.png)

---

### 4. Volcano Eruption Evacuation Simulation (`Screen 2 - Volcano Mode`)
Calibrated 40×40 volcanic topography with active central caldera, dynamic seismic tremors, lava meanders, fast pyroclastic density currents (PDCs), toxic ash fallout, dynamic hazard risk zoning (Safe / Caution / Danger), and BFS shortest-path evacuation paths to coastal assembly zones.

![Volcano Eruption Evacuation](docs/images/04_volcano_evacuation_sim.png)

---

### 5. Mission Debrief & Comparative Analysis (`Debrief Modal`)
End-of-event telemetry modal summarizing the agent's survival outcome, cause of death (if fatal), full step-by-step decision trajectory, and quantum vs classical cognitive divergence with instant replay capabilities.

![Mission Debrief Modal](docs/images/05_mission_debrief.png)

---

## Dual Simulation Scenarios

Players can explore two fundamentally distinct environmental and psychological challenges:

### 🏝️ Scenario A: Island Wilderness Survival
- **Procedural Topography**: Unique 40×40 archipelago generated from a procedural seed with organic coastline harmonics, dense pine forests, freshwater springs, and alpine snowcaps.
- **Resource Economy**: Full survival loop including wood harvesting, food foraging, shelter construction, and hydration management.
- **Stochastic Environment**: Dynamic weather transitions (Markov rain, maritime storms, freezing nights) and territorial wildlife encounters (wild boars).
- **Quantum Mechanics**: Superposition exploration walks across uncharted land and belief interference under cold exposure.

### 🌋 Scenario B: Volcano Eruption Evacuation
- **Calibrated Geography**: Fixed 40×40 volcanic island featuring a central volcanic crater, radial drainage valleys, and designated coastal assembly points (250m per tile scale).
- **Hazard Clock**: Seeded hidden unrest, precursory tremors, sulfur gas plumes, explosive eruptions, lava flows, and lethal pyroclastic surges.
- **Emergency Routing**: Dynamic evacuation zoning with automated BFS pathfinding guiding the agent away from danger zones toward clean water springs and rescue points.
- **Quantum Mechanics**: Order effects under seismic warnings (e.g. tremor then gas plume vs gas plume then tremor) and rapid threat-induced decoherence.

---

## Architecture & Codebase Layout

The project enforces clean separation between the shared physics/world engine, cognitive models, frozen contracts, and frontend visualizers:

```
QWC/
├── contracts.py                  # Frozen interfaces, state validation & heuristic stubs
├── requirements.txt              # Pinned dependency environment (pygame-ce, qiskit, pytest)
├── main.py                       # Unified entrypoint (GUI, CLI demo, batch benchmark, tests)
├── test_contracts_and_engine.py  # Comprehensive integration test suite (31 tests)
├── timeline.json                 # Standardized simulation run output schema
├── docs/                         # Theory, mathematical models & assets
│   ├── images/                   # High-resolution screenshots of the UI and simulation
│   │   ├── 01_event_choice_hub.png
│   │   ├── 02_home_configuration.png
│   │   ├── 03_island_survival_sim.png
│   │   ├── 04_volcano_evacuation_sim.png
│   │   └── 05_mission_debrief.png
│   ├── VOLCANO_MODEL.md          # Volcanic hazard assumptions, constants & JSON schema
│   ├── 01_THEORY_AND_ARCHITECTURAL_FOUNDATIONS.md
│   └── 03_CODEBASE_IMPLEMENTATION_AND_MODULES.md
├── engine/                       # World, volcano, agents & simulation engine
│   ├── world.py                  # Dual-scenario map generator (procedural island & fixed volcano)
│   ├── volcano.py                # Hazard model (unrest, lava, PDCs, ash fallout)
│   ├── agent.py                  # Physiological state, needs decay, lethal thresholds & movement
│   ├── events.py                 # Environmental weather & contextual activity triggers
│   ├── simulation.py             # Shared simulation loop emitting timeline.json
│   ├── batch_runner.py           # Multi-seed batch comparison & demo curation
│   └── gui.py                    # 1600x900 interactive Pygame UI with vector graphics & particles
└── demo-pack/                    # Curated signature runs for frontend replay
    ├── run_01_heroic_survival.json
    ├── run_02_dramatic_death.json
    ├── run_03_order_effect_quantum.json
    ├── run_04_order_effect_classical.json
    └── run_05_stress_decoherence.json
```

---

## Frozen Contracts (`contracts.py`)

All cognitive decision engines plug into the strict interface defined in `contracts.py`:

### Primitive Constants
- **`ACTIONS`**: `["forage", "drink", "build_shelter", "rest", "explore", "craft", "hide"]`
- **`EVENTS`**: `["storm", "injury", "find_food", "animal", "cold_night", "none", "tremor", "gas_plume", "eruption", "ash_fall"]`
- **`TILE_TYPES`**: `{0: "water", 1: "plains", 2: "forest", 3: "mountain", 4: "shelter"}`

### Interface Signatures
```python
def get_prior(state: dict) -> dict:
    """Baseline habit distribution derived from physiological needs and ATUS tables."""

def classical_decide(state: dict) -> dict:
    """Rational classical decision baseline (deterministic prior utility argmax)."""

def quantum_decide(state: dict) -> dict:
    """2-Qubit quantum cognition decision engine (Qiskit 2.x)."""

def explore_step(pos: list, world: Any, mode: str = "quantum") -> list:
    """Discrete step generator: quantum walk superposition spread vs classical Brownian walk."""
```

### Standardized Decision Schema
Every step output adheres strictly to:
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
Classical Bayesian models assume events commute:
$$P(A \cap B) = P(B \cap A)$$

In human cognition under crisis, mental operators do not commute ($[U_A, U_B] \neq 0$). Experiencing an **injury followed by a storm** collapses the agent's belief state into defensive constructive interference favoring `hide` and `build_shelter`. Conversely, experiencing a **storm followed by an injury** channels beliefs toward physical recuperation (`rest`).

### 2. Stress as Environmental Decoherence
In physics, open quantum systems undergo decoherence ($T_1$ relaxation and $T_2$ dephasing) when coupled to a thermal bath. In this simulation, critical physiological stress (dehydration, hypothermia, acute predator threat):
- Dampens cognitive interference patterns.
- Decays off-diagonal density matrix terms, collapsing the pure quantum state into a classical mixed distribution.
- Mechanistically replicates cognitive "tunnel vision" and survival panic.

---

## Quickstart & Launch Commands

### 1. Interactive Graphical Visualizer (Recommended)
Launch the full desktop application:
```bash
python main.py
```
This boots into the **Event Choice Hub**, where you can pick Island Survival or Volcano Evacuation, tweak seed/mind parameters, and run the real-time simulation.

### 2. Headless & CLI Execution Modes
```bash
# Launch GUI directly with specific parameters
python main.py --seed 42 --mind quantum --scenario island

# ASCII terminal replay demo
python main.py --demo --seed 101

# Multi-seed batch divergence benchmark (Quantum vs Classical)
python main.py --batch

# Regenerate curated demo-pack/ timelines
python main.py --curate

# Run the automated test suite
python main.py --test
```

---

## Fullscreen & Interactive Controls

| Screen | Control | Action |
|---|---|---|
| **Any Screen** | `F11` or `[Fullscreen]` Button | **Toggle Fullscreen / Windowed Mode** (with automatic aspect-ratio letterboxing) |
| **Event Choice Hub** | `[1]` / `[2]` | **Select Island Survival** (`1`) or **Volcano Evacuation** (`2`) |
| **Event Choice Hub** | Click on Card or Button | **Open Scenario Configuration** |
| **Configuration Hub** | `ENTER` or `SPACE` | **Launch Simulation** |
| **Configuration Hub** | `ESC` or `< Change Scenario` | **Return to Event Choice Hub** |
| **Simulation View** | `SPACE` | **Play / Pause** auto-stepping |
| **Simulation View** | `RIGHT ARROW` or `N` | **Step Forward** single 2-hour turn |
| **Simulation View** | `Q` or `[Mind Toggle]` Button | **Toggle Mind Live** (Quantum Mind $\leftrightarrow$ Classical Baseline) |
| **Simulation View** | `1` / `2` / `3` or `[Speed]` Button | **Cycle Speed** (1.0× normal, 2.5× fast, 6.0× instant) |
| **Simulation View** | `E` | **Toggle Evacuation Map Overlay** (zones, assembly points, BFS paths) |
| **Simulation View** | `TAB` or `[Log]` Button | **Toggle Chronological Action History Overlay** |
| **Simulation View** | `R` | **Reset Current Run** |
| **Simulation View** | `ESC` or `H` or `[Menu]` Button | **Return to Home Configuration Screen** |

---

## Daily Integration Testing

The test suite validates contract integrity, terrain generation, physiological decay rates, volcanic hazards, agent movement, and GUI interaction:

```bash
python -m pytest test_contracts_and_engine.py -v
```
All **31 integration tests** pass consistently across platforms.

---

## Citations & Theoretical References

1. **Busemeyer, J. R., & Wang, Z. (2014).** *Quantum model of cognition and decision.* Current Directions in Psychological Science.
2. **Pothos, E. M., & Busemeyer, J. R. (2022).** *Quantum cognition.* Annual Review of Psychology.
3. **Qiskit Development Team (2025).** *Qiskit: An Open-source Framework for Quantum Computing.*
4. **Bureau of Labor Statistics (BLS).** *American Time Use Survey (ATUS) Summary Tables.*

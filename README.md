# Quantum Cognition Simulation: Decision-Making & Multi-Scenario Survival

[![Integration Tests](https://img.shields.io/badge/tests-142%20passed-brightgreen.svg)](#daily-integration--testing)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x-6929C4.svg)](https://qiskit.org/)
[![Status](https://img.shields.io/badge/Tech%20A%20%2B%20B%20%2B%20C-Unified-success.svg)](#unified-track-documentation-tech-a--tech-b--tech-c)
[![Resolution](https://img.shields.io/badge/Resolution-1600%C3%97900%20(Fullscreen%20Scaled)-blueviolet.svg)](#fullscreen--interactive-controls)

> **"Can quantum probability explain why humans make counterintuitive survival decisions under extreme environmental stress?"**

**Quantum Cognition Simulation** is an interactive multi-scenario cognitive modeling and physical hazard platform. The system simulates human decision-making under existential pressure by contrasting a **2-qubit quantum cognition architecture** (exhibiting non-commuting order effects, Tversky–Shafir interference, and physiological stress decoherence) against a **zero-coherence classical mixture control** and an empirical **classical rational baseline** (derived from American Time Use Survey utility priors and calibrated against 49 real-world volcanic/disaster datasets).

---

## Unified Track Documentation (Tech A + Tech B + Tech C)

Detailed technical documentation explaining how **Tech A**, **Tech B**, and **Tech C** work both **separately** and **together**:

- **[How Tech A, Tech B, and Tech C Work Together & Separately (`docs/TECH_A_B_C_INTEGRATION.md`)](docs/TECH_A_B_C_INTEGRATION.md)** — Complete end-to-end architecture, frozen `contracts.py` boundary, step-by-step turn lifecycle, causal isolation guarantees, and 3-way cognitive benchmarking.
- **[Tech A: 2-Qubit Quantum Cognitive Architecture (`docs/TECH_A_QUANTUM_MIND.md`)](docs/TECH_A_QUANTUM_MIND.md)** — Density-matrix belief tracking, non-commuting $R_y(\theta)R_z(\phi)$ event gates, projective collapse, phase-damping decoherence under stress, deliberation unitary $U(q_S, q_D, \eta)$, and Qiskit circuits (`mind/`).
- **[Tech B: Empirical Disaster Calibration, Classical Priors & Physics Framework (`docs/TECH_B_PHYSICS_AND_PRIORS.md`)](docs/TECH_B_PHYSICS_AND_PRIORS.md)** — 49 empirical disaster datasets (anchored on the April 2021 La Soufrière eruption on St. Vincent), ATUS classical utility priors, and the 14-domain unit-checked (`pint`) `stranded_physics/` framework.
- **[Tech C: World Generation, Volcanic Hazard Engine, Physiological Agent & GUI (`docs/TECH_C_ENGINE_WORLD_AND_GUI.md`)](docs/TECH_C_ENGINE_WORLD_AND_GUI.md)** — Dual-scenario $40 \times 40$ world generator, priority-flood drainage, Tobler hiking Dijkstra routing, active vs. deposited PDC/lahar/surge hazards, physiological agent, and 1600×900 Pygame visualizer (`engine/`).

---

## Visual Interface & Simulation Showcase

The application features an engineered 1600×900 research & tactical visualizer with dynamic relief shading, atmospheric particle systems, aspect-scaled fullscreen rendering, and real-time cognitive telemetry.

### 1. Scenario Selection Hub (`Screen 0`)
The initial screen presented on launch allows users to choose their survival environment: **Island Wilderness** or **Volcano Evacuation**. Features interactive hover states, metadata pill badges, and direct keyboard navigation (`[1]` / `[2]`).

![Scenario Selection Hub](docs/images/01_event_choice_hub.png)

---

### 2. Scenario Configuration & Seed Hub (`Screen 1`)
An interactive pre-flight dashboard equipped with real-time procedural minimap generation, seed steppers (±1, ±10, ±100, randomize), cognitive architecture toggles (**2-Qubit Quantum Mind** vs **Classical Rational Mind**), scenario presets, and configurable simulation horizons (12, 24, 36, 48 steps).

![Scenario Configuration & Seed Hub](docs/images/02_home_configuration.png)

---

### 3. Island Wilderness Survival Simulation (`Screen 2 - Island Mode`)
Real-time 40×40 procedural island simulation. Features animated survival agent movement (smooth lerp interpolation with idle bobbing), vital physiological telemetry bars (hunger, thirst, warmth, energy, safety, morale), quantum probability breakdown, inventory tracking, and dynamic weather particle effects.

![Island Wilderness Survival](docs/images/03_island_survival_sim.png)

---

### 4. Volcano Eruption Evacuation Simulation (`Screen 2 - Volcano Mode`)
Calibrated 40×40 volcanic topography with active central caldera, priority-flood drainage channels, dynamic seismic tremors, steepest-descent lava flows, valley-confined pyroclastic density currents (PDCs), peripheral thermal surges, rain-reactivated lahars, wind-advected ash fallout, hazard risk zoning (Safe / Caution / Danger), and Tobler least-time evacuation paths to coastal assembly zones.

![Volcano Eruption Evacuation](docs/images/04_volcano_evacuation_sim.png)

---

### 5. Mission Debrief & Comparative Analysis (`Debrief Modal`)
End-of-event telemetry modal summarizing the agent's survival outcome, cause of death (if fatal), stress & decoherence metrics, and instant replay or mind-switching capabilities.

![Mission Debrief Modal](docs/images/05_mission_debrief.png)

---

## Dual Simulation Scenarios

Users can explore two distinct environmental and psychological challenges:

### 🏝️ Scenario A: Island Wilderness Survival
- **Procedural Topography**: Unique 40×40 archipelago generated from a procedural seed with organic coastline harmonics, dense pine forests, freshwater springs, and alpine ridges.
- **Resource Economy**: Full survival loop including wood harvesting, food foraging, shelter construction, and hydration management.
- **Stochastic Environment**: Dynamic weather transitions (Markov rain, maritime storms, freezing nights) and wildlife encounters.
- **Quantum Mechanics**: Superposition exploration walks across uncharted land and belief interference under cold exposure.

### 🌋 Scenario B: Volcano Eruption Evacuation
- **Calibrated Geography**: Fixed 40×40 volcanic island (`250m` per tile scale) featuring a ~1000m central volcanic crater, priority-flood radial drainage valleys, clean springs, and two separated coastal assembly points.
- **Coupled Hazard Clock**: Seeded hidden unrest, precursory tremors, sulfur gas plumes, explosive eruptions, steepest-descent lava flows, active vs. deposited PDCs, dilute thermal surges, rain-reactivated lahars, and anisotropic wind-advected ash grids.
- **Tobler Emergency Routing**: Dynamic evacuation zoning with automated Dijkstra least-time pathfinding (using Tobler's hiking function over slope, vegetation, and ash load) guiding the agent away from danger zones toward clean water springs and rescue assembly points.
- **Quantum Mechanics**: Order effects under seismic warnings (`tremor` $\to$ `gas_plume` vs. `gas_plume` $\to$ `tremor`), disjunction interference under ambiguity, and stress-induced phase damping ($\lambda$).

---

## Architecture & Codebase Layout

```
QWC/
├── contracts.py                  # Frozen interfaces, state validation & ATUS classical baseline
├── requirements.txt              # Core dependencies (pygame-ce, qiskit, qiskit-aer, numpy, pytest)
├── requirements-physics.txt      # Physics track dependencies (pint, numpy, pytest)
├── main.py                       # Unified entrypoint (GUI, CLI demo, batch benchmark, tests)
├── test_contracts_and_engine.py  # Tech C + integration test suite (62 tests)
├── mind/                         # Tech A: 2-Qubit Quantum Cognitive Architecture
│   ├── model.py                  # Deliberation unitary U(q_S, q_D, eta) & Tversky-Shafir calibration
│   ├── belief.py                 # Density-matrix belief state, Ry*Rz event gates & collapse
│   ├── decoherence.py            # Stress -> phase-damping channel E_lambda(rho)
│   ├── quantum_mind.py           # quantum_decide, classical_mixture_decide & reflex layer
│   ├── circuits.py               # Gate-level Qiskit circuits transpiled for FakeTorino
│   ├── experiments/              # Validation scripts & figure generators
│   └── tests/                    # Tech A unit & circuit test suite (37 tests)
├── stranded_physics/             # Tech B: Verification-First 14-Domain Physics Framework
│   ├── core/                     # Pint unit registry, FieldStore, Parameter, verdicts & 43 tests
│   ├── domains/                  # 14 self-contained physical hazard domains (terrain, pdc, tephra, etc.)
│   ├── packs/                    # Topological ScenarioPack (.npz) builder & SHA-256 verification
│   ├── runtime/                  # Causal perceive(), AgentBody & PackSimulation
│   ├── catalog.py                # Automated parameter & provenance catalog builder
│   └── gates.py                  # Pre-registered verification & validation gate runner
├── disaster_data/                # Tech B: 49 Curated Real-World Volcano & Weather Datasets
│   ├── REPORT.md                 # Empirical calibration report (2021 La Soufrière St. Vincent, etc.)
│   └── manifest.json             # SHA-256 dataset provenance manifest
├── engine/                       # Tech C: World, Volcano, Agent, Loop & Interactive Visualizer
│   ├── world.py                  # Dual-scenario DEM, priority-flood drainage & Tobler Dijkstra paths
│   ├── volcano.py                # Seeded wind, ash grid, active PDC/lahar, surge & lava model
│   ├── agent.py                  # Physiology, Tobler walking budget, ration eating & fatal checks
│   ├── events.py                 # Markov weather & activity-linked event generator
│   ├── simulation.py             # Turn-based simulation loop emitting timeline.json
│   ├── batch_runner.py           # 3-model batch comparison & demo curation
│   ├── gui.py                    # 1600x900 interactive Pygame Research & Tactical Visualizer
│   ├── gui_map.py                # Auxiliary relief & hazard map renderer
│   └── gui_panels.py             # Auxiliary panel & modal helpers
├── docs/                         # Architecture guides, theoretical models & screenshots
│   ├── TECH_A_B_C_INTEGRATION.md # How Tech A, Tech B, and Tech C work together & separately
│   ├── TECH_A_QUANTUM_MIND.md    # Tech A standalone & mathematical documentation
│   ├── TECH_B_PHYSICS_AND_PRIORS.md # Tech B empirical data, priors & physics documentation
│   ├── TECH_C_ENGINE_WORLD_AND_GUI.md # Tech C world, volcano, agent & GUI documentation
│   ├── VOLCANO_MODEL.md          # Volcanic hazard assumptions, constants & JSON schema
│   ├── tech-a/                   # Detailed Stage 1-9 Tech A derivation notes & figures
│   └── images/                   # High-resolution screenshots of the UI and simulation
└── demo-pack/                    # Curated signature runs & Tech A validation JSONs
```

---

## Quickstart & Launch Commands

### 1. Interactive Graphical Visualizer (Recommended)
Launch the full 1600×900 desktop application:
```bash
python main.py
```
This boots into the **Event Choice Hub**, where you can pick **Island Wilderness Survival** or **Volcano Eruption Evacuation**, configure seed and cognitive architecture parameters, and run the real-time simulation.

### 2. Headless & CLI Execution Modes
```bash
# Launch GUI directly into a specific scenario and seed
python main.py --seed 42 --mind quantum --scenario volcano

# ASCII terminal live survival run
python main.py --demo --seed 101 --mind quantum --scenario volcano

# Multi-seed batch comparison (Quantum vs Classical Mixture vs Classical Rational)
python main.py --batch

# Regenerate curated demo-pack/ timelines
python main.py --curate

# Run the integration test suite
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
| **Simulation View** | `E` | **Toggle Evacuation Map Overlay** (zones, assembly points, Dijkstra paths) |
| **Simulation View** | `TAB` or `[Action Log]` Button | **Toggle Chronological Action History Overlay** (mouse wheel scrolls) |
| **Simulation View** | `R` | **Reset Current Run** |
| **Simulation View** | `ESC` or `H` or `[Menu]` Button | **Return to Home Configuration Screen** |

---

## Daily Integration & Verification Testing

Run the unified test suite across **Tech A**, **Tech B**, and **Tech C**:

```bash
python -m pytest test_contracts_and_engine.py mind/tests stranded_physics/core -v
```

---

## Citations & Theoretical References

1. **Busemeyer, J. R., & Bruza, P. D. (2012).** *Quantum Models of Cognition and Decision.* Cambridge University Press.
2. **Pothos, E. M., & Busemeyer, J. R. (2022).** *Quantum cognition.* Annual Review of Psychology, 73, 749–778.
3. **Tversky, A., & Shafir, E. (1992).** *The disjunction effect in choice under uncertainty.* Psychological Science, 3(5), 305–309.
4. **Tobler, W. (1993).** *Three Presentations on Geographical Analysis and Modeling.* NCGIA Technical Report 93-1.
5. **Bureau of Labor Statistics (BLS).** *American Time Use Survey (ATUS) Summary Tables.*

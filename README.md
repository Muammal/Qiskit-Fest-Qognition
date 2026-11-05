# Quantum Cognition Simulation: Decision-Making & Multi-Scenario Survival

[![Integration Tests](https://img.shields.io/badge/tests-158%20passed-brightgreen.svg)](#daily-integration--verification-testing)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x-6929C4.svg)](https://qiskit.org/)
[![Status](https://img.shields.io/badge/Tech%20A%20%2B%20B%20%2B%20C%20%2B%20D-Unified-success.svg)](#unified-track-documentation-tech-a--tech-b--tech-c--product-d)
[![Resolution](https://img.shields.io/badge/Resolution-1600%C3%97900%20(Fullscreen%20Scaled)-blueviolet.svg)](#fullscreen--interactive-controls)

> **"Can quantum probability explain why humans make counterintuitive survival decisions under extreme environmental stress?"**

> **Start here:** the project notebook, [`notebooks/stranded_quantum_cognition.ipynb`](notebooks/stranded_quantum_cognition.ipynb), states what is real, what is a model, and where this falls short. Engine results are in [`workboard/ENGINE_STATUS.md`](workboard/ENGINE_STATUS.md).

**Quantum Cognition Simulation** is an interactive multi-scenario cognitive modeling and physical hazard platform. The system simulates human decision-making under existential pressure by contrasting a **2-qubit quantum cognition architecture**—alongside **6 quantum cognition models adapted from published papers and open-source code** (exhibiting non-commuting order effects, Tversky–Shafir interference, Belief Entropy QLBN, Busemeyer dynamic Hamiltonians, and Lindblad open-system decoherence)—against a **zero-coherence classical mixture control ($\lambda=1$)** and an empirical **classical rational baseline** (derived from Bureau of Labor Statistics American Time Use Survey utility priors and calibrated against 49 real-world volcanic/disaster datasets).

---

## Unified Track Documentation (Tech A + Tech B + Tech C + Product D)

Detailed technical documentation explaining how **Tech A**, **Tech B**, **Tech C**, and **Product D** work both **separately** and **together**:

- **[Full System Report (`docs/FULL_SYSTEM_REPORT.md`)](docs/FULL_SYSTEM_REPORT.md)** — Master technical report covering end-to-end architecture, complete Tech B status audit (14/14 record checks pass (settings and data files load; the physics is not tested against reality)), Clash of Clans / Hay Day UI design, and production verification.
- **[Full System Presentation Slide Deck (`docs/PRESENTATION_SLIDES.md`)](docs/PRESENTATION_SLIDES.md)** — 14-slide presentation deck with Mermaid diagrams, equations, screenshots, and live demo guide.
- **[New Implementations & Published Quantum Cognition Models Report (`docs/NEW_IMPLEMENTATIONS_REPORT.md`)](docs/NEW_IMPLEMENTATIONS_REPORT.md)** — Complete report of all newly implemented features and the **6 quantum cognition models adapted from published papers** (`jbusemey/ChoiceModeling`, `Insight137/insight137-eap`, `hwilner/open-system-decision-dynamics`, `ljaustc/QRL`, `WileQ/QCog`, `robertcprice/nQPU`).
- **[How Tech A, Tech B, Tech C, and Product D Work Together & Separately (`docs/TECH_A_B_C_INTEGRATION.md`)](docs/TECH_A_B_C_INTEGRATION.md)** — Complete end-to-end architecture, frozen `contracts.py` boundary, step-by-step turn lifecycle, causal isolation guarantees, and 3-way cognitive benchmarking.
- **[Tech A: 2-Qubit Quantum Cognitive Architecture (`docs/TECH_A_QUANTUM_MIND.md`)](docs/TECH_A_QUANTUM_MIND.md)** — Density-matrix belief tracking, non-commuting $R_y(\theta)R_z(\phi)$ event gates, projective collapse, Kraus & Lindblad decoherence under stress, deliberation unitary $U(q_S, q_D, \eta)$, 6 published cognition models (`mind/cognition_models.py`), and Qiskit circuits (`mind/`).
- **[Tech B: Empirical Disaster Calibration, Classical Priors & Physics Framework (`docs/TECH_B_PHYSICS_AND_PRIORS.md`)](docs/TECH_B_PHYSICS_AND_PRIORS.md)** — 49 empirical disaster datasets (anchored on the April 2021 La Soufrière eruption on St. Vincent), 9 simplified stand-in solvers (`stranded_physics/scenarios.py`), BLS ATUS priors (`data/priors.json`), and 4-direction Grover-coined Discrete-Time Quantum Walk (`contracts.explore_step`).
- **[Tech C: World Generation, Volcanic Hazard Engine, Physiological Agent & GUI (`docs/TECH_C_ENGINE_WORLD_AND_GUI.md`)](docs/TECH_C_ENGINE_WORLD_AND_GUI.md)** — Dual-scenario $40 \times 40$ world generator, priority-flood drainage, Tobler hiking Dijkstra routing, active vs. deposited PDC/lahar/surge hazards, counterfactual `scripted_events`, 1600×900 Pygame visualizer (`engine/gui.py`), and Product D Web Replay Inspector (`site/index.html`).

---

## Visual Interface & Simulation Showcase

The application features an engineered 1600×900 research & tactical visualizer with dynamic relief shading, atmospheric particle systems, aspect-scaled fullscreen rendering, and real-time cognitive telemetry.

### 1. Scenario Selection Hub (`Screen 0`)
The initial screen presented on launch allows users to choose their survival environment: **Island Wilderness** or **Volcano Evacuation**. Features interactive hover states, metadata pill badges, and direct keyboard navigation (`[1]` / `[2]`).

![Scenario Selection Hub](docs/images/01_event_choice_hub.png)

---

### 2. Scenario Configuration & Seed Hub (`Screen 1`)
An interactive pre-flight dashboard equipped with real-time procedural minimap generation, seed steppers (±1, ±10, ±100, randomize), 3-way cognitive architecture selector (**2-Qubit Quantum Mind** $\to$ **Classical Mixture ($\lambda=1$)** $\to$ **Classical Rational Mind**), scenario presets, and configurable simulation horizons (12, 24, 36, 48 steps).

![Scenario Configuration & Seed Hub](docs/images/02_home_configuration.png)

---

### 3. Island Wilderness Survival Simulation (`Screen 2 - Island Mode`)
Real-time 40×40 procedural island simulation. Features animated survival agent movement, vital physiological telemetry bars (hunger, thirst, warmth, energy, safety, morale), quantum probability breakdown, live quantum coherence & interference telemetry (`|x|`, `λ`, `ΔP`), inventory tracking, and dynamic weather particle effects.

![Island Wilderness Survival](docs/images/03_island_survival_sim.png)

---

### 4. Volcano Eruption Evacuation Simulation (`Screen 2 - Volcano Mode`)
Fictional 40×40 volcanic topography, with assumed rates, with active central caldera, priority-flood drainage channels, dynamic seismic tremors, steepest-descent lava flows, valley-confined pyroclastic density currents (PDCs), peripheral thermal surges, rain-reactivated lahars, wind-advected ash fallout, hazard risk zoning (Safe / Caution / Danger), and Tobler least-time evacuation paths to coastal assembly zones.

![Volcano Eruption Evacuation](docs/images/04_volcano_evacuation_sim.png)

---

### 5. Mission Debrief & Comparative Analysis (`Debrief Modal`)
End-of-event telemetry modal summarizing the agent's survival outcome, cause of death (if fatal), stress & decoherence metrics, and instant replay or mind-switching capabilities.

![Mission Debrief Modal](docs/images/05_mission_debrief.png)

---

## Architecture & Codebase Layout

```
QWC/
├── contracts.py                  # Frozen interfaces, Grover DTQW explore_step & rule-based classical baseline
├── data/priors.json              # ATUS reference hours, loaded but not used in decisions, & hand-set urgency boosts
├── requirements.txt              # Core dependencies (pygame-ce, qiskit, qiskit-aer, numpy, pytest)
├── requirements-physics.txt      # Physics track dependencies (pint, numpy, pytest)
├── main.py                       # Unified entrypoint (GUI, CLI demo, batch benchmark, physics engine)
├── test_contracts_and_engine.py  # Tech C + integration test suite (66 tests)
├── mind/                         # Tech A: 2-Qubit Quantum Cognitive Architecture
│   ├── model.py                  # Deliberation unitary U(q_S, q_D, eta) & Tversky-Shafir calibration
│   ├── cognition_models.py       # 6 quantum cognition models adapted from published papers from GitHub
│   ├── belief.py                 # Density-matrix belief state, Ry*Rz event gates & collapse
│   ├── decoherence.py            # Stress -> Kraus phase-damping & GKSL Lindblad master equation
│   ├── quantum_mind.py           # quantum_decide (with selectable cognition_model) & classical_mixture
│   ├── circuits.py               # Gate-level Qiskit circuits (with mid-circuit collapse & Lüders)
│   ├── experiments/              # Validation scripts (with 6-paper library_cross_check) & figures
│   └── tests/                    # Tech A unit, Qiskit & published model test suite (48 tests)
├── stranded_physics/             # Tech B: Verification-First 14-Domain Physics Framework
│   ├── scenarios.py              # 9 concrete T1 domain solvers for April 2021 La Soufrière eruption
│   ├── core/                     # Pint unit registry, FieldStore, Parameter, verdicts & 44 tests
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
│   ├── events.py                 # Markov weather, activity events & scripted_events counterfactuals
│   ├── simulation.py             # Turn-based simulation loop emitting timeline.json
│   ├── batch_runner.py           # 3-model batch comparison & demo curation
│   ├── gui.py                    # 1600x900 interactive Pygame Research & Tactical Visualizer
│   ├── gui_map.py                # Auxiliary relief & hazard map renderer
│   └── gui_panels.py             # Auxiliary panel & modal helpers
├── site/                         # Product D: Client-Side Web Replay & Quantum Cognition Inspector
│   └── index.html                # HTML5 40x40 replay canvas, Bloch circle & 6-model live inspector
├── docs/                         # Architecture guides, theoretical models & screenshots
│   ├── NEW_IMPLEMENTATIONS_REPORT.md # Comprehensive report of all new implementations & 6 models
│   ├── TECH_A_B_C_INTEGRATION.md # How Tech A, Tech B, Tech C & Product D work together & separately
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

### 2. Headless, Physics Pack & CLI Execution Modes
```bash
# Launch GUI directly into a specific scenario and seed
python main.py --seed 42 --mind quantum --scenario volcano

# ASCII terminal live survival run (Legacy Engine or T1 St. Vincent Physics Pack)
python main.py --demo --seed 101 --mind quantum --scenario volcano --engine legacy
python main.py --demo --seed 101 --mind quantum --engine physics

# Multi-seed batch comparison (Quantum vs Classical Mixture vs Classical Rational)
python main.py --batch

# Regenerate curated demo-pack/ timelines
python main.py --curate

# Open Product D Web Replay & Quantum Inspector in browser
start site/index.html
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
| **Simulation View** | `Q` or `[Mind Toggle]` Button | **Cycle Mind Live** (`Quantum` $\to$ `Classical Mixture` $\to$ `Classical Rational`) |
| **Simulation View** | `[Speed]` Button | **Cycle Speed** (0.5×, 1×, 2×, 4×) |
| **Simulation View** | `E` | **Toggle Evacuation Map Overlay** (zones, assembly points, Dijkstra paths) |
| **Simulation View** | `TAB` or `[Action Log]` Button | **Toggle Chronological Action History Overlay** (mouse wheel scrolls) |
| **Simulation View** | `R` | **Reset Current Run** |
| **Simulation View** | `ESC` or `H` or `[Menu]` Button | **Return to Home Configuration Screen** |

---

## Daily Integration & Verification Testing

Run the unified 158-test suite (`158 passed`) across **Tech A**, **Tech B**, and **Tech C**:

```powershell
$env:SDL_VIDEODRIVER="dummy"; python -m pytest test_contracts_and_engine.py mind/tests stranded_physics/core -q
```

---

## Citations & Theoretical References

1. **Busemeyer, J. R., & Bruza, P. D. (2012).** *Quantum Models of Cognition and Decision.* Cambridge University Press.
2. **Pothos, E. M., & Busemeyer, J. R. (2009).** *A quantum probability explanation for violations of 'rational' decision theory.* Proceedings of the Royal Society B, 276(1665), 2171–2178. (`jbusemey/ChoiceModeling`)
3. **Tversky, A., & Shafir, E. (1992).** *The disjunction effect in choice under uncertainty.* Psychological Science, 3(5), 305–309.
4. **Huang, Z., Yang, L., & Jiang, W. (2019).** *Uncertainty measurement with belief entropy on quantum model for decision making.* Applied Mathematics and Computation, 347, 417–428. (`Insight137/insight137-eap`)
5. **Moreira, C., & Wichert, A. (2016).** *Quantum-Like Bayesian Networks for modeling decision making.* Frontiers in Psychology, 7, 11.
6. **Broekaert, J., Busemeyer, J. R., & Pothos, E. M. (2020).** *The disjunction effect in two-stage simulated gambles: An experimental study and comparison of a heuristic, Markov, and quantum model.* Cognitive Psychology, 117, 101262. (`hwilner/open-system-decision-dynamics`)
7. **Yearsley, J. M., & Busemeyer, J. R. (2016).** *Quantum cognition and decision theories: A tutorial.* Journal of Mathematical Psychology, 74, 99–116.
8. **Li, J.-A., Dong, D., Wei, Z., Liu, Y., Pan, Y., Nori, F., & Zhang, X. (2020).** *Quantum reinforcement learning during human decision-making.* Nature Human Behaviour, 4, 294–307. (`ljaustc/QRL`)
9. **Wang, Z., Solloway, T., Shiffrin, R. M., & Busemeyer, J. R. (2014).** *Context effects produced by question orders reveal quantum nature of human judgments.* PNAS, 111(26), 9431–9436. (`WileQ/QCog`)
10. **Trueblood, J. S., & Busemeyer, J. R. (2011).** *A quantum probability account of order effects in inference.* Cognitive Science, 35(8), 1518–1552. (`robertcprice/nQPU`)
11. **Tobler, W. (1993).** *Three Presentations on Geographical Analysis and Modeling.* NCGIA Technical Report 93-1.
12. **Bureau of Labor Statistics (BLS).** *American Time Use Survey (ATUS) Summary Tables.*

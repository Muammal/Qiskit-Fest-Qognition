# Qognition: Decision-Making & Multi-Scenario Evacuation Survival

[![CI](https://github.com/Muammal/Qiskit-Fest-Qognition/actions/workflows/ci.yml/badge.svg)](https://github.com/Muammal/Qiskit-Fest-Qognition/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

> **"Can quantum probability explain why humans make counterintuitive evacuation and survival decisions under extreme environmental stress — and how can we use it to improve real-life evacuation survival rates?"**

> **Start here:** the project notebook, [`notebooks/stranded_quantum_cognition.ipynb`](notebooks/stranded_quantum_cognition.ipynb), explains the model, its evidence, and next steps. Engine results are in [`workboard/ENGINE_STATUS.md`](workboard/ENGINE_STATUS.md).

**Qognition** is an interactive multi-scenario cognitive modeling, crowd evacuation, and physical hazard platform. The system simulates human decision-making under existential pressure across **five evacuation and survival scenarios** (**Island Wilderness**, **Volcano Eruption**, **RMS Titanic 1912**, **Pompeii AD 79**, and **Waterloo Pool Chlorine Leak**) plus an **Interactive Scenario Builder**. It contrasts a **2-qubit quantum cognition architecture**—alongside **6 quantum cognition models adapted from published papers and open-source code** (exhibiting non-commuting order effects, Tversky–Shafir disjunction interference, Belief Entropy QLBN, Busemeyer dynamic Hamiltonians, and Lindblad open-system decoherence)—against a **zero-coherence classical mixture control ($\lambda=1$)** and a **classical rational baseline**.

---

## Five Evacuation & Survival Scenarios + Custom Scenario Builder

Results are in the generated table [`docs/results/SCENARIO_NUMBERS.md`](docs/results/SCENARIO_NUMBERS.md), written by `python tools/make_readme_numbers.py`. Numbers are kept there rather than typed here so they cannot go stale. They are model runs, not predictions.

| # | Scenario | Scale & Horizon | Physical Hazard Engine | Real-Life Evacuation & Cognitive Insight |
|---|---|---|---|---|
| **1** | **Island Wilderness (`island`)** | 1 agent, 36 steps (72 h) | 40×40 DEM, Markov storms, exposure & dehydration | Shelter timing before storm hypothermia (a Grover walk for `explore` is available but off by default; default runs use a random walk) |
| **2** | **Volcano Evacuation (`volcano`)** | 1 agent (or multi-agent builder), 36 steps | Caldera DEM, active PDCs, surges, lahars, downwind ash & Tobler Dijkstra paths | Cue order effects: `Tremor → Gas` and `Gas → Tremor` give different $P(\text{protect})$ |
| **3** | **RMS Titanic 1912 (`titanic`)** | **2,208 agents** across 10 decks, 44 steps (5 min/step) | Progressive compartment flooding (`engine/flood.py`) & 20 lifeboats (`1,178` seats, Wormstedt schedule) | Models below-deck normalcy bias, and how the result moves with the cue translation |
| **4** | **Pompeii AD 79 (`pompeii`)** | **11,500 citizens** across households, 128 steps (15 min/step) | Plinian column, pumice accumulation, roof collapses & pyroclastic surges (`engine/eruption.py`) | Deaths depend strongly on the cue translation, so all four are reported |
| **5** | **Waterloo Pool Chlorine Leak (`waterloo`)** | **100 swimmers & staff**, 721 steps (10 sec/step) | 2D chlorine gas advection-diffusion plume (`engine/chlorine.py`) & EPA AEGL-1/2/3 thresholds | Compares exposure with and without a staff alarm, under each cue translation |
| **6** | **Scenario Builder (`stranded_physics/builder_screen.py`)** | Custom multi-person packs | Interactive terrain, hazard, and multi-agent placement editor | Build, save, and replay custom evacuation packs directly in the GUI (`[B]`) |

---

## Results and changes

- **[What changed and what came out (`docs/CHANGES_AND_RESULTS.md`)](docs/CHANGES_AND_RESULTS.md)**, including results that go against the paper, and suggested paper edits.
- [Human data, every row](docs/HUMAN_DATA_RESULTS.md), [lead-time sweep](docs/results/LEAD_TIME.md), [sensitivity](docs/results/SENSITIVITY.md), [pre-registered protocols](docs/protocols/README.md).

---

## Unified Track Documentation (Tech A + Tech B + Tech C + Product D)

Detailed technical documentation explaining how **Tech A**, **Tech B**, **Tech C**, and **Product D** work both **separately** and **together**:

- **[Full System Report (`docs/FULL_SYSTEM_REPORT.md`)](docs/FULL_SYSTEM_REPORT.md)** — Master technical report covering end-to-end architecture, complete Tech B status audit (14/14 record checks pass (settings and data files load; the physics is not tested against reality)), wood-and-parchment UI design, and production verification.
- **[Full System Presentation Slide Deck (`docs/PRESENTATION_SLIDES.md`)](docs/PRESENTATION_SLIDES.md)** — 14-slide presentation deck with Mermaid diagrams, equations, screenshots, and live demo guide.
- **[New Implementations & Published Quantum Cognition Models Report (`docs/NEW_IMPLEMENTATIONS_REPORT.md`)](docs/NEW_IMPLEMENTATIONS_REPORT.md)** — Complete report of all newly implemented features and the **6 quantum cognition models adapted from published papers** (`jbusemey/ChoiceModeling`, `Insight137/insight137-eap`, `hwilner/open-system-decision-dynamics`, `ljaustc/QRL`, `WileQ/QCog`, `robertcprice/nQPU`).
- **[How Tech A, Tech B, Tech C, and Product D Work Together & Separately (`docs/TECH_A_B_C_INTEGRATION.md`)](docs/TECH_A_B_C_INTEGRATION.md)** — Complete end-to-end architecture, frozen `contracts.py` boundary, step-by-step turn lifecycle, causal isolation guarantees, and 3-way cognitive benchmarking.
- **[Tech A: 2-Qubit Quantum Cognitive Architecture (`docs/TECH_A_QUANTUM_MIND.md`)](docs/TECH_A_QUANTUM_MIND.md)** — Density-matrix belief tracking, non-commuting $R_y$ and $R_x$ event gates, projective collapse, Kraus & Lindblad decoherence under stress, deliberation unitary $U(q_S, q_D, \eta)$, 6 published cognition models (`mind/cognition_models.py`), and Qiskit circuits (`mind/`).
- **[Tech B: Empirical Disaster Calibration, Classical Priors & Physics Framework (`docs/TECH_B_PHYSICS_AND_PRIORS.md`)](docs/TECH_B_PHYSICS_AND_PRIORS.md)** — 49 empirical disaster datasets (anchored on the April 2021 La Soufrière eruption on St. Vincent), 9 simplified stand-in solvers (`stranded_physics/scenarios.py`), ATUS reference hours that decisions do not use (`data/priors.json`), and 4-direction Grover-coined Discrete-Time Quantum Walk (`contracts.explore_step`, opt-in with `explore_walk="grover"`, off by default).
- **[Tech C: World Generation, Volcanic Hazard Engine, Physiological Agent & GUI (`docs/TECH_C_ENGINE_WORLD_AND_GUI.md`)](docs/TECH_C_ENGINE_WORLD_AND_GUI.md)** — Dual-scenario $40 \times 40$ world generator, priority-flood drainage, Tobler hiking Dijkstra routing, active vs. deposited PDC/lahar/surge hazards, counterfactual `scripted_events`, 1600×900 Pygame visualizer (`engine/gui.py`), and Product D Web Replay Inspector (`site/index.html`).

---

## Visual Interface & Simulation Showcase

The application lays out in 1600×900 logical units and renders text at the window's real resolution (`engine/hidpi.py`), so it stays sharp on a projector. A run ends in one debrief, with no mid-run cutscenes. All results shown are model output, not predictions.

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
├── contracts.py                  # Frozen interfaces, opt-in Grover explore_step & rule-based classical baseline
├── data/priors.json              # ATUS reference hours, loaded but not used in decisions, & hand-set urgency boosts
├── requirements.txt              # Core dependencies (pygame-ce, qiskit, qiskit-aer, numpy, pytest)
├── requirements-physics.txt      # Physics track dependencies (pint, numpy, pytest)
├── main.py                       # Unified entrypoint (GUI, CLI demo, batch benchmark, physics engine)
├── test_contracts_and_engine.py  # Tech C + integration test suite (66 tests)
├── mind/                         # Tech A: 2-Qubit Quantum Cognitive Architecture
│   ├── model.py                  # Deliberation unitary U(q_S, q_D, eta) & Tversky-Shafir calibration
│   ├── cognition_models.py       # 6 quantum cognition models adapted from published papers from GitHub
│   ├── belief.py                 # Density-matrix belief state, Ry and Rx event gates & collapse
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

## Install

You need Python 3.11 or newer.

```bash
git clone https://github.com/Muammal/Qiskit-Fest-Qognition.git
cd Qiskit-Fest-Qognition
python -m pip install -r requirements.txt -r requirements-physics.txt
python main.py
```

The gallery sims and the builder's starting points run straight away. Scenarios built on real records also need the 230 MB data pack: `python tools/fetch_artifacts.py`.

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

## Make, Share and Open Sims

Build a scenario from a ready-made starting point, then save it as a `.qsim` file that runs on any copy of the app. Open one by dropping it on the window, pasting a link, or browsing **Community**. Publish yours to the [community gallery](community/README.md) from the builder. Details, safety rules and limits are in [`docs/SIM_FILES.md`](docs/SIM_FILES.md).

```bash
python main.py --open community/sims/made_up_island_eruption.qsim
```

---

## End-of-Event Report

Every run ends in one debrief with the crucial details: survivors against deaths, key events, the paired run on the same seed, and the assumptions used. **Export Report** (or `K` in the debrief) writes an Excel workbook and a folder of CSVs to `exports/reports/`, with these tables:

| Table | Contents |
|---|---|
| Summary | Scenario, seed, mind, cue translation, totals and survival rate |
| Key events | First sign, first decision to evacuate, hazard onset, margin, seats used, causes of death, exposure |
| Timeline | Every step, end to end: event, action, needs, stress, P(danger), P(protect), λ, coherence, reason |
| Crowd over time | Everyone's status at every step (Titanic, Pompeii, Waterloo) |
| Groups | Outcomes by class or role, with history where a source gives it |
| Decisions | How often each action was chosen |
| Paired run | The other mind on the same seed |
| Assumptions | Cue translation, decision rule, dephasing and scope |

Without the GUI:

```bash
python main.py --report --scenario titanic --seed 42 --mind quantum
```

Reports are model output, not predictions.

---

## Fullscreen & Interactive Controls

| Screen | Control | Action |
|---|---|---|
| **Any Screen** | `F11` or `[Fullscreen]` Button | **Toggle Fullscreen / Windowed Mode** (with automatic aspect-ratio letterboxing) |
| **Event Choice Hub** | `[1]` / `[2]` / `[3]` / `[4]` / `[5]` | **Select Island** (`1`), **Volcano** (`2`), **Titanic** (`3`), **Pompeii** (`4`), or **Waterloo** (`5`) |
| **Event Choice Hub** | `B` or `[Build Scenario]` | **Open Interactive Scenario Builder** (`stranded_physics/builder_screen.py`) |
| **Event Choice Hub** | Click on Card or Button | **Open Scenario Configuration** |
| **Configuration Hub** | `ENTER` or `SPACE` | **Launch Simulation** |
| **Configuration Hub** | `ESC` or `< Change Scenario` | **Return to Event Choice Hub** |
| **Simulation View** | `SPACE` | **Play / Pause** auto-stepping |
| **Simulation View** | `RIGHT ARROW` or `N` | **Step Forward** single turn |
| **Simulation View** | `Q` or `[Mind Toggle]` Button | **Cycle Mind Live** (`Quantum` $\to$ `Classical Mixture` $\to$ `Classical Rational`) |
| **Simulation View** | `F` | **Follow Next Person / Role** (in crowd scenarios & custom builder packs) |
| **Simulation View** | `P` / `M` | **Toggle Split Panels** (`P`) or **Region Map** (`M` in Pompeii) |
| **Quantum panel** | `[Swap cues]` | **Order swap**: swaps the last two cues and shows the change in P(protect) |
| **Any Screen** | Drop a `.qsim` file on the window | **Open a sim** in the builder |
| **Scenario Builder** | `[Share]`, `[Undo]` or `Ctrl+Z` | **Export or publish a sim**, or step back |
| **Debrief** | `[Export Report]` or `K` | **Write the report** as Excel and CSV to `exports/reports/` |
| **Configuration Hub** | `A` / `B` / `C` / `D` buttons | **Cue translation** for Titanic, Pompeii and Waterloo. Each one is an assumption, and results move with it |
| **Simulation View** | `[Speed]` Button | **Cycle Speed** (0.5×, 1×, 2×, 4×) |
| **Simulation View** | `E` | **Toggle Evacuation Map Overlay** (zones, assembly points, Dijkstra paths) |
| **Simulation View** | `TAB` or `[Action Log]` Button | **Toggle Chronological Action History Overlay** (mouse wheel scrolls) |
| **Simulation View** | `R` | **Reset Current Run** |
| **Simulation View** | `ESC` or `H` or `[Menu]` Button | **Return to Home Configuration Screen** |

---

## Testing

Run the unified suite across **Tech A**, **Tech B**, **Tech C**, **Titanic**, **Pompeii**, and **Waterloo** (413 passed, 3 skipped on 6 November 2026; `test_ui_layout.py`, `test_report.py`, `test_simfile.py` and `mind/human_tests` add more):

```powershell
$env:SDL_VIDEODRIVER="dummy"; python -m pytest test_contracts_and_engine.py test_titanic.py test_pompeii.py test_waterloo.py mind/tests stranded_physics/core -q
```

---

## Contributing, Security and Licence

- [CONTRIBUTING.md](CONTRIBUTING.md) covers setup, checks and the rules for the science.
- [SECURITY.md](SECURITY.md) says how to report a problem.
- [community/REVIEW.md](community/REVIEW.md) says how published sims are reviewed.
- Code is licensed under [Apache-2.0](LICENSE). Community sims are licensed under [CC BY 4.0](community/LICENSE.txt). Third-party data in `disaster_data/` keeps its own terms, which aren't all confirmed. See [NOTICE](NOTICE).

Qognition is a research model. Its results are not predictions, and it must not be used to plan or make decisions in a real emergency.

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

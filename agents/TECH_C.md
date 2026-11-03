# Agent Specification: Tech C (World Generation, Engine & Integration)

## Overview & Role Mandate
**Role**: System Architect & Simulation Engine Lead  
**Code Ownership**: `engine/`, `contracts.py`, `requirements.txt`, `main.py`, `gui_island.py`, `test_contracts_and_engine.py`  
**Core Objective**: Build the 40x40 procedural wilderness island, implement the agent survival mechanics loop, maintain frozen contract stubs, orchestrate batch divergence benchmarks, provide the interactive Pygame GUI, and manage daily integration testing.

---

## Deliverables & Milestones

### 1. Frozen Interface & Contracts (`contracts.py`)
- Define canonical actions and events:
  - `ACTIONS = ["forage", "drink", "build_shelter", "rest", "explore", "craft", "hide"]`
  - `EVENTS = ["storm", "injury", "find_food", "animal", "cold_night", "none"]`
- Provide robust stubs returning valid synthetic telemetry so Tech A, Tech B, and Product D are never blocked.

### 2. Procedural World Generation (`engine/world.py`)
- Seeded $40 \times 40$ island generation with cellular automata / noise terrain.
- Hydrology: Coastlines, inland freshwater lakes, and river channels to allow realistic `drink` action execution.
- Biomes: Plains, forests (foraging/building), rocky mountains, and shelter building zones.

### 3. Agent Physiology & Hazards (`engine/agent.py`, `engine/events.py`)
- **Needs Metrics**: Hunger ($0 \to 1$), Thirst ($0 \to 1$), Warmth ($0 \to 1$), Energy ($0 \to 1$), Safety ($0 \to 1$), Morale ($0 \to 1$).
- **Lethal Checks**: Total dehydration (Thirst=1.0 for 24h) or starvation (Hunger=1.0 for 72h) triggers lethal failure.
- **Stress Mechanics**: Elevated needs and injury increase `stress` ($0 \to 1$), driving quantum decoherence in Tech A's mind circuit.
- **Environmental Hazard Generator**: Probabilistic weather events (severe storms, cold fronts) and predator encounters.

### 4. Turn-Based Simulation Loop (`engine/simulation.py`)
- Executes tick-by-tick simulation step calling either `quantum_decide()` or `classical_decide()`.
- Supports step callbacks for live UI streaming and headless batch evaluation.
- Outputs standardized `timeline.json` log documenting world state, agent position, needs, decisions, quantum measurement probabilities, and decision reasoning.

### 5. Interactive UI & Pygame Island (`gui_island.py`, `engine/gui.py`)
- 2D rendered island with player sprite, terrain textures, HUD telemetry bars, and decision dialogue.
- Unified launch architecture with Home Page screen:
  - Seed selection, map size, mind selection (`QUANTUM` vs `CLASSICAL`), hardware noise toggle, and step limits.
  - Fullscreen toggle, aspect-ratio scaling, and detailed end-of-sim recap screens.

### 6. Batch Runner & Divergence Suite (`engine/batch_runner.py`)
- Multi-run monte carlo simulation executing matched pairs of identical seeds across Quantum and Classical minds.
- Emits aggregate survival curves, death distributions, and action histograms for Tech B's divergence charts.

### 7. Daily Integration Discipline
- Executes the full integration test suite (`test_contracts_and_engine.py`) every evening to verify zero regression across branches.

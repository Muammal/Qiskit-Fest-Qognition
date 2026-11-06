# Progress

**Last updated: November 6, 2026.** Task-level status lives in [tasks.csv](tasks.csv).

## Where we are

| Track | Status | Details |
|---|---|---|
| **Tech A (`mind/`)** | **Built and tested** | 2-qubit deliberation unitary + **6 quantum cognition models adapted from published papers** (`mind/cognition_models.py`), Qiskit 2.x circuits, 48 passing tests |
| **Tech B (`stranded_physics/`, `disaster_data/`, `contracts.py`)** | **Verified with Data-v1 (`22 / 22 PASS`)** | 49 datasets registered in 14 category `datasets.toml` files, 20 Pint parameters in `params.toml`, 19 raw physics assets extracted from release `data-v1`, 9 stand-in solvers + physical domain solvers, Tobler locomotion, BLS ATUS `data/priors.json`, 4-direction Grover DTQW |
| **Tech C (`engine/`, `main.py`)** | **Built, verified & exported across 5 scenarios** | 5 Scenarios (`island`, `volcano`, `titanic`, `pompeii`, `waterloo`), counterfactual `scripted_events`, 3-mind selector, **1600×900 Clash / Hay Day Tactical UI**, Slow-Mo/Fast-Forward controls, and MP4 video / data exporters |
| **In-game scenario builder (`engine/builder.py`, `stranded_physics/builder_screen.py`)** | **Built** | See [ENTITIES.md](ENTITIES.md). In-GUI interactive level editor, custom hazard placement, and multi-agent pack simulation |
| **Real St Vincent engine (`stranded_physics/domains/`)** | **Built end to end with Data-v1 assets** | See [ENGINE_STATUS.md](ENGINE_STATUS.md). All 22 required physical gates PASS |
| **Product D (`site/index.html`)** | **Built with multi-scenario presets** | Client-side HTML5 40×40 replay canvas, Bloch circle & 6-model live Quantum Cognition Inspector |

## Verification Summary
- **Unified Pytest Suite**: `816 passed, 3 skipped` across the entire codebase (100% pass rate in 13 min 19 sec)
- **Physics Category Gates (`python -m stranded_physics.gates required`)**: `22 / 22 PASS` (recorded in [CLAIMS.md](CLAIMS.md))
- **Category Data & Parameter Catalog (`python -m stranded_physics.catalog`)**: 49 datasets and 20 Pint-checked parameters across 14 categories in [CATALOG.md](CATALOG.md)
- **Tech A Validation Suite (`python -m mind.experiments.validate`)**: `PASS` (`any_failed=False`)

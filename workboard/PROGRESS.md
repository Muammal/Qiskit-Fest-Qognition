# Progress

**Last updated: November 4, 2026.** Task-level status lives in [tasks.csv](tasks.csv).

## Where we are

| Track | Status | Details |
|---|---|---|
| **Tech A (`mind/`)** | **Done & Validated** | 2-qubit deliberation unitary + **6 peer-reviewed Quantum Cognition models** (`mind/cognition_models.py`), Qiskit 2.x circuits, 48 passing tests |
| **Tech B (`stranded_physics/`, `disaster_data/`, `contracts.py`)** | **Done & Verified (`14/14` gates `PASS`)** | 49 datasets registered in 14 category `datasets.toml` files, 20 Pint parameters in `params.toml`, 9 `T1` St. Vincent solvers in `stranded_physics/scenarios.py`, Tobler locomotion, BLS ATUS `data/priors.json`, 4-direction Grover DTQW |
| **Tech C (`engine/`, `main.py`)** | **Done & Production-Ready** | Dual-scenario simulator (`volcano` & `island`), counterfactual `scripted_events`, 3-mind selector, and **1600×900 Clash of Clans / Hay Day Village UI** |
| **Product D (`site/index.html`)** | **Done** | Client-side HTML5 40×40 replay canvas, Bloch circle & 6-model live Quantum Cognition Inspector |

## Verification Summary
- **Unified Pytest Suite**: `155 passed, 3 skipped` (`test_contracts_and_engine.py`, `mind/tests`, `stranded_physics/core`)
- **Physics Category Gates (`python -m stranded_physics.gates required`)**: `14 / 14 PASS` (recorded in [CLAIMS.md](CLAIMS.md))
- **Category Data & Parameter Catalog (`python -m stranded_physics.catalog`)**: 49 datasets and 20 Pint-checked parameters across 14 categories in [CATALOG.md](CATALOG.md)

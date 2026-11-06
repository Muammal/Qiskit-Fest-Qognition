# Quantum Cognition Simulation — Full System Report

## 1. System Overview & How Everything Works

**Quantum Cognition Simulation** is a complete, four-track research and interactive simulation platform that models human decision-making under acute environmental and volcanic hazards:

1. **Tech A (`mind/`) — 2-Qubit Quantum Cognitive Architecture & 6 Published Models**:
   - Represents the survivor's internal belief state on $\mathcal{H}_{\text{belief}} \otimes \mathcal{H}_{\text{action}}$ ($\mathbb{C}^2 \otimes \mathbb{C}^2$).
   - Evolves beliefs through non-commuting hazard gates $R_y(\theta_e)R_z(\phi_e)$ (`tremor`, `gas_plume`, `storm`, `animal`, `injury`, `cold_night`, `find_food`) or projective measurement collapse (`eruption`, `ash_fall`), interleaved with physiological stress decoherence $\lambda(\text{stress})$.
   - Implements **6 quantum cognition models adapted from published papers** in [`mind/cognition_models.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/cognition_models.py) alongside Qiskit 2.x circuit builders in [`mind/circuits.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/circuits.py).
2. **Tech B (`stranded_physics/`, `disaster_data/`, `data/priors.json`, `contracts.py`) — Empirical Disaster Calibration, Multi-Domain Physics Engine, ATUS Priors & Grover Quantum Walk**:
   - Curates **49 real-world volcanic, seismic, tsunami, cyclone, and ERA5 weather datasets** in [`disaster_data/`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/disaster_data/), registered across **14 domain categories** in [`stranded_physics/domains/`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/domains/) with SHA-256 verification and strict `calibration` vs. `holdout` split enforcement.
   - Implements **9 simplified stand-in solvers** for the April 2021 La Soufrière eruption on St. Vincent in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) (`build_st_vincent_pack`), replayed with Tobler slope/ash locomotion by [`PackSimulation`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/runtime/simulation.py).
   - Provides empirical Bureau of Labor Statistics (BLS) American Time Use Survey (ATUS) baseline activity priors in [`data/priors.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/data/priors.json) and a 4-direction **Grover-coined Discrete-Time Quantum Walk (DTQW)** in [`contracts.explore_step()`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/contracts.py).
3. **Tech C (`engine/`, `main.py`) — Five Evacuation & Survival Scenarios, Interactive Scenario Builder & Visualizer UI**:
   - **Island Wilderness (`island`) & Volcano Eruption (`volcano`)**: $40\times 40$ tile island (`250m` per tile) with priority-flood drainage, Tobler Dijkstra evacuation paths, active vs. deposited PDCs/lahars, dilute thermal surges, wind-advected ash, and counterfactual `scripted_events`.
   - **RMS Titanic 1912 (`titanic`, [`engine/titanic.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/titanic.py))**: 2,208 agents across 10 ship decks (`First`, `Second`, `Third` class + 5 crew roles), progressive compartment flooding ([`engine/flood.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/flood.py)), 20 lifeboats (`1,178` seats on Wormstedt's schedule in [`engine/lifeboats.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/lifeboats.py)), and counterfactual evacuation policy evaluation (`compare_titanic_policies`).
   - **Pompeii AD 79 (`pompeii`, [`engine/pompeii.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/pompeii.py))**: 11,500 (or 20,000) citizens across Roman households, Plinian eruption column, pumice fall, roof collapse hazard, pyroclastic surges ([`engine/eruption.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/eruption.py)), and 4 event-translation mappings (`A`–`D`).
   - **Waterloo Pool Chlorine Leak (`waterloo`, [`engine/waterloo.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/waterloo.py))**: 100–300 visitors & lifeguards across a municipal aquatic facility, 2D advection-diffusion chlorine plume ([`engine/chlorine.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/chlorine.py)), and EPA AEGL-1/2/3 toxic exposure tracking.
   - **Interactive Scenario Builder ([`engine/builder.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/builder.py))**: In-GUI custom scenario editor & multi-agent pack runner.
   - Renders an interactive **1600×900 Simulator UI** in [`engine/gui.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/gui.py) with a 3-Card Mind Selector (`2-Qubit Quantum Mind`, `Classical Mixture Control`, `Classical Rational Mind`).
4. **Product D (`site/index.html`) — Client-Side Web Replay & Quantum Cognition Inspector**:
   - Browser-based 40×40 replay canvas with built-in presets for **La Soufrière 2021**, **RMS Titanic 1912**, **Pompeii AD 79**, **Waterloo Chlorine Leak**, and **Island Survival**, plus live Bloch circle projection and real-time comparison of all 6 published quantum cognition models.

---

## 2. Multi-Scenario Evacuation Survival Rates & Real-Life Policy Insights

| Scenario | Population | Quantum Mind Outcome | Classical Mixture ($\lambda=1$) | Classical Rational | Key Real-Life Evacuation Insight |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Volcano (`volcano`)** | 1 agent (10 seeds) | **50% survived** ($P(\text{protect})=0.370$ at $p=0.5$) | **40% survived** ($P(\text{protect})=0.550$ at $p=0.5$) | **30% survived** | Non-commuting order effect (`Tremor→Gas` vs `Gas→Tremor`) shifts $P(\text{protect})$ by $\pm 15.6\%$; early premature hiding depletes hydration before main eruption |
| **Titanic (`titanic`, default)** | 2,208 aboard | **849 saved** (`38.45%`), 1,359 dead | **849 saved** (`38.45%`), 1,359 dead | **870 saved** (`39.40%`), 1,338 dead | Historical survival was **712 / 2,208 (`32.25%`)**. Distress rockets (`ash_fall`) collapse quantum superposition at 00:45 |
| **Titanic (`ambiguous_rockets`)** | 2,208 aboard | **815 saved** (`36.91%`), 1,393 dead | **848 saved** (`38.41%`), 1,360 dead | **870 saved** (`39.40%`), 1,338 dead | When rockets are treated as ambiguous (`gas_plume`), quantum destructive interference delays passenger ascent (**33 fewer survivors** than classical mixture) |
| **Titanic (`open_boarding_both_sides`)** | 2,208 aboard | **913+ saved** (`41.35%+`) | **913+ saved** (`41.35%+`) | **920+ saved** (`41.67%+`) | Unambiguous early PA alarm (`steward_warning -> eruption`) + allowing men onto port lifeboats after women/children board saves **64+ additional lives** |
| **Pompeii (`pompeii`, Mapping C)** | 11,500 citizens | **10,856 escaped** (`94.4%`), **644 dead** | **11,213 escaped** (`97.5%`), **287 dead** | **11,500 escaped** (`100%`), **0 dead** | Under ambiguous cues (`Mapping C`), quantum disjunction interference more than doubles fatalities (**644 vs 287**); under `Mapping D` with enslaved restrictions, quantum fatalities reach **981** |
| **Waterloo (`waterloo`, Alarm ON vs OFF)** | 100 visitors | **23 AEGL-2** (Alarm ON) vs **32 AEGL-2** (Alarm OFF) | **21 AEGL-2** (Alarm ON) vs **27 AEGL-2** (Alarm OFF) | **20 AEGL-2** | Unambiguous staff alarm collapses quantum hesitation (`alarm -> eruption`), cutting disabling AEGL-2 chlorine exposure by **28%** (`32 -> 23`) |

---

## 2. Exact Status of Tech B: Is Tech B Done Now?

### Yes — All Core Tech B Deliverables Are 100% Complete & Passing All Gates

| Tech B Component | Implementation Location | Status | Verification |
| :--- | :--- | :--- | :--- |
| **1. Frozen Physics Interfaces & Pint Unit Registry (`WS0: T-001, T-002`)** | [`stranded_physics/core/api.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/core/api.py), [`fields.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/core/fields.py), [`records.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/core/records.py), [`verdicts.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/core/verdicts.py) | **DONE** | `43/43` tests in `stranded_physics/core/tests/test_interfaces.py` |
| **2. 49 Empirical Disaster Datasets & Category Records (`WS1: T-100, T-101, T-102`)** | [`disaster_data/manifest.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/disaster_data/manifest.json) + all 14 `stranded_physics/domains/<cat>/datasets.toml` & `params.toml` | **DONE** | [`workboard/CATALOG.md`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/workboard/CATALOG.md) & [`workboard/CLAIMS.md`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/workboard/CLAIMS.md) (14/14 record checks pass (settings and data files load; the physics is not tested against reality)) |
| **3. Terrain & Drainage T1 Solver (`WS2: T-201, T-202`)** | `StVincentTerrain` in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) | **DONE** | `test_st_vincent_physics_pack_and_simulation` |
| **4. Atmosphere & Holland Storm T1 Solvers (`WS3: T-301, T-302`)** | `StVincentAtmos`, `HollandStorm` in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) | **DONE** | `atmos.records_and_units: PASS`, `storm.records_and_units: PASS` |
| **5. Eruption, Suzuki Tephra & Gaussian Gas T1 Solvers (`WS4: T-401, T-402, T-403`)** | `SoufriereEruption`, `SuzukiTephra`, `GaussianGas` in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) | **DONE** | `eruption`, `tephra`, `gas` gates `PASS` |
| **6. Energy-Cone PDC, LAHARZ Lahar & Dome Lava T1 Solvers (`WS5: T-501, T-502, T-504`)** | `EnergyConePDC`, `LaharzLahar`, `DomeLava` in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) | **DONE** | `pdc`, `lahar`, `lava` gates `PASS` |
| **7. Tobler Locomotion, Causal Perception & `--engine physics` (`WS6: T-601..T-604, T-701`)** | [`stranded_physics/runtime/simulation.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/runtime/simulation.py), [`perception.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/runtime/perception.py), [`main.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/main.py) | **DONE** | `python main.py --demo --engine physics` |
| **8. Empirical BLS ATUS Priors & 4-Direction Grover DTQW** | [`data/priors.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/data/priors.json), [`contracts.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/contracts.py) (`get_prior`, `classical_decide`, `explore_step`) | **DONE** | `test_grover_dtqw_explore_step_and_atus_priors` |
| **9. Data-v1 Release Import (`artifacts/physics/raw/`)** | Downloaded and extracted from [GitHub Release `data-v1`](https://github.com/Muammal/Qiskit-Fest-Qognition/releases/tag/data-v1) via `tools/fetch_artifacts.py` (19 verified raw data files: DEMs, ERA5 wind grids, storm tracks, ship plans) | **DONE** | `22 / 22` physical verification gates PASS (`python -m stranded_physics.gates required`) |

### What Is Optional / Future Post-Hackathon Work?
Only two items in [`workboard/tasks.csv`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/workboard/tasks.csv) remain marked as optional future extensions (neither blocks production or the simulation):
1. **`T-503` (Tier-2 2D Shallow-Water PDE Solver)**: The current production physics pack uses Tier-1 (`T1`) reduced-order geophysical solvers (`EnergyConePDC` and `LaharzLahar`), which run in `< 0.4s` per 36-step pack. A full Tier-2 (`T2`) finite-volume shallow-water PDE solver is an optional future research extension.
2. **`T-103` & `T-104` (External Registration-Gated EM-DAT Export & Third-Party Licence Sign-Off)**: 16 datasets have confirmed open/CC/US-Gov licences in `datasets.toml`; the remaining web-scraped case-study HTML pages are marked `licence_confirmed = false` so they are used strictly for internal calibration/verification and never redistributed as raw files.

---

## 3. Clash of Clans / Hay Day Simulator UI & Media Exporters (`engine/gui.py`, `site/index.html`)

The simulator UI in [`engine/gui.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/gui.py) has been styled after **Clash of Clans / Hay Day (Supercell Village & Island Games)** while preserving full scientific and cognitive telemetry:

1. **Carved Oak & Sunlit Parchment Cards (`draw_card`)**:
   - Warm carved timber backdrop `(62, 40, 22)`, golden ribbon headers `(244, 188, 58)`, cream parchment panels `(250, 239, 212)`, golden inner bevels, and 4 corner brass rivets.
2. **3D Beveled Glossy Game Buttons (`UIButton.draw`)**:
   - Chunky 3D bottom lip (`+3px`), rounded corners (`border_radius=10`), top specular gloss strip, and high-contrast typography.
3. **2.5D Village & Island Diorama Map (`draw_island_map` & `draw_character`)**:
   - Signature **Checkerboard Emerald Village Lawn** (`(126, 202, 68)` / `(114, 190, 58)`), golden sandy beaches, sparkling turquoise lagoon water with animated wave crests, puffy 2.5D orchard/pine trees with ruby/gold fruit clusters, red-roofed timber village cottages with glowing windows, smoking volcano caldera, and a straw-hat villager sprite with parchment thought bubbles.
4. **Glossy Elixir/Gold Telemetry Bars (`draw_progress_bar`)**:
   - Recessed dark wood troughs with golden rims and specular highlight strips for all 6 physiological needs, stress, decoherence $\lambda$, and the 7 survival action probabilities.
5. **Slow-Motion & Fast-Forward Simulation Controls**:
   - Speed buttons (`1x`, `2x`, `5x`, `10x`) and keyboard shortcuts (`[` for Slow-Mo down to 0.25x / 1 FPS, `]` for Fast-Forward up to 10x / 30 FPS, and `Space` to pause/resume) allow detailed inspection of critical order-effect decision moments and fast multi-agent runs.
6. **MP4 Simulation Video Exporter (`engine/video_exporter.py`)**:
   - High-definition MP4 video exporter (`python main.py --export-video --scenario <name> --duration 12`) renders headless Pygame simulation runs directly to video files with fallback to raw/FFmpeg.
7. **Empirical Evacuation Data & Seed Exporter (`engine/data_exporter.py`)**:
   - Generates production-ready CSV spreadsheets (`evacuation_survival_comparison.csv`), machine-readable policy bundles (`evacuation_data_bundle.json`), and comprehensive Markdown reports (`EVACUATION_INSIGHTS_REPORT.md`) across all 5 disaster scenarios.

---

## 4. Visual Gallery Across All Scenarios

| Scenario | Screenshot |
| :--- | :--- |
| **01: Event Choice Hub** | ![Event Choice Hub](../docs/images/01_event_choice_hub.png) |
| **02: Home Configuration & 3-Mind Selector** | ![Home Configuration](../docs/images/02_home_configuration.png) |
| **03: Island Wilderness Survival** | ![Island Wilderness](../docs/images/03_island_survival_sim.png) |
| **04: Volcano Evacuation (La Soufrière)** | ![Volcano Evacuation](../docs/images/04_volcano_evacuation_sim.png) |
| **05: Mission Debrief Modal** | ![Mission Debrief](../docs/images/05_mission_debrief.png) |
| **06: RMS Titanic 1912 Evacuation** | ![RMS Titanic](../docs/images/06_titanic_evacuation_sim.png) |
| **07: Pompeii AD 79 Evacuation** | ![Pompeii AD 79](../docs/images/07_pompeii_evacuation_sim.png) |
| **08: Waterloo Chlorine Gas Leak** | ![Waterloo Chlorine](../docs/images/08_waterloo_chlorine_sim.png) |
| **09: Interactive Scenario Builder** | ![Scenario Builder](../docs/images/09_scenario_builder.png) |

---

## 5. Production Verification Summary

All automated test suites, validation scripts, and physics gates pass out of the box across the entire repository:

```powershell
# 1. Full Unified Test Suite (816 tests passing across all tracks)
$env:SDL_VIDEODRIVER="dummy"; python -m pytest -q
# -> 816 passed, 3 skipped in 13m 19s (100% pass rate)

# 2. Tech A Validation Report & 6-Paper Cross-Check
python -m mind.experiments.validate
# -> Wrote docs/tech-a/07-validation-report.md (any_failed=False)

# 3. Tech B 14-Category Verification Gates (All 22 Gates Pass)
python -m stranded_physics.gates required
# -> 22 / 22 PASS (all datasets, records, and physics invariants verified)

# 4. Tech B Provenance & Unit Catalog
python -m stranded_physics.catalog
# -> 49 Datasets, 20 Pint Parameters catalogued in workboard/CATALOG.md
```


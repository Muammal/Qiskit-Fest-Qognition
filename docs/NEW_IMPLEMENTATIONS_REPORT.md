# New Implementations & Published Quantum Cognition Models Report

This report documents all newly implemented features, architectural completions, and **6 peer-reviewed, GitHub-sourced Quantum Cognition models** integrated across **Tech A (`mind/`)**, **Tech B (`stranded_physics/`, `contracts.py`, `data/priors.json`)**, **Tech C (`engine/`, `main.py`)**, and **Product D (`site/index.html`)**.

---

## 1. Executive Summary

| Track / Module | New Implementation | Primary Files | Verification Status |
| :--- | :--- | :--- | :--- |
| **Tech A — Quantum Mind** | **6 Research-Paper-Backed Quantum Cognition Models**: (1) Busemeyer Dynamic 2-Qubit Hamiltonian (`jbusemey/ChoiceModeling`), (2) Huang–Moreira–Wichert Parameter-Free QLBN via Belief Entropy (`Insight137/insight137-eap`), (3) Broekaert–Yearsley Open-System GKSL Lindblad Master Equation (`hwilner/open-system-decision-dynamics`), (4) Li–Busemeyer Quantum Reinforcement Learning via Generalized Grover Reflections (`ljaustc/QRL`), (5) Wang–Busemeyer QQ Equality & Lüders 2D Representability (`WileQ/QCog`), (6) Trueblood–Busemeyer Quantum Bayesian Givens Rotations (`robertcprice/nQPU`). | [`mind/cognition_models.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/cognition_models.py), [`mind/quantum_mind.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/quantum_mind.py), [`mind/model.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/model.py), [`mind/decoherence.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/decoherence.py) | `12/12` model tests + `45/45` total `mind/tests` passing |
| **Tech A — Qiskit Circuits & Validation** | Mid-circuit projective collapse (`allow_collapse=True` via `qc.reset(0)` + `qc.x(0)`), `build_busemeyer_hamiltonian_circuit()`, `build_luders_sequence_circuit()`, and automated 6-paper `library_cross_check()` in [`mind/experiments/validate.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/experiments/validate.py). | [`mind/circuits.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/circuits.py), [`mind/experiments/validate.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/experiments/validate.py), [`docs/tech-a/07-validation-report.md`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/docs/tech-a/07-validation-report.md) | Verified in Qiskit & `library_cross_check()` |
| **Tech B — T1 Volcanic Physics Engine** | Full 9-domain **T1 Physical Solver Suite** for the April 2021 La Soufrière eruption on St. Vincent (`StVincentTerrain`, `StVincentAtmos`, `HollandStorm`, `SoufriereEruption`, `SuzukiTephra`, `GaussianGas`, `EnergyConePDC`, `LaharzLahar`, `DomeLava`) + `build_st_vincent_pack()`. | [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) | Verified with `PackSimulation` & Pint unit checks |
| **Tech B — ATUS Priors & Grover Quantum Walk** | Empirical BLS American Time Use Survey (ATUS) activity weights in [`data/priors.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/data/priors.json) and 4-direction **Grover-coined Discrete-Time Quantum Walk (DTQW)** ($G = 2|s\rangle\langle s| - I_4$) with environmental phase-oracle kicks in `explore_step()`. | [`data/priors.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/data/priors.json), [`contracts.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/contracts.py) | Verified in `test_contracts_and_engine.py` |
| **Tech C — Engine, CLI & Pygame GUI** | Deterministic counterfactual event scripting (`scripted_events`), 3-way mind selector (`quantum` $\to$ `classical_mixture` $\to$ `classical`), `--engine {legacy,physics}` CLI switch, and live quantum telemetry HUD (`|x|`, `λ`, `ΔP`). | [`engine/events.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/events.py), [`engine/simulation.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/simulation.py), [`engine/gui.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/gui.py), [`main.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/main.py) | Verified in headless Pygame & CLI tests |
| **Product D — Web Replay & Quantum Inspector** | Self-contained HTML5/Canvas Replay Viewer & *"Why Did He Do That?"* Quantum Cognition Inspector with live Bloch circle projection, interactive stress/coherence sandbox, and 6-model comparison table. | [`site/index.html`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/site/index.html) | Built-in presets + `timeline.json` loader |

---

## 2. Six Research-Paper-Backed Quantum Cognition Models (`mind/cognition_models.py`)

All six published mathematical models are implemented in [`mind/cognition_models.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/cognition_models.py) and tested in [`mind/tests/test_cognition_models.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/tests/test_cognition_models.py).

### Model 1: Busemeyer Dynamic 2-Qubit Hamiltonian (`busemeyer_hamiltonian`, `p_protect_busemeyer`)
- **GitHub Source Repository**: [`jbusemey/ChoiceModeling`](https://github.com/jbusemey/ChoiceModeling) (`Quantum/ChoiceRTConfidence/Lquant.m`)
- **Peer-Reviewed Papers**:
  - Pothos, E. M., & Busemeyer, J. R. (2009). A quantum probability explanation for violations of 'rational' decision theory. *Proceedings of the Royal Society B*, 276(1665), 2171–2178.
  - Busemeyer, J. R., & Bruza, P. D. (2012). *Quantum Models of Cognition and Decision*. Cambridge University Press.
- **Mathematical Formulation**:
  Rather than a static rotation matrix, deliberation evolves in continuous time $t$ under a $4\times 4$ Hermitian Hamiltonian $H = H_{\text{payoff}} + H_{\text{dissonance}}$ on $\mathcal{H}_{\text{belief}} \otimes \mathcal{H}_{\text{action}}$:
  $$H_B(h) = \frac{1}{\sqrt{1 + h^2}}\begin{pmatrix} h & 1 \\ 1 & -h \end{pmatrix}, \qquad H_{\text{payoff}} = |0\rangle\langle 0| \otimes H_B(h_S) + |1\rangle\langle 1| \otimes H_B(h_D)$$
  Cognitive dissonance entangles belief and action via:
  $$H_{\text{dissonance}}(\gamma) = \frac{-\gamma}{\sqrt{2}}\Big[(|0\rangle\langle 1| + |1\rangle\langle 0|) \otimes Z - I_2 \otimes X\Big]$$
  $$U_{\text{dyn}}(t) = \exp\!\left(-i \, t \, \frac{\pi}{2} \left(H_{\text{payoff}} + H_{\text{dissonance}}\right)\right)(I_2 \otimes H_{\text{Had}})$$
- **Integration**: Selectable via `quantum_decide(state, cognition_model="busemeyer_hamiltonian")` and built as a Qiskit circuit in [`build_busemeyer_hamiltonian_circuit()`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/circuits.py).

---

### Model 2: Parameter-Free Quantum-Like Bayesian Network via Belief Entropy (`belief_degree_huang`, `p_protect_qlbn`)
- **GitHub Source Repository**: [`Insight137/insight137-eap`](https://github.com/Insight137/insight137-eap)
- **Peer-Reviewed Papers**:
  - Huang, Z., Yang, L., & Jiang, W. (2019). Uncertainty measurement with belief entropy on quantum model for decision making. *Applied Mathematics and Computation*, 347, 417–428.
  - Moreira, C., & Wichert, A. (2016). Quantum-Like Bayesian Networks for modeling decision making. *Frontiers in Psychology*, 7, 11.
  - Deng, Y. (2016). Deng entropy. *Chaos, Solitons & Fractals*, 91, 549–553.
- **Mathematical Formulation**:
  Eliminates hand-tuned interference angles by computing the belief distance $d_i$ and normalized belief entropy $D_b$ directly from the marginal belief $P = (1-p, p)$ and conditional action tables $Q_S = (q_S, 1-q_S)$, $Q_D = (q_D, 1-q_D)$:
  $$d_i = \sqrt{\frac{1}{2}\sum_{j} (P_j - Q_{i,j})^2}, \qquad B_d(i) = 1 - d_i$$
  $$D_b = \frac{\sum_i B_d(i) \log_2 B_d(i)}{\sum_i B_d(i)} \in [-1, 0]$$
  Using $|D_b|$ as the parameter-free coherence scale inside the unitary interference term yields $P_q(\text{defect}) = 0.3974$ on the Pothos & Busemeyer (2009) Prisoner's Dilemma ($p=0.5, q_S=0.69, q_D=0.59$), closely matching the human empirical unknown-condition rate ($0.37$) without fitting any free parameters.
- **Integration**: Selectable via `quantum_decide(state, cognition_model="qlbn_entropy")` and logged on every step as `decision["quantum"]["d_b_huang"]`.

---

### Model 3: Open Quantum System GKSL Lindblad Master Equation (`lindblad_rhs`, `evolve_lindblad`)
- **GitHub Source Repository**: [`hwilner/open-system-decision-dynamics`](https://github.com/hwilner/open-system-decision-dynamics)
- **Peer-Reviewed Papers**:
  - Broekaert, J., Busemeyer, J. R., & Pothos, E. M. (2020). The disjunction effect in two-stage simulated gambles: An experimental study and comparison of a heuristic, Markov, and quantum model. *Cognitive Psychology*, 117, 101262.
  - Yearsley, J. M., & Busemeyer, J. R. (2016). Quantum cognition and decision theories: A tutorial. *Journal of Mathematical Psychology*, 74, 99–116.
- **Mathematical Formulation**:
  Replaces discrete per-step dephasing with continuous open-system Gorini–Kossakowski–Sudarshan–Lindblad (GKSL) evolution:
  $$\frac{d\rho}{dt} = -i(1-\alpha)[H, \rho] + \alpha \sum_{k} \gamma_k \left( L_k \rho L_k^\dagger - \frac{1}{2}\{L_k^\dagger L_k, \rho\} \right)$$
  Integrated via 4th-order Runge–Kutta (`evolve_lindblad`), preserving $\text{Tr}(\rho) = 1$ and positive semidefiniteness for any stress-driven bath rate $\gamma(\text{stress})$.
- **Integration**: Selectable via `quantum_decide(state, cognition_model="lindblad_open")` and re-exported in [`mind/decoherence.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/decoherence.py).

---

### Model 4: Quantum Reinforcement Learning via Generalized Grover Reflections (`QuantumSequenceLearner`)
- **GitHub Source Repository**: [`ljaustc/QRL`](https://github.com/ljaustc/QRL) (`QRL_bandit`)
- **Peer-Reviewed Paper**:
  - Li, J.-A., Dong, D., Wei, Z., Liu, Y., Pan, Y., Nori, F., & Busemeyer, J. R. (2020). Quantum reinforcement learning during human decision-making. *Nature Human Behaviour*, 4, 294–307.
- **Mathematical Formulation**:
  Superposition over the 7 survival actions $|\psi\rangle = \sum_{a=0}^{6} c_a |a\rangle$ is updated after experiencing action $|a\rangle$ with Prospect-Theory utility $u(x)$ via two generalized Grover reflections:
  $$U_{\text{oracle}}(a, \phi_1) = I - (1 - e^{i\phi_1})|a\rangle\langle a|, \qquad U_{\text{diff}}(\psi, \phi_2) = (1 - e^{i\phi_2})|\psi\rangle\langle\psi| - I$$
  $$|\psi'\rangle = U_{\text{diff}}(\psi, \phi_2) \, U_{\text{oracle}}(a, \phi_1) |\psi\rangle$$
  Strictly unitary ($\||\psi'\rangle\|_2 = 1$) while amplifying rewarded survival actions and suppressing punished actions.

---

### Model 5: Wang–Busemeyer QQ Equality & Projective Lüders 2D Representability (`wang_busemeyer_qq_gap`, `verify_2d_representability`)
- **GitHub Source Repositories**: [`WileQ/QCog`](https://github.com/WileQ/QCog) & [`ProfessorBrunner/aggregation-observability`](https://github.com/ProfessorBrunner/aggregation-observability)
- **Peer-Reviewed Paper**:
  - Wang, Z., Solloway, T., Shiffrin, R. M., & Busemeyer, J. R. (2014). Context effects produced by question orders reveal quantum nature of human judgments. *Proceedings of the National Academy of Sciences (PNAS)*, 111(26), 9431–9436.
- **Mathematical Formulation**:
  For sequential projective Lüders measurements $P_A(\theta_A)$ and $P_B(\theta_B)$ on a 2D real Hilbert space, single-outcome order effects can be large:
  $$\Delta_{\text{single}} = P(A_y \text{ then } B_y) - P(B_y \text{ then } A_y) \neq 0$$
  Yet the **Quantum Question (QQ) identity** vanishes identically across all angles:
  $$q_{\text{QQ}} = \big(P(A_y B_n) + P(A_n B_y)\big) - \big(P(B_y A_n) + P(B_n A_y)\big) = 0$$
- **Integration**: Implemented in [`mind/cognition_models.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/cognition_models.py) and [`build_luders_sequence_circuit()`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/circuits.py), and verified across random angle grids in [`mind/experiments/validate.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/mind/experiments/validate.py).

---

### Model 6: Quantum Bayesian Belief Updating via Givens Rotations (`quantum_bayesian_update`)
- **GitHub Source Repository**: [`robertcprice/nQPU`](https://github.com/robertcprice/nQPU) (`apps/quantum_bayesian.py`)
- **Peer-Reviewed Paper**:
  - Trueblood, J. S., & Busemeyer, J. R. (2011). A quantum probability account of order effects in inference. *Cognitive Science*, 35(8), 1518–1552.
- **Mathematical Formulation**:
  Converts log-likelihood ratios of survival cues into unitary Givens rotations $G(\theta_e)$ accompanied by diagnostic phase shifts $\Phi(\phi_e)$:
  $$\theta_e = 2\arctan\!\left(\sqrt{\frac{P(e \mid \text{danger})}{P(e \mid \text{safe})}}\right) - \frac{\pi}{2}, \qquad U_e = \Phi(\phi_e) \, G(\theta_e)$$
  Because $U_{e_1}$ and $U_{e_2}$ do not commute when $\phi_e \neq 0 \pmod{\pi}$, sequential evidence produces recency/primacy order effects that classical Bayes' rule cannot generate.

---

## 3. Tech B, Tech C & Product D Implementations

### 3.1 Tech B: `st_vincent_2021` T1 Physics Solvers (`stranded_physics/scenarios.py`)
Implemented 9 Pint-unit-checked `T1` domain solvers in [`stranded_physics/scenarios.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py) driven by [`disaster_data/scenarios/st_vincent_2021.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/disaster_data/scenarios/st_vincent_2021.json):
1. [`StVincentTerrain`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L62-L130): Somma-wall and Rabacca/Wallibou drainage topography + high-hazard exclusion zones.
2. [`StVincentAtmos`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L133-L185): 36-step empirical ERA5/Open-Meteo wind speed, bearing, temperature, and precipitation fields.
3. [`HollandStorm`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L188-L216): Tropical squall wind amplification and storm-surge footprint.
4. [`SoufriereEruption`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L219-L261): Eruptive phase transitions (`unrest -> escalating -> erupting -> fading`), Mastin (2009) plume height $H = 2.0 \, \text{MER}^{0.241}$, and RSAM tremor amplitude.
5. [`SuzukiTephra`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L264-L296): Anisotropic downwind advective-diffusive tephra fallout accumulation ($\text{kg/m}^2$).
6. [`GaussianGas`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L299-L324): Downwind $\text{SO}_2$ concentration plume ($\text{mg/m}^3$).
7. [`EnergyConePDC`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L327-L347): Malin & Sheridan (1982) energy-cone pyroclastic density current dynamic pressure ($\text{kPa}$) channelized down radial valleys.
8. [`LaharzLahar`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L350-L366): Rainfall-remobilized lahar dynamic pressure ($\text{Pa}$) along drainage talwegs.
9. [`DomeLava`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/stranded_physics/scenarios.py#L369-L386): Summit crater dome extrusion footprint.

### 3.2 Tech B: Empirical BLS ATUS Priors (`data/priors.json`) & Grover DTQW (`contracts.py`)
- Created [`data/priors.json`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/data/priors.json) storing Bureau of Labor Statistics (BLS) American Time Use Survey (ATUS) Table A-1 baseline human activity weights and urgency multipliers, automatically loaded into [`contracts.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/contracts.py).
- Upgraded [`explore_step(pos, world, mode="quantum")`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/contracts.py) from a classical uniform step to a 4-direction **Grover-coined Discrete-Time Quantum Walk (DTQW)** using the $4\times 4$ Grover diffusion coin $G = 2|s\rangle\langle s| - I_4$ coupled to a local terrain/hazard phase oracle.

### 3.3 Tech C: Counterfactual Event Scripting, 3-Mind Selector & Live Telemetry (`engine/`, `main.py`)
- Added `scripted_events: Optional[Dict[int, str]] = None` to [`EventGenerator`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/events.py) and [`SimulationEngine`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/simulation.py) so researchers can run exact $A \to B$ vs. $B \to A$ order-effect counterfactuals on identical seeds.
- Added 3-mind cycling (`quantum` $\to$ `classical_mixture` $\to$ `classical`) and live quantum telemetry (`|x|`, `λ`, `ΔP`) in [`engine/gui.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/engine/gui.py) and `--mind {quantum,classical_mixture,classical}` + `--engine {legacy,physics}` in [`main.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/main.py).

### 3.4 Product D: Web Replay Viewer & Quantum Cognition Inspector (`site/index.html`)
- Created [`site/index.html`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/site/index.html) providing a client-side 40×40 field replay canvas, live Bloch circle visualization, interactive stress/coherence deliberation sandbox, and real-time evaluation of all 6 peer-reviewed quantum cognition models on every simulation step.

---

## 4. Automated Test & Validation Results

Running the full test suite across all tracks:

```powershell
$env:SDL_VIDEODRIVER="dummy"; python -m pytest test_contracts_and_engine.py mind/tests stranded_physics/core -q
```

- **Result**: **`155 passed, 3 skipped`** (100% pass rate across all unit, contract, physics, GUI, and quantum cognition model tests).

# Codebase Implementation & Module Architecture

## 1. Unified Directory Architecture

The framework is organized into decoupled engine, environment, runtime, and UI modules, all operating directly from the root repository directory:

```text
QWC/
├── main.py                     # Interactive Master Command Center (CLI Menu & Runner)
├── config.py                   # Master Hyperparameters, Qubit Caps & Compute Limits
├── requirements.txt            # Pinned Dependencies
├── setup_and_verify.py         # Pre-Flight Verification Suite for Assets & ROMs
├── visual_showcase.py          # Real-Time 320x RAM Benchmark & ANSI Telemetry
├── record_mario_videos.py      # PyAV H.264 Video Recording Engine
├── run_pipeline.py             # 4-Day Research Pipeline (Days 1–4 CLI Runner)
├── run_blackjack_exploit.py    # Standalone Blackjack Exploit Demo
├── docs/                       # Architectural Blueprints & Proofs
├── changes/                    # Historical Agentic Changelogs & Reasoning Ledgers
├── engines/                    # Quantum RL, Statevector Kernel & Grover Engines
├── envs/                       # Game Environments & RAM Wrappers
├── data/                       # Datasets & Scenarios (FENs, WADs)
├── artifacts/                  # Generated MP4 Videos, Reports & Weights
├── run/                        # Real-Time Game Simulation Suite
├── ui/                         # Real-Time Web Interface (FastAPI + HTML5 Canvas)
└── .gitignore                  # Clean Git Configuration
```

---

## 2. Quantum Engine Modules (`engines/`)

### 2.1 `engines/kernel_anomaly_engine.py`
Implements the $O(N)$ Fast Statevector Quantum Kernel and One-Class SVM pipeline.

```python
class FastQuantumKernel:
    """
    Computes Gram matrices using precomputed statevector projections:
    K_ij = |<ψ(x_i)|ψ(x_j)>|^2 = |(V V†)_ij|^2
    Complexity: O(N) evaluations instead of O(N^2 * shots).
    """
    def __init__(self, num_qubits: int = 4, reps: int = 2, entanglement: str = "linear"):
        self.num_qubits = num_qubits
        self.feature_map = ZZFeatureMap(num_qubits=num_qubits, reps=reps, entanglement=entanglement)
        self.cached_train_statevectors = None

    def compute_train_gram_matrix(self, X_train: np.ndarray) -> np.ndarray:
        V = self._extract_statevectors(X_train)  # Shape: (N, 2^n)
        self.cached_train_statevectors = V
        inner_products = V @ V.conj().T          # Shape: (N, N)
        K = np.abs(inner_products) ** 2
        np.fill_diagonal(K, 1.0)
        return K

    def compute_test_kernel_matrix(self, X_test: np.ndarray) -> np.ndarray:
        V_test = self._extract_statevectors(X_test)
        inner_products = V_test @ self.cached_train_statevectors.conj().T
        return np.abs(inner_products) ** 2
```

- **`QuantumKernelAnomalyDetector`**: Trains `sklearn.svm.OneClassSVM(kernel="precomputed", nu=0.08)`. For any incoming test state, evaluates anomaly score:
  ```python
  def exploit_anomaly_score(self, X: np.ndarray) -> np.ndarray:
      return -self.decision_function(X)
  ```

### 2.2 `engines/oracle_safety_engine.py`
Implements the Grover Phase Oracle and 16-Qubit Matrix Product State (MPS) constraint verifier.

- **`GroverSafetyEngine`**:
  Constructs optimal Grover circuits using Qiskit 1.0+ primitives:
  ```python
  oracle = PhaseOracle(expression)  # Marks exploit bitstrings with (-1)
  grover = Grover(oracle=oracle, iterations=optimal_k)
  ```
  Calculates the optimal iteration count via $k = \lfloor \frac{\pi}{4}\sqrt{N/M} \rfloor$ and executes on `AerSimulator()`.
- **`MPSConstraintVerifier`**:
  Initializes an Aer simulator configured with the tensor-network Matrix Product State method:
  ```python
  sim = AerSimulator(
      method="matrix_product_state",
      matrix_product_state_max_bond_dimension=32,
      matrix_product_state_truncation_threshold=1e-8
  )
  ```
  Verifies 16-qubit game invariant circuits in $0.028 \text{ seconds}$.

### 2.3 `engines/qrl_policy_engine.py`
Implements the 4-qubit Hybrid Variational Quantum Policy Network.

- **Ansatz & EstimatorQNN**:
  ```python
  qc = QuantumCircuit(4)
  for i in range(4):
      qc.ry(inputs[i], i)
  for layer in range(reps):
      for i in range(4):
          qc.ry(weights[layer, i], i)
      for i in range(3):
          qc.cx(i, i + 1)
  
  qnn = EstimatorQNN(
      circuit=qc,
      observables=[SparsePauliOp.from_list([(f"{'I'*i}Z{'I'*(3-i)}", 1)) for i in range(4)]),
      input_params=inputs,
      weight_params=weights
  )
  ```
- **PyTorch Connector**:
  Wrapped with Qiskit Machine Learning's `TorchConnector(qnn)` for automatic backward gradient propagation through PyTorch's `autograd` engine.
- **`QuantumExploitHunterAgent`**:
  Implements the Actor-Critic policy gradient with Intrinsic Exploit Curiosity reward shaping:
  $$R_{\text{total}} = R_{\text{game}} + \lambda \cdot \max(0, S_{\text{anomaly}})$$

---

## 3. Game Environment Wrappers (`envs/`)

### 3.1 `envs/retro_2d_ram_env.py`
- **`MarioRAMWrapper`**:
  Wraps `gym-super-mario-bros` with an 8-frame action repeat (`FrameSkip(8)`). Bypasses RGB pixel rendering by extracting 4 normalized float variables directly from `env.unwrapped.ram`:
  - Player X Page: `0x006D` & Sub-pixel X: `0x0086`
  - Player Y Position: `0x00CE`
  - Horizontal Velocity: `0x0057`
  - Collision State: `0x001D`
- **`ViZDoomRAMWrapper`**:
  Wraps ViZDoom headless scenario `basic.cfg` (`freedoom2.wad`), extracting:
  `POSITION_X`, `POSITION_Y`, `VELOCITY_X`, and `HEALTH`.
- **`GlitchGrid2DEnv`**:
  Lightweight 2D physics fallback environment that runs seamlessly when external SDL2 or NES ROM compilation is unavailable on restricted cloud containers.

### 3.2 `envs/chess_fuzz_env.py`
- Parses FEN strings into 4 topological invariants using `python-chess`:
  Material Imbalance, Piece Density, King Integrity, and Pawn Structure Legality.
- Generates `data/normal_chess_states.fen` (200 legal FENs) and `data/corrupted_chess_states.fen` (20 corrupted FENs with multiple kings or pawns on ranks 1/8).

### 3.3 `envs/sudoku_card_env.py`
- **`MiniSudoku4x4Env`**:
  Gymnasium environment verifying Latin-Square invariants across rows, columns, and $2 \times 2$ boxes. Injected exploits simulate duplicate values or blank cells.
- **`BlackjackExploitEnv`**:
  Gymnasium `Blackjack-v1` wrapper with exploit injection for card sum overflows ($>31$) and infinite soft aces.

---

## 4. Real-Time Game Simulation Suite (`run/`)

Each game runner shares unified ANSI telemetry formatting via `run/common.py` and hardware-accelerated visual playback via `run/visual_window.py`:
- `run/visual_window.py`: [`QuantumVisualWindow`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/visual_window.py) provides a high-DPI ($768 \times 720$) SDL2/Pygame visual rendering window with a Cyberpunk header, live game viewport, 4-qubit expectation meters ($\langle Z_i \rangle$), anomaly gauge, and dual-speed playback (1x 60 FPS real-time vs 240 FPS sped-up fuzzing).
- `run/run_mario.py`: Full-level Super Mario Bros World 1-1 traversal with edge-triggered pipe jumping, staircase climb, flagpole completion ($X \ge 2480$ px), and sub-pixel wall-clip warp interception.
- `run/run_doom.py`: Full-corridor ViZDoom combat episode completion with auto-aim monster elimination, health overflow, and coordinate perimeter tunneling interception.
- `run/run_chess.py`: Complete chess match playout with live chessboard visual rendering and illegal king/pawn exploit interception.
- `run/run_sudoku.py`: Simulates $4 \times 4$ permutations with row/box duplicate breach injection.
- `run/run_blackjack.py`: Simulates casino card deals with sum overflow ($>31$) injection.
- `run/run_game.py`: Unified CLI dispatcher supporting `--game [mario|doom|chess|sudoku|blackjack|all]`, `--realtime`, `--realtime-iter`, and `--headless`.

---

## 5. Real-Time Web User Interface (`ui/`)

### 5.1 `ui/server.py`
- Built on **FastAPI** and **Uvicorn**.
- Provides a Server-Sent Events (SSE) streaming endpoint:
  ```python
  @app.get("/api/stream")
  def stream_simulation(game: str, is_exploit: bool, steps: int, delay: float):
      return StreamingResponse(
          game_simulation_generator(game, is_exploit, steps, delay),
          media_type="text/event-stream"
      )
  ```
- Yields structured JSON events for every physics step containing:
  - Step progress and action name.
  - Telemetry variables (coordinates, velocity, health, FEN, Sudoku grid, cards).
  - 4-qubit Pauli expectations $\langle Z_i \rangle$.
  - Fast Quantum Kernel anomaly score and exploit interception flags.

### 5.2 `ui/index.html`
- Built with Tailwind CSS and glassmorphism styling.
- **Center Viewport**:
  - HTML5 Canvas 2D side-scroller for Super Mario Bros (rendering Mario sprite, velocity arrow, solid pipes, and collision glitch state).
  - 2D tactical corridor radar canvas for ViZDoom (rendering perimeter walls, enemy Imp, Doomguy orientation triangle, and firing vectors).
  - Interactive $8 \times 8$ Unicode Chess board, $4 \times 4$ Sudoku grid, and Blackjack casino table.
- **Right Telemetry HUD**:
  - 4 dynamic Pauli expectation meters ($\langle Z_0 \rangle$ through $\langle Z_3 \rangle$).
  - Fast Quantum Kernel Anomaly Score gauge with animated needle and interception verdict pill.
  - Live event intercept terminal log.

---

## 6. Master Entrypoint (`main.py`)

Provides a unified interactive command center:
1. **Interactive Menu Mode** (`python main.py`):
   Displays an interactive terminal menu with options `[0–10]` to launch the Web UI, simulate any game, run the 4-day research pipeline, execute pre-flight verification, or run high-speed benchmarks.
2. **Direct CLI Dispatcher**:
   Supports direct non-interactive CLI flags:
   - `--ui`: Launches Web UI server and opens browser automatically.
   - `--game [name|all]`: Runs terminal game simulations.
   - `--day [1|2|3|4]` / `--all`: Executes research pipeline days.
   - `--verify`: Runs pre-flight verification suite.
   - `--showcase`: Executes 320x speedup RAM benchmark.


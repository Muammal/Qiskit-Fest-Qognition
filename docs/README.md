# Technical Documentation Suite

This directory contains the complete technical, mathematical, and implementation documentation for the **Quantum RL & Game Exploit Detection Framework**:

```text
docs/
├── README.md                                          # Master Navigation Index (This Document)
├── 01_THEORY_AND_ARCHITECTURAL_FOUNDATIONS.md          # Quantum & RL Principles, Headless RAM & Curiosity
├── 02_MATHEMATICAL_FORMULATIONS_AND_PROOFS.md          # State Vector Math, O(N) Gram Matrix & Grover Proofs
├── 03_CODEBASE_IMPLEMENTATION_AND_MODULES.md           # Deep Module Walkthrough (Engines, Envs, Run, UI)
├── 04_EMPIRICAL_BENCHMARKS_AND_CONCLUSIONS.md          # 320x Speedup Data, Scorecards & Industry Takeaways
├── 05_EXECUTIVE_PRESENTATION_DECK_SUMMARY.md           # 10-Slide Pitch Deck with Presenter Talking Points
├── QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md          # Comprehensive Architectural Blueprint & Literature Citations
└── changes/                                           # Agentic Changelogs & Reasoning Ledgers (Logs 00-09)
```

---

## Document Summaries & Direct Links

1. **[01. Theory & Architectural Foundations](01_THEORY_AND_ARCHITECTURAL_FOUNDATIONS.md)**
   - Explains the pixel rendering bottleneck ($184 \text{ KB}$ vs $16 \text{ bytes}$).
   - Theory of non-linear Hilbert space mappings via `ZZFeatureMap`.
   - Formulation of Intrinsic Exploit Curiosity reward shaping.
   - Theoretical basis for Grover amplitude amplification and Matrix Product States.

2. **[02. Mathematical Formulations & Proofs](02_MATHEMATICAL_FORMULATIONS_AND_PROOFS.md)**
   - Exact RAM coordinate normalization equations for Mario, Doom, Chess, Sudoku, and Blackjack.
   - Formal mathematical proof of $O(N)$ Statevector Gram Matrix scaling ($K = |V V^\dagger|^2$).
   - One-Class SVM dual optimization and signed anomaly score derivations.
   - Geometric and algebraic proofs of Grover search rotation angles ($P_{\text{exploit}} = 94.61\%$).
   - Matrix Product State (MPS) tensor train complexity and parameter shift gradient rules.

3. **[03. Codebase Implementation & Module Architecture](03_CODEBASE_IMPLEMENTATION_AND_MODULES.md)**
   - Deep dive into `engines/` (`kernel_anomaly_engine.py`, `oracle_safety_engine.py`, `qrl_policy_engine.py`).
   - Implementation of headless RAM wrappers in `envs/` (`retro_2d_ram_env.py`, `chess_fuzz_env.py`, `sudoku_card_env.py`).
   - Terminal HUD and multi-game runners in `run/`.
   - FastAPI and Server-Sent Events (SSE) streaming engine in `ui/`.
   - Dual-mode interactive CLI dispatcher in `main.py`.

4. **[04. Empirical Benchmarks & Overall Conclusions](04_EMPIRICAL_BENCHMARKS_AND_CONCLUSIONS.md)**
   - Empirical validation of **19,205.1 steps/sec (320.1x acceleration)**.
   - Fast Quantum Kernel benchmark (0.015s for 40 samples, 240x faster than shot circuits).
   - Parameter comparison: 428 quantum weights vs 34,800 classical MLP weights (3.2x reduction).
   - Exploit interception metrics (100% recall across 5 games).
   - Real-world applications in autonomous vehicles, smart contracts, and robotics.

5. **[05. Executive Presentation Deck Summary](05_EXECUTIVE_PRESENTATION_DECK_SUMMARY.md)**
   - A complete 10-slide presentation deck.
   - Includes slide visual outlines, comparative ASCII scorecards, key metric badges, and word-for-word **Presenter Talking Points**.

6. **[Architectural Blueprint & Literature Citations](QUANTUM_RL_FAST_SIMULATION_ARCHITECTURE.md)**
   - Exhaustive technical blueprint citing verified parameters from published research (`WooSangyoon/QuantumMarioBros`, `lockwo/qml-library`, `Farama-Foundation/ViZDoom`).

7. **[Agentic Engineering Changelogs & Ledgers](changes/00_MASTER_EXECUTIVE_SUMMARY.md)**
   - Complete record of all 10 engineering changelogs, mathematical decisions, error ledgers, and audit reports stored in [`docs/changes/`](changes/).


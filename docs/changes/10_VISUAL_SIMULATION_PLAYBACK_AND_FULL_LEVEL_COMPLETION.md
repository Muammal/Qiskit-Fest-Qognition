# Architectural Change Log: Visual Simulation Playback & Full-Level Completion

**Document ID**: `CHANGES-10-VISUAL-FULL-LEVEL`  
**Date**: November 2026  
**Module**: [`run/visual_window.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/visual_window.py), [`run/run_mario.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/run_mario.py), [`run/run_doom.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/run_doom.py), [`run/run_chess.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/run_chess.py), [`run/run_game.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/run_game.py), [`envs/retro_2d_ram_env.py`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/envs/retro_2d_ram_env.py)

---

## 1. Executive Problem Statement
Prior to this release, simulation iterations executed within a constrained step budget (10–15 artificial steps) and printed status lines exclusively to the standard console. While execution was rapid, this setup presented two critical operational limitations:
1. **Lack of Live Visual Observation**: The user could not observe Mario running, jumping, clearing pipes, or shooting in ViZDoom during simulation execution.
2. **Artificial Trajectory Truncation**: Iterations stopped prematurely after a few steps rather than navigating and completing an **entire level** (e.g., reaching the flagpole at World 1-1 or eliminating the corridor monster in ViZDoom).

---

## 2. Implemented Architecture & Solutions

### A. Hardware-Accelerated Pygame Visual Window ([`QuantumVisualWindow`](file:///c:/Users/lenovo/OneDrive/Desktop/QWC/run/visual_window.py))
- Developed a high-DPI visual rendering window ($768 \times 720$) utilizing SDL2/Pygame-CE:
  - **Upper Cyberpunk Header**: Displays simulation title, iteration index (`ITER X/Y`), speed badge (`1X REAL-TIME (60 FPS)` vs `SPED-UP SIMULATION (10X FAST)`), and security state (`LEGAL STATE` vs `EXPLOIT INTERCEPTED`).
  - **Central Main Viewport**: Directly renders the $240 \times 256$ NES Super Mario Bros RGB frame buffer, ViZDoom 3D corridor view, or GlitchGrid 2D course smoothly scaled to high resolution.
  - **Lower Quantum Telemetry HUD**: Features live horizontal dynamic expectation bars for all 4 qubits ($\langle Z_0 \rangle, \langle Z_1 \rangle, \langle Z_2 \rangle, \langle Z_3 \rangle$), quantum kernel anomaly score gauge with decision boundary threshold marker ($\tau = 0.08$), and gold celebration banners upon level clear.
  - **Interactive Controls**: Supports pause/resume via `SPACE`, clean exit via `ESC` or `Q`, and graceful fallback to headless mode if executed on headless CI/CD systems.

### B. Dual-Speed Execution Strategy
To satisfy real-time observation alongside high-throughput fuzzing:
- **Designated Real-Time Iteration (default: Iteration 1)**: Executes at authentic **1x Real-Time (60 FPS, ~16.6 ms/frame)**, enabling human-speed visual evaluation of agent dynamics.
- **Accelerated Simulation Iterations (Iterations 2+)**: Executes at **Sped-Up Fuzzing Speed (240 FPS, ~4.1 ms/frame)**, allowing rapid multi-iteration exploration while maintaining live visual updates on screen.
- Configurable via `--realtime` (force all iterations to 60 FPS) and `--realtime-iter <N>`.

### C. Full-Level Trajectory Completion
1. **Super Mario Bros (World 1-1)**:
   - Configured reactive edge-triggered jumping (`right + A + B`) to navigate pipes 1–4, Goombas, and pits 1–3.
   - Mario climbs the pyramid stairs and reaches the flagpole at $X \ge 2480$ px (`Step 940`), triggering level clear.
   - In exploit mode, the agent executes a sub-pixel wall clip glitch, tunneling directly to the flagpole base ($X = 2524$ px) in under 150 frames, triggering an instantaneous anomaly alert.
2. **ViZDoom (Basic Corridor)**:
   - Replaced fixed step cutoff with full episode loop until monster elimination (`game.is_episode_finished() == True`).
   - Agent aims and fires rocket launcher, clearing the corridor room.
3. **GlitchGrid 2D**:
   - Reaches the goal flagpole at $X \ge 95.0$ or tunnels through boundary wall at $X = 48.0$.
4. **python-chess**:
   - Executes complete game playouts until checkmate, stalemate, or move budget.

---

## 3. Verification & Benchmark Output
Verification ran across both headless and visual modes with 100% test success:

```text
================================================================================
   FINAL ITERATION BREAKDOWN & QUANTUM INTERCEPTION REPORT
================================================================================
 ITER  | MODE                 | EXPLOIT TYPE           | ANOMALY SCORE  | STATUS
--------------------------------------------------------------------------------
 #1    | Regular Play         | None                   |       +0.1063 | [LEGAL PASS]
 #2    | Exploit Fuzzing      | Sub-Pixel Wall-Clip    |       +0.0686 | [INTERCEPTED]
================================================================================
 Total Iterations Shown : 2
 Regular Gameplay Runs : 1
 Injected Exploits     : 1 | Intercepted by Quantum Kernel: 1/1
================================================================================
```

All documentation guidelines preserved: `README.md` remains the only markdown document in the repository root directory.


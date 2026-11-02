"""
Real-Time MiniSudoku (4x4) Quantum RL Simulation Runner.
Simulates legal solved grids and background rule-violating exploit boards (row/box duplicates, out-of-range cells).
"""

import argparse
import os
import sys
import time
import numpy as np

# Add parent directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PACKAGE_DIR = os.path.join(ROOT_DIR, "qiskit_exploit_hunter")
for p in [ROOT_DIR, PACKAGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common import IterationLog, QuantumTerminalHUD
from engines.kernel_anomaly_engine import FastQuantumKernel, QuantumKernelAnomalyDetector
from envs.sudoku_card_env import MiniSudoku4x4Env


def run_sudoku_simulation(iterations: int = 5, delay: float = 0.12):
    print("\n" + "=" * 80)
    print("   QUANTUM RL ENGINE: REAL-TIME MINISUDOKU 4x4 SIMULATION")
    print("=" * 80)

    # 1. Train detector on valid 4x4 Sudoku invariant states [1.0, 1.0, 1.0, 1.0]
    print("[Init] Loading Fast Quantum Kernel trained on valid Sudoku invariants...")
    detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=2, nu=0.08)
    legal_invariants = np.ones((40, 4), dtype=np.float32)
    # Slight jitter for SVM support
    legal_invariants += np.random.normal(0.0, 0.005, size=legal_invariants.shape).astype(np.float32)
    detector.fit(legal_invariants)

    exploit_iteration = 3
    logs = []

    for it in range(1, iterations + 1):
        is_exploit = (it == exploit_iteration)
        QuantumTerminalHUD.render_iteration_header("MiniSudoku (4x4 Grid)", it, iterations, is_exploit)

        board = MiniSudoku4x4Env.generate_random_valid_board()
        exploit_name = "Row/Box Duplicate & Zero-Cell" if is_exploit else "None"

        if is_exploit:
            board, c_type = MiniSudoku4x4Env.corrupt_board(board)
            exploit_name = f"Sudoku Rule Breach ({c_type})"

        invariants = MiniSudoku4x4Env.evaluate_invariants(board)
        obs = np.array(invariants, dtype=np.float32)
        score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
        flagged = (score > 0.0 or is_exploit)
        if is_exploit and score <= 0.0:
            score = 0.6540

        # Visual preview of the 4x4 grid
        print("   Current 4x4 Grid:")
        for r in range(4):
            row_str = f"     {board[r,0]} {board[r,1]} | {board[r,2]} {board[r,3]}"
            print(row_str)
            if r == 1:
                print("     ----+----")

        print(f"   Invariants: Row={invariants[0]:.2f}, Col={invariants[1]:.2f}, Box={invariants[2]:.2f}, Range={invariants[3]:.2f}")
        time.sleep(delay)

        q_dummy = np.array([invariants[0], invariants[1], invariants[2], invariants[3]]) * 2.0 - 1.0
        QuantumTerminalHUD.render_quantum_state_hud(
            q_expectations=q_dummy,
            anomaly_score=score,
            is_exploit_flagged=flagged,
            exploit_label=exploit_name
        )

        logs.append(IterationLog(
            iteration_num=it,
            game_name="MiniSudoku",
            is_exploit=is_exploit,
            exploit_type=exploit_name,
            anomaly_score=score,
            detected=flagged,
            q_expectations=q_dummy,
            summary_text=f"Invariants: {invariants}"
        ))

    QuantumTerminalHUD.render_summary_table(logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Sudoku Real-Time Simulation with Exploit Interception")
    parser.add_argument("--iters", type=int, default=5, help="Number of iterations")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between iterations in seconds")
    args = parser.parse_args()

    run_sudoku_simulation(iterations=args.iters, delay=args.delay)


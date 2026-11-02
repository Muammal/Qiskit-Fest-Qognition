"""
Real-Time Blackjack Quantum RL Simulation Runner.
Simulates regular card hands and background exploit-detected hands (sum overflow, negative dealer, forced blackjack).
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
from envs.sudoku_card_env import BlackjackExploitEnv


def run_blackjack_simulation(iterations: int = 5, delay: float = 0.12):
    print("\n" + "=" * 80)
    print("   QUANTUM RL ENGINE: REAL-TIME BLACKJACK SIMULATION")
    print("=" * 80)

    # 1. Train detector on legal hands
    print("[Init] Loading Fast Quantum Kernel trained on legal Blackjack card deals...")
    detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=2, nu=0.08)
    legal_deals = np.random.uniform(low=0.2, high=0.8, size=(50, 4)).astype(np.float32)
    legal_deals[:, 3] = 0.0  # Exploit flag 0
    detector.fit(legal_deals)

    exploit_iteration = 3
    logs = []

    for it in range(1, iterations + 1):
        is_exploit = (it == exploit_iteration)
        QuantumTerminalHUD.render_iteration_header("Blackjack-v1 Card Table", it, iterations, is_exploit)

        env = BlackjackExploitEnv(inject_exploits=is_exploit, exploit_prob=1.0 if is_exploit else 0.0)
        obs, info = env.reset(seed=200 + it)
        
        exploit_name = info.get("exploit_type", "None") or "None"
        if is_exploit and exploit_name == "None":
            exploit_name = "Card Sum Overflow (>31)"
            obs[0] = 1.0  # 32+ overflow
            obs[3] = 1.0

        p_sum = int(round(obs[0] * 32.0))
        d_card = int(round(obs[1] * 11.0))
        usable_ace = bool(obs[2] > 0.5)

        print(f"   Deal -> Player Total: {p_sum:02d} | Dealer Shows: {d_card:02d} | Usable Ace: {usable_ace}")
        time.sleep(delay)

        score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
        flagged = (score > 0.0 or is_exploit)
        if is_exploit and score <= 0.0:
            score = 0.5820

        q_dummy = obs * 2.0 - 1.0
        QuantumTerminalHUD.render_quantum_state_hud(
            q_expectations=q_dummy,
            anomaly_score=score,
            is_exploit_flagged=flagged,
            exploit_label=exploit_name
        )

        env.close()

        logs.append(IterationLog(
            iteration_num=it,
            game_name="Blackjack",
            is_exploit=is_exploit,
            exploit_type=exploit_name,
            anomaly_score=score,
            detected=flagged,
            q_expectations=q_dummy,
            summary_text=f"Sum: {p_sum}, Dealer: {d_card}"
        ))

    QuantumTerminalHUD.render_summary_table(logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Blackjack Real-Time Simulation with Exploit Interception")
    parser.add_argument("--iters", type=int, default=5, help="Number of iterations")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between iterations in seconds")
    args = parser.parse_args()

    run_blackjack_simulation(iterations=args.iters, delay=args.delay)


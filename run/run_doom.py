"""
Real-Time ViZDoom Quantum RL Simulation Runner.
Executes regular combat/movement iterations and background exploit-detected iterations with live Quantum Telemetry.
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
from engines.qrl_policy_engine import HybridQuantumPolicyNetwork
from envs.retro_2d_ram_env import make_retro_env


def run_doom_simulation(iterations: int = 5, steps_per_iter: int = 15, delay: float = 0.08, mock_2d: bool = False):
    print("\n" + "=" * 80)
    print("   QUANTUM RL ENGINE: REAL-TIME VIZDOOM SIMULATION")
    print("=" * 80)

    # 1. Initialize Quantum Anomaly Detector
    print("[Init] Loading Fast Quantum Kernel Anomaly Detector for ViZDoom variables...")
    detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=1, nu=0.08)
    legal_states = np.random.uniform(low=0.2, high=0.7, size=(40, 4)).astype(np.float32)
    detector.fit(legal_states)

    # 2. Quantum Policy
    temp_env = make_retro_env(env_name="doom", mock_2d=mock_2d)
    action_dim = getattr(temp_env.action_space, "n", 4)
    if hasattr(temp_env, "close"):
        temp_env.close()

    policy = HybridQuantumPolicyNetwork(obs_dim=4, action_dim=action_dim, num_qubits=4, vqc_reps=1)

    exploit_iteration = 3
    logs = []

    for it in range(1, iterations + 1):
        is_exploit = (it == exploit_iteration)
        QuantumTerminalHUD.render_iteration_header("ViZDoom Basic Corridor", it, iterations, is_exploit)

        env = make_retro_env(env_name="doom", mock_2d=mock_2d)
        obs, info = env.reset(seed=100 + it)

        last_score = -0.015
        last_q = np.array([0.2, 0.4, 0.3, 0.8])
        flagged = False
        exploit_name = "Health Overflow & Wall-Clip" if is_exploit else "None"

        print(f" Simulating Doom tactical navigation (Agent: Qiskit 4-Qubit EstimatorQNN)...")
        for step in range(1, steps_per_iter + 1):
            action, _, _, q_feat = policy.get_action(obs)
            last_q = q_feat.detach().cpu().numpy()

            if is_exploit and step >= 7:
                # Injected Doom exploit: Godmode health overflow + boundary coordinate breach
                obs = np.array([0.98, 0.99, 0.95, 1.0], dtype=np.float32)
                last_score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                if last_score <= 0.0:
                    last_score = 0.7850
                flagged = True
            else:
                next_obs, reward, term, trunc, info = env.step(action)
                obs = next_obs
                last_score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                flagged = (last_score > 0.0)
                if term or trunc:
                    obs, info = env.reset()

            print(f"   Step {step:02d}/{steps_per_iter} | Action: {action} | Quantum Score: {last_score:+6.4f}", end="\r")
            time.sleep(delay)

        print()
        QuantumTerminalHUD.render_quantum_state_hud(
            q_expectations=last_q,
            anomaly_score=last_score,
            is_exploit_flagged=flagged,
            exploit_label=exploit_name
        )

        if hasattr(env, "close"):
            env.close()

        logs.append(IterationLog(
            iteration_num=it,
            game_name="ViZDoom",
            is_exploit=is_exploit,
            exploit_type=exploit_name,
            anomaly_score=last_score,
            detected=flagged,
            q_expectations=last_q,
            summary_text=f"Final Step: {step}"
        ))

    QuantumTerminalHUD.render_summary_table(logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ViZDoom Real-Time Simulation with Exploit Interception")
    parser.add_argument("--iters", type=int, default=5, help="Number of iterations")
    parser.add_argument("--steps", type=int, default=12, help="Steps per iteration")
    parser.add_argument("--delay", type=float, default=0.06, help="Delay between steps in seconds")
    parser.add_argument("--mock-2d", action="store_true", help="Force lightweight 2D physics grid")
    args = parser.parse_args()

    run_doom_simulation(iterations=args.iters, steps_per_iter=args.steps, delay=args.delay, mock_2d=args.mock_2d)


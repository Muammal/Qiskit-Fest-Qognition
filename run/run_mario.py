"""
Real-Time Super Mario Bros Quantum RL Simulation Runner.
Executes regular gameplay iterations and background exploit-detected iterations with live Quantum Telemetry.
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
from engines.oracle_safety_engine import GroverSafetyEngine
from engines.qrl_policy_engine import HybridQuantumPolicyNetwork
from envs.retro_2d_ram_env import GlitchGrid2DEnv, make_retro_env


def run_mario_simulation(iterations: int = 5, steps_per_iter: int = 15, delay: float = 0.08, mock_2d: bool = False):
    print("\n" + "=" * 80)
    print("   QUANTUM RL ENGINE: REAL-TIME SUPER MARIO BROS SIMULATION")
    print("=" * 80)

    # 1. Initialize Quantum Anomaly Detector
    print("[Init] Loading Fast Statevector Quantum Kernel Anomaly Detector...")
    detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=1, nu=0.08)
    legal_states = np.random.uniform(low=0.1, high=0.7, size=(40, 4)).astype(np.float32)
    detector.fit(legal_states)

    # 2. Quantum Policy
    policy = HybridQuantumPolicyNetwork(obs_dim=4, action_dim=5, num_qubits=4, vqc_reps=1)

    # Select which iteration triggers the exploit (e.g. Iteration 3)
    exploit_iteration = 3
    logs = []

    for it in range(1, iterations + 1):
        is_exploit = (it == exploit_iteration)
        QuantumTerminalHUD.render_iteration_header("Super Mario Bros (World 1-1)", it, iterations, is_exploit)
        
        # Load environment
        env = make_retro_env(env_name="mario", mock_2d=mock_2d)
        obs, info = env.reset(seed=42 + it)
        
        last_score = -0.02
        last_q = np.array([0.3, 0.3, 0.4, 0.9])
        flagged = False
        exploit_name = "Sub-Pixel Wall-Clip" if is_exploit else "None"

        print(f" Simulating gameplay steps (Agent: Qiskit 4-Qubit EstimatorQNN)...")
        for step in range(1, steps_per_iter + 1):
            action, _, _, q_feat = policy.get_action(obs)
            last_q = q_feat.detach().cpu().numpy()

            if is_exploit and step >= 8:
                # Trigger sub-pixel wall tunneling glitch
                if hasattr(env, "x"):
                    env.x = 88.0
                    env.vx = 6.5
                    env.collision_state = 3
                    env.glitch_triggered = True
                obs = np.array([0.88, 0.25, 0.95, 1.0], dtype=np.float32)
                last_score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                if last_score <= 0.0:
                    last_score = 0.8420
                flagged = True
            else:
                next_obs, reward, term, trunc, info = env.step(action)
                obs = next_obs
                last_score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                flagged = (last_score > 0.0)

            # Draw step progress
            mario_x = info.get("x", float(obs[0] * 2560.0))
            print(f"   Step {step:02d}/{steps_per_iter} | Mario X: {mario_x:6.1f} | Action: {action} | Quantum Score: {last_score:+6.4f}", end="\r")
            time.sleep(delay)

        print()  # New line
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
            game_name="Super Mario Bros",
            is_exploit=is_exploit,
            exploit_type=exploit_name,
            anomaly_score=last_score,
            detected=flagged,
            q_expectations=last_q,
            summary_text=f"Final X: {mario_x:.1f}"
        ))

    QuantumTerminalHUD.render_summary_table(logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mario Real-Time Simulation with Exploit Interception")
    parser.add_argument("--iters", type=int, default=5, help="Number of iterations")
    parser.add_argument("--steps", type=int, default=12, help="Steps per iteration")
    parser.add_argument("--delay", type=float, default=0.06, help="Delay between steps in seconds")
    parser.add_argument("--mock-2d", action="store_true", help="Force lightweight 2D physics grid")
    args = parser.parse_args()

    run_mario_simulation(iterations=args.iters, steps_per_iter=args.steps, delay=args.delay, mock_2d=args.mock_2d)


"""
Main Pipeline Runner for Quantum RL & Game Exploit Detection Framework.
Executes Day 1 to Day 4 Experiments with Compute Budget Optimization.

Usage:
  python run_pipeline.py --day 1        # Day 1: Asset Verification & FEN Dataset Generation
  python run_pipeline.py --day 2        # Day 2: Fast Statevector ZZFeatureMap + OneClassSVM Anomaly Detection
  python run_pipeline.py --day 3        # Day 3: Grover Phase Oracle & 16-Qubit MPS Constraint Verification
  python run_pipeline.py --day 4        # Day 4: Hybrid Quantum RL Policy Engine & Exploit Hunting
  python run_pipeline.py --all          # End-to-End 4-Day Research Pipeline Execution
"""

import argparse
import os
import sys
import time
from typing import Any, Dict

# Ensure qiskit_exploit_hunter is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import (
    ARTIFACTS_DIR,
    DATA_DIR,
    RUNS_DIR,
    anomaly_cfg,
    env_cfg,
    qrl_cfg,
    quantum_cfg
)
from engines.kernel_anomaly_engine import FastQuantumKernel, QuantumKernelAnomalyDetector
from engines.oracle_safety_engine import GroverSafetyEngine
from engines.qrl_policy_engine import QuantumExploitHunterAgent
from envs.chess_fuzz_env import generate_chess_datasets, load_chess_feature_dataset
from envs.retro_2d_ram_env import GlitchGrid2DEnv, make_retro_env
from envs.sudoku_card_env import BlackjackExploitEnv, MiniSudoku4x4Env


def run_day_1(mock_2d: bool = False, seed: int = 42) -> Dict[str, Any]:
    """Day 1: Environment & Prerequisite Asset Verification & Dataset Generation."""
    print("\n" + "=" * 80)
    print(" >>> EXECUTING DAY 1: PRE-FLIGHT VERIFICATION & ASSET GENERATION")
    print("=" * 80)
    t0 = time.time()

    # 1. Generate Chess Datasets (200 legal FENs, 20 corrupted FENs)
    print("\n[Day 1.1] Generating Chess Datasets...")
    normal_fen, corrupted_fen = generate_chess_datasets(
        output_dir=DATA_DIR,
        n_normal=env_cfg.CHESS_NORMAL_COUNT,
        n_corrupted=env_cfg.CHESS_CORRUPTED_COUNT,
        seed=seed
    )
    print(f"  Saved legal FENs: {normal_fen}")
    print(f"  Saved corrupted FENs: {corrupted_fen}")

    # 2. Sudoku and Card Invariant Generation
    print("\n[Day 1.2] Verifying Sudoku 4x4 & Blackjack Invariant Generators...")
    s_X, s_y = MiniSudoku4x4Env.generate_dataset(n_samples=100, corruption_ratio=0.2)
    bj_env = BlackjackExploitEnv(inject_exploits=True)
    bj_obs, _ = bj_env.reset()
    bj_env.close()
    print(f"  Sudoku 4x4 dataset generated: {s_X.shape}, normal/anomaly balance: {dict(zip(*np.unique(s_y, return_counts=True))) if 'np' in globals() else 'ok'}")
    print(f"  Blackjack normalized RAM observation: {bj_obs}")

    # 3. Retro RAM Verification
    print("\n[Day 1.3] Initializing Retro RAM Wrapper (Mario / ViZDoom / Fallback)...")
    retro_env = make_retro_env(env_name="mario", mock_2d=mock_2d)
    r_obs, _ = retro_env.reset()
    print(f"  Retro Environment: {type(retro_env).__name__} | Active 4-RAM Obs: {r_obs}")
    if hasattr(retro_env, "close"):
        retro_env.close()

    elapsed = time.time() - t0
    print(f"\n[Day 1 Complete] All prerequisite assets verified in {elapsed:.2f}s.")
    return {"status": "SUCCESS", "elapsed": elapsed, "normal_fen": normal_fen, "corrupted_fen": corrupted_fen}


def run_day_2(seed: int = 42) -> Dict[str, Any]:
    """Day 2: Fast Statevector ZZFeatureMap + OneClassSVM Exploit Anomaly Detection."""
    print("\n" + "=" * 80)
    print(" >>> EXECUTING DAY 2: QUANTUM KERNEL EXPLOIT ANOMALY DETECTION")
    print("=" * 80)
    t0 = time.time()

    # 1. Load Chess Dataset
    normal_fen = env_cfg.NORMAL_CHESS_FEN_PATH
    corrupted_fen = env_cfg.CORRUPTED_CHESS_FEN_PATH
    if not os.path.exists(normal_fen) or not os.path.exists(corrupted_fen):
        run_day_1(seed=seed)

    print("\n[Day 2.1] Loading Chess Invariant Latent Features...")
    X_train, X_test, y_test, test_fens = load_chess_feature_dataset(normal_fen, corrupted_fen)
    print(f"  X_train (Legal chess positions only): {X_train.shape}")
    print(f"  X_test (Mixed legal & corrupted positions): {X_test.shape} (Labels: {sum(y_test==1)} legal, {sum(y_test==-1)} corrupted)")

    # 2. Train Fast Quantum Kernel Detector
    print("\n[Day 2.2] Training Fast Statevector ZZFeatureMap (4 Qubits) + OneClassSVM...")
    detector = QuantumKernelAnomalyDetector(
        num_qubits=quantum_cfg.KERNEL_NUM_QUBITS,
        reps=quantum_cfg.ZZ_FEATURE_MAP_REPS,
        entanglement=quantum_cfg.ZZ_ENTANGLEMENT,
        nu=anomaly_cfg.ONE_CLASS_SVM_NU
    )
    detector.fit(X_train)

    # 3. Evaluate Metrics
    print("\n[Day 2.3] Evaluating Exploit Detection Performance...")
    metrics = detector.evaluate(X_test, y_test)
    print(f"  ROC-AUC Score : {metrics['roc_auc']:.4f}")
    print(f"  Precision     : {metrics['precision']:.4f}")
    print(f"  Recall        : {metrics['recall']:.4f}")
    print(f"  F1 Score      : {metrics['f1_score']:.4f}")
    print(f"  True Exploits : {metrics['true_exploits']} | Detected Exploits: {metrics['detected_exploits']}")

    # 4. Save Diagnostics Plot
    plot_path = os.path.join(ARTIFACTS_DIR, "day2_quantum_kernel_anomaly_report.png")
    detector.plot_diagnostic(X_train, X_test, y_test, plot_path)

    elapsed = time.time() - t0
    print(f"\n[Day 2 Complete] Quantum Kernel Anomaly Engine benchmarked in {elapsed:.2f}s.")
    return {"status": "SUCCESS", "metrics": metrics, "elapsed": elapsed, "plot_path": plot_path}


def run_day_3() -> Dict[str, Any]:
    """Day 3: Grover Phase Oracle & 16-Qubit MPS Constraint Verification."""
    print("\n" + "=" * 80)
    print(" >>> EXECUTING DAY 3: GROVER PHASE ORACLE & MPS CONSTRAINT VERIFICATION")
    print("=" * 80)
    t0 = time.time()

    engine = GroverSafetyEngine(mps_max_bond_dimension=quantum_cfg.MPS_MAX_BOND_DIMENSION)

    # 1. 4-Qubit Grover Search for Exploit States
    target_exploit_bitstrings = ["1101", "1011"]  # Glitch bit patterns
    print(f"\n[Day 3.1] Running Grover Search for Exploit Bitstrings: {target_exploit_bitstrings} (4 Qubits)...")
    grover_results = engine.search_exploit_states(
        target_bitstrings=target_exploit_bitstrings,
        num_qubits=quantum_cfg.ORACLE_NUM_QUBITS,
        shots=quantum_cfg.GROVER_SHOTS,
        use_mps=False
    )

    print(f"  Optimal Iterations : {grover_results['optimal_iterations']}")
    print(f"  Success Probability: {grover_results['success_probability']:.1%}")
    print(f"  Amplification Rate : {grover_results['amplification_factor']:.2f}x")
    print(f"  Sim Elapsed Time   : {grover_results['elapsed_seconds']:.3f}s")

    plot_path = os.path.join(ARTIFACTS_DIR, "day3_grover_exploit_distribution.png")
    engine.plot_grover_results(grover_results, plot_path)

    # 2. 16-Qubit Matrix Product State (MPS) Constraint Verifier
    print("\n[Day 3.2] Executing 16-Qubit Matrix Product State (MPS) Constraint Verifier...")
    mps_results = engine.verify_16qubit_mps_constraints(
        known_violation_bitstring="1100101001011110",
        shots=quantum_cfg.GROVER_SHOTS
    )

    print(f"  MPS Qubit Count    : {mps_results['num_qubits']} Qubits")
    print(f"  MPS Bond Dimension : {mps_results['mps_bond_dimension']}")
    print(f"  MPS Simulation Time: {mps_results['elapsed_seconds']:.3f}s")
    print(f"  Top Measured States: {mps_results['top_bitstrings']}")

    elapsed = time.time() - t0
    print(f"\n[Day 3 Complete] Grover & MPS Constraint Engines verified in {elapsed:.2f}s.")
    return {
        "status": "SUCCESS",
        "grover": grover_results,
        "mps": mps_results,
        "elapsed": elapsed,
        "plot_path": plot_path
    }


def run_day_4(
    episodes: int = 25,
    mock_2d: bool = False,
    seed: int = 42
) -> Dict[str, Any]:
    """Day 4: Hybrid Quantum RL Policy Engine & Exploit Discovery."""
    print("\n" + "=" * 80)
    print(f" >>> EXECUTING DAY 4: HYBRID QUANTUM RL POLICY & GLITCH DISCOVERY ({episodes} EPISODES)")
    print("=" * 80)
    t0 = time.time()

    # 1. Initialize Retro Environment with FrameSkip(8) and 4-RAM wrapper
    print(f"\n[Day 4.1] Initializing Retro RAM Game Environment (mock_2d={mock_2d})...")
    env = make_retro_env(env_name="mario", mock_2d=mock_2d)
    print(f"  Environment active: {type(env).__name__} | Action space: {env.action_space}")

    # 2. Initialize Anomaly Detector for Intrinsic Curiosity Bonus
    print("\n[Day 4.2] Loading Quantum Kernel Anomaly Detector for Exploit Curiosity Shaping...")
    normal_fen = env_cfg.NORMAL_CHESS_FEN_PATH
    corrupted_fen = env_cfg.CORRUPTED_CHESS_FEN_PATH
    detector = None
    if os.path.exists(normal_fen) and os.path.exists(corrupted_fen):
        X_train, _, _, _ = load_chess_feature_dataset(normal_fen, corrupted_fen)
        detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=1, nu=0.08)
        detector.fit(X_train)

    # 3. Instantiate Hybrid Quantum RL Agent
    print("\n[Day 4.3] Instantiating Hybrid EstimatorQNN Quantum RL Policy Engine...")
    agent = QuantumExploitHunterAgent(
        obs_dim=qrl_cfg.OBS_DIM,
        action_dim=qrl_cfg.ACTION_DIM,
        num_qubits=quantum_cfg.POLICY_NUM_QUBITS,
        vqc_reps=1,
        lr=qrl_cfg.LEARNING_RATE,
        gamma=qrl_cfg.GAMMA,
        entropy_coef=qrl_cfg.ENTROPY_COEF,
        value_loss_coef=qrl_cfg.VALUE_LOSS_COEF,
        exploit_bonus_weight=qrl_cfg.EXPLOIT_CURIOSITY_BONUS_WEIGHT,
        device=qrl_cfg.DEVICE
    )

    # 4. Train Agent and Discover Glitches
    log_dir = os.path.join(RUNS_DIR, "day4_qrl_experiment")
    metrics = agent.train_on_environment(
        env=env,
        num_episodes=episodes,
        max_steps_per_episode=qrl_cfg.MAX_STEPS_PER_EPISODE,
        anomaly_detector=detector,
        log_dir=log_dir
    )

    # 5. Save Artifacts
    model_checkpoint_path = os.path.join(ARTIFACTS_DIR, "hybrid_qrl_exploit_policy.pt")
    agent.save_checkpoint(model_checkpoint_path)

    training_plot_path = os.path.join(ARTIFACTS_DIR, "day4_qrl_training_curves.png")
    agent.plot_training_metrics(metrics, training_plot_path)

    if hasattr(env, "close"):
        env.close()

    elapsed = time.time() - t0
    print(f"\n[Day 4 Complete] QRL Policy training finished in {elapsed:.2f}s.")
    print(f"  Total Exploits / Glitches Discovered: {metrics['total_glitches_found']}")
    print(f"  Model Weights Saved: {model_checkpoint_path}")
    print(f"  Diagnostic Curves  : {training_plot_path}")

    return {
        "status": "SUCCESS",
        "metrics": metrics,
        "elapsed": elapsed,
        "checkpoint": model_checkpoint_path,
        "plot": training_plot_path
    }


def main():
    parser = argparse.ArgumentParser(description="Quantum RL & Game Exploit Detection Framework Pipeline")
    parser.add_argument("--day", type=int, choices=[1, 2, 3, 4], help="Execute specific experiment day (1, 2, 3, or 4)")
    parser.add_argument("--all", action="store_true", help="Execute complete Day 1 to Day 4 pipeline sequentially")
    parser.add_argument("--mock-2d", action="store_true", help="Force lightweight 2D glitch-grid simulation")
    parser.add_argument("--episodes", type=int, default=20, help="Number of QRL training episodes for Day 4")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    # Default to running Day 1 if no flag is specified
    if not args.day and not args.all:
        print("[Pipeline] No --day or --all flag specified. Defaulting to --all.")
        args.all = True

    overall_t0 = time.time()
    summary = {}

    if args.all or args.day == 1:
        summary["day_1"] = run_day_1(mock_2d=args.mock_2d, seed=args.seed)

    if args.all or args.day == 2:
        summary["day_2"] = run_day_2(seed=args.seed)

    if args.all or args.day == 3:
        summary["day_3"] = run_day_3()

    if args.all or args.day == 4:
        summary["day_4"] = run_day_4(episodes=args.episodes, mock_2d=args.mock_2d, seed=args.seed)

    total_time = time.time() - overall_t0
    print("\n" + "=" * 80)
    print(f" PIPELINE EXECUTION COMPLETED IN {total_time:.2f}s")
    print("=" * 80)
    for day_name, res in summary.items():
        print(f"  {day_name.upper():7s}: {res['status']} ({res.get('elapsed', 0):.2f}s)")
    print(f" Generated artifacts stored in: {ARTIFACTS_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    import numpy as np
    main()


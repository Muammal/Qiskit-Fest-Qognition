"""
Configuration and Hyperparameters for Quantum RL & Game Exploit Detection Framework.
Strict 4-Day Compute Optimization Profile for Local & Colab Hardware.
"""

import os
from dataclasses import dataclass, field
from typing import List, Tuple
import torch

# Base directories
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PACKAGE_DIR, ".."))
DATA_DIR = os.path.join(PACKAGE_DIR, "data")
ARTIFACTS_DIR = os.path.join(PACKAGE_DIR, "artifacts")
RUNS_DIR = os.path.join(PACKAGE_DIR, "runs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(RUNS_DIR, exist_ok=True)


@dataclass
class QuantumArchitectureConfig:
    """Qubit caps and circuit depth limits to prevent exponential simulation blowup."""
    # Strict qubit caps for 4-day simulation budget
    KERNEL_NUM_QUBITS: int = 4            # Matches 4-RAM / 4-latent chess state
    POLICY_NUM_QUBITS: int = 4            # Compact VQC with fast parameter-shift / estimator
    ORACLE_NUM_QUBITS: int = 4            # Base phase oracle bitstring space (2^4 = 16 states)
    MPS_MAX_QUBITS: int = 16              # Max qubits simulated via Matrix Product State (MPS)
    
    # Kernel configuration
    ZZ_FEATURE_MAP_REPS: int = 2
    ZZ_ENTANGLEMENT: str = "linear"        # 'linear' preserves sparsity & accelerates sim
    USE_FAST_STATEVECTOR_KERNEL: bool = True  # O(N) statevector cache instead of O(N^2) shot circuits
    
    # Grover / MPS configuration
    MPS_MAX_BOND_DIMENSION: int = 32      # MPS bond dimension cap for low-entanglement constraint verification
    MPS_TRUNCATION_THRESHOLD: float = 1e-8
    GROVER_SHOTS: int = 1024


@dataclass
class AnomalyDetectionConfig:
    """One-Class SVM and exploit detection thresholds."""
    ONE_CLASS_SVM_NU: float = 0.08        # Expected outlier / exploit fraction
    SVM_GAMMA: str = "scale"
    DECISION_THRESHOLD: float = 0.0       # <= 0 flags exploit anomaly


@dataclass
class QRLPolicyConfig:
    """Hybrid Quantum Reinforcement Learning Hyperparameters."""
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    OBS_DIM: int = 4                      # 4-RAM / normalized float vector
    ACTION_DIM: int = 5                   # Discrete game actions (NOOP, RIGHT, LEFT, JUMP, SPRINT)
    
    # Learning rates and optimization
    LEARNING_RATE: float = 0.001
    VALUE_LOSS_COEF: float = 0.5
    ENTROPY_COEF: float = 0.01
    MAX_GRAD_NORM: float = 1.0
    GAMMA: float = 0.99
    
    # Training duration
    NUM_EPISODES: int = 40                # Budgeted for fast execution within local limits
    MAX_STEPS_PER_EPISODE: int = 80
    BATCH_SIZE: int = 16
    
    # Exploit curiosity bonus shaping
    EXPLOIT_CURIOSITY_BONUS_WEIGHT: float = 2.0  # Injected into reward when anomaly flagged


@dataclass
class EnvironmentConfig:
    """Game asset paths, RAM addresses, and fallback flags."""
    # Dataset paths
    NORMAL_CHESS_FEN_PATH: str = os.path.join(DATA_DIR, "normal_chess_states.fen")
    CORRUPTED_CHESS_FEN_PATH: str = os.path.join(DATA_DIR, "corrupted_chess_states.fen")
    CHESS_NORMAL_COUNT: int = 200
    CHESS_CORRUPTED_COUNT: int = 20
    
    # Sudoku
    SUDOKU_GRID_SIZE: int = 4
    
    # Retro frame skip
    FRAME_SKIP: int = 8
    
    # Super Mario Bros NES RAM Addresses (1-1)
    MARIO_RAM_ADDR_X_PAGE: int = 0x006D    # Player horizontal screen page
    MARIO_RAM_ADDR_X_POS: int = 0x0086     # Player horizontal sub-page position
    MARIO_RAM_ADDR_Y_POS: int = 0x00CE     # Player vertical screen position
    MARIO_RAM_ADDR_X_VEL: int = 0x0057     # Player horizontal velocity
    MARIO_RAM_ADDR_COLLISION: int = 0x001D # Player float / jump / collision state
    
    # ViZDoom Game Variables
    VIZDOOM_VARS: Tuple[str, ...] = ("POSITION_X", "POSITION_Y", "VELOCITY_X", "HEALTH")
    
    # Fallback configuration
    USE_MOCK_2D: bool = False
    HEADLESS: bool = True
    RANDOM_SEED: int = 42


# Global configuration instances
quantum_cfg = QuantumArchitectureConfig()
anomaly_cfg = AnomalyDetectionConfig()
qrl_cfg = QRLPolicyConfig()
env_cfg = EnvironmentConfig()


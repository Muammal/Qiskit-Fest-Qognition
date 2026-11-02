"""
MiniSudoku4x4Env and Blackjack Game Exploit Environments.
Provides valid and rule-violating state generators with normalized feature extraction for quantum encoders.
"""

import copy
import random
from typing import Any, Dict, List, Optional, Tuple, Union
import gymnasium as gym
from gymnasium import spaces
import numpy as np


class MiniSudoku4x4Env(gym.Env):
    """
    Mini Sudoku (4x4) Gymnasium Environment.
    
    A 4x4 Sudoku board consists of 4 rows, 4 columns, and four 2x2 subgrids.
    Numbers must be from {1, 2, 3, 4}.
    
    This environment can generate:
      - Valid, fully solved or partial mini-sudoku boards
      - Corrupted / rule-violating boards (row/col/box duplicates, range overflows)
    
    Observation space:
      Either full normalized board (16-dim float in [0, 1]) or
      Compact invariant feature vector (4-dim float in [0, 1]) mapped for 4-qubit encoding.
    """
    metadata = {"render_modes": ["ansi"]}

    BASE_VALID_BOARD = np.array([
        [1, 2, 3, 4],
        [3, 4, 1, 2],
        [2, 1, 4, 3],
        [4, 3, 2, 1]
    ], dtype=np.int32)

    def __init__(self, compact_4d: bool = True, corruption_prob: float = 0.3):
        super().__init__()
        self.compact_4d = compact_4d
        self.corruption_prob = corruption_prob
        self.board: np.ndarray = np.copy(self.BASE_VALID_BOARD)
        self.is_corrupted: bool = False
        self.corruption_type: str = "none"

        if self.compact_4d:
            # 4 normalized invariants: [row_integrity, col_integrity, box_integrity, range_integrity]
            self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        else:
            # 16 cells normalized to [0, 1]
            self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(16,), dtype=np.float32)

        # Action: Predict whether the current board contains an exploit/rule violation (0: Legal, 1: Exploit)
        self.action_space = spaces.Discrete(2)

    @staticmethod
    def generate_random_valid_board() -> np.ndarray:
        """Generates a valid 4x4 Sudoku board via symmetry transformations."""
        board = np.copy(MiniSudoku4x4Env.BASE_VALID_BOARD)
        # Permute symbols 1..4
        perm = np.random.permutation([1, 2, 3, 4])
        symbol_map = {orig: new for orig, new in zip([1, 2, 3, 4], perm)}
        new_board = np.zeros_like(board)
        for r in range(4):
            for c in range(4):
                new_board[r, c] = symbol_map[board[r, c]]
        board = new_board

        # Row swaps within bands
        if random.random() < 0.5:
            board[[0, 1]] = board[[1, 0]]
        if random.random() < 0.5:
            board[[2, 3]] = board[[3, 2]]

        # Col swaps within stacks
        if random.random() < 0.5:
            board[:, [0, 1]] = board[:, [1, 0]]
        if random.random() < 0.5:
            board[:, [2, 3]] = board[:, [3, 2]]

        # Transpose symmetry
        if random.random() < 0.5:
            board = board.T

        return board.astype(np.int32)

    @staticmethod
    def corrupt_board(board: np.ndarray) -> Tuple[np.ndarray, str]:
        """Injects a specific rule violation into a Sudoku board."""
        corrupted = np.copy(board)
        corruption_type = random.choice(["row_duplicate", "col_duplicate", "box_duplicate", "value_overflow", "zero_cell"])
        
        r, c = random.randint(0, 3), random.randint(0, 3)

        if corruption_type == "row_duplicate":
            other_c = (c + random.randint(1, 3)) % 4
            corrupted[r, c] = corrupted[r, other_c]
        elif corruption_type == "col_duplicate":
            other_r = (r + random.randint(1, 3)) % 4
            corrupted[r, c] = corrupted[other_r, c]
        elif corruption_type == "box_duplicate":
            br, bc = (r // 2) * 2, (c // 2) * 2
            cells = [(br + dr, bc + dc) for dr in (0, 1) for dc in (0, 1)]
            cells = [cell for cell in cells if cell != (r, c)]
            target_cell = random.choice(cells)
            corrupted[r, c] = corrupted[target_cell[0], target_cell[1]]
        elif corruption_type == "value_overflow":
            corrupted[r, c] = random.choice([5, 8, 9, 255])  # Out of valid {1, 2, 3, 4}
        elif corruption_type == "zero_cell":
            corrupted[r, c] = 0

        return corrupted, corruption_type

    @staticmethod
    def evaluate_invariants(board: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Calculates 4 invariant integrity scores in [0, 1]:
          1. row_integrity: fraction of rows with no duplicates and valid range
          2. col_integrity: fraction of columns with no duplicates and valid range
          3. box_integrity: fraction of 2x2 boxes with no duplicates and valid range
          4. range_integrity: fraction of cells strictly in {1, 2, 3, 4}
        """
        valid_range = {1, 2, 3, 4}

        # Row integrity
        row_scores = []
        for r in range(4):
            vals = board[r, :]
            row_scores.append(1.0 if len(set(vals)) == 4 and set(vals).issubset(valid_range) else 0.0)
        row_integrity = float(np.mean(row_scores))

        # Col integrity
        col_scores = []
        for c in range(4):
            vals = board[:, c]
            col_scores.append(1.0 if len(set(vals)) == 4 and set(vals).issubset(valid_range) else 0.0)
        col_integrity = float(np.mean(col_scores))

        # Box integrity
        box_scores = []
        for br in (0, 2):
            for bc in (0, 2):
                vals = board[br:br+2, bc:bc+2].flatten()
                box_scores.append(1.0 if len(set(vals)) == 4 and set(vals).issubset(valid_range) else 0.0)
        box_integrity = float(np.mean(box_scores))

        # Range integrity
        valid_cells = np.isin(board, [1, 2, 3, 4])
        range_integrity = float(np.mean(valid_cells))

        return row_integrity, col_integrity, box_integrity, range_integrity

    def _get_obs(self) -> np.ndarray:
        if self.compact_4d:
            invariants = self.evaluate_invariants(self.board)
            return np.array(invariants, dtype=np.float32)
        else:
            return (self.board.flatten() / 4.0).astype(np.float32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        self.board = self.generate_random_valid_board()
        if random.random() < self.corruption_prob:
            self.board, self.corruption_type = self.corrupt_board(self.board)
            self.is_corrupted = True
        else:
            self.is_corrupted = False
            self.corruption_type = "none"

        obs = self._get_obs()
        info = {
            "is_corrupted": self.is_corrupted,
            "corruption_type": self.corruption_type,
            "board": np.copy(self.board)
        }
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        # Action is predicted class: 0 = Legal, 1 = Corrupted / Exploit
        correct = (action == (1 if self.is_corrupted else 0))
        reward = 1.0 if correct else -1.0
        terminated = True
        truncated = False
        obs = self._get_obs()
        info = {
            "correct": correct,
            "is_corrupted": self.is_corrupted,
            "corruption_type": self.corruption_type
        }
        return obs, reward, terminated, truncated, info

    def render(self) -> str:
        s = "4x4 Sudoku Board:\n"
        for r in range(4):
            if r == 2:
                s += "----+----\n"
            row_str = f"{self.board[r,0]} {self.board[r,1]} | {self.board[r,2]} {self.board[r,3]}\n"
            s += row_str
        s += f"Status: {'[EXPLOIT CORRUPTED: ' + self.corruption_type + ']' if self.is_corrupted else '[LEGAL VALID]'}\n"
        return s

    @staticmethod
    def generate_dataset(n_samples: int = 200, corruption_ratio: float = 0.2, compact_4d: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """Generates a labeled dataset of Sudoku boards for anomaly detection."""
        X_list = []
        y_list = []
        n_corrupted = int(n_samples * corruption_ratio)
        n_normal = n_samples - n_corrupted

        # Legal boards
        for _ in range(n_normal):
            board = MiniSudoku4x4Env.generate_random_valid_board()
            if compact_4d:
                X_list.append(MiniSudoku4x4Env.evaluate_invariants(board))
            else:
                X_list.append(board.flatten() / 4.0)
            y_list.append(1)  # 1 denotes normal/inlier in OneClassSVM

        # Corrupted boards
        for _ in range(n_corrupted):
            board = MiniSudoku4x4Env.generate_random_valid_board()
            c_board, _ = MiniSudoku4x4Env.corrupt_board(board)
            if compact_4d:
                X_list.append(MiniSudoku4x4Env.evaluate_invariants(c_board))
            else:
                X_list.append(c_board.flatten() / 4.0)
            y_list.append(-1)  # -1 denotes outlier/exploit

        return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)


class BlackjackExploitEnv(gym.Env):
    """
    Blackjack Environment with Exploit Injection Wrapper.
    Normalizes (player_sum, dealer_card, usable_ace) + exploit_indicator to 4 floats in [0, 1].
    """
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, inject_exploits: bool = False, exploit_prob: float = 0.15):
        super().__init__()
        self.underlying_env = gym.make("Blackjack-v1", natural=False, sab=False)
        self.inject_exploits = inject_exploits
        self.exploit_prob = exploit_prob
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        self.action_space = self.underlying_env.action_space
        self.current_exploit: Optional[str] = None

    def _normalize_obs(self, raw_obs: Tuple[int, int, int], is_exploit: bool = False) -> np.ndarray:
        player_sum, dealer_card, usable_ace = raw_obs
        
        if is_exploit and self.current_exploit == "sum_overflow":
            player_sum = 45  # Impossible total exceeding 31
        elif is_exploit and self.current_exploit == "negative_dealer":
            dealer_card = 0  # Impossible card index <= 0
        elif is_exploit and self.current_exploit == "infinite_ace":
            usable_ace = 1
            player_sum = 21  # Exploit: Forced Blackjack 21 regardless of initial deal

        p_norm = np.clip(player_sum / 32.0, 0.0, 1.0)
        d_norm = np.clip(dealer_card / 11.0, 0.0, 1.0)
        a_norm = 1.0 if usable_ace else 0.0
        e_norm = 1.0 if is_exploit else 0.0

        return np.array([p_norm, d_norm, a_norm, e_norm], dtype=np.float32)

    def render(self) -> str:
        raw_obs = getattr(self.underlying_env.unwrapped, "player", None)
        return (f"Blackjack Hand -> Player Sum: {int(self.observation_space.sample()[0]*32)} | "
                f"Exploit Active: {self.current_exploit}")

    @staticmethod
    def generate_dataset(n_samples: int = 200, exploit_ratio: float = 0.2) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        Generates normal and exploit Blackjack observations for quantum anomaly benchmark.
        Returns: (X, y, metadata_list) where y = +1 (normal), -1 (exploit).
        """
        env = gym.make("Blackjack-v1", natural=False, sab=False)
        X_list = []
        y_list = []
        meta_list = []

        n_exploits = int(n_samples * exploit_ratio)
        n_normal = n_samples - n_exploits

        # Normal hands
        for _ in range(n_normal):
            raw_obs, _ = env.reset()
            p, d, a = raw_obs
            x_norm = np.array([p / 32.0, d / 11.0, 1.0 if a else 0.0, 0.0], dtype=np.float32)
            X_list.append(x_norm)
            y_list.append(1)
            meta_list.append({"player_sum": p, "dealer_card": d, "usable_ace": bool(a), "is_exploit": False, "exploit_type": "none"})

        # Exploit hands
        exploit_types = ["sum_overflow", "negative_dealer", "infinite_ace"]
        for i in range(n_exploits):
            etype = exploit_types[i % len(exploit_types)]
            raw_obs, _ = env.reset()
            p, d, a = raw_obs
            if etype == "sum_overflow":
                p = random.randint(35, 50)
            elif etype == "negative_dealer":
                d = 0
            elif etype == "infinite_ace":
                p = 21
                a = 1
            x_norm = np.array([np.clip(p / 32.0, 0.0, 1.0), np.clip(d / 11.0, 0.0, 1.0), 1.0 if a else 0.0, 1.0], dtype=np.float32)
            X_list.append(x_norm)
            y_list.append(-1)
            meta_list.append({"player_sum": p, "dealer_card": d, "usable_ace": bool(a), "is_exploit": True, "exploit_type": etype})

        env.close()
        return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32), meta_list

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        raw_obs, info = self.underlying_env.reset(seed=seed, options=options)
        is_exploit = False
        self.current_exploit = None
        if self.inject_exploits and random.random() < self.exploit_prob:
            is_exploit = True
            self.current_exploit = random.choice(["sum_overflow", "negative_dealer", "infinite_ace"])

        obs = self._normalize_obs(raw_obs, is_exploit=is_exploit)
        info["is_exploit"] = is_exploit
        info["exploit_type"] = self.current_exploit
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        raw_obs, reward, terminated, truncated, info = self.underlying_env.step(action)
        is_exploit = (self.current_exploit is not None)
        obs = self._normalize_obs(raw_obs, is_exploit=is_exploit)
        info["is_exploit"] = is_exploit
        info["exploit_type"] = self.current_exploit
        return obs, float(reward), terminated, truncated, info

    def close(self):
        self.underlying_env.close()


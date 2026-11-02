"""
python-chess Latent Feature Extractor and Dataset Fuzzing Generator.
Generates 200 legal grandmaster/random opening FENs and 20 corrupted/illegal board FENs.
Extracts 4-dimensional normalized invariant features for quantum kernel anomaly detection.
"""

import os
import random
from typing import Any, Dict, List, Optional, Tuple, Union
import chess
import gymnasium as gym
from gymnasium import spaces
import numpy as np


class ChessFeatureExtractor:
    """
    Extracts 4 normalized latent invariant features from a chess.Board or FEN string:
      Feature 0: Material balance normalized to [0, 1] (0.5 is equal material)
      Feature 1: Piece density normalized to [0, 1] (32 pieces = 1.0)
      Feature 2: King integrity score [0.0 = violated (multiple/missing kings/adjacent), 1.0 = valid]
      Feature 3: Pawn rank validity [0.0 = pawns on rank 1/8 (rule breach), 1.0 = valid]
    """

    PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }

    @classmethod
    def extract_4d_features(cls, board: Union[chess.Board, str]) -> np.ndarray:
        if isinstance(board, str):
            # Allow creating board even from corrupted FEN without strict validation
            try:
                board = chess.Board(board)
            except Exception:
                # Custom parse for corrupted FEN
                board = chess.Board(None)
                board.set_fen(board if isinstance(board, str) else chess.STARTING_FEN)

        # 1. Material balance
        white_mat = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in cls.PIECE_VALUES.items())
        black_mat = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in cls.PIECE_VALUES.items())
        diff = (white_mat - black_mat) / 40.0  # roughly [-1, 1]
        mat_norm = np.clip((diff + 1.0) / 2.0, 0.0, 1.0)

        # 2. Piece density
        total_pieces = len(board.piece_map())
        piece_norm = np.clip(total_pieces / 32.0, 0.0, 1.0)

        # 3. King integrity: exactly 1 white king, exactly 1 black king, and not adjacent
        white_kings = len(board.pieces(chess.KING, chess.WHITE))
        black_kings = len(board.pieces(chess.KING, chess.BLACK))
        king_integrity = 1.0
        if white_kings != 1 or black_kings != 1:
            king_integrity = 0.0
        else:
            w_sq = board.king(chess.WHITE)
            b_sq = board.king(chess.BLACK)
            if w_sq is not None and b_sq is not None:
                if chess.square_distance(w_sq, b_sq) <= 1:
                    king_integrity = 0.0

        # 4. Pawn rank validity: pawns on rank 1 (0..7) or rank 8 (56..63) are illegal in chess rules
        pawn_rank_validity = 1.0
        pawns_white = board.pieces(chess.PAWN, chess.WHITE)
        pawns_black = board.pieces(chess.PAWN, chess.BLACK)
        all_pawns = pawns_white | pawns_black
        rank_1_mask = chess.BB_RANK_1
        rank_8_mask = chess.BB_RANK_8
        if (all_pawns & rank_1_mask) or (all_pawns & rank_8_mask):
            pawn_rank_validity = 0.0

        return np.array([mat_norm, piece_norm, king_integrity, pawn_rank_validity], dtype=np.float32)


def generate_chess_datasets(
    output_dir: str,
    n_normal: int = 200,
    n_corrupted: int = 20,
    seed: int = 42
) -> Tuple[str, str]:
    """
    Generates and saves:
      1. `normal_chess_states.fen`: 200 legal grandmaster/random opening states
      2. `corrupted_chess_states.fen`: 20 corrupted/illegal states (multiple kings, pawns on rank 1/8)
    """
    random.seed(seed)
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    normal_fen_path = os.path.join(output_dir, "normal_chess_states.fen")
    corrupted_fen_path = os.path.join(output_dir, "corrupted_chess_states.fen")

    # 1. Generate 200 legal chess positions
    normal_fens: List[str] = []
    attempts = 0
    while len(normal_fens) < n_normal and attempts < n_normal * 10:
        attempts += 1
        board = chess.Board()
        # Make between 4 and 35 random legal moves
        num_moves = random.randint(4, 35)
        for _ in range(num_moves):
            if board.is_game_over():
                break
            moves = list(board.legal_moves)
            if not moves:
                break
            move = random.choice(moves)
            board.push(move)

        if board.is_valid() and board.fen() not in normal_fens:
            normal_fens.append(board.fen())

    # Fallback if needed
    while len(normal_fens) < n_normal:
        normal_fens.append(chess.STARTING_FEN)

    with open(normal_fen_path, "w", encoding="utf-8") as f:
        for fen in normal_fens:
            f.write(fen + "\n")

    # 2. Generate 20 corrupted / illegal positions
    corrupted_fens: List[str] = []

    # Category A: Multiple Kings (8 states)
    for i in range(8):
        board = chess.Board()
        # Play a few random moves first
        for _ in range(random.randint(2, 10)):
            if board.legal_moves:
                board.push(random.choice(list(board.legal_moves)))
        # Add extra kings
        empty_squares = [sq for sq in chess.SQUARES if board.piece_at(sq) is None]
        if empty_squares:
            color = chess.WHITE if i % 2 == 0 else chess.BLACK
            board.set_piece_at(random.choice(empty_squares), chess.Piece(chess.KING, color))
            if i >= 4 and len(empty_squares) > 1:
                # Add another extra king (3 kings total)
                board.set_piece_at(empty_squares[1], chess.Piece(chess.KING, color))
        corrupted_fens.append(board.fen())

    # Category B: Pawns on Rank 1 or Rank 8 (8 states)
    for i in range(8):
        board = chess.Board()
        for _ in range(random.randint(2, 8)):
            if board.legal_moves:
                board.push(random.choice(list(board.legal_moves)))
        # Rank 1 squares (0..7) or Rank 8 squares (56..63)
        illegal_rank = random.choice([0, 7])
        sq = illegal_rank * 8 + random.randint(0, 7)
        color = chess.WHITE if random.random() < 0.5 else chess.BLACK
        board.set_piece_at(sq, chess.Piece(chess.PAWN, color))
        corrupted_fens.append(board.fen())

    # Category C: Impossible piece counts or adjacent kings (4 states)
    for i in range(4):
        board = chess.Board()
        w_sq = chess.E4
        b_sq = chess.E5  # Adjacent kings
        board.set_piece_at(w_sq, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(b_sq, chess.Piece(chess.KING, chess.BLACK))
        corrupted_fens.append(board.fen())

    with open(corrupted_fen_path, "w", encoding="utf-8") as f:
        for fen in corrupted_fens[:n_corrupted]:
            f.write(fen + "\n")

    return normal_fen_path, corrupted_fen_path


def load_chess_feature_dataset(
    normal_fen_path: str,
    corrupted_fen_path: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Loads normal and corrupted FEN files and converts them to 4D feature matrices:
    Returns (X_train_normal, X_test, y_test, test_fens)
    """
    with open(normal_fen_path, "r", encoding="utf-8") as f:
        normal_fens = [line.strip() for line in f if line.strip()]

    with open(corrupted_fen_path, "r", encoding="utf-8") as f:
        corrupted_fens = [line.strip() for line in f if line.strip()]

    # Extract features
    normal_features = [ChessFeatureExtractor.extract_4d_features(fen) for fen in normal_fens]
    corrupted_features = [ChessFeatureExtractor.extract_4d_features(fen) for fen in corrupted_fens]

    # Split normal into 80% train (inliers only for One-Class SVM) and 20% test
    n_train = int(len(normal_features) * 0.8)
    X_train = np.array(normal_features[:n_train], dtype=np.float32)
    
    X_test_normal = normal_features[n_train:]
    X_test_corrupted = corrupted_features

    X_test = np.array(X_test_normal + X_test_corrupted, dtype=np.float32)
    # Label: +1 for normal, -1 for corrupted/exploit (OneClassSVM convention)
    y_test = np.array([1] * len(X_test_normal) + [-1] * len(X_test_corrupted), dtype=np.int32)
    test_fens = normal_fens[n_train:] + corrupted_fens

    return X_train, X_test, y_test, np.array(test_fens)


class ChessFuzzEnv(gym.Env):
    """
    Gymnasium environment that serves legal and fuzzed chess states
    for testing exploit detection agents.
    """
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, normal_fen_path: str, corrupted_fen_path: str):
        super().__init__()
        self.normal_fen_path = normal_fen_path
        self.corrupted_fen_path = corrupted_fen_path
        
        with open(normal_fen_path, "r", encoding="utf-8") as f:
            self.normal_fens = [line.strip() for line in f if line.strip()]
        with open(corrupted_fen_path, "r", encoding="utf-8") as f:
            self.corrupted_fens = [line.strip() for line in f if line.strip()]

        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        self.action_space = spaces.Discrete(2)  # 0: Legal, 1: Exploit / Corrupted
        self.current_fen = chess.STARTING_FEN
        self.current_is_corrupted = False

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            random.seed(seed)

        if random.random() < 0.3 and self.corrupted_fens:
            self.current_fen = random.choice(self.corrupted_fens)
            self.current_is_corrupted = True
        else:
            self.current_fen = random.choice(self.normal_fens)
            self.current_is_corrupted = False

        obs = ChessFeatureExtractor.extract_4d_features(self.current_fen)
        return obs, {"fen": self.current_fen, "is_corrupted": self.current_is_corrupted}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        is_exploit = self.current_is_corrupted
        correct = (action == (1 if is_exploit else 0))
        reward = 1.0 if correct else -1.0
        obs = ChessFeatureExtractor.extract_4d_features(self.current_fen)
        return obs, reward, True, False, {"correct": correct, "is_corrupted": is_exploit}


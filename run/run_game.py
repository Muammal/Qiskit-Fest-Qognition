"""
Unified Real-Time Quantum RL Game Simulation Runner.
Executes real-time simulation iterations with live Quantum Telemetry HUD and background exploit interception.

Usage:
  python run/run_game.py --game mario
  python run/run_game.py --game doom
  python run/run_game.py --game chess
  python run/run_game.py --game sudoku
  python run/run_game.py --game blackjack
  python run/run_game.py --game all
"""

import argparse
import os
import sys

# Add parent directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PACKAGE_DIR = os.path.join(ROOT_DIR, "qiskit_exploit_hunter")
for p in [ROOT_DIR, PACKAGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_mario import run_mario_simulation
from run_doom import run_doom_simulation
from run_chess import run_chess_simulation
from run_sudoku import run_sudoku_simulation
from run_blackjack import run_blackjack_simulation


def main():
    parser = argparse.ArgumentParser(description="Real-Time Quantum RL Game Simulation & Exploit Interception Runner")
    parser.add_argument(
        "--game",
        type=str,
        required=True,
        choices=["mario", "doom", "chess", "sudoku", "blackjack", "all"],
        help="Target game to simulate in real time"
    )
    parser.add_argument("--iters", type=int, default=5, help="Number of simulation iterations to execute")
    parser.add_argument("--steps", type=int, default=12, help="Steps per iteration for retro games")
    parser.add_argument("--moves", type=int, default=None, help="Moves per iteration for chess")
    parser.add_argument("--delay", type=float, default=0.06, help="Step / iteration delay in seconds for real-time visibility")
    parser.add_argument("--mock-2d", action="store_true", help="Force lightweight 2D physics grid for retro games")
    args = parser.parse_args()

    game = args.game.lower()
    chess_moves = args.moves if args.moves is not None else min(args.steps, 10)

    if game in ["mario", "all"]:
        run_mario_simulation(iterations=args.iters, steps_per_iter=args.steps, delay=args.delay, mock_2d=args.mock_2d)

    if game in ["doom", "all"]:
        run_doom_simulation(iterations=args.iters, steps_per_iter=args.steps, delay=args.delay, mock_2d=args.mock_2d)

    if game in ["chess", "all"]:
        run_chess_simulation(iterations=args.iters, moves_per_iter=chess_moves, delay=args.delay)

    if game in ["sudoku", "all"]:
        run_sudoku_simulation(iterations=args.iters, delay=args.delay)

    if game in ["blackjack", "all"]:
        run_blackjack_simulation(iterations=args.iters, delay=args.delay)


if __name__ == "__main__":
    main()

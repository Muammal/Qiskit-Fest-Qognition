"""
Unified Real-Time Quantum RL Game Simulation Runner.
Executes real-time simulation iterations with live Quantum Telemetry HUD and background exploit interception.
Supports Hardware-Accelerated Visual Playback (1x Real-Time 60 FPS + Sped-Up Fuzzing) and Full-Level Completion.

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
for p in [ROOT_DIR, BASE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from .run_mario import run_mario_simulation
    from .run_doom import run_doom_simulation
    from .run_chess import run_chess_simulation
    from .run_sudoku import run_sudoku_simulation
    from .run_blackjack import run_blackjack_simulation
except ImportError:
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
    parser.add_argument("--iters", type=int, default=3, help="Number of simulation iterations to execute")
    parser.add_argument("--realtime-iter", type=int, default=1, help="Which iteration to run in 1x real-time (default: 1)")
    parser.add_argument("--realtime", action="store_true", help="Force all iterations to run in 1x real-time (60 FPS)")
    parser.add_argument("--fps", type=int, default=60, help="Target real-time FPS (default: 60)")
    parser.add_argument("--fast-fps", type=int, default=240, help="Target sped-up simulation FPS (default: 240)")
    parser.add_argument("--headless", action="store_true", help="Disable visual Pygame window (console output only)")
    parser.add_argument("--mock-2d", action="store_true", help="Force lightweight 2D physics grid for retro games")
    parser.add_argument("--steps", type=int, default=1500, help="Max level/episode steps")
    parser.add_argument("--moves", type=int, default=15, help="Moves per iteration for chess")
    parser.add_argument("--delay", type=float, default=0.06, help="Step / iteration delay in seconds for headless mode")
    args = parser.parse_args()

    game = args.game.lower()

    if game in ["mario", "all"]:
        run_mario_simulation(
            iterations=args.iters,
            realtime_iter=args.realtime_iter,
            force_realtime=args.realtime,
            fps=args.fps,
            fast_fps=args.fast_fps,
            headless=args.headless,
            mock_2d=args.mock_2d,
            max_level_steps=args.steps
        )

    if game in ["doom", "all"]:
        run_doom_simulation(
            iterations=args.iters,
            realtime_iter=args.realtime_iter,
            force_realtime=args.realtime,
            fps=min(args.fps, 35),
            fast_fps=args.fast_fps,
            headless=args.headless,
            mock_2d=args.mock_2d,
            max_episode_steps=min(args.steps, 250)
        )

    if game in ["chess", "all"]:
        run_chess_simulation(
            iterations=args.iters,
            realtime_iter=args.realtime_iter,
            force_realtime=args.realtime,
            moves_per_iter=args.moves,
            delay=args.delay,
            headless=args.headless
        )

    if game in ["sudoku", "all"]:
        run_sudoku_simulation(iterations=args.iters, delay=args.delay)

    if game in ["blackjack", "all"]:
        run_blackjack_simulation(iterations=args.iters, delay=args.delay)


if __name__ == "__main__":
    main()

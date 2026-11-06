"""play3d.py - Standalone executable entrypoint for the 3D Front-end (Ursina / Panda3D).

Usage:
  python play3d.py                                -> Launches interactive 3D Simulation
  python play3d.py --seed 101 --mind quantum      -> Sets custom seed and cognitive mind
  python play3d.py --scenario island              -> Launches directly into Island Wilderness
  python play3d.py --quality low|medium|high      -> Sets graphics quality preset
  python play3d.py --replay demo-pack/run_01.json -> Replays recorded simulation run
  python play3d.py --smoke                        -> Offscreen headless run for automated tests
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantum Cognition Simulation - 3D Front-end")
    parser.add_argument("--seed", type=int, default=101, help="Simulation seed (default: 101)")
    parser.add_argument("--mind", type=str, default="quantum", choices=["quantum", "classical", "classical_mixture"], help="Mind engine")
    parser.add_argument("--scenario", type=str, default="volcano", choices=["island", "volcano"], help="Scenario to play")
    parser.add_argument("--quality", type=str, default="high", choices=["low", "medium", "high"], help="Graphics quality")
    parser.add_argument("--replay", type=str, default=None, help="Path to recorded timeline JSON replay")
    parser.add_argument("--smoke", action="store_true", help="Run offscreen headless verification and exit 0")

    args = parser.parse_args()

    try:
        from gui3d.app import GameApp
    except ImportError as e:
        print(f"[3D Engine Error] Failed to import 3D engine dependencies: {e}", file=sys.stderr)
        print("Please install requirements: pip install -r requirements-3d.txt", file=sys.stderr)
        sys.exit(1)

    app = GameApp(
        seed=args.seed,
        mind=args.mind,
        scenario=args.scenario,
        quality=args.quality,
        replay_path=args.replay,
        smoke_mode=args.smoke,
    )
    app.run()


if __name__ == "__main__":
    main()


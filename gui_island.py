"""gui_island.py - Launch the 2D Pygame Quantum Cognition Simulation
Tech C Deliverable (Engine, World & Interactive Visualization)
"""

import argparse
import sys
from engine.gui import launch_gui


def main():
    parser = argparse.ArgumentParser(description="Quantum Cognition Simulation - 2D Visualizer")
    parser.add_argument("--seed", type=int, default=101, help="Seed for event hazards and terrain")
    parser.add_argument("--mind", type=str, default="quantum", choices=["quantum", "classical"], help="Mind engine")
    parser.add_argument("--noise", type=str, default="stub", help="Noise source profile")
    parser.add_argument("--scenario", type=str, default=None, choices=["island", "volcano"], help="Direct scenario launch")

    args = parser.parse_args()
    start_screen = "home" if args.scenario else "event_choice"
    print(f"Launching Quantum Cognition Simulation (Seed={args.seed}, Mind={args.mind})...")
    launch_gui(seed=args.seed, mind=args.mind, noise=args.noise, start_screen=start_screen)


if __name__ == "__main__":
    main()

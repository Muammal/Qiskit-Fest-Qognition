"""
gui_island.py - Launch the 2D Pygame Island and Character Visualizer
Quantum Cognition Survival Simulation Engine
Tech C Deliverable (Engine, World & Interactive Visualization)
"""

import argparse
import sys
from engine.gui import launch_gui


def main():
    parser = argparse.ArgumentParser(description="Stranded: 2D Pygame Island & Character Visualizer")
    parser.add_argument("--seed", type=int, default=101, help="Random seed for procedural island generation")
    parser.add_argument("--mind", type=str, default="quantum", choices=["quantum", "classical"], help="Mind engine")
    parser.add_argument("--noise", type=str, default="ibm_hardware", help="Hardware noise source profile")

    args = parser.parse_args()
    print(f"Launching Pygame 2D Island Visualizer (Seed={args.seed}, Mind={args.mind})...")
    launch_gui(seed=args.seed, mind=args.mind, noise=args.noise)


if __name__ == "__main__":
    main()


"""
Top-level entrypoint for Quantum RL & Game Exploit Detection Framework.
Routes to pipeline experiments, real-time game simulations, or specific exploit demonstrations.

Usage:
  python main.py --game [mario|doom|chess|sudoku|blackjack|all]  # Real-time game simulation
  python main.py --day [1|2|3|4]                                 # Run research day pipeline
  python main.py --all                                           # Run complete 4-day pipeline
  python main.py --blackjack                                     # Quick Blackjack exploit demo
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.join(BASE_DIR, "qiskit_exploit_hunter")
RUN_DIR = os.path.join(BASE_DIR, "run")
UI_DIR = os.path.join(BASE_DIR, "ui")
for p in [BASE_DIR, PACKAGE_DIR, RUN_DIR, UI_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    if "--ui" in sys.argv:
        from ui.server import launch_ui
        launch_ui(host="127.0.0.1", port=8000, auto_open=True)
    elif "--game" in sys.argv:
        from run.run_game import main as run_game_main
        run_game_main()
    elif "--blackjack" in sys.argv or "blackjack" in sys.argv:
        from run_blackjack_exploit import run_blackjack_exploit_demo
        run_blackjack_exploit_demo(num_hands=10)
    else:
        from run_pipeline import main as pipeline_main
        pipeline_main()

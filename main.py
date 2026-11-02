"""
Interactive Master Entrypoint for Quantum RL & Game Exploit Detection Framework.
Interactive CLI menu, web UI launcher, and direct CLI command runner.

Usage:
  python main.py                                                 # Interactive Menu
  python main.py --ui                                            # Launch Web UI (http://127.0.0.1:8000)
  python main.py --game [mario|doom|chess|sudoku|blackjack|all]  # Real-time game simulations
  python main.py --day [1|2|3|4]                                 # Run specific research day pipeline
  python main.py --all                                           # Run complete 4-day research pipeline
  python main.py --blackjack                                     # Quick Blackjack exploit demo
  python main.py --verify                                        # Run pre-flight verification
  python main.py --showcase                                      # Run 320x speedup RAM showcase
"""

import os
import sys

# Ensure root directory and submodules are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.join(BASE_DIR, "run")
UI_DIR = os.path.join(BASE_DIR, "ui")
ENGINES_DIR = os.path.join(BASE_DIR, "engines")
ENVS_DIR = os.path.join(BASE_DIR, "envs")

for p in [BASE_DIR, RUN_DIR, UI_DIR, ENGINES_DIR, ENVS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def interactive_menu():
    """Interactive terminal control center for launching simulations and web interfaces."""
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    while True:
        print("\n" + "=" * 80)
        print(f"{CYAN}{BOLD}   Ψ QUANTUM RL & GAME EXPLOIT DETECTION FRAMEWORK{RESET}")
        print(f"   {GREEN}Qiskit 1.0+ | Aer MPS | 320.1x Headless Statevector Acceleration{RESET}")
        print("=" * 80)
        print(f" {BOLD}[1]{RESET}  {CYAN}Launch Real-Time Web Interface{RESET}  (FastAPI Server at http://127.0.0.1:8000)")
        print(f" {BOLD}[2]{RESET}  Super Mario Bros (World 1-1)   (NES RAM 4D + Sub-Pixel Wall-Clip)")
        print(f" {BOLD}[3]{RESET}  ViZDoom Corridor Combat        (freedoom2.wad + Health Overflow & Clip)")
        print(f" {BOLD}[4]{RESET}  python-chess FEN Engine        (Legal GM Openings + Corrupted Kings/Pawns)")
        print(f" {BOLD}[5]{RESET}  MiniSudoku 4x4 Invariants      (Latin Square Invariants + Duplicate Breach)")
        print(f" {BOLD}[6]{RESET}  Blackjack-v1 Card Table        (Card Sum Overflow >31 & Infinite Ace)")
        print(f" {BOLD}[7]{RESET}  {YELLOW}Simulate All Games Sequentially{RESET} (Full 5-Game Real-Time Suite)")
        print("-" * 80)
        print(f" {BOLD}[8]{RESET}  {GREEN}4-Day Research Pipeline{RESET}        (Day 1 to Day 4 Experiments & Plots)")
        print(f" {BOLD}[9]{RESET}  Pre-Flight Verification Suite  (setup_and_verify.py)")
        print(f" {BOLD}[10]{RESET} High-Speed RAM Benchmark       (visual_showcase.py - 19,200+ steps/sec)")
        print(f" {BOLD}[0]{RESET}  {RED}Exit{RESET}")
        print("=" * 80)

        try:
            choice = input(f"{BOLD}Select an option [0-10]: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "0":
            print("Exiting Quantum Exploit Hunter.")
            break
        elif choice == "1":
            print("\nStarting Real-Time Web UI Server...")
            from ui.server import launch_ui
            launch_ui(host="127.0.0.1", port=8000, auto_open=True)
            break
        elif choice == "2":
            from run.run_mario import run_mario_simulation
            run_mario_simulation(iterations=3, realtime_iter=1, force_realtime=False, headless=False, mock_2d=False)
        elif choice == "3":
            from run.run_doom import run_doom_simulation
            run_doom_simulation(iterations=3, realtime_iter=1, force_realtime=False, headless=False, mock_2d=False)
        elif choice == "4":
            from run.run_chess import run_chess_simulation
            run_chess_simulation(iterations=3, realtime_iter=1, force_realtime=False, moves_per_iter=15, headless=False)
        elif choice == "5":
            from run.run_sudoku import run_sudoku_simulation
            run_sudoku_simulation(iterations=3, delay=0.05)
        elif choice == "6":
            from run.run_blackjack import run_blackjack_simulation
            run_blackjack_simulation(iterations=3, delay=0.05)
        elif choice == "7":
            from run.run_game import main as run_game_main
            sys.argv = ["run_game.py", "--game", "all", "--iters", "2", "--steps", "8", "--delay", "0.01"]
            run_game_main()
        elif choice == "8":
            from run_pipeline import main as pipeline_main
            sys.argv = ["run_pipeline.py", "--all"]
            pipeline_main()
        elif choice == "9":
            from setup_and_verify import main as verify_main
            verify_main()
        elif choice == "10":
            from visual_showcase import main as showcase_main
            showcase_main()
        else:
            print(f"{RED}Invalid option '{choice}'. Please enter a number between 0 and 10.{RESET}")


def main():
    args = sys.argv[1:]

    # If flags passed, dispatch directly
    if "--ui" in args:
        from ui.server import launch_ui
        launch_ui(host="127.0.0.1", port=8000, auto_open=True)
    elif "--game" in args:
        from run.run_game import main as run_game_main
        run_game_main()
    elif "--blackjack" in args:
        from run_blackjack_exploit import run_blackjack_exploit_demo
        run_blackjack_exploit_demo(num_hands=10)
    elif "--verify" in args:
        from setup_and_verify import main as verify_main
        sys.argv = ["setup_and_verify.py"]
        verify_main()
    elif "--showcase" in args:
        from visual_showcase import main as showcase_main
        sys.argv = ["visual_showcase.py", "--mode", "showcase", "--steps", "15", "--fps", "20"]
        showcase_main()
    elif "--all" in args or "--day" in args:
        from run_pipeline import main as pipeline_main
        pipeline_main()
    else:
        # Default: Launch Interactive Menu
        interactive_menu()


if __name__ == "__main__":
    main()

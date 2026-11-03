"""
main.py - Interactive CLI Entry Point for Stranded
Quantum Cognition Decision-Making & Survival Simulation Engine
Tech C Deliverable (Engine, World & Integration)
"""

import argparse
import os
import sys
import time
import json
import random
from typing import Dict, Any

from engine.world import IslandWorld
from engine.agent import SurvivalAgent
from engine.simulation import SimulationEngine, DEFAULT_STEPS
from engine.batch_runner import run_batch_comparison, curate_demo_pack
import contracts


# Terminal styling helpers
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

TILE_CHARS = {
    0: f"{BLUE}~{RESET}",  # water
    1: f"{YELLOW}.{RESET}",  # plains
    2: f"{GREEN}^{RESET}",   # forest
    3: f"{RESET}M{RESET}",   # mountain
    4: f"{MAGENTA}S{RESET}"   # shelter
}


def render_ascii_map(world: IslandWorld, agent_pos: list, radius: int = 7) -> str:
    """Renders a localized 2D viewport around the agent."""
    ax, ay = agent_pos
    lines = []
    lines.append(f"+{'-' * (radius * 2 + 1)}+")
    for y in range(max(0, ay - radius), min(world.height, ay + radius + 1)):
        row_str = "|"
        for x in range(max(0, ax - radius), min(world.width, ax + radius + 1)):
            if x == ax and y == ay:
                row_str += f"{BOLD}{RED}@{RESET}"
            else:
                tile = world.get_tile(x, y)
                row_str += TILE_CHARS.get(tile, " ")
        row_str += "|"
        lines.append(row_str)
    lines.append(f"+{'-' * (radius * 2 + 1)}+")
    return "\n".join(lines)


def format_bar(val: float, length: int = 12) -> str:
    """Renders an ASCII percentage progress bar."""
    filled = int(val * length)
    empty = length - filled
    color = GREEN if val > 0.5 else (YELLOW if val > 0.25 else RED)
    return f"{color}[{'=' * filled}{' ' * empty}] {int(val * 100):3d}%{RESET}"


def run_live_demo(seed: int = 101, mind: str = "quantum", noise: str = "stub", speed: float = 0.3):
    """Executes a live visual interactive survival run step-by-step in the terminal."""
    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN}   STRANDED - QUANTUM COGNITION SURVIVAL SIMULATION (LIVE RUN)       {RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}")
    print(f"  Configuration: Seed={seed} | Mind={mind.upper()} | Noise={noise}")
    print(f"  Legend: {BLUE}~{RESET} Water  {YELLOW}.{RESET} Plains  {GREEN}^{RESET} Forest  M Mountain  {MAGENTA}S{RESET} Shelter  {BOLD}{RED}@{RESET} Agent\n")

    sim = SimulationEngine(seed=seed, mind_type=mind, noise_source=noise)
    max_steps = DEFAULT_STEPS

    def on_step(step_record: Dict[str, Any], engine: SimulationEngine):
        t = step_record["t"]
        state = step_record["state"]
        event = step_record["event"]
        action = step_record["action"]
        probs = step_record["probs"]
        reason = step_record["reason"]
        in_shelter = engine.world.is_in_shelter(engine.agent.pos[0], engine.agent.pos[1])

        print(f"\n{BOLD}--- Step {t + 1}/{max_steps} | Day {state['day']}, Hour {state['hour']:02d}:00 ---{RESET}")
        map_view = render_ascii_map(engine.world, engine.agent.pos, radius=5)
        print(map_view)

        needs = state["needs"]
        print(f"  Position: [{engine.agent.pos[0]}, {engine.agent.pos[1]}]  | In Shelter: {'Yes' if in_shelter else 'No'} | Injured: {'YES' if state['injured'] else 'No'}")
        print(f"  Hunger: {format_bar(needs['hunger'])}  Thirst: {format_bar(needs['thirst'])}")
        print(f"  Warmth: {format_bar(needs['warmth'])}  Energy: {format_bar(needs['energy'])}")
        print(f"  Safety: {format_bar(needs['safety'])}  Morale: {format_bar(needs['morale'])}")
        print(f"  Stress: {format_bar(engine.agent.stress)}")
        print(f"  Recent Events: {state['recent_events']}")
        print(f"  {BOLD}Event Encountered:{RESET} {YELLOW}{event.upper()}{RESET}")
        print(f"  {BOLD}Chosen Action:{RESET} {GREEN}{action.upper()}{RESET}")
        print(f"  {BOLD}Cognitive Probs:{RESET} { {k: v for k, v in probs.items() if v > 0.05} }")
        print(f"  {BOLD}Quantum Reason:{RESET} {CYAN}{reason}{RESET}")

        if speed > 0:
            time.sleep(speed)

    try:
        timeline = sim.run(max_steps=max_steps, step_callback=on_step)
    except TypeError:
        # Fallback if SimulationEngine without step_callback parameter is loaded
        timeline = sim.run(max_steps=max_steps)
        for step in timeline.get("steps", []):
            on_step(step, sim)

    print(f"\n{BOLD}========================================================================{RESET}")
    if timeline["outcome"] == "survived":
        print(f"{BOLD}{GREEN}  >>> MISSION OUTCOME: SURVIVED! Successfully endured {len(timeline['steps']) * 2} hours on island. <<<{RESET}")
    else:
        print(f"{BOLD}{RED}  >>> MISSION OUTCOME: DIED ({str(timeline['cause']).upper()}) at Step {len(timeline['steps'])}. <<<{RESET}")
    print(f"{BOLD}========================================================================{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Stranded: Quantum Cognition Survival Engine")
    parser.add_argument("--gui", action="store_true", help="Launch interactive 2D Pygame Island and Character visualizer (default)")
    parser.add_argument("--demo", action="store_true", help="Run interactive terminal ASCII survival run")
    parser.add_argument("--terminal", action="store_true", help="Run interactive terminal ASCII survival run")
    parser.add_argument("--batch", action="store_true", help="Compare synthetic heuristic stubs (no quantum or hardware results)")
    parser.add_argument("--curate", action="store_true", help="Curate signature runs into demo-pack/")
    parser.add_argument("--test", action="store_true", help="Execute integration test suite")
    parser.add_argument("--seed", type=int, default=101, help="Event and volcano seed (the island is fixed)")
    parser.add_argument("--mind", type=str, default="quantum", choices=["quantum", "classical"], help="Mind engine")
    parser.add_argument("--noise", type=str, default="stub", help="Noise source profile")
    parser.add_argument("--speed", type=float, default=0.2, help="Seconds delay per step during live demo")

    args = parser.parse_args()

    if args.test:
        import pytest
        print(f"[Tech C] Running integration test suite...")
        sys.exit(pytest.main(["-v", "test_contracts_and_engine.py"]))
    elif args.batch:
        summary = run_batch_comparison(num_seeds=20, max_steps=DEFAULT_STEPS)
        print(f"\n{BOLD}=== Synthetic Heuristic-Stub Results ({summary['num_seeds']} Seeds) ==={RESET}")
        print(f"  {summary['provenance']['disclosure']} Noise source: {summary['noise_source']}")
        print(f"  Total Evaluated Decisions: {summary['total_evaluated_steps']}")
        print(f"  Decision Divergences:      {summary['total_divergences']}")
        print(f"  Divergence Rate:           {BOLD}{summary['divergence_rate_pct']}%{RESET}")
        print(f"  Quantum-labelled Stub Survival Rate:     {GREEN}{summary['quantum_survival_rate_pct']}%{RESET}")
        print(f"  Classical-labelled Stub Survival Rate:   {YELLOW}{summary['classical_survival_rate_pct']}%{RESET}\n")
    elif args.curate:
        curate_demo_pack("demo-pack")
    elif args.demo or args.terminal:
        run_live_demo(seed=args.seed, mind=args.mind, noise=args.noise, speed=args.speed)
    else:
        # Default single launch command: Full Pygame Application with Home Screen
        from engine.gui import launch_gui
        print(f"Launching Stranded 2D Island & Quantum Survival Simulation (Seed={args.seed}, Mind={args.mind})...")
        launch_gui(seed=args.seed, mind=args.mind, noise=args.noise, start_screen="home")


if __name__ == "__main__":
    main()

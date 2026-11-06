"""main.py - Single executable entrypoint for Quantum Cognition Simulation.
Integration Deliverable for Tech C (Engine, World & Interactive Visualization).

Usage:
  python main.py                        -> Launches interactive 2D Simulation starting at Event Choice Hub
  python main.py --demo                 -> Runs live visual terminal simulation
  python main.py --demo --engine physics -> Runs St. Vincent 2021 T1 ScenarioPack simulation
  python main.py --batch                -> Runs Quantum vs Classical Mixture vs Classical divergence comparison
  python main.py --curate               -> Curates signature runs into demo-pack/
  python main.py --test                 -> Executes test suite
"""

import os
import sys
import time
import argparse
from typing import Dict, Any

from engine.world import IslandWorld
from engine.agent import SurvivalAgent
from engine.simulation import SimulationEngine, DEFAULT_STEPS
from engine.batch_runner import run_batch_comparison, curate_demo_pack
from engine.titanic import TitanicSimulation
from engine.pompeii import PompeiiSimulation
from engine.waterloo import WaterlooSimulation
import contracts

# Terminal ANSI formatting
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"

TILE_CHARS = {
    0: f"{BLUE}~{RESET}",
    1: f"{YELLOW}.{RESET}",
    2: f"{GREEN}^{RESET}",
    3: f"{RESET}M{RESET}",
    4: f"{MAGENTA}S{RESET}"
}


def render_ascii_map(world: IslandWorld, agent_pos: list, radius: int = 5) -> str:
    """Renders a 2D ASCII local viewport centered on agent."""
    ax, ay = agent_pos
    lines = []
    tile_symbols = {0: f"{BLUE}~{RESET}", 1: f"{YELLOW}.{RESET}", 2: f"{GREEN}^{RESET}", 3: "M", 4: f"{MAGENTA}S{RESET}"}

    lines.append("  +" + "---" * (radius * 2 + 1) + "+")
    for y in range(max(0, ay - radius), min(world.height, ay + radius + 1)):
        row_str = "  |"
        for x in range(max(0, ax - radius), min(world.width, ax + radius + 1)):
            if x == ax and y == ay:
                row_str += f"{BOLD}{RED} @ {RESET}"
            else:
                t = world.get_tile(x, y)
                sym = tile_symbols.get(t, " ")
                row_str += f" {sym} "
        row_str += "|"
        lines.append(row_str)
    lines.append("  +" + "---" * (radius * 2 + 1) + "+")
    return "\n".join(lines)


def format_bar(val: float, length: int = 12) -> str:
    """Renders an ASCII percentage progress bar."""
    filled = int(val * length)
    empty = length - filled
    color = GREEN if val > 0.5 else (YELLOW if val > 0.25 else RED)
    return f"{color}[{'=' * filled}{' ' * empty}] {int(val * 100):3d}%{RESET}"


def run_live_demo(
    seed: int = 101,
    mind: str = "quantum",
    noise: str = "stub",
    scenario: str = "volcano",
    speed: float = 0.3,
    engine_mode: str = "legacy",
):
    """Executes a live visual interactive survival run step-by-step in the terminal."""
    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN}   QOGNITION (TERMINAL LIVE RUN)                                        {RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}")
    print(f"  Configuration: Engine={engine_mode.upper()} | Scenario={scenario.upper()} | Seed={seed} | Mind={mind.upper()} | Noise={noise}")
    print(f"  Legend: {BLUE}~{RESET} Water  {YELLOW}.{RESET} Plains  {GREEN}^{RESET} Forest  M Mountain  {MAGENTA}S{RESET} Shelter  {BOLD}{RED}@{RESET} Agent\n")

    if engine_mode == "legacy_pack":
        from stranded_physics.packs.legacy import build_legacy_pack
        from stranded_physics.runtime.simulation import PackSimulation
        sim = PackSimulation(build_legacy_pack(seed), mind_type=mind, noise_source=noise)
    elif engine_mode == "physics":
        from stranded_physics.packs.st_vincent_2021 import build
        from stranded_physics.runtime.simulation import PackSimulation
        pack = build(seed)
        sim = PackSimulation(pack, mind_type=mind, noise_source=noise)
    elif scenario == "titanic":
        sim = TitanicSimulation(seed=seed, mind_type=mind, noise_source=noise)
    elif scenario == "pompeii":
        sim = PompeiiSimulation(seed=seed, mind_type=mind, noise_source=noise)
    elif scenario == "waterloo":
        sim = WaterlooSimulation(seed=seed, mind_type=mind, noise_source=noise)
    else:
        sim = SimulationEngine(seed=seed, mind_type=mind, noise_source=noise, scenario=scenario)
    max_steps = getattr(sim, "horizon", DEFAULT_STEPS)

    def on_step(step_record: Dict[str, Any], engine: Any):
        t = step_record["t"]
        state = step_record["state"]
        event = step_record["event"]
        action = step_record["action"]
        probs = step_record["probs"]
        reason = step_record["reason"]
        pos = step_record.get("pos_after", state["pos"])
        in_shelter = engine.world.is_in_shelter(pos[0], pos[1])

        print(f"\n{BOLD}--- Step {t + 1}/{max_steps} | Day {state['day']}, Hour {state['hour']:02d}:00 ---{RESET}")
        map_view = render_ascii_map(engine.world, pos, radius=5)
        print(map_view)

        needs = state["needs"]
        print(f"  Position: [{pos[0]}, {pos[1]}]  | In Shelter: {'Yes' if in_shelter else 'No'} | Injured: {'YES' if state['injured'] else 'No'}")
        print(f"  Hunger: {format_bar(needs['hunger'])}  Thirst: {format_bar(needs['thirst'])}")
        print(f"  Warmth: {format_bar(needs['warmth'])}  Energy: {format_bar(needs['energy'])}")
        print(f"  Safety: {format_bar(needs['safety'])}  Morale: {format_bar(needs['morale'])}")
        print(f"  Stress: {format_bar(state['stress'])}")
        print(f"  Recent Events: {state['recent_events']}")
        print(f"  {BOLD}Event Encountered:{RESET} {YELLOW}{event.upper()}{RESET}")
        print(f"  {BOLD}Chosen Action:{RESET} {GREEN}{action.upper()}{RESET}")
        print(f"  {BOLD}Cognitive Probs:{RESET} { {k: round(v, 3) for k, v in probs.items() if v > 0.05} }")
        print(f"  {BOLD}Cognitive Reason:{RESET} {CYAN}{reason}{RESET}")

        if speed > 0:
            time.sleep(speed)

    try:
        timeline = sim.run(max_steps=max_steps, step_callback=on_step)
    except TypeError:
        timeline = sim.run(max_steps=max_steps)
        for step in timeline.get("steps", []):
            on_step(step, sim)

    print(f"\n{BOLD}========================================================================{RESET}")
    if timeline["outcome"] == "survived":
        span = {"titanic": f"{len(timeline['steps']) * 5} minutes",
                "pompeii": f"{len(timeline['steps']) * 15 / 60:.1f} hours",
                "waterloo": f"{len(timeline['steps']) * 10 / 60:.1f} minutes"}.get(scenario, f"{len(timeline['steps']) * 2} hours")
        print(f"{BOLD}{GREEN}  >>> MISSION OUTCOME: SURVIVED! Successfully endured {span}. <<<{RESET}")
    else:
        print(f"{BOLD}{RED}  >>> MISSION OUTCOME: DIED ({str(timeline['cause']).upper()}) at Step {len(timeline['steps'])}. <<<{RESET}")
    print(f"{BOLD}========================================================================{RESET}\n")


def open_builder(app):
    """The scenario builder, imported only when asked for, so the original scenarios run without the physics packages."""
    from stranded_physics.builder_screen import BuilderScreen
    return BuilderScreen(app)


def main():
    parser = argparse.ArgumentParser(description="Qognition")
    parser.add_argument("--gui", action="store_true", help="Launch interactive 2D Pygame simulation (default)")
    parser.add_argument("--demo", action="store_true", help="Run interactive terminal ASCII survival run")
    parser.add_argument("--terminal", action="store_true", help="Run interactive terminal ASCII survival run")
    parser.add_argument("--batch", action="store_true", help="Compare Quantum vs Classical Mixture vs Classical Rational")
    parser.add_argument("--curate", action="store_true", help="Curate signature runs into demo-pack/")
    parser.add_argument("--export-data", action="store_true", help="Export evacuation survival rates, critical seeds & policy interventions to exports/")
    parser.add_argument("--export-video", action="store_true", help="Export full simulation run MP4 video to exports/videos/")
    parser.add_argument("--test", action="store_true", help="Execute integration test suite")
    parser.add_argument("--seed", type=int, default=101, help="Event hazard or terrain seed")
    parser.add_argument("--mind", type=str, default="quantum",
                        choices=["quantum", "classical_mixture", "classical"], help="Mind engine")
    parser.add_argument("--engine", type=str, default="legacy",
                        choices=["legacy", "physics", "legacy_pack"], help="Simulation runtime: legacy, the T1 St. Vincent physics pack, or the fictional island through the pack runtime")
    parser.add_argument("--noise", type=str, default="stub", help="Noise source profile")
    parser.add_argument("--scenario", type=str, default=None, choices=["island", "volcano", "titanic", "pompeii", "waterloo"], help="Choose scenario directly")
    parser.add_argument("--speed", type=float, default=0.2, help="Seconds delay per step during live demo")
    parser.add_argument("--video-speed", type=float, default=1.0, help="Playback speed multiplier (e.g. 0.25 for Slow-Mo, 2.0 for Fast-Forward) when exporting video")
    parser.add_argument("--output", type=str, default=None, help="Optional output file or directory path for exports")

    args = parser.parse_args()

    if args.test:
        import pytest
        print("[Tech C] Running integration test suite...")
        sys.exit(pytest.main(["-v", "test_contracts_and_engine.py"]))
    elif args.export_data:
        from engine.exporter import export_evacuation_datasets
        out_dir = args.output or "exports"
        info = export_evacuation_datasets(output_dir=out_dir, num_seeds=12)
        print(f"\n{BOLD}{GREEN}=== Exported Evacuation Survival & Policy Datasets ==={RESET}")
        for k, v in info.items():
            print(f"  {k}: {CYAN}{v}{RESET}")
    elif args.export_video:
        from engine.exporter import export_simulation_video
        scen = args.scenario or "volcano"
        info = export_simulation_video(
            scenario=scen,
            seed=args.seed,
            mind=args.mind,
            output_path=args.output,
            speed_multiplier=args.video_speed,
        )
        print(f"\n{BOLD}{GREEN}=== Exported Full Simulation Video ==={RESET}")
        for k, v in info.items():
            print(f"  {k}: {CYAN}{v}{RESET}")
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
        scen = args.scenario or "volcano"
        run_live_demo(seed=args.seed, mind=args.mind, noise=args.noise,
                      scenario=scen, speed=args.speed, engine_mode=args.engine)
    else:
        from engine.gui import launch_gui
        start_screen = "home" if args.scenario else "event_choice"
        print(f"Launching Quantum Cognition Simulation (Seed={args.seed}, Mind={args.mind})...")
        launch_gui(seed=args.seed, mind=args.mind, noise=args.noise, start_screen=start_screen,
                   scenario=args.scenario or "volcano", builder_factory=open_builder)


if __name__ == "__main__":
    main()

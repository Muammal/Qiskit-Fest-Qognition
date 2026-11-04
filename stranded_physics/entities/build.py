"""Turns a scenario file into a scenario the engine can run. No scenario should need new engine code.

    python -m stranded_physics.entities.build check <file>
    python -m stranded_physics.entities.build run <file> --seed 1 [--mind quantum]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from stranded_physics.core.api import InterfaceError, ScenarioSpec, TimeAxis
from stranded_physics.entities.api import ScenarioFile, load_scenario
from stranded_physics.entities.kinds import BUILD_ORDER, KINDS, World, check_entity


def check_scenario(scenario: ScenarioFile) -> None:
    """Every entity can be built, and everything each one depends on is present."""
    present = {entity.kind for entity in scenario.entities}
    for entity in scenario.entities:
        check_entity(entity)
        missing = set(KINDS[entity.kind].needs) - present
        if missing:
            raise InterfaceError(f"{entity.kind} needs {sorted(missing)} in the same scenario")
    if "person" in present and sum(entity.kind == "person" for entity in scenario.entities) != 1:
        raise InterfaceError("One person per scenario for now. Stage 4 of workboard/ENTITIES.md adds groups")
    if "person" in present and "shelter" not in present:
        raise InterfaceError("A person needs at least one shelter to evacuate to")
    if "person" in present and "eruption" not in present:
        raise InterfaceError("People can only play scenarios with an eruption for now. Stage 4 of workboard/ENTITIES.md removes this")


def to_spec(scenario: ScenarioFile) -> ScenarioSpec:
    from stranded_physics.packs.st_vincent_2021 import CONTRACT_GRID, place_sites
    check_scenario(scenario)
    time = TimeAxis(scenario.start_utc, scenario.step_hours * 3600., scenario.hours // scenario.step_hours)
    world = World(time)
    domains = []
    for kind in BUILD_ORDER:
        for entity in (e for e in scenario.entities if e.kind == kind):
            domains.extend(KINDS[kind].build(entity, world))
    person = next((e for e in scenario.entities if e.kind == "person"), None)
    shelters = [e for e in scenario.entities if e.kind == "shelter"]
    sites = {}
    if person:
        sites = place_sites((person.settings["start_lon"], person.settings["start_lat"]), [(s.settings["lon"], s.settings["lat"]) for s in shelters], world.vent)
    local_hour = (time.t0_utc.hour + scenario.local_utc_offset) % 24
    return ScenarioSpec(scenario.id, world.grid, CONTRACT_GRID, time, local_hour, tuple(domains), sites)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("file", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mind", choices=("quantum", "classical"), default="quantum")
    args = parser.parse_args(argv)
    scenario = load_scenario(args.file)
    try:
        check_scenario(scenario)
    except InterfaceError as error:
        print(f"Can't build {scenario.id}: {error}")
        return 1
    if args.command == "check":
        print(f"{scenario.id} can be built: {[entity.kind for entity in scenario.entities]}")
        return 0
    from stranded_physics.packs.builder import build_pack
    from stranded_physics.runtime.simulation import PackSimulation
    pack = build_pack(to_spec(scenario), args.seed)
    if not any(entity.kind == "person" for entity in scenario.entities):
        print(f"{scenario.id}: built pack {pack.content_hash[:12]}, with fields {sorted(pack.header['fields'])}. It has no people, so there is nothing to play.")
        return 0
    timeline = PackSimulation(pack, mind_type=args.mind).run()
    print(f"{scenario.id}: {timeline['outcome']} {timeline['cause'] or ''} after {len(timeline['steps'])} steps. Pack {pack.content_hash[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

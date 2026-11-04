"""Turns a scenario file into a scenario the engine can run. No scenario should need new engine code.

    python -m stranded_physics.entities.build check <file>
    python -m stranded_physics.entities.build run <file> --seed 1 [--mind quantum]
"""
from __future__ import annotations

import argparse
import math
import sys
import zlib
from pathlib import Path
from typing import NamedTuple

import numpy as np

from stranded_physics.core.api import InterfaceError, ScenarioSpec, TimeAxis
from stranded_physics.entities.api import ScenarioFile, load_scenario
from stranded_physics.entities.kinds import BUILD_ORDER, KINDS, World, check_entity
from stranded_physics.st_vincent import to_utm


KM_PER_DEGREE = 111.  # Close enough for spreading people around a point.


class Person(NamedTuple):
    name: str
    start: tuple[float, float]
    mind: str


def check_scenario(scenario: ScenarioFile) -> None:
    """Every entity can be built, and everything each one depends on is present."""
    present = {entity.kind for entity in scenario.entities}
    for entity in scenario.entities:
        check_entity(entity)
        missing = set(KINDS[entity.kind].needs) - present
        if missing:
            raise InterfaceError(f"{entity.kind} needs {sorted(missing)} in the same scenario")
    if present & {"person", "group"} and "shelter" not in present:
        raise InterfaceError("People need at least one shelter to evacuate to")


def people_of(scenario: ScenarioFile) -> list[Person]:
    """Everyone in the scenario, in file order. A group's spread is fixed by the scenario's id, so it never changes between runs."""
    people: list[Person] = []
    for index, entity in enumerate(scenario.entities):
        if entity.kind == "person":
            people.append(Person(entity.name or f"person {len(people) + 1}", (entity.settings["start_lon"], entity.settings["start_lat"]), entity.mind))
        elif entity.kind == "group":
            rng = np.random.default_rng([zlib.crc32(scenario.id.encode()), index])
            for number in range(int(entity.settings["count"])):
                angle, distance = rng.uniform(0., 2. * math.pi), entity.settings["radius_km"] * math.sqrt(rng.uniform()) / KM_PER_DEGREE
                people.append(Person(f"{entity.name or 'group'} {number + 1}", (entity.settings["start_lon"] + distance * math.cos(angle), entity.settings["start_lat"] + distance * math.sin(angle)), entity.mind))
    return people


def to_spec(scenario: ScenarioFile) -> ScenarioSpec:
    from stranded_physics.packs.st_vincent_2021 import CONTRACT_GRID, place_sites
    check_scenario(scenario)
    time = TimeAxis(scenario.start_utc, scenario.step_hours * 3600., scenario.hours // scenario.step_hours)
    world = World(time)
    domains = []
    for kind in BUILD_ORDER:
        for entity in (e for e in scenario.entities if e.kind == kind):
            domains.extend(KINDS[kind].build(entity, world))
    shelters = [e for e in scenario.entities if e.kind == "shelter"]
    people = people_of(scenario)
    sites = {}
    if people:
        sites = place_sites([person.start for person in people], [(s.settings["lon"], s.settings["lat"]) for s in shelters], world.vent)
        for what in ("water", "food"):
            found = [to_utm((e.settings["lon"], e.settings["lat"])) for e in scenario.entities if e.kind == "resource" and e.what == what]
            if found:
                sites[what] = [*sites.get(what, []), *found]
    local_hour = (time.t0_utc.hour + scenario.local_utc_offset) % 24
    return ScenarioSpec(scenario.id, world.grid, CONTRACT_GRID, time, local_hour, tuple(domains), sites)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("file", type=Path)
    parser.add_argument("--seed", type=int, default=1)
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
    from stranded_physics.runtime.group import play_people
    pack = build_pack(to_spec(scenario), args.seed)
    people = people_of(scenario)
    if not people:
        print(f"{scenario.id}: built pack {pack.content_hash[:12]}, with fields {sorted(pack.header['fields'])}. It has no people, so there is nothing to play.")
        return 0
    print(f"{scenario.id}: pack {pack.content_hash[:12]}, {len(people)} people")
    for person, timeline in zip(people, play_people(pack, [person.mind for person in people])):
        print(f"  {person.name} ({person.mind}): {timeline['outcome']} {timeline['cause'] or ''} after {len(timeline['steps'])} steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())

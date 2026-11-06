"""People on a sinking ship. They walk to the boats if their mind chooses to, seats run out, and whoever is left ends up in the water.

Boarding belongs to the crew, not to minds: nothing about seats, boats or the flooding reaches a mind, because the frozen contract has no place for it.
"""

from __future__ import annotations

import math
import zlib
from typing import NamedTuple

import numpy as np

from stranded_physics.core.api import ScenarioPack, XY
from stranded_physics.domains.sea.model import immersion_death_probability
from stranded_physics.entities.api import ScenarioFile
from stranded_physics.runtime.simulation import PackSimulation, Shared

BOARD_REACH_TILES = 2.5  # assumption: close enough to the boat to step in, on a 7 m deck grid.
CREW_PER_BOAT = 2  # assumption: seamen needed before a boat can be lowered. The report's boats carried a few.
ADULT_MALE, ADULT_FEMALE, CHILD = "adult_male", "adult_female", "child"


class Passenger(NamedTuple):
    cohort: str
    group: str
    mind: str
    reach_minutes: float
    boat_crew: bool
    start: XY


def _deck_position(grid, length_m: float, beam_m: float, share: float, across: float) -> XY:
    bow = (grid.nx * grid.dx_m - length_m) / 2
    return grid.x0_m + bow + share * length_m, grid.y0_m - grid.ny * grid.dx_m / 2 + across * (beam_m / 2 - grid.dx_m / 2)


def passengers_of(scenario: ScenarioFile, grid, length_m: float, beam_m: float) -> list[Passenger]:
    """Everyone aboard, in file order. Where each starts is fixed by the scenario's id, so it never changes between runs."""
    people: list[Passenger] = []
    for index, entity in enumerate(scenario.entities):
        if entity.kind != "passengers":
            continue
        settings = entity.settings
        rng = np.random.default_rng([zlib.crc32(scenario.id.encode()), index])
        groups = [ADULT_MALE] * int(settings["men"]) + [ADULT_FEMALE] * int(settings["women"]) + [CHILD] * int(settings["children"])
        crewing = int(round(settings["boat_crew"] * len(groups)))
        for number, group in enumerate(groups):
            share = float(rng.uniform(settings["deck_from"], settings["deck_to"]))
            where = _deck_position(grid, length_m, beam_m, share, float(rng.uniform(-1.0, 1.0)))
            people.append(Passenger(entity.name or f"group {index}", group, entity.mind, settings["reach_minutes"], number < crewing, where))
    return people


def ship_sites(scenario: ScenarioFile, world) -> dict[str, list[XY]]:
    people = passengers_of(scenario, world.grid, world.ship.length_m, world.ship.beam_m)
    middle = _deck_position(world.grid, world.ship.length_m, world.ship.beam_m, 0.5, 0.0)
    stations = list(dict.fromkeys(station for station, _, _ in world.boats))
    return {"spawn": [person.start for person in people] or [middle], "assembly": stations, "water": [middle], "vent": []}


class BoatStation:
    """Seats and a departure time. Boats sharing a station share its queue."""

    def __init__(self, xy: XY, seats: int, launch_s: float) -> None:
        self.xy, self.seats, self.launch_s = xy, seats, launch_s


class ShipSimulation(PackSimulation):
    """One person aboard. Walking and the body are as on land. Only where they can go, and what the water does, differ."""

    def __init__(self, pack: ScenarioPack, passenger: Passenger, index: int, shared: Shared, stations: list[BoatStation], lifebelt: bool = True) -> None:
        super().__init__(pack, mind_type=passenger.mind, person=index, shared=shared)
        self.passenger, self.stations, self.lifebelt = passenger, stations, lifebelt
        self.boat: BoatStation | None = None
        self.heading_for_boat = False  # True once this person has chosen to go and reached the boat deck. A start position stands in for a cabin decks below.
        self.in_water_since: float | None = None
        self.fate = float(self.luck.random())
        self.temperature_c = float(pack.series("sea.temperature")[0])
        alarm = np.flatnonzero(pack.series("ship.alarm") > 0)
        self.free_to_go_s = (float(alarm[0]) * pack.time.dt_s if alarm.size else math.inf) + passenger.reach_minutes * 60.0

    def _clock(self) -> float:
        return len(self.steps) * self.pack.time.dt_s

    def _walk_goal(self, action: str) -> XY | None:
        """Only a person who has reached the boat deck, and chooses to go, heads for a boat that is still there and has seats."""
        at_work = self.passenger.boat_crew and self._clock() >= self.free_to_go_s
        if self.boat is not None or self.in_water_since is not None or self._clock() < self.free_to_go_s or not (at_work or (action == "hide" and self.warned)):
            return None
        open_boats = [station.xy for station in self.stations if station.seats > 0 and station.launch_s > self._clock()]
        return self._nearest_site(open_boats) if open_boats else None

    def after_step(self, clock_s: float) -> None:
        """The water reaches whoever is not in a boat. Each person's fate is drawn once, so a longer time in the water can only make death likelier."""
        if self.steps and clock_s >= self.free_to_go_s and (self.passenger.boat_crew or self.steps[-1]["action"] == "hide"):
            self.heading_for_boat = True
        if not self.agent.alive or self.boat is not None:
            return
        if self.in_water_since is None and self.pack.sample("ship.submerged", self.agent.xy_m, min(clock_s, self.pack.time.dt_s * (self.pack.time.n - 1))) > 0:
            self.in_water_since = clock_s
        if (
            self.in_water_since is not None
            and immersion_death_probability((clock_s - self.in_water_since) / 60.0, self.temperature_c, lifebelt=self.lifebelt) > self.fate
        ):
            self.agent.alive, self.agent.cause = False, "immersion"


def _board(
    people: list[ShipSimulation], stations: list[BoatStation], clock_s: float, women_first: bool, port_women_only: bool, reach_m: float, port_y: float
) -> None:
    """The crew fill each boat from whoever has reached it: seamen first, then women and children if that's the order, then men."""
    waiting = [person for person in people if person.agent.alive and person.boat is None and person.in_water_since is None and person.heading_for_boat]
    for station in stations:
        if station.launch_s <= clock_s - 1e-9 or station.seats <= 0:
            continue
        here = [person for person in waiting if person.boat is None and math.dist(person.agent.xy_m, station.xy) <= reach_m]
        seamen = [person for person in here if person.passenger.boat_crew][:CREW_PER_BOAT]
        rest = [person for person in here if person not in seamen]
        women_children = [person for person in rest if person.passenger.group != ADULT_MALE]
        men = [person for person in rest if person.passenger.group == ADULT_MALE]
        men_allowed = not (port_women_only and station.xy[1] > port_y)
        if women_first:
            queue = [*women_children, *(men if men_allowed and not women_children else [])]
        else:
            queue = rest if men_allowed else women_children
        for person in [*seamen, *queue]:
            if station.seats <= 0:
                break
            person.boat = station
            station.seats -= 1


def play_ship(pack: ScenarioPack, scenario: ScenarioFile) -> list[ShipSimulation]:
    """Everyone, step by step together, because boat seats are shared. Returns each person's finished simulation."""
    grid = pack.grid
    ship = next(entity for entity in scenario.entities if entity.kind == "ship")
    from stranded_physics.domains.ship.model import make_ship, titanic_ship

    spec = (
        titanic_ship()
        if ship.source == "replay"
        else make_ship(
            ship.settings["length_m"],
            ship.settings["beam_m"],
            ship.settings["draught_m"],
            ship.settings["displacement_t"],
            int(ship.settings["compartments"]),
            ship.settings["bulkhead_top_m"],
            ship.settings["boat_deck_m"],
        )
    )
    shared = Shared(pack)
    stations = [BoatStation(xy, int(pack.sample("boats.capacity", xy)), pack.sample("boats.launch", xy)) for xy in pack.sites["assembly"]]
    people = [
        ShipSimulation(pack, passenger, index, shared, stations) for index, passenger in enumerate(passengers_of(scenario, grid, spec.length_m, spec.beam_m))
    ]
    boats = next(entity for entity in scenario.entities if entity.kind == "lifeboats")
    women_first, port_only = bool(boats.settings.get("women_first", 1)), bool(boats.settings.get("port_women_only", 0))
    port_y = grid.y0_m - grid.ny * grid.dx_m / 2
    for step in range(pack.time.n):
        for person in people:
            person.step()
        clock = (step + 1) * pack.time.dt_s
        for person in people:
            person.after_step(clock)
        _board(people, stations, clock, women_first, port_only, BOARD_REACH_TILES * grid.dx_m, port_y)
    return people


def summary(people: list[ShipSimulation]) -> dict[str, float]:
    """Shares saved, in the groupings the 1912 report used, with whatever else the file calls its cohorts."""

    def share(chosen):
        chosen = list(chosen)
        return sum(person.agent.alive for person in chosen) / len(chosen) if chosen else float("nan")

    result = {"all": share(people)}
    for group in (ADULT_MALE, ADULT_FEMALE, CHILD):
        result[group] = share(person for person in people if person.passenger.group == group)
    for cohort in dict.fromkeys(person.passenger.cohort for person in people):
        result[cohort] = share(person for person in people if person.passenger.cohort == cohort)
    result["in_boats"] = sum(person.boat is not None for person in people) / max(len(people), 1)
    return result

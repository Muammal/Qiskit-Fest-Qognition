"""A scenario file in the game window: the same run as PackSimulation, plus what the window draws each step."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from stranded_physics.core.api import InterfaceError, ScenarioPack
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.terrain.model import ST_VINCENT_GRID, Terrain
from stranded_physics.entities.api import ScenarioFile
from stranded_physics.entities.build import Person, check_events_happen, people_of, to_spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.packs.st_vincent_2021 import CONTRACT_GRID
from stranded_physics.runtime.simulation import PackSimulation, Shared
from stranded_physics.st_vincent import to_lonlat, to_utm

ASH_FULL_KG_M2 = 100.  # For drawing only: the deposit at which the map's ash haze reaches full strength.
LONLAT_DECIMALS = 4  # About 10 m, which is finer than the terrain's 90 m cells.
SEA, LOW_LAND, HIGH_FOREST, SUMMIT = (38, 150, 212), (126, 202, 68), (74, 130, 48), (150, 132, 112)
HIGH_FOREST_M, SUMMIT_M = 600., 1200.  # For drawing only.


class GameSimulation(PackSimulation):
    """One person, with the extra surface the game window reads. Nothing here changes how they move or decide."""

    def __init__(self, pack: ScenarioPack, mind_type: str, person: int, shared: Shared) -> None:
        super().__init__(pack, mind_type=mind_type, person=person, shared=shared)
        exported = self._volcano_export()
        self.volcano = SimpleNamespace(phases=exported["phases"], hazard_by_step=exported["hazard_by_step"] or [{}] * pack.time.n)
        self.event_gen = SimpleNamespace(weather=self._weather_labels())
        self.world.pdc, self.world.ash = set(), 0.
        self.agent.recent_events = self.recent_events

    def step(self) -> dict | None:
        record = super().step()
        if record is not None:
            frame = self.volcano.hazard_by_step[record["t"]]
            self.world.pdc = {tuple(cell) for cell in frame.get("active_pdc", ())}
            self.world.ash = min(1., frame.get("ash", 0.) / ASH_FULL_KG_M2)
            self.agent.recent_events = self.recent_events
        return record


@dataclass
class CustomGame:
    """A built scenario ready to play. Replaying reuses the same pack, so every mind meets the same world."""

    pack: ScenarioPack
    people: list[Person]
    title: str
    shared: Shared
    index: int = 0

    @property
    def person(self) -> Person:
        return self.people[self.index]

    def next_person(self) -> None:
        self.index = (self.index + 1) % len(self.people)

    def simulation(self, mind: str) -> GameSimulation:
        return GameSimulation(self.pack, mind, self.index, self.shared)


def build_game(scenario: ScenarioFile, seed: int) -> CustomGame:
    """The slow part, meant for a background thread: the pack, hazard frames and walking routes are all ready before play starts."""
    people = people_of(scenario)
    if not people:
        raise InterfaceError("There is nobody to play yet. Add a person or a group")
    pack = build_pack(to_spec(scenario, seed), seed)
    check_events_happen(pack)
    game = CustomGame(pack, people, scenario.title, Shared(pack))
    simulation = game.simulation(people[0].mind)
    for site in ("assembly", "water", "food"):
        for point in pack.sites.get(site, ()):
            simulation._field(point)
    return game


def map_to_lonlat(fraction_x: float, fraction_y: float) -> tuple[float, float]:
    """A point on the map, as fractions from its top-left corner."""
    grid = CONTRACT_GRID
    lon, lat = to_lonlat((grid.x0_m + fraction_x * grid.nx * grid.dx_m, grid.y0_m - fraction_y * grid.ny * grid.dx_m))
    return round(lon, LONLAT_DECIMALS), round(lat, LONLAT_DECIMALS)


def lonlat_to_map(lonlat: tuple[float, float]) -> tuple[float, float]:
    grid = CONTRACT_GRID
    x, y = to_utm(lonlat)
    return (x - grid.x0_m) / (grid.nx * grid.dx_m), (grid.y0_m - y) / (grid.ny * grid.dx_m)


def terrain_picture(size: int = 130) -> np.ndarray:
    """The land the map covers, as rows of colours, for choosing where things go. Needs the raw terrain data."""
    domain = Terrain()
    store = FieldStore()
    domain.run(ScopedFields(store, domain.id, domain.inputs, domain.outputs), np.random.default_rng(0))
    elevation, land = store.get("terrain.elevation", "m"), store.get("terrain.land_mask", "dimensionless") > 0
    grid, full = CONTRACT_GRID, ST_VINCENT_GRID
    centres = (np.arange(size) + .5) / size * grid.nx * grid.dx_m
    cols = np.clip(((grid.x0_m + centres - full.x0_m) / full.dx_m).astype(int), 0, full.nx - 1)
    rows = np.clip(((full.y0_m - (grid.y0_m - centres)) / full.dx_m).astype(int), 0, full.ny - 1)
    height, is_land = elevation[np.ix_(rows, cols)], land[np.ix_(rows, cols)]
    ramp = np.stack([np.interp(height, (0., HIGH_FOREST_M, SUMMIT_M), channel) for channel in zip(LOW_LAND, HIGH_FOREST, SUMMIT)], axis=-1)
    return np.where(is_land[..., None], ramp, np.array(SEA, float)).astype(np.uint8)

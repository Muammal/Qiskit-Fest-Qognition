"""The entity kinds: which sources each supports, what its dials are, and which engine model it builds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stranded_physics.core.api import Domain, GridSpec, InterfaceError, TimeAxis, XY
from stranded_physics.entities.api import Dial, EntitySpec
from stranded_physics.st_vincent import UTM, VENT_LONLAT, to_utm

WORLD_LON = ("longitude", "degree", -180., 180.)
WORLD_LAT = ("latitude", "degree", -90., 90.)
NOT_BUILT = {("eruption", "catalogue"): 2, ("eruption", "dials"): 2, ("storm", "catalogue"): 2, ("storm", "dials"): 2,
             ("terrain", "catalogue"): 3, ("terrain", "dials"): 3, ("weather", "catalogue"): 3, ("weather", "dials"): 3}
TERRAIN_EVENTS = ("st_vincent",)
WEATHER_EVENTS = ("st_vincent",)
ERUPTION_EVENTS = {"st_vincent_2021": VENT_LONLAT}
STORM_EVENTS = ("beryl_2024",)


def lon_lat_dials(prefix: str, what: str) -> tuple[Dial, Dial]:
    return (Dial(f"{prefix}lon", "degree", -180., 180., f"Longitude of {what}"), Dial(f"{prefix}lat", "degree", -90., 90., f"Latitude of {what}"))


@dataclass
class World:
    """What entities built so far have decided. Later entities read this, so order in the file matters only where stated."""

    time: TimeAxis
    grid: GridSpec | None = None
    vent: XY | None = None


@dataclass(frozen=True)
class Kind:
    name: str
    sources: tuple[str, ...]
    dials: tuple[Dial, ...]
    events: tuple[str, ...]
    needs: tuple[str, ...]
    build: Callable[[EntitySpec, World], tuple[Domain, ...]]


def _terrain(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.terrain.model import ST_VINCENT_GRID, Terrain
    world.grid = ST_VINCENT_GRID
    return (Terrain(),)


def _weather(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.atmos.model import Atmos
    return (Atmos(world.time),)


def _eruption(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.eruption.model import Eruption
    world.vent = to_utm(ERUPTION_EVENTS[entity.event])
    return (Eruption(world.time),)


def _ash(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.tephra.model import Tephra
    return (Tephra(world.grid, world.time, world.vent),)


def _flow(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.pdc.model import Pdc
    return (Pdc(world.grid, world.time, world.vent),)


def _mudflow(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.lahar.model import Lahar
    return (Lahar(world.grid, world.time, world.vent),)


def _storm(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.storm.model import Storm
    return (Storm(world.time, (entity.settings["site_lon"], entity.settings["site_lat"])),)


def _no_model(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    return ()  # People and shelters are sites and bodies in the runtime, not fields in a pack.


KINDS: dict[str, Kind] = {kind.name: kind for kind in (
    Kind("terrain", ("replay",), (), TERRAIN_EVENTS, (), _terrain),
    Kind("weather", ("replay",), (), WEATHER_EVENTS, (), _weather),
    Kind("eruption", ("replay",), (), tuple(ERUPTION_EVENTS), ("terrain",), _eruption),
    Kind("ash", ("replay",), (), (), ("terrain", "weather", "eruption"), _ash),
    Kind("flow", ("replay",), (), (), ("terrain", "eruption"), _flow),
    Kind("mudflow", ("replay",), (), (), ("terrain", "weather", "ash"), _mudflow),
    Kind("storm", ("replay",), lon_lat_dials("site_", "the place whose wind is reported"), STORM_EVENTS, (), _storm),
    Kind("person", ("dials",), lon_lat_dials("start_", "where this person starts"), (), ("terrain", "weather"), _no_model),
    Kind("group", ("dials",), (*lon_lat_dials("start_", "the middle of this group"), Dial("count", "person", 1, 500, "How many people", whole=True),
                               Dial("radius_km", "km", 0., 20., "How far they spread from the middle")), (), ("terrain", "weather"), _no_model),
    Kind("shelter", ("dials",), lon_lat_dials("", "this shelter"), (), ("terrain",), _no_model),
    Kind("resource", ("dials",), lon_lat_dials("", "this resource"), (), ("terrain",), _no_model),
)}
BUILD_ORDER = ("terrain", "weather", "eruption", "ash", "flow", "mudflow", "storm", "person", "group", "shelter", "resource")


def check_entity(entity: EntitySpec) -> None:
    """Refuses anything that can't be built, and says why."""
    kind = KINDS[entity.kind]
    if entity.source not in kind.sources:
        stage = NOT_BUILT.get((entity.kind, entity.source))
        built = f"Stage {stage} of workboard/ENTITIES.md builds it" if stage else f"{entity.kind} supports {kind.sources}"
        raise InterfaceError(f"{entity.kind} from source {entity.source!r} isn't built yet. {built}.")
    if entity.source == "replay" and kind.events and entity.event not in kind.events:
        raise InterfaceError(f"{entity.kind}: no recorded event {entity.event!r}. Known: {list(kind.events)}")
    dials = {dial.name: dial for dial in kind.dials}
    unknown, missing = set(entity.settings) - set(dials), set(dials) - set(entity.settings)
    if unknown or missing:
        raise InterfaceError(f"{entity.kind}: unknown settings {sorted(unknown)}, missing settings {sorted(missing)}")
    for name, value in entity.settings.items():
        dial = dials[name]
        if not dial.low <= value <= dial.high:
            raise InterfaceError(f"{entity.kind}: {name} = {value} is outside {dial.low} to {dial.high} {dial.unit}")
        if dial.whole and value != int(value):
            raise InterfaceError(f"{entity.kind}: {name} must be a whole number, not {value}")

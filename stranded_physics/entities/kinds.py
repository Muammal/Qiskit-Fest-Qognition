"""The entity kinds: which sources each supports, what its dials are, and which engine model it builds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stranded_physics.core.api import Domain, GridSpec, InterfaceError, TimeAxis, XY
from stranded_physics.entities.api import Dial, EntitySpec
from stranded_physics.st_vincent import UTM, VENT_LONLAT, to_utm

WORLD_LON = ("longitude", "degree", -180., 180.)
WORLD_LAT = ("latitude", "degree", -90., 90.)
NOT_BUILT: dict[tuple[str, str], int] = {}  # Every kind's sources are built now. A later stage that adds one lists it here until then.
GENERATED = ("catalogue", "dials")
TERRAIN_EVENTS = ("st_vincent",)
WEATHER_EVENTS = ("st_vincent",)
ERUPTION_EVENTS = {"st_vincent_2021": VENT_LONLAT}
STORM_EVENTS = ("beryl_2024",)
SHIP_EVENTS = ("titanic_1912",)
FLOW_MODELS = ("energy_cone", "depth_averaged")  # The energy cone is the default; the solver takes minutes, not seconds.
SECONDS_PER_HOUR = 3600.
WEATHER_ISLANDS = ("st_vincent", "la_palma", "miyakejima", "montserrat", "stromboli")  # Islands whose weather records are held.
GENERATED_ISLAND_CENTRE = (697000., 1471000.)  # The middle of the game's map, so that a generated island fills it.


def lon_lat_dials(prefix: str, what: str) -> tuple[Dial, Dial]:
    return (Dial(f"{prefix}lon", "degree", -180., 180., f"Longitude of {what}"), Dial(f"{prefix}lat", "degree", -90., 90., f"Latitude of {what}"))


@dataclass
class World:
    """What entities built so far have decided. Later entities read this, so order in the file matters only where stated."""

    time: TimeAxis
    seed: int = 1
    grid: GridSpec | None = None
    vent: XY | None = None
    onset_s: float | None = None  # When a generated eruption begins. None for a recorded one, whose models know their own dates.
    erupted_kg: float | None = None  # How much a generated eruption erupts, which sizes its flows.
    contract_grid: GridSpec | None = None  # Set by a ship, whose deck replaces the land map.
    breach: object = None
    impact_s: float | None = None
    alarm_s: float | None = None
    ship: object = None
    boats: tuple = ()  # Each boat's station, seats and launch time.


@dataclass(frozen=True)
class Kind:
    name: str
    sources: tuple[str, ...]
    dials: tuple[Dial, ...]
    events: tuple[str, ...]
    needs: tuple[str, ...]
    build: Callable[[EntitySpec, World], tuple[Domain, ...]]
    generated_dials: tuple[Dial, ...] = ()  # Settings for the catalogue and dials sources, where they differ from replay.
    model_choice: bool = False  # `event` names a model here, not a record, and may be left out for the first one.
    catalogue_dials: tuple[Dial, ...] | None = None  # Only where the catalogue source's settings differ from the dials source's.

    def dials_for(self, source: str) -> tuple[Dial, ...]:
        if source == "catalogue" and self.catalogue_dials is not None:
            return self.catalogue_dials
        return self.generated_dials if source in GENERATED and self.generated_dials else self.dials


def _sampled(entity: EntitySpec, name: str, scale: float = 1.) -> float | None:
    """A dial's value in the generator's unit, or None so that the generator samples it."""
    return None if name not in entity.settings else entity.settings[name] * scale


def vent_of(entity: EntitySpec) -> XY:
    """Decided before anything is built, because the terrain's hazard zones are measured from it."""
    return to_utm(ERUPTION_EVENTS[entity.event] if entity.source == "replay" else (entity.settings["vent_lon"], entity.settings["vent_lat"]))


def terrain_domain(entity: EntitySpec, seed: int, vent: XY | None = None) -> Domain:
    """The land an entity describes. The builder's map uses this too, so the map always shows the land that will be played on."""
    from stranded_physics.domains.terrain.model import ST_VINCENT_GRID, Terrain
    if entity.source == "replay":
        return Terrain(vent=vent) if vent else Terrain()
    from stranded_physics.domains.terrain.generator import GeneratedTerrain, sample_island
    from stranded_physics.packs.builder import stream
    summit_m, area_km2 = sample_island(stream(seed, "terrain", "generator")) if entity.source == "catalogue" else (None, None)
    return GeneratedTerrain(ST_VINCENT_GRID, GENERATED_ISLAND_CENTRE, entity.settings.get("summit_m", summit_m), entity.settings.get("area_km2", area_km2), vent=vent)


def _terrain(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.terrain.model import ST_VINCENT_GRID
    world.grid = ST_VINCENT_GRID
    return (terrain_domain(entity, world.seed, world.vent),)


def _weather(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    if entity.source == "replay":
        from stranded_physics.domains.atmos.model import Atmos
        return (Atmos(world.time),)
    from stranded_physics.domains.atmos.generator import WeatherDials, WeatherWindow
    if entity.source == "catalogue":
        month = entity.settings.get("month")
        return (WeatherWindow(world.time, entity.what, month=None if month is None else int(month)),)
    return (WeatherDials(world.time, *(entity.settings[dial.name] for dial in WEATHER_DIALS)),)


def _eruption(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.eruption.model import Eruption
    if entity.source == "replay":
        return (Eruption(world.time),)
    from stranded_physics.domains.eruption.generator import from_dials
    from stranded_physics.packs.builder import stream
    made = from_dials(stream(world.seed, "eruption", "generator"), world.time.dt_s * (world.time.n - 1), size=_sampled(entity, "size"),
                      lead_s=_sampled(entity, "lead_hours", SECONDS_PER_HOUR), onset_s=_sampled(entity, "onset_hours", SECONDS_PER_HOUR),
                      column_m=_sampled(entity, "column_m"))
    world.onset_s, world.erupted_kg = made.onset_s, made.total_mass_kg
    return (Eruption(world.time, generated=made),)


def _ash(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.exposure.model import Exposure
    from stranded_physics.domains.tephra.model import Tephra
    return (Tephra(world.grid, world.time, world.vent), Exposure(world.grid, world.time))


def _gas(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.gas.model import Gas
    return (Gas(world.grid, world.time, world.vent),)


def _lava(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.lava.model import Lava
    return (Lava(world.grid, world.time, world.vent, None if world.onset_s is None else 0.),)


def _flow(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.pdc.model import Pdc, SETTINGS, size_scale
    first, scale = None, None
    if world.onset_s is not None:
        delay_s = entity.settings["delay_hours"] * SECONDS_PER_HOUR if "delay_hours" in entity.settings else SETTINGS["generated_collapse_delay"]
        first, scale = world.onset_s + delay_s, size_scale(world.erupted_kg)
    if entity.event == "depth_averaged":
        from stranded_physics.domains.pdc.model_t2 import PdcT2
        return (PdcT2(world.grid, world.time, world.vent, first, 1. if scale is None else scale ** 3),)
    return (Pdc(world.grid, world.time, world.vent, first, None if scale is None else scale * SETTINGS["reference_reach"]),)


def _mudflow(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.lahar.model import Lahar
    return (Lahar(world.grid, world.time, world.vent),)


def _storm(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.storm.model import Storm
    site = (entity.settings["site_lon"], entity.settings["site_lat"])
    if entity.source == "replay":
        return (Storm(world.time, site),)
    from stranded_physics.domains.storm.generator import generate
    from stranded_physics.packs.builder import stream
    made = generate(stream(world.seed, "storm", "generator"), site, world.time.dt_s * (world.time.n - 1), max_wind_m_s=_sampled(entity, "max_wind_m_s"),
                    closest_km=_sampled(entity, "closest_km"), bearing_deg=_sampled(entity, "bearing_deg"), speed_m_s=_sampled(entity, "speed_m_s"),
                    rmax_m=_sampled(entity, "rmax_km", 1000.), closest_s=_sampled(entity, "closest_hours", SECONDS_PER_HOUR))
    return (Storm(world.time, site, generated=made),)


def _no_model(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    return ()  # People and shelters are sites and bodies in the runtime, not fields in a pack.


TERRAIN_DIALS = (Dial("summit_m", "m", 100., 3000., "Height of the summit", optional=True, default=900.),
                 Dial("area_km2", "km2", 10., 250., "Land area of the island", optional=True, default=100.))
WEATHER_DIALS = (Dial("rain_mm_h", "mm/h", 0., 200., "Rain, constant throughout", default=1.),
                 Dial("wind_m_s", "m/s", 0., 80., "Surface wind", default=6.),
                 Dial("wind_bearing_deg", "degrees", 0., 360., "The direction surface air moves toward", default=270.),
                 Dial("temperature_c", "C", -40., 50., "Air temperature", default=27.),
                 Dial("upper_wind_m_s", "m/s", 0., 120., "Wind high up, which carries ash", default=20.),
                 Dial("upper_bearing_deg", "degrees", 0., 360., "The direction high air moves toward", default=90.))
WEATHER_WINDOW_DIALS = (Dial("month", "month", 1, 12, "Month of 2023 to draw the weather from. Unset, any", whole=True, optional=True),)
SHIP_TILES_ALONG = 36  # The hull fills 36 of the map's 40 tiles, leaving sea all round.
MAP_TILES = 40
BOAT_DECK_FORWARD, BOAT_DECK_AFT = .25, .65  # assumption: where the forward and after groups of boats sit, as shares of the ship's length.
BOAT_NAMES_PORT = ("B", "D")  # Even numbers and these collapsibles are on the port side, per the 1912 report.


def _ship(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.core.api import GridSpec
    from stranded_physics.domains.ship.model import Ship, ShipDeck, make_ship, titanic_recorded_sinking, titanic_ship
    settings = entity.settings
    spec = titanic_ship() if entity.source == "replay" else make_ship(settings["length_m"], settings["beam_m"], settings["draught_m"], settings["displacement_t"],
                                                                      int(settings["compartments"]), settings["bulkhead_top_m"], settings["boat_deck_m"])
    dx = spec.length_m / SHIP_TILES_ALONG
    world.grid = world.contract_grid = GridSpec("LOCAL:ship", 0., MAP_TILES * dx, dx, MAP_TILES, MAP_TILES)
    world.ship = spec
    # A replay follows the recorded sinking, so people meet what really happened. A ship with no record sinks as the flooding model says.
    recorded = None if entity.source != "replay" else tuple(world.impact_s + minutes * 60. for minutes in titanic_recorded_sinking())
    return (ShipDeck(world.grid, spec), Ship(world.grid, world.time, spec, _breach_of(world.breach, spec), world.impact_s, world.alarm_s, recorded_sinking=recorded))


def _breach_of(entity: EntitySpec, spec):
    from stranded_physics.domains.ship.model import even_breach, titanic_breach
    if entity.source == "replay":
        return titanic_breach()
    first, holed = int(entity.settings["first_compartment"]), int(entity.settings["holed"])
    if first + holed > len(spec.compartments):
        raise InterfaceError(f"breach: {holed} compartments from number {first} runs past this ship's {len(spec.compartments)}")
    return even_breach(spec, first, holed, entity.settings["area_m2"])


def _breach(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    world.impact_s, world.alarm_s = entity.settings["impact_minutes"] * 60., entity.settings["alarm_minutes"] * 60.
    world.breach = entity
    return ()


def _sea(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.sea.model import Sea, titanic_sea_temperature_c
    return (Sea(world.time, titanic_sea_temperature_c() if entity.source == "replay" else entity.settings["temperature_c"]),)


def boat_position(name: str, spec, grid: GridSpec) -> XY:
    """Boats stand along the deck edges: port is the north edge of the map, because the bow points west. Numbers start at the bow."""
    tag = name.replace("No.", "").strip()
    port = tag in BOAT_NAMES_PORT or (tag.isdigit() and int(tag) % 2 == 0)
    forward = not tag.isdigit() or int(tag) <= 8
    bow = (MAP_TILES - SHIP_TILES_ALONG) / 2 * grid.dx_m
    x = grid.x0_m + bow + (BOAT_DECK_FORWARD if forward else BOAT_DECK_AFT) * spec.length_m
    y_middle = grid.y0_m - MAP_TILES / 2 * grid.dx_m
    return x, y_middle + (.5 if port else -.5) * max(spec.beam_m - grid.dx_m, 0.)


def _lifeboats(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    from stranded_physics.domains.ship.model import Boat, Boats, titanic_boats, titanic_boats_revised
    settings = entity.settings
    if entity.source == "replay":
        boats = titanic_boats() if entity.event == "titanic_1912_inquiry_times" else titanic_boats_revised()
    else:
        count = int(settings["boats"])
        first, last = settings["first_launch_minutes"], settings["last_launch_minutes"]
        boats = tuple(Boat(str(i + 1), int(settings["seats"]), first + (last - first) * i / max(count - 1, 1), False) for i in range(count))
    world.boats = tuple((boat_position(b.name, world.ship, world.grid), b.capacity, world.impact_s + b.launch_minutes * 60.) for b in boats)
    return (Boats(world.grid, list(world.boats)),)


BREACH_TIMES = (Dial("impact_minutes", "minute", 0., 1440., "When it happens, after the scenario starts", default=10.),
                Dial("alarm_minutes", "minute", 0., 1440., "When the crew call people to the boats, after the scenario starts", default=35.))
SHIP_DIALS = (Dial("length_m", "m", 20., 500., "Length of the hull", default=150.), Dial("beam_m", "m", 5., 80., "Width of the hull", default=20.),
              Dial("draught_m", "m", 1., 30., "Depth below the waterline", default=7.), Dial("displacement_t", "t", 100., 500000., "Weight of the ship", default=15000.),
              Dial("compartments", "count", 2, 40, "Watertight compartments", whole=True, default=10), Dial("bulkhead_top_m", "m", .5, 40., "Bulkhead tops above the waterline", default=5.),
              Dial("boat_deck_m", "m", 1., 60., "Boat deck above the waterline", default=15.))
BREACH_DIALS = (Dial("first_compartment", "index", 0, 39, "First holed compartment, counted from the bow", whole=True, default=0), Dial("holed", "count", 1, 40, "How many compartments are holed", whole=True, default=2),
                Dial("area_m2", "m2", .001, 50., "Total size of the opening", default=1.), *BREACH_TIMES)
LIFEBOAT_POLICY = (Dial("women_first", "yes or no", 0, 1, "1 fills boats with women and children first", whole=True, default=1),
                   Dial("port_women_only", "yes or no", 0, 1, "1 lets men into port boats only as crew", whole=True, default=0))
LIFEBOAT_DIALS = (Dial("boats", "count", 1, 100, "How many boats", whole=True, default=10), Dial("seats", "person", 1, 200, "Seats in each boat", whole=True, default=40),
                  Dial("first_launch_minutes", "minute", 0., 1440., "First boat leaves, after the impact", default=30.), Dial("last_launch_minutes", "minute", 0., 1440., "Last boat leaves, after the impact", default=120.),
                  *LIFEBOAT_POLICY)
PASSENGER_DIALS = (Dial("men", "person", 0, 5000, "Adult men", whole=True, default=100), Dial("women", "person", 0, 5000, "Adult women", whole=True, default=100),
                   Dial("children", "person", 0, 5000, "Children", whole=True, default=10), Dial("deck_from", "share", 0., 1., "Start of where they begin, from the bow", default=.2),
                   Dial("deck_to", "share", 0., 1., "End of where they begin, from the bow", default=.8), Dial("reach_minutes", "minute", 0., 240., "Time to reach the boat deck after the alarm", default=10.),
                   Dial("boat_crew", "share", 0., 1., "Share who are needed to man the boats, so board regardless", default=0.))


def _no_domains(entity: EntitySpec, world: World) -> tuple[Domain, ...]:
    return ()


ERUPTION_DIALS = (*lon_lat_dials("vent_", "the vent"),
                  Dial("size", "VEI", 0, 7, "Volcanic Explosivity Index", whole=True, optional=True, default=4),
                  Dial("lead_hours", "hour", 0., 720., "Warning time before the first explosion", optional=True, default=24.),
                  Dial("onset_hours", "hour", 0., 2400., "When the first explosion comes, after the scenario starts", optional=True, default=48.),
                  Dial("column_m", "m", 100., 60000., "Column height above the vent", optional=True, default=15000.))
STORM_DIALS = (*lon_lat_dials("site_", "the place whose wind is reported"),
               Dial("max_wind_m_s", "m/s", 1., 150., "Peak wind of the storm", optional=True, default=50.),
               Dial("closest_km", "km", 0., 2000., "How close its centre passes", optional=True, default=50.),
               Dial("bearing_deg", "degrees", 0., 360., "The compass direction it travels toward", optional=True, default=300.),
               Dial("speed_m_s", "m/s", 1., 30., "How fast its centre moves", optional=True, default=6.),
               Dial("rmax_km", "km", 1., 200., "Radius of its strongest wind", optional=True, default=30.),
               Dial("closest_hours", "hour", 0., 2400., "When it passes closest, after the scenario starts", optional=True, default=48.))


KINDS: dict[str, Kind] = {kind.name: kind for kind in (
    Kind("terrain", ("replay", "catalogue", "dials"), (), TERRAIN_EVENTS, (), _terrain, TERRAIN_DIALS),
    Kind("weather", ("replay", "catalogue", "dials"), (), WEATHER_EVENTS, (), _weather, WEATHER_DIALS, catalogue_dials=WEATHER_WINDOW_DIALS),
    Kind("eruption", ("replay", "catalogue", "dials"), (), tuple(ERUPTION_EVENTS), ("terrain",), _eruption, ERUPTION_DIALS),
    Kind("ash", ("replay",), (), (), ("terrain", "weather", "eruption"), _ash),
    Kind("flow", ("replay",), (Dial("delay_hours", "hour", 0., 240., "For a generated eruption: how long after its first explosion the first flow comes", optional=True),),
         FLOW_MODELS, ("terrain", "eruption"), _flow, model_choice=True),
    Kind("mudflow", ("replay",), (), (), ("terrain", "weather", "ash"), _mudflow),
    Kind("gas", ("replay",), (), (), ("terrain", "weather", "eruption"), _gas),
    Kind("lava", ("replay",), (), (), ("terrain", "eruption"), _lava),
    Kind("storm", ("replay", "catalogue", "dials"), lon_lat_dials("site_", "the place whose wind is reported"), STORM_EVENTS, (), _storm, STORM_DIALS),
    Kind("ship", ("replay", "dials"), (), SHIP_EVENTS, ("breach",), _ship, SHIP_DIALS),
    Kind("breach", ("replay", "dials"), BREACH_TIMES, SHIP_EVENTS, ("ship",), _breach, BREACH_DIALS),
    Kind("lifeboats", ("replay", "dials"), LIFEBOAT_POLICY, (*SHIP_EVENTS, "titanic_1912_inquiry_times"), ("ship",), _lifeboats, LIFEBOAT_DIALS),
    Kind("sea", ("replay", "dials"), (), SHIP_EVENTS, (), _sea, (Dial("temperature_c", "C", -2., 35., "Water temperature", default=10.),)),
    Kind("passengers", ("dials",), PASSENGER_DIALS, (), ("ship", "lifeboats", "sea", "weather"), _no_domains),
    Kind("person", ("dials",), lon_lat_dials("start_", "where this person starts"), (), ("terrain", "weather"), _no_model),
    Kind("group", ("dials",), (*lon_lat_dials("start_", "the middle of this group"), Dial("count", "person", 1, 500, "How many people", whole=True),
                               Dial("radius_km", "km", 0., 20., "How far they spread from the middle")), (), ("terrain", "weather"), _no_model),
    Kind("shelter", ("dials",), lon_lat_dials("", "this shelter"), (), ("terrain",), _no_model),
    Kind("resource", ("dials",), lon_lat_dials("", "this resource"), (), ("terrain",), _no_model),
)}
BUILD_ORDER = ("breach", "ship", "lifeboats", "sea", "passengers", "terrain", "weather", "eruption", "ash", "flow", "mudflow", "gas", "lava", "storm", "person", "group", "shelter", "resource")


def check_entity(entity: EntitySpec) -> None:
    """Refuses anything that can't be built, and says why."""
    kind = KINDS[entity.kind]
    if entity.source not in kind.sources:
        stage = NOT_BUILT.get((entity.kind, entity.source))
        built = f"Stage {stage} of workboard/ENTITIES.md builds it" if stage else f"{entity.kind} supports {kind.sources}"
        raise InterfaceError(f"{entity.kind} from source {entity.source!r} isn't built yet. {built}.")
    if entity.source == "replay" and kind.events and entity.event not in kind.events and not (kind.model_choice and entity.event is None):
        raise InterfaceError(f"{entity.kind}: no recorded event {entity.event!r}. Known: {list(kind.events)}")
    if entity.source != "replay" and entity.event is not None:
        raise InterfaceError(f"{entity.kind}: event names a record, so it can't go with source {entity.source!r}")
    if entity.kind == "weather" and entity.source == "catalogue" and entity.what not in WEATHER_ISLANDS:
        raise InterfaceError(f"weather: what = {entity.what!r} isn't an island with records held. Known: {list(WEATHER_ISLANDS)}")
    dials = {dial.name: dial for dial in kind.dials_for(entity.source)}
    needed = {name for name, dial in dials.items() if entity.source == "dials" or not dial.optional}
    unknown, missing = set(entity.settings) - set(dials), needed - set(entity.settings)
    if unknown or missing:
        raise InterfaceError(f"{entity.kind}: unknown settings {sorted(unknown)}, missing settings {sorted(missing)}")
    for name, value in entity.settings.items():
        dial = dials[name]
        if not dial.low <= value <= dial.high:
            raise InterfaceError(f"{entity.kind}: {name} = {value} is outside {dial.low} to {dial.high} {dial.unit}")
        if dial.whole and value != int(value):
            raise InterfaceError(f"{entity.kind}: {name} must be a whole number, not {value}")

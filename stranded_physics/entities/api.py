"""What an entity is, and what a scenario file holds. Light enough for the checker and a builder screen to import."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

from stranded_physics.core.api import InterfaceError

SOURCES = ("replay", "catalogue", "dials")
PLACES = ("real", "fictional", "generated")
REQUIRED_KEYS = {"id", "title", "place", "start_utc", "hours", "local_utc_offset", "entity"}
STEP_KEYS = {"step_hours", "step_minutes"}  # A scenario gives exactly one. A sinking takes hours, so two-hour steps can't show it.
ENTITY_KEYS = {"kind", "source", "event", "name", "mind", "what"}
MINDS = ("quantum", "classical_mixture", "classical")
RESOURCES = ("water", "food", "wood")
CATEGORY_OF = {
    "terrain": "terrain",
    "weather": "atmos",
    "eruption": "eruption",
    "ash": "tephra",
    "flow": "pdc",
    "mudflow": "lahar",
    "gas": "gas",
    "lava": "lava",
    "ship": "ship",
    "breach": "ship",
    "lifeboats": "ship",
    "sea": "sea",
    "passengers": "agent",
    "storm": "storm",
    "person": "agent",
    "group": "agent",
    "shelter": "agent",
    "resource": "agent",
}


ALSO_USES = {"ash": ("exposure",), "person": ("exposure",), "group": ("exposure",)}  # Ash builds roof failure, and people are exposed to hazards.


@dataclass(frozen=True)
class Dial:
    """One setting a person can change. The builder screen draws these."""

    name: str
    unit: str
    low: float
    high: float
    note: str
    whole: bool = False
    optional: bool = False  # A catalogue source may leave this unset, and then samples it. A dials source must set it.
    default: float | None = None  # What the builder starts from, where the low end of the range would be a poor start.


@dataclass(frozen=True)
class EntitySpec:
    kind: str
    source: str
    event: str | None = None
    name: str = ""
    settings: Mapping[str, float] = field(default_factory=dict)
    mind: str = "quantum"  # For people and groups.
    what: str = ""  # For resources.


@dataclass(frozen=True)
class ScenarioFile:
    id: str
    title: str
    place: str
    start_utc: datetime
    hours: int
    step_hours: int | None
    local_utc_offset: int
    entities: tuple[EntitySpec, ...]
    step_minutes: int | None = None

    @property
    def step_s(self) -> float:
        return self.step_hours * 3600.0 if self.step_hours is not None else self.step_minutes * 60.0

    def evidence_ids(self) -> frozenset[str]:
        """Which gate scenarios speak about this scenario: its own id, plus the generators it samples from."""
        generated = {("eruption", "catalogue"): "generated_eruption", ("storm", "catalogue"): "generated_storm"}
        return frozenset({self.id, *(generated[(e.kind, e.source)] for e in self.entities if (e.kind, e.source) in generated)})

    def variants(self) -> dict[str, str]:
        """Categories using a model other than their first one, so each model's evidence stays with that model."""
        return {"pdc": "t2"} if any(e.kind == "flow" and e.event == "depth_averaged" for e in self.entities) else {}

    def uses(self) -> tuple[str, ...]:
        """The engine categories this scenario relies on, in order, for the checker."""
        ordered: list[str] = []
        for entity in self.entities:
            for category in (CATEGORY_OF[entity.kind], *ALSO_USES.get(entity.kind, ())):
                if category not in ordered:
                    ordered.append(category)
        return tuple(ordered)


def _entity(entry: dict, where: str) -> EntitySpec:
    if "kind" not in entry or "source" not in entry:
        raise InterfaceError(f"{where}: every entity needs a kind and a source")
    if entry["kind"] not in CATEGORY_OF:
        raise InterfaceError(f"{where}: no entity kind {entry['kind']!r}. Known: {sorted(CATEGORY_OF)}")
    if entry["source"] not in SOURCES:
        raise InterfaceError(f"{where}: {entry['kind']} has source {entry['source']!r}. Sources: {SOURCES}")
    settings = {key: value for key, value in entry.items() if key not in ENTITY_KEYS}
    mind = entry.get("mind", "quantum")
    if mind not in MINDS:
        raise InterfaceError(f"{where}: no mind {mind!r}. Minds: {MINDS}")
    what = entry.get("what", "")
    if entry["kind"] == "resource" and what not in RESOURCES:
        raise InterfaceError(f"{where}: a resource needs what = one of {RESOURCES}, not {what!r}")
    return EntitySpec(entry["kind"], entry["source"], entry.get("event"), entry.get("name", ""), settings, mind, what)


def parse_scenario(table: dict, where: str = "scenario") -> ScenarioFile:
    unknown, missing = set(table) - REQUIRED_KEYS - STEP_KEYS, REQUIRED_KEYS - set(table)
    if unknown or missing:
        raise InterfaceError(f"{where}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")
    if len(STEP_KEYS & set(table)) != 1:
        raise InterfaceError(f"{where}: give one of step_hours or step_minutes")
    if table["place"] not in PLACES:
        raise InterfaceError(f"{where}: place must be one of {PLACES}")
    start = datetime.fromisoformat(table["start_utc"])
    if start.utcoffset() is None:
        raise InterfaceError(f"{where}: start_utc needs a timezone, such as +00:00")
    step_minutes = table["step_minutes"] if "step_minutes" in table else table["step_hours"] * 60
    if table["hours"] <= 0 or step_minutes <= 0 or (table["hours"] * 60) % step_minutes:
        raise InterfaceError(f"{where}: hours must be a positive multiple of the step")
    return ScenarioFile(
        table["id"],
        table["title"],
        table["place"],
        start,
        table["hours"],
        table.get("step_hours"),
        table["local_utc_offset"],
        tuple(_entity(entry, f"{where}: entity {i + 1}") for i, entry in enumerate(table["entity"])),
        table.get("step_minutes"),
    )


def load_scenario(path: Path) -> ScenarioFile:
    return parse_scenario(tomllib.loads(Path(path).read_text(encoding="utf-8")), str(path))


def _value(value: object) -> str:
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return repr(value)


def dump_scenario(scenario: ScenarioFile) -> str:
    """The file form of a scenario. The builder screen saves through this, so screen and file can't drift apart."""
    lines = [
        f"id = {_value(scenario.id)}",
        f"title = {_value(scenario.title)}",
        f"place = {_value(scenario.place)}",
        f"start_utc = {_value(scenario.start_utc.isoformat())}",
        f"hours = {scenario.hours}",
        f"step_hours = {scenario.step_hours}" if scenario.step_hours is not None else f"step_minutes = {scenario.step_minutes}",
        f"local_utc_offset = {scenario.local_utc_offset}",
    ]
    for entity in scenario.entities:
        lines += ["", "[[entity]]", f"kind = {_value(entity.kind)}", f"source = {_value(entity.source)}"]
        if entity.event is not None:
            lines.append(f"event = {_value(entity.event)}")
        if entity.name:
            lines.append(f"name = {_value(entity.name)}")
        if entity.kind in ("person", "group", "passengers"):
            lines.append(f"mind = {_value(entity.mind)}")
        if entity.what:
            lines.append(f"what = {_value(entity.what)}")
        lines += [f"{key} = {_value(value)}" for key, value in entity.settings.items()]
    return "\n".join(lines) + "\n"

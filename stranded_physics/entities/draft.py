"""A scenario being edited. The builder screen changes one of these and draws it; every rule lives here, so it can be tested without a window."""
from __future__ import annotations

import math
import os
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Mapping

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities.api import MINDS, PLACES, RESOURCES, ScenarioFile, dump_scenario, load_scenario, parse_scenario
from stranded_physics.entities.build import check_scenario
from stranded_physics.entities.kinds import KINDS, WEATHER_ISLANDS

CARDS = Path(__file__).resolve().parents[1] / "scenario_cards"
SAVED = CARDS / "saved"  # Kept apart from the shipped scenarios, which the builder never overwrites.
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
STEP_HOURS = 2  # PackSimulation moves people in 2-hour steps, the frozen contract's step.
MAX_UTC_OFFSET = 14
WINDOWS_DEVICE_NAMES = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}  # Can never be file names there.
HEADER_KEYS = ("id", "title", "place", "start_utc", "hours", "step_hours", "local_utc_offset")


@dataclass(frozen=True)
class Draft:
    header: Mapping[str, object]
    entries: tuple[Mapping[str, object], ...]


def _usable_id(text: object) -> bool:
    return bool(ID_PATTERN.fullmatch(str(text))) and str(text) not in WINDOWS_DEVICE_NAMES


def _table(path: Path) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def from_file(path: Path) -> Draft:
    """Opens a scenario as a draft, refusing a file the engine wouldn't read."""
    try:
        load_scenario(path)
        table = _table(path)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
        raise InterfaceError(f"Can't read {Path(path).name}: {error}") from error
    return Draft({key: table[key] for key in HEADER_KEYS}, tuple(table["entity"]))


def new_draft() -> Draft:
    """The one place the engine holds land and weather for so far, and when: St Vincent, from its shipped scenario."""
    template = from_file(CARDS / "st_vincent_2021.toml")
    kept = tuple(entry for entry in template.entries if entry["kind"] in ("terrain", "weather"))
    return Draft({**template.header, "id": "new_scenario", "title": "New scenario"}, kept)


def to_scenario(draft: Draft) -> ScenarioFile:
    return parse_scenario({**draft.header, "entity": list(draft.entries)}, "this scenario")


def problem(draft: Draft) -> str | None:
    """The next thing stopping this draft being built, or None."""
    try:
        check_scenario(to_scenario(draft))
    except InterfaceError as error:
        return str(error)
    return None


def _changed(draft: Draft, index: int, entry: Mapping[str, object]) -> Draft:
    return replace(draft, entries=(*draft.entries[:index], entry, *draft.entries[index + 1:]))


def add_entity(draft: Draft, kind: str) -> Draft:
    """A new entity, using what is built. Its position stays unset until someone places it, because no spot is a sensible default."""
    described = KINDS[kind]
    entry: dict[str, object] = {"kind": kind, "source": described.sources[0]}
    if described.events:
        entry["event"] = described.events[0]
    if kind in ("person", "group"):
        entry["mind"] = MINDS[0]
    if kind == "resource":
        entry["what"] = RESOURCES[0]
    return replace(draft, entries=(*draft.entries, {**entry, **_starting_values(described.dials_for(str(entry["source"])), str(entry["source"]))}))


def _starting_values(dials: tuple, source: str) -> dict[str, float]:
    """A catalogue source samples its optional dials, so they start unset. Positions start unset, because no spot is a sensible default."""
    values: dict[str, float] = {}
    for dial in dials:
        if dial.unit == "degree" or (dial.optional and source != "dials"):
            continue
        start = dial.low if dial.default is None else dial.default
        values[dial.name] = int(start) if dial.whole else start
    return values


def remove_entity(draft: Draft, index: int) -> Draft:
    return replace(draft, entries=(*draft.entries[:index], *draft.entries[index + 1:]))


def dials_of(entry: Mapping[str, object]) -> tuple:
    return KINDS[str(entry["kind"])].dials_for(str(entry["source"]))


def set_dial(draft: Draft, index: int, name: str, text: str) -> Draft:
    """Sets one dial from typed text. Anything outside its range is refused, never clamped."""
    dial = next(d for d in dials_of(draft.entries[index]) if d.name == name)
    try:
        value = float(text)
    except ValueError:
        raise InterfaceError(f"{name} needs a number, not {text!r}") from None
    if not (math.isfinite(value) and dial.low <= value <= dial.high):
        raise InterfaceError(f"{name} = {text} is outside {dial.low:g} to {dial.high:g} {dial.unit}")
    if dial.whole and value != int(value):
        raise InterfaceError(f"{name} must be a whole number, not {text}")
    return _changed(draft, index, {**draft.entries[index], name: int(value) if dial.whole else value})


def place(draft: Draft, index: int, lonlat: tuple[float, float]) -> Draft:
    """Puts an entity at a point, through its longitude and latitude dials."""
    names = [dial.name for dial in dials_of(draft.entries[index]) if dial.unit == "degree"]
    if not names:
        raise InterfaceError(f"A {draft.entries[index]['kind']} has no position to set")
    lon, lat = (name for suffix in ("lon", "lat") for name in names if name.endswith(suffix))
    return set_dial(set_dial(draft, index, lon, repr(lonlat[0])), index, lat, repr(lonlat[1]))


def position(entry: Mapping[str, object]) -> tuple[float, float] | None:
    """Where an entity is, or None if it has no position or hasn't been placed."""
    names = [dial.name for dial in dials_of(entry) if dial.unit == "degree"]
    if not names or any(name not in entry for name in names):
        return None
    lon, lat = (name for suffix in ("lon", "lat") for name in names if name.endswith(suffix))
    return float(entry[lon]), float(entry[lat])


def set_name(draft: Draft, index: int, text: str) -> Draft:
    if not text.isprintable():
        raise InterfaceError("A name has to fit on one line")
    entry = {key: value for key, value in draft.entries[index].items() if key != "name"}
    return _changed(draft, index, {**entry, "name": text} if text else entry)


def choices(entry: Mapping[str, object], key: str) -> tuple[str, ...]:
    """What this setting can honestly be right now. Sources that aren't built aren't offered."""
    kind = KINDS[str(entry["kind"])]
    if key == "event":
        return kind.events if entry["source"] == "replay" else ()
    if key == "source":
        return kind.sources
    if key == "mind":
        return MINDS if kind.name in ("person", "group") else ()
    if key == "what":
        if kind.name == "weather" and entry["source"] == "catalogue":
            return WEATHER_ISLANDS
        return RESOURCES if kind.name == "resource" else ()
    return ()


def _with_source(entry: Mapping[str, object], source: str) -> dict[str, object]:
    """An entry under another source: settings that still apply are kept, and everything else goes, so no stale value can be saved."""
    kind = KINDS[str(entry["kind"])]
    dials = kind.dials_for(source)
    names = {dial.name for dial in dials}
    kept = {key: value for key, value in entry.items() if key in ("kind", "name", "mind") or key in names or (key == "what" and kind.name == "resource")}
    if source == "replay" and kind.events and not kind.model_choice:
        kept["event"] = kind.events[0]
    if kind.name == "weather" and source == "catalogue":
        kept["what"] = WEATHER_ISLANDS[0]
    return {**_starting_values(dials, source), **kept, "source": source}


def set_choice(draft: Draft, index: int, key: str, value: str) -> Draft:
    if value not in choices(draft.entries[index], key):
        raise InterfaceError(f"{value!r} isn't available for {key}")
    return _changed(draft, index, _with_source(draft.entries[index], value) if key == "source" else {**draft.entries[index], key: value})


def _whole(key: str, text: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise InterfaceError(f"{key} needs a whole number, not {text!r}") from None


def set_header(draft: Draft, key: str, text: str) -> Draft:
    """Changes one scenario-wide setting, refusing anything the engine wouldn't accept."""
    value: object = text
    if key == "id" and not _usable_id(text):
        raise InterfaceError("An id is 1 to 40 lowercase letters, digits, _ or -, starting with a letter or digit, and can't be a device name such as nul")
    if key == "title" and not (text.strip() and text.isprintable()):
        raise InterfaceError("A title has to be one line, and can't be empty")
    if key == "place" and text not in PLACES:
        raise InterfaceError(f"place must be one of {PLACES}")
    if key == "start_utc":
        try:
            aware = datetime.fromisoformat(text).utcoffset() is not None
        except ValueError:
            raise InterfaceError(f"{text!r} isn't a date and time like 2021-04-08T00:00:00+00:00") from None
        if not aware:
            raise InterfaceError("The start time needs a timezone, such as +00:00")
    if key == "step_hours" and text != str(STEP_HOURS):
        raise InterfaceError(f"People move in {STEP_HOURS}-hour steps, so step_hours has to stay {STEP_HOURS}")
    if key in ("hours", "step_hours", "local_utc_offset"):
        value = _whole(key, text)
    if key == "hours" and (value <= 0 or value % STEP_HOURS):
        raise InterfaceError(f"hours must be a positive multiple of {STEP_HOURS}")
    if key == "local_utc_offset" and abs(value) > MAX_UTC_OFFSET:
        raise InterfaceError(f"local_utc_offset must be within {MAX_UTC_OFFSET} hours of UTC")
    return replace(draft, header={**draft.header, key: value})


def _shipped_ids() -> set[str]:
    return {path.stem for path in CARDS.glob("*.toml")}


def borrows_evidence(draft: Draft) -> bool:
    """True when this uses a shipped scenario's id but isn't that scenario. Results are tied to the id, so they wouldn't belong to this."""
    shipped = CARDS / f"{draft.header['id']}.toml"
    return str(draft.header["id"]) in _shipped_ids() and to_scenario(draft) != load_scenario(shipped)


def save_draft(draft: Draft, folder: Path = SAVED) -> Path:
    """Saves through dump_scenario, then reads the file back. Refuses to keep a file that wouldn't reload identically."""
    found = problem(draft)
    if found:
        raise InterfaceError(found)
    scenario = to_scenario(draft)
    if not _usable_id(scenario.id):
        raise InterfaceError(f"{scenario.id!r} can't be used as an id")
    if scenario.id in _shipped_ids():
        raise InterfaceError(f"{scenario.id!r} is a shipped scenario, and results are tied to its id. Give this copy a new id before saving")
    text = dump_scenario(scenario)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{scenario.id}.toml"
    trial = folder / f"{scenario.id}.saving"  # Checked before it replaces anything, so a failed save can't cost the previous file.
    trial.write_text(text, encoding="utf-8", newline="\n")
    if load_scenario(trial) != scenario or dump_scenario(load_scenario(trial)) != text:
        trial.unlink()
        raise InterfaceError(f"{path.name} didn't reload identically, so it wasn't kept")
    os.replace(trial, path)
    return path


def saved_scenarios(folder: Path = SAVED) -> list[Path]:
    """Shipped scenarios first, then the ones people have saved."""
    return [*sorted(CARDS.glob("*.toml")), *sorted(Path(folder).glob("*.toml"))]


def terrain_entry(draft: Draft) -> Mapping[str, object] | None:
    return next((entry for entry in draft.entries if entry["kind"] == "terrain"), None)

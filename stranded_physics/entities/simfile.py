"""Sim files: one small file that carries a scenario to any copy of the app.

A `.qsim` file is JSON around a scenario's text. It holds data only: nothing in it is ever run as
code, and it can't name a file on anyone's computer. Files may come from strangers on the internet,
so everything is checked here before it reaches the builder, and the limits below are hard limits.

The hash catches damage in transit. It doesn't say who made a file, or that the file is any good.

    export_sim   a draft to a .qsim file
    read_sim     checked bytes to a Sim
    fetch_sim    a link to a Sim
    fetch_gallery, fetch_gallery_sim   the public gallery in this repository
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import tomllib
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from stranded_physics.core.api import InterfaceError
from stranded_physics.entities import draft as edit
from stranded_physics.entities.api import ScenarioFile, dump_scenario
from stranded_physics.entities.build import people_of

FORMAT, VERSION, SUFFIX = "qognition-sim", 1, ".qsim"
ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "exports" / "sims"
RAW_DATA = ROOT / "artifacts" / "physics" / "raw"
MAX_BYTES = 256 * 1024
MAX_ENTITIES, MAX_PEOPLE, MAX_HOURS, MAX_SEED = 64, 500, 240, 2 ** 31 - 1
MAX_SHORT_TEXT, MAX_LONG_TEXT = 120, 600
TIMEOUT_S, MAX_REDIRECTS = 15, 4
REPOSITORY = "Muammal/Qiskit-Fest-Qognition"
GALLERY_ROOT = f"https://raw.githubusercontent.com/{REPOSITORY}/main/community"
GALLERY_INDEX = f"{GALLERY_ROOT}/index.json"
UPLOAD_PAGE = f"https://github.com/{REPOSITORY}/upload/main/community/sims"
GALLERY_FILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}\.qsim")
ENVELOPE_KEYS = {"format", "version", "title", "author", "description", "created_utc", "seed", "needs_data_pack", "scenario", "sha256"}
# Sources that read the data pack, tested by building each one on a checkout that doesn't hold it.
DATA_PACK_SOURCES = {("terrain", "replay"), ("weather", "replay"), ("weather", "catalogue"), ("eruption", "replay"), ("storm", "replay")}
SHIP_KINDS = {"ship", "breach", "lifeboats", "sea", "passengers"}
DATA_PACK_HELP = "This sim needs the 230 MB data pack, which this copy doesn't hold. Get it with: python tools/fetch_artifacts.py"


@dataclass(frozen=True)
class Sim:
    draft: edit.Draft
    seed: int
    author: str
    description: str
    created_utc: str
    needs_data_pack: bool
    sha256: str

    @property
    def title(self) -> str:
        return str(self.draft.header["title"])


def needs_data_pack(scenario: ScenarioFile) -> bool:
    """True if this can't be built without the raw data download."""
    return any((entity.kind, entity.source) in DATA_PACK_SOURCES for entity in scenario.entities)


def data_pack_present() -> bool:
    return RAW_DATA.is_dir() and any(RAW_DATA.iterdir())


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plain(text: object, limit: int, what: str) -> str:
    """One piece of someone else's text. Control and direction-changing characters are refused, not cleaned."""
    if not isinstance(text, str):
        raise InterfaceError(f"{what} has to be text")
    if len(text) > limit:
        raise InterfaceError(f"{what} is longer than {limit} characters")
    if any(unicodedata.category(character) in ("Cc", "Cf", "Cs", "Co", "Cn") and character != "\n" for character in text):
        raise InterfaceError(f"{what} holds characters that can't be shown")
    return text


def _walk_text(value: object, where: str) -> None:
    if isinstance(value, str):
        _plain(value, MAX_SHORT_TEXT, where)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _walk_text(key, where)
            _walk_text(item, where)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk_text(item, where)


def _check_size(draft: edit.Draft) -> None:
    if len(draft.entries) > MAX_ENTITIES:
        raise InterfaceError(f"This has {len(draft.entries)} things in it. A sim file can hold {MAX_ENTITIES}")
    if not isinstance(draft.header.get("hours"), int) or draft.header["hours"] > MAX_HOURS:
        raise InterfaceError(f"A sim file can run for {MAX_HOURS} hours at most")


def _checked_scenario(draft: edit.Draft) -> ScenarioFile:
    """Everything a sim file must be, on the way in and on the way out."""
    _check_size(draft)
    found = edit.problem(draft)
    if found:
        raise InterfaceError(found)
    scenario = edit.to_scenario(draft)
    if not edit.usable_id(scenario.id):
        raise InterfaceError(f"{scenario.id!r} can't be used as an id")
    if scenario.id in edit.shipped_ids():
        raise InterfaceError(f"{scenario.id!r} belongs to a shipped scenario, and results are tied to it, so a sim file can't use it. Choose another id")
    if {entity.kind for entity in scenario.entities} & SHIP_KINDS:
        raise InterfaceError("Ship scenarios only run from the command line for now, so they can't be shared as sim files")
    people = len(people_of(scenario))
    if not people:
        raise InterfaceError("There is nobody in this yet. Add a person or a group")
    if people > MAX_PEOPLE:
        raise InterfaceError(f"This has {people} people. A sim file can hold {MAX_PEOPLE}")
    return scenario


def to_bytes(draft: edit.Draft, seed: int, author: str = "", description: str = "", now: datetime | None = None) -> bytes:
    scenario = _checked_scenario(draft)
    _walk_text(draft.header, "The scenario")
    _walk_text(draft.entries, "The scenario")
    if not 0 <= seed <= MAX_SEED:
        raise InterfaceError(f"The seed has to be from 0 to {MAX_SEED}")
    text = dump_scenario(scenario)
    envelope = dict(format=FORMAT, version=VERSION, title=scenario.title, author=_plain(author, MAX_SHORT_TEXT, "The author"),
                    description=_plain(description, MAX_LONG_TEXT, "The description"),
                    created_utc=(now or datetime.now(timezone.utc)).isoformat(timespec="seconds"), seed=seed,
                    needs_data_pack=needs_data_pack(scenario), scenario=text, sha256=_digest(text))
    data = json.dumps(envelope, indent=1, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise InterfaceError(f"This comes to {len(data):,} bytes. A sim file can be {MAX_BYTES:,}")
    return data


def export_sim(draft: edit.Draft, seed: int, author: str = "", description: str = "", folder: Path = EXPORTS) -> Path:
    data = to_bytes(draft, seed, author, description)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{draft.header['id']}{SUFFIX}"
    path.write_bytes(data)
    return path


def read_sim(data: bytes) -> Sim:
    """Checks bytes from anywhere. Raises InterfaceError, with a reason a person can act on, for anything wrong."""
    if len(data) > MAX_BYTES:
        raise InterfaceError(f"That file is too big to be a sim file. The limit is {MAX_BYTES:,} bytes")
    try:
        envelope = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise InterfaceError("That isn't a sim file: it can't be read") from None
    if not isinstance(envelope, dict) or envelope.get("format") != FORMAT:
        raise InterfaceError("That isn't a Qognition sim file")
    if not isinstance(envelope.get("version"), int) or envelope["version"] < 1:
        raise InterfaceError("That sim file has no usable version")
    if envelope["version"] > VERSION:
        raise InterfaceError("That sim file was made by a newer version of the app. Update the app to open it")
    if set(envelope) != ENVELOPE_KEYS:
        raise InterfaceError("That sim file has missing or unknown fields")
    text = envelope["scenario"]
    if not isinstance(text, str) or _digest(text) != envelope["sha256"]:
        raise InterfaceError("That sim file is damaged: its contents don't match its hash")
    seed = envelope["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= MAX_SEED:
        raise InterfaceError("That sim file has no usable seed")
    author = _plain(envelope["author"], MAX_SHORT_TEXT, "The author")
    description = _plain(envelope["description"], MAX_LONG_TEXT, "The description")
    created = _plain(envelope["created_utc"], MAX_SHORT_TEXT, "The date")
    try:
        draft = edit.draft_from_table(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
        raise InterfaceError(f"That sim file's scenario can't be read: {error}") from None
    _walk_text(draft.header, "The scenario")
    _walk_text(draft.entries, "The scenario")
    scenario = _checked_scenario(draft)
    return Sim(draft, seed, author, description, created, needs_data_pack(scenario), envelope["sha256"])


def read_path(path: Path) -> Sim:
    path = Path(path)
    if path.suffix.lower() != SUFFIX:
        raise InterfaceError(f"Only {SUFFIX} files can be opened here, not {path.name}")
    try:
        if path.stat().st_size > MAX_BYTES:
            raise InterfaceError(f"That file is too big to be a sim file. The limit is {MAX_BYTES:,} bytes")
        return read_sim(path.read_bytes())
    except OSError as error:
        raise InterfaceError(f"Can't read {path.name}: {error.strerror or error}") from None


# ---- The internet ----
def normalise_link(url: str) -> str:
    """Accepts a GitHub file page as well as the file itself."""
    url = url.strip()
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/blob/(.+)", url)
    return f"https://raw.githubusercontent.com/{match[1]}/{match[2]}" if match else url


def _check_link(url: str) -> None:
    """HTTPS to a public address only, so a link in a file can't reach this computer or its network."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise InterfaceError("That link has to start with https://")
    if parts.username or parts.password:
        raise InterfaceError("That link holds a user name or password, so it wasn't opened")
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise InterfaceError(f"Can't find {parts.hostname}. Check the link and your connection") from None
    for *_ignored, address in addresses:
        if not ipaddress.ip_address(address[0].split("%")[0]).is_global:
            raise InterfaceError(f"{parts.hostname} isn't a public address, so it wasn't opened")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECTS

    def redirect_request(self, request, stream, code, message, headers, new_url):
        _check_link(new_url)
        return super().redirect_request(request, stream, code, message, headers, new_url)


def _download(url: str, limit: int) -> bytes:
    _check_link(url)
    opener = urllib.request.build_opener(_CheckedRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": "Qognition"})
    try:
        with opener.open(request, timeout=TIMEOUT_S) as response:
            data = response.read(limit + 1)
    except urllib.error.HTTPError as error:
        raise InterfaceError(f"The server said {error.code}, so nothing was downloaded") from None
    except (urllib.error.URLError, OSError) as error:
        raise InterfaceError(f"Couldn't download that: {getattr(error, 'reason', error)}") from None
    if len(data) > limit:
        raise InterfaceError(f"That download is over the {limit:,} byte limit, so it was dropped")
    return data


def fetch_sim(url: str) -> Sim:
    return read_sim(_download(normalise_link(url), MAX_BYTES))


def _gallery_row(row: object) -> dict | None:
    """One row of the public list, or None if it isn't usable. A bad row must not cost the others."""
    try:
        if not GALLERY_FILE.fullmatch(row["file"]):
            return None
        return dict(file=row["file"], title=_plain(row["title"], MAX_SHORT_TEXT, "title"), author=_plain(row["author"], MAX_SHORT_TEXT, "author"),
                    description=_plain(row["description"], MAX_LONG_TEXT, "description"), needs_data_pack=row["needs_data_pack"] is True, sha256=str(row["sha256"]))
    except (KeyError, TypeError, InterfaceError):
        return None


def parse_gallery(data: bytes) -> list[dict]:
    try:
        table = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise InterfaceError("The gallery list can't be read") from None
    rows = table.get("sims") if isinstance(table, dict) else None
    if not isinstance(rows, list):
        raise InterfaceError("The gallery list can't be read")
    return [row for row in map(_gallery_row, rows) if row]


def fetch_gallery() -> list[dict]:
    return parse_gallery(_download(GALLERY_INDEX, 4 * MAX_BYTES))


def fetch_gallery_sim(row: Mapping[str, object]) -> Sim:
    sim = read_sim(_download(f"{GALLERY_ROOT}/sims/{row['file']}", MAX_BYTES))
    if sim.sha256 != row["sha256"]:
        raise InterfaceError("That sim doesn't match the gallery's list, so it wasn't opened")
    return sim

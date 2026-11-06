"""Restores terrain raw files from their records, and refuses anything that fails its size or hash check.

python -m stranded_physics.domains.terrain.fetch
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

from stranded_physics.core.api import DatasetRecord, InterfaceError
from stranded_physics.core.records import load_datasets
from stranded_physics.domains.terrain.model import HERE, RAW, raw_path

USER_AGENT = "stranded-physics-fetch"
TIMEOUT_S = 120


def check_file(path: Path, record: DatasetRecord) -> None:
    rule, _, amount = record.content_check.partition(":")
    if rule != "min_bytes":
        raise InterfaceError(f"{record.id}: unknown content_check {record.content_check!r}")
    if path.stat().st_size < int(amount):
        raise InterfaceError(f"{record.id}: {path.name} is smaller than {amount} bytes, so it may be an error page")
    if hashlib.sha256(path.read_bytes()).hexdigest() != record.sha256:
        raise InterfaceError(f"{record.id}: {path.name} does not match its recorded sha256")


def fetch(record: DatasetRecord) -> Path:
    target = raw_path(record.url)
    if not target.exists():
        partial = target.with_suffix(target.suffix + ".partial")
        request = urllib.request.Request(record.url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        partial.replace(target)
    check_file(target, record)
    return target


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for record in load_datasets(HERE / "datasets.toml", "terrain"):
        print(f"{record.id}: {fetch(record).name} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())

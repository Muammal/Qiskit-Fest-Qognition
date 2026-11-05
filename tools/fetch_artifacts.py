"""Downloads the shareable raw data from the repo's `data-v1` release and puts it in `artifacts/physics/raw/`.

    python tools/fetch_artifacts.py

Every part, the joined archive and every file are checked against their SHA-256 hashes. Parts already downloaded are kept.
Research papers and some third-party web pages aren't shared, because we don't have the right to redistribute them.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "https://github.com/Muammal/Qiskit-Fest-Qognition/releases/download/data-v1/"
ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "artifacts" / "downloads"
PREFIX = "artifacts/physics/raw/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(name: str) -> Path:
    target = DOWNLOADS / name
    print(f"Downloading {name}...", flush=True)
    urllib.request.urlretrieve(RELEASE + name, target)
    return target


def fetch_part(part: dict) -> Path:
    path = DOWNLOADS / part["name"]
    if not (path.exists() and sha256(path) == part["sha256"]):
        path = download(part["name"])
    if sha256(path) != part["sha256"]:
        raise SystemExit(f"{part['name']} doesn't match its hash. Delete it and run this again.")
    return path


def join(parts: list[Path], manifest: dict) -> Path:
    archive = DOWNLOADS / manifest["archive"]
    with archive.open("wb") as out:
        for part in parts:
            out.write(part.read_bytes())
    if sha256(archive) != manifest["archive_sha256"]:
        raise SystemExit("The joined archive doesn't match its hash. Delete artifacts/downloads and run this again.")
    return archive


def extract(archive: Path, manifest: dict) -> None:
    expected = {item["path"]: item["sha256"] for item in manifest["files"]}
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            relative = name.removeprefix(PREFIX)
            if not name.startswith(PREFIX) or relative not in expected or ".." in Path(relative).parts:
                raise SystemExit(f"Unexpected file in the archive: {name}")
            bundle.extract(name, ROOT)
    for relative, digest in expected.items():
        if sha256(ROOT / PREFIX / relative) != digest:
            raise SystemExit(f"{relative} doesn't match its hash after extracting.")


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(download("manifest.json").read_text(encoding="utf-8"))
    archive = join([fetch_part(part) for part in manifest["parts"]], manifest)
    extract(archive, manifest)
    archive.unlink()
    print(f"Done: {len(manifest['files'])} files in {PREFIX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

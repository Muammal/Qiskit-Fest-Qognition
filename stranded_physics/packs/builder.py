"""Builds one immutable ScenarioPack offline. The same scenario and seed always give the same hash."""

from __future__ import annotations

import hashlib
import json
import zlib
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from stranded_physics.core.api import Domain, GridSpec, InterfaceError, INTERFACE_VERSION, ScenarioSpec, TimeAxis, Verdict, XY
from stranded_physics.core.fields import FieldStore, ScopedFields

AGENT_DRAWS_PER_STEP = 4
PACK_SCHEMA = "stranded-pack-1"


def stream(seed: int, category: str, name: str = "main") -> np.random.Generator:
    """An independent random stream for one category. Global `random` and `hash()` are not allowed."""
    return np.random.default_rng(np.random.SeedSequence([seed, zlib.crc32(category.encode()), zlib.crc32(name.encode())]))


def dependency_order(domains: Sequence[Domain]) -> list[Domain]:
    """Sort so producers run before consumers. Missing, duplicate or circular links are errors."""
    producer: dict[str, Domain] = {}
    for domain in domains:
        for output in domain.outputs:
            if output.name in producer:
                raise InterfaceError(f"{output.name} has two producers: {producer[output.name].id} and {domain.id}")
            producer[output.name] = domain
    for domain in domains:
        for field in domain.inputs:
            if field.name not in producer:
                raise InterfaceError(f"{domain.id} needs {field.name}, and nothing in this scenario produces it")
            if producer[field.name].outputs and field.kind != next(o for o in producer[field.name].outputs if o.name == field.name).kind:
                raise InterfaceError(f"{domain.id} expects {field.name} as {field.kind}")
    ordered: list[Domain] = []
    state: dict[str, str] = {}

    def visit(domain: Domain) -> None:
        if state.get(domain.id) == "done":
            return
        if state.get(domain.id) == "active":
            raise InterfaceError(f"circular dependency through {domain.id}")
        state[domain.id] = "active"
        for field in domain.inputs:
            visit(producer[field.name])
        state[domain.id] = "done"
        ordered.append(domain)

    for domain in sorted(domains, key=lambda d: d.id):
        visit(domain)
    return ordered


class Pack:
    """Read-only view of built fields. See ScenarioPack in core/api.py."""

    def __init__(self, header: dict, arrays: Mapping[str, np.ndarray]) -> None:
        self.header, self._arrays = header, dict(arrays)
        for array in self._arrays.values():
            array.setflags(write=False)
        self.scenario, self.seed = header["scenario"], header["seed"]
        self.content_hash: str = header["content_hash"]
        self.verdicts: dict[str, Verdict] = header["verdicts"]
        self.grid = GridSpec(**header["grid"])
        self.contract_grid = GridSpec(**header["contract_grid"])
        self.time = TimeAxis(datetime.fromisoformat(header["time"]["t0_utc"]), header["time"]["dt_s"], header["time"]["n"])
        self.t0_local_hour: int = header["t0_local_hour"]
        self.sites: dict[str, list[XY]] = {k: [tuple(p) for p in v] for k, v in header["sites"].items()}
        self.agent_uniforms = self._arrays["__agent_uniforms__"]

    def _kind(self, name: str) -> str:
        if name not in self.header["fields"]:
            raise InterfaceError(f"this pack has no field {name}")
        return self.header["fields"][name]["kind"]

    def has(self, name: str) -> bool:
        return name in self.header["fields"]

    def sample(self, name: str, xy_m: XY, t_s: float | None = None) -> float:
        kind, array = self._kind(name), self._arrays[name]
        if kind == "series":
            raise InterfaceError(f"{name} is a series; use series()")
        located = self.grid.locate(xy_m)
        if located is None:
            return float("inf") if kind == "arrival" else 0.0
        if kind == "frames":
            if t_s is None:
                raise InterfaceError(f"{name} changes with time; pass t_s")
            return float(array[self.time.index_at(t_s), located[0], located[1]])
        return float(array[located])

    def series(self, name: str) -> np.ndarray:
        if self._kind(name) != "series":
            raise InterfaceError(f"{name} is not a series")
        return self._arrays[name]

    def frame(self, name: str, t_s: float | None = None) -> np.ndarray:
        kind, array = self._kind(name), self._arrays[name]
        if kind == "frames":
            if t_s is None:
                raise InterfaceError(f"{name} changes with time; pass t_s")
            return array[self.time.index_at(t_s)]
        if kind == "series":
            raise InterfaceError(f"{name} is a series; use series()")
        return array


def _content_hash(header: dict, arrays: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256(json.dumps({k: v for k, v in header.items() if k != "content_hash"}, sort_keys=True, default=str).encode())
    for name in sorted(arrays):
        digest.update(name.encode())
        digest.update(arrays[name].tobytes())
    return digest.hexdigest()


def build_pack(spec: ScenarioSpec, seed: int, verdicts: Mapping[str, Verdict] | None = None) -> Pack:
    """Run every category once. A validity breach is recorded and blocks play, never silently passed."""
    store = FieldStore()
    recorded: dict[str, Verdict] = dict(verdicts or {})
    budgets: dict[str, dict[str, float]] = {}
    domain_rows = []
    for domain in dependency_order(spec.domains):
        scoped = ScopedFields(store, domain.id, domain.inputs, domain.outputs)
        problems = domain.check_validity(scoped)
        if problems:
            recorded[f"{domain.id}.validity"] = "OUT_OF_DOMAIN"
        budgets[domain.id] = {k: float(v) for k, v in domain.run(scoped, stream(seed, domain.id)).items()}
        domain_rows.append({"id": domain.id, "tier": domain.tier, "problems": problems, "parameters": [p.id for p in domain.parameters]})
    arrays = {name: store.stored(name).data for name in store.names()}
    arrays["__agent_uniforms__"] = stream(seed, "agent", "uniforms").random((spec.time.n, AGENT_DRAWS_PER_STEP))
    header = {
        "schema": PACK_SCHEMA,
        "interface_version": INTERFACE_VERSION,
        "scenario": spec.name,
        "seed": seed,
        "verdicts": recorded,
        "domains": domain_rows,
        "budgets": budgets,
        "grid": asdict(spec.grid),
        "contract_grid": asdict(spec.contract_grid),
        "time": {"t0_utc": spec.time.t0_utc.isoformat(), "dt_s": spec.time.dt_s, "n": spec.time.n},
        "t0_local_hour": spec.t0_local_hour,
        "sites": {k: [list(p) for p in v] for k, v in spec.sites.items()},
        "fields": {name: {"unit": store.stored(name).unit, "kind": store.stored(name).kind} for name in store.names()},
    }
    header["content_hash"] = _content_hash(header, arrays)
    return Pack(header, arrays)


def save_pack(pack: Pack, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, __header__=np.array(json.dumps(pack.header)), **pack._arrays)


def load_pack(path: Path) -> Pack:
    with np.load(path, allow_pickle=False) as archive:
        header = json.loads(str(archive["__header__"]))
        if header.get("schema") != PACK_SCHEMA:
            raise InterfaceError(f"{path} has schema {header.get('schema')!r}, expected {PACK_SCHEMA!r}")
        arrays = {k: archive[k] for k in archive.files if k != "__header__"}
    if _content_hash(header, arrays) != header["content_hash"]:
        raise InterfaceError(f"{path} does not match its content hash")
    return Pack(header, arrays)

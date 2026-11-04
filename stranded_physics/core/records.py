"""Strict loaders for params.toml and datasets.toml. Unknown keys are rejected, never ignored."""
from __future__ import annotations

import tomllib
from pathlib import Path

from stranded_physics.core.api import DatasetRecord, InterfaceError, Parameter, Q_, Split

PARAM_KEYS = {"id", "value", "unit", "valid_min", "valid_max", "role", "status", "source", "sd"}
DATASET_KEYS = {"id", "kind", "url", "retrieved_utc", "sha256", "licence", "licence_confirmed", "citation", "split", "content_check", "notes"}


def _check_keys(entry: dict, allowed: set[str], where: str) -> None:
    unknown = set(entry) - allowed
    if unknown:
        raise InterfaceError(f"{where}: unknown keys {sorted(unknown)}")


def load_parameters(path: Path) -> tuple[Parameter, ...]:
    table = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    _check_keys(table, {"parameter"}, str(path))
    parameters = []
    for entry in table.get("parameter", []):
        _check_keys(entry, PARAM_KEYS, f"{path}: {entry.get('id')}")
        unit = entry["unit"]
        parameters.append(Parameter(
            id=entry["id"], value=Q_(entry["value"], unit),
            valid=(Q_(entry["valid_min"], unit), Q_(entry["valid_max"], unit)),
            role=entry["role"], status=entry["status"], source=entry.get("source"),
            sd=Q_(entry["sd"], unit) if "sd" in entry else None))
    return tuple(parameters)


def load_datasets(path: Path, category: str) -> tuple[DatasetRecord, ...]:
    table = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    _check_keys(table, {"dataset"}, str(path))
    records = []
    for entry in table.get("dataset", []):
        _check_keys(entry, DATASET_KEYS, f"{path}: {entry.get('id')}")
        records.append(DatasetRecord(category=category, **entry))
    return tuple(records)


def open_for_calibration(records: tuple[DatasetRecord, ...], dataset_id: str) -> DatasetRecord:
    """Refuses held-out data, so a model can't be tuned on what later judges it."""
    return _select(records, dataset_id, allowed=("calibration", "reference"))


def open_for_validation(records: tuple[DatasetRecord, ...], dataset_id: str) -> DatasetRecord:
    return _select(records, dataset_id, allowed=("holdout", "reference"))


def _select(records: tuple[DatasetRecord, ...], dataset_id: str, allowed: tuple[Split, ...]) -> DatasetRecord:
    match = next((r for r in records if r.id == dataset_id), None)
    if match is None:
        raise InterfaceError(f"no dataset {dataset_id!r}")
    if match.split not in allowed:
        raise InterfaceError(f"{dataset_id} has split {match.split!r}; this use allows only {allowed}")
    return match

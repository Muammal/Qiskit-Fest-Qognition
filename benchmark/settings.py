"""Scoped overrides of imported mind constants and shared assumptions."""
from __future__ import annotations

import copy
import importlib
import math
import sys
import tomllib
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterator

from mind import config
from stranded_physics.entities.api import ScenarioFile

MINDS = ('quantum', 'classical', 'classical_mixture')
DEFAULTS = {name: copy.deepcopy(value) for name, value in vars(config).items()
            if name.isupper() and name not in ('ETA', 'ACTIONS')}


def normalize(name: str, value: object) -> object:
    default = DEFAULTS[name]
    if isinstance(default, dict):
        return {key: tuple(gate) for key, gate in value.items()}
    if isinstance(default, set):
        return set(value)
    if isinstance(default, tuple):
        return tuple(value)
    return value


def load_settings(path: Path | None = None) -> dict:
    settings = tomllib.loads(path.read_text(encoding='utf-8')) if path else {}
    for section, values in settings.items():
        if section not in (*MINDS, 'shared') or not isinstance(values, dict):
            raise ValueError(f'Unknown settings section: {section}')
        for name, value in values.items():
            if section != 'shared':
                if name not in DEFAULTS:
                    raise ValueError(f'{section}: setting {name} is forbidden or unknown (ETA is fixed)')
                normalize(name, value)
            elif name == 'lifebelt':
                if not isinstance(value, bool):
                    raise ValueError('lifebelt must be true or false')
            elif name in ('reach_minutes_scale', 'boat_crew_share'):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f'{name} must be finite and nonnegative')
                if name == 'boat_crew_share' and value > 1:
                    raise ValueError('boat_crew_share must be at most 1')
            else:
                raise ValueError(f'Unknown shared setting: {name}')
    return settings


def nondefault(values: dict) -> bool:
    return any(normalize(name, value) != DEFAULTS[name] for name, value in values.items())


@contextmanager
def mind_settings(values: dict) -> Iterator[None]:
    importlib.import_module('mind.quantum_mind')
    changes = []
    try:
        for module in list(sys.modules.values()):
            if module is None:
                continue
            for name, value in values.items():
                if hasattr(module, name) and getattr(module, name) is getattr(config, name):
                    changes.append((module, name, getattr(module, name)))
        for module, name, _ in changes:
            setattr(module, name, copy.deepcopy(normalize(name, values[name])))
        yield
    finally:
        for module, name, original in reversed(changes):
            setattr(module, name, original)


def scenario_settings(scenario: ScenarioFile, mind: str, shared: dict) -> ScenarioFile:
    entities = []
    for entity in scenario.entities:
        if entity.kind == 'passengers':
            values = dict(entity.settings)
            values['reach_minutes'] *= shared.get('reach_minutes_scale', 1)
            if values['boat_crew'] != 1 and 'boat_crew_share' in shared:
                values['boat_crew'] = shared['boat_crew_share']
            entity = replace(entity, mind=mind, settings=values)
        entities.append(entity)
    return replace(scenario, entities=tuple(entities))

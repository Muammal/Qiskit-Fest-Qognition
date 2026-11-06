"""Run calibration comparisons, or an explicitly numbered holdout checkpoint."""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from contracts import ACTIONS
from benchmark.settings import MINDS, load_settings, mind_settings, nondefault, scenario_settings
from benchmark.tuning import check_budget
from stranded_physics.entities.api import load_scenario
from stranded_physics.entities.build import to_spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime import ship

ROOT = Path(__file__).resolve().parent
SEED = 1


def check_checkpoint(number: int, path: Path) -> None:
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    headings = re.findall(r'^## Checkpoint[^\r\n]*', text, re.MULTILINE)
    if number not in (1, 2, 3) or any(re.match(rf'^## Checkpoint {number}(?:\s|$)', h) for h in headings) or len(headings) >= 3:
        raise ValueError('Checkpoint must be unused, numbered 1, 2 or 3, with fewer than three recorded checkpoints')


def perfect_decide(state: dict) -> dict:
    return {'action': 'hide', 'probs': {a: float(a == 'hide') for a in ACTIONS}, 'reason': 'Always head for boats'}


@contextmanager
def runtime_settings(shared: dict, bound: str | None, seed: int) -> Iterator[None]:
    original = ship.ShipSimulation
    class Configured(original):
        def __init__(self, pack, passenger, index, *args, **kwargs):
            if bound == 'random':
                rng = np.random.default_rng([seed, index])
                def decide(state):
                    return {'action': str(rng.choice(ACTIONS)), 'probs': {a: 1 / len(ACTIONS) for a in ACTIONS}, 'reason': 'Uniform random action'}
                kwargs['decide_fn'] = decide
            super().__init__(pack, passenger, index, *args, **kwargs)
            self.lifebelt = shared.get('lifebelt', True)
    saved = random.getstate()
    try:
        random.seed(seed)
        ship.ShipSimulation = Configured
        yield
    finally:
        ship.ShipSimulation = original
        random.setstate(saved)


def run_event(path: Path, mind: str, settings: dict, bound: str | None = None) -> dict[str, float]:
    shared = settings.get('shared', {})
    scenario = scenario_settings(load_scenario(path), mind, shared)
    with mind_settings({} if bound else settings.get(mind, {})):
        pack = build_pack(to_spec(scenario, SEED), SEED)
        with runtime_settings(shared, bound, SEED):
            people = ship.play_ship(pack, scenario, decide_fn=perfect_decide if bound == 'perfect' else None)
        result = ship.summary(people)
        crew = [p for p in people if p.passenger.cohort.startswith('crew') or p.passenger.cohort in ('deck_crew', 'engineering_crew', 'victualling_crew')]
        if crew:
            result['crew'] = ship.summary(crew)['all']
        return result


def scenario_path(event: str) -> Path:
    if event == 'titanic_1912':
        return ROOT.parent / 'stranded_physics/scenario_cards/titanic_1912.toml'
    return ROOT / 'scenarios' / f'{event}.toml'


def evaluate(minds: list[str], settings: dict, checkpoint: bool = False) -> dict:
    with (ROOT / 'targets.csv').open(encoding='utf-8', newline='') as handle:
        targets = [r for r in csv.DictReader(handle) if (checkpoint or r['split'] == 'calibration')
                   and (r['status'] == 'runnable' or scenario_path(r['event']).exists())]
    results = {}
    labels = [*minds, 'perfect', 'random']
    for event in dict.fromkeys(r['event'] for r in targets):
        results[event] = {label: run_event(scenario_path(event), minds[0] if label in ('perfect', 'random') else label,
                                         settings, label if label in ('perfect', 'random') else None) for label in labels}
    rows = []
    for target in targets:
        if target['measure'] != 'saved_share':
            raise ValueError(f"Unsupported measure: {target['measure']}")
        group = 'all' if target['group'].startswith('all') else target['group']
        model = {label: results[target['event']][label][group] for label in labels}
        observed = float(target['observed'])
        rows.append({**{k: target[k] for k in ('event', 'group', 'measure', 'split')}, 'observed': observed,
                     'model': model, 'error': {k: abs(v - observed) for k, v in model.items()}})
    scores = {split: {label: sum(r['error'][label] for r in rows if r['split'] == split) /
                     sum(r['split'] == split for r in rows) for label in labels}
              for split in ('calibration', 'holdout') if any(r['split'] == split for r in rows)}
    return {'minds': minds, 'settings': settings, 'rows': rows, 'scores': scores}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minds', default=','.join(MINDS))
    for name in ('settings', 'out', 'log', 'checkpoint-file'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--checkpoint', type=int)
    args = parser.parse_args(argv)
    try:
        if args.checkpoint is not None:
            if args.checkpoint_file is None:
                raise ValueError('--checkpoint requires --checkpoint-file')
            check_checkpoint(args.checkpoint, args.checkpoint_file)
        minds = args.minds.split(',')
        if not minds or len(set(minds)) != len(minds) or any(m not in MINDS for m in minds):
            raise ValueError(f'Choose distinct minds from {MINDS}')
        settings = load_settings(args.settings)
        tuned = [m for m in minds if nondefault(settings.get(m, {}))]
        if args.log:
            log = args.log.read_text(encoding='utf-8') if args.log.exists() else ''
            for mind in tuned:
                check_budget(log, mind)
        result = evaluate(minds, settings, args.checkpoint is not None)
        encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n'
        if args.out:
            args.out.write_text(encoded, encoding='utf-8')
        if args.checkpoint is not None:
            with args.checkpoint_file.open('a', encoding='utf-8') as handle:
                handle.write(f'\n## Checkpoint {args.checkpoint}\n\n```json\n{encoded}```\n')
        if args.log:
            with args.log.open('a', encoding='utf-8') as handle:
                for mind in tuned:
                    handle.write(f'- run mind={mind} settings={json.dumps(settings[mind], sort_keys=True)} calibration_error={result["scores"]["calibration"][mind]}\n')
        print('split         mind                 mean absolute error')
        for split, scores in result['scores'].items():
            for mind, score in scores.items():
                print(f'{split:13} {mind:20} {score:.6f}')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())

from dataclasses import replace
import json
import numpy as np
import pytest
from benchmark import run
from benchmark.settings import load_settings, mind_settings, scenario_settings
from benchmark.tuning import count_runs, check_budget
from mind import config, quantum_mind
from stranded_physics.entities.api import load_scenario
from stranded_physics.entities.build import to_spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.ship import play_ship, summary

@pytest.mark.parametrize('number,text', [(0,''),(4,''),(1,'## Checkpoint 1\n'),(2,'## Checkpoint 1\n## Checkpoint 2\n## Checkpoint 3\n')])
def test_checkpoint_refusal(tmp_path, monkeypatch, number, text):
    path = tmp_path / 'checkpoints.md'
    path.write_text(text)
    monkeypatch.setattr(run, 'evaluate', lambda *a: pytest.fail('simulation began'))
    with pytest.raises(SystemExit) as error:
        run.main(['--checkpoint',str(number),'--checkpoint-file',str(path)])
    assert error.value.code == 2
    assert path.read_text() == text

def test_budget():
    line = '- run mind=quantum settings={} calibration_error=0.2\n'
    assert count_runs(line * 19 + '- run mind=classical settings={}\n', 'quantum') == 19
    assert count_runs('prefix ' + line, 'quantum') == 0
    check_budget(line * 19, 'quantum')
    with pytest.raises(ValueError):
        check_budget(line * 20, 'quantum')
    assert count_runs('- run mind=quantum_extra settings={}\n', 'quantum') == 0


def test_runner_budget_refuses_before_simulation(tmp_path, monkeypatch):
    settings = tmp_path / 'settings.toml'
    settings.write_text('[quantum]\nSTRESS_FLOOR = 0.25\n')
    log = tmp_path / 'runs.md'
    text = '- run mind=quantum settings={} calibration_error=0.2\n' * 20
    log.write_text(text)
    monkeypatch.setattr(run, 'evaluate', lambda *a: pytest.fail('simulation began'))
    with pytest.raises(SystemExit) as error:
        run.main(['--settings', str(settings), '--log', str(log)])
    assert error.value.code == 2
    assert log.read_text() == text


def test_cli_output_and_checkpoint(tmp_path, monkeypatch):
    result = {'minds': ['classical'], 'settings': {}, 'rows': [],
              'scores': {'calibration': {'classical': 0.2}}}
    calls = []
    def fake(minds, settings, checkpoint):
        calls.append(checkpoint)
        return result
    monkeypatch.setattr(run, 'evaluate', fake)
    output = tmp_path / 'result.json'
    args = ['--minds', 'classical', '--out', str(output)]
    assert run.main(args) == 0
    first = output.read_bytes()
    assert run.main(args) == 0
    assert output.read_bytes() == first
    assert json.loads(first) == result
    checkpoint = tmp_path / 'checkpoint.md'
    assert run.main(args + ['--checkpoint', '1', '--checkpoint-file', str(checkpoint)]) == 0
    assert '\n## Checkpoint 1\n' in checkpoint.read_text()
    assert calls == [False, False, True]

def test_eta_and_unknown_refused(tmp_path):
    for setting in ('ETA', 'BOGUS'):
        path = tmp_path / 'settings.toml'
        path.write_text(f'[quantum]\n{setting} = 0.1\n')
        with pytest.raises(ValueError, match=setting):
            load_settings(path)

def test_restore_even_after_failure():
    before = config.DECISION_RULE
    with pytest.raises(RuntimeError):
        with mind_settings({'DECISION_RULE': 'sample'}):
            assert config.DECISION_RULE == quantum_mind.DECISION_RULE == 'sample'
            raise RuntimeError()
    assert config.DECISION_RULE == quantum_mind.DECISION_RULE == before

def small_scenario():
    scenario = load_scenario(run.scenario_path('titanic_1912'))
    entities = tuple(replace(e, settings={**e.settings, 'men': 1, 'women': 1, 'children': 1})
                     if e.kind == 'passengers' else e for e in scenario.entities)
    return replace(scenario, hours=1, entities=entities)

@pytest.mark.parametrize('mind', ['quantum','classical','classical_mixture'])
def test_defaults_match_plain_run(mind):
    scenario = scenario_settings(small_scenario(), mind, {})
    pack = build_pack(to_spec(scenario, 1), 1)
    plain = play_ship(pack, scenario)
    with mind_settings({}), run.runtime_settings({}, None, 1):
        wrapped = play_ship(pack, scenario)
    assert summary(plain) == summary(wrapped)
    assert [p.steps for p in plain] == [p.steps for p in wrapped]

@pytest.mark.parametrize('event,minutes',[('lusitania_1915',18),('empress_of_ireland_1914',14)])
def test_sinking_time(event, minutes):
    scenario = load_scenario(run.scenario_path(event))
    pack = build_pack(to_spec(scenario, 1), 1)
    impact = next(e.settings['impact_minutes'] for e in scenario.entities if e.kind == 'breach')
    sunk = np.flatnonzero(pack.series('ship.afloat') == 0)
    assert len(sunk)
    assert abs(sunk[0] * scenario.step_s / 60 - impact - minutes) <= scenario.step_s / 60
    assert minutes * 60 / scenario.step_s >= 10

def test_calibration_filter(monkeypatch):
    events = []
    def fake(path, mind, settings, bound=None):
        events.append(path.stem)
        return {k: .5 for k in ('all','adult_male','adult_female','child','first_class','second_class','third_class','crew')}
    monkeypatch.setattr(run, 'run_event', fake)
    result = run.evaluate(['classical'], {})
    assert set(events) == {'titanic_1912'}
    assert 'holdout' not in json.dumps(result)
    assert len(result['rows']) == 8

def test_shared_settings():
    scenario = small_scenario()
    changed = scenario_settings(scenario, 'classical', {'reach_minutes_scale': 2, 'boat_crew_share': .3})
    for original, entity in zip(scenario.entities, changed.entities):
        if entity.kind == 'passengers':
            assert entity.settings['reach_minutes'] == original.settings['reach_minutes'] * 2
            assert entity.settings['boat_crew'] == (1 if original.settings['boat_crew'] == 1 else .3)

def test_settings_restored_after_run(monkeypatch):
    scenario = small_scenario()
    monkeypatch.setattr(run, 'load_scenario', lambda path: scenario)
    original = config.STRESS_FLOOR
    from mind import decoherence
    result = run.run_event(run.scenario_path('titanic_1912'), 'quantum', {'quantum': {'STRESS_FLOOR': .25}})
    assert 0 <= result['all'] <= 1
    assert config.STRESS_FLOOR == decoherence.STRESS_FLOOR == original


def test_bound_decisions_are_valid_and_reproducible(monkeypatch):
    import contracts
    from stranded_physics.runtime import ship
    contracts.validate_decision(run.perfect_decide({}))
    assert sum(run.perfect_decide({})['probs'].values()) == 1
    scenario = scenario_settings(small_scenario(), 'classical', {})
    pack = build_pack(to_spec(scenario, 1), 1)
    def actions():
        with run.runtime_settings({'lifebelt': False}, 'random', 1):
            people = ship.play_ship(pack, scenario)
        assert all(not person.lifebelt for person in people)
        return [[s['action'] for s in p.steps] for p in people]
    assert actions() == actions()

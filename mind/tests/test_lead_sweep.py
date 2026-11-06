"""The lead-time sweep and sensitivity helpers. Experiment results themselves are in docs/results/."""

import math

import numpy as np
import pytest

import mind.experiments.lead_time_sweep as sweep
import mind.experiments.sensitivity as sensitivity
from mind.config import ETA


def test_a_person_depends_only_on_seed_and_replicate():
    assert sweep.person(3, 7) == sweep.person(3, 7)
    assert sweep.person(3, 7) != sweep.person(3, 8)
    draws = [sweep.person(s, r) for s in range(40) for r in range(10)]
    assert all(-1 <= eta <= 0 for _, eta in draws)
    assert np.mean([eta for _, eta in draws]) == pytest.approx(ETA, abs=0.03)
    assert np.mean([offset for offset, _ in draws]) == pytest.approx(0, abs=0.03)


def test_start_tiles_lie_on_the_valley_every_flow_uses():
    from engine.world import MAP_SEED, IslandWorld

    world = IslandWorld(seed=MAP_SEED, scenario="volcano")
    for distance, tile in sweep.start_tiles().items():
        assert tile in world.valleys[0]
        assert math.dist(tile, world.vent) == pytest.approx(distance, abs=0.6)


def test_run_once_is_repeatable_and_paired_on_the_world():
    start = sweep.start_tiles()[6.4]
    assert sweep.run_once(1, 2, "quantum", 4, start) == sweep.run_once(1, 2, "quantum", 4, start)


def test_every_arm_uses_the_sample_rule():
    from engine.agent import SurvivalAgent

    state = SurvivalAgent().get_state()
    for arm in sweep.ARMS:
        assert sweep.make_decider(arm, 0.0, ETA)(state)["quantum"]["decision_rule"] == "sample"


def test_trait_stress_reaches_lambda_in_the_quantum_arm():
    from engine.agent import SurvivalAgent

    state = SurvivalAgent().get_state()
    state["stress"] = 0.5
    calm = sweep.make_decider("quantum", -0.2, ETA)(state)["quantum"]["lam"]
    tense = sweep.make_decider("quantum", 0.2, ETA)(state)["quantum"]["lam"]
    assert calm < tense


def test_holm_adjustment():
    assert sweep.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_bootstrap_interval_covers_the_mean():
    rng = np.random.default_rng(1)
    low, high = sweep.bootstrap_ci([0.1, 0.2, 0.3, 0.4], rng)
    assert low < 0.25 < high


def test_sign_flip_test_flags_a_clear_effect_and_not_a_null():
    rng = np.random.default_rng(2)
    assert sweep.bootstrap_p([0.2] * 30, rng) < 0.01
    assert sweep.bootstrap_p([0.0] * 30, rng) == 1.0


def test_sensitivity_never_varies_eta():
    assert "ETA" not in sensitivity.GRID
    with pytest.raises(KeyError):
        sensitivity.apply_override("ETA", 0.0)


def test_sensitivity_defaults_are_the_config_values():
    from mind import config

    for name in ("CF_SAFE_SAFETY", "CF_DANGER_SAFETY", "STRESS_FLOOR", "STRESS_SPAN"):
        assert sensitivity.DEFAULTS[name] == getattr(config, name)
        assert getattr(config, name) in sensitivity.GRID[name]


def test_sensitivity_scales_avoid_pi_over_two():
    from mind.config import EVENT_GATES

    for scale in sensitivity.GRID["angle_scale"]:
        for _axis, angle in EVENT_GATES.values():
            assert abs(abs(angle * scale) - math.pi / 2) > 1e-6


def test_order_gap_at_defaults_matches_the_paper():
    assert sensitivity.paper_order_gap() == pytest.approx(0.140, abs=5e-4)


def test_sensitivity_verdicts_flag_a_sign_change():
    rows = [
        dict(constant=name, value=1, is_default=True, order_gap=0.14, delay=0.5, delay_se=0.1, survival_quantum=0.99, survival_mixture=0.99)
        for name in sensitivity.GRID
    ]
    rows.append(dict(constant="angle_scale", value=2, is_default=False, order_gap=-0.1, delay=0.5, delay_se=0.1, survival_quantum=0.99, survival_mixture=0.99))
    verdict = sensitivity.verdicts(rows)
    assert verdict["angle_scale"]["order_gap"] is False and verdict["STRESS_SPAN"]["order_gap"] is True

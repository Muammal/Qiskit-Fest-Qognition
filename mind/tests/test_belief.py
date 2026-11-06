"""Stage 2: belief preparation, event gates and collapse.

In this stage lam is always 0; dephasing is added to run_events in Stage 3.
"""

import numpy as np
import pytest

from mind.belief import EVENT_GATES, apply_event, prepare_belief, run_events
from mind.model import bloch_vector

INITIAL_AGENT_SAFETY = 0.85  # engine/agent.py Agent.needs default


def test_prepare_belief_p_danger_is_one_minus_safety():
    for safety, expected_p_danger in [(0.85, 0.15), (0.6, 0.4), (0.3, 0.7)]:
        rho = prepare_belief(safety)
        _x, _y, z = bloch_vector(rho)
        p_danger = (1 - z) / 2
        assert p_danger == pytest.approx(expected_p_danger, abs=1e-9)


def test_prepare_belief_clamps_p_danger():
    _x, _y, z_low_safety = bloch_vector(prepare_belief(-0.5))  # 1-safety=1.5 -> clamp 0.98
    assert (1 - z_low_safety) / 2 == pytest.approx(0.98, abs=1e-9)

    _x, _y, z_high_safety = bloch_vector(prepare_belief(1.5))  # 1-safety=-0.5 -> clamp 0.02
    assert (1 - z_high_safety) / 2 == pytest.approx(0.02, abs=1e-9)


def test_ry_moves_z_into_x_rx_leaves_x_unchanged():
    safe = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)  # pure |0>, x=0, z=1

    after_ry = apply_event(safe, "tremor")  # ry(pi/3)
    x1, y1, z1 = bloch_vector(after_ry)
    assert y1 == pytest.approx(0.0, abs=1e-12)
    assert x1 == pytest.approx(np.sin(np.pi / 3), abs=1e-9)
    assert z1 == pytest.approx(np.cos(np.pi / 3), abs=1e-9)

    after_rx = apply_event(after_ry, "injury")  # rx(2*pi/3), rotates about x
    x2, _y2, _z2 = bloch_vector(after_rx)
    assert x2 == pytest.approx(x1, abs=1e-9)


def test_collapse_on_eruption_is_idempotent_and_certain():
    rho = prepare_belief(INITIAL_AGENT_SAFETY)
    once = apply_event(rho, "eruption")
    x, y, z = bloch_vector(once)
    assert x == pytest.approx(0.0, abs=1e-12)
    assert y == pytest.approx(0.0, abs=1e-12)
    assert (1 - z) / 2 == pytest.approx(1.0, abs=1e-9)

    twice = apply_event(once, "ash_fall")
    assert np.allclose(once, twice, atol=1e-12)


def test_order_noncommutation_tremor_gas_plume():
    rho = prepare_belief(INITIAL_AGENT_SAFETY)
    tremor_then_gas = run_events(rho, ["tremor", "gas_plume"], lam=0)
    gas_then_tremor = run_events(rho, ["gas_plume", "tremor"], lam=0)
    assert not np.allclose(tremor_then_gas, gas_then_tremor, atol=1e-6)


def test_no_event_angle_is_plus_or_minus_half_pi():
    for event, (_axis, angle) in EVENT_GATES.items():
        assert abs(abs(angle) - np.pi / 2) > 1e-9, f"{event} angle is +-pi/2"

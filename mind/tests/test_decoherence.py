"""Stage 3: stress as dephasing (TECH_A_BUILD_PLAN.md Section 4.5).

gamma = 1 - (1-lam)**2 is the trap: Aer's phase_damping_error(gamma) scales
coherence by sqrt(1-gamma), not (1-gamma). With this gamma, sqrt(1-gamma)
= 1-lam exactly, so lam is a per-slot linear coherence-decay rate.
"""
import numpy as np
import pytest
from qiskit.quantum_info import DensityMatrix, Kraus
from qiskit_aer.noise import phase_damping_error

from mind.belief import apply_event, prepare_belief, run_events
from mind.decoherence import apply_phase_damping, decoherence_strength
from mind.model import bloch_vector


def test_gamma_mapping_matches_aer_phase_damping_error():
    plus = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)

    aer_kraus = Kraus(phase_damping_error(0.36))
    aer_out = DensityMatrix(plus).evolve(aer_kraus).data
    assert aer_out[0, 1] == pytest.approx(0.4, abs=1e-9)

    lam = 0.2  # gamma = 1 - (1-0.2)**2 = 0.36
    ours = apply_phase_damping(plus, lam)
    assert ours[0, 1] == pytest.approx(0.4, abs=1e-9)
    assert np.allclose(ours, aer_out, atol=1e-9)

    for lam in (0.0, 0.2, 0.5, 0.929, 1.0):
        out = apply_phase_damping(plus, lam)
        assert out[0, 1].real == pytest.approx(0.5 * (1 - lam), abs=1e-9)


def test_x_monotone_non_increasing_in_lambda_tremor_then_gas_plume():
    rho0 = prepare_belief(0.85)
    lams = np.linspace(0.0, 1.0, 21)
    abs_x = []
    for lam in lams:
        rho = run_events(rho0, ["tremor", "gas_plume"], lam)
        x, _y, _z = bloch_vector(rho)
        abs_x.append(abs(x))

    diffs = np.diff(abs_x)
    assert np.all(diffs <= 1e-9)


def test_classical_limit_order_gap_vanishes_at_full_dephasing():
    rho0 = prepare_belief(0.85)
    qS, qD, eta = 0.69, 0.59, -0.7853897988344999
    from mind.model import p_protect_closed_form

    # A prefix event before the swapped pair, matching how the real order
    # gap (Section 4.7) always swaps the *last* two of a longer history.
    prefix = ["storm"]
    pairs = [
        ["tremor", "gas_plume"],
        ["injury", "cold_night"],
        ["gas_plume", "injury"],
    ]
    for pair in pairs:
        rho_a = run_events(rho0, prefix + pair, lam=1.0)
        rho_b = run_events(rho0, prefix + pair[::-1], lam=1.0)
        xa, _ya, za = bloch_vector(rho_a)
        xb, _yb, zb = bloch_vector(rho_b)

        assert abs(xa) < 1e-9
        assert abs(xb) < 1e-9

        pa, pb = (1 - za) / 2, (1 - zb) / 2
        P_a = p_protect_closed_form(pa, xa, qS, qD, eta)
        P_b = p_protect_closed_form(pb, xb, qS, qD, eta)
        assert abs(P_a - P_b) < 1e-9

        classical_a = (1 - pa) * qS + pa * qD
        assert P_a == pytest.approx(classical_a, abs=1e-9)


def test_stress_mapping():
    assert decoherence_strength(0.15) == pytest.approx(0.0, abs=1e-9)
    assert decoherence_strength(0.85) == pytest.approx(0.9285714285714285, abs=1e-9)
    assert decoherence_strength(1.0) == pytest.approx(1.0, abs=1e-9)

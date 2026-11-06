"""Stage 6: gate-level circuits and fake-backend noise runs.

The fake-backend/SamplerV2 tests are real Aer runs (not mocked) and take a
few seconds each; marked slow. Run everything with `pytest -q mind/tests`;
skip the slow ones with `pytest -q mind/tests -m "not slow"`.
"""

import pytest
from qiskit import transpile

from mind.belief import prepare_belief, run_events
from mind.circuits import build_coherence_probe_circuit, build_decision_circuit
from mind.model import bloch_vector, p_protect_closed_form

Q_S, Q_D, ETA = 0.69, 0.59, -0.7853897988344999


def test_collapse_events_raise_not_a_gate():
    with pytest.raises(ValueError):
        build_decision_circuit(0.85, ["eruption"], Q_S, Q_D, ETA)


def test_decision_circuit_statevector_matches_closed_form():
    from qiskit.quantum_info import Statevector

    for safety, events in [(0.85, ["tremor", "gas_plume"]), (0.5, [])]:
        qc = build_decision_circuit(safety, events, Q_S, Q_D, ETA)
        qc.remove_final_measurements()
        p_circuit = Statevector(qc).probabilities([1])[1]

        rho = run_events(prepare_belief(safety), events, lam=0.0)
        x, _y, z = bloch_vector(rho)
        p = (1 - z) / 2
        closed = p_protect_closed_form(p, x, Q_S, Q_D, ETA)
        assert p_circuit == pytest.approx(closed, abs=1e-9)


@pytest.mark.slow
def test_transpiled_gate_counts_on_fake_torino():
    FakeTorino = pytest.importorskip("qiskit_ibm_runtime.fake_provider").FakeTorino
    backend = FakeTorino()
    qc = build_decision_circuit(0.85, ["tremor", "gas_plume"], Q_S, Q_D, ETA)
    tqc = transpile(qc, backend=backend, optimization_level=3, seed_transpiler=42)
    counts = tqc.count_ops()

    assert counts["cz"] == 2
    assert 9 <= counts["sx"] <= 13
    assert 8 <= counts["rz"] <= 12


@pytest.mark.slow
def test_fake_backend_estimates_within_4_standard_errors():
    pytest.importorskip("qiskit_ibm_runtime")
    from mind.experiments.run_fake_backend import run_fake_backend_experiment

    summary, _circuits = run_fake_backend_experiment(shots=4000)
    for name, row in summary["results"].items():
        assert row["within_4se"], f"{name}: diff/SE={row['diff_over_se']:.2f}"


@pytest.mark.slow
def test_delay_requires_scheduled_transpile_or_is_a_noop_in_this_backend():
    """Documents the actual behavior of this qiskit-aer version (0.18.2):
    an explicit qc.delay(...) with a fixed duration survives transpile and
    is honored by AerSimulator.from_backend's thermal-relaxation noise
    whether or not scheduling_method='alap' is passed. The plan's pitfall
    #7 ("unscheduled delays are ignored") did not reproduce here; we still
    pass scheduling_method='alap' everywhere (mind/experiments/) since the
    plan's guidance is correct in general (multi-qubit circuits needing
    idle-padding alignment) and costs nothing in this simpler circuit.
    """
    FakeTorino = pytest.importorskip("qiskit_ibm_runtime.fake_provider").FakeTorino
    backend = FakeTorino()
    from qiskit_aer.primitives import SamplerV2

    sampler = SamplerV2.from_backend(backend, seed=7)
    probe = build_coherence_probe_circuit(200)

    tqc_unscheduled = transpile(probe, backend=backend, optimization_level=1, seed_transpiler=7, initial_layout=[10, 11])
    tqc_scheduled = transpile(probe, backend=backend, optimization_level=1, seed_transpiler=7, initial_layout=[10, 11], scheduling_method="alap")

    shots = 4000
    p0_unscheduled = sampler.run([tqc_unscheduled], shots=shots).result()[0].data.c.get_counts().get("0", 0) / shots
    p0_scheduled = sampler.run([tqc_scheduled], shots=shots).result()[0].data.c.get_counts().get("0", 0) / shots

    assert abs(p0_unscheduled - p0_scheduled) < 0.05
    assert p0_scheduled < 0.9  # delay noise was applied at all (not a no-op)

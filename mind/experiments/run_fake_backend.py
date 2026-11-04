"""Stage 6: run decision circuits on AerSimulator.from_backend(FakeTorino())
and compare against the exact closed-form values. Offline only - this
never runs during gameplay (D7); see 06-circuits-and-hardware.md.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import qiskit
from qiskit import transpile, qpy
from qiskit_aer.primitives import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino

from mind.belief import prepare_belief, run_events
from mind.circuits import build_decision_circuit
from mind.model import bloch_vector, p_protect_closed_form

Q_S, Q_D, ETA = 0.69, 0.59, -0.7853897988344999

CASES = {
    "tremor_then_gas_plume": dict(safety=0.85, events=["tremor", "gas_plume"]),
    "gas_plume_then_tremor": dict(safety=0.85, events=["gas_plume", "tremor"]),
    "tversky_shafir_p0.5": dict(safety=0.5, events=[]),
}


def exact_p_protect(safety, events):
    rho = run_events(prepare_belief(safety), events, lam=0.0)
    x, _y, z = bloch_vector(rho)
    p = (1 - z) / 2
    return p_protect_closed_form(p, x, Q_S, Q_D, ETA)


def run_fake_backend_experiment(shots=4000, seed_transpiler=42, sampler_seed=42):
    backend = FakeTorino()
    sampler = SamplerV2.from_backend(backend, seed=sampler_seed)

    results = {}
    transpiled_circuits = {}
    for name, cfg in CASES.items():
        qc = build_decision_circuit(cfg["safety"], cfg["events"], Q_S, Q_D, ETA)
        tqc = transpile(qc, backend=backend, optimization_level=3, seed_transpiler=seed_transpiler)
        transpiled_circuits[name] = tqc

        job = sampler.run([tqc], shots=shots).result()
        counts = job[0].data.c.get_counts()
        p_sim = counts.get("1", 0) / shots

        exact = float(exact_p_protect(cfg["safety"], cfg["events"]))
        se = float(np.sqrt(exact * (1 - exact) / shots))
        diff = float(abs(p_sim - exact))

        results[name] = {
            "safety": cfg["safety"],
            "events": cfg["events"],
            "shots": shots,
            "p_sim": float(p_sim),
            "p_exact": exact,
            "standard_error": se,
            "abs_diff": diff,
            "diff_over_se": diff / se if se > 0 else None,
            "within_4se": bool(diff <= 4 * se),
        }

    ref_tqc = transpiled_circuits["tremor_then_gas_plume"]
    gate_counts = dict(ref_tqc.count_ops())

    summary = {
        "backend": backend.name,
        "calibration_source": "qiskit_ibm_runtime.fake_provider.FakeTorino snapshot",
        "qiskit_version": qiskit.__version__,
        "shots": shots,
        "seed_transpiler": seed_transpiler,
        "sampler_seed": sampler_seed,
        "date": datetime.now(timezone.utc).isoformat(),
        "q_safe": Q_S,
        "q_danger": Q_D,
        "eta": ETA,
        "transpiled_gate_counts_reference_circuit": gate_counts,
        "results": results,
    }
    return summary, transpiled_circuits


def main(out_dir="mind/results"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary, transpiled_circuits = run_fake_backend_experiment()

    with open(out / "fake_backend_run.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with open(out / "hardware_circuits.qpy", "wb") as f:
        qpy.dump(list(transpiled_circuits.values()), f)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

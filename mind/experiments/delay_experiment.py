"""Stage 6: delay experiment (D7, offline only - Tech B's hardware job).

Belief prepared at p=0.5 (x=1), idle for t, then U, then measure. A
separate Ramsey-style coherence probe isolates the T2 decay from the
decision-mixing unitary's own effect on P(protect).

Caveat: T1 relaxation pushes the belief toward |0>=safe as well as
destroying coherence, so this is not a pure T2 measurement in the full
decision circuit - only the coherence-probe circuit isolates T2 alone.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import qiskit
from qiskit import transpile
from qiskit_aer.primitives import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeTorino

from mind.circuits import build_coherence_probe_circuit, build_delay_circuit
from mind.model import p_protect_closed_form

Q_S, Q_D, ETA = 0.69, 0.59, -0.7853897988344999
DELAYS_US = [0, 20, 50, 100, 200]
PROBE_QUBIT = 10  # fake_torino qubit with T1=200.8us, T2=228.3us (snapshot)


def run_delay_experiment(shots=4000, seed_transpiler=7, sampler_seed=7, qubit=PROBE_QUBIT):
    backend = FakeTorino()
    sampler = SamplerV2.from_backend(backend, seed=sampler_seed)
    t1 = backend.qubit_properties(qubit).t1 * 1e6
    t2 = backend.qubit_properties(qubit).t2 * 1e6

    exact_no_delay = p_protect_closed_form(0.5, 1.0, Q_S, Q_D, ETA)

    rows = []
    for t_us in DELAYS_US:
        probe = build_coherence_probe_circuit(t_us)
        probe_t = transpile(probe, backend=backend, optimization_level=1,
                             seed_transpiler=seed_transpiler, initial_layout=[qubit, qubit + 1],
                             scheduling_method="alap")
        probe_job = sampler.run([probe_t], shots=shots).result()
        p0 = probe_job[0].data.c.get_counts().get("0", 0) / shots
        x_measured = 2 * p0 - 1
        theory = float(np.exp(-t_us / t2))

        decide = build_delay_circuit(t_us, Q_S, Q_D, ETA)
        decide_t = transpile(decide, backend=backend, optimization_level=1,
                              seed_transpiler=seed_transpiler, initial_layout=[qubit, qubit + 1],
                              scheduling_method="alap")
        decide_job = sampler.run([decide_t], shots=shots).result()
        p_protect = decide_job[0].data.c.get_counts().get("1", 0) / shots

        rows.append({
            "t_us": t_us,
            "coherence_x_measured": x_measured,
            "coherence_theory_exp_t_over_t2": theory,
            "coherence_ratio_measured_over_theory": x_measured / theory if theory > 0 else None,
            "p_protect_under_delay": p_protect,
        })

    summary = {
        "backend": backend.name,
        "calibration_source": "qiskit_ibm_runtime.fake_provider.FakeTorino snapshot",
        "qiskit_version": qiskit.__version__,
        "probe_qubit": qubit,
        "t1_us": t1,
        "t2_us": t2,
        "shots": shots,
        "seed_transpiler": seed_transpiler,
        "sampler_seed": sampler_seed,
        "date": datetime.now(timezone.utc).isoformat(),
        "p_protect_exact_no_delay": exact_no_delay,
        "caveat": "T1 relaxation also pushes the belief toward |0>=safe in the full "
                  "decision circuit; only the coherence-probe rows isolate T2 alone.",
        "rows": rows,
    }
    return summary


def main(out_dir="mind/results"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = run_delay_experiment()
    with open(out / "delay_experiment.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

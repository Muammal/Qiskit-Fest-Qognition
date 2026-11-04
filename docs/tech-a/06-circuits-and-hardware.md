# Circuits and hardware

## What it does

Every decision in the game runs on a fast numpy evaluation of the closed
form (Stage 1-4) — that's what makes 36-step simulations and 200-seed
batches practical. This stage builds the *actual gate-level circuit*
version of the same model, offline: a real `QuantumCircuit` with `ry`,
`rx` and a single two-qubit `UnitaryGate(U)`, transpiled for a real IBM
device's calibration snapshot (`FakeTorino`) and run through Qiskit Aer's
noise simulator. It exists to prove the fast path isn't hiding anything —
the circuit and the closed form agree to machine precision — and to
produce the artifacts (QPY circuits, a delay-vs-coherence sweep) Tech B
needs for an eventual real hardware job. Nothing in this stage runs during
gameplay, and nothing here has touched real IBM hardware (D7).

## The math

**Why the circuit only covers rotation-only histories.** `eruption` and
`ash_fall` are a projective collapse (Stage 2, D2) — `rho -> Pi rho Pi /
Tr(...)`. A collapse is not a unitary, so it has no gate representation; a
`QuantumCircuit` genuinely cannot express it. `build_decision_circuit`
raises `ValueError` if asked to, rather than silently approximating it
with some rotation. This is a real, stated limitation of the circuit
picture, not a bug: the closed-form/density-matrix path (Stages 1-4) is
the one that handles collapse, and is what actually runs in the game.

**Why `det(U)=+1` compiles to at most 2 CZ gates.** `U ∈ SO(4)` (Stage 1,
D-QR) can always be written, via the KAK (Cartan) decomposition, as
`U = (A1 ⊗ A2) · N(a,b,c) · (B1 ⊗ B2)`, where `A1,A2,B1,B2` are single-qubit
unitaries and `N(a,b,c)` is a "canonical" two-qubit interaction
parameterized by three angles. Vatan & Williams (2004) show that for a
*real orthogonal* `U` (which is exactly what an `SO(4)` deliberation
unitary is), the canonical interaction degenerates to something
realizable with **at most 2 CNOT-equivalent two-qubit gates**, versus the
3 needed for a general `SU(4)` unitary. `det(U)=+1` is precisely the
condition that keeps `U` inside the real-orthogonal subgroup where this
cheaper decomposition applies — one more reason the Stage 1 sign-fixing
(always landing on `det=+1`, never `-1`) matters beyond just bookkeeping.

**Shot statistics.** For a true probability `P` estimated by `N` shots,
the binomial standard error is `SE = sqrt(P(1-P)/N)`. A noisy hardware (or
fake-backend) estimate landing within about 4 SE of the exact value is
consistent with "the circuit implements the model plus realistic device
noise," not "the circuit is wrong."

**Delay physics.** Idling a qubit for time `t` under pure T2 dephasing
decays coherence as `e^(-t/T2)`. `FakeTorino`'s snapshot also includes
gate and readout error, so a *measured* coherence tracks
`e^(-t/T2) * (a constant below 1)` — the gap between "theoretical T2
decay" and "what you actually read out." **Caveat:** in the *full decision
circuit* (not the isolated coherence probe), T1 relaxation also pulls the
belief toward `|0>=safe` during the idle time, on top of the T2 dephasing
— so sweeping `t` in the decision circuit mixes two physical effects, and
only the dedicated coherence-probe circuit isolates T2 alone.

## The code

`mind/circuits.py`:
- `build_decision_circuit(safety, events, q_S, q_D, eta)` — `ry`
  preparation, each event's gate, `UnitaryGate(U)`, measure qubit 1.
  Raises `ValueError` on a collapse event.
- `build_coherence_probe_circuit(t_us)` — Ramsey-style: `|+>`, idle,
  rotate back, measure — isolates T2 decay alone.
- `build_delay_circuit(t_us, q_S, q_D, eta)` — the full decision pipeline
  (`p=0.5, x=1` preparation) under a scheduled idle, for the delay sweep.

`mind/experiments/run_fake_backend.py` — runs the three representative
circuits (`tremor_then_gas_plume`, `gas_plume_then_tremor`,
`tversky_shafir_p0.5`) on `AerSimulator`-backed `SamplerV2.from_backend`,
compares to the exact closed form, writes `mind/results/fake_backend_run.json`
and exports the transpiled circuits to `mind/results/hardware_circuits.qpy`
(for Tech B's hardware job) via `qiskit.qpy.dump`.

`mind/experiments/delay_experiment.py` — sweeps `t in {0,20,50,100,200}`
µs on `FakeTorino` qubit 10, both the coherence probe and the full
decision circuit, writes `mind/results/delay_experiment.json`.

## How we know it works

```
$ source .venv/bin/activate && python -m pytest -v mind/tests/test_circuits.py
test_collapse_events_raise_not_a_gate PASSED
test_decision_circuit_statevector_matches_closed_form PASSED
test_transpiled_gate_counts_on_fake_torino PASSED
test_fake_backend_estimates_within_4_standard_errors PASSED
test_delay_requires_scheduled_transpile_or_is_a_noop_in_this_backend PASSED
5 passed in 6.03s
```

**Transpiled gate counts** (`tremor_then_gas_plume`, `FakeTorino`,
`optimization_level=3`, `seed_transpiler=42`):
```
{"sx": 11, "rz": 10, "cz": 2, "measure": 1}
```
Exactly 2 CZ (plan: 2 CZ), 11 SX (plan: ~11), 10 RZ (plan: ~10).

**Fake-backend estimates vs exact**, from `mind/results/fake_backend_run.json`
(`shots=4000`, `seed_transpiler=42`, `sampler_seed=42`, `FakeTorino`,
qiskit 2.6.1):

| Case | p_sim | p_exact | SE | diff/SE | within 4 SE |
| --- | --- | --- | --- | --- | --- |
| tremor_then_gas_plume | 0.3748 | 0.3744 | 0.0077 | 0.04 | yes |
| gas_plume_then_tremor | 0.5670 | 0.5561 | 0.0079 | 1.38 | yes |
| tversky_shafir_p0.5 | 0.3753 | 0.3600 | 0.0076 | 2.01 | yes |

(plan prototype: "every estimate within 4 SE... the prototype's were
within 1.3"; here the max is 2.01, still comfortably under 4.)

**Delay experiment**, from `mind/results/delay_experiment.json`
(`FakeTorino` qubit 10, T1=200.80µs, T2=228.33µs, `shots=4000`):

| t (µs) | x measured | e^(-t/T2) | ratio |
| --- | --- | --- | --- |
| 0 | 0.9085 | 1.0000 | 0.909 |
| 20 | 0.8230 | 0.9161 | 0.898 |
| 50 | 0.7270 | 0.8033 | 0.905 |
| 100 | 0.5915 | 0.6453 | 0.917 |
| 200 | 0.3910 | 0.4165 | 0.939 |

Measured coherence tracks `e^(-t/T2)` scaled by a roughly constant
`~0.90-0.94` (plan: "about 0.91") - the gate-and-readout-error factor the
plan's reference number describes, reproduced here on a live
`FakeTorino` calibration snapshot with the exact same qiskit-aer version
(0.18.2) the plan's prototype used.

**Scheduling finding (differs from the plan's stated pitfall #7):** in
this qiskit/qiskit-aer version, an explicit `qc.delay(t, qubit, unit='us')`
with a fixed duration survived `transpile()` and was honored by
`AerSimulator.from_backend`'s thermal-relaxation noise whether or not
`scheduling_method='alap'` was passed (`test_delay_requires_scheduled_transpile_or_is_a_noop_in_this_backend`,
`|p0_unscheduled - p0_scheduled| < 0.05` at `t=200us`, and both show real
decay, not a no-op). We still pass `scheduling_method='alap'` everywhere
in `mind/experiments/`, since it is correct general practice (needed when
multiple qubits have asynchronous gate timing that must be aligned) and
costs nothing here — but we are not claiming the plan's exact failure
mode reproduces in this environment, since it didn't.

## Limits and honest claims

- This is the only stage that runs an actual `QuantumCircuit` through
  Qiskit Aer. It is offline, never called during gameplay, and never
  touches real IBM hardware - every "backend" here is `FakeTorino`, a
  calibration *snapshot*, not a live device.
- The circuit path covers rotation-only event histories only; any history
  containing `eruption`/`ash_fall` is handled by the closed-form path, not
  the circuit path, by design (not an oversight).
- "~0.91" and the SE comparisons are properties of *this specific*
  `FakeTorino` snapshot and qiskit-aer version; a different snapshot or a
  real device would give different numbers (the physics, not the exact
  constants, is the claim).
- `hardware_circuits.qpy` is handed to Tech B for a possible real hardware
  job; nothing in this repo runs it there, and no job ID exists yet.

## Questions a judge might ask

**Why does `det(U)=+1` matter for hardware?** It keeps `U` inside the
real-orthogonal subgroup of two-qubit unitaries, where the Vatan &
Williams (2004) decomposition needs only 2 CZ-equivalent gates instead of
the 3 a general two-qubit unitary would need — fewer two-qubit gates means
less accumulated hardware error on a real device.

**Why must delays be scheduled?** In general, Aer's noise model applies
thermal relaxation based on each qubit's actual idle duration, which the
transpiler normally only computes during scheduling (so that idle time on
*other* qubits waiting for a slower one is accounted for too). We found
this specific circuit's explicit, fixed-duration delay was honored even
without scheduling in this qiskit-aer version — but scheduling is still
the documented, correct practice for circuits where multiple qubits have
asynchronous gate timing, so we use it unconditionally.

**Did any of this run on real IBM hardware?** No. `FakeTorino` is a
calibration snapshot bundled with `qiskit-ibm-runtime`, run entirely
through Qiskit Aer's local simulator. The QPY export exists so Tech B
*can* run it on real hardware later; that job has not happened.

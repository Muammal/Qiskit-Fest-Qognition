# Tech A: the quantum mind

Index for everything Tech A built for the volcano-evacuation survival engine:
a real two-qubit quantum-probability model behind `quantum_decide`, a
classical control mind (`classical_mixture_decide`), and the documentation
and validation evidence needed to defend both at judging.

## Environment (verified, Stage 0)

Local venv at `.venv/` (not part of the team's shared environment; this repo
had no committed lockfile or venv, so Tech A pinned to the versions the
build plan's prototype numbers were measured against):

```
$ source .venv/bin/activate && python --version && python -c "import qiskit, qiskit_aer, qiskit_ibm_runtime; print('qiskit', qiskit.__version__); print('qiskit-aer', qiskit_aer.__version__); print('qiskit-ibm-runtime', qiskit_ibm_runtime.__version__)"
Python 3.12.12
qiskit 2.6.1
qiskit-aer 0.18.2
qiskit-ibm-runtime 0.51.0
```

These match the versions `TECH_A_BUILD_PLAN.md` Section 7 cites for its
prototype numbers, so the plan's expected figures should reproduce exactly.

## How to run the tests

```
# Tech A's own suite
source .venv/bin/activate
pytest -q mind/tests

# Full repo suite, before every commit
SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py mind/tests
```

Baseline (Stage 0, before any mind code existed):

```
$ SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py
31 passed in 6.96s
```

## What Tech A built

Filled in as each stage lands:

- `mind/model.py` — the deliberation unitary (Stage 1)
- `mind/belief.py` — belief preparation, event gates, collapse (Stage 2)
- `mind/quantum_mind.py`, `mind/config.py` — decoherence, decision rule, `quantum_decide` / `classical_mixture_decide` (Stages 3–4)
- `mind/circuits.py`, `mind/experiments/` — gate circuits, fake-backend runs, delay experiment (Stage 6)
- `mind/experiments/validate.py`, `mind/figures.py` — generate `07-validation-report.md` and `figures/` (Stage 7)
- `demo-pack/tech-a/` — three short explainers for Product E (Stage 8)

## Docs index

| File | Contents |
| --- | --- |
| `DECISIONS.md` | Decision log |
| `01-model-overview.md` | Two qubits, protect vs carry-on, data flow |
| `02-deliberation-unitary.md` | Construction of U, derivation of P(protect) |
| `03-events-and-order-effects.md` | Rotations, collapse, order effects |
| `04-stress-and-decoherence.md` | Phase damping, classical-limit proof |
| `05-decision-rule-and-reflexes.md` | argmax vs sampling, reflexes, action split |
| `06-circuits-and-hardware.md` | Gate circuits, transpile counts, noise, delay experiment |
| `07-validation-report.md` | Generated validation report and batch statistics |
| `08-integration-notes.md` | Stage 5 integration PR notes |

## Q&A

**Is the brain quantum?** No. The model's claim is that representing
ambiguous evidence as non-commuting rotations and combining beliefs with a
real interference term reproduces *patterns* seen in human judgment under
uncertainty (the Tversky & Shafir 1992 disjunction effect) — not that
neurons perform unitary evolution. See `02-deliberation-unitary.md` and
`03-events-and-order-effects.md`, "Limits and honest claims."

**Why Qiskit, if the in-game decision path is just numpy?** Because the
numpy closed form isn't trusted blind — it's checked against real
`QuantumCircuit`/`Statevector` execution to `1e-9` (Stage 1,
`test_gate_circuit_matches_closed_form`), and Stage 6 builds and runs the
actual gate-level circuits (2 CZ, ~11 SX, ~10 RZ after transpiling for a
real device calibration snapshot) on Qiskit Aer with a fake-IBM noise
model, landing within 2.01 standard errors of the exact values
(`06-circuits-and-hardware.md`). Qiskit is the verification tool and the
offline-experiment tool; numpy is the fast path that verification backs.

**Couldn't a classical model do this?** That's exactly what
`classical_mixture_decide` tests: it is the *same* pipeline, same `q_S`,
`q_D`, same prior split, with the interference term forced to exactly
zero (`lam=1`). Any measured difference between it and `quantum_decide` on
identical seeds is attributable to that one term and nothing else — in our
200-seed batch, 8.3% of compared decisions differ, and survival differs
significantly by McNemar's exact test (13 vs 3 discordant seeds, p=0.021)
(`07-validation-report.md`, Section 2).

**Isn't it just noise?** No — it's deterministic given the state (D3:
`argmax`, no sampling by default), and two identically-seeded runs produce
bit-identical action sequences (`test_determinism_seeded_run`). The
"quantum" and "classical" minds disagree in a structured, reproducible
way tied to one named mechanism (interference), not run-to-run randomness.

**Where does eta come from?** An exact solve against Tversky & Shafir
(1992)'s published disjunction-effect numbers (0.69 / 0.59 / 0.36) — one
equation, one unknown, not a fit to many data points. Transferring that
constant from a gambling-choice study to a volcano-evacuation scenario is
an assumption stated openly, not hidden (D6, `DECISIONS.md`).

**Why does a storm sometimes reassure?** Every ambiguous-sign rotation
can move the belief toward *or* away from danger, depending on the sign
of the belief's existing coherence (`x`) when it arrives — it is a fixed
geometric nudge, not a one-directional "this event is bad" rule. Real
example from this repo: starting from the initial agent state, three
`tremor` signs in a row leave `P(danger)=0.850`; a `storm` right after
that drops it to `P(danger)=0.366` — the same rotation that usually raises
alarm, here lowers it, because `x` had gone negative. This is a real,
reproducible property of the math (verified by running `mind/belief.py`
this session), not a scripted exception.

**What can't the model fit?** The Prisoner's Dilemma disjunction numbers
(cooperate-if-cooperate 0.97, cooperate-if-defect 0.84, cooperate-if-
unknown observed ~0.63). The model's minimum reachable value for that
`(q_S, q_D)` pair is bounded at 0.8357 — provably, by Cauchy-Schwarz on
the unitary's two columns, not by an implementation gap
(`test_prisoners_dilemma_bound_cannot_be_fit`,
`02-deliberation-unitary.md`). No unitary built this way can reach 0.63
for these conditionals; the model genuinely does not cover every
disjunction-effect dataset.

**Did it run on hardware?** No. Every run in this repo is either the
closed-form/numpy path (exact) or a Qiskit Aer simulation using a real
device *calibration snapshot* (`FakeTorino`) — never a live IBM job. The
transpiled circuits are exported to `mind/results/hardware_circuits.qpy`
for Tech B's possible future hardware run; no job ID exists yet (D7,
`06-circuits-and-hardware.md`).

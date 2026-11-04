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
- `mind/experiments/validate.py` — generates `07-validation-report.md` (Stage 7)

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

Filled in at Stage 9.

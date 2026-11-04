# Model overview

## What it does

`quantum_decide` replaces the stub two-qubit "mind" with a real model:
qubit 0 (belief: safe vs danger) carries the agent's uncertainty about
whether a threat is real, non-commuting rotations and collapses update it
as signs arrive, stress dephases it, and a deliberation unitary turns the
resulting belief into a probability of protecting (evacuating via `hide`)
versus carrying on with one of six other actions. `classical_mixture_decide`
is the same pipeline with the quantum interference switched off — the
control that makes every comparison in this project falsifiable.

## The math

See the per-stage docs for full derivations; this is the data flow that
connects them.

```
state (contracts.py)
  |
  |-- state["needs"]["safety"], state["stress"], state["recent_events"]
  |-- contracts.get_prior(state)                       -> prior
  |-- contracts.get_prior(cf_safe(state))["hide"]       -> q_S   (04.2)
  |-- contracts.get_prior(cf_danger(state))["hide"]     -> q_D   (04.2)
  v
prepare_belief(safety)                                  -> rho0  (02, 03)
  v
run_events(rho0, recent_events, lam)                     (03, 04)
  lam = decoherence_strength(stress)                      (04)
  v
bloch_vector(rho) -> (x, y, z); p = (1-z)/2
  v
build_U(q_S, q_D, eta); p_protect_closed_form(p, x, q_S, q_D, eta)  (02)
  -> P(protect), P(classical) = (1-p) q_S + p q_D
  v
decision_probs(P(protect), prior)                        -> probs[7 actions] (05)
  v
argmax(probs) -> rule_action                              (05, D3)
  v
reflex layer (thirst/warmth) -> action                    (05, D4)
  v
order-gap + decoherence text -> reason                    (05)
  v
{"action", "probs", "reason", "quantum": {...}}           -> validate_decision
```

**What is quantum, what is classical:**
- Quantum: the belief qubit's rotations/collapse (non-commuting -> order
  effects), the deliberation unitary `U` (real interference between
  amplitudes), phase damping (a named physical decoherence channel).
- Classical: `get_prior` (Tech B's stub), the 7-action probability split,
  `argmax`, the reflex layer. `classical_mixture_decide` proves the
  "quantum part" is exactly the `lam=1` -> `0` interference term and
  nothing else, by forcing it off and comparing.

## The code

| File | Contents |
| --- | --- |
| `mind/model.py` | `build_U`, `p_protect_closed_form`, `bloch_vector` (Stage 1) |
| `mind/belief.py` | `prepare_belief`, `apply_event`, `run_events` (Stage 2) |
| `mind/decoherence.py` | `decoherence_strength`, `apply_phase_damping` (Stage 3) |
| `mind/config.py` | every constant: `PROTECT`, `EVENT_GATES`, `ETA`, clamps, thresholds (Stage 4) |
| `mind/quantum_mind.py` | `decision_probs`, `quantum_decide`, `classical_mixture_decide` (Stage 4) |

## How we know it works

```
$ SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py mind/tests
67 passed in 7.26s
```

31 original repo tests (unchanged) + 36 Tech A tests (6 model, 6 belief,
4 decoherence, 15 quantum_mind, 5 circuits), including every one of the 7
pre-existing mind-related tests the plan (Section 2) requires to stay
green, run against `quantum_decide` via `monkeypatch`
(`mind/tests/test_quantum_mind.py::test_repo_compatibility`).

## Limits and honest claims

- This is a model of judgment *patterns* (order effects, an uncertainty
  dip, decoherence under stress) calibrated against a published human
  disjunction-effect study. It is not a claim that the agent's "brain" is
  physically quantum.
- Every number in this doc set comes from running this repo's own code
  this session (`mind/model.py`, `mind/belief.py`, `mind/decoherence.py`,
  `mind/quantum_mind.py`), not from the plan's prototype or from memory.
- Nothing here has run on IBM hardware; Stage 6 covers simulated-noise
  (`fake_torino`) circuit runs and an offline delay experiment only.

## Questions a judge might ask

See `02-deliberation-unitary.md`, `03-events-and-order-effects.md`,
`04-stress-and-decoherence.md` and `05-decision-rule-and-reflexes.md` for
the per-topic Q&A; `docs/tech-a/README.md`'s Q&A (Stage 9) covers the
project-level questions ("is the brain quantum", "why Qiskit", etc.).

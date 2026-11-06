# 2b: better controls

**Committed before any run.** Code: `mind/quantum_mind.py`, `engine/simulation.py`, `mind/experiments/lead_time_sweep.py`, `mind/experiments/arms_batch.py`.

## Question

A reviewer will ask whether a tuned classical delay gives the same hesitation. Separately: is the quantum arm's behaviour due to interference, or to coherent belief rotation?

## Arms

| Arm | Belief | P(protect) |
|---|---|---|
| `quantum` | Coherent, dephased by stress | With interference, at eta |
| `classical_no_interference` | Same as quantum | k forced to 0 |
| `classical_mixture` | lambda = 1 | Classical total |
| `markov_hesitation` | lambda = 1 | `(1 - h * 4p(1-p))` times the classical total, h fitted to `disjunction.csv` |
| `markov_hesitation_ts` | lambda = 1 | Same, with h = 0.4375, which hits Tversky & Shafir's 0.36. This is the row ETA was solved from, so it is the fair match for `quantum` |

`markov_hesitation` has one free parameter. h is the median of split-half fits on the 7 scored rows of `disjunction.csv`, and is scored on the held-out rows. No simulator result is used.

## Metrics

Two sets, all arms on paired seeds:

1. The sweep in [2a](2a_lead_time_sweep.md).
2. Default volcano, seeds 0 to 199, default `argmax` rule: survival, and paired evacuation delay against the mixture.

## What counts as a win

- **Tuned classical delay:** quantum differs from `markov_hesitation_ts` if the delay or primary survival difference has Holm-adjusted p < 0.05 at any lead. If not, the honest reading is that a one-parameter classical model gives the same hesitation here, and the simulator cannot tell them apart.
- **Interference against coherence:** same test, quantum against `classical_no_interference`.
- Either way, every arm is reported at every lead.

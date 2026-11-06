# 2d: time-aware decoherence

**Committed before any run.** Code: `mind/experiments/time_aware.py`.

## Question

`per_slot` dephasing applies the same lambda per decision whatever the step length: 2 h on the volcano, 5 min on the Titanic, 15 min at Pompeii and 1 min of decisions at Waterloo. What changes if dephasing follows elapsed time?

## Model

With `dephasing_mode="per_time"`, `lam_slot = 1 - exp(-dt / tau(stress))`, with `tau` chosen so that dt = 2 h gives the current `lam(stress)`. The default `per_slot` is untouched.

## Runs

Quantum mind, seed 42, default cue translation for Titanic, Pompeii and Waterloo; volcano seeds 0 to 199. Each in `per_slot` and `per_time`. Metric: saved or deaths, and for the volcano paired delay against the mixture.

## What counts as a pass

- The volcano in `per_time` must equal `per_slot` exactly, since dt = 2 h there. A difference is a bug.
- Two slots of dt must compose to one slot of 2 dt.
- Under the same exponential, `exp(-t/T2)` from `mind/results/delay_experiment.json` must match the model's decay at tau = T2. This checks the form of the decay. It does not link cognitive tau to qubit T2.

The scenario differences have no win condition. They are reported as they come out. This model assumes tau was correctly set on the 2 h step, which nothing validates.

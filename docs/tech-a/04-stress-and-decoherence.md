# Stress and decoherence

## What it does

Every event slot — including a step where nothing new happened ("none") —
is followed by a small, irreversible loss of the belief qubit's coherence,
sized by how stressed the agent currently is. At low stress this loss is
negligible and the belief keeps its full quantum behavior (order effects,
interference). As stress rises, coherence drains away a little more after
every slot, and in the limit of maximum stress the belief becomes a purely
classical mixture: no coherence survives from one event to the next, so
the order the signs arrived in stops mattering at all. This is the
honest, falsifiable version of "stress clouds judgment": we model stress
as **dephasing**, a specific, named physical channel, not as a vague
multiplier on the final answer.

## The math

**Why dephasing, not depolarizing or amplitude damping.** Depolarizing
would shrink the whole Bloch vector toward the center, including `z`
(destroying real information that safety set, not just coherence).
Amplitude damping relaxes the qubit toward `|0>` = safe specifically — the
wrong direction for a *stress* model, which should not by itself make the
agent feel safer. Dephasing shrinks only the off-diagonal (coherence)
terms and leaves the diagonal (the belief's actual safe/danger weighting)
untouched — exactly "losing track of how you got here," not "forgetting
what you believe."

**The environment-record derivation.** Dephasing is what happens when a
qubit's coherence leaks, unrecoverably, into an environment that is never
measured. If qubit 0's `|0>`, `|1>` components become correlated with two
orthogonal environment records `|E0>, |E1>` with overlap
`<E1|E0> = sqrt(1-gamma)`, tracing out the environment gives

```
rho_01 -> rho_01 * <E1|E0> = rho_01 * sqrt(1 - gamma)
```

— the off-diagonal entry shrinks by `sqrt(1-gamma)`, the diagonal entries
are untouched. This is exactly the phase-damping channel.

**Kraus operators:**

```
K0 = [[1, 0], [0, sqrt(1-gamma)]]
K1 = [[0, 0], [0, sqrt(gamma)]]
rho' = K0 rho K0^dagger + K1 rho K1^dagger
```

**The gamma trap.** Qiskit Aer's `phase_damping_error(gamma)` implements
exactly this channel, and it scales coherence by `sqrt(1-gamma)`, **not**
`(1-gamma)`. So passing a per-slot decay rate `lam` directly as `gamma`
over-damps. The fix:

```
gamma = 1 - (1 - lam)^2   =>   sqrt(1 - gamma) = 1 - lam
```

which makes `lam` itself the clean, linear per-slot coherence-retention
complement: after one slot, off-diagonal magnitude is multiplied by
exactly `(1 - lam)`.

**Stress mapping (D5):** `lam = decoherence_strength(stress) =
clamp((stress - 0.2) / 0.7, 0, 1)`. The engine's agent starts at stress
0.15 (below the 0.2 floor, so `lam = 0`, full coherence) and each sign adds
roughly 0.08 to stress; the GUI's decoherence meter must use this same
function (Stage 5), not its own `(stress-0.4)/0.5` formula, or the
displayed number and the model's actual per-step behavior would silently
diverge.

**Commuting-flip theorem at lam=1.** Once a slot's damping is total
(`gamma=1`, i.e. `sqrt(1-gamma)=0`), the off-diagonal is zeroed exactly, so
the belief entering the *next* slot is always perfectly diagonal
(`x=y=0`). Acting on a diagonal state, *either* rotation axis reduces to a
pure scalar map on `z`: `R_y` gives `z' = z cos(theta)` (using `x=0`),
`R_x` gives `z' = z cos(phi)` (using `y=0`) — the same form regardless of
axis. A chain of scalar multiplications commutes, so **the final `z`,
and therefore `P(protect)`, does not depend on the order of any two slots
that are both preceded by at least one fully-damped slot.** The one
exception is the very *first* slot applied straight out of
`prepare_belief`, which already carries nonzero `x` (the preparation
rotation itself creates coherence) — swapping the first two events of a
bare two-event history can still show a gap even at `lam=1`, because that
first rotation's axis choice interacts with the pre-existing `x`. In the
real game this never arises in practice: `recent_events` almost always has
a sign already in it before the pair being compared, and the plan's own
definition of "order gap" (Section 4.7) swaps the *last* two events of
whatever history exists, not the first two of an empty one.

## The code

`mind/decoherence.py`:
- `decoherence_strength(stress)` — the `lam` mapping above.
- `apply_phase_damping(rho, lam)` — the Kraus channel, with the `gamma`
  trap already corrected internally.

`mind/belief.py`'s `run_events(rho, events, lam)` now calls
`apply_phase_damping` after every `apply_event`, including after `"none"`.

## How we know it works

```
$ source .venv/bin/activate && python -m pytest -v mind/tests/test_decoherence.py
test_gamma_mapping_matches_aer_phase_damping_error PASSED
test_x_monotone_non_increasing_in_lambda_tremor_then_gas_plume PASSED
test_classical_limit_order_gap_vanishes_at_full_dephasing PASSED
test_stress_mapping PASSED
4 passed in 0.20s
```

Numbers from running the real `mind/decoherence.py` / `mind/belief.py`
this session:

```
apply_phase_damping(|+><+|, lam=0.2)[0,1] = 0.4   (gamma=0.36; matches qiskit_aer.noise.phase_damping_error(0.36) exactly)

decoherence_strength(0.15) = 0.0
decoherence_strength(0.85) = 0.9285714285714285   (plan: 0.929)
decoherence_strength(1.0)  = 1.0

|x| vs lam, prepare_belief(0.85) then [tremor, gas_plume]:
  lam=0.000  |x|=0.963289
  lam=0.200  |x|=0.616505
  lam=0.400  |x|=0.346784
  lam=0.600  |x|=0.154126
  lam=0.800  |x|=0.038532
  lam=0.929  |x|=0.004856
  lam=1.000  |x|=0.000000        -> strictly non-increasing

Order gap at lam=1, prefix=[storm] before the swapped pair (q_S=0.69, q_D=0.59, eta=-0.7853897988344999):
  [tremor, gas_plume]  vs reversed: |Pa-Pb| = 1.11e-16,  Pa = 0.642074 = classical total exactly
  [injury, cold_night] vs reversed: |Pa-Pb| = 1.11e-16,  Pa = 0.645812 = classical total exactly
  [gas_plume, injury]  vs reversed: |Pa-Pb| = 0.00e+00,  Pa = 0.637926 = classical total exactly
```

Same prefix=[storm], [tremor, gas_plume] pair, swept over lam (cited in
`demo-pack/tech-a/03-stress-turns-quantum-mind-classical.md`'s "0.140"
claim; `docs/tech-a/figures/order_effect_vs_lambda.png` plots the full
curve):
```
$ python3 -c "
from mind.belief import prepare_belief, run_events
from mind.model import bloch_vector, p_protect_closed_form
qS,qD,eta=0.69,0.59,-0.7853897988344999
rho0 = prepare_belief(0.85)
a = run_events(rho0, ['storm','tremor','gas_plume'], 0.0)
b = run_events(rho0, ['storm','gas_plume','tremor'], 0.0)
xa,ya,za = bloch_vector(a); xb,yb,zb=bloch_vector(b)
pa,pb=(1-za)/2,(1-zb)/2
Pa=p_protect_closed_form(pa,xa,qS,qD,eta); Pb=p_protect_closed_form(pb,xb,qS,qD,eta)
print('gap at lam=0:', Pa-Pb)
"
gap at lam=0: 0.13981761515248126
```

## Limits and honest claims

- "We model stress as dephasing" — a specific, named, falsifiable physical
  channel, verified against Qiskit Aer's own `phase_damping_error` above.
  This is not a claim that human stress physically is quantum dephasing.
- The stress-to-`lam` mapping (D5) is a design choice tuned to the
  engine's own stress dynamics (starting stress, per-sign increments), not
  a value derived from any external data.
- The commuting-flip theorem is exact only once at least one prior slot
  has fully damped the belief; a bare two-event order-gap check applied
  directly to a freshly prepared belief is not guaranteed to vanish at
  `lam=1`, for the reason given above. `quantum_decide`'s order-gap
  calculation (Stage 4) always operates on a real `recent_events` history,
  where this edge case does not arise.

## Questions a judge might ask

**Why does full dephasing make the order of events irrelevant?** Define
`F(f) = (1-f) I + f X` conceptually as "fully randomize the off-diagonal
with probability `f`, keep it with probability `1-f`" — at `f=1` (full
dephasing), every slot forces the belief back onto the diagonal (`x=y=0`)
before the next slot starts. A rotation applied to a diagonal state is
then just a scalar multiply of `z` by `cos(angle)`, and scalar
multiplication commutes — so chaining any two such slots gives the same
final `z`, hence the same `P(protect)`, regardless of which came first.

**Why dephasing and not depolarizing or amplitude damping?** Depolarizing
would also shrink `z`, destroying the safety information itself, not just
the memory of event order. Amplitude damping specifically relaxes toward
`|0>=safe`, which would make a *stressed* agent artificially feel safer —
backwards. Dephasing is the only one of the three standard noise channels
that touches only coherence and leaves the belief's actual safe/danger
weighting alone.

**Isn't `gamma = 1-(1-lam)^2` an arbitrary fudge?** No — it is the unique
function of `lam` that makes Aer's own `sqrt(1-gamma)` coherence-scaling
equal exactly `(1-lam)`, so that `lam` itself has a clean physical meaning
(fraction of coherence lost per slot) instead of a meaning tied to Aer's
particular parameterization.

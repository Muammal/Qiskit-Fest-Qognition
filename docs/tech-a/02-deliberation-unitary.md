# The deliberation unitary

## What it does

The mind holds two qubits: qubit 0 is **belief** (|0⟩ = "it's a false
alarm, I'm safe", |1⟩ = "danger is real") and qubit 1 is **decision**
(|0⟩ = carry on, |1⟩ = protect/evacuate). The decision qubit always starts
at |carry on⟩. A single real 4×4 unitary `U` — the deliberation step —
turns the current belief into a joint belief+decision state whose
probability of landing in "protect" is the agent's P(protect). `U` is built
from two classical conditional probabilities, `q_S` (how often protecting
is right when the agent is actually safe) and `q_D` (how often it's right
when danger is real), plus one calibrated constant `eta` that controls how
much quantum interference the deliberation adds on top of the classical
mixture of those two conditionals. This is the mechanism behind the
"uncertainty dip": an agent that is genuinely unsure (belief near 50/50)
can end up *less* likely to protect than either the "definitely safe" or
"definitely in danger" case would predict on its own — the well-documented
disjunction effect from human judgment under uncertainty.

## The math

**Basis.** Qiskit is little-endian, so basis index = belief + 2·decision:
index 0 = (safe, carry), 1 = (danger, carry), 2 = (safe, protect),
3 = (danger, protect).

**Inputs.** `q_S, q_D ∈ [0.02, 0.98]`, clamped elsewhere (Section 4.2); the
calibration constant `eta`.

**Bound on interference.** Define

```
kappa_max = min(1, sqrt((1 - q_S)(1 - q_D) / (q_S q_D)))
kappa = eta * kappa_max
```

The `min(1, ...)` matters: without it, a `kappa` fixed independently of
`q_S, q_D` can push `cos(beta)` below -1 or above +1 for some `(q_S, q_D)`
pairs, and the resulting `sin(beta) = sqrt(1 - cos(beta)^2)` is then the
square root of a negative number — the NaN the plan warns about. Capping
`kappa` at `kappa_max` guarantees `|cos(beta)| <= 1` for every `eta` in
`[-1, 1]`.

**The two live columns of U.** Since the decision qubit always starts at
|carry⟩, only `u = U|safe,carry⟩` and `w = U|danger,carry⟩` matter:

```
u = sqrt(q_S) |safe,protect>  + sqrt(1 - q_S) |safe,carry>
w = sqrt(q_D) (kappa |safe,protect> + sqrt(1-kappa^2) |danger,protect>)
    + sqrt(1 - q_D) (cos(beta) |safe,carry> + sin(beta) |danger,carry>)
```

**Deriving cos(beta) from orthogonality.** `U` must be unitary, so
`<u|w> = 0`. In the basis above, `u` has nonzero components only at
indices 0 (`sqrt(1-q_S)`) and 2 (`sqrt(q_S)`); `w` has nonzero components
at all four indices, with index 0 = `sqrt(1-q_D) cos(beta)` and index 2 =
`sqrt(q_D) kappa`. So

```
<u|w> = sqrt(1-q_S) sqrt(1-q_D) cos(beta) + sqrt(q_S) sqrt(q_D) kappa = 0
=> cos(beta) = - kappa * sqrt(q_S q_D) / sqrt((1-q_S)(1-q_D))
```

`||u||=1` and `||w||=1` hold automatically from `sin²+cos²=1` identities —
no extra constraint is needed. `sin(beta)` is taken as the positive root;
its sign is a free gauge choice (it multiplies the |danger,carry⟩
component, which only affects phase information inside the "carry on"
branch of the decision qubit, not any measured probability).

**Completing to a 4×4 real orthogonal matrix.** `u, w` are only two
orthonormal columns of the basis; the other two are filled by QR-completing
`[u, w, e2, e3]` (numpy `linalg.qr`), then fixing signs so columns 0 and 1
come back out as `+u, +w` exactly, then negating column 3 if `det(U) = -1`.
This makes `U ∈ SO(4)` (`det = +1`), which by the Cartan KAK decomposition
(Vatan & Williams 2004) compiles to at most 2 CZ gates — see
`06-circuits-and-hardware.md`.

**P(protect), closed form.** For a belief with real Bloch components
`(x, y, z)` and `p = (1-z)/2` (the probability the belief qubit measures
|danger⟩):

```
P(protect) = (1-p) q_S + p q_D   +   x * sqrt(q_S q_D) * kappa
             classical total probability      interference
```

`y` does not appear: `U` and the protect-measurement projector are both
real, so the probability is invariant under `y -> -y`, and only the real
(x, z) Bloch components couple to the deliberation.

**The bound no unitary can beat (Cauchy–Schwarz).** The interference term
is `x * sqrt(q_S q_D) * kappa`, and `|x| <= 1`, `|kappa| <= kappa_max =
sqrt((1-q_S)(1-q_D)/(q_S q_D))`. So

```
|interference| <= sqrt(q_S q_D) * sqrt((1-q_S)(1-q_D)/(q_S q_D)) = sqrt((1-q_S)(1-q_D))
```

which is exactly the amount by which `P(protect)` can move away from the
classical total probability at `p=0.5`. No unitary deliberation — real,
complex, 2-qubit or larger — can push `P(protect)` further than this for
given `q_S, q_D`, because the bound comes from the Cauchy–Schwarz inequality
on normalized `u, w`, not from the specific construction of `U`. This is
why the Prisoner's Dilemma case (test 6 below) is a genuine, provable
limitation, not an implementation gap.

**Calibration (D6).** `eta` was exactly solved so that
`p_protect_closed_form(0.5, x=1, q_S=0.69, q_D=0.59, eta) = 0.36`, the
"unknown" disjunction-effect choice rate from Tversky & Shafir (1992) for
their `69/59/36` numbers. This is a one-shot exact solve, not a fit to many
data points, and transferring it from a gambling-choice study to a
volcano-evacuation scenario is an assumption stated here, not hidden.

## The code

`mind/model.py`:
- `kappa_max(q_S, q_D)` — the bound above.
- `build_U(q_S, q_D, eta)` — builds `u, w` directly from the formulas, then
  QR-completes and sign-fixes as described.
- `p_protect_closed_form(p, x, q_S, q_D, eta)` — the closed form; used both
  as the fast path in `quantum_decide` and as the independent check against
  the full density-matrix / gate-circuit pipelines.
- `bloch_vector(rho_1q)` — `x = 2 Re(rho01)`, `y = -2 Im(rho01)`,
  `z = rho00 - rho11`, the standard Pauli decomposition
  `rho = (I + x X + y Y + z Z) / 2`.

## How we know it works

```
$ source .venv/bin/activate && python -m pytest -v mind/tests/test_model.py
test_tversky_shafir_calibration PASSED
test_classical_limit_eta_zero PASSED
test_U_validity_random_sweep PASSED
test_circuit_equals_formula_random_mixed_beliefs PASSED
test_gate_circuit_matches_closed_form PASSED
test_prisoners_dilemma_bound_cannot_be_fit PASSED
6 passed in 0.17s
```

Numbers from running `mind/model.py` directly, this session:

```
kappa_max(0.69, 0.59)                        = 0.5587560314022095   (plan: 0.5588)
kappa = eta * kappa_max                      = -0.4388412871005448  (plan: -0.4389)
P(p=0.5, x=1, q_S=0.69, q_D=0.59)            = 0.36
P(p=0,   x=0, q_S=0.69, q_D=0.59)            = 0.69
P(p=1,   x=0, q_S=0.69, q_D=0.59)            = 0.59
max |U^T U - I| over this U                  = 2.220446049250313e-16
det(U)                                       = 1.0000000000000002
Prisoner's Dilemma bound (q_S=0.97,q_D=0.84, eta=-1) = 0.8357179676972449 (plan: 0.8357)
```

`test_circuit_equals_formula_random_mixed_beliefs` confirms the closed form
matches the full density-matrix evolution (200 random mixed single-qubit
beliefs, seeds 0–199) to under `1e-12`; `test_gate_circuit_matches_closed_form`
confirms a real `QuantumCircuit` (`ry` + `UnitaryGate(U)`, read via
`Statevector(...).probabilities([1])`) agrees with the same formula.

## Limits and honest claims

- This derivation assumes a **real** unitary throughout (no complex phases
  anywhere in `U`); the model's "quantum-ness" is interference between real
  amplitudes, not a claim about complex quantum mechanics generally.
- `eta = -0.7854` (rounded; `mind/tests/test_model.py` uses the unrounded
  exact-solve value) is a calibration transferred from a published human
  decision-making study, not a property derived from this game's own data.
- The Prisoner's Dilemma bound is a proof that **this model family cannot
  fit every disjunction-effect dataset** — specifically, numbers where the
  "unknown" case drops further below both conditionals than
  `sqrt((1-q_S)(1-q_D))` allows. That is a stated limitation, not a bug.
- Nothing here ran on IBM hardware; `U` was evaluated with `numpy` and with
  Qiskit's `Statevector` simulator only.

## Questions a judge might ask

**Why can't a bigger/different unitary fit the Prisoner's Dilemma numbers
better?** Because the bound `sqrt((1-q_S)(1-q_D))` on how far interference
can move `P(protect)` away from the classical total probability comes from
Cauchy–Schwarz on two unit vectors (`u, w`) with a fixed inner product of
zero (orthogonality is required for `U` to be unitary at all) — it isn't a
limitation of this particular `U`, it's a limitation of *any* unitary
deliberation built this way.

**Why does the interference term vanish at p=0 or p=1?** Those correspond
to `z = ±1`, pure `|safe⟩` or `|danger⟩` beliefs, which have `x = 0` (no
real coherence term left — the Bloch vector is purely along `z`). With
`x = 0` the interference term `x * sqrt(q_S q_D) * kappa` is exactly zero,
so `P(protect)` reduces to `q_S` or `q_D` respectively, matching the test.

**Why does a fixed `kappa` (not tied to `q_S, q_D`) produce NaNs?** Because
`cos(beta) = -kappa * sqrt(q_S q_D) / sqrt((1-q_S)(1-q_D))` can exceed 1 in
magnitude for some `(q_S, q_D)` once `kappa` is unconstrained, and
`sin(beta) = sqrt(1 - cos(beta)^2)` is then undefined. Capping
`kappa = eta * kappa_max(q_S, q_D)` with `|eta| <= 1` keeps `|cos(beta)| <= 1`
for every valid `q_S, q_D`.

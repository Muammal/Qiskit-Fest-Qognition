# Events and order effects

## What it does

The belief qubit starts at a mix of "safe" and "danger" set by the agent's
`safety` need, then each recent event nudges that belief with its own gate:
ambiguous signs (`tremor`, `gas_plume`, `storm`, `animal`, `injury`,
`cold_night`, `find_food`) are rotations, and unambiguous danger
(`eruption`, `ash_fall`) is a projective collapse onto "danger" — not a
rotation, because real evidence can't be walked back by rotating the wrong
way. Because `tremor` and `gas_plume` rotate about different axes, they
**do not commute**: feeling the tremor first and then smelling gas leaves
the agent in a measurably different belief state than smelling gas first
and then feeling the tremor, even though the same two signs were observed.
That difference in belief is what produces the order effect in
`quantum_decide` later (Stage 4).

## The math

**Preparation.** `R_y(theta0)` on `|0>`, with
`sin^2(theta0/2) = clamp(1 - safety, 0.02, 0.98)`. This is a pure state at
`y = 0`; its Bloch `z = cos(theta0)`, `x = sin(theta0)`.

**Rotation gates**, applied by conjugation `rho -> U rho U^dagger`:

```
R_y(theta) = [[cos(theta/2), -sin(theta/2)], [sin(theta/2), cos(theta/2)]]
R_x(theta) = [[cos(theta/2), -i sin(theta/2)], [-i sin(theta/2), cos(theta/2)]]
```

`R_y` rotates in the Bloch x-z plane (leaves `y` fixed); `R_x` rotates in
the y-z plane (leaves `x` fixed). That is exactly why `tremor` (`R_y`) and
`gas_plume` (`R_x`) don't commute — they rotate about different axes of the
same sphere, and rotations about different axes compose differently
depending on order (this is the same non-commutativity as 3D rigid-body
rotations; it is not something special to quantum mechanics by itself).

**Collapse**, for unambiguous evidence (`eruption`, `ash_fall`):

```
rho -> Pi rho Pi / Tr(Pi rho Pi),   Pi = |danger><danger| = diag(0, 1)
```

This sets `x = y = 0` and `z = -1` (`P(danger) = 1`) from any starting
belief, and is idempotent: collapsing an already-collapsed belief changes
nothing, because `Pi` applied to `|danger><danger|` is `|danger><danger|`
again.

**Angle rule.** No event's rotation angle is `+-pi/2`: under full
dephasing (Stage 3, lam=1), a `pi/2` rotation would reset any belief to
50/50 regardless of what came before, destroying the very history the
model is trying to represent.

| Event | Gate | Angle (rad) |
| --- | --- | --- |
| tremor | R_y | 1.047198 (pi/3) |
| gas_plume | R_x | 1.884956 (3pi/5) |
| storm, animal | R_y | 1.047198 (pi/3) |
| injury | R_x | 2.094395 (2pi/3) |
| cold_night | R_x | 0.523599 (pi/6) |
| find_food | R_y | -0.785398 (-pi/4) |
| eruption, ash_fall | collapse onto \|danger\> | n/a |
| none | identity | n/a |

## The code

`mind/belief.py`:
- `prepare_belief(safety)` — the R_y preparation above.
- `apply_event(rho, event)` — one gate: rotation, collapse, or identity.
- `run_events(rho, events, lam)` — applies events in order, oldest first.
  `lam` must be `0` in this stage (`NotImplementedError` otherwise);
  per-slot phase damping is added here in Stage 3 without changing this
  function's signature.
- `EVENT_GATES` holds the angle table above; it moves into
  `mind/config.py` in Stage 4 alongside the model's other constants.

## How we know it works

```
$ source .venv/bin/activate && python -m pytest -v mind/tests/test_belief.py
test_prepare_belief_p_danger_is_one_minus_safety PASSED
test_prepare_belief_clamps_p_danger PASSED
test_ry_moves_z_into_x_rx_leaves_x_unchanged PASSED
test_collapse_on_eruption_is_idempotent_and_certain PASSED
test_order_noncommutation_tremor_gas_plume PASSED
test_no_event_angle_is_plus_or_minus_half_pi PASSED
6 passed in 0.02s
```

**Bloch walk-through**, from `prepare_belief(safety=0.85)` — the engine's
default initial agent `safety` (`engine/agent.py` `Agent.needs`):

```
prepare_belief(0.85):        x=0.714143  y=-0.000000  z=0.700000  P(danger)=0.150000

Order A: tremor, then gas_plume
  after tremor:               x=0.963289  y=-0.000000  z=-0.268466  P(danger)=0.634233
  after gas_plume:             x=0.963289  y=0.255326   z=0.082961   P(danger)=0.458520

Order B: gas_plume, then tremor
  after gas_plume:             x=0.714143  y=-0.665740  z=-0.216312  P(danger)=0.608156
  after tremor:                x=0.169740  y=-0.665740  z=-0.726622  P(danger)=0.863311
```

The two orders end at different `(x, y, z)` — and, notably, different
`P(danger)` even though "danger" readout is only one axis: the
intermediate rotations don't commute, so the full state (not just one
projection of it) depends on order. Order A ends with `P(danger)=0.459`;
order B ends with `P(danger)=0.863` — a large, visible difference from the
same two signs in a different sequence.

```
Eruption collapse from prepare_belief(0.85):
  x=0.000000  y=-0.000000  z=-1.000000  P(danger)=1.000000
  idempotent, max|rho - rho_after_second_ash_fall| = 0.0
```

## Limits and honest claims

- A rotation is **not** a Bayesian update. It has no concept of a prior
  times a likelihood; it is a fixed geometric nudge regardless of how
  confident the belief already is. The model's claim is narrower: that
  representing ambiguous evidence as non-commuting rotations reproduces
  *order effects* seen in human judgment, not that it reproduces Bayesian
  reasoning.
- Collapse is used only for the two events the plan calls unambiguous
  (`eruption`, `ash_fall`). Every other event, including genuinely strong
  signs like `injury`, is modeled as a rotation — a design choice (D2),
  not a law derived from the game's physics.
- `run_events` in this stage has no decoherence; the order effect shown
  above is at full coherence (`lam=0`). Stage 3 shows how this gap shrinks
  to (and below) the test threshold as stress rises.

## Questions a judge might ask

**Why does an eruption collapse the belief instead of just rotating it a
lot?** A large rotation can overshoot: starting already near `|danger>`
and applying a "move toward danger" rotation can, depending on the exact
starting angle, rotate *past* `|danger>` and back toward `|safe>` on the
far side of the sphere. A projective collapse can't do that — Pi always
leaves you at `|danger>` exactly, from any starting belief (D2).

**Why do R_y and R_x act on different Bloch components?** Because they are
rotations about different axes of the same Bloch sphere (y and x
respectively); a rotation about an axis never moves the component along
that axis. `R_y` fixes `y`, `R_x` fixes `x`. Using two different axes for
`tremor` and `gas_plume` is exactly what makes them non-commuting — using
the same axis for both would make order never matter, and the order-effect
test would fail.

**Is this really modeling a "memory" of event order, or just an artifact
of picking non-commuting gates?** Both, honestly: the model's claim is
that representing ambiguous signs as non-commuting Bloch rotations is a
*mechanism* capable of producing order effects, calibrated against a human
judgment phenomenon elsewhere (the Tversky-Shafir disjunction effect,
Stage 1). It is not claiming the brain literally performs qubit rotations.

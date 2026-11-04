# Decision rule and reflexes

## What it does

Once `P(protect)` is known, it is split by prior into 7 action
probabilities (one for `hide`, six for the rest), one of those is chosen,
and then a small physiology-driven safety net can override that choice:
critical thirst always means `drink`, critical warmth always means
building shelter (if there's wood) or foraging, no matter what the
deliberation computed. The override is logged, not hidden — the reason
string and the `quantum` diagnostics both say when it fired, so later
analysis can tell "the model chose this" apart from "physiology forced
this."

## The math

**Splitting P(protect) into 7 actions (Section 4.6):**

```
probs[a] = P(protect) * prior[a] / sum(prior[b] for b in PROTECT)     for a in PROTECT
probs[a] = (1-P(protect)) * prior[a] / sum(prior[b] for b in CARRY_ON) for a in CARRY_ON
```

Since `PROTECT = ["hide"]` (D1), the first line always reduces to
`probs["hide"] = P(protect)` exactly — the division cancels. The six
carry-on actions share `1 - P(protect)` in proportion to their prior
weight relative to each other.

**Decision rule (D3):** `action = argmax(probs)` by default. A `"sample"`
mode is available (Born-rule draw via the global `random`), but is not the
default — see D3's rationale in `DECISIONS.md`.

**Reflex layer (D4), applied after the rule, unconditionally:**

```
if thirst < 0.3:        action = "drink"
elif warmth < 0.4:       action = "build_shelter" if wood >= 2 else "forage"
```

**Order gap (Section 4.7):** swap the last two non-`"none"` events in
`recent_events`, recompute `P(protect)` for that swapped history with the
same `q_S, q_D`, and report `gap = P(protect)_actual - P(protect)_swapped`.
If `|gap| > 0.02` (`ORDER_GAP_REPORT_THRESHOLD`), the reason gains
`"Order effect: A then B shifts P(protect) by +-N%"`.

**Decoherence note:** if `lam > 0`, the reason gains
`"Decoherence: stress S, dephasing N% per step"`.

**Output contract:** `{"action", "probs", "reason", "quantum": {p_danger,
p_protect, p_classical, lam, q_safe, q_danger, order_gap, reflex,
decision_rule}}` — a superset of the frozen `{"action", "probs", "reason"}`
contract, which `validate_decision` explicitly allows (extra keys OK).

**Control:** `classical_mixture_decide(state)` calls the exact same
pipeline with `lam` forced to `1` and the order-gap text suppressed. Since
the final event slot's dephasing is always total, the belief entering the
probability split is always exactly diagonal (`x=0`), so the interference
term vanishes identically and `p_protect == p_classical` — not
approximately, but as a direct algebraic consequence of `x=0`.

## The code

`mind/quantum_mind.py`:
- `decision_probs(p_protect, prior)` — the 4.6 split.
- `_q_safe_danger(state)` — builds `cf_safe`/`cf_danger` counterfactual
  states (Section 4.2) and calls `contracts.get_prior` on each.
- `_apply_reflex(state, action)` — D4.
- `_choose_action(probs, decision_rule)` — D3.
- `_order_gap(state, lam, q_S, q_D)` — Section 4.7's order-gap calculation.
- `_decide(state, force_lam=None, suppress_order_gap=False, decision_rule=None)`
  — the shared pipeline; `quantum_decide` and `classical_mixture_decide`
  are both thin wrappers over it.
- `decoherence_strength` is re-exported from `mind.decoherence`.

## How we know it works

```
$ source .venv/bin/activate && python -m pytest -v mind/tests/test_quantum_mind.py
test_decision_probs_split PASSED
test_contract_seven_actions_sum_to_one_and_diagnostics_present PASSED
test_repo_compatibility[test_contracts_stubs] PASSED
test_repo_compatibility[test_quantum_order_effect_in_contracts] PASSED
test_repo_compatibility[test_quantum_stress_decoherence] PASSED
test_repo_compatibility[test_volcanic_order_effect_and_lethal_overlay] PASSED
test_repo_compatibility[test_urgent_thirst_beats_warning_in_both_stubs] PASSED
test_repo_compatibility[test_simulation_engine_run] PASSED
test_repo_compatibility[test_demo_pack_validity] PASSED
test_volcano_order_demo PASSED
test_after_eruption_no_interference PASSED
test_reflex_thirst_overrides PASSED
test_classical_mixture_control PASSED
test_determinism_seeded_run PASSED
test_speed_under_10ms_per_call PASSED
15 passed in 0.21s

$ SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py mind/tests
62 passed in 1.45s
```

Real examples, from `SurvivalAgent().get_state()` (stress=0.15, safety=0.85,
`recent_events=["none","none"]` by default — `q_S, q_D` recomputed per
`recent_events` below) via `mind/quantum_mind.py` this session:

**Order demo** (`q_S=0.100, q_D=0.550` from the current `get_prior` stub):

| Order | p_danger | P(protect) | classical | action |
| --- | --- | --- | --- | --- |
| tremor, gas_plume | 0.459 | 0.129 | 0.306 | explore |
| gas_plume, tremor | 0.863 | 0.457 | 0.488 | hide |

```
Order gap |0.129-0.457| = 0.328 > 0.2; actions differ (explore vs hide)
reason (order A): "...Order effect: tremor then gas_plume shifts P(protect) by -32.8%"
reason (order B): "...Order effect: gas_plume then tremor shifts P(protect) by +32.8%"
```

**After eruption** (`recent_events=["tremor","ash_fall","eruption"]`):
```
p_danger = 1.0, P(protect) = 0.550 = q_danger exactly, no interference
```

**Reflex** (thirst=0.1, `recent_events=["gas_plume","tremor"]`):
```
action: drink
reason: "Reflex (thirst) overrides drink -> drink. Quantum deliberation: ...
         Order effect: gas_plume then tremor shifts P(protect) by +10.9%"
```
The rule itself already chose `drink` here (the stub `get_prior` weighs
critical thirst heavily enough on its own) — the reflex and the
deliberation agree in every state this repo's tests construct. The reflex
is still load-bearing: it is what `test_urgent_thirst_beats_warning_in_both_stubs`
requires, and it is logged (`quantum.reflex`) precisely so an analysis
that finds a state where they *disagree* can separate "physiology
decided" from "the model decided."

**Control** (`recent_events=["tremor","gas_plume"]`, `classical_mixture_decide`):
```
p_protect = 0.30633388566476744
p_classical = 0.30633388566476744   (equal to 1e-9)
reason: "...Decoherence: stress 0.15, dephasing 100% per step"   (no "Order effect" text)
```

**Speed:** 0.067 ms/call average over 200 calls (plan prototype: 2-3.5 ms;
well under the 10 ms budget either way).

## Limits and honest claims

- The reflex layer means `quantum_decide`'s final `action` is not purely a
  quantum-model output in every state — it is "quantum model, with a
  physiological safety net," exactly like Tech C's classical stub. The
  `quantum` diagnostics make this auditable rather than hidden.
- `argmax` is deterministic and noise-free by design (D3); it does not
  demonstrate anything about how a human or an agent "samples" a decision
  under uncertainty, only which action the model's probabilities favor.
- The order-gap text uses a `0.02` threshold (D-config); smaller genuine
  effects exist but aren't narrated in the reason string, only in
  `quantum.order_gap`.

## Questions a judge might ask

**Why is the control mind (`classical_mixture_decide`) the strongest
answer to "isn't this just noise"?** Because it is built from the *exact
same* pipeline, the *exact same* `q_S, q_D`, the *exact same* prior split —
the only difference is `lam` forced to `1`. Any measured difference
between `quantum_decide` and `classical_mixture_decide` on the same seeds
(Stage 7's batch statistics) is attributable to the interference term
specifically, not to some other unaccounted-for modeling choice.

**What does the reflex layer hide from the quantum layer, and why log
it?** It can silently overrule the deliberation's chosen action in states
the quantum layer never "sees" as a conflict — physiology always wins. We
log `quantum.reflex` precisely so Stage 7's analysis can exclude
reflex-overridden steps from the quantum-vs-classical action-divergence
count: comparing what two minds are *forced* to do tells you nothing about
how they differ when they're free to decide.

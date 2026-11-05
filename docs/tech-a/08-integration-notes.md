# Integration notes (Stage 5)

PR branch `tech-a/integration` (from `tech-a/quantum-mind`), for Tech C to
review. **Not merged by Tech A** — per plan rule D9. `git diff --stat`
against `tech-a/quantum-mind` touches exactly these four files:

```
contracts.py           | 21 ++++++++++++++++++--
engine/batch_runner.py | 54 ++++++++++++++++++++++++++++++++++++++++++++++----
engine/gui.py          | 16 +++++++++------
engine/simulation.py   | 15 +++++++++++++-
4 files changed, 93 insertions(+), 13 deletions(-)
```

## 1. `contracts.py`: delegate quantum_decide to mind.quantum_mind

**What:** renamed the existing stub to `_quantum_decide_stub`, kept
verbatim as a fallback. `quantum_decide` now tries
`from mind.quantum_mind import quantum_decide`; on `ImportError` it calls
the stub instead.

**Why:** this is the one line that actually wires Tech A's model into the
game. The `try/except ImportError` means the repo still runs with the old
stub behavior if `mind/` is ever removed or broken — no hard dependency.

**Diff:**
```diff
-def quantum_decide(state: Dict[str, Any]) -> Dict[str, Any]:
-    """Tech A responsibility: 2-qubit decision circuit. Heuristic stub with no circuits until then."""
+def _quantum_decide_stub(state: Dict[str, Any]) -> Dict[str, Any]:
+    """Heuristic stub, kept as a fallback if mind.quantum_mind is unavailable."""
     validate_state(state)
     ...
     return decision


+try:
+    from mind.quantum_mind import quantum_decide as _quantum_decide_impl
+except ImportError:
+    _quantum_decide_impl = None
+
+
+def quantum_decide(state: Dict[str, Any]) -> Dict[str, Any]:
+    """Tech A responsibility: 2-qubit decision circuit.
+
+    Delegates to mind.quantum_mind.quantum_decide; falls back to the
+    heuristic stub if mind/ is unavailable.
+    """
+    if _quantum_decide_impl is not None:
+        return _quantum_decide_impl(state)
+    return _quantum_decide_stub(state)
```

**Evidence:** `test_repo_compatibility` (`mind/tests/test_quantum_mind.py`)
monkeypatches this exact function and runs all 7 required pre-existing
mind tests against it; all pass. With this edit live (no monkeypatch
needed), the full suite still passes — see bottom of this file.

## 2. `engine/simulation.py`: log quantum diagnostics, add a classical_mixture mind

**What:** `SimulationEngine.step`'s step record now includes
`quantum=decision.get('quantum')` — the full diagnostics dict
(`p_danger`, `p_protect`, `p_classical`, `lam`, `q_safe`, `q_danger`,
`order_gap`, `reflex`, `decision_rule`) when the mind provides one, else
`None`. Also added `mind_type='classical_mixture'` as a third option
(alongside `'quantum'`/`'classical'`), resolving to
`mind.quantum_mind.classical_mixture_decide` when `mind/` is importable.

**Why:** this is a new JSON key on every logged step (`timeline.json`,
demo-pack files) — **flag this to Product D**, since anything reading
step records positionally or with strict schema validation needs to know.
The `classical_mixture` mind type is what lets `batch_runner.py` and any
future GUI toggle run the control mind by name, the same way `'quantum'`
and `'classical'` already work.

**Diff:**
```diff
+try:
+    from mind.quantum_mind import classical_mixture_decide
+except ImportError:
+    classical_mixture_decide = None
+
 DEFAULT_STEPS = 36
 ...
-        self.decide_fn = decide_fn or (contracts.quantum_decide if self.mind_type == 'quantum' else contracts.classical_decide)
+        if decide_fn:
+            self.decide_fn = decide_fn
+        elif self.mind_type == 'quantum':
+            self.decide_fn = contracts.quantum_decide
+        elif self.mind_type == 'classical_mixture' and classical_mixture_decide is not None:
+            self.decide_fn = classical_mixture_decide
+        else:
+            self.decide_fn = contracts.classical_decide
 ...
         record = dict(t=t, state=state, event=event, action=decision['action'],
                       probs=decision['probs'], reason=decision['reason'],
+                      quantum=decision.get('quantum'),
                       pos_after=list(agent.pos), phase=self.volcano.phases[t])
```

**Evidence:** `test_simulation_engine_run` and `test_demo_pack_validity`
(run via `test_repo_compatibility`) still pass with the new key present;
`test_determinism_seeded_run` confirms two seeded runs with
`mind_type`/`decide_fn=quantum_decide` are still bit-identical.

## 3. `engine/gui.py`: honest labels, real decoherence-meter formula

**What:** two wording fixes (the overclaims the plan flagged at
~line 702 and ~line 1419), and the decoherence meter / debrief line
(~line 1748 and ~line 1897) now call `decoherence_strength(stress)` from
`mind.decoherence` (guarded import; falls back to the old
`(stress-0.4)/0.5` formula if `mind/` is unavailable, so the GUI still
runs standalone).

**Why:** "real delay decoherence under stress" and "driving real IBM
quantum physical decoherence" are exactly the claims
`TECH_A_BUILD_PLAN.md` and `CLAUDE.local.md` prohibit — nothing in this
game calls hardware live. The meter formula was also silently different
from the model's actual per-step `lam` (`(stress-0.4)/0.5` vs
`(stress-0.2)/0.7`, D5) — fixing the formula source means the number on
screen is the number the model actually used, not a separate guess.

**Diff:**
```diff
+try:
+    from mind.decoherence import decoherence_strength
+except ImportError:
+    def decoherence_strength(stress):
+        return min(1.0, max(0.0, (stress - 0.4) / 0.5))
+
 ...
-            subtext="Non-commuting belief rotations + real delay decoherence under stress",
+            subtext="Non-commuting belief rotations + simulated dephasing (stress model)",
 ...
-            "  * Hardware Stress: Physiological stress increases delay-gate duration, driving real IBM quantum physical decoherence.",
+            "  * Stress Model: Physiological stress maps to a simulated dephasing channel (stress model); no hardware decoherence is driven live.",
 ...
-        decoherence_pct = 0.0
-        if self.agent.stress > 0.4:
-            decoherence_pct = min(1.0, (self.agent.stress - 0.4) / 0.5)
+        decoherence_pct = decoherence_strength(self.agent.stress)
 ...
-            ("Final Stress & Noise:", f"...Decoherence: {int(max(0, self.agent.stress - 0.4)/0.5 * 100)}% off-diagonal decay", COLOR_CYAN),
+            ("Final Stress & Noise:", f"...Decoherence: {int(decoherence_strength(self.agent.stress) * 100)}% off-diagonal decay (stress model)", COLOR_CYAN),
```

**Not changed, flagged for Tech C to consider separately:** line ~1891,
`engine_name = "2-Qubit Quantum Mind (Qiskit 2.x)"` in the debrief screen.
This isn't one of the plan's four flagged locations, so it wasn't touched
here, but worth a look: the live decision path validates against real
Qiskit circuits (Stage 1 tests) without running one every decision (for
speed - see `05-decision-rule-and-reflexes.md`), so "(Qiskit 2.x)" is
true of the verification, not of what executes live each step. Tech C's
call whether that distinction needs surfacing in the GUI.

**Also not changed, found by the Stage 9 overclaim audit (fresh-context
subagent, run against `tech-a/quantum-mind`, which doesn't have this PR's
changes yet):** line ~1413, the section header
`"SIMULATION DYNAMICS & QUANTUM HARDWARE SPECIFICATION"`. On its own it's
borderline, but it sits directly above the line ~1419 fix above and
reinforces the same false "runs on real hardware" impression that fix is
meant to remove. Not in the plan's original four-location list, so not
touched in this PR; flagged here so Tech C can fold it into this same
review pass rather than finding it separately later.

**Evidence:** `test_gui_module`, `test_gui_home_and_end_screen`,
`test_gui_fullscreen_and_aspect_scaling`, `test_gui_event_choice_and_scenarios`
(all in the required full-suite run) still pass with
`SDL_VIDEODRIVER=dummy`.

## 4. `engine/batch_runner.py`: quantum vs classical_mixture as the primary comparison

**What:** `run_batch_comparison` now also runs the `classical_mixture`
mind on every seed (guarded by the same `ImportError` pattern) and adds a
`summary["mixture_comparison"]` block (divergence rate, survival rate)
documented as the primary comparison per D9/Stage 4's control-mind
rationale. The original quantum-vs-classical-stub (argmax) comparison is
**left completely unchanged** — same keys, same values — because
`main.py`'s `--batch` output reads those keys directly, and `main.py` is
outside Tech A's ownership (not even covered by the Stage 5 exception).

**Why:** the plan (Stage 5, item 4) asks for "quantum vs mixture, with
argmax kept for reference" — this does both without touching `main.py`.

**Diff:** see the full diff above (`engine/batch_runner.py`, 54 lines).

**Evidence:**
```
$ SDL_VIDEODRIVER=dummy python main.py --batch
=== Synthetic Heuristic-Stub Results (20 Seeds) ===
  Synthetic heuristic-stub results; no quantum circuits or hardware runs. Noise source: stub
  Total Evaluated Decisions: 646
  Decision Divergences:      237
  Divergence Rate:           36.69%
  Quantum-labelled Stub Survival Rate:     70.0%
  Classical-labelled Stub Survival Rate:   65.0%
```
(unchanged output - confirms `main.py` needed no changes) and, calling
`run_batch_comparison` directly to show the new block:
```
$ python -c "from engine.batch_runner import run_batch_comparison; import json; print(json.dumps(run_batch_comparison(num_seeds=5)['mixture_comparison'], indent=2))"
{
  "description": "Primary comparison (D9): quantum vs classical_mixture_decide, same model with lam forced to 1.",
  "mixture_policy": "mind.quantum_mind.classical_mixture_decide",
  "total_evaluated_steps": 179,
  "total_divergences": 46,
  "divergence_rate_pct": 25.7,
  "mixture_survival_rate_pct": 60.0
}
```

## 5. Scripted event sequence for a reproducible order demo (proposal only, not implemented)

**Proposal:** `EventGenerator` currently derives `tremor`/`gas_plume`
timing from its own seeded random process (`engine/events.py`), which
means there's no single seed guaranteed to produce the
`[tremor, gas_plume]` vs `[gas_plume, tremor]` pair back-to-back for a
clean demo recording. A small, optional override — e.g.
`EventGenerator(seed, scripted_events: dict[int, str] | None = None)` that
forces specific events at specific steps when provided, defaulting to
`None` (today's behavior unchanged) — would let the demo pack pin an
exact, reproducible order-effect run. **This is Tech C's design call**
(it touches `engine/events.py`, which Tech A does not own and this PR does
not modify); Tech A is not proposing a specific implementation, only the
need.

## 6. README "What's Real vs. What's Metaphor?" wording (proposal only, no diff)

**Current text** (`README.md` lines 119-120):
```
| **Quantum Circuits** | Planned | 2-qubit Qiskit 2.x circuits on the Aer simulator and fake backends, then IBM Quantum hardware. Not done yet: current runs use stubs. |
| **Decoherence Delay** | Planned | Circuits with qc.delay(...) idling to measure physical qubit decoherence as a function of simulated stress. Not done yet: the stub only mixes probabilities. |
```

**Proposed text**, once this PR (and Stage 6's circuit/fake-backend work)
lands:
```
| **Quantum Circuits** | Live decision path validated against real Qiskit circuits in tests; offline gate-level runs on Aer + fake-backend noise models (Stage 6) | The in-game decision path is a validated closed-form evaluation of the same unitary (see docs/tech-a/02-deliberation-unitary.md); it is checked against real `QuantumCircuit` execution in tests but does not build/run a circuit every decision, for speed. Offline scripts run actual gate-level circuits on Aer with a fake-IBM noise model. Nothing calls real IBM hardware. |
| **Decoherence Delay** | Offline experiment only (Stage 6); in-game stress uses an exact phase-damping channel, not a delay circuit | In-game, stress maps to an exact, verified phase-damping Kraus channel (docs/tech-a/04-stress-and-decoherence.md). A separate offline `delay(t)` experiment on a fake-backend noise model exists for Tech B's hardware job; it never runs live in the game. |
```

This is wording only — Tech C decides the final phrasing and makes the
README edit; Tech A does not touch `README.md`.

## Final check

```
$ SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py mind/tests
62 passed in 1.45s

$ git diff --stat tech-a/quantum-mind  (working tree, before commit)
 contracts.py           | 21 ++++++++++++++++++--
 engine/batch_runner.py | 54 ++++++++++++++++++++++++++++++++++++++++++++++----
 engine/gui.py          | 16 +++++++++------
 engine/simulation.py   | 15 +++++++++++++-
 4 files changed, 93 insertions(+), 13 deletions(-)
```

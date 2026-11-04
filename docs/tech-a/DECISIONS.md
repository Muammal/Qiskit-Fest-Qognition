# Tech A decision log

One entry per decision or deviation. Template from `TECH_A_BUILD_PLAN.md`
Section 6.

## Env-0: No existing git history; fresh local repo created (2026-11-03, stage 0, status: accepted)
**Context:** The working copy at `Qiskit-Fest-Qognition-pre-main` had no
`.git` directory at all — it is an extracted snapshot, not a clone. There
was no `origin/pre-main`, no commit `cccc781`, and no Python environment
with `qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`, `pytest` or `pygame-ce`
installed, even though all are pinned in `requirements.txt`. The build plan
(Section 7, Stage 0) assumes all of this exists. Per the plan's own rule
("if anything in the repo contradicts this file, stop and report... do not
pick one side yourself"), this was reported to Brodin before proceeding.
**Decision:** Brodin chose to `git init` in place, committing the existing
tree as the baseline (there is no prior history to inherit — commit
`7e6ac61`), then create `tech-a/quantum-mind` from that baseline. A `.venv`
was created (via `python3.12`, for broad Qiskit compatibility — the
machine's default `python3` is 3.14.3) and the exact pinned packages from
`requirements.txt` installed into it.
**Alternatives considered:** (a) locate a real clone with the actual
`pre-main` history and an `origin` remote — none was found on this machine;
(b) skip git entirely and just verify tests pass — rejected because Stage 5
needs a branch to open a PR from.
**Consequences:** "Baseline" for this work is commit `7e6ac61` wherever the
plan says `cccc781`. There is no `origin` remote; pushing a branch for
review (e.g. `agent-docs`, `tech-a/integration`) will need one added later,
which is Brodin's call, not something to do silently. All later "N tests
pass" / version claims in Tech A docs are run against this venv.
**Evidence:**
```
$ git init && git add -A && git commit -m "baseline: pre-main snapshot (no prior git history available)"
Initialized empty Git repository in .../Qiskit-Fest-Qognition-pre-main/.git/
7e6ac61 baseline: pre-main snapshot (no prior git history available)

$ python --version && python -c "import qiskit, qiskit_aer, qiskit_ibm_runtime; print(qiskit.__version__, qiskit_aer.__version__, qiskit_ibm_runtime.__version__)"
Python 3.12.12
2.6.1 0.18.2 0.51.0

$ SDL_VIDEODRIVER=dummy python -m pytest -q test_contracts_and_engine.py
31 passed in 6.96s
```
Installed versions match exactly the versions `TECH_A_BUILD_PLAN.md`
Section 7 cites for its prototype numbers (Qiskit 2.6.1, Aer 0.18.2,
qiskit-ibm-runtime 0.51.0).

## Env-1: CLAUDE.local.md untracked from git (2026-11-03, stage 0, status: accepted)
**Context:** `CLAUDE.local.md` (at `Tech A/CLAUDE.local.md`) does not match
any pattern in the shared `.gitignore` (no "plan", "role", "risk", "skill",
"tech_stack" or "techstack" in the name), and the team rule is that editing
`.gitignore` is not Tech A's call. It was swept into the initial baseline
commit by `git add -A` before this was caught.
**Decision:** `git rm --cached "Tech A/CLAUDE.local.md"` (kept on disk,
untracked from git), then appended `Tech A/CLAUDE.local.md` to
`.git/info/exclude`, exactly as Stage 0 task 5 specifies.
**Alternatives considered:** editing the shared `.gitignore` — rejected,
out of ownership.
**Consequences:** none to code; local-only housekeeping.
**Evidence:**
```
$ git rm --cached "Tech A/CLAUDE.local.md"
$ echo "Tech A/CLAUDE.local.md" >> .git/info/exclude
$ git status --short
D  "Tech A/CLAUDE.local.md"
```

## D0: Plan overrides team spec (2026-11-03, stage 0, status: accepted)
**Context:** `agents/TECH_A.md` on the `agent-docs` branch (not present in
this working copy — no such branch/remote exists here; description taken
from `TECH_A_BUILD_PLAN.md` Section 2) differs from the build plan in five
places.
**Decision:** The build plan wins in every case:
1. The decision dict uses the contract's key `"probs"`, not `"probabilities"`.
2. Two qubits give four basis states, not seven actions directly; use the
   protect/carry-on grouping (D1) and split within each group by prior.
3. Priors set the conditionals `q_S`/`q_D` and the within-group split; they
   are not encoded as R_y state-preparation angles.
4. Delay-gate decoherence is an offline experiment (`mind/experiments/`),
   never run live in the game — `RISKS_AND_FAQ.md` states "Sim never calls
   hardware live."
5. The order-effect demo uses `tremor` then `gas_plume` (volcano scenario
   events), not `storm` then `find_food`.
**Alternatives considered:** following `agents/TECH_A.md` — rejected on all
five points per the plan's explicit instruction that it wins.
**Consequences:** `mind/` is written against the build plan's design
throughout; no code should ever reference `"probabilities"`, a seven-outcome
measurement, R_y priors, a live delay circuit, or the storm/find_food order
pair.
**Evidence:** `TECH_A_BUILD_PLAN.md` Section 2, "Team spec conflicts."

## D1: Binary groups (2026-11-03, stage 0, status: accepted)
**Context:** Two qubits give four basis states, which must map onto the
7-action contract somehow. `TECH_A_BUILD_PLAN.md` Section 4.1 offers
PROTECT/CARRY-ON vs an earlier guide's act/wait split.
**Decision:** `PROTECT = ["hide"]`; every other action is CARRY_ON. In the
volcano scenario `hide` is the evacuation action, so "hesitation under
uncertainty" means a delayed evacuation — the documented wait-and-see
pattern this model targets.
**Alternatives considered:** act/wait (act = forage, drink, explore, craft,
build; wait = hide, rest) — rejected: it doesn't match the volcano
scenario's evacuation framing, and all of Section 4's math and the Stage
1–4 tests are written against the protect/carry-on split.
**Consequences:** `mind/config.py`'s `PROTECT` constant is `["hide"]`. The
U-matrix derivation (Section 4.3) and the 7-action split (Section 4.6) both
assume this grouping.
**Evidence:** Brodin's decision, recorded 2026-11-03.

## D6: eta / calibration (2026-11-03, stage 0, status: accepted)
**Context:** The interference-strength constant `ETA` needs a value and a
label defensible at judging. Section 4.3/4.8 and Appendix A recommend
`ETA = -0.7854`, an exact solve against Tversky & Shafir (1992)'s
disjunction-effect numbers (0.69 / 0.59 / 0.36), vs. fitting eta to other
data.
**Decision:** `ETA = -0.7854`, labelled explicitly as a calibration from
Tversky & Shafir 1992, not a fit. Transferring it from a gambling-choice
study to a volcano-evacuation scenario is an assumption stated openly.
**Alternatives considered:** fitting eta to other data — rejected: no
alternative dataset was identified, and it would trade one open assumption
(transfer across domains) for another (what data, what fit procedure)
without plan guidance.
**Consequences:** `mind/config.py`'s `ETA` constant stores the unrounded
exact-solve value `-0.7853897988344999` (solving
`p_protect_closed_form(0.5, 1, 0.69, 0.59, eta) = 0.36` exactly), so that
Stage 1's Tversky–Shafir test can check `P(0.5) = 0.36` to `1e-9`, not just
to the 4-decimal rounding `-0.7854` that `TECH_A_BUILD_PLAN.md` Appendix A
prints for human readability. `02-deliberation-unitary.md`'s "Questions a
judge might ask" states the cross-domain transfer assumption.
**Evidence:**
```
$ python3 -c "
import math
qS, qD, Ptarget = 0.69, 0.59, 0.36
kmax = math.sqrt((1-qS)*(1-qD)/(qS*qD))
kappa = (Ptarget - 0.5*(qS+qD)) / math.sqrt(qS*qD)
print(kappa/kmax)"
-0.7853897988344999
```

## D-QR: QR completion with det +1 (2026-11-03, stage 1, status: accepted)
**Context:** `u = U|safe,carry>` and `w = U|danger,carry>` are fixed by
Section 4.3's formulas, but that only pins down 2 of `U`'s 4 columns. The
remaining 2 columns, and the overall orientation (`det = +1` vs `-1`), are
unconstrained by the physics and need a concrete, reproducible procedure.
**Decision:** QR-decompose `[u, w, e2, e3]` (numpy `linalg.qr`, where
`e2, e3` are the standard basis vectors at indices 2, 3). Flip the sign of
`Q`'s first two columns if they come back negated relative to `u, w` (numpy
`qr` can flip a column's sign to make its leading `R` entry positive).
Then, if `det(Q) = -1`, negate column 3 only (never columns 0 or 1, which
must stay `+u, +w`).
**Alternatives considered:** Gram-Schmidt by hand on `e2, e3` — equivalent
to what `numpy.linalg.qr` already does; no reason to hand-roll it.
**Consequences:** `build_U` always returns an `SO(4)` matrix (`det = +1`),
which is what makes the $\le 2$ CZ-gate hardware compilation in
`06-circuits-and-hardware.md` possible (Vatan & Williams 2004). Columns 2,
3 of `U` have no physical meaning on their own — the decision qubit never
starts in `|protect>`, so those columns are never read from in-game; they
only matter for `det(U)` and for the gate-level circuit in Stage 6.
**Evidence:** `mind/tests/test_model.py::test_U_validity_random_sweep` (500
random `(q_S, q_D, eta)` triples, `max|U^T U - I| < 1e-10`,
`det(U) == 1` to `1e-9`) and `test_gate_circuit_matches_closed_form`.

## D2: Eruption and ash_fall (2026-11-03, stage 2, status: accepted)
**Context:** `eruption` and `ash_fall` are unambiguous threat evidence
(Section 4.4), unlike the ambiguous signs (`tremor`, `gas_plume`, etc.).
They need a belief update that can't be "wrong" in the way a rotation can.
**Decision:** Projective collapse onto `|danger>`:
`rho -> Pi rho Pi / Tr(Pi rho Pi)`, `Pi = |danger><danger|`. From any
starting belief this sets `x=y=0`, `z=-1` (`P(danger)=1`), and is
idempotent.
**Alternatives considered:** a large-angle rotation toward `|danger>` —
rejected: a fixed rotation can overshoot `|danger>` and rotate back toward
`|safe>` depending on the starting angle, which real unambiguous evidence
should never do. A collapse structurally cannot overshoot.
**Consequences:** `mind/belief.py`'s `apply_event` branches on
`COLLAPSE_EVENTS = {"eruption", "ash_fall"}` before consulting the
rotation-angle table. The Stage 6 gate-circuit version of the model can
only represent rotation-only event histories, since collapse is not a
unitary gate — documented in `06-circuits-and-hardware.md`.
**Evidence:** `mind/tests/test_belief.py::test_collapse_on_eruption_is_idempotent_and_certain`;
`03-events-and-order-effects.md` "Eruption collapse" walk-through
(`x=0, y=0, z=-1, P(danger)=1`, idempotent to `max|diff|=0.0`).

## D5: Stress map (2026-11-03, stage 3, status: accepted)
**Context:** Per-slot dephasing strength `lam` needs a function of the
agent's `stress` need. The engine's existing GUI (`engine/gui.py`
~1748-1753, 1897) already has its own decoherence-meter formula,
`(stress-0.4)/0.5`, which is a display-only overclaim Tech C must fix in
Stage 5; it must not silently diverge from whatever this model actually
uses.
**Decision:** `lam = clamp((stress-0.2)/0.7, 0, 1)`. The engine's agent
starts at `stress=0.15` (so `lam=0`, full coherence at game start) and
each sign adds roughly `0.08` to stress (`engine/agent.py`), so this
mapping reaches near-full dephasing only after several signs have
accumulated — matching the intended "stress builds up, then clouds
judgment" arc.
**Alternatives considered:** the team stub's `(stress-0.4)/0.5` — rejected:
reusing the team's existing meter formula might look consistent, but it
was never derived from the engine's actual stress dynamics, and Stage 5
must change the GUI meter to call this same function rather than keep two
divergent formulas.
**Consequences:** `mind/decoherence.py`'s `decoherence_strength(stress)`
implements this mapping. Stage 5's integration PR must point
`engine/gui.py`'s decoherence meter at this same function (see
`08-integration-notes.md`).
**Evidence:**
```
$ python -c "from mind.decoherence import decoherence_strength as d; print(d(0.15), d(0.85), d(1.0))"
0.0 0.9285714285714285 1.0
```

## D3: Decision rule (2026-11-03, stage 4, status: accepted)
**Context:** `decision_probs` gives a 7-action probability dict; something
must turn it into one chosen action. Section 4.7 offers `argmax` (matching
Tech C's classical/quantum stubs) vs Born-rule sampling.
**Decision:** Default `argmax(probs)`. A `"sample"` mode exists behind
`quantum_decide(state, decision_rule=...)`/`_decide`'s `decision_rule`
param, drawing from `probs` via the global `random` (reproducible per seed
since `SimulationEngine.step` isolates `random`'s state around `decide_fn`).
**Alternatives considered:** Born-rule sampling by default — rejected: it
would add sampling noise on top of the quantum-vs-classical-mixture
comparison, making Stage 7's batch statistics (survival rate, evacuation
delay) noisier and harder to attribute to the model rather than to RNG.
**Consequences:** `mind/config.py`'s `DECISION_RULE = "argmax"`.
`mind/tests/test_quantum_mind.py::test_determinism_seeded_run` depends on
this: two `SimulationEngine(seed=7, decide_fn=quantum_decide).run()` calls
must give identical action lists, which only holds with no sampling in the
default path.
**Evidence:** `mind/tests/test_quantum_mind.py::test_determinism_seeded_run` passed.

## D4: Reflex layer (2026-11-03, stage 4, status: accepted)
**Context:** `test_urgent_thirst_beats_warning_in_both_stubs` (the existing
repo suite) requires both `classical_decide` and `quantum_decide` to return
`"drink"` when thirst is critical, regardless of competing signals.
**Decision:** Keep Tech C's reflex layer, applied after the quantum rule:
`thirst < 0.3 -> drink`; else `warmth < 0.4 -> build_shelter` (if
`wood >= 2`) else `forage`. When it fires, the reason starts with
`"Reflex (<kind>) overrides <rule_action> -> <action>."`, and
`quantum.reflex` is set to `"thirst"` or `"warmth"` (else `None`) so later
analysis (Stage 7) can exclude reflex-overridden steps from the
quantum-vs-classical action-divergence count.
**Alternatives considered:** removing the reflex — rejected: breaks the
required repo test, and removes a documented, intentional "physiology
overrides deliberation" design point the plan calls out explicitly.
**Consequences:** `mind/quantum_mind.py`'s `_apply_reflex` runs after
`_choose_action`; `probs` is left as the quantum layer computed it (the
reflex changes only `action` and `reason`, not `probs`), so what the
quantum layer "wanted" is still visible in the logged decision even when
the reflex overrides it.
**Evidence:** `mind/tests/test_quantum_mind.py::test_reflex_thirst_overrides`
and `test_repo_compatibility[test_urgent_thirst_beats_warning_in_both_stubs]`
passed.

## D9: Integration edits (2026-11-03, stage 5, status: accepted)
**Context:** recorded on branch `tech-a/integration` (not this branch);
see that branch's `docs/tech-a/DECISIONS.md` and `08-integration-notes.md`
for the full entry. Summary: one PR on `tech-a/integration`, not merged
by Tech A, touching exactly `contracts.py`, `engine/simulation.py`,
`engine/gui.py`, `engine/batch_runner.py`.

## D7: Hardware decoherence (2026-11-03, stage 6, status: accepted)
**Context:** Stress-driven decoherence could either stay as the exact,
fast phase-damping channel used in-game (Stage 3), with real delay-gate
hardware physics explored only offline, or actual delay circuits could run
live during gameplay to compute decoherence from real/simulated gate
timing.
**Decision:** Exact phase damping in-game (already built, Stage 3); delay
circuits as an offline experiment only (`mind/experiments/delay_experiment.py`),
never called during a `SimulationEngine` step. Brodin confirmed this
2026-11-03, before Stage 6 began (matching what Stages 1-4 had already
built).
**Alternatives considered:** live delay circuits in the sim - rejected:
too slow for a real-time game loop (a single fake-backend circuit run
takes much longer than the <10ms/decision budget, Stage 4), not
reproducible run-to-run, and `RISKS_AND_FAQ.md` states the sim never calls
hardware live.
**Consequences:** `mind/circuits.py` and `mind/experiments/` exist purely
for offline verification and for producing `mind/results/hardware_circuits.qpy`
for Tech B's eventual hardware job - no code path from `quantum_decide`
ever imports or calls them.
**Evidence:** `mind/tests/test_circuits.py` (5 tests, including the
transpiled gate counts and the 4-SE fake-backend check);
`06-circuits-and-hardware.md`.

## D8: Library cross-check (2026-11-03, stage 7, status: accepted)
**Context:** `qcog` and `quantum-mind` are the two cross-check candidates
Appendix/Section 5 name, both flagged as October 2026 alpha packages.
**Decision:** Took the plan's own recommended default directly (optional,
time-boxed, no new dependency) without a separate stop-and-ask: the
plan's own Section 5 table already states the alternative ("make it a
dependency") as something to avoid, with no real second design path for
Brodin to weigh. `mind/experiments/validate.py`'s `library_cross_check()`
only *imports* `qcog`/`quantum_mind` in the current venv (no network
calls, no `pip install`) and records whatever happens.
**Alternatives considered:** making either package a hard dependency -
rejected per the plan; a full 45-minute exploratory session - skipped,
since neither package is installed or installable without adding an
unreviewed dependency outside `requirements.txt` (not Tech A's call to
add silently).
**Consequences:** `07-validation-report.md` Section 4 records the real,
negative result (`ModuleNotFoundError` for both) rather than a
fabricated comparison. If Brodin wants the full 45-minute exploration,
it can be done as a follow-up without touching the validated model.
**Evidence:** `docs/tech-a/07-validation-report.md` Section 4.

## Stage 9: overclaim audit (2026-11-03, stage 9, status: accepted)
**Context:** a fresh-context subagent (no access to this session's
reasoning) audited every file under `docs/tech-a/` and `demo-pack/tech-a/`,
plus `engine/gui.py`'s user-visible strings, against
`07-validation-report.md` and the hard rule against hardware/advantage/
real-decoherence claims, per the plan's Stage 9 instruction.
**Findings and fixes (in-ownership, applied directly):**
1. `01-model-overview.md` cited a stale `"62 passed in 1.45s"` (predates
   Stage 6's 5 circuit tests). Fixed to `"67 passed in 7.26s"` and the
   test-count breakdown, matching `07-validation-report.md`.
2. `demo-pack/tech-a/01-why-an-unsure-evacuee-waits.md` cited `0.356` /
   `0.631` (the curve's true numerical minimum, accurate but never pasted
   anywhere as a cited command+output) instead of the already-sourced
   `0.36` / `0.64` (`02-deliberation-unitary.md`'s `p=0.5` calibration
   values). Fixed to cite the already-sourced numbers.
3. `demo-pack/tech-a/03-stress-turns-quantum-mind-classical.md`'s `0.140`
   order-gap-at-lam=0 claim was accurate (independently reproduced by the
   subagent) but had no pasted command+output anywhere in `docs/tech-a/`.
   Flagged as a judgment call; closed by adding the citation to
   `04-stress-and-decoherence.md` directly in this session.
**Findings in `engine/gui.py` (out of ownership - not edited; reported):**
Three of four matched exactly what Stage 5's `tech-a/integration` PR
already fixes (line ~702 "real delay decoherence", line ~1419 "driving
real IBM quantum physical decoherence", the ~1748-1753/1897 decoherence-
meter formula) - the audit re-surfaced the same issues against this
branch (which doesn't have the unmerged PR's changes), confirming Stage
5's fix list was complete for what it covered. One new finding: the
section header at line ~1413, `"SIMULATION DYNAMICS & QUANTUM HARDWARE
SPECIFICATION"`, reinforces the hardware impression alongside line 1419.
Not in Stage 5's original fix list; relayed to Tech C via an addendum to
`08-integration-notes.md` on `tech-a/integration`, not touched here.
**Evidence:** subagent audit transcript (this session); `git diff` on the
two fixed files, reviewed before accepting.



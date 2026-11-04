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
**Consequences:** `mind/config.py`'s `ETA = -0.7854`. Stage 1's
Tversky–Shafir test (κ_max = 0.5588, κ = −0.4389, P(0.5) = 0.36) is the
evidence this constant reproduces the calibration source exactly; the
"Questions a judge might ask" section of `02-deliberation-unitary.md` must
state the cross-domain transfer assumption.
**Evidence:** Brodin's decision, recorded 2026-11-03.


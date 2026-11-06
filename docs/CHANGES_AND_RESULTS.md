# Changes and results

Everything done to align the repository with the Qognition paper, what came out, favourable or not, and what was not done. All results are model output, not predictions. No IBM hardware job was submitted: every "backend" result here is `FakeTorino` simulation.

## Read this first

- **The paper is not in this repository.** Paper Tables III and IV and claim labels C1 to C4 were not available to read. Numbers were checked against the values in the implementation prompt. The C1 to C4 mapping in [SENSITIVITY.md](results/SENSITIVITY.md) is an assumption and is labelled as one.
- **Default behaviour is unchanged.** The Phase 0 guard passes after every phase. The scenario table was regenerated at the end, and every number matches the first run exactly.
- **Several new results go against the paper's framing.** See the summary below and the paper edits at the end.

## Results at a glance

| Question | Result | Reading |
|---|---|---|
| Does hesitation cost survival when warning is short? | **No.** Pre-registered win test failed. Quantum minus mixture is +2.3 points at lead 0, and not significant at other leads | Claim not supported |
| Is there a quantum delay under the `sample` rule? | **No.** Quantum minus mixture is within ±0.08 steps at every lead, none significant | The +0.55 steps depends on the `argmax` rule |
| Does a tuned classical delay match the hesitation? | It **exceeds** it. Markov gives +1.57 to +1.97 steps on the default batch, against quantum's +0.55. In the sweep quantum hesitates less than Markov at every lead of 2 h or more | A one-parameter classical model produces the same kind of delay, and more |
| Is the default-batch delay from interference? | **Yes, on this batch.** With k forced to 0 the delay is -0.16, against +0.55 | Interference, not coherent rotation alone, gives the delay under `argmax` |
| Does quantum predict human data better? | **No.** Fixed η error 0.176, classical average 0.171, Markov held out 0.071 | The best rival is classical |
| Is Test 2's poor score a bug? | **No bug found.** Recovery is exact | It is the two-angle model's own limit |
| Does the Huang check pass? | **No.** D_b = -0.4855 against -0.942 | Open issue, factor about 1.94 |
| Is the delay robust? | Sensitive to the event angle scale; other constants are robust | See sensitivity |

## Phase 0: baseline guard

`mind/tests/test_paper_baseline.py` asserts all the listed numbers: P(protect) 0.36; order gap 0.140, 0.085, 0.043, 0.015, 0; p_danger 0.634 and 0.325; survival 99.5 / 99.5 / 100%; delay +0.55, SE 0.091, split 45 / 5 / 90. All reproduced first time. It lives in `mind/tests` so the standard test command runs it.

The signed gap (gas_plume then tremor, minus tremor then gas_plume) is -0.140. The paper reports the size.

One test was already failing before this work: `stranded_physics/core/tests/test_interfaces.py::test_timeline_keeps_every_existing_json_key`. Pack timelines lacked `world.scenario` and each step's `quantum`. Both are fixed.

## Phase 1: honesty and consistency

| Item | Change |
|---|---|
| 1. `library_cross_check` | Verdicts are computed against stated criteria. Huang now reports **FAIL**. The two external packages are stated as not run. Report regenerated |
| 2. Gates | Corrected to Ry and Rx in README and four docs. `docs/tech-a/*` was already right. `TECH_A_QUANTUM_MIND.md` also had a whole event table matching nothing in the code, now replaced |
| 3. README numbers | `tools/make_readme_numbers.py` writes [SCENARIO_NUMBERS.md](results/SCENARIO_NUMBERS.md), and the README links it |
| 4. GUI order-effect text | Computed at runtime from the mind |
| 5. GUI and FAQ | "Checked Against Qiskit" replaced. Hardware claims and placeholders removed from the FAQ |
| 6. Grover walk | Wired in behind `explore_walk="grover"`, off by default, tested. README says so |
| 7. `data/priors.json` | States plainly that the ATUS hours are not used, and that the mapping to survival actions was done by hand and not checked against the published table |
| 8. Titanic | "Two different Titanics" note in `ENGINE_STATUS.md` and `TITANIC_MODEL.md` |

**Different from the prompt:**

- **Item 4:** the old text, ".33, against .04", was hard-coded but not wrong. From the default start the computed gaps are 0.328 and 0.043. It is computed now anyway.
- **Item 5:** `RISKS_AND_FAQ.md`, `PLAN.md` and `TECH_STACK.md` were git-ignored, so these edits first existed only locally. They are now tracked, with exceptions in `.gitignore`.

## Phase 2: scientific work

Protocols were committed before each run, in [docs/protocols/](protocols/README.md). Disclosed exceptions: a small pilot for 2a on separate seeds, and feasibility checks for 2c. Each is described in its protocol.

### 2a. Lead-time sweep

[LEAD_TIME.md](results/LEAD_TIME.md), figure `docs/images/lead_time_sweep.png`, CSVs in `mind/results/lead_time/`. 288,000 runs: 60 seeds, 30 replicates, 8 leads, 4 distances, 5 arms.

- Survival is off the ceiling now: about 57% at lead 0, rising to 98.5% at 30 h.
- **The pre-registered win test failed.** It needed a significantly negative survival difference at a lead of 6 h or less. The largest difference is **positive**: quantum +2.3 points at lead 0 (interval +0.8 to +3.8, Holm p = 0.048). With p that close to the line, this should be read as "not worse", not as a benefit.
- **The delay difference from the mixture is null at every lead** (largest ±0.08 steps, Holm p = 1).

Limits: steps are 2 h, so the catalogue's median lead of 1.9 h sits at the model's resolution, and half the catalogue is below the shortest nonzero lead. Survival is to the end of a 72 h run with repeated flows, and sampled actions can walk a person back into a valley. In this setup every seed erupts and the first flow comes with the onset.

### 2b. Control arms

Default volcano, seeds 0 to 199, `argmax` rule (`mind/results/arms_batch.json`):

| Arm | Survival | Delay against mixture (steps) | Later / earlier / same |
|---|---|---|---|
| Quantum | 99.5% | +0.55 (SE 0.091) | 45 / 5 / 90 |
| No interference | 99.0% | -0.16 (SE 0.062) | 6 / 24 / 105 |
| Markov, h fitted (0.240) | 98.5% | +1.57 (SE 0.126) | 95 / 0 / 46 |
| Markov, h from T&S (0.4375) | 98.5% | +1.97 (SE 0.131) | 111 / 0 / 30 |
| Mixture | 99.5% | 0 | n/a |
| Classical argmax | 100% | -0.92 (SE 0.115) | 0 / 57 / 78 |

In the sweep, quantum differs from both Markov arms at Holm p < 0.05, in the direction of hesitating **less** and surviving more. So by the protocol's test quantum is distinguishable from a tuned classical delay, but this does not support a claim that hesitation is special to the quantum model. A classical model with one parameter hesitates more.

Quantum against `classical_no_interference` in the sweep: +2.3 points at lead 0, and +0.14 and +0.15 steps at 24 and 30 h. Nothing else is significant.

### 2c. Human data

Every row is in [HUMAN_DATA_RESULTS.md](HUMAN_DATA_RESULTS.md).

| Test 1, 7 scored rows | Mean absolute error |
|---|---|
| Markov, held out | **0.071** |
| Best classical, chosen after seeing the answer | 0.079 |
| Per-study η, leave-one-out | 0.132 |
| Superposed, leave-one-out | 0.169 |
| Classical average | 0.171 |
| Quantum, fixed η | 0.176 |
| Per-study η, in-sample (not a test) | 0.043 |

Per-study η and superposed beat both fixed η and the classical average on held-out rows, as the protocol defines a win, but both lose clearly to the one-parameter Markov rival. Two of seven studies need |η| > 1: Shafir & Tversky (-3.97) and Busemeyer et al. (-1.79). Fitted h ranged from 0.147 to 0.318.

**Test 2 audit:** [AUDIT_2026-11-06.md](../mind/human_tests/AUDIT_2026-11-06.md). **No convention bug, and nothing was fixed.** Exact tables from the independent `luders_sequential_probs` are recovered to a TVD of 3e-8. The poor score comes from the two-angle model forcing P(B yes | A yes) = P(B no | A no), which the data break, with fit gaps up to 0.354. `PRE_REGISTERED.md` is unchanged and the score stands.

**`qr_unitary_superposed`, built differently from the prompt.** One fixed superposed start cannot remove the Cauchy-Schwarz bound: `U|safe,s>` and `U|danger,s>` are still orthogonal, so the bound follows the new conditional rates. A test shows this. The built model ties the angle to belief coherence, `phi * |x|`, so a settled belief still gives q_S and q_D exactly. It reaches the Prisoner's Dilemma's 0.63, but that needs one fitted parameter, and reach is not evidence.

### 2d. Time-aware decoherence

`dephasing_mode="per_time"` and `dt_seconds` are in. Default `per_slot` is identical. Engines pass 2 h (volcano, island), 5 min (Titanic), 15 min (Pompeii) and `decision_seconds`, 60 s by default (Waterloo). Titanic and Pompeii decide every step.

| Scenario | `per_slot` | `per_time` |
|---|---|---|
| Volcano, 200 seeds | 99.5% | 99.5%, actions identical, as required |
| Titanic, saved | 578 (26.2%) | 705 (31.9%) |
| Pompeii, deaths | 0 | 0 |
| Waterloo, AEGL-2 or worse | 1 | 2 |

**The Titanic's 31.9% is close to the historical 32.3%, but this was not fitted and is not validation.** `tau` is set on a 2 h step that nothing validates, and it is one seed. The test against `delay_experiment.json` checks the form of the decay only. It does not link a cognitive tau to a qubit's T2.

### 2e. Sensitivity

[SENSITIVITY.md](results/SENSITIVITY.md).

- **`CF_SAFE_SAFETY` and `CF_DANGER_SAFETY` change nothing in the tested ranges.** They act only through a threshold at 0.3 in `get_prior`, so 0.90 to 0.99 and 0.01 to 0.10 give identical runs.
- **The delay is sensitive to the event angle scale.** At 1.2 it is +0.20 ± 0.24, which includes 0, and it moves non-monotonically (+1.07 at 0.9).
- `STRESS_FLOOR` and `STRESS_SPAN` keep the delay above 0 at every value, between +0.37 and +0.48.
- **The order gap changes sign with q.** With the paper's q of 0.69 and 0.59, tremor-first is 0.140 higher. Through the live mind, with q values from its priors, the same pair is -0.190. The size is robust, and the direction is not a property of the cues alone.

A bug in the script's first draft was caught by a unit test before the run. It is recorded as an amendment in the protocol.

## Phase 3: UI

| Item | State |
|---|---|
| 1. Resolution | `engine/hidpi.py` renders text at `round(size × scale)`. Fonts raised: body is 17 px at 1080p. Text colours pass 4.5:1 on both panels, by test |
| 2. Claims as visuals | `engine/gui_quantum.py`: quantum-against-control timeline, Bloch x-z path with |x| bar, order-swap button with ΔP, stress-to-λ dial. They replace the paragraph |
| 3. Cue translation | A/B/C/D selector on the Titanic, Pompeii and Waterloo config screens, wired to `event_mapping`, labelled as an assumption. Titanic has three options, Waterloo three, Pompeii four, matching the engines |
| 4. Scenario panels | Island vitals and actions replaced, using each engine's own action labels. "Not yet recorded." is gone |
| 5. One debrief | No mid-run cutscenes, `C` key removed. Title follows steps endured. Survival, survivors against deaths, paired result on the same seed, and a footer. |
| 6. Layout | Hub cards flow, so text cannot collide. Config rows re-spaced. `test_ui_layout.py` checks 1280×720, 1920×1080 and 2560×1440 |
| 7. 3D coverage | Dropped. The project is 2D only, and all 3D code was removed from every local branch |
| 8. Naming | "Qognition" in titles, caption, README and site. Internal `Stranded` strings stay |

**Different from the prompt, or limited:**

- **Item 1:** a full logical-unit rewrite of every draw call was not done. Text is rendered at final size, but shapes are still drawn at 1600×900 and scaled, integer nearest-neighbour first, then a smooth fit. Shapes are soft at non-integer scales such as 1.2, and text is sharp.
- **Item 5:** `engine/cutscenes.py` stays, because engines still emit scene requests and existing tests cover the player and skip. The GUI just never queues them.
- **Item 2:** the control line evaluates the mixture mind on the quantum run's own state at each step, not as a separate run, so both lines share one world.
- **Verification:** all UI checks and screenshots ran headless with SDL's dummy driver. **Nothing has been seen on a real display or projector**, and frame rate was not measured.

## End-of-event report

`engine/report.py` builds the report from a finished run, and the debrief shows its key events. **Export Report** (or `K` in the debrief) writes an Excel workbook and a folder of CSVs to `exports/reports/`, and `python main.py --report` does the same without the GUI. The tables are Summary, Key events, Timeline, Crowd over time, Groups, Decisions, Paired run and Assumptions.

## Sim files and the easier builder

The builder opens on starting points, with a checklist, undo, plain messages and an Advanced switch. `.qsim` files carry a scenario and seed to any copy of the app, and the community gallery publishes them through GitHub. See [SIM_FILES.md](SIM_FILES.md).

## Tests

The standard command gives 413 passed, 3 skipped (the 3 need `qiskit_ibm_runtime`, which is not installed here). `test_ui_layout.py`, `test_report.py` and `mind/human_tests` add 89 passed. The README had claimed 712, which matched nothing. New files: `mind/tests/test_paper_baseline.py`, `test_cross_check_verdicts.py`, `test_phase1_honesty.py`, `test_readme_numbers.py`, `test_extended_models.py`, `test_synthetic_recovery.py`, `test_time_aware.py`, `test_lead_sweep.py`, and `test_ui_layout.py`.

## Suggested paper edits

The paper was not edited, and could not be read here, so check each against its text.

1. **Survival.** Do not imply hesitation costs lives. Under short warning, sampled decisions and per-person variation, quantum is no worse than the mixture.
2. **Evacuation delay.** State that +0.55 steps is under the deterministic `argmax` rule. Under `sample` it disappears. Also state it is sensitive to the event angle scale.
3. **Tuned classical rival.** Report that one-parameter Markov hesitation gives a larger delay than the quantum model, and fits the disjunction data better on held-out rows (0.071 against 0.176).
4. **Interference.** The default-batch delay does come from the interference term (+0.55 against -0.16 with k = 0). This is a good result to keep.
5. **Order effect sign.** State that the direction depends on q_S and q_D: +0.140 at 0.69 and 0.59, and -0.190 through the live mind's q values.
6. **Counterfactual constants.** `CF_SAFE_SAFETY` and `CF_DANGER_SAFETY` are not sensitive parameters. Say they act only through a threshold.
7. **Test 2.** Explain that the loss comes from the two-angle model, and that the QQ equality is a weaker claim. It does not refute higher-dimensional models, and it does not support them either.
8. **Prisoner's Dilemma.** The bound of 0.836 cannot be escaped with a fixed superposed start. Any fix needs a condition-dependent start and at least one more parameter.
9. **Table III.** Keep Huang as FAIL, and add the factor of about 1.94 as an unresolved issue.
10. **Titanic.** Name `engine/titanic.py` as the implementation. Seed 42 gives 26.2%, so quote a seed or a range rather than "about 27%". Do not quote the `per_time` 31.9% as agreement with history.
11. **Cue translation (C6).** Pompeii deaths run 0, 0, 1,095 and 0 across translations, and only under C for quantum, so it is a strong demonstration.
12. **Precursor lead times.** Say the 2 h step cannot represent the catalogue's median lead of 1.9 h or below.
13. **Hardware.** Keep the wording to `FakeTorino` simulation only.

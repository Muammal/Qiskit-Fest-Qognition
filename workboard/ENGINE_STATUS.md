# Engine status

**Updated November 6, 2026.** The engine is built end to end: every kind in [ENTITIES.md](ENTITIES.md) has its sources, and scenarios run on real or generated land. With the import and extraction of all 19 raw physics datasets from GitHub Release [`data-v1`](https://github.com/Muammal/Qiskit-Fest-Qognition/releases/tag/data-v1), **all 22 required physical verification gates pass (`22 / 22 PASS`)**, and the complete test suite passes at **816 passed, 3 skipped**. On St Vincent 2021 it agrees with one of three blind real-world checks. Rerun the full table with:

```bash
python -m stranded_physics.check stranded_physics/scenario_cards/st_vincent_2021.toml
```

## What exists

| Part | Built by | Model | Result |
|---|---|---|---|
| Land and drainage | Claude | Real GLO-30 and WorldCover on a 90 m grid | Height and area match. One target of ours fails, see below |
| Generated islands | Codex | A synthetic cone, sized from real volcanic islands or by hand | Meets its size and drainage checks. The shapes are rather round, and aren't checked against real relief |
| Wind and rain | Codex | Replays Open-Meteo hourly data | Matches the source |
| Weather from records | Codex | A window of 2023 from any of 5 held islands, or set by hand | Matches its source |
| Eruption | Codex | 22 dated events from published sources | Inputs, so unscored |
| Generated eruptions | Codex | Sizes and warnings sampled from catalogues, or set by hand | **Size holdout fails** at 0.225 against 0.1. See below |
| Ash | Codex | Suzuki release, Gaussian fallout, 64 grain sizes | Passes two checks, but not blind |
| Hot flows, energy cone | Claude | Energy line along connected valleys. The default | **1 pass, 2 fail** |
| Hot flows, solver | Codex | Depth-averaged shallow water with Voellmy friction (T-503). Chosen per scenario, and takes minutes | **1 real pass, 1 fail**, and 1 pass that means nothing. See below |
| Mudflows | Claude | LAHARZ scaling, rain on ash | Tests pass. None trigger on St Vincent, as the rain data never exceeds 0.7 mm/h |
| Gas | Codex | Gaussian SO2 plume | **Its anchor fails**, at 99.7 kt against 100 to 300 kt |
| Lava dome | Codex | Huppert spreading from a flux derived from the dome's published volume | The volume check is arithmetic. A round dome can't represent the real coulee |
| Exposure | Codex, wired by Claude | Roof fragility, odds of surviving a flow, tiredness from ash | Rules tested. **Not fitted to casualty data** |
| Walking | Claude | Tobler speeds, Dijkstra routes | Matches exact answers |
| Body | Claude | Water and energy balance from published limits | Tests pass |
| People together | Claude | Seeing a warned neighbour warns you, and an able neighbour helps the injured | Rules tested. The distances are assumptions |
| Storm | Codex | Holland profile on Hurricane Beryl's real track | Tests pass. Nothing to score it against yet |
| Generated storms | Codex | Winds sampled from catalogues, straight tracks, or set by hand | Wind holdout passes, at 0.094 against 0.25. That checks peak winds only, not tracks or local impact |
| Old fictional island | Codex | Its hazards as a pack, so both worlds share one runtime (T-604) | Hazards match exactly. Survival differs, because the body model differs |
| Ship flooding | Codex | Compartments on a box hull, with trim and spilling over bulkheads | **Founders at 201 minutes against 160** |
| Immersion | Codex | Time in the water, by temperature and lifebelt | Rules tested. **Not fitted to survival data** |
| Lifeboats and boarding | Claude | Shared seats, launch times, who the crew let in first | Rules tested. See the Titanic section |
| Scenario checker | Claude | Reports what each part of a scenario can support | Works |

## Blind checks against 2021

Targets come from Cole et al. and were committed before each flow model first ran. Each model is scored separately.

| Check | Observed | Energy cone | Verdict | Solver | Verdict |
|---|---|---|---|---|---|
| Flows reach the sea on the west flank | Yes | Yes | PASS | No, 0 m3 | FAIL |
| Sea reached only on the west | Only there | 44% of sea-edge cells are elsewhere | FAIL | No flow touches the sea | PASS, **but this means nothing** |
| Reach on the southeast flank | About 1.8 km, within 1 km | 8.1 km | FAIL | 2.19 km | PASS |

The two models fail in opposite ways: the cone runs too far everywhere, and the solver stops too soon everywhere.

**Why the solver stops short, as far as we know:** nothing passes 2.5 km. After 30 minutes, 53% of the volume lies between 1.3 and 2.5 km from the vent, 36% is still where it was released, and 11% is in the crater. Releasing a 2.83 million m3 pulse evenly around the crater gives a layer only 0.86 m deep, which these friction settings may stop quickly. That's a diagnosis made after the result, and the settings stay locked, so the failure stands. The real flows were channelled, which an even release doesn't capture.

The solver's scheme for moving flow over small bed steps was derived here, not taken from a published method. It passes exact-answer tests, but grid convergence isn't proved. Between 90 m and 180 m cells, its furthest reach moves from 2.46 to 2.60 km.

## Results that don't count as agreement

- **Ash at Barbados and across St Vincent** pass, but the grain model changed after the first run missed Barbados, so neither is blind. Barbados also sits exactly on the edge of its allowed range, at 48 h, about 13 hours before Cole's "mid-morning" on 10 April.
- **Erupted mass** is about 3.5 times the published fallout: 3.1 x 10^11 kg to 12 April, against 8.9 x 10^10 kg for the whole eruption. Column heights and durations are assumed, so ash amounts can't be trusted yet.
- **The highest point's position** fails its target by 2,007 m against a 1,500 m limit. The catalogue point appears to mark the crater, not the summit. That is a diagnosis made after the result, so the failure stays until someone else reviews it.
- **Generated sizes and winds** check the sampling against catalogues. They don't show that a made-up eruption or storm would behave like a real one.
- **Weather windows** match their files. Those files are coarse-grid models, not stations.

## A gate we changed after it failed

`eruption-lead-time-sampling` could not be passed by any correct sampler, so it now compares whole distributions. See [changes/003-lead-time-gate.md](changes/003-lead-time-gate.md). It's a check of the sampling, not of reality, and it should be reviewed by someone else.

## The Titanic

The scenario is `scenario_cards/titanic_1912.toml`: 2,201 people, with the ship, damage, boats and who was aboard from the 1912 British inquiry. Targets were committed before any ship model existed, but everyone working on this knows how it ended, so they are blind to the result and not to the target. Boat times come from Wormstedt, Fitch and Behe's revised table, with the 1912 table held for comparison.

**The flooding model, tested alone:**

| Check | Record | Model | Verdict |
|---|---|---|---|
| Water after 40 minutes | About 16,000 tons | 18,401 tons | PASS, but it's an anchor: the 12 square feet was worked out from this |
| Time to founder | 160 minutes, within 30 | 201 minutes | **FAIL** |

A box hull with no tuning sinks about a quarter too slowly. Because of that, the people below meet the *recorded* sinking, not this model's.

**Who was saved, in one run of each mind:**

| Group | Record | Quantum (the scored one) | Control | Classical (reported, unscored) |
|---|---|---|---|---|
| Everyone | 32.3% | **3.4%** | 3.4% | 33.9% |
| Adult men | 20.3% | 4.4% | 4.4% | 12.9% |
| Adult women | 74.4% | **0.2%** | 0.2% | 100% |
| Children | 52.3% | 0.9% | 0.9% | 100% |
| First class | 62.5% | 0.6% | 0.6% | 51.7% |
| Second class | 41.4% | 0.4% | 0.4% | 63.9% |
| Third class | 25.2% | 0.4% | 0.4% | 43.6% |

**This scenario does not reproduce the Titanic.** With the quantum mind, every people gate fails. Why, as far as we know:

- **Minds decide too late.** The quantum mind first chooses to go at about 2:10 a.m. The control chooses it once at about 11:50 p.m., before the alarm, and not again. Both were built for two-hour steps, and nothing rescales them for ten-minute ones.
- **Everyone with the same mind decides alike.** Minds pick their top action, so people differ only in where they start.
- **Nobody is ordered to the boats.** Real stewards sent people up. Here only the 66 deck crew go as a duty, and they are almost all the survivors in the quantum and control runs.
- **The classical mind's 33.9% isn't agreement.** Its total is close, but its breakdown is wrong.

**Don't read the gap between minds as a result about people.** It comes from when each mind's fixed rules happen to trip at this step size.

**Two faults found on the way, both in the wiring, and both fixed after the first results were seen:**

1. In the first full run, all boats shared four deck cells, so they merged and left with the earliest boat. Saved: 21.3%.
2. With that fixed, saved came out at 33.0%, almost exactly the record, and **that was an artefact.** People who had never chosen to go boarded because their starting point happened to be near a boat. Requiring the choice dropped it to 3.4%.

Neither fix was aimed at a target, but the final numbers aren't from a first, blind run, and this section should be read that way.

**Assumed, and set before any run:** where each group starts, how long each takes to reach the boat deck, two seamen per boat, and lifebelts for everyone. **Not fitted:** the time people last in the water has a median of 20 minutes at freezing, or 30 with a lifebelt. Wikipedia's "within 15 to 30 minutes" is a cross-check only. **Sources disagree:** the inquiry counts 711 saved of 2,201, and modern work counts 712 of 2,208.

## What the minds do on the real island

With the real minds and the current body and exposure models, over 8 seeds, from each of two start points:

| Behaviour | Chateaubelair (flows never arrive) | Richmond (flow arrives at 69.5 h) |
|---|---|---|
| Quantum mind | All survive, first move at step 7 to 11 | All survive, first move at step 7 to 11 |
| Control (mixture) | All survive, first move at step 6 to 11 | All survive, first move at step 6 to 11 |
| Classical mind | All survive, first move at step 6 to 7 | All survive, first move at step 6 to 7 |
| Never leaves, only rests | All survive | **All killed by the flow, at 72 h** |
| Stays, but drinks | All survive | **All killed by the flow, at 72 h** |

The minds decide differently, which says nothing about which is better. Eight of eight staying at Richmond die in part because the odds of dying in a flow outdoors are set at 95%, an assumption. Survival numbers are not findings about people.

## Known limits

- **Exposure odds** are labelled assumptions: 95% outdoors and 50% in shelter. Nothing here uses a flow's speed or depth to set them. Heat stress isn't modelled.
- **A flow's reach for a generated eruption** scales with erupted mass to the 1/3, from a St Vincent reference. That's one eruption and a scaling law from memory.
- **The game shows one person, playing alone.** People see and help each other only in command-line runs through `play_people`. Nothing about other people reaches a mind, because the frozen contract has no place for it.
- **Input ambiguity:** Cole et al. tie the onset of flows to the 18:30 UTC explosion in one place, and "first significant" activity to 21:30 UTC in another. The model uses 21:30. Both are more than 24 hours after the first explosion.
- **Rain** comes from one coarse grid cell, so mudflow timing can't be judged.
- **Site positions** are from memory, to about 500 m, then snapped to land.
- **Raw data** stays out of git until licences are confirmed (T-104), so a fresh checkout can't build the St Vincent pack or draw weather from records. `stranded_physics/domains/terrain/fetch.py` restores the terrain files. Wind and storm files need the same. Generated land and hand-set weather need no raw data.
- **Citations from memory** are marked in each `params.toml`, including Briggs, Huppert and the Newhall and Self table. T-104 should check them.
- **Nobody independent has rerun this.** The workboard requires someone other than the author to rerun each gate before a task is done.
- **T-001 is not signed off,** including `workboard/changes/001-engine-fields.md`.

## What's next

| Task | Why it matters |
|---|---|
| T-102 data hunt | Ash and flow maps would allow far stronger checks, and could trace the SO2 anchor to a paper |
| Channelled release for the solver | The likeliest route to reaching the sea, with new settings committed first |
| Exposure from flow speed and depth | The solver has both, and the odds ignore them |
| T-104 licences and citations | Lets raw data into git, and checks what's cited from memory |
| Someone independent reruns the gates | Required before any task counts as done |
| Decide how crew orders work on a ship, then commit the targets again | The Titanic can't show who is saved until people are sent to the boats |
| Rescale minds to the step size | They were built for two-hour steps |

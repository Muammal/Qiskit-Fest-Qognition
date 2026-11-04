# Engine status

**Updated November 5, 2026.** The real St Vincent engine runs end to end, with simple models. It agrees with one of the three blind real-world checks it has been given. Rerun the full table with:

```bash
python -m stranded_physics.check stranded_physics/scenario_cards/st_vincent_2021.toml
```

## What exists

| Part | Built by | Model | Result |
|---|---|---|---|
| Land and drainage | Claude | Real GLO-30 and WorldCover on a 90 m grid | Height and area match. One target of ours fails, see below |
| Wind and rain | Codex | Replays Open-Meteo hourly data | Matches the source |
| Eruption | Codex | 22 dated events from published sources | Inputs, so unscored |
| Ash | Codex | Suzuki release, Gaussian fallout, 64 grain sizes | Passes two checks, but not blind |
| Hot flows | Claude | Energy line along connected valleys | **1 pass, 2 fail** |
| Mudflows | Claude | LAHARZ scaling, rain on ash | Tests pass. None trigger, as the rain data never exceeds 0.7 mm/h |
| Walking | Claude | Tobler speeds, Dijkstra routes | Matches exact answers |
| Storm | Codex | Holland profile on Hurricane Beryl's real track | Tests pass. Nothing to score it against yet |
| Scenario checker | Claude | Reports what each part of a scenario can support | Works |

## Blind checks against 2021

Targets come from Cole et al. and were committed before the flow model first ran.

| Check | Observed | Model | Verdict |
|---|---|---|---|
| Flows reach the sea on the west flank | Yes | Yes | PASS |
| Sea reached only on the west | Only there | 44% of the flow's sea-edge cells are elsewhere | FAIL |
| Reach on the southeast flank | About 1.8 km, within 1 km | 8.1 km | FAIL |

None of 9 energy-cone settings, tried for reporting only, passes all three. The fix is a better flow model (T-503), not retuning.

## Results that don't count as agreement

- **Ash at Barbados and across St Vincent** pass, but the grain model changed after the first run missed Barbados, so neither is blind. Barbados also sits exactly on the edge of its allowed range, at 48 h, about 13 hours before Cole's "mid-morning" on 10 April.
- **Erupted mass** is about 3.5 times the published fallout: 3.1 x 10^11 kg to 12 April, against 8.9 x 10^10 kg for the whole eruption. Column heights and durations are assumed, so ash amounts can't be trusted yet.
- **The highest point's position** fails its target by 2,007 m against a 1,500 m limit. The catalogue point appears to mark the crater, not the summit. That is a diagnosis made after the result, so the failure stays until someone else reviews it.

## What the minds do on the real island

With the real minds, over 8 seeds, from each of two start points:

| Behaviour | Chateaubelair (flows never arrive) | Richmond (flow arrives at 69.5 h) |
|---|---|---|
| Quantum mind | All survive, first move at step 7 to 12 | All survive, first move at step 7 to 12 |
| Control (mixture) | All survive, first move at step 6 to 12 | All survive, first move at step 6 to 12 |
| Classical mind | All survive, first move at step 6 to 7 | All survive, first move at step 6 to 7 |
| Never leaves, never drinks | Dies of thirst | Dies of thirst, before the flow arrives |
| Stays, but drinks (one seed) | Survives | **Killed by the flow at 72 h** |

The minds decide differently, which says nothing about which is better. Thirst, hunger and energy are placeholder rates, so survival numbers are not findings about people.

## Known limits

- **Input ambiguity:** Cole et al. tie the onset of flows to the 18:30 UTC explosion in one place, and "first significant" activity to 21:30 UTC in another. The model uses 21:30. Both are more than 24 hours after the first explosion.
- **Rain** comes from one coarse grid cell, so mudflow timing can't be judged.
- **Site positions** are from memory, to about 500 m, then snapped to land.
- **Raw data** stays out of git until licences are confirmed (T-104), so a fresh checkout can't build the St Vincent pack. `stranded_physics/domains/terrain/fetch.py` restores the terrain files. Wind and storm files need the same.
- **Nobody independent has rerun this.** The workboard requires someone other than the author to rerun each gate before a task is done.
- **T-001 is not signed off,** including `workboard/changes/001-engine-fields.md`.

## What's next

| Task | Why it matters |
|---|---|
| T-503 depth-averaged flow solver | The two failed checks |
| T-602 real physiology | Placeholder thirst currently kills before hazards can |
| T-603 exposure | Ash and heat don't affect the body yet |
| T-102 data hunt | Ash and flow maps would allow far stronger checks |
| T-403 gas, T-504 lava | Only stand-ins exist, and neither is in the real scenario |
| T-604 legacy wrapper | The `--engine` switch points at the real pack, but the wrapper isn't built |

# Titanic scenario model

A demonstration of evacuation behaviour using the existing mind. It is not a reconstruction of the sinking and does not make claims about real individuals. A tile is about 7 m, a step is five minutes, and the run covers 23:30 to 03:30 ship's time, or ends once nobody is left on the ship or in the water.

> **Two different Titanics.** This page describes `engine/titanic.py`, the crowd simulation the paper uses, which saves far more people; see [SCENARIO_NUMBERS.md](results/SCENARIO_NUMBERS.md) for its numbers under each cue translation. `workboard/ENGINE_STATUS.md` reports a different program, the physics-engine scenario `scenario_cards/titanic_1912.toml`, which saves 3.4% and fails every people gate. They differ in step size (5 against 10 minutes), boarding rules and how people are sent to the boats. Neither result should be quoted as the other's.

## Running it

```
python gui_island.py --scenario titanic --seed 105
python main.py --demo --scenario titanic --seed 105 --speed 0
python -m pytest test_titanic.py -q
```

In the GUI: click a person to follow them, press `F` for the next role, and `Q` to switch mind. There are no mid-run cutscenes: one summary film/debrief appears at the end, and Watch the Run Summary or `C` on the end screen replays it.

## Files

| File | Role | Modelled on |
|---|---|---|
| `engine/ship.py` | 40x40 cutaway grid, decks, stairs, compartments | `world.py` (`ShipWorld` subclasses `IslandWorld`) |
| `engine/flood.py` | Precomputed flooding, independent of decisions | `volcano.py` |
| `engine/lifeboats.py` | Boats, seats, launch times, boarding rules | new |
| `engine/crowd.py` | Head-counts, roles, five-minute `ShipAgent` | `agent.py` (subclass) |
| `engine/titanic.py` | Step loop and timeline export | `simulation.py` (same public methods) |
| `engine/gui_ship.py`, `engine/cutscenes.py` | Cutaway map and diagonal cutscenes | `gui_map.py` |

Existing files changed only to connect this: `engine/gui.py`, `engine/__init__.py`, `main.py`, `gui_island.py`. `mind/`, `contracts.py`, `simulation.py`, `world.py`, `agent.py`, `events.py` and `volcano.py` are unchanged.

## The mind

Everyone calls the same `decide_fn`. Its input is the frozen state contract, with no role field, so a role cannot change how anyone reasons. Roles set where a person starts, what they hear and when, and what an action does on the ship.

The mind raises `KeyError` on event names it does not know, so ship events reach it under existing names. The screen and timeline carry the real wording.

| Ship event | Mind event | Why |
|---|---|---|
| Collision, ship tilting | `tremor` | Ambiguous physical sign |
| Steward warning, crowd moving, crew orders | `gas_plume` | Ambiguous information, does not commute with `tremor` |
| Distress rocket | `ash_fall` | Collapses belief to danger |
| Told the ship will sink, water at feet | `eruption` | Collapses belief to danger |

This mapping is a modelling choice, and it shapes results.

Actions: `hide` heads for the boats, `rest` stays put, `forage` fetches a lifebelt, `build_shelter` moves indoors, `explore` looks around, `drink` stops for water, and `craft` helps nearby people. Role-specific wording is in `ROLE_ACTION_LABELS`.

Decisions are cached on the state fields the mind reads. It ignores `pos` and `day`, so identical inputs share one answer. `test_shared_decisions_equal_a_direct_mind_call` checks this against direct calls.

## Roles

| Role | Count | Differences |
|---|---|---|
| Passenger | 1,317 | Berths by class. Third-class single men forward, families aft (assumption) |
| Server / steward | 500 | Warn nearby cabins unless heading for the boats themselves |
| Engine room worker | 325 | Start lowest in the ship |
| Evacuation worker | 58 | Told early. Speed up loading at a boat station |
| Officer | 7 | As above, starting near the bridge |
| Captain | 1 | Told early. Never takes a boat seat (assumption) |

## Sources and how far they were checked

The Titanic inquiry site returned 403 to automated fetching, so its pages were not read directly. Crew department numbers come from search-result extracts of those pages.

| Fact | Value | Source | Status |
|---|---|---|---|
| Aboard and saved, by class and group | 2,208 and 712 | [Wikipedia casualty table](https://en.wikipedia.org/wiki/Sinking_of_the_Titanic), citing Encyclopedia Titanica | Read. The inquiry's totals differ: 2,201 and 711 |
| Crew departments | 66 deck, 325 engine, 494 victualling | [British inquiry](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepCrewpax.php) | Search extract only |
| Remaining crew counted as servers | 500 | Assumption | Makes the crew total 891, matching the casualty table |
| Boat launch times | See `BOAT_TABLE` | [Wormstedt revised table](https://wormstedt.com/Titanic/revised.html) | Read. The table calls its times approximate. Sides inferred from page layout |
| Standard and collapsible seats | 65 and 47 | [Museums Worcestershire](https://www.museumsworcestershire.org.uk/wp-content/uploads/2021/05/14.-Launching-the-Lifeboats.pdf) | Search extract only |
| Cutter seats | 40 | Not confirmed | Gives the 1,178 total widely quoted |
| Collision, boats uncovered, sinking | 23:40, 00:05, 02:20 | Wikipedia | Collision and sinking read. 00:05 from an automated summary |
| Loading order | 00:25 | Widely repeated | Assumption |
| Rockets | 00:47 onward, eight by 01:20 | Wormstedt; Wikipedia summary | Partly summary |
| Water temperature, survival in water | -2 C, 15-30 minutes | Wikipedia | Automated summary |
| Rescued from the water | About 40 | Wikipedia | Read. Used as a hard limit |

Every other constant is marked `assumption` in the code. These include the walking speeds, warning probabilities, loading rates, flood fill rates and the shape of the waterline between its timing anchors.

## Known simplifications

- Vertical and horizontal scales differ, so the waterline is shaped to meet timing anchors rather than calculated. Trim angle affects perception and cutscenes only.
- The ship stays level in the cutaway and does not break in two on the map.
- Boats leave at recorded times whoever has boarded, and do not return. Only collapsibles A and B take people from the water.
- Boarding is women and children first. Men board on the starboard side only, except as rowers (assumption, after Lightoller's reported policy).
- Locked gates, language barriers, family groups and the actual ages of passengers are not modelled.
- Warmth in a lifeboat cannot kill, so anyone in a boat counts as a survivor.
- Flooded tiles end at the deck rather than filling partial rows.

## Results

Ten seeds (1-10), after the fixes described above. Survivors are means except the range column. These numbers were not fitted to history, but the assumptions above were chosen by the same person reading the outputs, so agreement with history is weak evidence.

| Mind | Survivors: mean (range) | First | Second | Third | Crew | Chose `hide` | Chose `rest` |
|---|---|---:|---:|---:|---:|---:|---:|
| `quantum` | 608 (570-675) | 218 | 106 | 222 | 63 | 22% | 73% |
| `classical_mixture` | 600 (554-664) | 238 | 101 | 202 | 59 | 18% | 77% |
| `classical` | 840 (768-888) | 262 | 134 | 317 | 127 | 53% | 44% |
| History | 712 | 201 | 118 | 181 | 212 | n/a | n/a |

Reading these:

- **The gap between `quantum` and `classical` is not evidence for interference.** `classical_mixture` is the same pipeline with coherence removed, and it lands within 8 survivors of `quantum` on average, well inside the seed range. The larger gap to `classical` comes from a different decision rule: `classical` takes the argmax of the prior, which favours `hide` more often in this setting.
- **Crew survival is well below history** (63 against 212). The model has no mechanism that puts crew in boats beyond three rowers per boat.
- **Third class is above history under `quantum`** (222 against 181), which may reflect the missing barriers listed above.
- These are model outputs under stated assumptions. They should not be presented as findings about real behaviour on the night.

# Entities

The engine's reusable building blocks. An entity is one thing in a scenario: an eruption, a storm, a person, a shelter. You describe a scenario by listing its entities and their settings, and the engine builds it, runs it and reports what it can honestly support. No scenario should need new engine code.

## How a scenario is written

A scenario is a short file in `stranded_physics/scenario_cards/`. The in-game builder will read and write this same format, so there is only ever one way to describe a scenario.

```toml
id = "st_vincent_2021"
title = "La Soufriere, St Vincent, April 2021"
place = "real"
start_utc = "2021-04-08T00:00:00+00:00"
hours = 96
step_hours = 2
local_utc_offset = -4

[[entity]]
kind = "eruption"
source = "replay"
event = "st_vincent_2021"

[[entity]]
kind = "person"
source = "dials"
start_lon = -61.226
start_lat = 13.317
```

```bash
python -m stranded_physics.entities.build check <file>       # Is it well formed, and can it be built yet?
python -m stranded_physics.entities.build run <file> --seed 1
python -m stranded_physics.check <file>                      # What can it honestly claim?
```

## The in-game builder

The builder now opens on ready-made starting points that need no downloaded data, with **Advanced** for everything below. Sharing is in [SIM_FILES.md](../docs/SIM_FILES.md).

From the game's first screen, choose **Build your own scenario** or press `3`. Add entities from the left, click the map to place what's selected, change its settings on the right, then **Save** or **Play this scenario**. In play, `P` follows the next person, and `Q` changes the mind on the same world.

The screen draws from `KINDS` and every rule lives in `entities/draft.py`, so the screen and a hand-written file can't disagree. Saves go to `scenario_cards/saved/` and never overwrite a shipped scenario. Results belong to a scenario's id, so a changed copy of a shipped scenario shows none of the original's results, and it can't be saved until it has a new id. A generated island can't be saved with its place set to real.

## Where an entity's numbers come from

Every entity states its `source`:

| Source | Meaning | How it is checked |
|---|---|---|
| `replay` | A real recorded event | Directly against records of that event |
| `catalogue` | Sampled from real records, and any dial can override | Generated behaviour is compared with the catalogue's statistics |
| `dials` | Every value set by hand | Its models' own tests only. Nothing ties it to reality, and the checker says so |

Evidence never carries over. A pass on St Vincent says nothing about a generated eruption elsewhere.

## Kinds

| Kind | What it is | `replay` | `catalogue` | `dials` |
|---|---|---|---|---|
| `terrain` | The land | Built | Built: a generated island, sized from real ones | Built |
| `weather` | Wind, rain, temperature | Built | Built: a window of 2023 at one of 5 held islands, named by `what` | Built |
| `eruption` | Timeline, column, mass | Built | Built | Built |
| `ash` | Fallout from an eruption, and what it does to roofs | Built, needs an eruption | | |
| `flow` | Hot flows from an eruption. `event = "depth_averaged"` chooses the solver | Built, needs an eruption | | |
| `mudflow` | Rain on ash | Built, needs ash | | |
| `gas` | SO2 downwind | Built, needs an eruption | | |
| `lava` | A dome that grows until the first explosion | Built, needs an eruption | | |
| `storm` | Wind from a cyclone | Built | Built | Built |
| `ship` | Hull, compartments and decks. It is its own map, so it can't share a scenario with land | Built: the Titanic | | Built |
| `breach` | Where a hull is holed, how large the opening is, and when | Built: the Titanic | | Built |
| `lifeboats` | Seats, launch times, and who the crew let in first | Built: the Titanic, at revised or 1912 times | | Built |
| `sea` | Water temperature, and how long a person lasts in it | Built: the Titanic | | Built |
| `passengers` | People aboard, by men, women and children, with where they start and how long they take to reach the boat deck | | | Built |
| `person` | A body and a mind, at a start point | | | Built |
| `shelter` | A place to evacuate to. It lowers the odds of dying in a flow, and its roof can fail under ash | | | Built |
| `resource` | Food, water or wood at a place | | | Built |
| `group` | Many people with one mind, spread around a point | | | Built |

Hunger, thirst and energy belong to the body of each `person`, and their settings live in `domains/agent/params.toml`.

## Stages

| Stage | Result | Status |
|---|---|---|
| **1. Interfaces and replay** | St Vincent runs from a scenario file | Done |
| **2. Generated eruptions and storms** | An eruption or storm sampled from real catalogues | Built. The storm wind holdout passes. **The eruption size holdout fails**, at 0.225 against 0.1 |
| **3. Generated weather and land** | Weather from real records at any held island; generated islands | Built. Weather windows match their source, and generated islands pass the terrain checks they were given. Real relief isn't compared |
| **4. People, shelters, resources** | Many different people on one map, who affect each other | Built. Seeing a warned neighbour warns you, an able neighbour helps the injured, wood builds a shelter or a tool, and injuries heal. Their distances are assumptions |
| **5. In-game builder** | Pick and adjust entities on a screen | Built. The game shows one person at a time, playing alone, so people only affect each other in command-line runs |

## Ships

A ship scenario lists a `ship`, a `breach`, `lifeboats`, a `sea`, `weather` and its `passengers`, and uses `step_minutes` in place of `step_hours`, because a sinking takes hours. Run one with `python -m stranded_physics.entities.build run <file>`. The game window can't play one yet, and the builder's map doesn't show a deck.

A replay follows the recorded sinking, so people meet what really happened. A ship set by hand sinks as the flooding model says.

## Rules

- **A setting outside its valid range is refused,** never quietly clamped.
- **Unknown kinds, sources and settings are refused,** so a typo can't silently do nothing.
- **A source that isn't built yet says so,** and names its stage.
- **Every dial has a unit and a valid range.** Defaults come from `params.toml` or a catalogue, not from code.
- **Minds stay separate.** Entities describe the world and the body. Choosing actions belongs to Tech A and Tech B.

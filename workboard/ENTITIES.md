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

From the game's first screen, choose **Build your own scenario** or press `3`. Add entities from the left, click the map to place what's selected, change its settings on the right, then **Save** or **Play this scenario**. In play, `P` follows the next person, and `Q` changes the mind on the same world.

The screen draws from `KINDS` and every rule lives in `entities/draft.py`, so the screen and a hand-written file can't disagree. Saves go to `scenario_cards/saved/` and never overwrite a shipped scenario. Results belong to a scenario's id, so a changed copy of a shipped scenario shows none of the original's results, and it can't be saved until it has a new id.

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
| `terrain` | The land | Built | Stage 3 | Stage 3 |
| `weather` | Wind, rain, temperature | Built | Stage 3 | Stage 3 |
| `eruption` | Timeline, column, mass | Built | Stage 2 | Stage 2 |
| `ash` | Fallout from an eruption | Built, needs an eruption | | |
| `flow` | Hot flows from an eruption | Built, needs an eruption | | |
| `mudflow` | Rain on ash | Built, needs ash | | |
| `storm` | Wind from a cyclone | Built | Stage 2 | Stage 2 |
| `person` | A body and a mind, at a start point | | | Built |
| `shelter` | A place to evacuate to, which also prevents storm injury | | | Built. Doesn't yet protect from ash or flows |
| `resource` | Food or water at a place | | | Built. Wood isn't yet |
| `group` | Many people with one mind, spread around a point | | | Built. People don't yet see or help each other |

Hunger, thirst and energy belong to the body of each `person`, and their settings live in `domains/agent/params.toml`.

## Stages

| Stage | Result | Done when |
|---|---|---|
| **1. Interfaces and replay** | St Vincent runs from a scenario file | Its results match the hard-coded scenario exactly |
| **2. Generated eruptions and storms** | An eruption or storm sampled from real catalogues | Generated sizes, lead times and storm winds match the catalogues statistically, with targets set first |
| **3. Generated weather and land** | Weather from real records at any held island; generated islands | Weather windows match their source. Generated islands pass the terrain checks |
| **4. People, shelters, resources** (built, first version) | Many different people on one map; a storm-only scenario runs | Done: the runtime no longer assumes an eruption, and each person sees only their own state. Not yet: people interacting, or shelters protecting from ash and flows |
| **5. In-game builder** (built, first version) | Pick and adjust entities on a screen | Done: saving and reloading gives an identical file, and the game runs it. Not yet: the game shows one person at a time, and only St Vincent's land can be used until Stage 3 |

## Rules

- **A setting outside its valid range is refused,** never quietly clamped.
- **Unknown kinds, sources and settings are refused,** so a typo can't silently do nothing.
- **A source that isn't built yet says so,** and names its stage.
- **Every dial has a unit and a valid range.** Defaults come from `params.toml` or a catalogue, not from code.
- **Minds stay separate.** Entities describe the world and the body. Choosing actions belongs to Tech A and Tech B.

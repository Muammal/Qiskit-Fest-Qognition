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
| `person` | A body and a mind, at a start point | | | Built for one. Groups in Stage 4 |
| `shelter` | A place to evacuate to | | | Built as an assembly point. Protection in Stage 4 |
| `resource` | Food, water, wood | | | Stage 4 |
| `group` | Many people, who can differ | | | Stage 4 |

Hunger, thirst and energy belong to the body of each `person`, and their settings live in `domains/agent/params.toml`.

## Stages

| Stage | Result | Done when |
|---|---|---|
| **1. Interfaces and replay** | St Vincent runs from a scenario file | Its results match the hard-coded scenario exactly |
| **2. Generated eruptions and storms** | An eruption or storm sampled from real catalogues | Generated sizes, lead times and storm winds match the catalogues statistically, with targets set first |
| **3. Generated weather and land** | Weather from real records at any held island; generated islands | Weather windows match their source. Generated islands pass the terrain checks |
| **4. People, shelters, resources** | Many different people on one map; a storm-only scenario runs | Runtime no longer assumes an eruption. Each person sees only their own state |
| **5. In-game builder** | Pick and adjust entities on a screen | Saving and reloading gives an identical file, and the game runs it |

## Rules

- **A setting outside its valid range is refused,** never quietly clamped.
- **Unknown kinds, sources and settings are refused,** so a typo can't silently do nothing.
- **A source that isn't built yet says so,** and names its stage.
- **Every dial has a unit and a valid range.** Defaults come from `params.toml` or a catalogue, not from code.
- **Minds stay separate.** Entities describe the world and the body. Choosing actions belongs to Tech A and Tech B.

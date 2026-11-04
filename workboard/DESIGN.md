# Physics engine design

**Goal:** an engine we can defend when someone presses on it. Each claim traces to a source, a check and a stated range of validity. The claim is "verified and validated within a stated domain", never "correct".

**Island:** real St Vincent, checked against the April 2021 La Soufriere eruption. A made-up island has no real eruption to compare with.

**Status:** interfaces and fakes only. No real physics has been written yet, and no result from this code should be cited.

## How it fits together

```
categories (terrain, atmos, eruption, tephra, pdc, ...)
      |  share data only through Fields, with units and grids converted
      v
  ScenarioPack            one immutable file per scenario and seed, built offline
      |  read only
      v
  perceive()              what a person could notice, here and now, never the future
      v
  to_state()              exactly the frozen contracts.py keys
      v
  quantum or classical mind
```

- **Precompute, then play.** Real solvers can't run per frame. They run once when the pack is built, and the runtime only reads it.
- **The same pack hash means the same world for every mind.** That is what makes comparing minds fair.
- **Minds stay unaware.** `contracts.py` doesn't change. Elevation, wind and hidden phases never reach a mind.

## Categories

Each category is a complete component: data records, parameters, models, gates and tests in one folder. A category can hold data before it has a model. See [CATALOG.md](CATALOG.md).

Decision-making stays with the minds. Tech B's ATUS data stays in `data/`.

## Tiers

| Tier | Meaning |
|---|---|
| T0 | Fake or legacy wrapper, so nobody waits |
| T1 | Reduced-order, such as energy cone, LAHARZ, Suzuki |
| T2 | In-house depth-averaged solver, for PDC and lahar only |
| TX | External code, through a WSL file bridge. GPL code stays out of the repo |

A scenario chooses a tier per category. Verdicts attach per tier, so a T1 pass never covers T2.

## Scales

The air over a 10 km island is on the order of 10^37 molecules, and molecular dynamics reaches nanoseconds to microseconds rather than 72 hours. So we don't simulate molecules. Molecular knowledge enters through cited property tables and constitutive laws, such as water and air properties and melt viscosity. The island scale uses continuum and reduced-order models.

## Why not The Well

[The Well](https://github.com/PolymathicAI/the_well) is 15 TB of precomputed, idealised simulations for machine learning. Its listed datasets and docs show nothing on volcanoes or molecular scale, and it holds data rather than physical laws. It's a good benchmark if we want ML surrogates later, so we aren't downloading it now.

## Grids

- Hazards: about 90 m, in EPSG:32620 (UTM 20N), north-up, `[row, column]`, with row 0 at the northern edge.
- Mind tiles: 500 m over a 20 km northern window. 40 by 40 at 250 m can't hold the island.

## Honest verdicts

| Verdict | Meaning |
|---|---|
| PASS | Met a target committed before the run |
| FAIL | Missed it |
| INSUFFICIENT_DATA | The confidence interval straddles the bar |
| NO_TARGET | Nothing to compare with. Never counts as a pass |
| NOT_RUN | Not run, or inputs changed since |
| OUT_OF_DOMAIN | Inputs left the model's valid range. Blocks play |

Agreement counts only `prediction` values on `holdout` data. Inputs, anchors and calibrated values never count.

## What we learned from OptiSim

OptiSim had good honesty tools, but its evidence was thinner than its summary looked. This design fixes the specific gaps:

| OptiSim gap | Here |
|---|---|
| One citation per file | One `Parameter` per value |
| No data hashes or manifests | `DatasetRecord` with a hash and a bot-page check |
| Units were only labels | `pint`, converted and checked at every exchange |
| No conservation or grid-convergence checks | Required per category |
| "PASS" with no target | `NO_TARGET` |
| Agreement counted configured inputs | Only holdout predictions count |
| Compared with a paper's formula | Compare with measurements, and anchors are labelled |
| Validation never failed the build | `gates` exits nonzero, and CI runs it |
| Silent numerical fallbacks | `InterfaceError`, never a quiet fallback |
| Validity ranges not enforced | `check_validity` blocks play |

## Known limits

- This is weeks to months of work for students. The minimum honest product is terrain, atmos, eruption, tephra T1, pdc T1, lahar T1 and the adapter, end to end.
- Validation data may not be public. If isopachs and PDC polygons can't be found, tephra and PDC stay `NO_TARGET`, and the claim is "verified, not validated".
- GLO-30 is a surface model, so forest canopy raises narrow valley floors and can misroute flows.
- One eruption can't validate lethality or a mind. Expect `INSUFFICIENT_DATA` there.
- Benchmark citations in the task specs are from memory until each gate adds a checked locator.

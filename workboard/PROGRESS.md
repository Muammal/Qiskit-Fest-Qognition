# Progress

**Last updated: November 4, 2026.** Update this when something meaningful changes. Task-level status lives in [tasks.csv](tasks.csv).

## Where we are

| Track | Status | Next |
|---|---|---|
| Nov 6 demo, on `mohamed/tech-c-volcano` | Built and pushed, awaiting a hand-played run and team sign-off | Play one full run; agree `gui.py` with Muammal |
| Physics engine, on `physics/main` | Interfaces done. **No real physics yet** | Review and freeze the interfaces (`T-001`) |
| Real disaster data, in [`disaster_data/`](../disaster_data/) | Collected, checked and pushed, awaiting a separate full review | Review the facts; move them into category records (`T-101`) |

## Done

### Nov 6 demo (`269dcd2`)
- **Terrain and movement:** elevation-based island, drainage from the terrain, walking time from Tobler's hiking function, two assembly points.
- **Hazards:** wind-driven ash, recurring flows, a surge margin that injures, and lahars only while rain falls on ash.
- **Body:** eating, finite food and healing. Safety and stress now respond to an eruption.
- **UI:** relief map, hazard legend, run timeline, evacuation debrief and scrollable history.
- **Checks:** all 161 checks passed on two fresh sets of secret seeds, and all 60 tests pass.

Survival on erupting seeds, from those two runs:

| Strategy | Survival |
|---|---|
| Ignores the warnings | 0% |
| Leaves once it erupts | 68-75% |
| Gathers wood, then leaves | 95-100% |
| Leaves at the first sign | 99-100% |

These come from a calibrated model with assumed rates, and the rates were tuned so that decisions carry stakes. They are not findings about real people or real volcanoes. Both minds are still placeholder stubs, so comparing them shows nothing yet.

### Physics engine (`ac875bb`)
- **Interfaces:** every value carries its own source, units and valid range. Categories share data only through checked fields.
- **Fair comparison:** a precomputed pack means the same world for every mind. Tests confirm minds can't see future hazards, and that state keeps exactly the frozen contract keys.
- **Categories:** 14 created, including storms, earthquakes and tsunamis. All are empty until the data arrives. See [CATALOG.md](CATALOG.md).
- **Honest verdicts:** PASS needs a target committed before the run, and having no target never counts as a pass.
- **Checks:** all 43 interface tests pass, and the GitHub check passes.

Every model in this branch is a deliberate fake, so no result from it can be cited.

### Real disaster data (`T-100`, in review)
- **Collected:** 49 sources, including Smithsonian volcanoes and eruptions, NOAA events, tsunamis and earthquakes, the Brown et al. fatalities database, IBTrACS cyclones, Natural Earth, and Open-Meteo weather for 5 islands.
- **Written up:** 6 eruption case studies with 76 quoted facts, 2 real-event scenarios, and a [report comparing the engine with the data](../disaster_data/REPORT.md).
- **Checks:** all 48 data checks pass, including re-downloading sources and re-fetching every quote live. The headline figures were recomputed separately from the raw files and match. Only the St Vincent facts have been read by a reviewer so far, so a quote existing doesn't yet prove each fact is labelled correctly.
- **Licences:** 33 of 49 are not confirmed (`T-104`). Check them before republishing any of this data.
- **Raw files:** about 180 MB stays out of git. The manifest records each file's source and hash, and `tools/` can download them again.

## In progress

- **Full review of the case-study facts,** beyond St Vincent.
- **Filling the categories (`T-101`):** the data sits in `disaster_data/` for now, and the 14 categories stay empty until it moves into their records.

## Waiting on people

| Who | What | Why it matters |
|---|---|---|
| Mohamed | Play one full demo run by hand | No one has played the final build through |
| Mohamed and Muammal | Agree who owns `gui.py` | Our UI is 1280x760 and `main` is 1600x900, so merging will conflict |
| Muammal | Change the `noise_source` default on `main` from `"ibm_hardware"` to `"stub"` | It would label placeholder runs as hardware results |
| The team | Sign off on the new events and JSON fields | Needed before the demo reaches `main`. Old flow deposits no longer kill, which changes existing behaviour |
| Mohamed and friends | Review the interfaces (`T-001`) | Most coding tasks wait on this |
| Friends | Claim streams in [tasks.csv](tasks.csv) | Anything unclaimed falls to Claude |
| The team | Choose a repo licence | It decides whether GPL tools can ever be bundled |

## Known weak spots

- **Leaving early costs almost nothing in the demo.** Runs end at 72 hours, before scarce food matters, so leaving at the first sign is nearly always best.
- **Wood and shelter no longer affect survival much.** Cold deaths were removed because tropical night temperatures don't support them.
- **First-flow delay is an assumption.** We found no published statistic for it. In the 4 real cases that report a flow, it came more than a day after onset. The demo's model still allows immediate flows, which those selected cases neither support nor rule out.
- **Wind in the demo is seeded, not real.** Real data shows direction changes by event and by height, and 500 hPa alone isn't enough.
- **Exhaustion deaths aren't defensible.** The rule is inherited, and `T-602` replaces it.
- **Validation data may not be public.** 2021 ash and flow maps are the biggest question (`T-102`). If we can't get them, those categories can claim "verified" but not "validated".
- **The physics engine is weeks to months of work.** It won't be ready for Nov 6, and the demo doesn't depend on it.

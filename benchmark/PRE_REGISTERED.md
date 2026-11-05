# Benchmark: do our minds act like people in real disasters?

Committed on 5 November 2026, before any benchmark code exists and before any tuning. The targets are in `targets.csv`. **Nothing here changes after tuning starts.** If a mistake in a target is found, it's corrected in a new, dated commit that says why.

## Question

When our scenarios are run with each mind, how close is the share of people saved to what happened in real events the mind was never tuned on? And is the quantum mind closer than the classical one, given the same tuning?

A better score would show that this model predicts these events better. It wouldn't prove the model is right, or that minds are quantum.

## Events

| Events | Split | Why |
|---|---|---|
| 8 shipwrecks from 1852 to 1912, including the Titanic | Calibration | Tuning may look at these |
| 10 shipwrecks from 1914 to 2011, including the Lusitania and Canada's Empress of Ireland | Holdout | Scored only at checkpoints |
| Lusitania by class, crew and children, and Empress of Ireland by class and crew | Holdout | The same ships in more detail |
| Mississauga 1979: a chlorine evacuation in Ontario, with 0 deaths and about 218,000 people evacuated in under 20 hours | Holdout | The nearest real event to our Waterloo chlorine scenario |

The split is by date: everything up to 1912 is for tuning, and everything from 1914 is for testing, so the model has to predict later events from earlier ones.

The overall shipwreck figures come from Elinder and Erixson 2012, Table 1. It covers 18 wrecks, each with its survivors, its deaths, whether it sank quickly or slowly, and whether "women and children first" was ordered. Every row in `targets.csv` names its source.

### The Titanic moves from holdout to calibration

The Titanic's eight survival targets in `stranded_physics/domains/ship/gates.toml` were committed as holdout predictions. We have since seen the models' results on them, so they can no longer be an honest blind test. From now on they're calibration data. The gates file is left as it is, so this change is recorded here and not hidden.

### Events we couldn't use yet

- **Waterloo Region:** we found no real evacuation in the region with recorded survival or evacuation figures. Our Waterloo chlorine scenario is hypothetical and has no real outcome to score. Mississauga 1979 stands in for it.
- **Fort McMurray 2016:** about 88,000 people evacuated, but the engine has no wildfire hazard yet.
- **St Vincent 2021:** its evacuation figures haven't been sourced for this benchmark yet.

Events can be added later only as new holdout events, committed before they're first run.

## Every event says whether it can run

`status` in `targets.csv` is `runnable` or `needs_scenario`. Only the Titanic runs today. Each other event needs a scenario file built from our entities: the ship's size, compartments, boats, the time it took to sink, and who was aboard. Every value in a scenario comes from a named source, or is labelled `assumption`. Scenario files are committed before their event is first scored.

## What tuning may change

1. **Mind settings:** the interference strength `kappa_max`, the stress dephasing, the decision rule (`argmax` or `sample`), and the prior weights. The quantum mind's `ETA` stays fixed, because it was solved from an experiment.
2. **Shared, non-mind assumptions:** how long people take to reach the deck, how the crew fills the boats, and lifebelt use. These are tuned once, jointly, and are the same for every mind.
3. **Not tuned:** physics models, gates, pass marks and `contracts.py`.

Each change is a named setting, labelled `assumption`, and recorded in `benchmark/LOG.md` with the reason and the calibration score.

## Fairness

- The quantum, classical and classical-control minds each get the **same budget: 20 tuning runs** on the calibration events.
- **Bounds** for every event: everyone choosing perfectly (always heading for the boats when warned), and everyone choosing at random. The gap between them is how much a mind can move the result at all. If an event's bounds don't reach the real value, the miss belongs to the physics or the scenario, not the mind, and is reported that way.

## Score

- **Main score:** mean absolute error of the saved share, over holdout targets whose event can run, for each mind.
- **Also reported:** the calibration score, the error of each bound, and each event's error separately.
- Lower error wins. There's no combined score across different measures.

## Checkpoints

The holdout score is computed at most **three times**: (1) before any tuning, (2) once halfway through the budget, and (3) at the end. Every result is reported, whether it favours quantum or not, and the models aren't changed afterwards to improve the holdout.

## Behaviour, not only survival

Where records allow, the benchmark also compares behaviour, for example how full the Titanic's boats were when they left. These measures are added to `targets.csv` before they're scored.

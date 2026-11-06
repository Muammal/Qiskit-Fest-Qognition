# 2a: does hesitation matter to survival?

**Committed before the main run.** Code: `mind/experiments/lead_time_sweep.py`.

## Question

In the default volcano, margin is about 25 h and quantum delay about 1.1 h, so survival sits at its ceiling and hesitation cannot change it. If warning is short, does the quantum mind's hesitation lower survival against the mixture control?

## Arms

`quantum` and `classical_mixture`, on the same seed and replicate. The other arms are in [2b](2b_control_arms.md).

## Setup, all fixed

- Lead: 0, 2, 4, 6, 8, 12, 24, 30 h from first sign to first flow. Steps are 2 h, so shorter leads cannot be represented. `disaster_data/catalog/precursor_lead_times.csv` has median 1.9 h, quartiles 1.1 and 5.8 h, and 90th percentile 28 h.
- Start: the tile on the perennial valley nearest 4.2, 6.4, 8.9 and 10.8 tiles from the vent (a tile is 250 m). Every flow pulse uses this valley.
- Decision rule: `sample`.
- 60 seeds (0 to 59), 30 replicates per seed. Every seed erupts. The onset step is drawn from 16 to 21 and does not depend on the lead, and the first flow comes with the onset.
- Each person: trait stress offset from Normal(0, 0.10), added at each decision and clipped to [0, 1]; own eta from Normal(ETA, 0.15), clipped to [-1, 0]. Draws depend only on seed and replicate, so all arms get the same people.

## Metrics

- **Primary:** survived to the end of the run, averaged over the four distances, quantum minus mixture, at each lead.
- **Secondary:** survived the first flow; delay from first sign to first `hide`; share who never hid.

Uncertainty treats the seed as the unit: 95% percentile bootstrap over seeds, and a sign-flip test over seeds with Holm correction across the 8 leads.

## What counts as a win

A win for "hesitation costs survival" is a **negative** primary difference with Holm-adjusted p < 0.05 at any lead of 6 h or less. A positive or null result is a loss for that claim and is reported as such. Leads above 6 h are reported, but do not decide it.

## Pilot, disclosed

Seeds 5000 to 5004, 8 replicates, saved in `mind/results/lead_time_pilot/`. It checked that survival leaves the ceiling (about 58% at lead 0) and measured run time. The Markov arms in that pilot used an unset h, so they say nothing. One change was made after it: seeds went from 30 to 60, chosen from run time alone, because the job took under a minute. No lead, distance, distribution or metric was changed.

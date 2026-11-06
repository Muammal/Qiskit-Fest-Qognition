# 2e: sensitivity

**Committed before any run.** Code: `mind/experiments/sensitivity.py`.

## Question

How much do the headline claims depend on constants nobody measured?

## Design

One at a time, others at default. `ETA` is held fixed throughout.

| Constant | Values |
|---|---|
| `CF_SAFE_SAFETY` | 0.90, 0.95, 0.99 |
| `CF_DANGER_SAFETY` | 0.01, 0.05, 0.10 |
| `STRESS_FLOOR` | 0.1, 0.2, 0.3 |
| `STRESS_SPAN` | 0.5, 0.7, 0.9 |
| Scale on all event angles | 0.8, 0.9, 1.0, 1.1, 1.2 |

The scales avoid an angle of pi/2, which the model rules out.

## Metrics

Volcano seeds 0 to 99, default `argmax` rule: order gap for (storm, gas_plume, tremor) against (storm, tremor, gas_plume) at lambda = 0 from the default start, paired evacuation delay against the mixture, and survival.

## What counts as robust

A claim is robust if, at every value: the order gap stays the same sign and at least half its default size; the paired delay stays positive with its 95% interval above 0; survival stays within 2 points of the mixture. Otherwise it is reported as sensitive, and the constant that breaks it is named.

Claim labels C1 to C4 are the paper's. The paper is not in this repository, so the mapping used in the results table is an assumption and is stated next to it.

## Amendment, before the run

A unit test showed the first script read the order gap with q values that matched neither the paper nor the live mind. It now reports two columns: the paper's gap with q fixed at 0.69 and 0.59, and the same pair through the mind with its own q values. The robustness rule uses the mind's gap, because the counterfactual constants have no effect on the fixed-q gap. This was changed before any sensitivity run.

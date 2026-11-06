# 2c: human-data evidence

**Committed before `mind/human_tests/extended.py` was run.** `mind/human_tests/PRE_REGISTERED.md` and the scoring in `contest.py` are not changed.

## Audit of Test 2

The quantum predictor scored TVD 0.30 to 0.42 against classical 0.125. Check for a bug with a synthetic-recovery test: generate exact and sampled data from the independent `luders_sequential_probs`, fit angles on the first order only, and check the second order is recovered. A convention bug shows up as failed recovery on exact data. If recovery works, the code stands and the score stays as it was. Record the outcome in a dated note.

An exploratory run of this check on 300 exact tables was made while writing this protocol. It found no failure.

## New model: `qr_unitary_superposed`

The default unitary cannot go below `(a+b)/2 - sqrt((1-a)(1-b))`, which is 0.836 for the Prisoner's Dilemma against 0.63 observed.

A fixed superposed decision start cannot remove this: inputs `|safe,s>` and `|danger,s>` stay orthogonal under any unitary, so the same bound holds for the new conditional rates. The angle therefore depends on belief coherence, `phi * |x|`, so a settled belief starts at `|carry>` and gives q_S and q_D exactly. This feasibility was checked on `disjunction.csv` before this protocol was written. One global phi is fitted, with eta held at ETA.

## Per-study eta

For each scored study: the eta that would hit it, whether that is within ±1, and a leave-one-out prediction using the mean eta of the other six. `ETA` itself does not change.

## Markov rival

See [2b](2b_control_arms.md). Every split of the 7 scored rows into 3/4 and 4/3.

## Metric and win

Mean absolute error on the 7 scored rows, held out wherever a parameter is fitted. A variant beats fixed eta only if its held-out error is lower than fixed eta's 0.176, and beats classical only if it is lower than the classical average's 0.171. In-sample fits and reach are reported but are not wins. Tversky & Shafir stay unscored.

Every row goes in `docs/HUMAN_DATA_RESULTS.md`, favourable or not.

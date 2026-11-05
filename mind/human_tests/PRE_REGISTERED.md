# Quantum against classical, on published human data

Committed before the code that scores this was written or run. **Nothing here is fitted to the outcome, and every row counts, whichever theory it favours.** The quantum model's `ETA` stays at its value in `mind/config.py`.

These data were already published, and the author worked out some of the first table by hand before committing this. There is nothing to adjust, so that can't move a result, but this isn't blind in the way a new experiment would be.

## Question

When people decide, does our quantum model predict what they do better than classical probability, given the same information?

## Test 1: deciding without knowing (`disjunction.csv`)

People choose after a known outcome A, after a known outcome B, and with the outcome unknown. Both theories get the two known rates, and predict the unknown rate.

- **Quantum:** `p_protect_closed_form(0.5, 1.0, known_a, known_b, ETA)`.
- **Classical, equal information (the main comparison):** the average of the two known rates. Like the quantum model, it assumes even odds and has nothing to adjust.
- **Classical, best possible (reported too):** the law of total probability puts the unknown rate between the two known rates, for any odds. This gets the best weight for each row after seeing the answer, so it is deliberately generous to classical.
- **Score:** absolute error against the observed rate, averaged over scored rows.
- **Not scored:** Tversky and Shafir 1992, because `ETA` was solved from it.

## Test 2: predicting the other question order (`question_order.csv`)

The same two questions were asked in both orders. Both theories see only the first order, and predict the second.

- **Classical:** answers don't depend on order, so each pair of answers keeps its probability.
- **Quantum:** a two-dimensional model with projective measurement, as in `luders_sequential_probs`. Its two angles are fitted by maximum likelihood to the first order only. That first order can't fix the sign between the angles, so each sign gives a prediction. **The main score averages both signs,** and the better one is reported too.
- **Score:** total variation distance to the observed second order, averaged over all 13 data sets.
- All 13 count, including the seven from Boyer-Kassem et al. 2016, a paper arguing against these models.

## Test 3: each theory's own prediction, against sampling noise

- **Quantum's:** the QQ equality, q = 0, by a z test, at 5%, two-sided.
- **Classical's:** no order effect at all, by a chi-squared test of the two tables, with 3 degrees of freedom, at 5%.
- Report how many of the 13 each survives. No order effect implies q = 0, so classical's claim is the stronger one, and these aren't the same size of bet.

## How this will be read

- Lower mean error wins that test. There's no combined score, because the tests measure different things.
- A win here would show the model predicts these data better than this classical rival. **It wouldn't prove the model is right,** or that minds are quantum.
- Other classical accounts exist with more freedom, such as order-dependent Markov and noisy sampling models. They aren't tested here.
- Results are reported as they come out, and the model isn't changed afterwards.

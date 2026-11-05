# T-503: moving flow over unresolved bed steps

The second-round change corrects two causes of artificial trapping: a
surface-slope limiter could erase the outgoing depth at a change in terrain
slope, and hydrostatic face reconstruction could block an energetic shallow
flow at a rise taller than its depth. Terrain and physical settings are
unchanged. The original analytic tests are retained.

## Scheme and limits

For normal Froude number above one, limit depth directly instead of deriving
its slope from independently limited surface and bed slopes. At a bed step,
preserve normal discharge and Bernoulli head on the original admissible
subcritical/supercritical branch. Include the corresponding advective
momentum correction in the bed source. With insufficient specific energy
for that discharge, retain the hydrostatic reconstruction and let the
transient flux adjust the flow. See [README.md](README.md) for the equations
and the Audusse et al. hydrostatic reference. This hybrid extension is
derived here; it is not claimed to reproduce a published moving-water scheme.

No new physical settings, speed caps, terrain preprocessing or island
conditions were added. Existing numerical constants remain: velocity division
threshold 1e-12 m, CFL cap 0.45, draining safety 0.9 and three-cell work halo.
The only added diagnostic threshold is 1 mm for comparing trace reach.
SSPRK2 draining bounds preserve nonnegative depth without clipping or volume
renormalisation. Normal and transverse directions use the same operations.
No general entropy-stability or moving-equilibrium proof is claimed.

## Preserved baseline and controls

Measured before modifying the original solver:

| Quantity | Round 1 | Round 2 |
|---|---:|---:|
| Volume in release ring after 1800 s | 84.0530% | 35.7157% |
| Maximum reach, locked 0.1 m threshold | 1.567927 km | 2.461170 km |
| Maximum reach at 1 mm | 1.567927 km (review result) | 2.461170 km |
| Volume reaching sea | 0 m3 | 0 m3 |
| Southeast reach | 1.390771 km | 2.190888 km |
| Reached area | 4.0176 km2 | 5.2083 km2 |
| Absolute relative volume error | 9.873e-16 | 1.645e-16 |
| Solver steps | 2813 | 1704 |
| Measured pulse wall time | 99.326 s | 162.781 s |

Wall times above were measured with another verification process running;
they are not an isolated performance comparison. Both were below 5 minutes.
Round 2 final volume is 2,829,999.9999999995 m3 from 2,830,000 m3 released.
Final speed at depths at least 1 mm is 15.5743 m/s; peak recorded wet speed
is 22.4451 m/s. The sea-contact gate's off-west share is zero with zero
contact cells; that PASS does not establish correct coastal routing.

For the stated 1 m, 30 m/s, 5 m hollow on a 20-degree slope, using three
identical rows and no friction:

| Cell size | Baseline held above far edge | Revised held | Revised peak wet speed |
|---|---:|---:|---:|
| 90 m | 100% | 0.013006% | 246.989 m/s |
| 45 m | 30.7132% | 0.001784% | 248.163 m/s |
| 15 m | Not rerun | 0.000031% | 250.153 m/s |

The comparison uses the same 60 s horizon and geometry at every resolution.
New regressions also cover parameter variants, actual uphill steps in either
direction, cumulative uphill steps that exhaust available head, insufficient
energy at a barrier, slow pooling in an 8 m pit, and rotation with nonzero
initial momentum. The six preliminary barrier controls passed zero volume
past their far edge; the pit retained 88.03%, 98.52% and 99.64% for initial
speeds 2, 3 and 4 m/s respectively. The original 16 solver tests and all 14
new tests passed before the full checker run.

## Provenance

Runs use the prescribed project Python with `-X utf8`, from the worktree
root. Python 3.12.10, NumPy 2.5.4. Inputs and choices are deterministic;
the external checker independently chooses unseeded random controls.

SHA-256 of raw file bytes:

| Input | SHA-256 |
|---|---|
| Original solver | `322901d570d323c4b37bd151030ecb345e9303f8c7ba7cd9d7df73883f9a4193` |
| Revised solver | `7ceb2e4f7e6bc2ba2c6d8f5f6b4f80a2b624ea0dc8e240e173d4b303d036df7a` |
| Unchanged original solver tests | `d60ad94ac290f88b1d8138fe12ceecffa5e4fc26f57cdb9aad28dc573e1a5c12` |
| Unchanged params_t2.toml | `8592453eba47a37831b6c71086a61b12126526ce1588f8fe2791cc7850eb0357` |
| Unchanged gates.toml | `936c522524bafc712c00b363df54b0a2ecb7bc56f43cd439dc7af695273366fa` |

## Checker and gates

The prescribed `python -X utf8 ../evaluate_t2.py` finished with exit 0:
**56 checks, 0 failed**, including its full-project pytest run, randomized
analytic controls, both coarse hollow grids, bounded fronts, barrier and
pit controls. Its gate run took 1057 seconds, below the 1200 second limit.
The solver was frozen before inspecting these real-world verdicts.

| Gate | Verdict | Value |
|---|---|---|
| pdc-model | PASS | PDC tests |
| pdc-reaches-west-sea | PASS | 1 |
| pdc-sea-only-on-west | FAIL | 0.4405594406 |
| pdc-southeast-reach | FAIL | 8.137428368 km |
| pdc-first-flow-time | PASS | 69.5 h |
| pdc.records_and_units | PASS | Records and units |
| pdc-t2-solver | PASS | All 30 solver tests |
| pdc-t2-volume | PASS | 1.645446245e-16 |
| pdc-t2-reaches-west-sea | FAIL | 0 |
| pdc-t2-sea-only-on-west | PASS | 0; zero sea-contact cells |
| pdc-t2-southeast-reach | PASS | 2.190888035 km |
| pdc-t2-grid-sensitivity | NO_TARGET | See paired grid values below |

Paired grids: maximum reach 2.461169702 km (90 m), 2.603230874 km (180 m);
reached area 5.2083 km2 (90 m), 5.9292 km2 (180 m). This is a sensitivity
measurement, not a convergence demonstration. Solving the numerical hollow
fault does not make the locked dense-flow assumptions pass all holdouts.

Commands executed with the prescribed project Python and `-X utf8`:

```text
python -X utf8 -m pytest stranded_physics/solvers/tests stranded_physics/domains/pdc/tests/test_t2.py -q -p no:cacheprovider
python -X utf8 -m pytest stranded_physics/solvers/tests -q -p no:cacheprovider
python -X utf8 -m pytest stranded_physics/solvers/tests/test_energy_terrain.py -q -p no:cacheprovider
python -X utf8 ../evaluate_t2.py
python -X utf8 -m stranded_physics.gates run pdc
```

The first command established the unchanged 20-test baseline. The dedicated
solver and moving-flow runs passed 16 and 14 tests respectively. The full
checker then passed against the final solver. The separately requested final
gate command completed in **727.703 seconds**, with the same twelve verdicts:
eight PASS, three FAIL and one NO_TARGET. Its exit status is **1**, reflecting
the three holdout failures above; all verification gates pass. Only the gate
runner writes `domains/pdc/verdicts.json`. No commit or push was performed.

# Depth-averaged flow

`depth_averaged.simulate` advances cell averages of `(h, hu, hv)` with
unsplit HLL fluxes and hydrostatic reconstruction extended for moving flow.
Momentum points east (`hu`) and south (`hv`). The outer boundary reflects
normal momentum and transports exactly zero volume.

The reconstruction limits free surface and gravity-wave invariants with
Superbee and bed slope with MC. At a downhill thinning front, positivity
limits the free surface while retaining the terrain slope. Where the normal
Froude number exceeds one, it limits depth directly: a change in bed slope
must not set a fast flow's outgoing depth to zero. Subcritical cells retain
the surface limiter, including an exactly level lake with dry land.

Across a reconstructed bed rise, solve the steady normal-discharge and
Bernoulli relations `q*=h*u` and `h* + q*²/(2*g*h*²) = h + u²/(2*g) - rise`.
Use the original subcritical or supercritical branch of the cubic. Its
minimum specific energy is `1.5*cbrt(q*²/g)`. If the remaining head is below
that minimum, use the original hydrostatic state; flow must adjust or pool.
At zero velocity the relations reduce to hydrostatic reconstruction. The
momentum correction includes `h* u*² - h u²` as well as pressure, so passing
a rise costs head. Transverse velocity is carried through unchanged.

The hydrostatic base is [Audusse et al. (2004), *A Fast and Stable
Well-Balanced Scheme with Hydrostatic Reconstruction for Shallow Water
Flows*](https://doi.org/10.1137/S1064827503431090). The branch solve and
supercritical limiter here are a custom extension derived from the steady
shallow-water relations, not a reproduction of a published moving-water
scheme. No discrete entropy inequality or general moving-equilibrium
preservation proof is claimed. The HLL shock flux and hydrostatic fallback
remain dissipative; head conservation is a reconstruction property, not a
claim that transient solutions conserve mechanical energy exactly.

Time integration uses SSPRK2. The requested CFL is capped at 0.45; each
Euler stage also respects 90% of its conservative donor draining time. A
step is retried at half its duration if the second stage needs a tighter
bound. Negative depths are neither clipped nor globally renormalised.
Sinks are emptied in each stage, with the RK weights applied to the removed
volume. Friction follows the transport step: the nonnegative root of
`v_new + dt*g*v_new**2/(xi*h) = max(0, v_star-dt*mu*g)` scales both momenta
together. Friction is split at first order in time.

The velocity division threshold is `1e-12 m`; it never removes water.
Arrival times interpolate threshold crossings between accepted steps.
Maxima include initial conditions and accepted end states before sink
removal. Dry areas outside a three-cell halo are omitted from flux work;
the active rectangle includes every strictly positive depth.

Verification uses Ritter's dry-bed dam break, the planar Thacker bowl
oscillation, the accelerating frictional dam-break front, lake balance,
stopping, positivity, closed and sink volume budgets, and vector rotation.
Moving-flow regressions cover coarse-grid hollows, bounded fronts, an
uphill step in either direction, cumulative stair climbing, insufficient
head at barriers, slow pooling, and discharge/head reconstruction.
These checks verify numerical behaviour; they do not calibrate dense-flow
parameters or establish real-island physical accuracy. The PDC adapter
reads all physical settings from the locked `params_t2.toml`.

Run from the repository root:

```text
python -X utf8 -m pytest stranded_physics/solvers/tests stranded_physics/domains/pdc/tests -q -p no:cacheprovider
```

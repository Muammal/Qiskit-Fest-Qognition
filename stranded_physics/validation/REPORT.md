# St Vincent wind, eruption and ash handoff

Implemented 4 November 2026. No commits or pushes. Only the three authorized category folders and new validation files were changed; locked gates, datasets and category records are unchanged. Workboard tasks T-301, T-401 and T-402 remain untouched because that folder is locked. Claude's independent rerun/review remains outstanding.

## Delivered

- `atmos/model.py`: exact hourly UTC replay, km/h conversion, FROM-to-TOWARD bearings, completed-hour rain means, source checksum and coverage checks. No interpolation to future hours.
- `eruption/model.py` and `facts.csv`: 22 supported timed entries through 11 April 20:22 UTC, including the first 9 April 12:41 event. Arbitrary time axes, deterministic phases/events/columns, seeded run-up signs, Mastin inversion and MTT height.
- `tephra/model.py`: normalized Suzuki release, three grain classes, guarded Stokes settling for fine ash, assumed terminal speeds for other classes, vector wind interpolation, release-time wind snapshots and delayed cumulative Gaussian deposition. `load_at` supports points outside the hazard grid.
- `validation/st_vincent_ash.py`: dependency-ordered, scoped field coupling with seed 1; all three requested measurements.
- 14 category tests cover replay, invalid files, arbitrary event axes, precursor prefix reproducibility, physical scaling, quadrature, vector cancellation, fall-time causality, frozen winds, empty forcing and Suzuki quadrature convergence.

## Verification and gate results

Python: `D:/Projects/Quantum/qiskit-fall-fest-2026/qognition/.venv/Scripts/python.exe -X utf8`.
Working directory: this engine worktree. Run the checker with the supplied absolute `evaluate.py` path, then `-m stranded_physics.gates run atmos`, `eruption`, and `tephra`.

The locked checker exited 0: **74 checks, 0 failed**, including the full project test suite and randomized hidden axes/physical inputs. The initial run caught three CSV quote whitespace joins; those were corrected without changing facts or assumptions. The category tests separately reported **14 passed**.

| Gate | Verdict | Value |
|---|---|---:|
| atmos-model | PASS | 2 tests; no scalar |
| atmos-wind-200hpa-speed | PASS | 23.416666666666664 m/s |
| atmos-wind-200hpa-bearing | PASS | 70 degrees TOWARD |
| eruption-model | PASS | 4 tests; no scalar |
| eruption-plume-scaling | PASS | 0.2409999999999999 |
| tephra-model | PASS | 8 tests; no scalar |
| tephra-mass-balance | PASS | 3.9313227608482356e-9 relative error |
| tephra-barbados-first-ash | NOT_RUN | No threshold crossing; measurement exits 0 without a value |
| tephra-island-cover | PASS | 0.999089295722025 of land cells |

`NOT_RUN` is the locked runner's verdict for a missing scalar. Here the calculation did run and predicted no detectable Barbados arrival; this is a physical shortfall, not a validation success. Maximum Barbados load was 3.0031146360990785e-14 kg/m2, versus the requested 0.001 kg/m2 threshold. No parameters were adjusted after observing these holdouts.

On the default axis, 288 packets contain 194258936886.00314 kg released mass. Independent wide-grid quadrature integrates 194258936122.30856 kg of ultimate deposition. By the last frame, 141159126598.9525 kg has landed; the remainder is airborne. The budget includes ultimate deposition, not just the island or the finite scenario horizon. It checks Gaussian normalization and packet mass allocation, not whether the assumed eruption mass is realistic.

## Assumptions and their importance

Each constant is recorded in its category's `params.toml`; the comments give the reason. Exact unit conversions, analytic constants such as pi, Boolean state codes and array indexing are conventions rather than uncertain physical estimates.

| Choice | Value | Consequence / importance |
|---|---|---|
| Weather conversions | 3600 s/hour, 3.6 km/h per m/s, 180-degree rotation, 360-degree wrap | Exact conventions; wrong conversions would reverse transport or rescale it. |
| Weather sub-hour behavior | Reject axes off the hourly lattice | Avoids inventing unavailable forcing or using future hours. |
| Escalation time | 8 April 12:00 UTC | Date-only tremor/gas observations placed at noon as requested; up to about half a day of timing uncertainty. |
| Tremor and gas probabilities | 0.5 each per run-up frame, independent draws | Controls precursor percept frequency only; neither physical ash nor the timeline changes with seed. No measured probabilities supplied. |
| First column | 8000 m above vent | IPGP reports about 8 km without an explicit datum. Treating it as above vent is an assumption; Taylor reports a different satellite height. |
| Other columns | 12000 m above vent | Unmeasured event-specific surrogate; high importance for mass, release winds, travel and fall times. Not fitted to holdouts. |
| First column duration | 15480 s (4.3 h) | Taylor's lower visible-plume duration applied from Cole's seismic onset. Plume visibility is not the same as sustained vent emission; mass is sensitive to this proxy. |
| Other unresolved column durations | 1800 s | Half-hour assumption; Cole's RSAM spike durations were deliberately not treated as column lifetimes. Strongly affects mass and coarse-frame sampling. |
| DRE density | 2500 kg/m3 | Specified in task; mass scales directly with it. |
| Overlapping columns | Later active event supersedes older active height | Reduced-order single-column representation; does not add simultaneous separate plumes. |
| Release timing | Rate at frame k times dt, released instantaneously at k*dt | Uses only current forcing. Coarse time steps can miss short columns or overrepresent their duration. |
| Fine particle diameter and density | 20 micrometres, 2500 kg/m3 | Fine speed scales as diameter squared and density contrast; large influence on long-range travel and airborne residence. Dense spherical approximation. |
| Air properties | 1.2 kg/m3, 1.8e-5 Pa s | Held constant along descent; ignores altitude/temperature dependence. Fine settling scales inversely with viscosity. |
| Gravity and Stokes guard | 9.80665 m/s2, Reynolds limit 1 | Gravity convention has little local uncertainty; the guard excludes invalid coarse-particle use of Stokes law. |
| Coarser settling laws | Constant 0.5 and 5 m/s | Explicit assumed terminal-speed laws, not Stokes predictions. Shape and variable drag unresolved; high influence on arrival and range. |
| Grain mass fractions | Fine 0.3, medium 0.4, coarse 0.3 | Illustrative distribution, not measured. Loads are linear in fractions; high influence on distal versus local deposition. |
| Wind level heights | 10, 5850 and 12400 m | Fixed geometric anchors; pressure surfaces move. Wind above/below is held constant. Shear interpolation affects direction and speed. |
| Vertical datum | Release and wind heights use the task's common height coordinate | No vent-elevation correction is introduced; the pressure-level versus above-vent datum is a physical limitation. |
| Suzuki release shape | a=4, lambda=1 | Uncalibrated shape; affects which winds transport each mass fraction and when it lands. |
| Release quadrature | 12 equal-height midpoint bins | Numerical approximation, most important in strong shear. Tested mean-release-height convergence at 12, 24 and 48 bins; no claim of deposit-field convergence. |
| Diffusivity | 1000 m2/s, constant and isotropic | Spread scales as sqrt(diffusivity); point-load tails can change greatly. No umbrella spreading, aggregation, terrain interception or wet scavenging. |
| Packet winds | Frozen at release height and release frame | Requested approximation; no later wind changes along the trajectory. This matters over long fall times. |
| Mass quadrature | +/-6 sigma, 241 midpoint cells per dimension, centred on each packet | Independent from the island grid; approximately 4e-9 tail/truncation error. Ultimate deposition includes particles landing after the axis ends. |
| Detection thresholds | Barbados 0.001, island 0.01 kg/m2 | Requested thresholds, not observed sensitivities. They materially affect first arrival and coverage. |
| Validation seed | 1 | Reproducibility convention; affects only precursor signs. |

Mastin gives mass proportional to height^(1/0.241), approximately height^4.15: a 10% height increase gives about 49% more mass. This is an analytic sensitivity, not a completed uncertainty sweep. Scenario mass and ash maps should not be described as calibrated forecasts.

## Evidence and disagreements

The supplied Cole accepted text was read, and PDF Table 6 was independently checked with layout-preserving extraction (PDF pages 35-36). Quotes in `facts.csv` preserve wording with whitespace normalized so table line breaks cannot join tokens in CSV consumers. Some table passages contain the supplied extraction's watermark/column artefacts; the original files remain unchanged.

- Cole section 4 gives the first explosion at 12:41 UTC and the second at 18:59 UTC on 9 April. IPGP instead gives 14:45 local, equivalent to 18:45 UTC, for the second; the catalogue prefers Cole.
- Taylor section 3.1 gives first satellite visibility at 12:54 UTC and the second phase at 19:14 UTC. These are delayed observations, not extra explosions; Cole's onset times are retained.
- Taylor explicitly identifies a new pulse/phase onset at 04:54 UTC on 10 April. It is included as an additional supported timed event. Cole combines three early sustained-phase events without giving separate times; no unreported timestamps were invented.
- Cole Table 6 gives 21:20 seismic onset and 21:30 plume emergence on 10 April. The catalogue uses 21:20. The prose elsewhere mentions activity from 21:30 and inconsistently gives the first onset as 12:36; the explicit main account/table and task use 12:41.
- Cole's 18:30 UTC passage also says 16:30 local, an inconsistent conversion. The explicitly printed UTC value and Table 6 are used.
- Table 6 gives 20:22 seismic onset on 11 April but 20:20 plume emergence. The onset is retained; the two-minute inconsistency is not repaired silently.
- Cole's spike durations measure RSAM energy, not how long a plume emits ash. Taylor's visible-plume lifetimes also include rise/dispersal. Missing emission lifetimes remain explicit assumptions.
- IPGP's approximate 8 km first column and Taylor's roughly 13.11 km satellite solution differ in method and possibly height definition. No event-specific height has been scored or validated.

## Citations from memory

These original works were unavailable offline. Their equations were required by the task; metadata/locators below are explicitly from memory, not claims to have read them:

1. Mastin et al. (2009), https://doi.org/10.1016/j.jvolgeores.2009.01.008, height versus DRE volume-rate relation H_km=2 V^0.241.
2. Morton, Taylor and Turner (1956), https://doi.org/10.1098/rspa.1956.0011, stratified buoyant-plume height scaling H=5 F^0.25 N^-0.75.
3. Suzuki (1983), A theoretical model for dispersion of tephra, in Arc Volcanism: Physics and Tectonics, pp. 95-113; normalized release form [(1-z/H) exp(a(z/H-1))]^lambda. Bibliographic locator from memory; a and lambda are assumptions.

Read supplied sources: Cole doi:10.1144/SP539-2022-292, Taylor doi:10.5194/acp-23-15209-2023, IPGP summary and both Open-Meteo JSON files. Raw inputs were never modified or fetched. Upstream licence-confirmation fields remain false and locked; reading an article is not a licence audit.

## Limits and target doubts

- The Barbados absence is inconsistent with the supplied observation of ash on 10 April. The simplified release spectrum, frozen winds and diffusion have not reproduced distal arrival. `NOT_RUN` must not hide that result.
- The island-cover gate asks for at least 0.01 kg/m2 by the end of 10 April, while the IPGP statement says covered by 11 April and gives no measured load threshold. That gate is a stricter numerical interpretation of a date-only qualitative observation, not a verified isopach target. Its PASS does not resolve the discrepancy.
- `TIME` has 36 frames at 2-hour spacing: its last sample is 70 hours after the start, 10 April 22:00 UTC, despite the nominal 72-hour description. Validation uses this locked axis exactly. The separate timeline test includes the 96-hour endpoint and all supported later events.
- Short pulses may fall entirely between frame samples. The required instantaneous-column interface plus rate*dt release can alias the event mass severely; a future interface could carry interval-integrated mass explicitly.
- Coarse Open-Meteo weather is model forcing, not local observation. Weather anchor gates only verify replay. The plume-slope gate checks scaling, not measured column heights. All assumptions remain unchanged after holdout inspection.
- The mass residual is not finite-grid retained mass, and not mass landed by the final frame. Off-grid and late-arriving mass are included in ultimate analytic deposition.

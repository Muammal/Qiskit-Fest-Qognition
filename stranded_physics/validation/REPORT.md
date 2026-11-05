# St Vincent wind, eruption, ash and Beryl storm handoff

Updated 4 November 2026 after Claude's review. No commits or pushes. Baseline commit: `f1b072d780b8fa12b4edd06de3834f2a96a68dfb`. Only atmos, eruption, tephra, storm and validation files changed. Gates, datasets, category records and raw inputs remain untouched. Workboard task files are locked; this report records completion evidence without changing their status. Claude's code review remains outstanding.

## What changed

- Kept the hourly UTC weather replay, 22 timeline facts, Suzuki release and vector wind interpolation.
- Eruption mass now integrates each event's overlap with every completed frame interval, adds overlapping events, and reports the tallest overlapping column. Frame zero has no emission interval. All 11 explosion frames on the shared axis release mass; 17 frames have positive emission. The shared axis now emits 241093852924.44412 kg.
- Added `eruption.measure total_mass`: 48 samples span 8 April 00:00 through 12 April 00:00 UTC. Their spacing is 96/47 hours so the actual last frame matches the reported endpoint. Model mass is 309689788821.8786 kg, beside Cole's whole-eruption fallout comparison of 88750000000 kg. No `value` key or scored mass target is supplied.
- Replaced three fixed grains with a log-spaced spectrum, normal mass density in phi, truncated to [-4, 6]. The representative nodes include both endpoints; endpoint weights receive half a quadrature interval. Added Schiller-Naumann sphere settling; retained guarded Stokes settling.
- Kept release winds frozen at the release frame and release height. Interval mass is released at its right endpoint, so it never arrives early. `load_at` remains available off the hazard grid.
- Added grain convergence and explicit Barbados non-arrival reporting (`value=999`, `reached=false`, plus maximum load); maximum load is also included when reached.
- Removed conversion parameters in favor of named constants. Physical assumptions now use meaningful input ranges; numerical controls remain conventions. Atmos retains its existing cache size as a real numerical parameter.
- Added Storm T1, checksum-checked IBTrACS replay, complete-fix interpolation, great-circle distances, Holland winds, Kingstown peak and named-storm catalog rate. Categories exchange fields only; storm and tephra measurement modules import no other categories.
- Gaussian evaluation and its independent wide-grid mass quadrature use separability to reduce computation. The mass integral still samples the implemented Gaussian, rather than returning each packet's input mass.

## Verification and current gate results

Interpreter: `D:/Projects/Quantum/qiskit-fall-fest-2026/qognition/.venv/Scripts/python.exe -X utf8`; Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1. Working directory: this engine worktree. Seed 1 for scenario validation; ash and storm are deterministic.

The committed baseline's category tests were rerun before edits: 14 passed. Updated focused tests: 25 passed (atmos 2, eruption 9, tephra 9, storm 5). Tests check independent interval mass sums across steps and alignments, short overlapping pulses, sphere force balance over 50 diameters, track gaps, unit conversion, spherical geometry and named-storm deduplication. Existing causality, replay and Gaussian quadrature checks remain. Separate mocked CLI controls confirmed both reached and unreached Barbados JSON (including sentinel 999 and maximum load) and exit 1 for a missing terrain file.

The first updated checker run reported 121 checks with one failure: `atmos_has_parameters`, after exact conversions were removed. Its physics and gate checks passed. Retaining the existing cache-size control corrected that issue. The corrected checker exited 0: **121 checks, zero failures**, including the full project tests and randomized hidden axes/inputs. `CHECKER.txt` holds the complete successful log. After the checker, all four standalone `python -m stranded_physics.gates run <category>` commands exited 0. There are 11 PASS and three NO_TARGET verdicts, with no FAIL or NOT_RUN. `GATES.txt` records their commands and exits; `RUN_RECORD.json` records configurations, source hashes and the final values.

| Gate | Verdict | Value |
|---|---|---:|
| atmos-model | PASS | 2 tests, no scalar |
| atmos-wind-200hpa-speed | PASS | 23.416666666666664 m/s |
| atmos-wind-200hpa-bearing | PASS | 70 degrees TOWARD |
| eruption-model | PASS | 9 tests, no scalar |
| eruption-total-mass | NO_TARGET | 309689788821.8786 kg; whole-eruption comparison 88750000000 kg; axis ends 2021-04-12T00:00Z |
| eruption-plume-scaling | PASS | 0.2409999999999999 |
| tephra-model | PASS | 9 tests, no scalar |
| tephra-mass-balance | PASS | 3.9313313579827565e-9 relative error |
| tephra-grain-convergence | PASS | 0.00006666497463850544 relative change |
| tephra-barbados-first-ash | PASS | 48 hours; reached=true; maximum 0.18204575557846558 kg/m2 |
| tephra-island-cover | PASS | 1.0 of land cells |
| storm-model | PASS | 5 tests, no scalar |
| storm-beryl-peak | NO_TARGET | 42.63812758951193 m/s at 2024-07-01T15:00:00Z; closest sampled centre 75.53214107195339 km |
| storm-cyclone-rate | NO_TARGET | 1.0217391304347827 named storms/year; 47 distinct storms, 1980-2025 inclusive, radius 200 km |

The change-review script reported no fatal issues; its documentation suggestions are addressed here because parent README/DESIGN files are locked. Its zero line-count output was not used as a diff-size audit. Manual `git diff --check`, locked-record comparisons and current gate input hashes were checked.

The mass residual compares released mass with ultimate deposition on a separate +/-6-sigma analytic grid. It includes off-island and still-airborne packets; it is not a balance of mass landed on the finite island by the final frame. All three NO_TARGET results remain unvalidated measurements, not passes.

## Grain selection protocol and evidence

Cole section 3, Grainsize analyses, and Fig. 6 were checked before choosing the spectrum. They describe ~60 samples, size changes by unit, manual sieving to 125 micrometres and finer analysis, and peaks at 1 phi caused by aggregation in units U4/U6. They do not supply one eruption-wide normal median and spread. Local deposit peaks cannot identify a total emitted grain distribution.

Median 1 phi (0.5 mm before truncation) and standard deviation 2 phi were chosen as round assumptions, not inferred measured parameters or fits. The [-4, 6] bounds were specified by the task. Normal weights are renormalized after truncation.

Only the declared convergence metric was inspected during resolution selection: mean final land load at 64 versus 128 grains changed by 6.666497463850544e-5, or 0.0066665%. Default 64 was frozen before running the checker or reading either Barbados or island-cover results. No distribution, diffusion, height, duration or release-shape parameter was changed after those holdouts were observed. An initial run of the slower Gaussian implementation was stopped after the equivalent separable implementation completed; no physical parameter was changed to improve runtime or fit.

## Assumptions, ranges and importance

The following acceptance ranges are engineering bounds, not measured confidence intervals or proof of validity throughout each interval. No physical uncertainty sweep was performed. Source timestamps remain exact inputs; listed physical choices are `role="input"` in params.toml. Exact conversions, algebraic coefficients and state codes are code conventions.

| Assumption or convention | Value and accepted range | Importance and limits |
|---|---|---|
| Escalation timestamp | 8 April 12:00 UTC | Date-only IPGP tremor/gas placed at noon as required; about half-day timing ambiguity. |
| Tremor and gas probabilities | Each 0.5, range [0,1] | Independent per-frame run-up draws; seed changes only these percepts. No measured probabilities; do not infer probabilities per hour across different dt. |
| First column | 8000 m, [2000,25000] m | IPGP's approximate height interpreted above vent; datum ambiguity and satellite disagreement remain. High importance for mass and transport. |
| Other column heights | 12000 m, [2000,25000] m | Missing per-event heights remain uncalibrated surrogates. Mastin mass scales as H^(1/0.241), about H^4.15; +10% height gives about +49% mass. |
| First emission duration | 15480 s, [3600,21600] s | Taylor's lower visible-plume lifetime used as an emission proxy from Cole's onset; visibility is not sustained vent flux. Mass scales linearly with duration. |
| Unresolved emission durations | 1800 s, [60,21600] s | Round half-hour assumption; RSAM minutes were not used as emission duration. High mass sensitivity. |
| Second event duration | 34260 s; acceptance [18000,43200] s | Sourced continuous pulsatory interval in Cole, still a reduced-order constant column during that interval. The facts retain this measured interval. |
| DRE density | 2500 kg/m3, [1500,3000] | Task choice; mass scales linearly. Cole's stated DRE density elsewhere is 2.79 g/cm3, so the comparison uses the requested convention, not that value. |
| Within-frame release | Right endpoint; tallest overlapping column | Conserves interval mass and prevents early arrival. Delays true emission by up to dt; mixes simultaneous columns at their tallest height. Transport is not time-step independent. |
| Particle density | 2500 kg/m3, [500,3000] | Constant dense spheres; vesicular scoria, crystals, shapes and aggregates are unresolved. Strong fall-speed effect. |
| Air density | 1.2 kg/m3, [0.1,1.5] | Fixed through descent; altitude dependence ignored. Changes buoyancy and drag. |
| Air viscosity | 1.8e-5 Pa s, [1e-5,3e-5] | Fixed temperature approximation; fine settling roughly inversely proportional to viscosity. |
| Gravity | 9.80665 m/s2 | Standard-gravity convention; small local effect compared with grain uncertainty. |
| Sphere drag law | Schiller-Naumann: 0.15, 0.687; transition Re=1000; Cd=0.44 above | Required empirical law; shape and aggregation uncertainty remains large. The rounded branches leave a 0.39% drag gap at transition; the solver uses Re=1000 in that narrow no-exact-root interval. |
| Stokes guard | Re <= 1 | Retained validity check; the full spectrum uses the sphere solver rather than invalid coarse Stokes speeds. |
| Phi median | 1, [-3,5] | Round assumption; no eruption-wide fitted distribution. Strong control of local versus distal deposition. |
| Phi standard deviation | 2, [0.5,4] | Round assumption; strong tail and distal-mass sensitivity. A normal distribution in phi does not represent observed unit-dependent aggregation. |
| Grain support and resolution | Phi [-4,6], 64 nodes; allowed count [2,4096] | Task-defined truncated support (16 mm to 15.625 micrometres); sizes beyond the bounds are omitted and mass renormalized. Grain-only mean-land convergence is verified, not pointwise or vertical convergence. |
| Suzuki release | a=4 [0.1,20], lambda=1 [0.1,10] | Uncalibrated shape; chooses release winds and fall times. |
| Release height quadrature | 12 midpoint bins, [2,192] | Retained convention. Existing tests establish mean-height quadrature convergence, not full deposit-field convergence. |
| Diffusivity | 1000 m2/s, [10,10000] | Constant isotropic diffusion; width scales as sqrt(K). Point loads and tail arrival can change substantially. |
| Wind anchors | 10 m; 5850 m [5000,6500]; 12400 m [10000,14000] | 10 m is archive convention; pressure-level geometric heights are assumptions. Vector interpolation, with constant extrapolation, ignores moving pressure surfaces. |
| Wind history and height datum | Release-frame snapshot, common task height coordinate | No descent-time wind updates or vent-elevation correction. Strong shear and long flight times matter. |
| Budget quadrature | +/-6 sigma [4,10], 241 cells/axis [41,1001] | Independent sampled Gaussian integration; around 4e-9 omitted tail/numerical error. |
| Settling solver tolerance | 1e-12 Reynolds, [1e-14,1e-8] | Numerical precision; much smaller than physical-law uncertainty. |
| Ash thresholds | Barbados 0.001; island 0.01 kg/m2 | Requested conventions, not measured detection limits or isopachs. Direct effect on reported arrival and coverage. |
| Weather cache | 4 files, [1,32] | Memory convention; no effect on replay values. Hour-lattice rejection is retained. |
| Validation seeds and axes | Seed 1; shared TIME; Beryl 72 hourly samples | Reproducibility conventions; ash/storm do not depend on seed. The shared last frame is 70 h, Beryl's is 71 h. |
| Holland b | 1.5, [0.5,3] | Round uncalibrated radial shape; strongly affects Kingstown winds away from the maximum-wind radius. |
| Storm geometry | Spherical Earth 6371 km, [6350,6400] km | Task approximation; small compared with track/size uncertainties. Knot and nautical-mile conversions are named constants. |
| Kingstown site | (-61.227,13.158) degrees; lon [-61.3,-61.1], lat [13,13.3] | Task location, not an independently geolocated anemometer. Wind is a model estimate at this point. |
| Track representation | Linear latitude, longitude, USA_WIND and USA_RMW between complete fixes | Task-defined retrospective best estimate. Blank wind or radius fixes are dropped, possibly increasing gaps. Outside track times wind is zero. Symmetric cyclostrophic model omits translation, asymmetry, terrain, boundary-layer friction and gusts. |
| Catalog observation window | 1980-2025 inclusive; 200 km | Locally documented in calibration.json and disaster_data/REPORT.md. Includes zero-storm years; final incomplete archive year excluded. Radius is storm-centre proximity, not an impact zone. |
| Named-storm counting | Distinct SID, excluding blank/UNNAMED/NOT_NAMED/NONAME | Requested named-storm statistic. 47 named systems versus the local calibration's 51 all-system count. Lifetime names and winds cannot establish intensity at closest passage. |

## Evidence and disagreements retained from the reviewed first round


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

The following originals were unavailable offline. Equations were specified by the task, and comments label their provenance rather than claiming they were read:

1. Mastin et al. (2009), https://doi.org/10.1016/j.jvolgeores.2009.01.008, height versus DRE volume-rate relation H_km=2 V^0.241.
2. Morton, Taylor and Turner (1956), https://doi.org/10.1098/rspa.1956.0011, stratified plume scaling H=5 F^0.25 N^-0.75.
3. Suzuki (1983), A theoretical model for dispersion of tephra, Arc Volcanism: Physics and Tectonics, pp. 95-113; release function [(1-z/H) exp(a(z/H-1))]^lambda.
4. Schiller and Naumann (1933), VDI 77, pp. 318-320: sphere drag correlation. Bibliographic locator from memory; task-provided coefficients are labelled model conventions/assumptions in params.
5. Holland (1980), https://doi.org/10.1175/1520-0493(1980)108%3C1212:AAMOTW%3E2.0.CO;2, cyclostrophic radial wind profile. b is an assumption, not a measured Holland fit.

Inherited scenario coordinates also describe Barbados (-59.55,13.17) as an assumption from memory in the locked st_vincent.py. That is not a new source citation and was not independently surveyed.

Locally checked supplied sources include Cole doi:10.1144/SP539-2022-292 (grain-size text and DRE paragraph rechecked this round), Taylor doi:10.5194/acp-23-15209-2023, the retained IPGP/timeline evidence, Open-Meteo JSON, Beryl CSV and cyclone catalog plus local coverage metadata. No network or new document download was used. Locked licence-confirmation fields remain false.

## Remaining doubts and limits of targets

- The 96-hour mass is about 3.49 times the whole-eruption fallout comparison. Emitted magma and fallout volume are not identical quantities, and the time windows differ; nevertheless, an early total this large calls the height/duration surrogates into question. No retuning was done.
- Exact-onset boundary case: an event starting exactly at t_k has zero overlap with the ending interval, so its explosion flag can be 1 while interval mass/column remain zero until the next frame. Frame zero likewise has no mass even at an onset. Requiring both positive mass at every onset flag and the stated exact overlap formula is mathematically inconsistent in this case. The implementation follows the overlap formula; all actual scenario explosion frames have positive mass.
- The Schiller-Naumann piecewise rounding creates a narrow force-balance gap at Re=1000; the explicit limiting treatment is a numerical convention, not a physical discovery.
- Barbados now reaches the threshold at 48 h, the early edge of the 60 +/-12 h gate, and peaks at 0.182 kg/m2. This date-only success does not validate its load, source mass, grain spectrum or frozen-wind approximation. Threshold crossing is resolved only on the shared 2-hour frames.
- Island cover passes at the 70-hour final frame, but IPGP says the island was covered by 11 April and supplies no 0.01 kg/m2 isopach. The gate is a stricter numerical interpretation of qualitative text; it is not a measured deposit map.
- The mass reporting axis intentionally differs from locked TIME: 48 samples cover exactly 96 hours with both endpoints. TIME remains 36 samples at 2 hours, ending 10 April 22:00 UTC. Beryl's 72 hourly samples end 2 July 23:00 UTC. Closest Beryl distance is the minimum on that hourly axis, not a continuous closest-approach solve.
- Named cyclone rate is a retrospective catalog frequency, not landfall frequency, impact rate or a forecast probability. USA_WIND's local observation counterpart is absent, so storm peak is NO_TARGET.
- Broader validity, pointwise convergence, time-step convergence of ash transport, vertical release convergence, aggregation, scavenging and pressure-height corrections remain untested. Numerical passes do not establish a calibrated forecast or the user's personal reading milestones.

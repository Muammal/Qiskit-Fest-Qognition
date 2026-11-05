Ship and sea handoff — second round, 5 November 2026

The overflow solver now redistributes water directly between reservoirs and
cannot exhaust a relaxation budget. The five-hour Titanic benchmark took
1.49 s in the recorded run, below the requested 10 s. The physical inputs and
the foundering definition are unchanged. The 24-hour measurement finds the
modeled loss at 201.3666666667 minutes: the locked 160 ± 30 minute gate still
FAILS. No input was adjusted to improve a historical gate.

The measurement prints:

```json
{"value": 201.36666666666667, "water_tons": 70268.44109865467, "bow_draught_m": 28.219960873482712, "stern_draught_m": 11.87787776899288}
```

Water is in British long tons (1016.05 kg). These draughts and water mass are
from a second integration ending at the first foundering substep, rather than
the following output frame or the 24-hour endpoint. If no loss occurs within
24 hours, the output uses value 999.0 with foundered=false and diagnostics at
the horizon. A true foundering after 999 minutes would still print its actual
time, without the false flag.

Only the permitted ship/sea folders were used; gates.toml, datasets.toml and
category.toml were preserved. No commit or push was made. The sea implementation
was retained. Runtime, entities and scenario integration remain outside this
task. This report records completion evidence because the shared workboard is
outside the permitted edit scope.

The numerical change

Hull attitude is held during each spill, as before. Compartment storage floors
and bulkhead crests define barriers. At the highest barrier, the solver either
fills the connected reservoir to a common level or transfers only the volume
above that barrier into the adjacent lower reservoir, then processes its two
children. Each split reduces the number of compartments; there is no iteration
limit, recursive call stack, numerical volume cap or discarded excess. Emerged
storage floors also act as barriers. Tests independently check conservation,
nonnegative volumes, stable levels and decreasing gravitational energy.

The internal integration bound changed from 0.5 s to 2 s for speed. This is a
numerical setting, not a physical parameter. Exploratory checks at 0.5, 2 and
5 s retained the fixed physical inputs; 2 s was selected to retain accuracy
with ample runtime margin. The midpoint/exact-held-head ingress formula is
unchanged. The original spill tolerance and iteration-count records remain as
unused provenance. The reporting horizon changed from 10,800 to 86,400 s as
requested. Those are the only changed original parameter records; the two new
records supply the observed replay milestones.

The original solver was rerun before edits at 40 and 120 minutes. Results,
source and parameter hashes are in round2_baseline.json; original source,
parameters, report and verification metadata are preserved as round2_baseline_*
files. The original 120-minute run took 38.71 s. The review's five-hour >80 s
runtime and six-hour nonconvergence are review-reported failures, not additional
baseline reproductions claimed here.

| Quantity compared with original | 40 minutes | 120 minutes |
|---|---:|---:|
| Total water, relative change | -0.00000519% | -0.00609% |
| Largest compartment water change | 0.00000575% | 0.00818% |
| Bow draught, relative change | -0.00000186% | -0.00240% |
| Stern draught, relative change | +0.00000109% | -0.00183% |

All are within 2%; originally dry compartments remain dry at both checkpoints.

The recorded replay

`titanic_recorded_sinking()` returns **minutes after collision**, `(130.0, 160.0)`.
`Ship(..., recorded_sinking=(bow_awash_s, foundered_s))` instead takes seconds
after the axis start. For an impact away from the axis start, convert with
`tuple(impact_s + minutes * 60 for minutes in titanic_recorded_sinking())`.
Both values must be finite, nonnegative and strictly ordered; invalid values
raise InterfaceError.

The local British report, “FINAL EFFECT OF THE DAMAGE,” says the forecastle
head was “getting close down to the water, about half an hour before she
disappeared (1.50 a. m.)” and “The ship disappeared at 2.20 a. m.” These are
130 and 160 minutes after the 11.40 p.m. collision. Both passages are quoted
in the factory's comment and located individually in params.toml. The report
says the forecastle head was near the water, not already submerged: using that
observation as replay onset is explicitly a simplification. The advancing wet
front between the two times is a linear simplification, not an observed deck
flooding curve or a result of this box model.

With the record, submerged is zero before the first time, then marks deck-cell
centres west of the advancing front. At the first time the front is exactly
at the bow edge, so a grid with no cell centre on that edge has no wet cells
yet. At the second time every cell is 1 and afloat becomes 0. Until then afloat
is 1 even if the flooding model predicts otherwise. Water mass, impact and
alarm still use the original model/event rules. Without a record the existing
behavior is retained. Prefix and off-frame tests check the time rule.

Verification and limits

The original 28 tests remain, plus 19 new cases: 37 ship and 10 sea tests pass.
The new tests include nested sills and unequal storage, emerged floors, 200
random reservoir cases with an explicit RNG seed, baseline agreement, 24-hour
runs at 1/30/120 s, recorded replay direction/boundaries, physical loss before
recorded loss, modeled survival beyond recorded loss, preserved water mass,
causal prefixes, invalid records, and both measurement-output branches.

`python -X utf8 -m stranded_physics.domains.ship.verify_round2` passed 129
long runs: every integer output step 1–120 s for six hours; 24 hours at 1, 1.1,
7, 13.7, 30, 60, 119.9 and 120 s; and 30 s output through 21,600.25 s. It
independently accumulates committed ingress and measures each spill's volume
residual. Maximum accumulated mass error was 1.30857e-6 metric tonnes (about
1.31 g), below a 1e-11 relative budget tolerance. Maximum individual spill
residual was 1.16415e-10 m³. All arrays were finite/nonnegative and total water
was nondecreasing to rounding tolerance. First loss across those runs was
12,081–12,083 s; the default output step gives 12,082 s. This finite sweep does
not enumerate every real-valued step and horizon; direct finite splitting and
the independent internal step remove the former convergence dependency.

Raw results and environment/source fingerprints are in round2_verification.json.
That sweep preceded correction of the replay factory's return units; its exact
model is retained in round2_stress_model.py.txt. AST comparison confirms the
only subsequent model change was titanic_recorded_sinking, which the flood
solver does not call. Current-source fingerprints and final checker evidence
are in verification.json. The first second-round checker reported 163 checks
and one failure, the helper's seconds-versus-minutes return. That error was
corrected and the ship gates were refreshed. The final checker completed with **163 checks, 0 kinds failed, exit 0**
and `{"failed": []}`. All gate input hashes were then verified current.

Static quality checks passed with four warnings: the two required long API
signatures and two complexity warnings in the standalone verification runner.
The security scanner flagged the existing constant params.toml path as possible
path traversal; inspection shows it is derived from __file__ with a fixed
filename, with no user-controlled path. That is a false positive, not a claimed
clean scan. The git change analyzer misses the untracked first-version files,
so a direct comparison with the preserved baseline was also reviewed.

All current gate results

| Gate | Verdict | Value / evidence |
|---|---|---|
| ship.records_and_units | PASS | Clean exit |
| ship-model | PASS | 37 ship tests |
| ship-water-at-40-minutes | PASS | 18,400.54835234533 long tons |
| ship-foundering-time | FAIL | 201.36666666666667 minutes |
| titanic-saved-all | FAIL | No value; missing validation.titanic module |
| titanic-saved-adult_male | FAIL | No value; missing validation.titanic module |
| titanic-saved-adult_female | FAIL | No value; missing validation.titanic module |
| titanic-saved-child | FAIL | No value; missing validation.titanic module |
| titanic-saved-first_class | FAIL | No value; missing validation.titanic module |
| titanic-saved-second_class | FAIL | No value; missing validation.titanic module |
| titanic-saved-third_class | FAIL | No value; missing validation.titanic module |
| titanic-saved-crew | FAIL | No value; missing validation.titanic module |
| sea.records_and_units | PASS | Clean exit |
| sea-model | PASS | 10 sea tests |

The ship gate runner exits 1 for these retained FAILs; the sea runner exits 0.
The supplied checker allows the honest historical FAIL and the unfinished
scenario gates. No saved shares were measured. The water anchor is 15.0% high
and within its locked tolerance. Wilding inferred his aperture estimate from
roughly this water volume/time, so that PASS is not independent validation.

Retained records, assumptions and doubts

The first-version extraction and per-value locators remain intact. Registered
length is 852.5 ft, breadth 92.5 ft, draught 34 ft 7 in, and displacement 52,310
long tons. The 15 listed compartment lengths total 813 ft; the afterpeak is the
derived residual 39.5 ft with an empty CSV quote. D and E bulkheads use their
amidships 20 ft and 11 ft heights throughout; sheer is omitted. The chosen boat
deck is 58 ft from the steel-decks table; the dimensions table's approximately
60.5 ft at the accident is an unresolved datum discrepancy. Neither was changed.

The report names the forepeak, holds 1–3 and boiler rooms 6/5 as breached.
Wilding Q20422–20423 supplies the aggregate 12 ft² opening and about 25 ft head.
The six apertures remain split in proportion to compartment length, with no
claim of measured individual areas. Damage-extent descriptions of about 300 ft
(report) and 500 ft between extreme punctures (Wilding) are not used to invent
opening measurements. Boat capacity totals 1,178 across 20 boats. Eighteen
numerical departure times are marked as recorded; No. 7 follows the approximate
12.45 narrative (65 minutes), despite 12.46 in the table. D is the last davit
departure at 145 minutes. A/B at 150/155 minutes are filled assumptions between
D and recorded loss, not observed launches. The report itself warns about times.

| Assumption retained | Influence and limit |
|---|---|
| T1 constant beam, wall sides, horizontal compartment surface, storage floor at hole datum | Major. Hull taper and storage below the datum are omitted. |
| Permeability 0.85, range 0.1–1 | Major. Scales storage area and changes head/overtopping. |
| Cd 0.60, range 0.1–1, from memory | Major. Fixed-head inflow scales directly with Cd. |
| Density 1025 kg/m³, range 990–1040, from memory | Fixed-volume mass scales directly with density. |
| Gravity 9.80665 m/s², range 9.7–9.9, from memory | Inflow scales with its square root. |
| Length-proportional aperture split, exponent 1, range 0–2 | Major for trim/spill sequence; total stays 12 ft². |
| Amidships partition heights throughout, zero sheer marker | Potentially major for overtopping at the ends. |
| GML = L²/(12T) at initial T; trim moment divided by dry plus flood mass | Major box approximation; no free-surface stability correction. |
| Loss at first bow boat-deck contact OR exhaustion of full-box buoyancy, whichever occurs first | Fixed outcome definition; unchanged after results. Full volume is L × B × (T + deck height). The present loss is bow contact. |
| No pumps, doors, waves, damage growth, structural failure or breakup | Potentially major omissions; prevents a historical reconstruction claim. |
| Continue water bookkeeping after loss | Preserves the first event; later states are not a breakup model. |
| A/B scheduling at 150/155 minutes | Potentially major for later rescue results; no effect on flooding. |
| Flat deck terrain elevation 1 m | Field representation only; independent of physical freeboard. |
| Broad generic geometry/aperture/event/capacity domains | Input validation, not empirical ship data; displacement accepts every finite value ≥0. |
| 2 s internal bound, 10 s default output, 24 h horizon, 999 no-loss sentinel | Numerical accuracy, output resolution and censoring; not physical calibration. |
| Linear replay from near-water forecastle observation to recorded end | Major simplification of deck exposure; overrides only afloat/submerged. |

Sea choices are unchanged: freezing median 20 min (range 1–120), log-time spread
0.6 (0.05–3), warming rate 0.06 per °C (0.001–0.2), lifebelt factor 1.5
(1.01–10), freezing reference −1.9 °C (−3–0) and Titanic water −2 °C (−5–40).
These are labelled assumptions, not a fit. A +1 °C change multiplies median
by exp(0.06), about 1.062; a lifebelt multiplies it by 1.5. The freezing median
rescales all times, and spread changes the tails. At −2 °C the medians are
about 19.88 min without a belt and 29.82 min with one. No published 0 °C figure
is in hand. Cold shock and hypothermia are not separate hazards in this curve,
which is an unvalidated incapacitation-as-death proxy. The task brief supplied
the cold-shock warning, Tipton quotation and 10–40 minute swim-failure range;
no original Tipton publication was accessed.

Every citation from memory remains explicit: seawater density 1025, standard
gravity 9.80665, Cd around 0.60, seawater freezing around −1.9 °C, and Titanic
water around −2 °C. The report's 33/32 °F weather passage does not clearly
identify a water measurement. No new memory citation or network source was
introduced. Exact unit conversions are named constants. Passing numerical
checks establishes the checked calculations, not historical or clinical accuracy.

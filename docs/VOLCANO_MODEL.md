# Volcano scenario model

This is a synthetic evacuation scenario, not a calibrated forecast. One tile is 250 m; a step is two hours and the default horizon is 36 steps (72 h). The fixed MAP_SEED produces one island. Run seeds change events and the hidden volcano, never terrain. Decisions belong entirely to the supplied mind policy. The bundled quantum-labelled and classical policies are explicit Python stubs; no circuits, hardware jobs or measured decoherence are produced.

## Evidence and access limits

The following sources were supplied in the task. No network was used, so these references were not independently opened or verified here.

- [Phillipson & Gottsmann abstract](https://theghub.org/resources/2435): about two thirds of reported unrest episodes erupt in the short term. Access basis: supplied search summary, not full text. This is a broad prior, not an island-specific estimate.
- [USGS prediction FAQ](https://www.usgs.gov/faqs/how-can-we-tell-when-volcano-will-erupt): unrest can fade, with increasing felt earthquake frequency/intensity and steaming before eruptions. The model emits tremor and gas-plume signs, never animal warnings.
- The supplied 15-minute-to-13-day lead-time range over 21 eruptions is an **unconfirmed search-summary claim**, not a verified primary result. Two-hour time bins cannot resolve a 15-minute warning. The onset distribution below is an assumption, not a fit to that claim.
- [La Soufriere 2021 chronology](https://en.wikipedia.org/wiki/2021_eruption_of_La_Soufri%C3%A8re): supplied analog: swarm on April 5, evacuation order April 8, explosion April 9 at 08:41. We simulate final escalation only; time compression is an assumption.
- Cole IUGG abstract (supplied summary) and [USGS data release](https://data.usgs.gov/datacatalog/data/USGS:65baeb12d34e18c6baf2df6c): first flows around 30 h after onset, valley routing, explosions about 48 h, lahars lasting months. This single case anchors one delay only.
- [Geology.com volcanic hazards](https://geology.com/volcanoes/volcanic-hazards/): deadly PDCs can exceed 50 mph and cannot be outrun. A whole footprint activates in one step; an occupant is killed before movement, so a policy cannot outrun an arriving flow. Lava permits movement away before end-of-step collision checks.
- [USGS lava speed](https://www.usgs.gov/news/volcano-watch-how-fast-does-hawaiian-lava-flow): most lava fronts below 0.15 m/s; the model adds at most two adjacent cells per step (at most about 0.069 m/s along a path). Lava blocks routes and is lethal only if occupied at step end.
- [FEMA/UW water advice](https://mitigate.be.uw.edu/wp-content/uploads/sites/37/2017/05/hgwatersupply.pdf): ash increases stream turbidity and unpalatability; rainfall remobilises ash. Dirty stream water reduces thirst relief and morale, without poisoning.

## Hidden process and event ordering

The volcano precomputes every phase, sign and overlay for the whole horizon before any decisions. Erupting seeds follow unrest, escalating, erupting; false alarms follow unrest, fading. Early sign distributions overlap. Only recent events enter the mind state; hidden phases and future hazards are exported for replay/audit, never passed to the mind.

Weather follows a persistent Markov chain. The same weather drives rain-triggered lahars. Cold-night occurrence is independent of shelter; shelter changes its physiological cost. World events are precomputed and identical for any policy with the same seed. Agent-linked events use one precomputed uniform per step and contextual thresholds. They describe the preceding interval's action and movement, so an injury observed before this decision reflects travel already performed, never an action the mind has not chosen.

Exactly one event enters recent_events each step: volcanic, injury, storm, boar encounter, cold_night, find_food, none. Lower-priority conditions are suppressed, not appended. The world_events export retains the world-only event before agent-linked priority is applied.

Movement uses cardinal shortest land paths avoiding ocean and lava. Hide remains stationary before signs and walks toward assembly after a sign; reaching safe terrain stops further hide travel. After ash, drink prefers reachable clean springs; before ash all freshwater is clean and nearest water is preferred. It approaches within two Euclidean tiles, and never crosses danger from outside it after warning. Forage targets unburied food; wood gathering requires forest. Shelter building works on land.

## Constants and assumptions

Unless a source is explicitly stated, every value in this table is an **assumption**. Indices, tile codes and Boolean indicators are interface conventions, not fitted physical parameters.

| Parameter | Value | Basis |
|---|---|---|
| Map seed; size; scale; step; horizon | 42; 40 x 40; 250 m; 2 h; 36 | assumption |
| Coast radius and harmonics | .40 + .065 sin(3 angle+.7) + .045 sin(7 angle+seed) | assumption |
| Mountain / forest edge | .12+noise / coast-.065+noise; noise .018 sin(.7x+.3y)+.012 cos(.5y-.4x) | assumption |
| Forest food density | .30; spawn always food | assumption |
| Vent; stream | centre; bent southward stream, with valleys at angles pi/2, -.55, 3.6; bend .28 sin(.55 distance) | assumption |
| Spawn offset; clean spring; assembly offset | (0,+4); (-10,+7); (-9,+7) from centre | assumption |
| Danger distance / valley buffer | <=4 tiles / <=2 tiles | assumption |
| Caution distance / valley buffer | <=7 tiles / <=4 tiles | assumption |
| Eruption probability | 2/3 | supplied Phillipson & Gottsmann abstract summary |
| Onset range | uniform integers 4..19 | assumption: compressed final escalation |
| Escalation starts | onset // 2 | assumption |
| PDC delays after onset | uniform choice 0,0,0,1,3,8,15; cap at horizon - 1 | assumption; 15 steps anchored to supplied Cole ~30 h case; immediate flows assumed |
| Initial sign probability; rise | .12; +.75 * min(1,t/onset) after midpoint | assumption; qualitative rise from USGS |
| False-alarm fade | .12 * max(0,1-(t-transition)/6) | assumption: six-step fade |
| Sign identity | equal tremor / gas_plume | assumption |
| Ash accumulation | +.16 per erupting step, capped 1 | assumption |
| Lava advance; extent | vent at onset, then two adjacent new cells per step, nondecreasing radial distance; random branches | assumption; maximum ~.069 m/s is below supplied USGS .15 m/s anchor; <=2 tiles/step |
| PDC footprint | seed chooses 1..3 valleys, with .85 chance to replace one with the dominant stream valley; pulses every 3..5 steps; corridor radius uniform 1.5..2.5 tiles per selected valley; reach min(5+2*(step-first_pdc), seeded valley runout), safe zone excluded | assumption: valley routing from Cole |
| PDC runout per selected valley | uniform integer ceil(.6 * valley length)..valley length | assumption: variable flow volume, no calibrated magnitude data |
| PDC geometry RNG offset | seed +2027 | assumption: independent stream preserves timing and signs |
| Lahar footprint; activation | stream radius 1; rain/storm and ash >=.3 | assumption; ash/rain mechanism from FEMA/UW |
| Deposit persistence | lava/PDC/lahar lethal for rest of horizon | assumption: conservative residual hazard proxy |
| Weather RNG offset | seed +1009 | assumption: independent random stream |
| Weather transitions to calm/rain/storm | calm .78/.19/.03; rain .22/.65/.13; storm .12/.38/.50 | assumption |
| Cold-night hours; probability | 20..6 inclusive; .12 + .22 wet + .20 ash | assumption |
| Injury probability | .002 + .025 moving + .020 moving in dark + .025 moving on mountain + .030*(1-energy) moving | assumption |
| Boar probability | .003 + .012 forest + .012 at hours 6,8,18,20 | assumption; no large predators or animal precursors |
| Forage discovery | uniform <.30, only prior forage in forest | assumption |
| Travel budget | 8 tiles; injury halves; darkness multiplies .75; ash >.5 halves; minimum 1 | assumption: rough-ground 1 km/h |
| Water radius; clean/dirty relief; dirty morale cost | 2 tiles; .65/.30; .06 | assumption; unpalatability from FEMA/UW |
| Shelter wood; food/wood forage yield; food consumption | 2; 2/1; +.4 hunger if below .7 | assumption |
| Rest energy/warmth/safety | +.30/+.12 sheltered or .015 outdoors/+.05 | assumption |
| Non-rest energy cost; hide safety/stress | .025; +.20/-.10 | assumption |
| Ash warmth/safety loss; shelter exposure | .040/.025 times ash; .10 of outdoor exposure | assumption |
| Warning stress increase | .08 | assumption |
| Initial hunger/thirst/warmth/energy/safety/morale; stress | .85/.80/.90/.90/.85/.80; .15 | inherited scenario assumptions |
| Hunger/thirst decay | .025; 1/36 per step | assumption: 72 h from full hydration; .80 initial lasts 29 steps |
| Low hunger; energy/morale cost | <=.15; .015 each | assumption |
| Starvation threshold | empty hunger and >72 steps without food | assumption: cannot starve within three days; cause retained |
| Outdoor night chill / daytime warming | .015 forest or .025 open / .05 at hours 10..16 without storm | inherited assumptions |
| Stress weights safety/thirst/hunger/warmth/injury | .35/.25/.20/.15/.20; smoothing .7 old + .3 target | inherited assumptions |
| Death thresholds | thirst <=1e-9; warmth <=0; energy <=0 with safety <.2 | inherited assumptions, with numerical tolerance |
| Storm safety/warmth losses indoors vs outdoors; outdoor stress | .10/.05 vs .15/(.06 forest, .10 open); +.30 | inherited assumptions |
| Cold-night warmth indoors/outdoors; morale loss | .03/(.06 forest, .10 open); .10 | inherited assumptions |
| Boar safety/stress indoors vs outdoors | .15/.20 vs .40/.45; outdoor injury | inherited assumptions |
| Injury energy/morale/stress; cooldown metadata | -.20/-.20/+.35; 5 steps (boar 4) | inherited assumptions; persistent injury simplification |
| Find-food ration/morale/stress effects | +2/+.15/-.10 | inherited assumptions |
| Stub warning hide weight; volcanic order adjustments | +6 prior weight; tremor->gas hide +.45, reverse rest +.30 | assumption; illustrative order effect, no quantum evidence |
| Stub stress mixing threshold/range | .4/.5 | inherited assumption, no measured decoherence |
| Demo search bound | seeds 0..1999; require stress >.4 for stress example | assumption: finite illustrative search, no outcome guarantees |
| Stub base action weights | 1 each | assumption |
| Stub thirst/hunger triggers and weight additions | <.3: drink +40, forage +3 | assumption |
| Stub cold trigger / weights | warmth <.4: build +3.5, rest +2 | assumption |
| Stub night / threat weights | hours >=21 or <=5: rest +3.5; safety <.3 or storm: hide +3 | assumption |
| Stub injury->storm adjustments | hide +.45, explore -.2 (floor .01) | assumption |
| Stub storm->injury adjustments | rest +.40, hide -.1 (floor .01) | assumption |
| Stub boar adjustments | hide +.35, build +.2 | assumption |
| Probability rounding / fallback | four decimals / .1 default / 1 divided by action count | interface assumption |
| Stub seed loader | integers 0..19 | assumption: placeholder, no empirical seeds |

Legacy heuristic prior weights and injury/storm stub order effects are compatibility defaults in contracts.py; they are assumptions, not measured ATUS or hardware data. All probabilities and need values are clamped or normalised to their contract ranges.

## JSON handoff

Existing keys remain. world adds map_seed, scale_m_per_tile, volcano and evacuation_map. Volcano includes vent, erupts, nullable onset_step/first_pdc_step, phases, world_events and hazard_by_step arrays covering all 36 steps, even when the agent dies early. Hazard records contain new_lava, new_pdc, new_lahar coordinate arrays and ash in [0,1]. Coordinates use [x,y], grids use [y][x]. Accumulate new_* overlays for replay; base tile codes remain 0..4. world.tiles contains current terrain including shelters; world.initial_tiles preserves the initial terrain.

Evacuation_map includes static zones (0 safe, 1 caution, 2 danger), assembly_points near clean springs, and a connected route_from_spawn. Zoning uses geography, never future hazards. Each step adds pos_after and phase. Only replay shows the hidden phase. New event names are tremor, gas_plume, eruption, ash_fall; state keys and action names are unchanged. noise_source defaults to stub; explicit integration labels are honoured. Curated runs use stub.

## Limits

No topographic DEM, wind/ash transport, gas toxicity, hydrodynamics, eruption magnitude, route-capacity model, rescue, long-term lahars, or calibrated physiological hazard rates. Stream channels are shallow traversable land with a freshwater overlay; oceans are never drinkable. PDC deposits persist as a conservative lethal overlay, rather than simulating cooling. Lava branches downhill by radial distance, without a measured elevation model; the 2-hour step allows escape before end-of-step lethality. Animal encounters are boars, unrelated to unrest. The example pair illustrates differences between stubs, not causal proof of quantum order effects. Search-selected demos are not unbiased performance estimates. Requirements involving real quantum circuits or hardware remain teammate work.

`world.tiles` records current terrain including built shelters (tile 4). `world.initial_tiles` preserves terrain before the run for replay.

## Revised scenario assumptions

| Parameter | Value | Basis |
|---|---|---|
| Ash sign allocation | floor(post-onset steps / 2), excluding explosive pulses | assumption; deposition still increases .16 each step |
| Explosive signs | onset and every PDC pulse | assumption; repeated explosions informed by supplied Cole summary |
| Outdoor heat loss | .018 ash + .035 wet + .025 darkness per step; forest cover multiplies .35 | assumption; shelter/preparation trade-off, not calibrated physiology |
| Stub preparation | warmth <.65 adds 9 build weight; energy <.3 adds 15 rest weight | assumption |
| Stub selection | maximum probability; quantum-labelled stub prioritises drink below .3 and build below .4 | assumption; same basic competence, illustrative order preferences |

The quantum-labelled placeholder now selects its largest adjusted probability rather than sampling. Neither placeholder is evidence of a quantum advantage. Warning preference is restricted to the three recent events; urgent hydration overrides warning. Exposure and preparation outcomes must be assessed over paired seeds, not inferred from selected demos.

Forest canopy provides partial wind/rain protection, but is not waterproof shelter. Its assumed 65% reduction in additional outdoor heat loss preserves a reason to gather wood and build after evacuation. These thermal rates are scenario assumptions, not clinical predictions.

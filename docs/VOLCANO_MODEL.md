# Volcano scenario model

Synthetic terrain and hazards support a survival/evacuation demonstration, not a forecast or civil-protection tool. A tile is 250 m, a step is two hours, and the default horizon is 36 steps (72 hours). Both labelled minds are heuristic stubs. No quantum circuits, hardware measurements or calibrated human survival probabilities are produced.

This model is not calibrated. Tobler's 0.6 off-path factor is taken from the supplied summary, while the additional forest and mountain multipliers are assumptions. PDC_DELAYS is not fitted. Numerical choices below do not estimate a real island's probabilities.

## Evidence and access

No network was used. All sources below were supplied through search summaries; none was independently opened or verified in this round. Mechanisms inform this model; numerical scenario choices are assumptions unless explicitly attributed.

- [Tobler hiking function](https://en.wikipedia.org/wiki/Tobler%27s_hiking_function): W = 6 exp(-3.5 abs(S + .05)) km/h, S = rise/run; off-path speed factor .6. A plains edge takes exactly .25/(W*.6)*60 minutes. Forest and mountain factors are assumptions.
- [2023 UK GPS study](https://arxiv.org/abs/2303.16065): Tobler's .6 off-road penalty is stronger than observed, and one multiplier does not distinguish open from obstructed terrain. Our separate forest/mountain factors are not fitted to that study.
- [USGS ash and pumice hazards](https://www.usgs.gov/volcanoes/long-valley-caldera/science/volcanic-ash-and-pumice-hazards-long-valley-caldera): grain size/thickness generally decline away from the vent; downwind thickness depends on wind, which cannot be predicted in advance. Our persistent drifting wind and deposition kernel are synthetic, precomputed only for reproducible replay.
- USGS tephra/lahar summaries: intense rainfall can remobilise ash and send lahars down valleys. [FEMA/UW water advice](https://mitigate.be.uw.edu/wp-content/uploads/sites/37/2017/05/hgwatersupply.pdf): ash affects turbidity/unpalatability. Stream drinking gives reduced relief without poisoning; clean springs remain clean by assumption.
- [Baxter et al. summary](https://resources.pedspandemicnetwork.org/library/4778/human-survival-in-volcanic-eruptions-thermal-injuries-in-pyroclastic-surges-their-causes-prognosis-and-emergency-management-4778): some surge victims survive burns. About a third of 106 patients survived in one Merapi hospital cohort. This is selected hospital data, **not** a model survival probability. Our nonfatal surge margin is an assumption, not fitted to that cohort.
- [Phillipson & Gottsmann abstract summary](https://theghub.org/resources/2435): approximately two thirds of reported unrest episodes erupt in the short term. This motivates a broad prior, not an island-specific probability.
- [USGS prediction FAQ](https://www.usgs.gov/faqs/how-can-we-tell-when-volcano-will-erupt): unrest can fade; seismicity/steaming may increase before eruption. Early signs overlap between eruption and false-alarm runs.
- [La Soufriere 2021 chronology](https://en.wikipedia.org/wiki/2021_eruption_of_La_Soufri%C3%A8re) and supplied Cole IUGG summary/[USGS release](https://data.usgs.gov/datacatalog/data/USGS:65baeb12d34e18c6baf2df6c): examples of escalating unrest, valley routing, repeated explosions and delayed flows. These are examples, not a distribution fit.
- [Geology.com hazards](https://geology.com/volcanoes/volcanic-hazards/): fast PDCs cannot be outrun. The whole active corridor arrives within a two-hour bin.
- [USGS lava speed](https://www.usgs.gov/news/volcano-watch-how-fast-does-hawaiian-lava-flow): most fronts below .15 m/s. Two 250 m cells per two-hour bin bound our pathwise advance at about .069 m/s.

No published onset-to-first-flow statistic was found in the supplied search. **PDC_DELAYS = (0, 0, 1, 2, 3, 5, 8, 15) is an assumption and is not fitted.** The earlier 15-minute-to-13-day range was an unconfirmed search-summary claim and is not used as calibration.

## Terrain and travel

MAP_SEED fixes geography independently of the event seed. A noisy volcanic cone with winding erosional depressions generates elevation, coast and vegetation. Priority flooding raises enclosed pits and adds a tiny gradient across flats. Cardinal steepest descent on that filled field produces drainage. Main channels start next to the vent, descend monotonically, and end at the last land cell next to ocean. The first is the perennial stream; stream_tiles is exactly valleys[0][1:]. The filled synthetic surface is the exported elevation, not a measured DEM.

Zones use vent distance and distance/height above the nearest main channel, never future hazards. Two separated assembly points sit in safe terrain, each within 500 m of its own clean spring on a different tile. Dijkstra routing minimises directed Tobler walking time, avoiding ocean, lava and hot PDC deposits while allowing escape from a blocked starting cell. routes_from_spawn contains a route to each assembly; route_from_spawn selects the fastest.

Every movement action spends 120 minutes along a least-time route. Injury and darkness reduce the budget; local ash along each edge increases its time cost. A possible move always covers at least one cell, even if that cell exceeds the budget. This coarse-grid minimum is an explicit assumption. Hide continues to an assembly point after observed signs, including after reaching safe terrain; before warning it stays still. Once outside danger it avoids crossing back through it. Drink walks the least-time route to within two tiles of any usable water, wherever that is, and has no warning logic: whether to leave danger is the mind's choice alone. An earlier version removed danger-zone water after a warning, which walked agents to safety without any decision, so it was dropped. Water quality follows the source. Explore chooses a random nearby target then follows a least-time path.

Terrain generation is cached by dimensions/seed; mutable terrain and run state are copied per engine. Relief images are cached once per terrain per process; hazard surfaces refresh only after a simulation step.

## Hidden hazards and step ordering

Volcano phases, signs, wind, ash and flow masks are precomputed before decisions, independently of policies. The frozen mind receives only its original state keys: elevation, zones, wind, phases and future hazards are never added to state. The ordinary position/recent events remain visible. One event per step enters recent_events, with volcanic signs taking precedence over contextual events. Weather still acts and renders when a volcanic event occupies that slot.

At step start, current overlays are loaded, events affect the agent, and active PDC/lahar occupancy kills before movement. The policy decision is still recorded. Survivors act, eat automatically if needed, and experience local exposure and need decay. At step end active PDCs/lahars and lava kill. Surge occupancy at either check injures and raises stress. Old PDC deposits block paths and injure at step end without killing. Old lahar deposits are passable when flow stops. Lava may be escaped before the end-of-step check.

Active PDC pulses include previously covered tiles; new_pdc includes only first coverage. A one-cardinal-cell surge fringe excludes active flow and zone 0. Lahars activate only on wet steps whose channel-average accumulated ash exceeds the threshold; rain can reactivate old channels with empty new_lahar. Lava chooses adjacent downhill candidates, sometimes branching, with at most two additions per step. Slow growth/occupation approximates ponding; there is no volume-conserving lava hydraulics.

Ash accumulates through a downwind Gaussian-shaped widening kernel with a small radial background. wind_deg is travel-toward bearing, 0 north (-y), 90 east (+x). ash is the unrounded island-grid maximum; ash_grid quantises each local value to round(ash*9). Physiological and visual local ash uses that quantised field. No ash removal is simulated. Stream water quality uses ash in its upstream channel catchment; shelter attenuates outdoor ash exposure.

Foraging searches within 500 m (two tiles), an assumption that prevents incidental island-wide evacuation. Food concentrates in moist valley bottoms near the main channels, which is why staying is tempting; this concentration is an assumption, not a surveyed distribution. Food patches yield once per run, with an assumed four-ration carrying capacity. Full inventory leaves the patch unharvested. find_food describes discovery and gives morale/stress relief, not additional unbounded rations. Automatic eating happens before and after any action when hunger <.5 and food is held. Rebuilding an existing shelter spends no wood. Injury cooldown falls every action, faster on rest. Boars only cause injury outdoors when energy <.3. Recent volcanic events cap safety by zone and impose stress floors; hiding cannot erase this threat. Morale falls slightly during unrest while in harm's way, and recovers slowly on quiet steps when the agent is safe, fed, watered and uninjured.

## Numerical constants

All entries marked assumption are scenario choices, not measured/fitted rates. Coordinate indices, frozen action/event/tile names, zero/one normalisation and formatting are interface conventions. Pixel positions, colours, font sizes and animation parameters are visual assumptions rather than physical quantities.

| Parameters | Values and basis |
|---|---|
| Terrain seed / dimensions / resolution | 42 / 40 x 40 / 250 m; assumption |
| Cone and coast | 1030 m coefficient, exponent 1.6; radius 16 + 2.6 sin(3 angle+.7) + 1.8 sin(7 angle+seed); assumption |
| Gullies / roughness / ocean | .42 exp(-.5(sin(3 angle+.4+.45 sin(.55 r))/.25)^2), fade over 3 tiles; +/-18 m noise fading to coast; offshore -20-8 distance; minimum land 1 m; assumption |
| Flood flat gradient / cache | .001 m; cache up to 16 terrains and their initial routes; up to 128 forecasts, copied per engine; assumption |
| Vegetation | mountain >750 m; forest >100 m; lower plains; forest spawn clearing; assumption |
| Channels / spawn | up to four cardinal vent-adjacent sources, distinct coastal outlets, >4-cell channels; spawn first stream tile at least 6 tiles (1.5 km) from the vent; assumption |
| Danger / caution | vent distance <=4.5 / <=7 tiles OR channel distance <=1.6 / <=3 and relative height <100 / <180 m; assumption |
| Assembly / springs | safe band 80-300 m; first near vent+(-9,+7), second opposite bearing; clean spring on the highest safe land within 2 tiles of each, never the assembly tile; assumption |
| Food density / yield | .45 on land within 3 tiles of a main channel at 30..650 m; .03 on other forest; spawn always; one ration once per patch, carrying capacity four rations; assumption |
| Walking | Tobler constants 6, -3.5, +.05 and off-path .6 from supplied summary; cardinal adjacency assumption |
| Forest / mountain speed | .8 / .65 additional multiplier; plains/shelter 1; assumption |
| Movement budget / modifiers | 120 min; injury x.5, darkness (20..6) x.75, local ash x(1-.5 ash); >=1-cell movement; assumption |
| Explore target | 12 random neighbor choices then least-time route; assumption |
| Eruption / onset / delays | 2/3 broad supplied prior; onset uniform 4..19, escalation halfway; delays (0,0,1,2,3,5,8,15) not fitted; assumption |
| Signs | base .12; after midpoint +.75 min(1,t/onset); equal tremor/gas_plume; false alarm fades over six steps; assumption |
| Explosions / ash signs | onset plus pulses every 3..5 steps; ash_fall selected on up to half of post-onset nonexplosive steps; assumption |
| PDC geometry | random secondary channels plus perennial stream in every pulse; RNG offset 2027; runout .6..1 channel length, radius 1.5..2.5 tiles; proximal apron radius 5 tiles (1.25 km); full seeded runout within each two-hour pulse, safe zone excluded; assumption |
| Surge / injury | one cardinal fringe; cooldown at least 3, stress +.15, energy -.06 with .03 mobility reserve at each exposed check; assumption |
| Lava | vent first, at most two downhill neighbor additions; lowest elevation with uniform 0..35 m perturbation for branching; assumption |
| Wind | initial uniform 0..360 degrees, independent per-step drift +/-6 degrees; assumption |
| Ash | radial .025 exp(-distance/4); downwind .20 exp(-distance/14) exp(-.5(cross/(1.5+.22 along))^2), capped 1; assumption |
| Lahar | wet weather and channel-average ash >=.12; current channel after vent only; assumption |
| Weather | RNG seed+1009; transition calm .78/.19/.03, rain .22/.65/.13, storm .12/.38/.50 to calm/rain/storm; assumption |
| Contextual injury | .002 + .025 moving + .020 moving at night + .025 moving on mountain + .030(1-energy) moving; assumption |
| Boars / discovery | .003 + .012 forest + .012 dawn/dusk (6,8,18,20); discovery <.30 after forest foraging; assumption |
| Cold-night chance | .12 + .22 wet + .20 maximum ash, night 20..6; inherited assumption |
| Initial hunger/thirst/warmth/energy/safety/morale | .85/.80/.90/.90/.85/.80; stress .15; inherited assumption |
| Warning feelings | stress +.08, safety -.10, morale -.02; recent-event safety caps safe/caution/danger .8/.5/.3; stress floors .3/.45/.6; morale -.01 per feeling check (start/end) outside the safe zone; +.03 per quiet step when safe with hunger and thirst >.3, uninjured; assumption |
| Eating / shelter | hunger <.5, one ration +.4, food timer reset; wood cost 2 once; forest gathering +1 wood; assumption |
| Healing | injury cooldown 5, tired-boar cooldown 4; -1/action, -2/rest; assumption |
| Water | within radius 2; clean +.65 thirst; catchment ash >.1 dirty +.30, morale -.06; assumption |
| Rest / hide / craft | rest energy +.30, warmth +.12 sheltered/.015 outdoors, safety +.05; hide safety +.20 stress -.10 before caps; craft consumes one wood for tool; assumption |
| Action / metabolism | nonrest energy -.025; hunger -.025, thirst -1/36 per step; hunger <=.15 costs .015 energy/morale; assumption |
| Exposure | local ash warmth -.040/safety -.025/energy -.035; shelter exposure x.1; extra outdoor chill .018 ash+.035 wet+.025 darkness, forest x.35; assumption |
| Ambient thermal | night 21..5 warmth -.015 forest/-.025 open; daytime 10..16 +.05 absent storm; inherited assumption |
| Storm | shelter safety -.10 warmth -.05; outside safety -.15 warmth -.06 forest/-.10 open, stress +.30; inherited assumption |
| Cold-night event | warmth -.03 shelter/-.06 forest/-.10 open; morale -.04; assumption |
| Boar event | shelter safety -.15 stress +.20; outside safety -.40 stress +.45; injury only when energy <.3; assumption |
| Injury event / discovery | injury energy/morale -.20, stress +.35; discovery morale +.15 stress -.10; inherited assumption |
| Stress smoothing | weights safety .35, thirst .25, hunger .20, warmth .15, injury .20; .7 old+.3 target, then warning floor; inherited assumption |
| Death | thirst <=1e-9; empty hunger after >72 steps without food; warmth <=0; energy <=0 and safety <.2; inherited assumption |
| UI geometry / cache | 1280 x 760 virtual canvas, 760 px map, 19 px/tile; relief cache 8; assumption |
| Relief | eight-pixel Gaussian relief smoothing (radius 24 px); 100 m contours; hypsometric stops -100,0,35,150,400,750,1050 m; northwest shade .91+(-gx+gy)*.035 clipped .65..1.15, canopy noise sigma 1.4, coast blend within 2.5 m; visual assumptions |
| Hazard opacity | deposit 150, lahar 235, surge 105, PDC pulse 255 fading to 95 over 1.6 s with patchy texture, lava glow/core 150/255, ash up to 65 of 255; visual assumptions |
| Day/weather animation | dawn 05..08/dusk 16..19; night tint max125/255; 70 rain/130 storm streaks, 45 locally filtered ash particles; 14-puff ash column widening from 30 px and bending downwind; active-front billows sampled every fourth boundary cell, fading with the pulse; visual assumptions |
| Playback / shake | 60 fps, .8 s/step, 1/2.5/6 speed; .3 s shake <=2 px; interpolation 10/s, bubble 3 s; visual assumptions |
| Demo curation | seeds 0..1999, high stress >.4, distinct fifth-run seed; illustrative selection assumption |

The frozen stubs retain their inherited illustrative weights and order-effect/decoherence labels. Those are assumptions, not measured ATUS priors or quantum evidence; contracts.py is unchanged.

## JSON handoff

All existing keys retain their meaning except the explicitly revised lethal-deposit semantics. Coordinates are [x,y]; grids are [y][x]. Base tile codes and mind state keys are unchanged.

- world.elevation: integer metre grid, 40 rows of 40 values. world.weather: calm/rain/storm for all 36 steps, including beyond death.
- world.evacuation_map retains zones, assembly_points and route_from_spawn; adds routes_from_spawn, one least-time route per assembly point.
- world.volcano retains vent, erupts, onset_step, first_pdc_step, phases, world_events and hazard_by_step. Each hazard retains new_lava/new_pdc/new_lahar (first coverage), ash (maximum); adds active_pdc, active_lahar, surge coordinate arrays, wind_deg and ash_grid (40 strings of 40 digits). Active masks replace each step; deposits accumulate. Empty active masks mean the pulse stopped. Lahars do not leave blocked paths.
- Existing step records retain state/event/action/probs/reason and pos_after/phase. world.tiles includes built shelters; world.initial_tiles preserves starting terrain. noise_source is honoured; demos use stub.
- Top-level evacuation adds nullable first_sign_step (first volcanic event), left_danger_step (first pos_after outside zone 2), reached_safe_step (first zone 0), reached_assembly_step, onset_step and first_pdc_step. All are zero-based. warning_lead_hours = 2(onset-first sign); margin_hours = 2(first PDC-reached safe). Missing endpoints yield null. A negative margin means safety was reached after first flow. Onset/first PDC describe the seeded whole horizon even if the agent dies before them; the debrief marks unobserved events.

Exports use compact JSON, retaining all grids and keys, with each curated file below 400 KB. Demos are search-selected illustrations, not unbiased policy performance estimates.

## Limits and validation

There is no measured topographic DEM, hydrodynamics, grain-size transport, wind forecast, gas toxicity, lava volume conservation, deposit cooling, evacuation congestion or rescue model. Filled terrain is synthetic; cardinal paths and coarse minimum movement distort travel. PDC cores are deterministically lethal and surge fringes deterministically nonfatal; neither is a clinical survival model. Thermal, food, injury and stress rates are assumed. Ash persists indefinitely within the horizon. Springs are assumed protected. Local catchment quality is a channel-average proxy, not a watershed sediment model. Seeded future hazards are for replay only. Tropical rain and cool nights are represented; no snow is simulated.

Regression tests cover field signs, descent, least-time walking against independent relaxation, active/deposit differences, surge injury, recurring lahars, wind/ash, food/eating/healing, wood, stress, evacuation arithmetic and GUI events. The final task report records actual test/checker results and draw timing; generated output alone does not establish scientific realism or the user's understanding.

Tropical thermal assumption: warmth is floored at .05 before metabolic decay. Without clothing or wet-bulb exposure measurements, neither tropical rain nor ash alone justifies lethal hypothermia. Open-Meteo reanalysis for St Vincent, 2015-2024, gives a night 5th percentile near 19 degrees C; that grid cell sits high, so the coast is warmer. Colder analog islands would change this conclusion. Ash still lowers comfort, safety and energy. As a result wood and shelter buy comfort and energy rather than survival, and leaving at once with no wood survives at least as often as gathering first. That is a modelling result, not a target. Leaving also has little modelled cost, because a 72 h run ends before scarce upland food matters. Exhaustion collapse remains an inherited rule: a policy that never rests for 72 h can die of it, which is weakly supported and marked for replacement. This floor and the injury mobility reserve are not fitted physiological estimates; hypothermia remains an agent threshold for direct callers supplying other environments.

## Limitations and uncertainty

This is a synthetic evacuation scenario, not a validated hazard or medical model. The 250 m grid and two-hour bins cannot resolve individual escape times or exposure dose. Terrain is generated rather than surveyed; channels have no discharge, sediment volume or hydraulic calculation. Safe-zone exclusion from PDC masks is a scenario boundary, not a real safety guarantee. Lahars use channel-average ash and wet weather rather than rainfall intensity or a water balance. Wind has no forecast skill.

Tobler travel times omit trail quality, load, route finding and individual fitness. The off-road factor is disputed by the supplied 2023 GPS summary; forest and mountain factors remain assumptions. Injury healing, thermal comfort, ash fatigue and safety caps are illustrative. Nonfatal surge injury does not reproduce burns or the hospital cohort's survival fraction. PDC_DELAYS is not fitted, and the eruption prior is not a probability for this island. Demo runs are selected examples; neither labelled stub establishes quantum advantage. Sources were read only through the supplied search summaries, without network verification.

Pulse geometry assumption: each pulse covers its entire seeded runout in one two-hour bin. A 1.25 km proximal apron represents spreading on the upper cone before confinement to the derived valleys; the perennial valley always carries a pulse, while secondary outlets and runout vary by seed. Neither the apron radius nor preferential perennial routing is fitted. This synthetic collapse geometry does not model every eruption style, flow volume or a measured runout envelope.

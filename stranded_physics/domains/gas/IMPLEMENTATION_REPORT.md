# Gas, lava and exposure implementation

Implemented the requested T1 interfaces, analytic helpers, frame-local coupling, measurement commands and six tests. Categories use no random draws. Only the gas measurement glue imports Eruption. No commits or pushes; locked metadata and pre-existing parameter values are unchanged.

## Gate results

| Gate | Verdict | Value |
| --- | --- | --- |
| gas.records_and_units | PASS | verification, no scalar |
| gas-model | PASS | 2 tests |
| gas-total-so2 | FAIL | 99.67443982842491 kt |
| lava.records_and_units | PASS | verification, no scalar |
| lava-model | PASS | 2 tests |
| lava-dome-volume | PASS | 20.0 million m3 |
| lava-dome-radius | NO_TARGET | 335.30413655590183 m |
| exposure.records_and_units | PASS | verification, no scalar |
| exposure-model | PASS | 2 tests |

SO2 is below the locked 100?300 kt acceptance interval. The fraction was selected before opening gates and was not adjusted. The volume check is an anchor arithmetic check, not independent validation. Radius has no observation target.

## Assumptions and influence

All added assumptions have role input and nonzero-width ranges in their category params.toml. Bounds are admissible configuration bounds, not confidence intervals.

| Category / parameter | Default (range) | Influence and uncertainty |
| --- | --- | --- |
| gas.so2_mass_fraction | 0.001 (0?0.1) | Dominant uncertainty in explosive SO2; its contribution scales linearly. Not measured or fitted. |
| gas.min_wind | 0.5 m/s (0.01?10) | Calm frames use this floor; concentration scales inversely with effective wind. Steady Gaussian dispersion is doubtful in calm weather. |
| gas.release_height | 100 m (0?5000) | Effective height above vent; ground concentration changes exponentially with height/sigma_z. No terrain correction. |
| gas.sigma_y_coefficient | 0.08 (0.001?1) | Briggs class D width coefficient, recalled from memory. Controls crosswind spread and dilution. |
| gas.sigma_y_decay | 0.0001 /m (0?0.1) | Briggs class D downwind correction, recalled from memory. |
| gas.sigma_z_coefficient | 0.06 (0.001?1) | Briggs class D vertical width coefficient, recalled from memory. Strong ground-concentration sensitivity. |
| gas.sigma_z_decay | 0.0015 /m (0?0.1) | Briggs class D vertical correction, recalled from memory. |
| lava.viscosity | 1e8 m2/s (1e2?1e14) | Effective Newtonian kinematic viscosity; radius scales as viscosity^(-1/8) before capping. Not a rheological fit. |
| lava.huppert_coefficient | 0.715 (0.1?2) | Huppert (1982) constant-flux expression recalled from memory; radius scales linearly. |
| lava.gravity | 9.80665 m/s2 (9?10) | Standard gravity recalled from memory; radius scales as g^(1/8), a small effect. |
| exposure.roof_fragility_beta | 0.6 (0.05?3) | Controls transition width; failure remains 0.5 at the inherited 300 kg/m2 median. Not fitted to casualty data. |
| exposure.flow_death_outdoors | 0.95 (0?1) | Direct event probability; substantial, unvalidated effect. Not fitted to casualty data. |
| exposure.flow_death_sheltered | 0.5 (0?0.94) | Direct event probability; lower than outdoors at chosen defaults. Not fitted to casualty data. |
| exposure.ash_fatigue_per_hour | 0.1 /hour (0?10) | Direct fatigue scale; gameplay assumption, not a physiological estimate. Not fitted to casualty data. |
| exposure.ash_fatigue_load | 10 kg/m2 (0.01?1000) | Sets fatigue saturation threshold; below it cost is proportional to load. Not fitted to casualty data. |
| exposure.shelter_ash_factor | 0.2 (0?1) | Direct multiplier on sheltered fatigue. Not fitted to casualty data. |

Measurement conventions are also input assumptions: both measurement starts are 2021-04-08T00:00Z (epoch range 0?4e9 s); gas ends 2021-04-10T00:00Z (same range), uses 3600 s steps (1?86400 s), and seed 0 (0?4294967295). Lava's explosion instant is the task-specified 2021-04-09T12:41Z (epoch range 0?4e9 s), not independently verified here. These select the measurement window. Eruption mass rates represent preceding intervals; integration combines those rates with left-edge passive emissions, avoiding an extra endpoint hour. Seed affects no measured mass rates.

The source gives a date rather than time of day for growth onset. Midnight UTC on 27 December 2020 is assumed within the derived growth_before_axis and flux records. Default prior growth is 8,812,800 s; flux is 20 million m3 divided by the 103 days 12 h 41 min to the first explosion. A one-day onset shift changes flux by about 1%. A generated eruption may replace prior growth explicitly, including zero.

## Evidence and limitations

Read artifacts/physics/raw/eruption/st_vincent_cole_accepted.txt: lines 103?106 give 27 December 2020 and subsequent passive dome extrusion; lines 477?486 report almost complete destruction and assume about 20 million m3 before explosions. These are the only newly read research claims used. The near-total destruction is simplified to complete disappearance at the first sampled explosion frame. The real elongated coulee is represented by a disc. No validation of spatial dome shape was possible.

Memory-based references: Briggs open-country class D coefficients, Huppert (1982) spreading expression and coefficient, and standard gravity. No original papers for those were read. Existing citations for gas.peak_so2_flux (Carn et al. 2016), lava.max_dome_radius (UWI reports) and exposure.roof_collapse_load (Spence et al. 2005 Table 3) were preserved, not independently read or verified. Their attribution is inherited, not a new verification claim.

The ground plume assumes flat terrain, steady neutral dispersion and instantaneous adjustment at each frame; it models neither transport delay nor chemistry. Surface wind and assumed release height may be poor proxies for a volcanic plume. Exposure outputs are illustrative fragilities/probabilities, not casualty predictions.

## Verification limits

The six category tests pass together. Randomized checker behavior checks pass. The final checker still cannot exit 0 because existing core tests using pytest tmp_path encounter Windows PermissionError (WinError 5) under C:/Users/HP OMEN/AppData/Local/Temp/pytest-of-HP OMEN. An attempt to use a workspace-local temp directory failed with the same permissions problem; gas/test_tmp/core is an inaccessible temporary directory and could not be removed in this sandbox. No core tests or pytest behavior were modified. The authorized measurement import uses normal relative-import syntax; the old static core check does not recognize its explicit task exception.

The checker output is retained in checker.log; a diagnostic core run is in core-check.log (ignored diagnostic files). This environment limitation remains unresolved and requires a rerun in an environment where pytest can create and access its temporary directories.

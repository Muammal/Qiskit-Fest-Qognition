# Benchmark settings

No settings file, an empty file, and empty sections preserve simulation defaults. Names are case sensitive. ETA is fixed and rejected, as are unknown names. ACTIONS is imported from the frozen contract and is not tunable.

The classical mind in contracts.py has no constants of its own exposed here; all mind/config.py overrides have no effect on classical decisions. There is no kappa_max or prior-weight constant in the current config.

| Setting | Default | Effect |
|---|---|---|
| `PROTECT` | `['hide']` | Quantum and classical_mixture; no classical effect |
| `CARRY_ON` | `['forage', 'drink', 'build_shelter', 'rest', 'explore', 'craft']` | Quantum and classical_mixture; no classical effect |
| `THREAT_EVENTS` | `{'gas_plume', 'tremor', 'ash_fall', 'cold_night', 'storm', 'injury', 'animal', 'eruption'}` | Quantum and classical_mixture; no classical effect |
| `EVENT_GATES` | `{'tremor': ('ry', 1.0471975511965976), 'gas_plume': ('rx', 1.8849555921538759), 'storm': ('ry', 1.0471975511965976), 'animal': ('ry', 1.0471975511965976), 'injury': ('rx', 2.0943951023931953), 'cold_night': ('rx', 0.5235987755982988), 'find_food': ('ry', -0.7853981633974483)}` | Quantum and classical_mixture; no classical effect |
| `COLLAPSE_EVENTS` | `{'eruption', 'ash_fall'}` | Quantum and classical_mixture; no classical effect |
| `CF_SAFE_SAFETY` | `0.95` | Quantum and classical_mixture; no classical effect |
| `CF_DANGER_SAFETY` | `0.05` | Quantum and classical_mixture; no classical effect |
| `Q_CLAMP` | `(0.02, 0.98)` | Quantum and classical_mixture; no classical effect |
| `STRESS_FLOOR` | `0.2` | Quantum only; mixture forces dephasing to 1; no classical effect |
| `STRESS_SPAN` | `0.7` | Quantum only; mixture forces dephasing to 1; no classical effect |
| `ORDER_GAP_REPORT_THRESHOLD` | `0.02` | Quantum explanation text only; no action effect; mixture suppresses it; no classical effect |
| `DECISION_RULE` | `'argmax'` | Quantum and classical_mixture; no classical effect |

Use TOML arrays for sets and tuples, and a table for EVENT_GATES (each value is an axis/angle array). Settings temporarily replace every loaded import of the config constant and are restored even on failure. Runs use seed 1, isolating Python random state for sampling.

[shared] accepts reach_minutes_scale (default 1), boat_crew_share (default: preserve each cohort), and lifebelt (default true). All apply identically to minds and bounds. Existing boat_crew = 1 cohorts stay at 1.

The runner reports mean absolute saved-share error over targets, without population weighting. Checkpoints append full deterministic JSON including settings and all scores. Only explicitly non-default mind sections consume a logged tuning run; shared settings alone do not count against a mind budget.

Scenario limits: supplied cohort totals take precedence over overall target denominators when they differ (Lusitania 1,957 aboard; Empress 1,477). These counts are not adjusted to fit saved shares. Uniform compartments approximate Titanic geometry; breach area alone matches collision-to-sinking time. Lifeboat and demographic assumptions remain unvalidated.

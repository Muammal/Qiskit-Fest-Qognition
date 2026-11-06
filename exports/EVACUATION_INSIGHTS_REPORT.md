# Real-Life Evacuation Survival Rates, Critical Seeds & Policy Insights

## 1. Executive Summary: How Quantum vs. Classical Agents Model Real Human Evacuations
- **Quantum Mind (`mind/quantum_mind.py`)**: Models human belief states as a 2-qubit density matrix (`belief` $\otimes$ `action`). Ambiguous warnings (`tremor`, `gas_plume`, faint chlorine odour, distant steward knocks) apply non-commuting $R_y(\theta)R_z(\phi)$ rotations that preserve off-diagonal coherence $|x| = |\rho_{01}|$. This produces:
  1. **Disjunction / Normalcy Bias**: Under unresolved ambiguity ($p_{\text{danger}} \approx 0.5$), destructive interference reduces $P(\text{protect})$ by **18%** below the classical mixture (`0.370` vs `0.550`), reproducing real-world human hesitation before evacuating.
  2. **Order Effects**: Experiencing a mild cue followed by an acute cue (`tremor -> gas_plume`) boosts evacuation probability by **+14% to +17%** compared to the reverse order (`gas_plume -> tremor`).
  3. **Projective Collapse via Clear Alarms**: Unambiguous signals (`eruption`, `ash_fall`, PA alarms, distress rockets) collapse off-diagonal superposition ($|x| \to 0$), immediately aligning human response with urgent evacuation.
- **Classical Mixture Control (`classical_mixture_decide`)**: Identical gates and conditional parameters ($q_S, q_D$) with coherence forced to zero ($\lambda = 1$). Follows the Classical Law of Total Probability without interference or hesitation.
- **Classical Rational Baseline (`contracts.classical_decide`)**: Deterministic argmax utility rule over physiological needs and recent events.

## 2. Exported Policy Intervention Results (`evacuation_policy_interventions.csv`)
| Scenario | Policy Intervention | Mind | Population | Safe / Survived | Fatalities / AEGL-2+ | Rate (%) |
|---|---|---|---:|---:|---:|---:|
| `titanic` | `historical_baseline` | `quantum` | 2,208 | 578 | 1,630 | **26.18%** |
| `titanic` | `historical_baseline` | `classical_mixture` | 2,208 | 536 | 1,672 | **24.28%** |
| `titanic` | `historical_baseline` | `classical` | 2,208 | 839 | 1,369 | **38.00%** |
| `titanic` | `ambiguous_rockets` | `quantum` | 2,208 | 297 | 1,911 | **13.45%** |
| `titanic` | `ambiguous_rockets` | `classical_mixture` | 2,208 | 278 | 1,930 | **12.59%** |
| `titanic` | `ambiguous_rockets` | `classical` | 2,208 | 839 | 1,369 | **38.00%** |
| `titanic` | `early_pa_alarm` | `quantum` | 2,208 | 824 | 1,384 | **37.32%** |
| `titanic` | `early_pa_alarm` | `classical_mixture` | 2,208 | 796 | 1,412 | **36.05%** |
| `titanic` | `early_pa_alarm` | `classical` | 2,208 | 839 | 1,369 | **38.00%** |
| `titanic` | `open_boarding_both_sides` | `quantum` | 2,208 | 1,027 | 1,181 | **46.51%** |
| `titanic` | `open_boarding_both_sides` | `classical_mixture` | 2,208 | 975 | 1,233 | **44.16%** |
| `titanic` | `open_boarding_both_sides` | `classical` | 2,208 | 1,045 | 1,163 | **47.33%** |
| `pompeii` | `mapping_A_unambiguous_column` | `quantum` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_A_unambiguous_column` | `classical_mixture` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_A_unambiguous_column` | `classical` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_B_literal_default` | `quantum` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_B_literal_default` | `classical_mixture` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_B_literal_default` | `classical` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_C_ambiguous_cues` | `quantum` | 500 | 468 | 32 | **93.60%** |
| `pompeii` | `mapping_C_ambiguous_cues` | `classical_mixture` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_C_ambiguous_cues` | `classical` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_D_milder_plus_enslaved_restricted` | `quantum` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_D_milder_plus_enslaved_restricted` | `classical_mixture` | 500 | 500 | 0 | **100.00%** |
| `pompeii` | `mapping_D_milder_plus_enslaved_restricted` | `classical` | 500 | 500 | 0 | **100.00%** |
| `waterloo` | `alarm_off_ambiguous_smell` | `quantum` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_off_ambiguous_smell` | `classical_mixture` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_off_ambiguous_smell` | `classical` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_on_ambiguous_mapping_A` | `quantum` | 100 | 99 | 1 | **99.00%** |
| `waterloo` | `alarm_on_ambiguous_mapping_A` | `classical_mixture` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_on_ambiguous_mapping_A` | `classical` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_on_unambiguous_mapping_B` | `quantum` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_on_unambiguous_mapping_B` | `classical_mixture` | 100 | 100 | 0 | **100.00%** |
| `waterloo` | `alarm_on_unambiguous_mapping_B` | `classical` | 100 | 100 | 0 | **100.00%** |

## 3. Critical Evacuation Seeds Catalog (`critical_evacuation_seeds_catalog.csv`)
| Scenario | Seed | Quantum Outcome | Mixture Outcome | Classical Outcome | Q-M Divergences | Max Order Gap | Insight |
|---|---:|---|---|---|---:|---:|---|
| `volcano` | `100` | **survived** (none) | **survived** (none) | **survived** (none) | 3 | 0.330 | Quantum vs Mixture diverged on 3 steps (max order-effect gap=0.330) |
| `volcano` | `101` | **survived** (none) | **survived** (none) | **survived** (none) | 2 | 0.263 | Quantum vs Mixture diverged on 2 steps (max order-effect gap=0.263) |
| `volcano` | `102` | **survived** (none) | **survived** (none) | **survived** (none) | 7 | 0.064 | Quantum vs Mixture diverged on 7 steps (max order-effect gap=0.063) |
| `volcano` | `103` | **survived** (none) | **survived** (none) | **survived** (none) | 8 | 0.138 | Quantum vs Mixture diverged on 8 steps (max order-effect gap=0.138) |
| `volcano` | `104` | **survived** (none) | **survived** (none) | **survived** (none) | 6 | 0.152 | Quantum vs Mixture diverged on 6 steps (max order-effect gap=0.153) |
| `volcano` | `105` | **survived** (none) | **survived** (none) | **survived** (none) | 10 | 0.097 | Quantum vs Mixture diverged on 10 steps (max order-effect gap=0.097) |
| `volcano` | `106` | **survived** (none) | **survived** (none) | **survived** (none) | 12 | 0.035 | Quantum vs Mixture diverged on 12 steps (max order-effect gap=0.035) |
| `volcano` | `107` | **survived** (none) | **survived** (none) | **survived** (none) | 0 | 0.061 | Aligned trajectory across Quantum and Classical Mixture |
| `volcano` | `108` | **survived** (none) | **survived** (none) | **survived** (none) | 0 | 0.330 | Aligned trajectory across Quantum and Classical Mixture |
| `volcano` | `109` | **survived** (none) | **survived** (none) | **survived** (none) | 6 | 0.073 | Quantum vs Mixture diverged on 6 steps (max order-effect gap=0.073) |
| `volcano` | `110` | **survived** (none) | **survived** (none) | **survived** (none) | 9 | 0.093 | Quantum vs Mixture diverged on 9 steps (max order-effect gap=0.093) |
| `volcano` | `111` | **survived** (none) | **survived** (none) | **survived** (none) | 7 | 0.178 | Quantum vs Mixture diverged on 7 steps (max order-effect gap=0.179) |
| `island` | `100` | **survived** (none) | **survived** (none) | **survived** (none) | 5 | 0.058 | Quantum vs Mixture diverged on 5 steps (max order-effect gap=0.058) |
| `island` | `101` | **survived** (none) | **survived** (none) | **survived** (none) | 22 | 0.012 | Quantum vs Mixture diverged on 22 steps (max order-effect gap=0.012) |
| `island` | `102` | **survived** (none) | **survived** (none) | **survived** (none) | 12 | 0.064 | Quantum vs Mixture diverged on 12 steps (max order-effect gap=0.064) |
| `island` | `103` | **survived** (none) | **survived** (none) | **survived** (none) | 15 | 0.083 | Quantum vs Mixture diverged on 15 steps (max order-effect gap=0.083) |
| `island` | `104` | **survived** (none) | **survived** (none) | **survived** (none) | 6 | 0.025 | Quantum vs Mixture diverged on 6 steps (max order-effect gap=0.025) |
| `island` | `105` | **survived** (none) | **survived** (none) | **survived** (none) | 8 | 0.060 | Quantum vs Mixture diverged on 8 steps (max order-effect gap=0.060) |
| `island` | `106` | **survived** (none) | **survived** (none) | **survived** (none) | 11 | 0.021 | Quantum vs Mixture diverged on 11 steps (max order-effect gap=0.021) |
| `island` | `107` | **survived** (none) | **survived** (none) | **survived** (none) | 14 | 0.040 | Quantum vs Mixture diverged on 14 steps (max order-effect gap=0.040) |
| `island` | `108` | **survived** (none) | **survived** (none) | **survived** (none) | 5 | 0.038 | Quantum vs Mixture diverged on 5 steps (max order-effect gap=0.038) |
| `island` | `109` | **survived** (none) | **survived** (none) | **survived** (none) | 14 | 0.026 | Quantum vs Mixture diverged on 14 steps (max order-effect gap=0.026) |
| `island` | `110` | **survived** (none) | **survived** (none) | **survived** (none) | 7 | 0.081 | Quantum vs Mixture diverged on 7 steps (max order-effect gap=0.081) |
| `island` | `111` | **survived** (none) | **survived** (none) | **survived** (none) | 9 | 0.016 | Quantum vs Mixture diverged on 9 steps (max order-effect gap=0.016) |

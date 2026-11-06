"""Constants for the quantum mind (TECH_A_BUILD_PLAN.md Section 4.8).

Consolidates everything that was previously local to mind/belief.py and
mind/decoherence.py, per the Stage 4 goal. Those modules re-export the
names tests already import from them (see mind/tests/test_belief.py).
"""
import numpy as np

from contracts import ACTIONS

# D1: PROTECT = {hide} (evacuation); everything else is carry-on.
PROTECT = ["hide"]
CARRY_ON = [a for a in ACTIONS if a not in PROTECT]

# Threat events stripped out of cf_safe / folded into cf_danger (Section 4.2).
THREAT_EVENTS = {
    "storm", "animal", "injury", "cold_night",
    "tremor", "gas_plume", "eruption", "ash_fall",
}

# Section 4.4: event -> (rotation axis, angle). No angle is +-pi/2.
EVENT_GATES = {
    "tremor": ("ry", np.pi / 3),
    "gas_plume": ("rx", 3 * np.pi / 5),
    "storm": ("ry", np.pi / 3),
    "animal": ("ry", np.pi / 3),
    "injury": ("rx", 2 * np.pi / 3),
    "cold_night": ("rx", np.pi / 6),
    "find_food": ("ry", -np.pi / 4),
}
COLLAPSE_EVENTS = {"eruption", "ash_fall"}

# Section 4.2: counterfactual safety values and clamp for q_S, q_D.
CF_SAFE_SAFETY = 0.95
CF_DANGER_SAFETY = 0.05
Q_CLAMP = (0.02, 0.98)

# D6: exact solve against Tversky & Shafir (1992) 69/59/36; rounds to -0.7854.
ETA = -0.7853897988344999

# D5: lam = clamp((stress - STRESS_FLOOR) / STRESS_SPAN, 0, 1).
STRESS_FLOOR = 0.2
STRESS_SPAN = 0.7

# Dephasing per decision slot, or per unit of time. "per_slot" is the paper's model.
# REFERENCE_SLOT_SECONDS is the 2 h step that lam(stress) was defined on.
DEPHASING_MODE = "per_slot"
REFERENCE_SLOT_SECONDS = 7200.0

# Opt-in comparison arm, fitted by mind/human_tests/extended.py on disjunction.csv only.
# Median of the split-half fits. Nothing in the simulator was used to choose it.
MARKOV_HESITATION = 0.2396072020948411

# Opt-in qr_unitary_superposed: decision start angle per unit of |x|, in radians. Same source.
SUPERPOSED_PHI = -0.2705260340591211

# D3 / Section 4.7.
ORDER_GAP_REPORT_THRESHOLD = 0.02
DECISION_RULE = "argmax"

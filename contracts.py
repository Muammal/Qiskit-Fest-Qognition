"""
contracts.py - Frozen Interfaces and Stubs for Stranded
Owned by Tech C (Integration, Contracts, Engine).

Agreed Tuesday. All team members code against these contracts.
Nobody waits on anybody; use stubs until actual modules are plugged in.
"""

from typing import Any, Dict, List, Optional
import random

# -----------------------------------------------------------------------------
# Constants & Enums
# -----------------------------------------------------------------------------
ACTIONS: List[str] = [
    "forage",
    "drink",
    "build_shelter",
    "rest",
    "explore",
    "craft",
    "hide"
]

EVENTS: List[str] = [
    "storm",
    "injury",
    "find_food",
    "animal",
    "cold_night",
    "none"
]

TILE_TYPES: Dict[int, str] = {
    0: "water",
    1: "plains",
    2: "forest",
    3: "mountain",
    4: "shelter"
}

# -----------------------------------------------------------------------------
# State Contract
# -----------------------------------------------------------------------------
# A valid state dictionary conforms to:
# {
#   "day": int,
#   "hour": int (0-23),
#   "pos": [int, int] (e.g. [x, y] in [0, 39]),
#   "needs": {
#       "hunger": float (0.0 to 1.0, 1.0 = fully satiated, 0.0 = starving),
#       "thirst": float (0.0 to 1.0, 1.0 = fully hydrated, 0.0 = dehydrated),
#       "warmth": float (0.0 to 1.0, 1.0 = warm, 0.0 = freezing),
#       "energy": float (0.0 to 1.0, 1.0 = rested, 0.0 = exhausted),
#       "safety": float (0.0 to 1.0, 1.0 = completely secure, 0.0 = imminent peril),
#       "morale": float (0.0 to 1.0, 1.0 = hopeful, 0.0 = despairing)
#   },
#   "stress": float (0.0 to 1.0),
#   "injured": bool,
#   "inventory": Dict[str, int] (e.g. {"wood": 2, "food": 1, "berries": 3}),
#   "recent_events": List[str] (last 3 events in chronological order, e.g. ["injury", "storm"])
# }


def validate_state(state: Dict[str, Any]) -> bool:
    """Verifies that a state dict strictly conforms to the frozen interface."""
    required_keys = {"day", "hour", "pos", "needs", "stress", "injured", "inventory", "recent_events"}
    if not required_keys.issubset(state.keys()):
        missing = required_keys - set(state.keys())
        raise ValueError(f"[ContractViolation] State missing required keys: {missing}")

    required_needs = {"hunger", "thirst", "warmth", "energy", "safety", "morale"}
    if not required_needs.issubset(state["needs"].keys()):
        missing = required_needs - set(state["needs"].keys())
        raise ValueError(f"[ContractViolation] State needs missing required keys: {missing}")

    if not isinstance(state["pos"], (list, tuple)) or len(state["pos"]) != 2:
        raise ValueError(f"[ContractViolation] State pos must be [x, y], got {state['pos']}")

    return True


def validate_decision(decision: Dict[str, Any]) -> bool:
    """Verifies that a decision dict strictly conforms to the frozen interface."""
    required_keys = {"action", "probs", "reason"}
    if not required_keys.issubset(decision.keys()):
        missing = required_keys - set(decision.keys())
        raise ValueError(f"[ContractViolation] Decision missing required keys: {missing}")

    if decision["action"] not in ACTIONS:
        raise ValueError(f"[ContractViolation] Action '{decision['action']}' not in ACTIONS: {ACTIONS}")

    if not isinstance(decision["probs"], dict):
        raise ValueError("[ContractViolation] Decision 'probs' must be a dict mapping action to probability.")

    return True


# -----------------------------------------------------------------------------
# Function Stubs (Replaced in Phase 2 by Tech A and Tech B)
# -----------------------------------------------------------------------------

def get_prior(state: Dict[str, Any]) -> Dict[str, float]:
    """
    Tech B Responsibility.
    Returns baseline human habit probability distribution over ACTIONS
    derived from published American Time Use Survey (ATUS) summary tables.
    
    Stub Implementation: Context-aware uniform baseline.
    """
    validate_state(state)
    needs = state["needs"]
    hour = state["hour"]
    
    # Simple heuristic fallback prior based on urgent needs
    raw_priors = {act: 1.0 for act in ACTIONS}
    
    # Thirst is urgent
    if needs["thirst"] < 0.3:
        raw_priors["drink"] += 4.0
    # Hunger is urgent
    if needs["hunger"] < 0.3:
        raw_priors["forage"] += 3.0
    # Cold / Low warmth -> build shelter or rest
    if needs["warmth"] < 0.4:
        raw_priors["build_shelter"] += 3.5
        raw_priors["rest"] += 2.0
    # Night time -> sleep
    if hour >= 21 or hour <= 5:
        raw_priors["rest"] += 3.5
    # Threat / low safety -> hide
    if needs["safety"] < 0.3 or "storm" in state.get("recent_events", []):
        raw_priors["hide"] += 3.0

    total = sum(raw_priors.values())
    return {k: round(v / total, 4) for k, v in raw_priors.items()}


def classical_decide(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tech B Responsibility.
    Baseline classical human decision model with no quantum interference or order effects.
    
    Stub Implementation: Deterministic argmax of ATUS priors with heuristic fallback.
    """
    validate_state(state)
    priors = get_prior(state)
    chosen_action = max(priors.items(), key=lambda item: item[1])[0]
    
    decision = {
        "action": chosen_action,
        "probs": priors,
        "reason": f"Classical rational choice: highest prior utility for {chosen_action} (p={priors[chosen_action]:.2f})"
    }
    validate_decision(decision)
    return decision


def quantum_decide(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tech A Responsibility.
    2-Qubit Quantum Cognition Decision Engine (Qiskit 2.x).
    Applies non-commuting unitary rotation gates for each recent event in order,
    incorporating decoherence under stress, followed by projective measurement.
    
    Stub Implementation: Non-commuting sequential rotation stub with explainability reason.
    """
    validate_state(state)
    recent = state.get("recent_events", [])
    stress = state.get("stress", 0.0)
    priors = get_prior(state)

    # Quantum cognition order effect simulation stub:
    # Event order (A then B vs B then A) changes resulting belief interference
    probs = dict(priors)
    reason = "Quantum baseline prior measurement"

    if recent:
        last_event = recent[-1]
        prior_event = recent[-2] if len(recent) > 1 else "none"

        if last_event == "storm" and prior_event == "injury":
            # Quantum constructive interference on safety
            probs["hide"] = round(probs.get("hide", 0.1) + 0.45, 4)
            probs["explore"] = round(max(0.01, probs.get("explore", 0.1) - 0.2), 4)
            reason = "Order effect: injury followed by storm induces constructive fear interference -> prioritizing safety"
        elif last_event == "injury" and prior_event == "storm":
            # Different order produces distinct cognitive state
            probs["rest"] = round(probs.get("rest", 0.1) + 0.40, 4)
            probs["hide"] = round(max(0.01, probs.get("hide", 0.1) - 0.1), 4)
            reason = "Order effect: storm then injury shifts cognitive state toward physical recuperation"
        elif last_event == "animal":
            probs["hide"] = round(probs.get("hide", 0.1) + 0.35, 4)
            probs["build_shelter"] = round(probs.get("build_shelter", 0.1) + 0.2, 4)
            reason = "Predator detection: belief rotation collapsed toward defensive evasion"

    # Normalize probabilities
    total = sum(probs.values())
    norm_probs = {k: round(v / total, 4) for k, v in probs.items()}

    # Stress washes out quantum interference (decoherence towards classical/mixed state)
    if stress > 0.4:
        decoherence_gamma = min(1.0, (stress - 0.4) / 0.5)
        blended_probs = {}
        for act in ACTIONS:
            pure_p = norm_probs.get(act, 0.0)
            class_p = priors.get(act, 1.0 / len(ACTIONS))
            blended_probs[act] = (1.0 - decoherence_gamma) * pure_p + decoherence_gamma * class_p
        total_p = sum(blended_probs.values())
        norm_probs = {k: round(v / total_p, 4) for k, v in blended_probs.items()}
        pct_decay = int(decoherence_gamma * 100)
        reason += f" [Decoherence: stress {stress:.2f} washes out {pct_decay}% quantum interference]"

    # Weighted choice based on quantum state probabilities
    actions = list(norm_probs.keys())
    weights = list(norm_probs.values())
    chosen_action = random.choices(actions, weights=weights, k=1)[0]

    decision = {
        "action": chosen_action,
        "probs": norm_probs,
        "reason": reason
    }
    validate_decision(decision)
    return decision


def explore_step(pos: List[int], world: Any, mode: str = "quantum") -> List[int]:
    """
    Tech B Responsibility (Optional / Stretch Goal).
    Discrete step generator for map exploration.
    mode: "quantum" (quantum walk / superposition spread) or "random" (classical brownian walk).
    
    Stub Implementation: Valid cardinal move [dx, dy].
    """
    x, y = pos
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    dx, dy = random.choice(directions)
    return [max(0, min(39, x + dx)), max(0, min(39, y + dy))]

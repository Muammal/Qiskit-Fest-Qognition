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
    "none",
    "tremor", "gas_plume", "eruption", "ash_fall"
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
    """Tech B responsibility: priors from published ATUS tables. Heuristic stub until then."""
    validate_state(state)
    needs = state["needs"]
    hour = state["hour"]
    
    # Simple heuristic fallback prior based on urgent needs
    raw_priors = {act: 1.0 for act in ACTIONS}
    wood = state.get("inventory", {}).get("wood", 0)
    
    # Thirst is urgent
    if needs["thirst"] < 0.3:
        raw_priors["drink"] += 40.0
    elif needs["thirst"] < 0.5:
        raw_priors["drink"] += 12.0

    # Hunger is urgent
    if needs["hunger"] < 0.3:
        raw_priors["forage"] += 8.0
    elif needs["hunger"] < 0.5:
        raw_priors["forage"] += 4.0

    # Cold / Low warmth -> build shelter if wood available, or forage for timber
    if needs["warmth"] < 0.4:
        if wood >= 2:
            raw_priors["build_shelter"] += 12.0
        else:
            raw_priors["forage"] += 10.0
        raw_priors["rest"] += 2.0
    elif needs["warmth"] < 0.65:
        if wood >= 2:
            raw_priors["build_shelter"] += 9.0
        else:
            raw_priors["forage"] += 6.0

    # Daytime exploration drive when vitals are comfortable
    if 8 <= hour <= 18 and needs["energy"] > 0.4 and needs["thirst"] >= 0.4 and needs["hunger"] >= 0.4:
        raw_priors["explore"] += 3.0

    # Night time -> sleep
    if hour >= 21 or hour <= 5:
        raw_priors["rest"] += 6.0
    # Threat / low safety -> hide
    if needs["safety"] < 0.3 or "storm" in state.get("recent_events", []):
        raw_priors["hide"] += 4.0

    if any(e in ("tremor", "gas_plume", "eruption", "ash_fall") for e in state["recent_events"]):
        raw_priors["hide"] += 6.0  # assumption: warning-sensitive stub preference

    if needs["energy"] < .3:
        raw_priors["rest"] += 15.0
    total = sum(raw_priors.values())
    return {k: round(v / total, 4) for k, v in raw_priors.items()}


def classical_decide(state: Dict[str, Any]) -> Dict[str, Any]:
    """Tech B responsibility: classical baseline. Deterministic heuristic stub; no ATUS priors are loaded."""
    validate_state(state)
    priors = get_prior(state)
    chosen_action = max(priors.items(), key=lambda item: item[1])[0]
    
    decision = {
        "action": chosen_action,
        "probs": priors,
        "reason": f"Classical stub choice: highest prior utility for {chosen_action} (p={priors[chosen_action]:.2f})"
    }
    validate_decision(decision)
    return decision


def _quantum_decide_stub(state: Dict[str, Any]) -> Dict[str, Any]:
    """Heuristic stub, kept as a fallback if mind.quantum_mind is unavailable."""
    validate_state(state)
    recent = state.get("recent_events", [])
    stress = state.get("stress", 0.0)
    priors = get_prior(state)

    # Quantum cognition order effect simulation stub:
    # Event order (A then B vs B then A) changes resulting belief interference
    probs = dict(priors)
    reason = "Quantum-labelled classical heuristic stub; no circuit or hardware execution"

    if recent:
        last_event = recent[-1]
        prior_event = recent[-2] if len(recent) > 1 else "none"

        if last_event == "gas_plume" and prior_event == "tremor":
            probs["hide"] += .45
            reason = "Stub Order effect: tremor then gas plume strengthens evacuation preference"
        elif last_event == "tremor" and prior_event == "gas_plume":
            probs["rest"] += .3
            reason = "Stub Order effect: gas plume then tremor favours recovery"
        elif last_event == "storm" and prior_event == "injury":
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
            reason = "Stub boar encounter shifts probabilities toward defensive evasion"

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

    # assumption: both placeholders use the same survival competence; order changes preferences.
    chosen_action = max(norm_probs, key=norm_probs.get)
    if state["needs"]["thirst"] < .3:
        chosen_action = "drink"
    elif state["needs"]["warmth"] < .4:
        if state.get("inventory", {}).get("wood", 0) >= 2:
            chosen_action = "build_shelter"
        else:
            chosen_action = "forage"

    decision = {
        "action": chosen_action,
        "probs": norm_probs,
        "reason": "Stub: " + reason
    }
    validate_decision(decision)
    return decision


try:
    from mind.quantum_mind import quantum_decide as _quantum_decide_impl
except ImportError:
    _quantum_decide_impl = None


def quantum_decide(state: Dict[str, Any]) -> Dict[str, Any]:
    """Tech A responsibility: 2-qubit decision circuit.

    Delegates to mind.quantum_mind.quantum_decide; falls back to the
    heuristic stub if mind/ is unavailable.
    """
    if _quantum_decide_impl is not None:
        return _quantum_decide_impl(state)
    return _quantum_decide_stub(state)


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


def load_seeds() -> list[int]:
    """Stub seed list until teammate data is integrated."""
    return list(range(20))

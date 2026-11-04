"""The decision function (TECH_A_BUILD_PLAN.md Section 4.6-4.7).

quantum_decide / classical_mixture_decide are what contracts.quantum_decide
delegates to (Stage 5). Stateless: belief is rebuilt from `state` on every
call, so results depend only on the input state (and, for decision_rule
"sample", the caller's global `random` state - SimulationEngine.step
isolates that per seed).
"""
import copy
import random

import contracts

from mind.belief import prepare_belief, run_events
from mind.config import (
    CARRY_ON,
    CF_DANGER_SAFETY,
    CF_SAFE_SAFETY,
    DECISION_RULE,
    ETA,
    ORDER_GAP_REPORT_THRESHOLD,
    PROTECT,
    Q_CLAMP,
    THREAT_EVENTS,
)
from mind.decoherence import decoherence_strength
from mind.model import bloch_vector, p_protect_closed_form

__all__ = [
    "decision_probs", "quantum_decide", "classical_mixture_decide",
    "decoherence_strength",
]


def _clamp_q(value):
    lo, hi = Q_CLAMP
    return min(hi, max(lo, value))


def _cf_safe_state(state):
    cf = copy.deepcopy(state)
    cf["needs"]["safety"] = CF_SAFE_SAFETY
    cf["recent_events"] = ["none" if e in THREAT_EVENTS else e for e in cf["recent_events"]]
    return cf


def _cf_danger_state(state):
    cf = copy.deepcopy(state)
    cf["needs"]["safety"] = CF_DANGER_SAFETY
    cf["recent_events"] = (list(cf["recent_events"]) + ["eruption"])[-3:]
    return cf


def _q_safe_danger(state):
    q_S = sum(contracts.get_prior(_cf_safe_state(state)).get(a, 0.0) for a in PROTECT)
    q_D = sum(contracts.get_prior(_cf_danger_state(state)).get(a, 0.0) for a in PROTECT)
    return _clamp_q(q_S), _clamp_q(q_D)


def _p_protect_for_events(safety, events, lam, q_S, q_D):
    rho = run_events(prepare_belief(safety), events, lam)
    x, _y, z = bloch_vector(rho)
    p = (1 - z) / 2
    return p, x, p_protect_closed_form(p, x, q_S, q_D, ETA)


def decision_probs(p_protect, prior):
    """Section 4.6: split the protect/carry-on probability by prior within
    each group."""
    protect_total = sum(prior.get(a, 0.0) for a in PROTECT) or 1e-12
    carry_total = sum(prior.get(a, 0.0) for a in CARRY_ON) or 1e-12

    probs = {}
    for a in PROTECT:
        probs[a] = p_protect * prior.get(a, 0.0) / protect_total
    for a in CARRY_ON:
        probs[a] = (1 - p_protect) * prior.get(a, 0.0) / carry_total
    return probs


def _apply_reflex(state, action):
    needs = state["needs"]
    if needs["thirst"] < 0.3:
        return "drink", "thirst"
    if needs["warmth"] < 0.4:
        if state.get("inventory", {}).get("wood", 0) >= 2:
            return "build_shelter", "warmth"
        return "forage", "warmth"
    return action, None


def _choose_action(probs, decision_rule):
    if decision_rule == "sample":
        actions = list(probs.keys())
        weights = list(probs.values())
        return random.choices(actions, weights=weights, k=1)[0]
    return max(probs, key=probs.get)


def _order_gap(state, lam, q_S, q_D):
    events = state["recent_events"]
    non_none = [i for i, e in enumerate(events) if e != "none"]
    if len(non_none) < 2:
        return None, None, None

    i_b, i_a = non_none[-1], non_none[-2]  # i_a before i_b, chronologically
    swapped = list(events)
    swapped[i_a], swapped[i_b] = swapped[i_b], swapped[i_a]

    _p, _x, p_protect_original = _p_protect_for_events(
        state["needs"]["safety"], events, lam, q_S, q_D)
    _p2, _x2, p_protect_swapped = _p_protect_for_events(
        state["needs"]["safety"], swapped, lam, q_S, q_D)

    gap = p_protect_original - p_protect_swapped
    return gap, events[i_a], events[i_b]


def _decide(state, *, force_lam=None, suppress_order_gap=False, decision_rule=None):
    contracts.validate_state(state)
    decision_rule = decision_rule or DECISION_RULE

    prior = contracts.get_prior(state)
    q_S, q_D = _q_safe_danger(state)
    stress = state["stress"]
    lam = decoherence_strength(stress) if force_lam is None else force_lam

    p, x, p_protect = _p_protect_for_events(
        state["needs"]["safety"], state["recent_events"], lam, q_S, q_D)
    p_classical = (1 - p) * q_S + p * q_D

    probs = decision_probs(p_protect, prior)
    rule_action = _choose_action(probs, decision_rule)
    action, reflex = _apply_reflex(state, rule_action)

    reason = (
        f"Quantum deliberation: q_safe={q_S:.3f}, q_danger={q_D:.3f}, "
        f"p_danger={p:.3f}, P(protect)={p_protect:.3f} (classical={p_classical:.3f})"
    )

    gap = None
    if not suppress_order_gap:
        gap, event_a, event_b = _order_gap(state, lam, q_S, q_D)
        if gap is not None and abs(gap) > ORDER_GAP_REPORT_THRESHOLD:
            pct = gap * 100
            reason += (
                f" Order effect: {event_a} then {event_b} shifts "
                f"P(protect) by {pct:+.1f}%"
            )

    if lam > 0:
        reason += f" Decoherence: stress {stress:.2f}, dephasing {lam * 100:.0f}% per step"

    if reflex:
        reason = f"Reflex ({reflex}) overrides {rule_action} -> {action}. " + reason

    decision = {
        "action": action,
        "probs": probs,
        "reason": reason,
        "quantum": {
            "p_danger": p,
            "p_protect": p_protect,
            "p_classical": p_classical,
            "lam": lam,
            "q_safe": q_S,
            "q_danger": q_D,
            "order_gap": gap,
            "reflex": reflex,
            "decision_rule": decision_rule,
        },
    }
    contracts.validate_decision(decision)
    return decision


def quantum_decide(state):
    return _decide(state)


def classical_mixture_decide(state):
    """quantum_decide with lam forced to 1 (D-control): no order-gap text."""
    return _decide(state, force_lam=1.0, suppress_order_gap=True)

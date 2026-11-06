"""The decision function (TECH_A_BUILD_PLAN.md Section 4.6-4.7).

quantum_decide / classical_mixture_decide are what contracts.quantum_decide
delegates to (Stage 5). Stateless: belief is rebuilt from `state` on every
call, so results depend only on the input state (and, for decision_rule
"sample", the caller's global `random` state - SimulationEngine.step
isolates that per seed).

Supports selectable research-paper-backed quantum cognition models via
`cognition_model`:
- `"default"` (or `"qr_unitary"`): 2-qubit SO(4) deliberation unitary calibrated
  to Tversky & Shafir (1992).
- `"busemeyer_hamiltonian"`: Busemeyer (2009/2012) continuous-time 2-qubit
  Hamiltonian U(t) = exp(-i*t*(pi/2)*(H_a + H_c)) (`jbusemey/ChoiceModeling`).
- `"qlbn_entropy"`: Huang et al. (2019) & Moreira & Wichert (2016) parameter-free
  Quantum-Like Bayesian Network using belief entropy (`Insight137/insight137-eap`).
- `"lindblad_open"`: Broekaert et al. (2020) & Yearsley & Busemeyer (2016) GKSL
  Lindblad open-system master equation (`hwilner/open-system-decision-dynamics`).
- `"no_interference"`: the same belief and events with the interference term
  forced to 0. Separates interference from coherence.
- `"qr_unitary_superposed"`: `qr_unitary` with the decision qubit started in a
  superposition that grows with belief coherence, so a settled belief still
  gives q_safe and q_danger exactly. See mind/model.py.

Opt-in comparison arms, none used by default: `classical_no_interference_decide`
and `markov_hesitation_decide`.
"""

import copy
import random

import contracts

from mind.belief import prepare_belief, run_events
from mind.cognition_models import (
    belief_degree_huang,
    evolve_lindblad,
    p_protect_busemeyer,
    p_protect_qlbn,
)
from mind.config import (
    CARRY_ON,
    CF_DANGER_SAFETY,
    CF_SAFE_SAFETY,
    DECISION_RULE,
    DEPHASING_MODE,
    ETA,
    MARKOV_HESITATION,
    ORDER_GAP_REPORT_THRESHOLD,
    PROTECT,
    Q_CLAMP,
    THREAT_EVENTS,
)
from mind.decoherence import decoherence_strength, lam_for_interval
from mind.model import bloch_vector, p_protect_closed_form, p_protect_superposed

__all__ = [
    "decision_probs",
    "quantum_decide",
    "classical_mixture_decide",
    "classical_no_interference_decide",
    "markov_hesitation_decide",
    "markov_p_protect",
    "decoherence_strength",
    "order_gap_at_lambda",
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


def _p_protect_for_events(safety, events, lam, q_S, q_D, cognition_model="default", eta=ETA):
    rho = run_events(prepare_belief(safety), events, lam)
    if cognition_model == "lindblad_open" and lam > 0.0:
        rho = evolve_lindblad(
            rho,
            omega=0.35 * (1.0 - lam),
            dephase_rate=1.2 * lam,
            commit_rate=0.15 * lam,
            t_final=1.0,
            n_steps=20,
        )
    x, y, z = bloch_vector(rho)
    p = (1 - z) / 2

    if cognition_model == "busemeyer_hamiltonian":
        p_prot = p_protect_busemeyer(rho, q_S, q_D, gamma=0.65, t=1.0)
    elif cognition_model == "qlbn_entropy":
        p_prot, _db = p_protect_qlbn(p, x, q_S, q_D)
    elif cognition_model == "no_interference":
        p_prot = p_protect_closed_form(p, x, q_S, q_D, 0.0)
    elif cognition_model == "qr_unitary_superposed":
        p_prot = p_protect_superposed(p, x, q_S, q_D, eta)
    else:
        p_prot = p_protect_closed_form(p, x, q_S, q_D, eta)

    return p, x, float(p_prot), (float(x), float(y), float(z)), rho


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


def markov_p_protect(p, q_S, q_D, hesitation=MARKOV_HESITATION):
    """Classical wait-and-see: with chance h * 4p(1-p), hold off and do not protect.

    A settled belief (p = 0 or 1) never hesitates, so q_safe and q_danger are
    reached exactly, as they are by the quantum mind. There is no interference.
    """
    return (1 - hesitation * 4 * p * (1 - p)) * ((1 - p) * q_S + p * q_D)


def _order_gap(state, lam, q_S, q_D, cognition_model="default", eta=ETA):
    events = state["recent_events"]
    non_none = [i for i, e in enumerate(events) if e != "none"]
    if len(non_none) < 2:
        return None, None, None

    i_b, i_a = non_none[-1], non_none[-2]  # i_a before i_b, chronologically
    swapped = list(events)
    swapped[i_a], swapped[i_b] = swapped[i_b], swapped[i_a]

    _p, _x, p_protect_original, _b1, _r1 = _p_protect_for_events(state["needs"]["safety"], events, lam, q_S, q_D, cognition_model=cognition_model, eta=eta)
    _p2, _x2, p_protect_swapped, _b2, _r2 = _p_protect_for_events(state["needs"]["safety"], swapped, lam, q_S, q_D, cognition_model=cognition_model, eta=eta)

    gap = p_protect_original - p_protect_swapped
    return gap, events[i_a], events[i_b]


def _decide(
    state,
    *,
    force_lam=None,
    suppress_order_gap=False,
    decision_rule=None,
    cognition_model="default",
    eta=ETA,
    dephasing_mode=DEPHASING_MODE,
    hesitation=None,
):
    contracts.validate_state(state)
    decision_rule = decision_rule or DECISION_RULE

    prior = contracts.get_prior(state)
    q_S, q_D = _q_safe_danger(state)
    stress = state["stress"]
    if force_lam is not None:
        lam = force_lam
    elif dephasing_mode == "per_time" and "dt_seconds" in state:
        lam = lam_for_interval(stress, state["dt_seconds"])
    else:
        lam = decoherence_strength(stress)

    p, x, p_protect, bloch, rho = _p_protect_for_events(
        state["needs"]["safety"],
        state["recent_events"],
        lam,
        q_S,
        q_D,
        cognition_model=cognition_model,
        eta=eta,
    )
    p_classical = (1 - p) * q_S + p * q_D
    if hesitation is not None:
        p_protect = markov_p_protect(p, q_S, q_D, hesitation)

    # Compute companion paper-backed metrics for diagnostic transparency
    d_b_huang = belief_degree_huang(p, q_S, q_D)
    p_busemeyer = p_protect_busemeyer(rho, q_S, q_D, gamma=0.65, t=1.0)

    probs = decision_probs(p_protect, prior)
    rule_action = _choose_action(probs, decision_rule)
    action, reflex = _apply_reflex(state, rule_action)

    reason = f"Quantum deliberation: q_safe={q_S:.3f}, q_danger={q_D:.3f}, p_danger={p:.3f}, P(protect)={p_protect:.3f} (classical={p_classical:.3f})"

    gap = None
    if not suppress_order_gap:
        gap, event_a, event_b = _order_gap(state, lam, q_S, q_D, cognition_model=cognition_model, eta=eta)
        if gap is not None and abs(gap) > ORDER_GAP_REPORT_THRESHOLD:
            pct = gap * 100
            reason += f" Order effect: {event_a} then {event_b} shifts P(protect) by {pct:+.1f}%"

    if lam > 0:
        reason += f" Decoherence: stress {stress:.2f}, dephasing {lam * 100:.0f}% per step"

    if reflex:
        reason = f"Reflex ({reflex}) overrides {rule_action} -> {action}. " + reason

    decision = {
        "action": action,
        "probs": probs,
        "reason": reason,
        "quantum": {
            "p_danger": float(p),
            "p_protect": float(p_protect),
            "p_classical": float(p_classical),
            "coherence": float(abs(x)),
            "bloch": list(bloch),
            "lam": float(lam),
            "q_safe": float(q_S),
            "q_danger": float(q_D),
            "order_gap": float(gap) if gap is not None else None,
            "reflex": reflex,
            "decision_rule": decision_rule,
            "cognition_model": cognition_model,
            "d_b_huang": float(d_b_huang),
            "p_protect_busemeyer": float(p_busemeyer),
        },
    }
    contracts.validate_decision(decision)
    return decision


def order_gap_at_lambda(state, first="tremor", second="gas_plume", lam=0.0):
    """P(protect) for (first, second) minus (second, first), from `state`, at a fixed lam."""
    forward = _decide(dict(state, recent_events=[first, second]), force_lam=lam, suppress_order_gap=True)
    reverse = _decide(dict(state, recent_events=[second, first]), force_lam=lam, suppress_order_gap=True)
    return forward["quantum"]["p_protect"] - reverse["quantum"]["p_protect"]


def quantum_decide(state, cognition_model="default", dephasing_mode=DEPHASING_MODE):
    return _decide(state, cognition_model=cognition_model, dephasing_mode=dephasing_mode)


def classical_mixture_decide(state):
    """quantum_decide with lam forced to 1 (D-control): no order-gap text."""
    return _decide(state, force_lam=1.0, suppress_order_gap=True)


def classical_no_interference_decide(state):
    """Same belief, events and dephasing as quantum_decide, with k forced to 0.

    Coherence still moves the belief, so order effects through P(danger)
    survive. Only the interference term in P(protect) is gone.
    """
    return _decide(state, cognition_model="no_interference")


def markov_hesitation_decide(state, hesitation=MARKOV_HESITATION):
    """A classical rival with a tuned delay: mixture belief, one hesitation parameter."""
    return _decide(state, force_lam=1.0, suppress_order_gap=True, hesitation=hesitation)


contracts._quantum_decide_impl = quantum_decide

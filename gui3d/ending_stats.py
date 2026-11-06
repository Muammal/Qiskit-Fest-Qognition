"""Pure-Python ending statistics engine (no Ursina imports).

Computes scenario-tailored ending metrics, letter grades, stars, quantum highlights,
and narrative epilogues from any timeline dictionary (live runs, recorded replays,
or demo-pack JSONs). Handles edge cases like death on step 0, missing fields, or empty steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HORIZON_STEPS = 36


@dataclass
class EndingStats:
    """Consolidated ending metrics for display in the ending cutscene."""

    outcome: str                        # "survived" | "died"
    cause: Optional[str]                # None | "pyroclastic_flow" | "dehydration" | ...
    scenario: str                       # "island" | "volcano" | ...
    seed: int
    mind: str                           # "quantum" | "classical"
    horizon: int
    steps_survived: int
    survival_pct: float                 # 0.0 to 100.0
    grade: str                          # "S", "A", "B", "C", "D"
    stars: int                          # 1, 2, or 3
    title: str                          # Scenario-specific ribbon banner
    epilogue: str                       # Narrative closing sentence
    freeze_pose: str                    # "happy" | "exhausted" | "fallen"
    celebration_particles: str          # "confetti" | "ash" | "sparkles"

    # Physiological & survival tracking
    final_vitals: Dict[str, float]
    lowest_vital_name: str
    lowest_vital_value: float
    lowest_vital_step: int
    shelters_built: int
    resources_gathered: int
    resources_consumed: int
    distance_traveled: int
    hazard_events_faced: int

    # Evacuation specifics (Volcano)
    reached_assembly: bool
    reached_safe_zone: bool
    steps_to_safety: Optional[int]
    margin_hours: Optional[int]
    warning_lead_hours: Optional[int]

    # Decisive moment (if fatal)
    decisive_step: Optional[int]
    decisive_event: Optional[str]
    decisive_action: Optional[str]
    decisive_reason: Optional[str]

    # Quantum cognition highlights
    order_effects_triggered: int
    decoherence_episodes: int
    divergence_count: int
    divergence_pct: float

    # Decision timeline strip: [(step, action, event, color_tag)]
    timeline_strip: List[Tuple[int, str, str, str]] = field(default_factory=list)


def calculate_grade_and_stars(outcome: str, steps: int, horizon: int, final_vitals: Dict[str, float]) -> Tuple[str, int]:
    """Determine tiered letter grade (S/A/B/C/D) and 1-3 stars based on longevity and health."""
    if horizon <= 0:
        return "D", 1
    pct = (steps / horizon) * 100.0
    avg_vital = sum(final_vitals.values()) / max(1, len(final_vitals)) if final_vitals else 0.5

    if outcome == "survived":
        if pct >= 99.0 and avg_vital >= 0.70:
            return "S", 3
        elif pct >= 99.0:
            return "A", 3
        else:
            return "B", 2
    else:
        if pct >= 75.0:
            return "B", 2
        elif pct >= 40.0:
            return "C", 2
        elif pct >= 15.0:
            return "D", 1
        else:
            return "D", 1


def generate_title_and_epilogue(scenario: str, outcome: str, cause: Optional[str], grade: str, reached_assembly: bool) -> Tuple[str, str, str, str]:
    """Generates scenario title, epilogue, character freeze pose, and ending particle effect."""
    cause_str = (cause or "").lower()

    if outcome == "survived":
        if scenario == "volcano":
            if reached_assembly:
                title = "Evacuation Triumphant"
                epilogue = "Through ash, tremors, and blinding smoke, they found the coastal haven and lived to tell the tale."
            else:
                title = "Endured the Ash"
                epilogue = "The caldera quieted at dawn. Scathed but unbroken, they greeted the rescue vessels."
        else:
            title = "Rescued at Dawn"
            epilogue = "Against the untamed wilderness and tempest winds, their instinct endured until the horizon broke."
        pose = "happy" if grade in ("S", "A") else "exhausted"
        particles = "confetti"
    else:
        if "pyroclastic" in cause_str:
            title = "Lost to the Eruption"
            epilogue = "The superheated pyroclastic surge swept the ridge faster than human stride could flee."
        elif "lahar" in cause_str:
            title = "Claimed by the Mudflow"
            epilogue = "Rain remobilized the ash slopes into torrential mud, closing the escape corridor."
        elif "lava" in cause_str:
            title = "Consumed by Magma"
            epilogue = "Incandescent flows enveloped the valley route before refuge could be secured."
        elif "thirst" in cause_str or "dehydration" in cause_str:
            title = "Parched in the Ashfall"
            epilogue = "Contaminated streams and scorching heat depleted the last drops of vitality."
        elif "hunger" in cause_str or "starvation" in cause_str:
            title = "The Famine of the Wild"
            epilogue = "Exhausted resources and unyielding storms left no strength to forage anew."
        elif "cold" in cause_str or "hypothermia" in cause_str:
            title = "Frozen in the Gloom"
            epilogue = "Piercing winds stripped all warmth before a secure shelter could be raised."
        else:
            title = "The Island Claimed Them"
            epilogue = f"The unforgiving elements prevailed ({cause_str or 'exhaustion'}). Their footsteps fade into history."
        pose = "fallen"
        particles = "ash"

    return title, epilogue, pose, particles


def build_ending_stats(timeline: Dict[str, Any], other_mind_timeline: Optional[Dict[str, Any]] = None) -> EndingStats:
    """Builds comprehensive ending stats from a timeline dictionary.

    Safely handles edge cases including zero steps, missing nested dicts, or unrecorded fields.
    """
    world = timeline.get("world") or {}
    steps = timeline.get("steps") or []
    evac = timeline.get("evacuation") or {}

    outcome = str(timeline.get("outcome") or ("survived" if steps and len(steps) >= HORIZON_STEPS else "died"))
    cause = timeline.get("cause")
    scenario = str(world.get("scenario") or "volcano")
    seed = int(world.get("seed") or 0)
    mind = str(world.get("mind") or "quantum")
    horizon = int(world.get("horizon") or len(world.get("weather") or []) or HORIZON_STEPS)

    steps_survived = len(steps)
    survival_pct = round((steps_survived / max(1, horizon)) * 100.0, 1)

    # Vitals & lowest vital
    final_vitals = {
        "hunger": 0.5, "thirst": 0.5, "warmth": 0.5, "energy": 0.5, "safety": 0.5, "morale": 0.5
    }
    lowest_name = "safety"
    lowest_val = 1.0
    lowest_step = 0

    shelters_built = 0
    resources_gathered = 0
    resources_consumed = 0
    distance_traveled = 0
    hazard_events_faced = 0
    decisive_step: Optional[int] = None
    decisive_event: Optional[str] = None
    decisive_action: Optional[str] = None
    decisive_reason: Optional[str] = None

    order_effects_triggered = 0
    decoherence_episodes = 0
    timeline_strip: List[Tuple[int, str, str, str]] = []

    last_pos: Optional[List[int]] = None

    for i, s in enumerate(steps):
        st = s.get("state") or {}
        needs = st.get("needs") or {}
        if i == len(steps) - 1 and needs:
            final_vitals = {k: round(float(needs.get(k, 0.5)), 3) for k in final_vitals}

        # Track lowest vital
        for k, v in needs.items():
            val = float(v)
            if val < lowest_val:
                lowest_val = val
                lowest_name = k
                lowest_step = i

        # Movement distance
        pos = s.get("pos_after") or st.get("pos")
        if pos and last_pos:
            distance_traveled += abs(pos[0] - last_pos[0]) + abs(pos[1] - last_pos[1])
        last_pos = pos

        # Action tracking
        act = s.get("action", "rest")
        ev = s.get("event", "none")
        if act == "build_shelter":
            shelters_built += 1
        elif act in ("forage", "drink"):
            resources_gathered += 1

        if ev not in ("none", "calm"):
            hazard_events_faced += 1

        # Quantum diagnostics
        q = s.get("quantum") or {}
        if q.get("order_gap") is not None and abs(float(q.get("order_gap") or 0.0)) > 0.01:
            order_effects_triggered += 1
        if float(q.get("lam") or 0.0) >= 0.50:
            decoherence_episodes += 1

        # Timeline strip
        timeline_strip.append((i, act, ev, "danger" if ev not in ("none", "calm") else "normal"))

    # Decisive moment (last step if died)
    if outcome == "died" and steps:
        last_step = steps[-1]
        decisive_step = last_step.get("t", len(steps) - 1)
        decisive_event = last_step.get("event", "none")
        decisive_action = last_step.get("action", "rest")
        decisive_reason = last_step.get("reason", "")

    # Evacuation metrics
    reached_assembly = bool(evac.get("reached_assembly_step") is not None)
    reached_safe_zone = bool(evac.get("reached_safe_step") is not None)
    steps_to_safety = evac.get("reached_safe_step")
    margin_hours = evac.get("margin_hours")
    warning_lead_hours = evac.get("warning_lead_hours")

    # Divergence comparison against other mind if provided
    divergence_count = 0
    divergence_pct = 0.0
    if other_mind_timeline:
        other_steps = other_mind_timeline.get("steps") or []
        n_comp = min(len(steps), len(other_steps))
        for a, b in zip(steps[:n_comp], other_steps[:n_comp]):
            if a.get("action") != b.get("action"):
                divergence_count += 1
        divergence_pct = round((divergence_count / max(1, n_comp)) * 100.0, 1)

    grade, stars = calculate_grade_and_stars(outcome, steps_survived, horizon, final_vitals)
    title, epilogue, freeze_pose, celebration_particles = generate_title_and_epilogue(
        scenario, outcome, cause, grade, reached_assembly
    )

    return EndingStats(
        outcome=outcome,
        cause=cause,
        scenario=scenario,
        seed=seed,
        mind=mind,
        horizon=horizon,
        steps_survived=steps_survived,
        survival_pct=survival_pct,
        grade=grade,
        stars=stars,
        title=title,
        epilogue=epilogue,
        freeze_pose=freeze_pose,
        celebration_particles=celebration_particles,
        final_vitals=final_vitals,
        lowest_vital_name=lowest_name,
        lowest_vital_value=round(lowest_val, 3),
        lowest_vital_step=lowest_step,
        shelters_built=shelters_built,
        resources_gathered=resources_gathered,
        resources_consumed=resources_consumed,
        distance_traveled=distance_traveled,
        hazard_events_faced=hazard_events_faced,
        reached_assembly=reached_assembly,
        reached_safe_zone=reached_safe_zone,
        steps_to_safety=steps_to_safety,
        margin_hours=margin_hours,
        warning_lead_hours=warning_lead_hours,
        decisive_step=decisive_step,
        decisive_event=decisive_event,
        decisive_action=decisive_action,
        decisive_reason=decisive_reason,
        order_effects_triggered=order_effects_triggered,
        decoherence_episodes=decoherence_episodes,
        divergence_count=divergence_count,
        divergence_pct=divergence_pct,
        timeline_strip=timeline_strip,
    )


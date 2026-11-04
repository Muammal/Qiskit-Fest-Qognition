"""T0 agent body, and the adapter to the frozen contract. WS6 replaces the placeholder physiology."""
from __future__ import annotations

from dataclasses import dataclass, field

STATE_KEYS = {"day", "hour", "pos", "needs", "stress", "injured", "inventory", "recent_events"}
NEED_KEYS = {"hunger", "thirst", "warmth", "energy", "safety", "morale"}


@dataclass
class AgentBody:
    """Placeholder physiology. The rates are `assumption` values until ISO 7933 and friends arrive."""

    xy_m: tuple[float, float]
    tile: list[int]
    hour: int
    day: int = 1
    hunger: float = .85
    thirst: float = .80
    warmth: float = .90
    energy: float = .90
    safety: float = .85
    morale: float = .80
    stress: float = .15
    injured: bool = False
    alive: bool = True
    cause: str | None = None
    inventory: dict[str, int] = field(default_factory=lambda: {"wood": 0, "food": 0, "tools": 0})


def to_state(body: AgentBody, recent_events: list[str]) -> dict:
    """Exactly the frozen contract keys. Nothing else may reach a mind."""
    return {
        "day": body.day, "hour": body.hour, "pos": list(body.tile),
        "needs": {key: round(getattr(body, key), 3) for key in sorted(NEED_KEYS)},
        "stress": round(body.stress, 3), "injured": body.injured,
        "inventory": dict(body.inventory), "recent_events": list(recent_events),
    }

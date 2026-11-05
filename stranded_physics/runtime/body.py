"""The agent's body, and the adapter to the frozen contract. Water, food and fatigue come from domains/agent/physiology.py."""
from __future__ import annotations

from dataclasses import dataclass, field

from stranded_physics.domains.agent.physiology import Body, start_body

STATE_KEYS = {"day", "hour", "pos", "needs", "stress", "injured", "inventory", "recent_events"}
NEED_KEYS = {"hunger", "thirst", "warmth", "energy", "safety", "morale"}


@dataclass
class AgentBody:
    """Needs a mind can see, plus the hidden balance behind thirst, hunger and energy."""

    xy_m: tuple[float, float]
    tile: list[int]
    hour: int
    day: int = 1
    minute: int = 0  # Within the hour. The frozen contract shows minds whole hours only.
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
    balance: Body = field(init=False)
    recent_events: list[str] = field(default_factory=lambda: ["none", "none"])  # For showing only. The mind gets them through to_state.

    def __post_init__(self) -> None:
        self.balance = start_body(self.thirst, self.hunger, self.energy)

    @property
    def pos(self) -> list[int]:
        return self.tile

    @property
    def needs(self) -> dict[str, float]:
        return {key: getattr(self, key) for key in NEED_KEYS}

    @property
    def is_alive(self) -> bool:
        return self.alive

    @property
    def cause_of_death(self) -> str | None:
        return self.cause


def to_state(body: AgentBody, recent_events: list[str]) -> dict:
    """Exactly the frozen contract keys. Nothing else may reach a mind."""
    return {
        "day": body.day, "hour": body.hour, "pos": list(body.tile),
        "needs": {key: round(getattr(body, key), 3) for key in sorted(NEED_KEYS)},
        "stress": round(body.stress, 3), "injured": body.injured,
        "inventory": dict(body.inventory), "recent_events": list(recent_events),
    }

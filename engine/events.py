"""Persistent weather and common-random-number contextual events.

Numerical probabilities are scenario assumptions, not measured island rates.
Supports optional `scripted_events: dict[int, str] | None` for deterministic
order-effect counterfactual demonstrations (per 08-integration-notes.md §5).
"""

import random

VOLCANIC = ("tremor", "gas_plume", "eruption", "ash_fall")  # source: frozen contract event names
WEATHER_TRANSITIONS = {  # assumption: persistent two-hour weather transitions
    "calm": (0.78, 0.19, 0.03),
    "rain": (0.22, 0.65, 0.13),
    "storm": (0.12, 0.38, 0.50),
}


class EventGenerator:
    def __init__(self, seed=42, horizon=36, scripted_events=None):
        rng = random.Random(seed + 1009)  # assumption: independent weather stream
        self.weather, self.uniforms, self.cold_draws = [], [], []
        self.scripted_events = dict(scripted_events) if scripted_events else {}
        weather = "calm"
        for _ in range(horizon):
            weather = rng.choices(("calm", "rain", "storm"), WEATHER_TRANSITIONS[weather])[0]
            self.weather.append(weather)
            self.uniforms.append(rng.random())
            self.cold_draws.append(rng.random())
        self.index = 0
        self.world_events = []

    def prepare(self, volcano):
        self.world_events = [self.world_event(t, (8 + 2 * t) % 24, volcano) for t in range(len(self.weather))]

    def world_event(self, t, hour, volcano):
        if t in self.scripted_events:
            return self.scripted_events[t]
        sign = volcano.world_events[t]
        if sign != "none":
            return sign
        if self.weather[t] == "storm":
            return "storm"
        wet = self.weather[t] != "calm"
        probability = 0.12 + 0.22 * wet + 0.2 * volcano.hazard_by_step[t]["ash"]  # assumption
        if (hour >= 20 or hour <= 6) and self.cold_draws[t] < probability:
            return "cold_night"
        return "none"

    def step_event(self, day, hour, current_pos, in_shelter, injured, action="rest", world=None, energy=1.0, moved=False, t=None):
        if t is None:
            t = self.index
            self.index += 1
        if t in self.scripted_events:
            return self.scripted_events[t]
        base = self.world_events[t] if self.world_events else ("storm" if self.weather[t] == "storm" else "none")
        if base in VOLCANIC:
            return base
        tile = world.get_tile(*current_pos) if world else 1
        night = hour >= 20 or hour <= 6
        # assumption: rest 0.2%; movement, darkness, slopes and fatigue add risk.
        risk = 0.002 + 0.025 * moved + 0.02 * (moved and night) + 0.025 * (moved and tile == 3) + 0.03 * (1 - energy) * moved
        u = self.uniforms[t]
        if u < risk:
            return "injury"
        if base == "storm":
            return base
        # assumption: boar encounters, forest exposure and dawn/dusk increase risk.
        animal = 0.003 + 0.012 * (tile == 2) + 0.012 * (hour in (6, 8, 18, 20))
        if u < animal:
            return "animal"
        if base == "cold_night":
            return base
        if action == "forage" and tile == 2 and u < 0.3:  # assumption: forage discovery rate
            return "find_food"
        return "none"

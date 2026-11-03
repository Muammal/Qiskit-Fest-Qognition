"""Persistent weather and common-random-number contextual events.

Numerical probabilities are scenario assumptions, not measured island rates.
"""
import random

VOLCANIC = ('tremor', 'gas_plume', 'eruption', 'ash_fall')
WEATHER_TRANSITIONS = {  # assumption: persistent two-hour weather transitions
    'calm': (.78, .19, .03), 'rain': (.22, .65, .13), 'storm': (.12, .38, .50)}


class EventGenerator:
    def __init__(self, seed=42, horizon=36):
        rng = random.Random(seed + 1009)  # assumption: independent weather stream
        self.weather, self.uniforms, self.cold_draws = [], [], []
        weather = 'calm'
        for _ in range(horizon):
            weather = rng.choices(('calm', 'rain', 'storm'), WEATHER_TRANSITIONS[weather])[0]
            self.weather.append(weather)
            self.uniforms.append(rng.random())
            self.cold_draws.append(rng.random())
        self.index = 0
        self.world_events = []

    def prepare(self, volcano):
        self.world_events = [self.world_event(t, (8+2*t) % 24, volcano) for t in range(len(self.weather))]

    def world_event(self, t, hour, volcano):
        sign = volcano.world_events[t]
        if sign != 'none':
            return sign
        if self.weather[t] == 'storm':
            return 'storm'
        wet = self.weather[t] != 'calm'
        probability = .12 + .22 * wet + .2 * volcano.hazard_by_step[t]['ash']  # assumption
        if (hour >= 20 or hour <= 6) and self.cold_draws[t] < probability:
            return 'cold_night'
        return 'none'

    def step_event(self, day, hour, current_pos, in_shelter, injured, action='rest',
                   world=None, energy=1.0, moved=False, t=None):
        if t is None:
            t = self.index
            self.index += 1
        base = self.world_events[t] if self.world_events else ('storm' if self.weather[t] == 'storm' else 'none')
        if base in VOLCANIC:
            return base
        tile = world.get_tile(*current_pos) if world else 1
        night = hour >= 20 or hour <= 6
        # assumption: rest 0.2%; movement, darkness, slopes and fatigue add risk.
        risk = .002 + .025*moved + .02*(moved and night) + .025*(moved and tile == 3) + .03*(1-energy)*moved
        u = self.uniforms[t]
        if u < risk:
            return 'injury'
        if base == 'storm':
            return base
        # assumption: boar encounters, forest exposure and dawn/dusk increase risk.
        animal = .003 + .012*(tile == 2) + .012*(hour in (6,8,18,20))
        if u < animal:
            return 'animal'
        if base == 'cold_night':
            return base
        if action == 'forage' and tile == 2 and u < .3:  # assumption: forage discovery rate
            return 'find_food'
        return 'none'

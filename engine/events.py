"""
engine/events.py - Environmental Event Generator
Owned by Tech C (Integration, Engine, Events).
"""

import random
from typing import Dict, List, Optional


class EventGenerator:
    """
    Simulates stochastic and contextual island environmental events:
      - 'storm': Severe rainfall and gales, severe hazard without shelter.
      - 'cold_night': Nighttime temperature drop (hours 21 to 5).
      - 'injury': Sprained ankle or cut sustained during strenuous work.
      - 'animal': Territorial predator or wild boar encounter.
      - 'find_food': High-yield foraging opportunity discovered.
      - 'none': Normal calm island conditions.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.storm_duration = 0

    def step_event(self, day: int, hour: int, current_pos: List[int], in_shelter: bool, injured: bool) -> str:
        """Evaluates time, terrain, and weather cycles to trigger a discrete event."""
        # Active storm continues for 2-3 hours
        if self.storm_duration > 0:
            self.storm_duration -= 1
            return "storm"

        roll = self.rng.random()

        # Nighttime temperature hazard (hours 21 to 5)
        if (hour >= 21 or hour <= 5) and not in_shelter and roll < 0.35:
            return "cold_night"

        # Stochastic storm front
        if roll < 0.12:
            self.storm_duration = self.rng.randint(1, 3)
            return "storm"

        # Wildlife encounter (more likely in deep forest/mountains)
        if roll < 0.22:
            return "animal"

        # Accidental injury (higher probability if already fatigued or rushing)
        if roll < 0.28:
            return "injury"

        # Lucky forage discovery
        if roll < 0.40:
            return "find_food"

        return "none"


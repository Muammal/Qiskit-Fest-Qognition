"""
engine/agent.py - Survival Agent State and Physiological Mechanics
Owned by Tech C (Integration, Contracts, Engine).
"""

from typing import Any, Dict, List, Optional
import contracts


class SurvivalAgent:
    """
    Manages physiological need decay, inventory management, dynamic stress
    calculation, environmental injury status, and lethal survival thresholds.
    Conforms to the state schema defined in contracts.py.
    """

    def __init__(self, start_pos: Optional[List[int]] = None):
        self.day: int = 1
        self.hour: int = 8  # Start at 08:00 AM on Day 1
        self.pos: List[int] = list(start_pos) if start_pos else [20, 20]
        
        # Physiological needs normalized [0.0, 1.0]
        self.needs: Dict[str, float] = {
            "hunger": 0.85,
            "thirst": 0.80,
            "warmth": 0.90,
            "energy": 0.90,
            "safety": 0.85,
            "morale": 0.80
        }
        
        self.stress: float = 0.15
        self.injured: bool = False
        self.injury_cooldown: int = 0
        self.inventory: Dict[str, int] = {
            "wood": 0,
            "food": 0,
            "tools": 0
        }
        self.recent_events: List[str] = ["none", "none"]
        self.is_alive: bool = True
        self.cause_of_death: Optional[str] = None

    def get_state(self) -> Dict[str, Any]:
        """Returns snapshot of current state dictionary conforming to contracts.py."""
        state = {
            "day": self.day,
            "hour": self.hour,
            "pos": list(self.pos),
            "needs": {k: round(v, 3) for k, v in self.needs.items()},
            "stress": round(self.stress, 3),
            "injured": self.injured,
            "inventory": dict(self.inventory),
            "recent_events": list(self.recent_events)
        }
        contracts.validate_state(state)
        return state

    def apply_event(self, event: str, in_shelter: bool):
        """Applies immediate environmental impacts to agent state."""
        self.recent_events.append(event)
        if len(self.recent_events) > 3:
            self.recent_events.pop(0)

        if event == "storm":
            if in_shelter:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.10)
                self.needs["warmth"] = max(0.0, self.needs["warmth"] - 0.05)
            else:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.35)
                self.needs["warmth"] = max(0.0, self.needs["warmth"] - 0.30)
                self.stress = min(1.0, self.stress + 0.30)

        elif event == "cold_night":
            chill = 0.08 if in_shelter else 0.35
            self.needs["warmth"] = max(0.0, self.needs["warmth"] - chill)
            self.needs["morale"] = max(0.0, self.needs["morale"] - 0.10)

        elif event == "animal":
            if in_shelter:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.15)
                self.stress = min(1.0, self.stress + 0.20)
            else:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.40)
                self.stress = min(1.0, self.stress + 0.45)
                # Possible physical confrontation injury
                self.injured = True
                self.injury_cooldown = 4

        elif event == "injury":
            self.injured = True
            self.injury_cooldown = 5
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.20)
            self.needs["morale"] = max(0.0, self.needs["morale"] - 0.20)
            self.stress = min(1.0, self.stress + 0.35)

        elif event == "find_food":
            self.inventory["food"] = self.inventory.get("food", 0) + 2
            self.needs["morale"] = min(1.0, self.needs["morale"] + 0.15)
            self.stress = max(0.0, self.stress - 0.10)

    def execute_action(self, action: str, world: Any) -> str:
        """Resolves chosen action against world terrain and updates inventory/needs."""
        x, y = self.pos
        tile = world.get_tile(x, y)
        narrative = ""

        if action == "forage":
            # Better foraging in forest (tile 2) or plains (tile 1)
            if tile == 2:
                yield_food = 2
                yield_wood = 1
            else:
                yield_food = 1
                yield_wood = 0

            self.inventory["food"] = self.inventory.get("food", 0) + yield_food
            self.inventory["wood"] = self.inventory.get("wood", 0) + yield_wood
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.12)
            narrative = f"Foraged {yield_food} food and {yield_wood} wood"

            # Auto-eat if hungry
            if self.needs["hunger"] < 0.6 and self.inventory["food"] > 0:
                self.inventory["food"] -= 1
                self.needs["hunger"] = min(1.0, self.needs["hunger"] + 0.40)
                narrative += "; consumed gathered rations"

        elif action == "drink":
            if world.is_near_water(x, y):
                self.needs["thirst"] = min(1.0, self.needs["thirst"] + 0.60)
                narrative = "Drank clean water from natural stream"
            else:
                narrative = "Searched for water but found none nearby"
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.05)

        elif action == "build_shelter":
            wood_needed = 2
            if self.inventory.get("wood", 0) >= wood_needed:
                self.inventory["wood"] -= wood_needed
                world.set_shelter(x, y)
                self.needs["safety"] = min(1.0, self.needs["safety"] + 0.35)
                self.needs["warmth"] = min(1.0, self.needs["warmth"] + 0.25)
                self.needs["energy"] = max(0.0, self.needs["energy"] - 0.25)
                narrative = "Constructed lean-to shelter with timber"
            else:
                # Gather initial branches
                self.inventory["wood"] = self.inventory.get("wood", 0) + 1
                self.needs["energy"] = max(0.0, self.needs["energy"] - 0.10)
                narrative = "Gathered timber for future shelter construction"

        elif action == "rest":
            in_shelter = world.is_in_shelter(x, y)
            recovery = 0.35 if in_shelter else 0.18
            self.needs["energy"] = min(1.0, self.needs["energy"] + recovery)
            if in_shelter:
                self.needs["warmth"] = min(1.0, self.needs["warmth"] + 0.20)
                self.needs["safety"] = min(1.0, self.needs["safety"] + 0.15)
            else:
                self.needs["warmth"] = min(1.0, self.needs["warmth"] + 0.08)
            self.stress = max(0.0, self.stress - 0.20)
            narrative = "Rested and recuperated vital energy"

            # Heal injury over time
            if self.injured:
                self.injury_cooldown -= 1
                if self.injury_cooldown <= 0:
                    self.injured = False
                    narrative += "; injury healed"

        elif action == "explore":
            # Step in random open direction
            deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            import random
            random.shuffle(deltas)
            for dx, dy in deltas:
                nx, ny = x + dx, y + dy
                # Avoid stepping directly into ocean water if land available
                if 0 <= nx < world.width and 0 <= ny < world.height and world.get_tile(nx, ny) != 0:
                    self.pos = [nx, ny]
                    break
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.15)
            narrative = f"Explored terrain toward [{self.pos[0]}, {self.pos[1]}]"

        elif action == "craft":
            if self.inventory.get("wood", 0) >= 1:
                self.inventory["wood"] -= 1
                self.inventory["tools"] = self.inventory.get("tools", 0) + 1
                self.needs["morale"] = min(1.0, self.needs["morale"] + 0.15)
                narrative = "Crafted basic survival tool"
            else:
                narrative = "Lacked materials to craft"
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.10)

        elif action == "hide":
            self.needs["safety"] = min(1.0, self.needs["safety"] + 0.30)
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.05)
            self.stress = max(0.0, self.stress - 0.15)
            narrative = "Concealed location, avoiding environmental threats"

        return narrative

    def step_decay(self, in_shelter: bool):
        """Natural physiological decay per simulation step (2 game hours)."""
        # Metabolic decay per 2-hour step (sustainable with daily drinking/eating)
        self.needs["hunger"] = max(0.0, self.needs["hunger"] - 0.025)
        self.needs["thirst"] = max(0.0, self.needs["thirst"] - 0.035)

        # Baseline energy and warmth
        if not in_shelter and (self.hour >= 21 or self.hour <= 5):
            self.needs["warmth"] = max(0.0, self.needs["warmth"] - 0.08)
        elif 10 <= self.hour <= 16 and "storm" not in self.recent_events[-1:]:
            self.needs["warmth"] = min(1.0, self.needs["warmth"] + 0.05)

        # Compute composite stress level:
        # Stress rises when needs are critically low or agent is injured
        peril_factors = [
            (1.0 - self.needs["safety"]) * 0.35,
            (1.0 - self.needs["thirst"]) * 0.25,
            (1.0 - self.needs["hunger"]) * 0.20,
            (1.0 - self.needs["warmth"]) * 0.15,
            0.20 if self.injured else 0.0
        ]
        target_stress = min(1.0, sum(peril_factors))
        # Smooth stress transition
        self.stress = round(0.7 * self.stress + 0.3 * target_stress, 3)

        # Advance game clock (2 hours per step)
        self.hour += 2
        if self.hour >= 24:
            self.hour -= 24
            self.day += 1

        # Check lethal survival thresholds
        if self.needs["thirst"] <= 0.0:
            self.is_alive = False
            self.cause_of_death = "dehydration"
        elif self.needs["hunger"] <= 0.0:
            self.is_alive = False
            self.cause_of_death = "starvation"
        elif self.needs["warmth"] <= 0.0:
            self.is_alive = False
            self.cause_of_death = "hypothermia"
        elif self.needs["energy"] <= 0.0 and self.needs["safety"] < 0.2:
            self.is_alive = False
            self.cause_of_death = "exhaustion_collapse"

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
        self.volcanic_sign_seen = False
        self.steps_without_food = 0
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

    def apply_event(self, event: str, in_shelter: bool, forest_cover: bool = False):
        """Applies immediate environmental impacts to agent state."""
        self.recent_events.append(event)
        if len(self.recent_events) > 3:
            self.recent_events.pop(0)

        if event in ("tremor", "gas_plume", "eruption", "ash_fall"):
            self.volcanic_sign_seen = True
            self.stress = min(1.0, self.stress + 0.08)
            self.needs["safety"] = max(0., self.needs["safety"] - .1)  # assumption: warning costs perceived safety
            self.needs["morale"] = max(0., self.needs["morale"] - .02)  # assumption: warning morale cost

        if event == "storm":
            if in_shelter:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.10)
                self.needs["warmth"] = max(0.0, self.needs["warmth"] - 0.05)
            else:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.15)
                self.needs["warmth"] = max(0.0, self.needs["warmth"] - (0.06 if forest_cover else 0.10))
                self.stress = min(1.0, self.stress + 0.30)

        elif event == "cold_night":
            chill = 0.03 if in_shelter else (0.06 if forest_cover else 0.10)  # assumption: two-hour cold episode
            self.needs["warmth"] = max(0.0, self.needs["warmth"] - chill)
            self.needs["morale"] = max(0.0, self.needs["morale"] - 0.04)  # assumption: a damp tropical night is miserable, not grave

        elif event == "animal":
            if in_shelter:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.15)
                self.stress = min(1.0, self.stress + 0.20)
            else:
                self.needs["safety"] = max(0.0, self.needs["safety"] - 0.40)
                self.stress = min(1.0, self.stress + 0.45)
                # Possible physical confrontation injury
                if self.needs["energy"] < .3:  # assumption: fatigue prevents escape
                    self.injured = True
                    self.injury_cooldown = 4

        elif event == "injury":
            self.injured = True
            self.injury_cooldown = 5
            self.needs["energy"] = max(0.0, self.needs["energy"] - 0.20)
            self.needs["morale"] = max(0.0, self.needs["morale"] - 0.20)
            self.stress = min(1.0, self.stress + 0.35)

        elif event == "find_food":
            pass  # Food discovery is descriptive; finite patches are harvested by forage.
            self.needs["morale"] = min(1.0, self.needs["morale"] + 0.15)
            self.stress = max(0.0, self.stress - 0.10)

    def movement_budget(self, world):
        # assumption: 120 walking minutes; injury, night and local ash reduce speed.
        speed = (.5 if self.injured else 1.) * (.75 if self.hour >= 20 or self.hour <= 6 else 1.)
        return 120 * speed

    def follow_path(self, world, path):
        budget, moved = self.movement_budget(world), 0
        for a, b in zip(path, path[1:]):
            cost = world.travel_minutes(a, b) / (1 - .5 * world.ash_at(*a))
            if moved and cost > budget:
                break
            self.pos = list(b)
            moved += 1
            budget -= cost
            if budget <= 0:
                break

    def walk_to(self, world, goals, avoid_danger=False):
        self.follow_path(world, world.path(self.pos, goals, avoid_danger))

    def eat_if_needed(self):
        if self.needs['hunger'] < .5 and self.inventory['food']:
            self.inventory['food'] -= 1
            self.needs['hunger'] = min(1., self.needs['hunger'] + .4)  # assumption: ration recovery
            self.steps_without_food = 0

    def execute_action(self, action, world):
        self.eat_if_needed()
        if self.injury_cooldown:
            self.injury_cooldown = max(0, self.injury_cooldown - (2 if action == 'rest' else 1))  # assumption: rest halves healing time
            self.injured = self.injury_cooldown > 0
        x, y = self.pos
        warned = self.volcanic_sign_seen or world.volcanic_sign_seen
        if action == "hide":
            if warned and tuple(self.pos) not in world.assembly_points:
                self.walk_to(world, world.assembly_points, avoid_danger=world.zones[y][x] != 2)
            self.needs["safety"] = min(1, self.needs["safety"] + .2)
            self.stress = max(0, self.stress - .1)
        elif action == "drink":
            # Least walking time to water. Whether to leave danger is the mind's choice alone.
            sources = [p for p in world.freshwater_tiles if p not in world.lava]
            goals = {(px, py) for sx, sy in sources
                     for px in range(sx - 2, sx + 3) for py in range(sy - 2, sy + 3)
                     if (px - sx) ** 2 + (py - sy) ** 2 <= 4 and world.walkable((px, py))}
            self.follow_path(world, world.path(self.pos, goals))
            near = [p for p in sources if sum((a - b) ** 2 for a, b in zip(p, self.pos)) <= 4]
            if near:
                dirty = world.stream_ash() > .1 and not any(p in world.clean_springs for p in near)
                self.needs["thirst"] = min(1, self.needs["thirst"] + (.3 if dirty else .65))
                self.needs["morale"] = max(0, self.needs["morale"] - (.06 if dirty else 0))
        elif action == "forage":
            food = [p for p in world.food_tiles if p not in world.depleted_food and world.walkable(p)
                    and (getattr(world, "scenario", "volcano") == "island" or sum((a - b) ** 2 for a, b in zip(p, self.pos)) <= 4)]  # assumption: local 500 m search
            if tuple(self.pos) not in food and self.inventory["food"] < 4:
                self.walk_to(world, food)
            if tuple(self.pos) in food and self.inventory["food"] < 4:  # assumption: four-ration carrying capacity
                self.inventory["food"] += 1  # assumption: one ration per finite patch
                world.depleted_food.add(tuple(self.pos))
            if world.get_tile(*self.pos) == 2:
                self.inventory["wood"] += 1
        elif action == "build_shelter":
            if world.is_in_shelter(*self.pos):
                pass
            elif self.inventory["wood"] >= 2:
                self.inventory["wood"] -= 2
                world.set_shelter(*self.pos)
            elif world.get_tile(*self.pos) == 2:
                self.inventory["wood"] += 1
            elif getattr(world, "scenario", "volcano") == "island":
                forests = [(fx, fy) for fy in range(world.height) for fx in range(world.width)
                           if world.get_tile(fx, fy) == 2 and world.walkable((fx, fy))]
                if forests:
                    self.walk_to(world, forests)
        elif action == "rest":
            self.needs["energy"] = min(1, self.needs["energy"] + .3)
            self.needs["warmth"] = min(1, self.needs["warmth"] + (.12 if world.is_in_shelter(*self.pos) else .015))
            self.needs["safety"] = min(1, self.needs["safety"] + .05)
        elif action == "explore":
            import random
            reachable = [p for p in world.neighbors(tuple(self.pos)) if world.walkable(p)]
            if reachable:
                destination = random.choice(reachable)
                # A distant goal creates a continuous least-time walk rather than teleportation.
                for _ in range(12):  # assumption: exploratory target distance
                    choices = [p for p in world.neighbors(destination) if world.walkable(p)]
                    if choices:
                        destination = random.choice(choices)
                self.walk_to(world, [destination])
        elif action == "craft" and self.inventory["wood"]:
            self.inventory["wood"] -= 1
            self.inventory["tools"] += 1
        self.eat_if_needed()
        if action != "rest":
            self.needs["energy"] = max(0, self.needs["energy"] - .025)
        if any(e in ('tremor', 'gas_plume', 'eruption', 'ash_fall') for e in self.recent_events):
            zone = world.zones[self.pos[1]][self.pos[0]]
            self.needs['safety'] = min(self.needs['safety'], (.8, .5, .3)[zone])  # assumption: warning safety caps
        return f"{action} at {self.pos}"

    def step_decay(self, in_shelter: bool, forest_cover: bool = False):
        """Natural physiological decay per simulation step (2 game hours)."""
        # Metabolic decay per 2-hour step (sustainable with daily drinking/eating)
        self.needs["hunger"] = max(0.0, self.needs["hunger"] - 0.025)
        self.needs["thirst"] = max(0.0, self.needs["thirst"] - (1 / 36))  # assumption: full hydration lasts 72 hours; initial .8 lasts 29 steps

        self.steps_without_food += 1
        if self.needs["hunger"] <= .15:
            self.needs["energy"] = max(0, self.needs["energy"] - .015)
            self.needs["morale"] = max(0, self.needs["morale"] - .015)
        # Baseline energy and warmth
        if not in_shelter and (self.hour >= 21 or self.hour <= 5):
            self.needs["warmth"] = max(0.0, self.needs["warmth"] - (0.015 if forest_cover else 0.025))
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
        if self.needs["thirst"] <= 1e-9:
            self.is_alive = False
            self.cause_of_death = "dehydration"
        elif self.needs["hunger"] <= 0.0 and self.steps_without_food > 72:
            self.is_alive = False
            self.cause_of_death = "starvation"
        elif self.needs["warmth"] <= 0.0:
            self.is_alive = False
            self.cause_of_death = "hypothermia"
        elif self.needs["energy"] <= 0.0 and self.needs["safety"] < 0.2:
            self.is_alive = False
            self.cause_of_death = "exhaustion_collapse"

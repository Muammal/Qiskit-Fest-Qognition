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

    def movement_budget(self, world):
        # assumption: 1 km/h rough ground, two hours, 250 m tiles.
        speed = 8
        if self.injured:
            speed //= 2
        if self.hour >= 20 or self.hour <= 6:
            speed = max(1, speed * 3 // 4)  # assumption: darkness slows travel 25%.
        if world.ash > .5:
            speed = max(1, speed // 2)  # assumption: heavy ash halves travel speed.
        return speed

    def walk_to(self, world, goals, avoid_danger=False):
        path = world.path(self.pos, goals, avoid_danger)
        if path:
            self.pos = list(path[min(len(path)-1, self.movement_budget(world))])

    def execute_action(self, action, world):
        x, y = self.pos
        warned = self.volcanic_sign_seen or world.volcanic_sign_seen
        if action == "hide":
            if warned and world.zones[y][x] != 0:
                self.walk_to(world, world.assembly_points)
            self.needs["safety"] = min(1, self.needs["safety"] + .2)
            self.stress = max(0, self.stress - .1)
        elif action == "drink":
            outside = world.zones[y][x] != 2
            avoid = warned and outside
            sources = [p for p in world.freshwater_tiles if p not in world.lava
                       and (not avoid or world.zones[p[1]][p[0]] != 2)]
            # Prefer reachable clean springs; never cross danger after leaving it.
            clean = [p for p in sources if p in world.clean_springs]
            candidates = []
            for group in ((clean, sources) if world.ash > 0 else (sources,)):
                goals = {(px,py) for sx,sy in group
                         for px in range(sx-2,sx+3) for py in range(sy-2,sy+3)
                         if (px-sx)**2+(py-sy)**2 <= 4 and world.walkable((px,py))
                         and (not avoid or world.zones[py][px] != 2)}
                path = world.path(self.pos, goals, avoid)
                if path:
                    candidates = path
                    break
            if candidates:
                self.pos = list(candidates[min(len(candidates)-1, self.movement_budget(world))])
            near = [p for p in sources if sum((a-b)**2 for a,b in zip(p,self.pos)) <= 4]
            if near:
                dirty = world.ash > 0 and not any(p in world.clean_springs for p in near)
                self.needs["thirst"] = min(1, self.needs["thirst"] + (.3 if dirty else .65))
                self.needs["morale"] = max(0, self.needs["morale"] - (.06 if dirty else 0))
        elif action == "forage":
            food = [p for p in world.food_tiles if p not in world.lava and p not in world.pdc]
            if self.inventory["wood"] < 2 and world.get_tile(*self.pos) != 2:
                forests = [p for p in food if world.get_tile(*p) == 2] or food
                if forests:
                    self.walk_to(world, forests)
            elif tuple(self.pos) not in food:
                self.walk_to(world, food)
            if tuple(self.pos) in food:
                self.inventory["food"] += 2
            if world.get_tile(*self.pos) == 2:
                self.inventory["wood"] += 1
            if self.inventory["food"] and self.needs["hunger"] < .7:
                self.inventory["food"] -= 1
                self.needs["hunger"] = min(1, self.needs["hunger"] + .4)
                self.steps_without_food = 0
        elif action == "build_shelter":
            if self.inventory["wood"] >= 2:
                self.inventory["wood"] -= 2
                world.set_shelter(*self.pos)
            elif world.get_tile(*self.pos) == 2:
                self.inventory["wood"] += 1
        elif action == "rest":
            self.needs["energy"] = min(1, self.needs["energy"] + .3)
            self.needs["warmth"] = min(1, self.needs["warmth"] + (.12 if world.is_in_shelter(*self.pos) else .015))
            self.needs["safety"] = min(1, self.needs["safety"] + .05)
        elif action == "explore":
            import random
            budget = self.movement_budget(world)
            dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)])
            for _ in range(budget):
                x, y = self.pos
                candidates = [(x+cx, y+cy) for cx, cy in ((1,0),(-1,0),(0,1),(0,-1))
                              if world.walkable((x+cx, y+cy))]
                if not candidates:
                    break
                favored = [c for c in candidates if (c[0]-x)*dx >= 0 and (c[1]-y)*dy >= 0]
                if favored and random.random() < 0.75:
                    self.pos = list(random.choice(favored))
                else:
                    self.pos = list(random.choice(candidates))
        elif action == "craft" and self.inventory["wood"]:
            self.inventory["wood"] -= 1
            self.inventory["tools"] += 1
        if action != "rest":
            self.needs["energy"] = max(0, self.needs["energy"] - .025)
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

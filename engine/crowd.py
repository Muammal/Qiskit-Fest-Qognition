"""Everyone aboard: head-counts, roles, and the five-minute SurvivalAgent.

Every person decides with the same mind. A role never changes how anyone thinks;
it sets where they start, what they hear and when, and what an action does.
Head-counts: Wikipedia, Sinking of the Titanic, casualty table citing Encyclopedia
Titanica (2,208 aboard). Crew departments: British Wreck Commissioner's Inquiry.
"""

import random

from engine.agent import SurvivalAgent
from engine.flood import STEP_MINUTES, START_HOUR, START_MINUTE
from engine.ship import A, B, BOAT, C, D, E, F, G, TANK

PASSENGERS = {  # class: (men, women, children), Wikipedia casualty table
    "first": (175, 142, 7),
    "second": (166, 92, 26),
    "third": (444, 176, 89),
}
CREW_GROUPS = (866, 23, 2)  # men, women, children; Wikipedia casualty table
DECK_DEPARTMENT, ENGINE_DEPARTMENT = 66, 325  # British Wreck Commissioner's Inquiry
CAPTAINS, OFFICERS = 1, 7  # Smith; Wilde, Murdoch, Lightoller, Pitman, Boxhall, Lowe, Moody
# assumption: remaining crew, including restaurant staff and musicians, count as servers.
SERVERS = sum(CREW_GROUPS) - DECK_DEPARTMENT - ENGINE_DEPARTMENT
EVAC_WORKERS = DECK_DEPARTMENT - CAPTAINS - OFFICERS
ROLE_NAMES = {
    "captain": "Captain",
    "officer": "Officer",
    "evac_worker": "Evacuation worker",
    "server": "Server / steward",
    "engine_worker": "Engine room worker",
    "passenger": "Passenger",
}
ROLE_COLORS = {
    "captain": (255, 214, 64),
    "officer": (255, 170, 60),
    "evac_worker": (255, 120, 70),
    "server": (240, 240, 245),
    "engine_worker": (170, 150, 130),
    "passenger": (120, 200, 255),
}
SPAWN_AREAS = {  # assumption: schematic berthing as (rows, x range)
    "first": ((A, B, C), (14, 30)),
    "second": ((D, E, F), (8, 16)),
    "third_forward": ((F, G), (30, 36)),
    "third_aft": ((F, G), (3, 9)),
    "captain": ((BOAT,), (30, 30)),
    "officer": ((BOAT, A), (28, 31)),
    "evac_worker": ((C, D), (15, 30)),
    "engine_worker": ((G, TANK), (12, 27)),
    "server": ((A, B, C, D, E, F, G), (4, 34)),
}
ACTION_LABELS = {
    "hide": "Heads for the boats",
    "rest": "Stays put",
    "explore": "Looks for information",
    "forage": "Fetches a lifebelt",
    "drink": "Stops for water",
    "build_shelter": "Moves indoors",
    "craft": "Helps people nearby",
}
ROLE_ACTION_LABELS = {
    "captain": {"rest": "Holds the bridge", "craft": "Directs the crew", "explore": "Inspects the damage"},
    "officer": {"hide": "Goes to load a boat", "rest": "Holds position", "craft": "Directs the crew"},
    "evac_worker": {"hide": "Goes to work a boat", "rest": "Waits for orders", "craft": "Readies equipment"},
    "server": {"rest": "Knocks on cabin doors", "craft": "Hands out lifebelts", "explore": "Checks cabins"},
    "engine_worker": {"rest": "Keeps pumps and lights running", "craft": "Works the pumps"},
}
STEP_FRACTION = STEP_MINUTES / 120  # assumption: base decay rates are per two hours
DECK_CHILL, INDOOR_CHILL = 0.012, 0.002  # assumption: freezing air outdoors; heating fades indoors
WATER_CHILL = 0.3  # assumption: with warmth .9, death in 15 minutes; Wikipedia gives 15-30 minutes in -2 C
WATER_CHILL_LIFEBELT = 0.18  # assumption: floating upright stretches that to about 25 minutes
NO_LIFEBELT_DROWN_CHANCE = 0.15  # assumption: per step in the water without flotation
LIFEBOAT_WARMTH_FLOOR = 0.05  # assumption: exposure in boats is unpleasant, not modelled as lethal
CROWD_PER_INTERIOR, CROWD_PER_STAIR = 40, 15  # assumption: people on a tile that halve walking speed
BOAT_DECK_TILES_PER_STEP = 12  # assumption: about 85 m along a crowded boat deck in five minutes
STATION_QUEUE_WEIGHT = 4.0  # assumption: tiles someone would walk to avoid a queue as long as the seats left


class ShipAgent(SurvivalAgent):
    dt_seconds = 300  # decides every five-minute step

    def __init__(self, agent_id, role, group, cabin_class, start_pos):
        super().__init__(start_pos)
        self.id, self.role, self.group, self.cabin_class = agent_id, role, group, cabin_class
        self.hour, self.minute = START_HOUR, START_MINUTE
        self.inventory["lifebelt"] = 0
        self.status = "aboard"  # aboard, boat, water
        self.boat_id = None
        self.neutral_inputs = False  # True removes the nudges below; see TitanicSimulation's inputs setting
        self.knows_danger = False
        self.story_event = "none"
        self.last_action = "rest"
        self.log = []

    @property
    def label(self):
        name = ROLE_NAMES[self.role]
        if self.role == "passenger":
            return f"{self.cabin_class.capitalize()}-class {self.group} (#{self.id})"
        return f"{name} (#{self.id})"

    def action_label(self, action):
        return ROLE_ACTION_LABELS.get(self.role, {}).get(action, ACTION_LABELS[action])

    def board(self, boat):
        self.status, self.boat_id = "boat", boat.id
        self.needs["safety"] = max(self.needs["safety"], 0.7)

    def enter_water(self):
        self.status = "water"

    def walk(self, world, field, crowding):
        """Walk along a least-time field for one step; crowds on a tile slow everyone on it."""
        if field is None:
            return
        budget = STEP_MINUTES * (0.5 if self.injured else 1.0)
        p = tuple(self.pos)
        while budget > 0:
            q = field.get(p)
            if q is None:
                break
            per_tile = CROWD_PER_STAIR if p[1] != q[1] else CROWD_PER_INTERIOR
            cost = world.travel_minutes(p, q) * (1 + crowding.get(q, 0) / per_tile)
            if cost > budget:
                break
            budget -= cost
            crowding[p] = max(0, crowding.get(p, 0) - 1)
            crowding[q] = crowding.get(q, 0) + 1
            p = q
        self.pos = list(p)

    def walk_to_boat(self, world, fields, crowding):
        """Climb to the boat deck, then walk along it to the station that suits this person."""
        if self.pos[1] != BOAT:
            self.walk(world, fields["boats"], crowding)
        if self.pos[1] == BOAT and fields["stations"]:
            target = self._choose_station(fields["stations"])
            direction = 1 if target > self.pos[0] else -1
            steps = min(abs(target - self.pos[0]), BOAT_DECK_TILES_PER_STEP)
            for _ in range(steps):
                q = (self.pos[0] + direction, self.pos[1])
                if not world.walkable(q):
                    break
                self.pos = list(q)

    def _choose_station(self, stations):
        """Nearest station, discounted by how many are already waiting for its free seats."""

        def score(station):
            waiting, free_seats = stations[station]
            return abs(station - self.pos[0]) + STATION_QUEUE_WEIGHT * waiting / (free_seats + 1)

        return min(stations, key=score)

    def execute_ship_action(self, action, world, fields, crowding, rng, warned_only_hide=False):
        """What each of the seven contract actions means on the ship."""
        if self.injury_cooldown:
            self.injury_cooldown = max(0, self.injury_cooldown - 1)
            self.injured = self.injury_cooldown > 0
        indoors = world.get_tile(*self.pos) == 4
        if action == "hide":
            if self.neutral_inputs:
                if self.knows_danger:  # same rule as agent.py: with no warning, nobody knows to run
                    self.walk_to_boat(world, fields, crowding)
            else:
                if not warned_only_hide or bool(self.recent_events):
                    self.walk_to_boat(world, fields, crowding)
                    self.needs["safety"] = min(1, self.needs["safety"] + 0.05)
                    self.stress = max(0, self.stress - 0.02)
                else:
                    self.needs["energy"] = min(1, self.needs["energy"] + 0.02)
=======
                self.needs["energy"] = min(1, self.needs["energy"] + 0.02)
>>>>>>> a8750dbb13c6822b142844cb867d976177092ef4
        elif action == "forage":
            if not self.inventory["lifebelt"]:
                if indoors:
                    self.inventory["lifebelt"] = 1
                else:
                    self.walk(world, fields["indoors"], crowding)
            self.needs["warmth"] = min(1, self.needs["warmth"] + 0.05 * indoors)  # assumption: warm clothes collected too
        elif action == "build_shelter":
            self.walk(world, fields["indoors"], crowding)
            self.needs["warmth"] = min(1, self.needs["warmth"] + 0.03 * indoors)  # assumption: out of the wind
        elif action == "rest":
            self.needs["energy"] = min(1, self.needs["energy"] + 0.02)
        elif action == "explore":
            options = [p for p in world.neighbors(tuple(self.pos)) if world.walkable(p)]
            if options:
                self.pos = list(rng.choice(options))
        elif action == "drink":
            self.needs["thirst"] = min(1, self.needs["thirst"] + 0.1)
        if action != "rest":
            self.needs["energy"] = max(0, self.needs["energy"] - 0.025 * STEP_FRACTION)
        zone = world.zones[self.pos[1]][self.pos[0]]
        if not self.neutral_inputs and any(e in ("tremor", "gas_plume", "eruption", "ash_fall") for e in self.recent_events):
            self.needs["safety"] = min(self.needs["safety"], (.8, .5, .3)[zone])  # same warning caps as the volcano scenario

    def step_decay(self, in_shelter: bool, forest_cover: bool = False):
        """SurvivalAgent's two-hour decay rescaled to five minutes, on a minute clock."""
        self.needs["hunger"] = max(0.0, self.needs["hunger"] - 0.025 * STEP_FRACTION)
        self.needs["thirst"] = max(0.0, self.needs["thirst"] - STEP_FRACTION / 36)
        if self.status == "water":
            chill = WATER_CHILL_LIFEBELT if self.inventory["lifebelt"] else WATER_CHILL
        elif self.status == "boat":
            chill = INDOOR_CHILL
        else:
            chill = INDOOR_CHILL if in_shelter else DECK_CHILL
        self.needs["warmth"] = max(LIFEBOAT_WARMTH_FLOOR if self.status == "boat" else 0.0, self.needs["warmth"] - chill)
        peril = (
            (1.0 - self.needs["safety"]) * 0.35
            + (1.0 - self.needs["thirst"]) * 0.25
            + (1.0 - self.needs["hunger"]) * 0.2
            + (1.0 - self.needs["warmth"]) * 0.15
            + (0.2 if self.injured else 0.0)
        )
        self.stress = round(0.7 * self.stress + 0.3 * min(1.0, peril), 3)
        self.minute += STEP_MINUTES
        if self.minute >= 60:
            self.minute -= 60
            self.hour += 1
            if self.hour >= 24:
                self.hour -= 24
                self.day += 1
        if self.needs["warmth"] <= 0.0:
            self.is_alive, self.cause_of_death = False, "hypothermia"


def _spawn(rng, world, area):
    rows, (low, high) = SPAWN_AREAS[area]
    options = [(x, y) for y in rows for x in range(low, high + 1) if world.get_tile(x, y)]
    return list(rng.choice(options))


def _jitter(agent, rng):
    """Small seeded differences in starting state, in coarse steps; the mind stays identical."""
    agent.needs["safety"] = round(agent.needs["safety"] + rng.choice((-0.05, 0.0, 0.05)), 3)
    agent.stress = round(agent.stress + rng.choice((-0.05, 0.0, 0.05)), 3)


def build_crowd(world, seed):
    rng = random.Random(seed + 4242)
    people = []

    def add(role, group, cabin_class, area):
        agent = ShipAgent(len(people), role, group, cabin_class, _spawn(rng, world, area))
        _jitter(agent, rng)
        people.append(agent)

    for cabin_class, counts in PASSENGERS.items():
        for group, count in zip(("man", "woman", "child"), counts):
            for _ in range(count):
                if cabin_class == "third":
                    # assumption: single men berthed forward, families and women aft.
                    area = "third_forward" if group == "man" else "third_aft"
                else:
                    area = cabin_class
                add("passenger", group, cabin_class, area)
    groups = ["man"] * CREW_GROUPS[0] + ["woman"] * CREW_GROUPS[1] + ["child"] * CREW_GROUPS[2]
    for role, count in (("captain", CAPTAINS), ("officer", OFFICERS), ("evac_worker", EVAC_WORKERS), ("engine_worker", ENGINE_DEPARTMENT)):
        for _ in range(count):
            add(role, groups.pop(0), "crew", role)
    while groups:  # the women and boys among the crew are all in the victualling department
        add("server", groups.pop(0), "crew", "server")
    return people

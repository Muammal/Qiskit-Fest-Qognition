"""Everyone in Pompeii: head-counts, roles, households, news, and the 15-minute SurvivalAgent.

Every person decides with the same mind. A role never changes how anyone thinks or how
likely they are to notice something. High-status people can hear sooner only because
more servants carry news to their household. Numerical choices are assumptions unless
a source is cited; see PROVENANCE.
"""
import random

from engine.agent import SurvivalAgent
from engine.city import GATE_TO_REGION
from engine.eruption import START_HOUR, STEP_MINUTES

BERNARD = "https://hyperallergic.com/new-research-shows-slaverys-outsized-role-in-pompeiis-economy"
MAGISTRATES_SRC = "https://sites.google.com/narrabeenhs.com/pompeiiandherculaneum/2-3-local-political-life"
COUNCIL_SRC = "https://journal.fi/arctos/article/download/85058/44034/127474"
SHOPS_SRC = "https://blog.eixos.cat/?p=744"
POPULATION_LOW = "https://en.wikipedia.org/wiki/Pompeii"
POPULATION_HIGH = "https://pompeiisites.org/en/?p=64435"

DEFAULT_POPULATION = 11_500  # Wikipedia, Pompeii: 11,000-11,500 from household counts
HIGH_POPULATION = 20_000  # Pompeii park: at least 20,000; the setting
ENSLAVED_SHARE = .30  # Hyperallergic on Seth Bernard's study: as high as 30% in cities such as Pompeii
MAGISTRATES = 4  # two duumviri and two aediles; elected posts, so they do not scale with population
COUNCIL = 100  # assumption: attested for three other Italian towns; none found for Pompeii
MERCHANT_SHARE = 1_000 / DEFAULT_POPULATION  # assumption: one person per establishment; unverified blog count
VISITOR_SHARE = 100 / DEFAULT_POPULATION  # assumption: no evidence, the user's labelled small count
GUARD_SHARE = 20 / DEFAULT_POPULATION  # assumption: no evidence, the user's labelled small count
FREE_HOUSEHOLD_SIZE = 4  # assumption: free people per ordinary household
ENSLAVED_PER_MAGISTRATE, ENSLAVED_PER_COUNCILLOR = 30, 10  # assumption: wealthier households hold more
ENSLAVED_PER_MERCHANT = 1  # assumption
AT_WORK_AT_NOON = .4  # assumption: share of enslaved people away from the household tile at noon

ROLE_NAMES = {
    "magistrate": "Magistrate", "council": "Council member", "guard": "Guard", "merchant": "Merchant",
    "visitor": "Visitor", "enslaved": "Enslaved person", "resident": "Resident",
}
ROLE_COLORS = {
    "magistrate": (255, 214, 64), "council": (255, 170, 60), "guard": (224, 80, 60), "merchant": (120, 220, 130),
    "visitor": (200, 140, 240), "enslaved": (240, 240, 245), "resident": (120, 200, 255),
}
ACTION_LABELS = {
    "hide": "Heads for a gate", "rest": "Stays where they are", "explore": "Goes to see what is happening",
    "forage": "Gathers belongings", "drink": "Goes to a fountain",
    "build_shelter": "Takes cover indoors", "craft": "Helps people nearby",
}
ROLE_ACTION_LABELS = {
    "magistrate": {"rest": "Stays at their post", "craft": "Tries to organise people"},
    "council": {"rest": "Stays at home", "craft": "Gathers the household"},
    "guard": {"rest": "Holds their post", "craft": "Directs people"},
    "merchant": {"rest": "Stays with the shop", "forage": "Secures goods and takings"},
    "visitor": {"rest": "Waits at the inn", "explore": "Asks locals what is happening"},
    "enslaved": {"rest": "Stays at their work", "craft": "Carries out orders"},
}

NEWS_BASE_CHANCE = .5  # assumption: chance per step of noticing something at distance zero, outdoors, in clear view
NEWS_HALF_DISTANCE_TILES = 10.  # assumption: tiles at which that chance halves
INDOORS_FACTOR = .5  # assumption: being inside halves it
RELAY_BASE_CHANCE = .5  # assumption: chance per step a servant reaches their household, from nearby
RELAY_HALF_DISTANCE_TILES = 15.  # assumption: tiles at which that chance halves
STEP_FRACTION = STEP_MINUTES / 120  # assumption: base decay rates are per two hours
PUMICE_SLOWDOWN_PER_M = .5  # assumption: walking on pumice; the guide records people running over 3.5 m of it
OUTDOOR_CHILL_PER_DEG_BELOW_20 = .0006  # assumption: warmth lost per step, per degree below 20 C
STREET_CROWD_PER_TILE = 60  # assumption: people on one 30 m tile that halve walking speed; on by the user's choice

PROVENANCE = {
    "population_default": dict(value=DEFAULT_POPULATION, status="sourced", url=POPULATION_LOW),
    "population_setting": dict(value=HIGH_POPULATION, status="sourced", url=POPULATION_HIGH),
    "enslaved_share": dict(value=ENSLAVED_SHARE, status="news", url=BERNARD, note="news report of a journal article"),
    "magistrates": dict(value=MAGISTRATES, status="school", url=MAGISTRATES_SRC),
    "council": dict(value=COUNCIL, status="assumption", url=COUNCIL_SRC, note="other Italian towns; sizes vary"),
    "merchants": dict(value=1_000, status="assumption", url=SHOPS_SRC, note="an unverified blog count of establishments"),
    "visitors": dict(value=100, status="assumption", url=None, note="no evidence found"),
    "guards": dict(value=20, status="assumption", url=None, note="no evidence found"),
    "households": dict(value="sizes and who holds whom", status="assumption", url=None),
    "crowding": dict(value="60 per tile halves speed; 1,000 per gate per step", status="assumption", url=None),
    "noticing": dict(value="distance, indoors, visibility, chance", status="assumption", url=None,
                     note="the user's rule; chances are assumed and should be varied in testing"),
}


def notice_chance(distance_tiles, indoors, visibility):
    """Chance of noticing something this step. Deliberately takes no role or status."""
    chance = NEWS_BASE_CHANCE / (1 + distance_tiles / NEWS_HALF_DISTANCE_TILES)
    return chance * visibility * (INDOORS_FACTOR if indoors else 1.)


def relay_chance(distance_tiles):
    """Chance one servant who knows reaches their household this step."""
    return RELAY_BASE_CHANCE / (1 + distance_tiles / RELAY_HALF_DISTANCE_TILES)


class Citizen(SurvivalAgent):
    def __init__(self, agent_id, role, group_household, start_pos, home):
        super().__init__(start_pos)
        self.id, self.role = agent_id, role
        self.household = group_household
        self.home = tuple(home)
        self.hour, self.minute = START_HOUR, 0
        self.inventory["valuables"] = 0
        self.status = "city"  # city, road, escaped
        self.gate = None
        self.knows_danger = False
        self.story_event = "none"
        self.last_action = "rest"

    @property
    def is_servant(self):
        return self.role == "enslaved"

    @property
    def label(self):
        return f"{ROLE_NAMES[self.role]} (#{self.id})"

    def action_label(self, action):
        return ROLE_ACTION_LABELS.get(self.role, {}).get(action, ACTION_LABELS[action])

    def walk(self, world, field, budget, crowding=None):
        """Walk along a least-time field until the step's minutes run out."""
        if field is None:
            return
        p = tuple(self.pos)
        while budget > 0:
            q = field.get(p)
            if q is None:
                break
            cost = world.travel_minutes(p, q)
            if crowding is not None and STREET_CROWD_PER_TILE:
                cost *= 1 + crowding.get(q, 0) / STREET_CROWD_PER_TILE
            if cost > budget:
                break
            budget -= cost
            if crowding is not None:
                crowding[p] = max(0, crowding.get(p, 0) - 1)
                crowding[q] = crowding.get(q, 0) + 1
            p = q
        self.pos = list(p)

    def step_budget(self, depth_m, visibility):
        """Minutes of walking this step, reduced by injury, pumice underfoot and poor visibility."""
        speed = (.5 if self.injured else 1.) / (1 + PUMICE_SLOWDOWN_PER_M * depth_m) * (.6 + .4 * visibility)
        return STEP_MINUTES * speed

    def move_to_region(self, gate):
        """Cross from the city map's exit to the matching tile on the region map."""
        self.status, self.gate = "road", gate
        self.pos = list(GATE_TO_REGION[gate])

    def execute_town_action(self, action, world, fields, crowding, rng, depth_m, visibility, restrict_enslaved=False,
                            head_still_in_town=False):
        """What each of the seven contract actions means in the city or on the road."""
        if self.injury_cooldown:
            self.injury_cooldown = max(0, self.injury_cooldown - 1)
            self.injured = self.injury_cooldown > 0
        budget = self.step_budget(depth_m, visibility)
        indoors = world.get_tile(*self.pos) == 4
        held_back = restrict_enslaved and self.is_servant and head_still_in_town
        if action == "hide":
            if not self.knows_danger:  # same rule as agent.py: with no warning, nobody knows to run
                pass
            elif held_back:  # the optional rule: stays with the household, which is outside the mind
                self.walk(world, fields.get("home"), budget, crowding)
            else:
                self.walk(world, fields.get("leave"), budget, crowding)
        elif action == "build_shelter":
            self.walk(world, fields.get("indoors"), budget, crowding)
        elif action == "drink":
            self.walk(world, fields.get("water"), budget, crowding)
            self.needs["thirst"] = min(1, self.needs["thirst"] + .3)
        elif action == "forage":
            self.inventory["valuables"] += 1
            if not indoors:
                self.walk(world, fields.get("indoors"), budget, crowding)
        elif action == "explore":
            options = [p for p in world.neighbors(tuple(self.pos)) if world.walkable(p)]
            if options:
                self.pos = list(rng.choice(options))
        elif action == "rest":
            self.needs["energy"] = min(1, self.needs["energy"] + .02)
        if action != "rest":
            self.needs["energy"] = max(0, self.needs["energy"] - .025 * STEP_FRACTION)

    def step_decay(self, in_shelter: bool, forest_cover: bool = False, temperature_c: float = 27.):
        """SurvivalAgent's two-hour decay rescaled to fifteen minutes, on a minute clock."""
        self.needs["hunger"] = max(0., self.needs["hunger"] - .025 * STEP_FRACTION)
        self.needs["thirst"] = max(0., self.needs["thirst"] - STEP_FRACTION / 36)
        if not in_shelter:
            chill = max(0., 20. - temperature_c) * OUTDOOR_CHILL_PER_DEG_BELOW_20
            self.needs["warmth"] = max(.05, self.needs["warmth"] - chill)
        peril = ((1. - self.needs["safety"]) * .35 + (1. - self.needs["thirst"]) * .25
                 + (1. - self.needs["hunger"]) * .2 + (1. - self.needs["warmth"]) * .15
                 + (.2 if self.injured else 0.))
        self.stress = round(.7 * self.stress + .3 * min(1., peril), 3)
        self.minute += STEP_MINUTES
        if self.minute >= 60:
            self.minute -= 60
            self.hour += 1
            if self.hour >= 24:
                self.hour -= 24
                self.day += 1


def role_counts(population=DEFAULT_POPULATION):
    """Head-counts for a population. Elected bodies stay fixed; other shares scale."""
    counts = dict(magistrate=MAGISTRATES, council=COUNCIL, enslaved=round(population * ENSLAVED_SHARE),
                  merchant=round(population * MERCHANT_SHARE), visitor=round(population * VISITOR_SHARE),
                  guard=round(population * GUARD_SHARE))
    counts["resident"] = population - sum(counts.values())
    return counts


def _jitter(agent, rng):
    """Small seeded differences in starting state; the mind stays identical."""
    agent.needs["safety"] = round(agent.needs["safety"] + rng.choice((-.05, 0., .05)), 3)
    agent.stress = round(agent.stress + rng.choice((-.05, 0., .05)), 3)


def build_citizens(world, seed, population=DEFAULT_POPULATION):
    """Everyone with a role, a household and a place at noon. Returns (people, households)."""
    rng = random.Random(seed + 1079)
    counts = role_counts(population)
    buildings = [(x, y) for y in range(world.height) for x in range(world.width) if world.get_tile(x, y) == 4]
    streets = [(x, y) for y in range(world.height) for x in range(world.width)
               if world.get_tile(x, y) == 1 and (x, y) not in world.exit_road_tiles and (x, y) not in world.gates.values()]
    x0, y0, x1, y1 = 10, 19, 13, 25  # the Forum, where officials are at noon (assumption)
    forum = [p for p in streets if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]
    people, households = [], {}

    def add(role, household_id, position, home):
        agent = Citizen(len(people), role, household_id, position, home)
        _jitter(agent, rng)
        people.append(agent)
        return agent

    def new_household(head_role, position_options, enslaved_count):
        household_id = len(households)
        home = rng.choice(buildings)
        head = add(head_role, household_id, rng.choice(position_options) if position_options else home, home)
        households[household_id] = dict(id=household_id, head=head.id, members=[head.id], servants=[], home=home,
                                        enslaved_target=enslaved_count)
        return households[household_id]

    for _ in range(counts["magistrate"]):
        new_household("magistrate", forum, ENSLAVED_PER_MAGISTRATE)
    for _ in range(counts["council"]):
        new_household("council", None, ENSLAVED_PER_COUNCILLOR)
    for _ in range(counts["merchant"]):
        new_household("merchant", streets, ENSLAVED_PER_MERCHANT)
    for _ in range(counts["visitor"]):
        new_household("visitor", streets, 0)
    gate_tiles = list(world.gates.values())
    for i in range(counts["guard"]):
        new_household("guard", [gate_tiles[i % len(gate_tiles)]], 0)

    # Free residents fill households of their own.
    remaining = counts["resident"]
    while remaining > 0:
        size = min(remaining, FREE_HOUSEHOLD_SIZE)
        household = new_household("resident", None, 0)
        for _ in range(size - 1):
            member = add("resident", household["id"], household["home"], household["home"])
            household["members"].append(member.id)
        remaining -= size

    # Enslaved people belong to households, the wealthiest first; anyone left joins resident households.
    enslaved_left = counts["enslaved"]
    placed_order = sorted(households.values(), key=lambda h: -h["enslaved_target"])
    for household in placed_order:
        for _ in range(household["enslaved_target"]):
            if enslaved_left <= 0:
                break
            _add_servant(add, rng, household, buildings, streets)
            enslaved_left -= 1
    resident_households = [h for h in households.values() if people[h["head"]].role == "resident"]
    while enslaved_left > 0:
        _add_servant(add, rng, rng.choice(resident_households), buildings, streets)
        enslaved_left -= 1
    return people, households


def _add_servant(add, rng, household, buildings, streets):
    away = rng.random() < AT_WORK_AT_NOON
    position = rng.choice(streets) if away else household["home"]
    agent = add("enslaved", household["id"], position, household["home"])
    household["servants"].append(agent.id)
    household["members"].append(agent.id)


def spread_household_news(people, households, world_distance, rng):
    """Servants who know carry news home. More servants means sooner news; role plays no part."""
    told = []
    for household in households.values():
        head = people[household["head"]]
        if head.knows_danger or not head.is_alive:
            continue
        for servant_id in household["servants"]:
            servant = people[servant_id]
            if servant.knows_danger and servant.is_alive and servant.status == "city":
                distance = world_distance(servant.pos, household["home"])
                if rng.random() < relay_chance(distance):
                    head.knows_danger = True
                    told.append(head.id)
                    break
    return told

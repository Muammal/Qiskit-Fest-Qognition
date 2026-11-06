"""Everyone at the community centre: head-counts, roles, places, noticing, and the SurvivalAgent on a short clock.

Every person decides with the same mind. A role never changes how anyone thinks or how likely they
are to notice something. Roles set where someone starts, their walking speed by age, and whether they
can trigger the alarm. No source gives who was there, so the numbers are assumptions unless cited.
"""
import random

from engine.agent import SurvivalAgent
from engine.chlorine import ODOUR_PPM, START_HOUR, STEP_SECONDS
from engine.site import WALK_M_PER_S

DEFAULT_POPULATION = 100  # assumption: the user's choice; no attendance source
POPULATION_SETTINGS = (40, 100, 300)  # assumption: 40 echoes Edmonton 2018, about 40 evacuated
ROLE_SHARES = dict(child=.55, adult=.30, lifeguard=.10, desk=.05)  # assumption: the user's choice, families and camps
ROLE_SPEED_M_S = dict(child=1.5, adult=1.3, lifeguard=1.3, desk=1.3)  # Rinne et al. (2010), section 4.4.1, medians
ROLE_START = {  # assumption: shares of each role in the pool, on the deck and indoors at 14:00
    "child": dict(pool=.7, pool_deck=.2, indoors=.1),
    "adult": dict(pool=.3, pool_deck=.4, indoors=.3),
    "lifeguard": dict(pool_deck=1.),
    "desk": dict(lobby=1.),
}
STAFF_ROLES = ("lifeguard", "desk")
SMELL_CHANCE = .2  # assumption: chance per 10 s of noticing at the odour threshold, rising with level
WORD_CHANCE = .1  # assumption: chance per 10 s of being told by someone nearby who knows
WORD_RADIUS_TILES = 2  # assumption: about 10 m
CROWD_NOTICE_COUNT = 3  # assumption: people hurrying past within reach before it is noticeable
CROWD_CHANCE = .1  # assumption
ALARM_DELAY_STEPS = 3  # assumption: 30 s after the first staff member knows
ALARM_HEAR_CHANCE = dict(indoors=.5, outdoors=.25)  # assumption: per 10 s; loud pool areas lower
DECISION_SECONDS = 60  # the user's choice: keeps the mind's three-event memory at three minutes
STEP_FRACTION = STEP_SECONDS / 7200  # base decay rates are per two hours

ROLE_NAMES = dict(child="Child", adult="Adult", lifeguard="Lifeguard or instructor", desk="Front desk or maintenance")
ROLE_COLORS = dict(child=(255, 214, 64), adult=(120, 200, 255), lifeguard=(224, 80, 60), desk=(120, 220, 130))
ACTION_LABELS = {
    "hide": "Heads off the site", "rest": "Stays where they are", "explore": "Goes to see what is happening",
    "forage": "Gathers belongings", "drink": "Goes for a drink", "build_shelter": "Goes indoors", "craft": "Helps people nearby",
}
ROLE_ACTION_LABELS = {"lifeguard": {"craft": "Directs people", "rest": "Holds their post"}, "desk": {"craft": "Directs people", "rest": "Stays at the desk"}}

PROVENANCE = {
    "walking_speeds": dict(value="adults 1.3, children 1.5 m/s", status="sourced", url="https://sarjaweb.vtt.fi/pdf/tiedotteet/2010/T2562.pdf", note="section 4.4.1; children's value from one cinema drill"),
    "population": dict(value="100; settings 40 and 300", status="assumption", url=None, note="no attendance source"),
    "role_mix": dict(value=ROLE_SHARES, status="assumption", url=None, note="the user's choice"),
    "start_places": dict(value="see ROLE_START", status="assumption", url=None, note=""),
    "noticing": dict(value="smell, word, crowd, alarm chances", status="assumption", url=None, note="depend on gas, nearness and chance, never role"),
    "alarm": dict(value="first staff member knowing, plus 30 s", status="assumption", url=None, note="a switch; whether an alarm existed is unknown"),
    "independent_children": dict(value="children decide for themselves", status="assumption", url=None, note="no one follows a parent or leader; likely unrealistic"),
    "decision_interval": dict(value="60 s", status="assumption", url=None, note="the user's choice; a test setting. Delay of 0-60 s overlaps the 6-76 s in Rinne et al."),
}


def smell_chance(ppm):
    """Chance of noticing gas in 10 s. Takes only the level, never a role."""
    return min(1., SMELL_CHANCE * ppm / ODOUR_PPM) if ppm >= ODOUR_PPM else 0.


class Patron(SurvivalAgent):
    def __init__(self, agent_id, role, start_pos, decision_offset):
        super().__init__(start_pos)
        self.id, self.role = agent_id, role
        self.hour, self.minute, self.seconds = START_HOUR, 0, 0
        self.decision_offset = decision_offset
        self.status = "site"  # site, out
        self.exit_name = None
        self.knows_danger = False
        self.pending_story = "none"
        self.story_event = "none"
        self.last_action = "rest"
        self.exposure = []
        self.left_step = None
        self.walk_credit = 0.

    @property
    def label(self):
        return f"{ROLE_NAMES[self.role]} (#{self.id})"

    def action_label(self, action):
        return ROLE_ACTION_LABELS.get(self.role, {}).get(action, ACTION_LABELS[action])

    def walk(self, world, field):
        """Walk along a least-time field until this step's seconds run out."""
        if field is None:
            return
        self.walk_credit += STEP_SECONDS / 60 * ROLE_SPEED_M_S[self.role] / WALK_M_PER_S
        p = tuple(self.pos)
        while True:
            q = field.get(p)
            if q is None:
                self.walk_credit = 0.
                break
            cost = world.travel_minutes(p, q)
            if cost > self.walk_credit:  # unspent time carries over, so average speed matches the sourced value
                break
            self.walk_credit -= cost
            p = q
        self.pos = list(p)

    def execute_action(self, action, world, fields, rng):
        """What each of the seven contract actions means on this site, for one 10-second step."""
        if action not in ("hide", "build_shelter"):
            self.walk_credit = 0.
        if action == "hide":
            if self.knows_danger:  # same rule as agent.py: with no warning, nobody knows to run
                self.walk(world, fields["leave"])
        elif action == "build_shelter":
            self.walk(world, fields["indoors"])
        elif action == "explore":
            options = [p for p in world.neighbors(tuple(self.pos)) if world.walkable(p)]
            if options:
                self.pos = list(rng.choice(options))
        elif action == "drink":
            self.needs["thirst"] = min(1, self.needs["thirst"] + .3 * STEP_FRACTION)  # assumption: no fountains mapped
        elif action == "rest":
            self.needs["energy"] = min(1, self.needs["energy"] + .02 * STEP_FRACTION)
        # forage and craft keep the person in place; assumption, since belongings and helping are not modelled.
        if action != "rest":
            self.needs["energy"] = max(0, self.needs["energy"] - .025 * STEP_FRACTION)

    def step_decay(self):
        """Slow needs fall on this short clock. Clock advances by 10 s."""
        self.needs["hunger"] = max(0., self.needs["hunger"] - .025 * STEP_FRACTION)
        self.needs["thirst"] = max(0., self.needs["thirst"] - STEP_FRACTION / 36)
        self.seconds += STEP_SECONDS
        if self.seconds >= 60:
            self.seconds -= 60
            self.minute += 1
            if self.minute >= 60:
                self.minute -= 60
                self.hour += 1

    def update_stress(self):
        """Same formula as Pompeii, applied once per decision so it isn't washed out at 10-second steps."""
        peril = ((1. - self.needs["safety"]) * .35 + (1. - self.needs["thirst"]) * .25 + (1. - self.needs["hunger"]) * .2
                 + (1. - self.needs["warmth"]) * .15 + (.2 if self.injured else 0.))
        self.stress = round(.7 * self.stress + .3 * min(1., peril), 3)


def role_counts(population=DEFAULT_POPULATION):
    counts = {role: max(1, round(population * share)) for role, share in ROLE_SHARES.items() if role != "child"}
    counts["child"] = population - sum(counts.values())
    return counts


def build_patrons(world, seed, population=DEFAULT_POPULATION, decision_seconds=DECISION_SECONDS):
    """Everyone with a role and a starting place. Decision times are staggered, so people don't all decide at once."""
    rng = random.Random(seed + 2012)
    cycle = max(1, decision_seconds // STEP_SECONDS)
    pool = sorted(world.areas["pool"])
    places = dict(pool=pool, pool_deck=sorted(world.areas["pool_deck"]), indoors=sorted(world.areas["indoors"]), lobby=sorted(world.areas["lobby"]))
    people = []
    for role in ROLE_SHARES:
        names, weights = zip(*ROLE_START[role].items())
        for _ in range(role_counts(population)[role]):
            place = rng.choices(names, weights)[0]
            agent = Patron(len(people), role, rng.choice(places[place]), rng.randrange(cycle))
            agent.needs["safety"] = round(agent.needs["safety"] + rng.choice((-.05, 0., .05)), 3)  # same jitter as Pompeii
            agent.stress = round(agent.stress + rng.choice((-.05, 0., .05)), 3)
            people.append(agent)
    return people

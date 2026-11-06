"""Titanic simulation loop with the same public shape as SimulationEngine.

Everyone aboard runs the same decide_fn, unedited. The mind only understands its
frozen event names, so ship events reach it under existing names (EVENT_NAMES);
the screen and timeline carry the real wording in `story`.
The historical numbers are context for the result, not targets it is fitted to.
"""
import copy
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import contracts
from engine.crowd import NO_LIFEBELT_DROWN_CHANCE, ROLE_NAMES, build_crowd
from engine.events import EventGenerator
from engine.flood import (COLLISION_STEP, HORIZON, LOAD_STEP, ROCKET_STEPS, SINK_STEP, UNCOVER_STEP,
                          FloodModel)
from engine.lifeboats import LifeboatSchedule
from engine.ship import BOAT, D, E, ShipWorld

try:
    from mind.quantum_mind import classical_mixture_decide
except ImportError:
    classical_mixture_decide = None

# Ship event -> frozen contract event. Rotations for ambiguous signs, collapse for certainty.
EVENT_NAMES = {
    "collision": "tremor", "ship_tilting": "tremor",
    "steward_warning": "gas_plume", "crowd_moving": "gas_plume", "orders_to_crew": "gas_plume",
    "distress_rocket": "ash_fall", "officers_told_ship_will_sink": "eruption", "water_at_feet": "eruption",
}
<<<<<<< Updated upstream
EVENT_MAPPINGS = {
    "default": {},  # Rockets trigger projective collapse (ash_fall), steward warning is ambiguous (gas_plume)
    "ambiguous_rockets": {"distress_rocket": "gas_plume"},  # Rockets treated as ambiguous rotation (tests quantum coherence)
    "early_pa_alarm": {"steward_warning": "eruption", "orders_to_crew": "eruption"},  # Unambiguous PA / alarm policy intervention
}
EVENT_MAPPINGS["only_water_certain"] = {"distress_rocket": "gas_plume", "officers_told_ship_will_sink": "gas_plume"}
DEFAULT_MAPPING = "default"
=======
# The first version's translation is A. B and C read more events as uncertain. Nothing in the mind changes.
EVENT_MAPPINGS = {
    "A": EVENT_NAMES,
    "B": {**EVENT_NAMES, "distress_rocket": "gas_plume"},  # rockets as a warning, not certainty
    "C": {**EVENT_NAMES, "distress_rocket": "gas_plume", "officers_told_ship_will_sink": "gas_plume"},  # only water is certain
}
DEFAULT_MAPPING = "A"  # provisional; the user chooses after the side-by-side test
>>>>>>> Stashed changes
STORY_TEXT = {
    "none": "Nothing new", "collision": "A shudder runs through the ship",
    "ship_tilting": "The deck is visibly tilting", "steward_warning": "A steward says to put on lifebelts",
    "crowd_moving": "People nearby are heading upstairs", "orders_to_crew": "Crew ordered to stations",
    "distress_rocket": "Distress rockets overhead", "officers_told_ship_will_sink": "Told the ship will sink",
    "water_at_feet": "Water is reaching this deck",
}
COLLISION_FELT_FAR = .35  # assumption: slight shudder away from the forward lower decks
ROCKET_SEEN_INDOORS = .3  # assumption: rockets noticed from inside upper decks
WARNING_RADIUS = 3  # assumption: a steward reaches cabins within about 20 m
WARNING_HEARD = .6  # assumption: chance per step of being roused by a nearby steward
CROWD_NOTICED = .3  # assumption: chance per step of noticing others moving
CROWD_NOTICE_COUNT = 5  # assumption: people moving on a tile before it is noticeable
TILT_NOTICED_FROM_DEG = 4.  # assumption: trim begins to be felt underfoot
TILT_NOTICED_PER_DEG = .03  # assumption: chance per step, per degree of trim
RESCUE_ATTEMPT = .5  # assumption: chance per step of reaching a floated collapsible
FOCUS_ROLE_CYCLE = (("passenger", "third"), ("passenger", "first"), ("server", "crew"),
                    ("evac_worker", "crew"), ("passenger", "second"), ("officer", "crew"), ("captain", "crew"))
HISTORICAL = dict(aboard=2208, saved=712, source="Wikipedia casualty table citing Encyclopedia Titanica")


class TitanicSimulation:
    def __init__(self, seed=42, mind_type='quantum', noise_source='stub', decide_fn=None,
<<<<<<< Updated upstream
                 scenario='titanic', scripted_events=None, event_mapping=DEFAULT_MAPPING,
                 warned_only_hide=False, crew_seats=3, allow_all_sides=False,
                 inputs='original', crew_told=True, boarding_rule=True):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source, self.scenario = noise_source, scenario
        self.scripted_events = dict(scripted_events) if scripted_events else {}
        self.event_mapping = event_mapping
        self.event_names = {**EVENT_NAMES, **EVENT_MAPPINGS.get(event_mapping, {})}
        self.warned_only_hide = warned_only_hide
        self.crew_seats = crew_seats
        self.allow_all_sides = allow_all_sides
        # 'neutral' removes the safety cap by deck and the nudge after hide, and hide then needs a warning.
        self.inputs, self.crew_told = inputs, crew_told
        self.neutral_inputs = inputs == 'neutral'
=======
                 scenario='titanic', scripted_events=None, inputs='neutral', event_mapping=DEFAULT_MAPPING,
                 crew_told=True, boarding_rule=True):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source, self.scenario = noise_source, scenario
        self.scripted_events = dict(scripted_events) if scripted_events else {}
        # 'original' reproduces the first version: safety capped by deck, a nudge after hide, and hide without a warning.
        self.neutral_inputs = inputs == 'neutral'
        self.inputs, self.event_mapping, self.crew_told = inputs, event_mapping, crew_told
        self.event_names = EVENT_MAPPINGS[event_mapping]
>>>>>>> Stashed changes
        self.horizon = HORIZON
        self.world = ShipWorld(seed=seed)
        self.initial_world = copy.deepcopy(self.world.export_dict())
        self.flood = FloodModel(seed, self.world)
        self.volcano = self.flood  # GUI and exports read hazards through this shared attribute name
        self.event_gen = EventGenerator(seed, horizon=HORIZON)
        self.event_gen.weather = ['calm'] * HORIZON  # Wikipedia: clear, flat calm night
        self.event_gen.world_events = list(self.flood.world_events)
<<<<<<< Updated upstream
        self.boats = LifeboatSchedule(self.world, crew_seats=crew_seats, allow_all_sides=allow_all_sides,
                                      boarding_rule=boarding_rule)
=======
        self.boats = LifeboatSchedule(self.world, boarding_rule=boarding_rule)
>>>>>>> Stashed changes
        self.people = build_crowd(self.world, seed)
        for person in self.people:
            person.neutral_inputs = self.neutral_inputs
        self.agent = self._default_focus()
        if decide_fn:
            self.decide_fn = decide_fn
        elif self.mind_type == 'quantum':
            self.decide_fn = contracts.quantum_decide
        elif self.mind_type == 'classical_mixture' and classical_mixture_decide is not None:
            self.decide_fn = classical_mixture_decide
        else:
            self.decide_fn = contracts.classical_decide
        self.steps = []
        self.t = 0
        self.rng = random.Random(seed + 77)
        self.random_state = random.Random(seed).getstate()
        self.moving_tiles = Counter()
        self.deaths_by_step = []
        self.scenes = []  # cutscene requests for the step just run
        self._memo, self._memo_fn = {}, None
        self.mind_calls = 0

    def _default_focus(self):
        role, cabin = FOCUS_ROLE_CYCLE[self.seed % len(FOCUS_ROLE_CYCLE)]
        options = [p for p in self.people if p.role == role and p.cabin_class == cabin]
        return options[self.seed % len(options)]

    def set_focus(self, agent):
        self.agent = agent

    def _decide(self, state):
        """Same answer as calling the mind; it ignores pos and day, so equal inputs share a result."""
        if self._memo_fn is not self.decide_fn:
            self._memo, self._memo_fn = {}, self.decide_fn
        needs = state["needs"]
        key = (needs["hunger"], needs["thirst"], needs["warmth"], needs["energy"], needs["safety"], needs["morale"],
               state["stress"], state["injured"], state["hour"], state["inventory"].get("wood", 0),
               tuple(state["recent_events"]))
        decision = self._memo.get(key)
        if decision is None:
            decision = self.decide_fn(state)
            contracts.validate_decision(decision)
            self._memo[key] = decision
            self.mind_calls += 1
        return decision

    def _perceive(self, agent, t, warned_tiles):
        """One ship event per person per step, the most salient they could have noticed."""
        pos = tuple(agent.pos)
        rng, world = self.rng, self.world
        if pos in world.rising or pos in world.flooded:
            return "water_at_feet"
        if t in self.scripted_events:
            return self.scripted_events[t]
        if t == COLLISION_STEP:
            forward_below = pos[0] >= 22 and pos[1] >= E
            return "collision" if forward_below or rng.random() < COLLISION_FELT_FAR else "none"
        crew = agent.cabin_class == "crew"
        if self.crew_told:
            if t == UNCOVER_STEP and agent.role in ("captain", "officer", "evac_worker"):
                return "officers_told_ship_will_sink"
            if t in (UNCOVER_STEP, LOAD_STEP) and crew:
                return "orders_to_crew"
        if t in ROCKET_STEPS:
            on_deck = world.get_tile(*pos) == 1
            if on_deck or (pos[1] < D and rng.random() < ROCKET_SEEN_INDOORS):
                return "distress_rocket"
        if t >= UNCOVER_STEP and pos in warned_tiles and rng.random() < WARNING_HEARD:
            return "steward_warning"
        if self.moving_tiles.get(pos, 0) >= CROWD_NOTICE_COUNT and rng.random() < CROWD_NOTICED:
            return "crowd_moving"
        trim = self.flood.hazard_by_step[t]["trim_deg"]
        if trim >= TILT_NOTICED_FROM_DEG and rng.random() < trim * TILT_NOTICED_PER_DEG:
            return "ship_tilting"
        return "none"

    def _warned_tiles(self):
        warned = set()
        for person in self.people:
            if person.role == "server" and person.status == "aboard" and person.is_alive \
                    and person.last_action != "hide" and self.t >= UNCOVER_STEP and (self.crew_told or person.knows_danger):
                x, y = person.pos
                for dx in range(-WARNING_RADIUS, WARNING_RADIUS + 1):
                    warned.add((x + dx, y))
        return warned

    def _fields(self, t):
        world = self.world
        stations = self.boats.open_stations(t)
        indoors = [(x, y) for y in range(world.height) for x in range(world.width)
                   if world.get_tile(x, y) == 4 and (x, y) not in world.flooded and (x, y) not in world.rising]
        waiting = Counter(p.pos[0] for p in self.people
                          if p.is_alive and p.status == "aboard" and p.pos[1] == BOAT)
        free_seats = Counter()
        for boat in self.boats.boats:
            if boat.state != "lowered":
                free_seats[boat.station[0]] += boat.free_seats
        return dict(boats=world.next_step_field(stations) if stations else None,
                    indoors=world.next_step_field(indoors) if indoors else None,
                    stations={x: (waiting[x], free) for x, free in free_seats.items()})

    def step(self):
        t = self.t
        if t >= self.horizon or self._finished():
            return None
        world, hazard = self.world, self.flood.hazard_by_step[t]
        world.flooded.update(map(tuple, hazard['new_flood']))
        world.rising = set(map(tuple, hazard['rising']))
        self.scenes = []
        warned = self._warned_tiles()
        fields = self._fields(t)
        crowding = Counter(tuple(p.pos) for p in self.people if p.is_alive and p.status == "aboard")
        moving = Counter()
        external_state = random.getstate()
        random.setstate(self.random_state)
        focus_record = None
        try:
            for agent in self.people:
                if not agent.is_alive or agent.status == "boat":
                    continue
                record = self._step_person(agent, t, warned, fields, crowding, moving)
                if agent is self.agent:
                    focus_record = record
            self.random_state = random.getstate()
        finally:
            random.setstate(external_state)
        self.moving_tiles = moving
        self._boats_step(t)
        self._hazards_step(t)
        self.t += 1
        return self._focus_step_record(t, focus_record)

    def _step_person(self, agent, t, warned, fields, crowding, moving):
        world = self.world
        story = self._perceive(agent, t, warned)
        event = self.event_names.get(story, "none")
        agent.story_event = story
        if event != "none":
            agent.knows_danger = True
        in_shelter = world.is_in_shelter(*agent.pos) and agent.status == "aboard"
        agent.apply_event(event, in_shelter)
        state = agent.get_state()
        decision = self._decide(state)
        action = decision['action']
        agent.last_action = action
        before = tuple(agent.pos)
        if agent.status == "aboard":
            agent.execute_ship_action(action, world, fields, crowding, self.rng,
                                      warned_only_hide=self.warned_only_hide)
            if tuple(agent.pos) != before and action == "hide":
                moving[before] += 1
        agent.step_decay(world.is_in_shelter(*agent.pos) and agent.status == "aboard")
        record = dict(t=t, state=state, event=event, story=STORY_TEXT[story], action=action,
                      action_label=agent.action_label(action), probs=decision['probs'], reason=decision['reason'],
                      quantum=decision.get('quantum'), pos_after=list(agent.pos), phase=self.flood.phases[t],
                      status=agent.status)
        agent.log.append(record)
        return record

    def _boats_step(self, t):
        at_station = defaultdict(list)
        for agent in self.people:
            if agent.is_alive and agent.status == "aboard" and agent.last_action == "hide" \
                    and tuple(agent.pos)[1] == BOAT and (agent.knows_danger or not self.neutral_inputs):
                at_station[tuple(agent.pos)].append(agent)
        boarded = self.boats.load(t, at_station)
        self._scene_boarding(t, boarded)
        launched = self.boats.launch_due(t)
        if launched:
            names = ", ".join(boat.id for boat in launched)
            aboard = sum(len(boat.aboard) for boat in launched)
            self._add_scene("boat_lowered", t, f"Lifeboat {names} lowered: {aboard} aboard of "
                            f"{sum(boat.seats for boat in launched)} seats",
                            focus=self.agent.boat_id in {boat.id for boat in launched}, side=launched[0].side)
        floated = self.boats.float_off_due(t)
        if floated:
            self._add_scene("float_off", t, "Collapsibles A and B float off as the bridge goes under",
                            focus=False, side="starboard")
        if any(boat.state == "floated" for boat in self.boats.floating):
            for agent in self.people:
                if agent.is_alive and agent.status == "water" and agent.last_action == "hide" \
                        and self.rng.random() < RESCUE_ATTEMPT:
                    self.boats.rescue(agent)

    def _scene_boarding(self, t, boarded):
        if not boarded:
            return
        focus = next(((a, b) for a, b in boarded if a is self.agent), None)
        agent, boat = focus or boarded[0]
        count = len(boarded)
        caption = (f"{agent.label} jumps into lifeboat {boat.id}" if focus
                   else f"{count} people climb and jump into the lifeboats")
        self._add_scene("jump_boat", t, caption, focus=bool(focus), side=boat.side, role=agent.role)

    def _add_scene(self, kind, t, caption, focus=False, side="starboard", role="passenger", count=1):
        self.scenes.append(dict(kind=kind, t=t, caption=caption, focus=focus, side=side, role=role, count=count,
                                trim_deg=self.flood.hazard_by_step[t]["trim_deg"]))

    def _hazards_step(self, t):
        """Water wins after everyone has moved: below decks drowns, on deck goes overboard."""
        world, jumpers, swept, deaths = self.world, [], 0, 0
        for agent in self.people:
            if not agent.is_alive or agent.status == "boat":
                continue
            pos = tuple(agent.pos)
            if agent.status == "water":
                if not agent.inventory["lifebelt"] and self.rng.random() < NO_LIFEBELT_DROWN_CHANCE:
                    agent.is_alive, agent.cause_of_death = False, "drowning"
                continue
            if pos in world.flooded:
                if world.get_tile(*pos) == 1 or pos[1] == BOAT:  # open air: washed into the sea
                    agent.enter_water()
                    swept += 1
                else:  # below decks: trapped as the compartment fills
                    agent.is_alive, agent.cause_of_death = False, "drowning"
                    deaths += 1
            elif pos in world.rising and world.get_tile(*pos) == 1:
                agent.enter_water()
                jumpers.append(agent)
        if jumpers:
            focus = self.agent in jumpers
            who = self.agent if focus else jumpers[0]
            caption = (f"{who.label} jumps overboard into -2 C water" if focus
                       else f"{len(jumpers)} people jump overboard into -2 C water")
            self._add_scene("jump_sea", t, caption, focus=focus, role=who.role, count=len(jumpers))
        self.deaths_by_step.append(deaths)

    def _focus_step_record(self, t, focus_record):
        if focus_record is not None:
            record = focus_record
        else:  # the followed person is already in a boat or dead; keep the shared timeline moving
            agent = self.agent
            state = agent.get_state()
            status = "In a lifeboat" if agent.status == "boat" else "Dead"
            record = dict(t=t, state=state, event="none", story=status, action="rest", action_label=status,
                          probs={a: 1. / len(contracts.ACTIONS) for a in contracts.ACTIONS},
                          reason=f"{status}: no further decisions.", quantum=None, pos_after=list(agent.pos),
                          phase=self.flood.phases[t], status=agent.status)
        record = dict(record, counts=self.counts())
        self.steps.append(record)
        return record

    def _finished(self):
        if self.t <= SINK_STEP:
            return False
        return not any(p.is_alive and p.status != "boat" for p in self.people)

    def counts(self):
        tally = Counter()
        for person in self.people:
            tally["dead" if not person.is_alive else person.status] += 1
        return dict(aboard=tally["aboard"], boats=tally["boat"], water=tally["water"], dead=tally["dead"])

    def outcome_table(self):
        rows = defaultdict(lambda: [0, 0])
        for person in self.people:
            key = person.cabin_class if person.role == "passenger" else person.role
            rows[key][0] += 1
            rows[key][1] += person.status == "boat" and person.is_alive
        return {key: dict(aboard=a, saved=s) for key, (a, s) in rows.items()}

    def timeline(self):
        world = copy.deepcopy(self.world.export_dict())
        world['initial_tiles'] = copy.deepcopy(self.initial_world['tiles'])
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, scenario=self.scenario)
        world['weather'] = list(self.event_gen.weather)
        world['flood'] = self.flood.export_dict()

        def first(predicate):
            return next((r['t'] for r in self.steps if predicate(r)), None)

        boarded = first(lambda r: r.get('status') == 'boat')
        evacuation = dict(
            first_sign_step=first(lambda r: r['event'] != 'none'),
            first_evacuating_step=first(lambda r: r['action'] == 'hide'),
            boarded_step=boarded,
            onset_step=self.flood.onset_step,
            sink_step=self.flood.sink_step,
        )
        focus = self.agent
        counts = self.counts()
        return dict(world=world, steps=self.steps, evacuation=evacuation,
                    outcome='survived' if focus.is_alive else 'died', cause=focus.cause_of_death,
                    focus=dict(id=focus.id, role=focus.role, label=focus.label, status=focus.status),
                    crowd=dict(counts=counts, by_group=self.outcome_table(), boats=self.boats.export_dict(),
                               water_rescued=self.boats.water_rescued, historical=HISTORICAL,
                               roles={role: sum(p.role == role for p in self.people) for role in ROLE_NAMES}))

    def run(self, max_steps=HORIZON, step_callback=None):
        while self.t < min(max_steps, self.horizon):
            record = self.step()
            if record is None:
                break
            if step_callback:
                step_callback(record, self)
        return self.timeline()

    def run_and_save(self, output_path, max_steps=HORIZON):
        timeline = self.run(max_steps)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(timeline, separators=(',', ':')), encoding='utf-8')
        return timeline


def compare_titanic_policies(seed=42, minds=('quantum', 'classical_mixture', 'classical')):
    """Run counterfactual evacuation policy interventions across cognitive models."""
    policies = {
        "historical_baseline": dict(event_mapping="default", warned_only_hide=False, allow_all_sides=False),
        "ambiguous_rockets": dict(event_mapping="ambiguous_rockets", warned_only_hide=False, allow_all_sides=False),
        "early_pa_alarm": dict(event_mapping="early_pa_alarm", warned_only_hide=False, allow_all_sides=False),
        "open_boarding_both_sides": dict(event_mapping="early_pa_alarm", warned_only_hide=False, allow_all_sides=True),
    }
    results = {}
    for policy_name, kwargs in policies.items():
        results[policy_name] = {}
        for mind in minds:
            sim = TitanicSimulation(seed=seed, mind_type=mind, **kwargs)
            sim.run()
            counts = sim.counts()
            results[policy_name][mind] = dict(
                saved=counts["boats"],
                dead=counts["dead"],
                survival_rate=round(counts["boats"] / len(sim.people), 4),
            )
    return results



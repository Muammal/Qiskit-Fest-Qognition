"""Pompeii simulation loop with the same public shape as SimulationEngine and TitanicSimulation.

Everyone runs the same decide_fn, unedited, on the frozen state contract. What a person
notices depends on distance, being indoors, visibility and chance, never on role.
The historical figures in COMPARISON are context for the result, not targets it is fitted to.
"""

import copy
import json
import math
import random
from collections import Counter
from pathlib import Path

import contracts
from engine.citizens import DEFAULT_POPULATION, ROLE_NAMES, build_citizens, notice_chance, spread_household_news
from engine.city import CityWorld, RegionWorld
from engine.eruption import FALL_END_STEP, HORIZON, PLINIAN_STEP, PUMICE_TOTAL_M, TOWN_KM, EruptionModel
from engine.events import EventGenerator

try:
    from mind.quantum_mind import classical_mixture_decide
except ImportError:
    classical_mixture_decide = None

STORY_TEXT = {
    "none": "Nothing new",
    "column_seen": "A great column rises over Vesuvius",
    "pumice_falling": "Pumice is falling",
    "quake": "The ground shakes",
    "collapse_nearby": "A building collapses nearby",
    "servant_news": "A servant brings news",
    "word_of_mouth": "Neighbours talk of danger",
    "crowd_moving": "People are hurrying past",
    "flow_seen": "A burning cloud is coming down the mountain",
    "hurt_by_collapse": "A roof comes down on you",
}
EVENT_NAMES = {  # town events reach the mind under its existing names; these parts are common to every mapping
    "flow_seen": "eruption",
    "quake": "tremor",
    "collapse_nearby": "tremor",
    "servant_news": "gas_plume",
    "word_of_mouth": "gas_plume",
    "crowd_moving": "gas_plume",
    "hurt_by_collapse": "injury",
}
# How the column and the falling pumice are translated. The user chose B on meaning, as the most
# literal, and asked for all four to be reported: quantum deaths range from 0 to about 1,000 across them.
EVENT_MAPPINGS = {
    "A": dict(column_seen="eruption", pumice_falling="ash_fall"),  # both read as certain danger
    "B": dict(column_seen="gas_plume", pumice_falling="ash_fall"),  # most literal; the default
    "C": dict(column_seen="gas_plume", pumice_falling="gas_plume"),  # both ambiguous, as gas_plume
    "D": dict(column_seen="tremor", pumice_falling="tremor"),  # both ambiguous, as tremor
}
DEFAULT_MAPPING = "B"
COLLAPSE_DEATH_CHANCE = 0.5  # assumption: the user's choice; no source gives odds
COLLAPSE_INJURY_STEPS = 8  # assumption: two hours of slowed walking
COLLAPSE_NOTICE_TILES = 2  # assumption: about 60 m
BAY_SCENE_DELAY_STEPS = 6  # display only: the wide shot follows the column by 90 minutes
CROWD_SCENE_MIN_MOVING = 800  # display only: when the aerial shot of the crowds plays
CROWD_NOTICE_COUNT = 5  # assumption: people hurrying past on one tile before it is noticeable
GATE_CROSSINGS_PER_STEP = 1_000  # assumption: limit per gate per 15 minutes; part of the crowding switch
SAFE_ROAD_ENDS = ("nola", "sarno", "nocera", "stabia")  # the Naples and Vesuvio roads end on the mountain's flank; no boats
FOCUS_ROLE_CYCLE = ("resident", "enslaved", "merchant", "council", "guard", "visitor", "magistrate")
COMPARISON = dict(
    bodies_found_on_site=1150,
    share_of_known_victims_in_pumice_phase=0.38,
    share_of_flow_phase_victims_on_roads=0.49,
    source="Luongo et al. 2003, doi 10.1016/S0377-0273(03)00147-1, abstract",
    caution="Body counts are excavated finds, not total deaths. No source gives survivors.",
)


class PompeiiSimulation:
    def __init__(
        self,
        seed=42,
        mind_type="quantum",
        noise_source="stub",
        decide_fn=None,
        scenario="pompeii",
        scripted_events=None,
        population=DEFAULT_POPULATION,
        date="august",
        quake=True,
        restrict_enslaved=False,
        crowding=True,
        event_mapping=DEFAULT_MAPPING,
    ):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source, self.scenario = noise_source, scenario
        self.scripted_events = dict(scripted_events) if scripted_events else {}
        self.restrict_enslaved, self.crowding = restrict_enslaved, crowding
        self.event_mapping = event_mapping
        self.event_names = {**EVENT_NAMES, **EVENT_MAPPINGS[event_mapping]}
        self.horizon = HORIZON
        self.world = CityWorld(seed=seed)
        self.region = RegionWorld(seed=seed)
        self.initial_world = copy.deepcopy(self.world.export_dict())
        self.eruption = EruptionModel(seed, self.world, region=self.region, date=date, quake=quake)
        self.volcano = self.eruption  # GUI and exports read hazards through this shared attribute name
        self.event_gen = EventGenerator(seed, horizon=HORIZON)
        self.event_gen.weather = ["calm"] * HORIZON  # assumption: no rain modelled
        self.event_gen.world_events = list(self.eruption.world_events)
        self.people, self.households = build_citizens(self.world, seed, population)
        self.agent = self._default_focus()
        self.watched = {self.agent.id}
        if decide_fn:
            self.decide_fn = decide_fn
        elif self.mind_type == "quantum":
            self.decide_fn = contracts.quantum_decide
        elif self.mind_type == "classical_mixture" and classical_mixture_decide is not None:
            self.decide_fn = classical_mixture_decide
        else:
            self.decide_fn = contracts.classical_decide
        self.steps, self.t, self.scenes = [], 0, []
        self.logs = {self.agent.id: []}
        self.rng = random.Random(seed + 7900)
        self.random_state = random.Random(seed).getstate()
        self.moving_tiles = Counter()
        self.deaths = []  # (t, cause, role, was_on_street)
        self._memo, self._memo_fn = {}, None
        self.mind_calls = 0
        self._exit_gate = {tile: gate for gate, tile in self.world.exits.items()}
        self._city_leave = self.world.next_step_field(self.world.exits.values())
        ends = [self.region.road_ends[name] for name in SAFE_ROAD_ENDS]
        self._region_leave = self.region.next_step_field(ends)
        self._region_ends = set(map(tuple, ends))
        self._water = self.world.next_step_field(self.world.freshwater_tiles)
        self._indoors_cache = None
        self._scenes_played, self._last_flow_size = set(), 0

    def _default_focus(self):
        role = FOCUS_ROLE_CYCLE[self.seed % len(FOCUS_ROLE_CYCLE)]
        options = [p for p in self.people if p.role == role]
        return options[self.seed % len(options)]

    def set_focus(self, agent):
        self.agent = agent
        self.watch(agent)

    def watch(self, agent):
        """Keep a full log for this person from now on. Others keep none, to save memory."""
        self.watched.add(agent.id)
        self.logs.setdefault(agent.id, [])

    def _decide(self, state):
        """Same answer as calling the mind: it ignores pos and day, so equal inputs share a result."""
        if self._memo_fn is not self.decide_fn:
            self._memo, self._memo_fn = {}, self.decide_fn
        needs = state["needs"]
        key = (
            needs["hunger"],
            needs["thirst"],
            needs["warmth"],
            needs["energy"],
            needs["safety"],
            needs["morale"],
            state["stress"],
            state["injured"],
            state["hour"],
            state["inventory"].get("wood", 0),
            tuple(state["recent_events"]),
        )
        decision = self._memo.get(key)
        if decision is None:
            decision = self.decide_fn(state)
            contracts.validate_decision(decision)
            self._memo[key] = decision
            self.mind_calls += 1
        return decision

    def _indoor_field(self):
        """Nearest standing building; rebuilt only when a roof has fallen."""
        if self._indoors_cache is None:
            standing = [(x, y) for y in range(self.world.height) for x in range(self.world.width) if self.world.get_tile(x, y) == 4]
            self._indoors_cache = self.world.next_step_field(standing) if standing else None
        return self._indoors_cache

    def _world_of(self, person):
        return self.world if person.status == "city" else self.region

    def _depth_at(self, person, hazard):
        if person.status == "city":
            return hazard["pumice_m"]
        x, y = person.pos
        return int(hazard["region_ash_grid"][y][x]) / 9 * PUMICE_TOTAL_M

    def _is_indoors(self, person):
        return person.status == "city" and self.world.get_tile(*person.pos) == 4

    def _collapse_buildings(self, t, hazard):
        """Roofs and walls fall before anyone moves this step. Returns injured people and tiles to notice."""
        fallen = set(map(tuple, hazard["new_collapse"]))
        hurt = set()
        if not fallen:
            return fallen, hurt
        for x, y in fallen:
            self.world.tiles[y][x] = 1  # rubble: open to walk over, no longer cover
        self._indoors_cache = None
        for person in self.people:
            if person.is_alive and person.status == "city" and tuple(person.pos) in fallen:
                if self.rng.random() < COLLAPSE_DEATH_CHANCE:
                    self._kill(person, t, "roof_collapse")
                else:
                    person.injured = True
                    person.injury_cooldown = COLLAPSE_INJURY_STEPS
                    hurt.add(person.id)
        return fallen, hurt

    def _kill(self, person, t, cause):
        person.is_alive, person.cause_of_death = False, cause
        was_on_street = person.status != "city" or self.world.get_tile(*person.pos) != 4
        self.deaths.append((t, cause, person.role, was_on_street))

    def _perceive(self, person, t, hazard, fallen, hurt, told, knowing):
        """One event per person per step, the most salient they could have noticed."""
        if person.id in hurt:
            return "hurt_by_collapse"
        if t in self.scripted_events:
            return self.scripted_events[t]
        rng = self.rng
        indoors = self._is_indoors(person)
        visibility = hazard["visibility"]
        runout = hazard["flow_runout_km"]
        if runout:
            distance_tiles = max(0.0, math.dist(person.pos, self.region.vent) * 0.25 * 1000 / 30 if person.status != "city" else (TOWN_KM - runout) * 1000 / 30)
            if rng.random() < notice_chance(distance_tiles, indoors, visibility):
                return "flow_seen"
        if t == PLINIAN_STEP and rng.random() < notice_chance(0, indoors, 1.0):
            return "column_seen"
        if PLINIAN_STEP < t < FALL_END_STEP and rng.random() < notice_chance(0, indoors, 1.0):
            return "pumice_falling"
        if hazard["quake"]:
            return "quake"
        if fallen and person.status == "city":
            x, y = person.pos
            if any(abs(x - a) + abs(y - b) <= COLLAPSE_NOTICE_TILES for a, b in fallen) and rng.random() < notice_chance(1, indoors, visibility):
                return "collapse_nearby"
        if person.id in told:
            return "servant_news"
        if person.status == "city" and knowing.get(tuple(person.pos), 0) and not person.knows_danger and rng.random() < notice_chance(0, indoors, visibility):
            return "word_of_mouth"
        if self.moving_tiles.get(tuple(person.pos), 0) >= CROWD_NOTICE_COUNT and rng.random() < notice_chance(0, indoors, visibility):
            return "crowd_moving"
        return "none"

    def step(self):
        t = self.t
        if t >= self.horizon or self._finished():
            return None
        hazard = self.eruption.hazard_by_step[t]
        self.world.ash = hazard["ash"]
        self.world.ash_grid = hazard["ash_grid"]
        self.scenes = []
        fallen, hurt = self._collapse_buildings(t, hazard)
        told = set(spread_household_news(self.people, self.households, lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1]), self.rng))
        knowing = Counter(tuple(p.pos) for p in self.people if p.is_alive and p.status == "city" and p.knows_danger)
        crowding = Counter(tuple(p.pos) for p in self.people if p.is_alive and p.status == "city") if self.crowding else None
        city_fields = dict(leave=self._city_leave, indoors=self._indoor_field(), water=self._water)
        region_fields = dict(leave=self._region_leave)
        moving = Counter()
        crossings = Counter()
        focus_record = None
        external_state = random.getstate()
        random.setstate(self.random_state)
        try:
            for person in self.people:
                if not person.is_alive or person.status == "escaped":
                    continue
                record = self._step_person(person, t, hazard, fallen, hurt, told, knowing, city_fields, region_fields, crowding, moving, crossings)
                if person is self.agent:
                    focus_record = record
            self.random_state = random.getstate()
        finally:
            random.setstate(external_state)
        self.moving_tiles = moving
        focus_before = (self.agent.is_alive, self.agent.status)
        self._apply_flows(t, hazard)
        self._emit_scenes(t, hazard, fallen, hurt, sum(moving.values()), focus_before)
        self.t += 1
        return self._focus_step_record(t, focus_record)

    def _step_person(self, person, t, hazard, fallen, hurt, told, knowing, city_fields, region_fields, crowding, moving, crossings):
        story = self._perceive(person, t, hazard, fallen, hurt, told, knowing)
        event = self.event_names.get(story, "none")
        person.story_event = story
        if event != "none":
            person.knows_danger = True
        person.apply_event(event, self._is_indoors(person))
        state = person.get_state()
        decision = self._decide(state)
        action = decision["action"]
        person.last_action = action
        before = tuple(person.pos)
        world = self._world_of(person)
        fields = city_fields if person.status == "city" else region_fields
        head = self.people[self.households[person.household]["head"]]
        head_in_town = head.is_alive and head.status == "city"
        person.execute_town_action(
            action,
            world,
            fields,
            crowding if person.status == "city" else None,
            self.rng,
            self._depth_at(person, hazard),
            hazard["visibility"],
            self.restrict_enslaved,
            head_in_town,
        )
        if action == "hide" and tuple(person.pos) != before:
            moving[before] += 1
        self._cross_boundaries(person, crossings)
        person.step_decay(self._is_indoors(person), temperature_c=hazard["temperature_c"])
        if person.id not in self.watched:
            return None
        record = dict(
            t=t,
            state=state,
            event=event,
            story=STORY_TEXT[story],
            action=action,
            action_label=person.action_label(action),
            probs=decision["probs"],
            reason=decision["reason"],
            quantum=decision.get("quantum"),
            pos_after=list(person.pos),
            phase=self.eruption.phases[t],
            status=person.status,
        )
        self.logs[person.id].append(record)
        return record

    def _add_scene(self, kind, t, caption, focus=False, **extra):
        self.scenes.append(dict(kind=kind, t=t, caption=caption, focus=focus, role=self.agent.role, **extra))

    def _emit_scenes(self, t, hazard, fallen, hurt, moving_count, focus_before):
        """Requests for the display only. Nothing here feeds back into the simulation."""
        once = self._scenes_played
        if t == PLINIAN_STEP:
            self._add_scene("column_street", t, "A column rises over Vesuvius, seen from the street")
        if t == PLINIAN_STEP + BAY_SCENE_DELAY_STEPS:
            self._add_scene("bay_wide", t, "From the bay: the column stands over Vesuvius and the town")
        if moving_count >= CROWD_SCENE_MIN_MOVING and "crowd" not in once:
            once.add("crowd")
            self._add_scene("crowd_aerial", t, f"From above: {moving_count:,} people heading for the gates", world=self.world, field=self._city_leave)
        if fallen and "roof" not in once:
            once.add("roof")
            self._add_scene("roof_cutaway", t, "Under the weight of pumice, the first roofs give way")
        if self.agent.id in hurt:
            self._add_scene("roof_cutaway", t, f"{self.agent.label} is hurt as a roof comes down", focus=True)
        if hazard["active_pdc"]:
            count = len(hazard["active_pdc"])
            if count != self._last_flow_size:
                self._last_flow_size = count
                self._add_scene("flow_arrival", t, "A pyroclastic flow reaches the town")
                if count > len(hazard["active_pdc"]) * 0.99 and "bay_flow" not in once:
                    once.add("bay_flow")
                    self._add_scene("bay_wide", t, "From the bay: a flow pours down toward the town", flow=True)
        self._focus_closeup(t, focus_before)

    def _focus_closeup(self, t, focus_before):
        """Close in on the followed person at the turning points of their own night."""
        agent, once = self.agent, self._scenes_played
        moments = []
        if agent.knows_danger and ("know", agent.id) not in once:
            moments.append(("know", f"{agent.label} learns something is wrong"))
        if agent.status == "road" and ("road", agent.id) not in once:
            moments.append(("road", f"{agent.label} leaves through the {str(agent.gate).capitalize()} gate"))
        if agent.status == "escaped" and ("escaped", agent.id) not in once:
            moments.append(("escaped", f"{agent.label} reaches a road out of the region"))
        if not agent.is_alive and ("dead", agent.id) not in once:
            moments.append(("dead", f"{agent.label} dies: {str(agent.cause_of_death).replace('_', ' ')}"))
        for key, caption in moments[-1:]:
            once.add((key, agent.id))
            from engine.gui_city import thought_text

            record = self.logs[agent.id][-1] if self.logs.get(agent.id) else None
            self._add_scene("person_closeup", t, caption, focus=True, thought=thought_text(agent, record))
        for key, _ in moments[:-1]:
            once.add((key, agent.id))

    def _cross_boundaries(self, person, crossings):
        pos = tuple(person.pos)
        if person.status == "city" and pos in self._exit_gate:
            gate = self._exit_gate[pos]
            if not self.crowding or crossings[gate] < GATE_CROSSINGS_PER_STEP:
                crossings[gate] += 1
                person.move_to_region(gate)
        elif person.status == "road" and pos in self._region_ends:
            person.status = "escaped"

    def _apply_flows(self, t, hazard):
        """Flows after everyone has moved: anyone in the covered area dies, indoors or out."""
        town = set(map(tuple, hazard["active_pdc"]))
        road = set(map(tuple, hazard["region_active_pdc"]))
        reaches_exit_roads = hazard["flow_runout_km"] > TOWN_KM
        for person in self.people:
            if not person.is_alive or person.status == "escaped":
                continue
            pos = tuple(person.pos)
            if person.status == "city":
                if pos in town or (reaches_exit_roads and pos in self.world.exit_road_tiles):
                    self._kill(person, t, "pyroclastic_flow")
            elif pos in road:
                self._kill(person, t, "pyroclastic_flow")

    def _focus_step_record(self, t, focus_record):
        if focus_record is not None:
            record = focus_record
        else:
            agent = self.agent
            status = "Escaped" if agent.status == "escaped" else "Dead"
            record = dict(
                t=t,
                state=agent.get_state(),
                event="none",
                story=status,
                action="rest",
                action_label=status,
                probs={a: 1.0 / len(contracts.ACTIONS) for a in contracts.ACTIONS},
                reason=f"{status}: no further decisions.",
                quantum=None,
                pos_after=list(agent.pos),
                phase=self.eruption.phases[t],
                status=agent.status,
            )
        record = dict(record, counts=self.counts())
        self.steps.append(record)
        return record

    def _finished(self):
        return not any(p.is_alive and p.status != "escaped" for p in self.people)

    def counts(self):
        tally = Counter("dead" if not p.is_alive else p.status for p in self.people)
        return dict(in_town=tally["city"], on_roads=tally["road"], escaped=tally["escaped"], dead=tally["dead"])

    def outcome_table(self):
        table = {role: dict(total=0, survived=0) for role in ROLE_NAMES}
        for person in self.people:
            table[person.role]["total"] += 1
            table[person.role]["survived"] += person.is_alive
        return table

    def death_breakdown(self):
        """The comparison the sources allow. Survivors have no historical count."""
        causes = Counter(cause for _, cause, _, _ in self.deaths)
        flow = [d for d in self.deaths if d[1] == "pyroclastic_flow"]
        total = len(self.deaths) or 1
        return dict(
            causes=dict(causes),
            share_in_pumice_phase=round(causes["roof_collapse"] / total, 3),
            share_of_flow_deaths_on_roads=round(sum(d[3] for d in flow) / (len(flow) or 1), 3),
        )

    def timeline(self):
        world = copy.deepcopy(self.world.export_dict())
        world["initial_tiles"] = copy.deepcopy(self.initial_world["tiles"])
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, scenario=self.scenario)
        world["weather"] = list(self.event_gen.weather)
        world["eruption"] = self.eruption.export_dict()
        world["region"] = self.region.export_dict()

        def first(predicate):
            return next((r["t"] for r in self.steps if predicate(r)), None)

        evacuation = dict(
            first_sign_step=first(lambda r: r["event"] != "none"),
            first_evacuating_step=first(lambda r: r["action"] == "hide"),
            left_town_step=first(lambda r: r.get("status") in ("road", "escaped")),
            onset_step=self.eruption.onset_step,
            first_city_flow_step=self.eruption.first_city_flow_step,
        )
        focus = self.agent
        return dict(
            world=world,
            steps=self.steps,
            evacuation=evacuation,
            outcome="survived" if focus.is_alive else "died",
            cause=focus.cause_of_death,
            focus=dict(id=focus.id, role=focus.role, label=focus.label, status=focus.status),
            crowd=dict(
                counts=self.counts(), by_role=self.outcome_table(), deaths=self.death_breakdown(), event_mapping=self.event_mapping, comparison=COMPARISON
            ),
        )

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
        path.write_text(json.dumps(timeline, separators=(",", ":")), encoding="utf-8")
        return timeline

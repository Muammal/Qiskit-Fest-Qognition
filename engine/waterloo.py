"""Waterloo chlorine leak simulation with the same public shape as PompeiiSimulation and TitanicSimulation.

A hypothetical evacuation at a real site, not a reconstruction: the 30 July 2012 leak's details are unknown.
Everyone runs the same decide_fn, unedited, on the frozen state contract. The gas is precomputed and never
depends on what anyone does. Exposure is reported against EPA planning levels. Nobody is scripted to be hurt or die.
"""

import copy
import json
import random
from collections import Counter
from pathlib import Path

import contracts
from engine.events import EventGenerator
from engine.chlorine import (
    DEFAULT_LEAK_SITE,
    HORIZON,
    LEAK_MINUTES,
    LEAK_START_STEP,
    SOURCE_PPM,
    START_HOUR,
    STEP_SECONDS,
    AEGL_MEANING,
    ChlorineModel,
    exposure_level,
)
from engine.patrons import (
    ALARM_DELAY_STEPS,
    ALARM_HEAR_CHANCE,
    CROWD_CHANCE,
    CROWD_NOTICE_COUNT,
    DECISION_SECONDS,
    DEFAULT_POPULATION,
    ROLE_NAMES,
    STAFF_ROLES,
    WORD_CHANCE,
    WORD_RADIUS_TILES,
    build_patrons,
    smell_chance,
)
from engine.site import SiteWorld

try:
    from mind.quantum_mind import classical_mixture_decide
except ImportError:
    classical_mixture_decide = None

STORY_TEXT = {
    "none": "Nothing new",
    "smell": "A sharp smell of chlorine",
    "word_of_mouth": "Someone nearby says there is a leak",
    "crowd_moving": "People are hurrying past",
    "alarm": "The alarm is sounding",
}
STORY_SALIENCE = ("alarm", "smell", "word_of_mouth", "crowd_moving", "none")  # most salient first; assumption
# How the site's events reach the mind under its existing names. Nothing in the mind changes.
EVENT_MAPPINGS = {
    "A": dict(smell="gas_plume", word_of_mouth="gas_plume", crowd_moving="gas_plume", alarm="gas_plume"),  # gas_plume alone
    "B": dict(smell="gas_plume", word_of_mouth="gas_plume", crowd_moving="gas_plume", alarm="eruption"),  # alarm read as certain danger
    "C": dict(smell="tremor", word_of_mouth="tremor", crowd_moving="tremor", alarm="gas_plume"),  # a milder reading
}
# The user chose A on meaning after seeing all three, and all three must be reported: it also gives the largest quantum gap.
DEFAULT_MAPPING = "A"
FOCUS_ROLE_CYCLE = ("child", "adult", "lifeguard", "desk")
AERIAL_SCENE_SHARE = 0.15  # display only: when the aerial shot plays, as a share of everyone
POOL_SCENE_COUNT = 3  # display only: people leaving the water before that shot plays
COMPARISON = dict(
    edmonton_2018=dict(evacuated_about=40, ppm=22, source="https://globalnews.ca/news/4060660/chlorine-leak-forces-evacuation-of-edmonton-rec-centre"),
    caution="Another centre and another leak. The Waterloo head-count, cause and injuries are unknown.",
)


class WaterlooSimulation:
    def __init__(
        self,
        seed=42,
        mind_type="quantum",
        noise_source="stub",
        decide_fn=None,
        scenario="waterloo",
        scripted_events=None,
        population=DEFAULT_POPULATION,
        leak_site=DEFAULT_LEAK_SITE,
        source_ppm=SOURCE_PPM,
        leak_minutes=LEAK_MINUTES,
        alarm=True,
        event_mapping=DEFAULT_MAPPING,
        decision_seconds=DECISION_SECONDS,
    ):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source, self.scenario = noise_source, scenario
        self.scripted_events = dict(scripted_events) if scripted_events else {}
        self.alarm_enabled, self.event_mapping = alarm, event_mapping
        self.event_names = EVENT_MAPPINGS[event_mapping]
        self.decision_steps = max(1, decision_seconds // STEP_SECONDS)
        self.horizon = HORIZON
        self.world = SiteWorld(seed=seed)
        self.initial_world = copy.deepcopy(self.world.export_dict())
        self.chlorine = ChlorineModel(seed, self.world, leak_site=leak_site, source_ppm=source_ppm, leak_minutes=leak_minutes)
        self.volcano = self.chlorine  # GUI and exports read hazards through this shared attribute name
        self.event_gen = EventGenerator(seed, horizon=HORIZON)
        self.event_gen.weather = ["calm"] * HORIZON  # the day's rain was 0 in the modelled weather
        self.event_gen.world_events = list(self.chlorine.world_events)
        self.people = build_patrons(self.world, seed, population, decision_seconds)
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
        self.rng = random.Random(seed + 2012)
        self.random_state = random.Random(seed).getstate()
        self.moving_tiles = Counter()
        self.alarm_step = None
        self.first_knew_step = None
        self._memo, self._memo_fn = {}, None
        self.mind_calls = 0
        self._exit_name = {tile: name for name, tile in self.world.exits.items()}
        self._fields = dict(
            leave=self.world.next_step_field(self.world.exits.values()), indoors=self.world.next_step_field(sorted(self.world.areas["indoors"]))
        )
        self._scenes_played = set()

    def _default_focus(self):
        role = FOCUS_ROLE_CYCLE[self.seed % len(FOCUS_ROLE_CYCLE)]
        options = [p for p in self.people if p.role == role]
        return options[self.seed % len(options)]

    def set_focus(self, agent):
        self.agent = agent
        self.watch(agent)

    def watch(self, agent):
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

    def _is_indoors(self, person):
        return tuple(person.pos) in self.world.areas["indoors"]

    def _nearby(self, counter, pos):
        x, y = pos
        return sum(
            counter.get((x + dx, y + dy), 0)
            for dx in range(-WORD_RADIUS_TILES, WORD_RADIUS_TILES + 1)
            for dy in range(-WORD_RADIUS_TILES, WORD_RADIUS_TILES + 1)
        )

    def _perceive(self, person, t, knowing):
        """The most salient thing this person noticed in the last 10 s. Never depends on role."""
        if t in self.scripted_events:
            return self.scripted_events[t]
        rng = self.rng
        pos = tuple(person.pos)
        noticed = "none"
        if self.alarm_step is not None and t >= self.alarm_step:
            where = "indoors" if self._is_indoors(person) else "outdoors"
            if rng.random() < ALARM_HEAR_CHANCE[where]:
                return "alarm"
        if rng.random() < smell_chance(self.chlorine.ppm_at(t, pos)):
            return "smell"
        if not person.knows_danger and self._nearby(knowing, pos) and rng.random() < WORD_CHANCE:
            return "word_of_mouth"
        if self.moving_tiles and self._nearby(self.moving_tiles, pos) >= CROWD_NOTICE_COUNT and rng.random() < CROWD_CHANCE:
            noticed = "crowd_moving"
        return noticed

    def step(self):
        t = self.t
        if t >= self.horizon or self._finished():
            return None
        self.scenes = []
        knowing = Counter(tuple(p.pos) for p in self.people if p.status == "site" and p.knows_danger)
        moving = Counter()
        focus_record = None
        external_state = random.getstate()
        random.setstate(self.random_state)
        try:
            for person in self.people:
                if person.status != "site":
                    person.exposure.append(0.0)
                    continue
                record = self._step_person(person, t, knowing, moving)
                if person is self.agent:
                    focus_record = record
            self.random_state = random.getstate()
        finally:
            random.setstate(external_state)
        self.moving_tiles = moving
        self._update_alarm(t)
        self._emit_scenes(t, sum(moving.values()))
        self.t += 1
        return self._focus_step_record(t, focus_record)

    def _add_scene(self, kind, t, caption, focus=False, **extra):
        self.scenes.append(dict(kind=kind, t=t, caption=caption, focus=focus, role=self.agent.role, **extra))

    def _emit_scenes(self, t, moving_count):
        """Requests for the display only. Nothing here feeds back into the simulation, and no random numbers are drawn."""
        once = self._scenes_played
        if t == LEAK_START_STEP:
            self._add_scene("leak_start", t, f"Chlorine starts to leak at {self.chlorine.source_ppm:g} ppm at the assumed spot")
        if self.alarm_step == t + ALARM_DELAY_STEPS:
            self._add_scene("alarm_cutaway", t, "A staff member knows. The alarm starts 30 seconds later")
        if self.alarm_step == t:
            self._add_scene("alarm_pool", t, "The alarm sounds across the pool")
        in_pool = [p for p in self.people if p.status == "site" and p.last_action == "hide" and p.knows_danger and tuple(p.pos) in self.world.pool_tiles]
        if len(in_pool) >= POOL_SCENE_COUNT and "pool_exit" not in once:
            once.add("pool_exit")
            self._add_scene("pool_exit", t, f"{len(in_pool)} people in the water start to leave", count=len(in_pool))
        if moving_count >= max(5, len(self.people) * AERIAL_SCENE_SHARE) and "aerial" not in once:
            once.add("aerial")
            people = [(list(p.pos), p.role, p.last_action == "hide") for p in self.people if p.status == "site"]
            self._add_scene(
                "site_aerial", t, f"From above: {moving_count} people heading off the site", world=self.world, field=self._fields["leave"], people=people
            )
        self._focus_closeup(t)

    def _focus_closeup(self, t):
        """Close in on the followed person when they learn of the leak and when they leave."""
        agent, once = self.agent, self._scenes_played
        moment = None
        if agent.knows_danger and ("know", agent.id) not in once:
            once.add(("know", agent.id))
            moment = f"{agent.label} learns something is wrong"
        if agent.status == "out" and ("out", agent.id) not in once:
            once.add(("out", agent.id))
            moment = f"{agent.label} leaves the site"
        if moment:
            from engine.gui_site import thought_text

            record = self.logs[agent.id][-1] if self.logs.get(agent.id) else None
            if record is not None and agent.pending_story != "none":
                record = dict(record, story=STORY_TEXT[agent.pending_story])  # noticed since their last decision
            self._add_scene("person_closeup", t, moment, focus=True, thought=thought_text(agent, record, self.chlorine.ppm_at(t, tuple(agent.pos))))

    def _update_alarm(self, t):
        if self.first_knew_step is None and any(p.knows_danger for p in self.people):
            self.first_knew_step = t
        if self.alarm_enabled and self.alarm_step is None and any(p.knows_danger and p.role in STAFF_ROLES for p in self.people):
            self.alarm_step = t + ALARM_DELAY_STEPS

    def _step_person(self, person, t, knowing, moving):
        story = self._perceive(person, t, knowing)
        if story != "none":
            person.knows_danger = True
        if STORY_SALIENCE.index(story) < STORY_SALIENCE.index(person.pending_story):
            person.pending_story = story
        record = None
        if (t + person.decision_offset) % self.decision_steps == 0:
            story_now = person.pending_story
            person.pending_story = "none"
            event = self.event_names.get(story_now, "none")
            person.story_event = story_now
            person.apply_event(event, self._is_indoors(person))
            state = person.get_state()
            decision = self._decide(state)
            person.last_action = decision["action"]
            person.update_stress()
            if person.id in self.watched:
                record = dict(
                    t=t,
                    state=state,
                    event=event,
                    story=STORY_TEXT[story_now],
                    action=decision["action"],
                    action_label=person.action_label(decision["action"]),
                    probs=decision["probs"],
                    reason=decision["reason"],
                    quantum=decision.get("quantum"),
                    pos_after=None,
                    phase=self.chlorine.phases[t],
                    status=person.status,
                )
                self.logs[person.id].append(record)
        before = tuple(person.pos)
        person.execute_action(person.last_action, self.world, self._fields, self.rng)
        if person.last_action == "hide" and tuple(person.pos) != before:
            moving[tuple(person.pos)] += 1
        if record is not None:
            record["pos_after"] = list(person.pos)
        person.exposure.append(self.chlorine.ppm_at(t, tuple(person.pos)))
        pos = tuple(person.pos)
        if person.last_action == "hide" and person.knows_danger and pos in self._exit_name:
            person.status, person.exit_name, person.left_step = "out", self._exit_name[pos], t
        person.step_decay()
        return record

    def _focus_step_record(self, t, focus_record):
        agent = self.agent
        if focus_record is not None:
            record = focus_record
        else:
            last = self.logs[agent.id][-1] if self.logs.get(agent.id) else None
            text = "Off the site" if agent.status == "out" else "Keeps doing the same thing"
            record = dict(
                t=t,
                state=agent.get_state(),
                event="none",
                story=text,
                action=agent.last_action,
                action_label=agent.action_label(agent.last_action),
                probs=last["probs"] if last else {a: 1.0 / len(contracts.ACTIONS) for a in contracts.ACTIONS},
                reason=f"{text}: no new decision this step.",
                quantum=None,
                pos_after=list(agent.pos),
                phase=self.chlorine.phases[t],
                status=agent.status,
            )
        record = dict(record, counts=self.counts())
        self.steps.append(record)
        return record

    def _finished(self):
        return not any(p.status == "site" for p in self.people)

    def counts(self):
        tally = Counter(p.status for p in self.people)
        return dict(on_site=tally["site"], off_site=tally["out"], knows=sum(p.knows_danger for p in self.people))

    def outcome_table(self):
        table = {role: dict(total=0, off_site=0, levels={str(level): 0 for level in AEGL_MEANING}) for role in ROLE_NAMES}
        for person in self.people:
            row = table[person.role]
            row["total"] += 1
            row["off_site"] += person.status == "out"
            row["levels"][str(exposure_level(person.exposure))] += 1
        return table

    def exposure_summary(self):
        """People above each EPA level. These are planning limits, so they don't predict injury."""
        levels = Counter(exposure_level(p.exposure) for p in self.people)
        return {AEGL_MEANING[level]: levels.get(level, 0) for level in AEGL_MEANING}

    def timing(self):
        """Seconds from the leak starting. None means it did not happen in the run."""

        def since(step):
            return None if step is None else (step - LEAK_START_STEP) * STEP_SECONDS

        left = sorted(p.left_step for p in self.people if p.left_step is not None)
        total = len(self.people)
        return dict(
            first_knew=since(self.first_knew_step),
            alarm=since(self.alarm_step),
            first_off_site=since(left[0]) if left else None,
            half_off_site=since(left[total // 2 - 1]) if len(left) >= total // 2 else None,
            all_off_site=since(left[-1]) if len(left) == total else None,
        )

    def timeline(self):
        world = copy.deepcopy(self.world.export_dict())
        world["initial_tiles"] = copy.deepcopy(self.initial_world["tiles"])
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, scenario=self.scenario)
        world["chlorine"] = self.chlorine.export_dict()
        focus = self.agent
        return dict(
            world=world,
            steps=self.steps,
            evacuation=self.timing(),
            start_hour=START_HOUR,
            outcome="survived",
            cause=None,  # nobody is scripted to die; see exposure
            focus=dict(id=focus.id, role=focus.role, label=focus.label, status=focus.status, exposure_level=exposure_level(focus.exposure)),
            crowd=dict(
                counts=self.counts(), by_role=self.outcome_table(), exposure=self.exposure_summary(), event_mapping=self.event_mapping, comparison=COMPARISON
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
        path.write_text(json.dumps(timeline, separators=(",", ":"), default=list), encoding="utf-8")
        return timeline

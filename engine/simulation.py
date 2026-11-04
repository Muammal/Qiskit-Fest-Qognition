"""Single simulation loop shared by CLI, batch exports and GUI.
Supports both Volcano Eruption and Island Wilderness scenarios,
selectable cognitive models, and optional scripted event overrides.
"""
import copy
import json
import random
from pathlib import Path
import contracts
from engine.world import IslandWorld, MAP_SEED
from engine.agent import SurvivalAgent
from engine.events import EventGenerator, VOLCANIC
from engine.volcano import VolcanoModel

try:
    from mind.quantum_mind import classical_mixture_decide
except ImportError:
    classical_mixture_decide = None

DEFAULT_STEPS = 36  # assumption: 72 hours, two hours per step


class SimulationEngine:
    def __init__(self, seed=42, mind_type='quantum', noise_source='stub', decide_fn=None,
                 scenario='volcano', scripted_events=None):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source = noise_source
        self.scenario = scenario
        self.scripted_events = scripted_events

        if self.scenario == 'island':
            self.world = IslandWorld(seed=seed, scenario='island')
            self.initial_world = copy.deepcopy(self.world.export_dict())
            self.agent = SurvivalAgent(self.world.spawn_pos)
            self.event_gen = EventGenerator(seed, scripted_events=scripted_events)
            self.volcano = VolcanoModel(seed, self.world, weather=self.event_gen.weather)
            # In island mode, volcano remains dormant
            self.volcano.erupts = False
            self.volcano.onset_step = None
            self.volcano.first_pdc_step = None
            self.volcano.phases = ['unrest'] * DEFAULT_STEPS
            self.volcano.world_events = ['none'] * DEFAULT_STEPS
            self.volcano.hazard_by_step = [
                {
                    'new_lava': [], 'new_pdc': [], 'new_lahar': [], 'ash': 0.0,
                    'active_pdc': [], 'active_lahar': [], 'surge': [],
                    'wind_deg': 0.0, 'ash_grid': ['0' * 40] * 40
                }
                for _ in range(DEFAULT_STEPS)
            ]
            self.event_gen.prepare(self.volcano)
        else:
            self.world = IslandWorld(seed=MAP_SEED, scenario='volcano')
            self.initial_world = copy.deepcopy(self.world.export_dict())
            self.agent = SurvivalAgent(self.world.spawn_pos)
            self.event_gen = EventGenerator(seed, scripted_events=scripted_events)
            self.volcano = VolcanoModel(seed, self.world, weather=self.event_gen.weather)
            self.event_gen.prepare(self.volcano)

        if decide_fn:
            self.decide_fn = decide_fn
        elif self.mind_type == 'quantum':
            self.decide_fn = contracts.quantum_decide
        elif self.mind_type == 'classical_mixture' and classical_mixture_decide is not None:
            self.decide_fn = classical_mixture_decide
        else:
            self.decide_fn = contracts.classical_decide
        self.steps = []
        self.previous_action, self.previous_moved = 'rest', False
        self.random_state = random.Random(seed).getstate()

    def step(self):
        t = len(self.steps)
        if not self.agent.is_alive or t >= DEFAULT_STEPS:
            return None
        world, agent = self.world, self.agent
        hazard = self.volcano.hazard_by_step[t]
        world.lava.update(map(tuple, hazard['new_lava']))
        world.pdc.update(map(tuple, hazard['new_pdc']))
        world.lahar.update(map(tuple, hazard['new_lahar']))
        world.ash = hazard['ash']
        world.ash_grid = hazard.get('ash_grid')
        world.active_pdc = set(map(tuple, hazard.get('active_pdc', [])))
        world.active_lahar = set(map(tuple, hazard.get('active_lahar', [])))
        world.surge = set(map(tuple, hazard.get('surge', [])))
        event = self.event_gen.step_event(agent.day, agent.hour, agent.pos,
                    world.is_in_shelter(*agent.pos), agent.injured,
                    action=self.previous_action, world=world, energy=agent.needs['energy'],
                    moved=self.previous_moved, t=t)
        if event in VOLCANIC:
            world.volcanic_sign_seen = True
        agent.apply_event(event, world.is_in_shelter(*agent.pos),
                          forest_cover=world.get_tile(*agent.pos) == 2)
        self._eruption_feelings()
        if tuple(agent.pos) in world.surge:
            self._injure()
        state = agent.get_state()
        # Isolate stub-policy/exploration randomness from other engines and GUI particles.
        external_state = random.getstate()
        random.setstate(self.random_state)
        try:
            decision = self.decide_fn(state)
            contracts.validate_decision(decision)
            before = list(agent.pos)
            # PDCs/lahars already arriving at the occupied tile cannot be outrun.
            arriving = next((cause for tiles, cause in ((world.active_pdc, 'pyroclastic_flow'),
                             (world.active_lahar, 'lahar')) if tuple(agent.pos) in tiles), None)
            if arriving:
                agent.is_alive, agent.cause_of_death = False, arriving
            else:
                agent.execute_action(decision['action'], world)
            self.random_state = random.getstate()
        finally:
            random.setstate(external_state)
        self.previous_action = decision['action']
        self.previous_moved = before != agent.pos
        sheltered = world.is_in_shelter(*agent.pos)
        # assumption: ash reduces outdoor warmth/safety; shelter attenuates by 90%.
        exposure = world.ash_at(*agent.pos) * (.1 if sheltered else 1)
        # assumption: exposed open terrain loses heat in wet weather and darkness.
        if not sheltered:
            cover = .35 if world.get_tile(*agent.pos) == 2 else 1.0  # assumption: canopy reduces exposure 65%, not waterproof shelter
            chill = cover * (.018 * world.ash_at(*agent.pos) + .035 * (self.event_gen.weather[t] != 'calm') + .025 * (agent.hour >= 20 or agent.hour <= 6))
            agent.needs['warmth'] = max(0, agent.needs['warmth'] - chill)
        agent.needs['warmth'] = max(0, agent.needs['warmth'] - .040 * exposure)
        agent.needs['safety'] = max(0, agent.needs['safety'] - .025 * exposure)
        agent.needs['energy'] = max(0, agent.needs['energy'] - .035 * exposure)  # assumption: breathing ash fatigue
        # assumption: absent a temperature model, tropical discomfort is not lethal cold.
        # Ash still reduces comfort and energy; it is not a hypothermia diagnosis.
        agent.needs['warmth'] = max(.05, agent.needs['warmth'])
        agent.step_decay(sheltered, forest_cover=world.get_tile(*agent.pos) == 2)
        self._eruption_feelings()
        self._recover_morale()
        if tuple(agent.pos) in world.surge | world.pdc and tuple(agent.pos) not in world.active_pdc:
            self._injure()
        for tiles, cause in ((world.active_pdc, 'pyroclastic_flow'), (world.active_lahar, 'lahar'), (world.lava, 'lava')):
            if tuple(agent.pos) in tiles:
                agent.is_alive, agent.cause_of_death = False, cause
                break
        record = dict(t=t, state=state, event=event, action=decision['action'],
                      probs=decision['probs'], reason=decision['reason'],
                      quantum=decision.get('quantum'),
                      pos_after=list(agent.pos), phase=self.volcano.phases[t])
        self.steps.append(record)
        return record

    def _injure(self):
        # assumption: nonfatal surge/deposit exposure; not fitted to hospital survival data.
        self.agent.injured = True
        self.agent.injury_cooldown = max(3, self.agent.injury_cooldown)
        self.agent.stress = min(1., self.agent.stress + .15)
        self.agent.needs['energy'] = max(.03, self.agent.needs['energy'] - .06)  # assumption: injury alone leaves a minimal mobility reserve

    def _eruption_feelings(self):
        agent, world = self.agent, self.world
        if any(e in VOLCANIC for e in agent.recent_events):
            zone = world.zones[agent.pos[1]][agent.pos[0]]
            agent.needs['safety'] = min(agent.needs['safety'], (.8, .5, .3)[zone])  # assumption: recent-event caps
            agent.stress = max(agent.stress, (.3, .45, .6)[zone])  # assumption: perceived volcanic threat
            if zone:
                agent.needs['morale'] = max(0., agent.needs['morale'] - .01)  # assumption: unrest morale cost in harm's way

    def _recover_morale(self):
        agent, zone = self.agent, self.world.zones[self.agent.pos[1]][self.agent.pos[0]]
        quiet = agent.recent_events[-1] not in VOLCANIC
        if quiet and zone == 0 and not agent.injured and min(agent.needs['hunger'], agent.needs['thirst']) > .3:
            agent.needs['morale'] = min(1., agent.needs['morale'] + .03)  # assumption: safe, fed and watered

    def timeline(self):
        world = copy.deepcopy(self.world.export_dict())
        world['initial_tiles'] = copy.deepcopy(self.initial_world['tiles'])
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, scenario=self.scenario)
        world['weather'] = list(self.event_gen.weather)
        world['volcano'] = self.volcano.export_dict()
        world['volcano']['world_events'] = list(self.event_gen.world_events)

        def first(predicate):
            return next((r['t'] for r in self.steps if predicate(r)), None)

        evacuation = dict(
            first_sign_step=first(lambda r: r['event'] in VOLCANIC),
            left_danger_step=first(lambda r: self.world.zones[r['pos_after'][1]][r['pos_after'][0]] != 2),
            reached_safe_step=first(lambda r: self.world.zones[r['pos_after'][1]][r['pos_after'][0]] == 0),
            reached_assembly_step=first(lambda r: tuple(r['pos_after']) in self.world.assembly_points),
            onset_step=self.volcano.onset_step,
            first_pdc_step=self.volcano.first_pdc_step,
        )
        sign, onset = evacuation['first_sign_step'], evacuation['onset_step']
        safe, flow = evacuation['reached_safe_step'], evacuation['first_pdc_step']
        evacuation['warning_lead_hours'] = (onset - sign) * 2 if onset is not None and sign is not None else None
        evacuation['margin_hours'] = (flow - safe) * 2 if flow is not None and safe is not None else None
        return dict(world=world, steps=self.steps, evacuation=evacuation, outcome='survived' if self.agent.is_alive else 'died',
                    cause=self.agent.cause_of_death)

    def run(self, max_steps=DEFAULT_STEPS, step_callback=None):
        while len(self.steps) < min(max_steps, DEFAULT_STEPS):
            record = self.step()
            if record is None:
                break
            if step_callback:
                step_callback(record, self)
        return self.timeline()

    def run_and_save(self, output_path, max_steps=DEFAULT_STEPS):
        timeline = self.run(max_steps)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(timeline, separators=(',', ':')), encoding='utf-8')
        return timeline

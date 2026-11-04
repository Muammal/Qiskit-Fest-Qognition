"""Single simulation loop shared by CLI, batch exports and GUI.
Supports both Volcano Eruption and Island Wilderness scenarios.
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

DEFAULT_STEPS = 36  # assumption: 72 hours, two hours per step


class SimulationEngine:
    def __init__(self, seed=42, mind_type='quantum', noise_source='stub', decide_fn=None, scenario='volcano'):
        self.seed, self.mind_type = seed, mind_type.lower()
        self.noise_source = noise_source
        self.scenario = scenario

        if self.scenario == 'island':
            self.world = IslandWorld(seed=seed, scenario='island')
            self.initial_world = copy.deepcopy(self.world.export_dict())
            self.agent = SurvivalAgent(self.world.spawn_pos)
            self.event_gen = EventGenerator(seed)
            self.volcano = VolcanoModel(seed, self.world, weather=self.event_gen.weather)
            # In island mode, volcano remains dormant
            self.volcano.erupts = False
            self.volcano.onset_step = None
            self.volcano.first_pdc_step = None
            self.volcano.phases = ['unrest'] * DEFAULT_STEPS
            self.volcano.world_events = ['none'] * DEFAULT_STEPS
            self.volcano.hazard_by_step = [
                {'new_lava': [], 'new_pdc': [], 'new_lahar': [], 'ash': 0.0}
                for _ in range(DEFAULT_STEPS)
            ]
            self.event_gen.prepare(self.volcano)
        else:
            self.world = IslandWorld(seed=MAP_SEED, scenario='volcano')
            self.initial_world = copy.deepcopy(self.world.export_dict())
            self.agent = SurvivalAgent(self.world.spawn_pos)
            self.event_gen = EventGenerator(seed)
            self.volcano = VolcanoModel(seed, self.world, weather=self.event_gen.weather)
            self.event_gen.prepare(self.volcano)

        self.decide_fn = decide_fn or (contracts.quantum_decide if self.mind_type == 'quantum' else contracts.classical_decide)
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
        event = self.event_gen.step_event(agent.day, agent.hour, agent.pos,
                    world.is_in_shelter(*agent.pos), agent.injured,
                    action=self.previous_action, world=world, energy=agent.needs['energy'],
                    moved=self.previous_moved, t=t)
        if event in VOLCANIC:
            world.volcanic_sign_seen = True
        agent.apply_event(event, world.is_in_shelter(*agent.pos),
                          forest_cover=world.get_tile(*agent.pos) == 2)
        state = agent.get_state()
        # Isolate stub-policy/exploration randomness from other engines and GUI particles.
        external_state = random.getstate()
        random.setstate(self.random_state)
        try:
            decision = self.decide_fn(state)
            contracts.validate_decision(decision)
            before = list(agent.pos)
            # PDCs/lahars already arriving at the occupied tile cannot be outrun.
            arriving = next((cause for tiles, cause in ((world.pdc, 'pyroclastic_flow'),
                             (world.lahar, 'lahar')) if tuple(agent.pos) in tiles), None)
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
        exposure = world.ash * (.1 if sheltered else 1)
        # assumption: exposed open terrain loses heat in wet weather and darkness.
        if not sheltered:
            cover = .35 if world.get_tile(*agent.pos) == 2 else 1.0  # assumption: canopy reduces exposure 65%, not waterproof shelter
            chill = cover * (.018 * world.ash + .035 * (self.event_gen.weather[t] != 'calm') + .025 * (agent.hour >= 20 or agent.hour <= 6))
            agent.needs['warmth'] = max(0, agent.needs['warmth'] - chill)
        agent.needs['warmth'] = max(0, agent.needs['warmth'] - .040 * exposure)
        agent.needs['safety'] = max(0, agent.needs['safety'] - .025 * exposure)
        agent.step_decay(sheltered, forest_cover=world.get_tile(*agent.pos) == 2)
        # Flows persist as lethal deposits in this simplified scenario.
        for tiles, cause in ((world.pdc, 'pyroclastic_flow'), (world.lahar, 'lahar'), (world.lava, 'lava')):
            if tuple(agent.pos) in tiles:
                agent.is_alive, agent.cause_of_death = False, cause
                break
        record = dict(t=t, state=state, event=event, action=decision['action'],
                      probs=decision['probs'], reason=decision['reason'],
                      pos_after=list(agent.pos), phase=self.volcano.phases[t])
        self.steps.append(record)
        return record

    def timeline(self):
        world = copy.deepcopy(self.world.export_dict())
        world['initial_tiles'] = copy.deepcopy(self.initial_world['tiles'])
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, scenario=self.scenario)
        world['volcano'] = self.volcano.export_dict()
        world['volcano']['world_events'] = list(self.event_gen.world_events)
        return dict(world=world, steps=self.steps, outcome='survived' if self.agent.is_alive else 'died',
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
        path.write_text(json.dumps(timeline, indent=2), encoding='utf-8')
        return timeline

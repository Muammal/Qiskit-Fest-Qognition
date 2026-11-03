"""Seeded hidden unrest model, independent of decisions.

All numerical parameters below are assumptions unless a source is cited.
They define a compressed scenario, not a forecasting or civil protection tool.
"""
import random
import math

HORIZON = 36  # assumption: 72 hours in two-hour steps
ERUPTION_PROBABILITY = 2 / 3  # Phillipson & Gottsmann abstract, supplied search summary
ONSET_RANGE = (4, 19)  # assumption: final escalation compressed into the run
PDC_DELAYS = (0, 0, 0, 1, 3, 8, 15)  # assumption; 15 steps anchors Cole's ~30 h case
SIGN_BASE = .12  # assumption: shared early unrest sign probability
SIGN_RISE = .75  # assumption: rising sign frequency; USGS volcano prediction FAQ
PDC_RUNOUT_FRACTION = (.6, 1.0)  # assumption: fraction of each drainage reached
PDC_WIDTH_RANGE = (1.5, 2.5)  # assumption: corridor radius in tiles
PDC_GEOMETRY_SEED_OFFSET = 2027  # assumption: independent geometry random stream
LAVA_RATE = 1  # assumption: 250 m/2 h (~0.035 m/s), USGS <0.15 m/s anchor


class VolcanoModel:
    def __init__(self, seed, world, horizon=HORIZON, weather=None):
        if weather is None:
            from engine.events import EventGenerator
            weather = EventGenerator(seed, horizon).weather
        rng = random.Random(seed)
        self.erupts = rng.random() < ERUPTION_PROBABILITY
        transition = rng.randint(*ONSET_RANGE)
        self.onset_step = transition if self.erupts else None
        self.first_pdc_step = min(horizon-1, transition+rng.choice(PDC_DELAYS)) if self.erupts else None
        self.phases, self.world_events, self.hazard_by_step = [], [], []
        self.vent = world.vent
        lava, pdc, lahar = set(), set(), set()
        # assumption: seeded drainage selection and pulses over roughly 48 hours.
        valleys = rng.sample(world.valleys, rng.randint(1, len(world.valleys)))
        # assumption: the perennial stream is the dominant drainage catchment.
        if rng.random() < .85 and world.valleys[0] not in valleys:
            valleys[0] = world.valleys[0]
        geometry_rng = random.Random(seed + PDC_GEOMETRY_SEED_OFFSET)
        # assumption: drainage-specific runout and width proxy varying flow volumes.
        corridors = [(valley, geometry_rng.randint(math.ceil(len(valley)*PDC_RUNOUT_FRACTION[0]),
                                                   len(valley)),
                      geometry_rng.uniform(*PDC_WIDTH_RANGE)) for valley in valleys]
        pulses = set(range(self.first_pdc_step, horizon, rng.randint(3, 5))) if self.erupts else set()
        explosive = pulses | ({transition} if self.erupts else set())
        ash_steps = set(rng.sample([t for t in range(transition, horizon) if t not in explosive],
                                  min((horizon-transition)//2, len([t for t in range(transition,horizon) if t not in explosive])))) if self.erupts else set()
        ash = 0.0
        for t in range(horizon):
            phase = ('erupting' if t >= transition else ('escalating' if t >= transition//2 else 'unrest')) if self.erupts else ('fading' if t >= transition else 'unrest')
            # USGS: early signs do not distinguish an eruption from a false alarm.
            probability = SIGN_BASE if t < transition//2 else (SIGN_BASE + SIGN_RISE * min(1, t/transition))
            if phase == 'fading':
                probability = SIGN_BASE * max(0, 1-(t-transition)/6)  # assumption: six-step fade
            event = rng.choice(('tremor', 'gas_plume')) if rng.random() < probability else 'none'
            new_lava, new_pdc, new_lahar = set(), set(), set()
            if phase == 'erupting':
                event = 'eruption' if t in explosive else ('ash_fall' if t in ash_steps else 'none')
                ash = min(1.0, ash + .16)  # assumption: retained deposition, independent of sign selection
                if not lava:
                    new_lava.add(world.vent)
                else:
                    # assumption: two new adjacent downhill cells per step; branching meanders.
                    growing = set(lava)
                    for _ in range(2):
                        candidates = {q for p in growing for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))
                                      for q in [(p[0]+dx,p[1]+dy)] if world.get_tile(*q) and q not in growing
                                      and math.dist(q,world.vent) >= math.dist(p,world.vent)}
                        if candidates:
                            q = rng.choice(sorted(candidates))
                            new_lava.add(q)
                            growing.add(q)
                if t in pulses:
                    # Geology.com: each fast pulse activates within this two-hour interval.
                    reach = 5 + 2*(t-self.first_pdc_step)  # assumption: later pulses travel farther
                    footprint = { (x,y) for valley, limit, radius in corridors for q in valley[:min(reach, limit)]
                                  for x in range(q[0]-math.ceil(radius),q[0]+math.ceil(radius)+1)
                                  for y in range(q[1]-math.ceil(radius),q[1]+math.ceil(radius)+1)
                                  if world.get_tile(x,y) and math.dist((x,y),q)<=radius and world.zones[y][x]!=0 }
                    new_pdc = footprint - pdc
                # FEMA/UW: rainfall remobilises deposited ash into valley lahars.
                if weather and weather[t] != 'calm' and ash >= .3:  # assumption: deposition threshold
                    new_lahar = world.lahar_footprint - lahar
            lava |= new_lava
            pdc |= new_pdc
            lahar |= new_lahar
            self.phases.append(phase)
            self.world_events.append(event)
            self.hazard_by_step.append(dict(new_lava=sorted(new_lava), new_pdc=sorted(new_pdc),
                                            new_lahar=sorted(new_lahar), ash=ash))

    def export_dict(self):
        return dict(vent=list(self.vent), erupts=self.erupts, onset_step=self.onset_step,
                    first_pdc_step=self.first_pdc_step, phases=self.phases,
                    world_events=self.world_events, hazard_by_step=[
                        {**h, **{key: [list(p) for p in h[key]]
                                 for key in ('new_lava','new_pdc','new_lahar')}}
                        for h in self.hazard_by_step])

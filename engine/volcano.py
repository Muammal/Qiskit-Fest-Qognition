"""Seeded hidden unrest model, independent of decisions.

All numerical parameters below are assumptions unless a source is cited.
They define a compressed scenario, not a forecasting or civil protection tool.
"""
import random
import math
import copy
from collections import OrderedDict

HORIZON = 36  # assumption: 72 hours in two-hour steps
ERUPTION_PROBABILITY = 2 / 3  # Phillipson & Gottsmann abstract, supplied search summary
ONSET_RANGE = (4, 19)  # assumption: final escalation compressed into the run
PDC_DELAYS = (0, 0, 1, 2, 3, 5, 8, 15)  # assumption: not fitted; no onset-to-flow statistic found
SIGN_BASE = .12  # assumption: shared early unrest sign probability
SIGN_RISE = .75  # assumption: rising sign frequency; USGS volcano prediction FAQ
PDC_RUNOUT_FRACTION = (.6, 1.0)  # assumption: fraction of each drainage reached
PDC_WIDTH_RANGE = (1.5, 2.5)  # assumption: corridor radius in tiles
PDC_APRON_RADIUS = 5.0  # assumption: proximal collapse apron, 1.25 km from vent
PDC_GEOMETRY_SEED_OFFSET = 2027  # assumption: independent geometry random stream
LAVA_RATE = 2  # assumption: at most 500 m/2 h; supplied USGS <0.15 m/s anchor
WARNING_SWEEP_ONSET_RANGE = (16, 21)  # assumption: onset for lead sweeps, late enough for a 30 h lead


_FORECAST_CACHE = OrderedDict()  # assumption: retain at most 128 immutable forecasts


class VolcanoModel:
    def __init__(self, seed, world, horizon=HORIZON, weather=None, warning_lead_override_hours=None):
        if weather is None:
            from engine.events import EventGenerator
            weather = EventGenerator(seed, horizon).weather
        key = (seed, horizon, warning_lead_override_hours, tuple(weather), world.vent, world.width, world.height,
               tuple(map(tuple,world.elevation)), tuple(map(tuple,world.tiles)),
               tuple(map(tuple,world.valleys)), tuple(map(tuple,world.zones)))
        if key in _FORECAST_CACHE:
            _FORECAST_CACHE.move_to_end(key)
            self.__dict__.update(copy.deepcopy(_FORECAST_CACHE[key]))
            return
        self._generate(seed, world, horizon, weather, warning_lead_override_hours)
        _FORECAST_CACHE[key] = copy.deepcopy(self.__dict__)
        if len(_FORECAST_CACHE)>128:  # assumption: bounded forecast cache
            _FORECAST_CACHE.popitem(last=False)

    def _generate(self, seed, world, horizon, weather, warning_lead_override_hours=None):
        rng = random.Random(seed)
        self.erupts = rng.random() < ERUPTION_PROBABILITY
        transition = rng.randint(*ONSET_RANGE)
        self.onset_step = transition if self.erupts else None
        self.first_pdc_step = min(horizon-1, transition+rng.choice(PDC_DELAYS)) if self.erupts else None
        sign_step = None
        if warning_lead_override_hours is not None:
            # Lead-time sweeps only. Every seed erupts, the first flow comes with the onset, and the
            # first sign comes exactly this long before it. The onset step ignores the lead, so
            # runs that differ only in lead share the same onset and hazards.
            transition = rng.randint(*WARNING_SWEEP_ONSET_RANGE)
            lead_steps = round(warning_lead_override_hours / 2)
            if lead_steps < 0 or lead_steps > transition:
                raise ValueError(f"warning lead of {warning_lead_override_hours} h does not fit before step {transition}")
            self.erupts, self.onset_step, self.first_pdc_step = True, transition, transition
            sign_step = transition - lead_steps
        self.phases, self.world_events, self.hazard_by_step = [], [], []
        self.vent = world.vent
        lava, pdc, lahar = set(), set(), set()
        # assumption: seeded drainage selection and pulses over roughly 48 hours.
        valleys = rng.sample(world.valleys, rng.randint(1, len(world.valleys)))
        # assumption: the perennial valley carries every pulse; other outlets vary.
        if world.valleys[0] not in valleys:
            valleys.append(world.valleys[0])
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
        wind = rng.uniform(0, 360)  # assumption: persistent wind with small per-step drift
        ash_field = [[0.0]*world.width for _ in range(world.height)]
        for t in range(horizon):
            phase = ('erupting' if t >= transition else ('escalating' if t >= transition//2 else 'unrest')) if self.erupts else ('fading' if t >= transition else 'unrest')
            # USGS: early signs do not distinguish an eruption from a false alarm.
            probability = SIGN_BASE if t < transition//2 else (SIGN_BASE + SIGN_RISE * min(1, t/transition))
            if phase == 'fading':
                probability = SIGN_BASE * max(0, 1-(t-transition)/6)  # assumption: six-step fade
            event = rng.choice(('tremor', 'gas_plume')) if rng.random() < probability else 'none'
            if sign_step is not None:
                if t < sign_step:
                    event = 'none'
                elif t == sign_step and event == 'none':
                    event = rng.choice(('tremor', 'gas_plume'))
            new_lava, new_pdc, new_lahar = set(), set(), set()
            active_pdc, active_lahar, surge = set(), set(), set()
            wind = (wind+rng.uniform(-6, 6)) % 360  # assumption: slow wind drift
            if phase == 'erupting':
                event = 'eruption' if t in explosive else ('ash_fall' if t in ash_steps else 'none')
                # USGS summary: downwind deposition decreases with distance.
                wx, wy = math.sin(math.radians(wind)), -math.cos(math.radians(wind))
                for y in range(world.height):
                    for x in range(world.width):
                        dx, dy = x-world.vent[0], y-world.vent[1]
                        distance = math.hypot(dx, dy)
                        along, cross = dx*wx+dy*wy, abs(dx*wy-dy*wx)
                        deposit = .025*math.exp(-distance/4)  # assumption: near-vent background
                        if along >= 0:
                            deposit += .20*math.exp(-distance/14)*math.exp(-.5*(cross/(1.5+.22*along))**2)  # assumption: plume width/rate
                        ash_field[y][x] = min(1., ash_field[y][x]+deposit)
                ash = max(map(max, ash_field))
                if not lava:
                    new_lava.add(world.vent)
                else:
                    # assumption: two new adjacent downhill cells per step; branching meanders.
                    growing = set(lava)
                    for _ in range(LAVA_RATE):
                        candidates = {q for p in lava for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))
                                      for q in [(p[0]+dx,p[1]+dy)] if world.get_tile(*q) and q not in growing
                                      and world.elevation[q[1]][q[0]] <= world.elevation[p[1]][p[0]]}
                        if candidates:
                            q = min(candidates, key=lambda p: world.elevation[p[1]][p[0]]+rng.uniform(0, 35))  # assumption: branching/ponding preference
                            new_lava.add(q)
                            growing.add(q)
                if t in pulses:
                    # Geology.com: each fast pulse activates within this two-hour interval.
                    # Fast flows reach their seeded runout within one two-hour bin.
                    footprint = { (x,y) for valley, limit, radius in corridors for q in valley[:limit]
                                  for x in range(q[0]-math.ceil(radius),q[0]+math.ceil(radius)+1)
                                  for y in range(q[1]-math.ceil(radius),q[1]+math.ceil(radius)+1)
                                  if world.get_tile(x,y) and math.dist((x,y),q)<=radius and world.zones[y][x]!=0 }
                    # A collapsing column spreads across the upper cone before valley confinement.
                    footprint.update((x,y) for y in range(world.height) for x in range(world.width)
                                     if world.get_tile(x,y) and world.zones[y][x] != 0
                                     and math.dist((x,y), world.vent) <= PDC_APRON_RADIUS)
                    active_pdc = footprint
                    new_pdc = footprint - pdc
                    surge = {q for p in footprint for q in world.neighbors(p)
                             if world.get_tile(*q) and q not in footprint and world.zones[q[1]][q[0]] != 0}
                # FEMA/UW: rainfall remobilises deposited ash into valley lahars.
                if weather and weather[t] != 'calm':
                    for valley in world.valleys:
                        catchment = sum(ash_field[y][x] for x,y in valley)/len(valley)
                        if catchment >= .12:  # assumption: wet ash catchment threshold
                            active_lahar.update(valley[1:])
                    new_lahar = active_lahar-lahar
            lava |= new_lava
            pdc |= new_pdc
            lahar |= new_lahar
            self.phases.append(phase)
            self.world_events.append(event)
            self.hazard_by_step.append(dict(new_lava=sorted(new_lava), new_pdc=sorted(new_pdc),
                                            new_lahar=sorted(new_lahar), ash=ash,
                                            active_pdc=sorted(active_pdc), surge=sorted(surge),
                                            active_lahar=sorted(active_lahar), wind_deg=round(wind, 2),
                                            ash_grid=[''.join(str(round(v*9)) for v in row) for row in ash_field]))

    def export_dict(self):
        return dict(vent=list(self.vent), erupts=self.erupts, onset_step=self.onset_step,
                    first_pdc_step=self.first_pdc_step, phases=self.phases,
                    world_events=self.world_events, hazard_by_step=[
                        {**h, **{key: [list(p) for p in h[key]]
                                 for key in ('new_lava','new_pdc','new_lahar')}}
                        for h in self.hazard_by_step])

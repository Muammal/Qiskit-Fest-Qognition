"""Plays a precomputed pack for any mind. Mirrors engine.simulation.SimulationEngine for GUI and JSON."""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

import contracts
from stranded_physics.core.api import InterfaceError, ScenarioPack, XY
from stranded_physics.domains.agent.physiology import advance, cause_of_death, needs, pandolf_watts, setting
from stranded_physics.domains.exposure.model import ash_energy_cost_per_hour, flow_death_probability
from stranded_physics.domains.agent.walking import TravelField, travel_field, walk
from stranded_physics.runtime.body import AgentBody, to_state
from stranded_physics.runtime.perception import perceive

SUBSTEP_MINUTES = 5  # Hazard contact is checked at this resolution along a walk.
DRINK_REACH_M = 400.  # assumption: close enough to a stream to drink from it.
FOOD_REACH_M = 400.  # assumption: close enough to gather food.
SHELTER_REACH_M = 400.  # assumption: close enough to count as sheltered.
WOOD_REACH_M = 400.  # assumption: close enough to gather wood.
WOOD_PER_SHELTER = 2  # assumption: carried over from the fictional island.
MOST_WOOD_CARRIED = 4  # assumption: carried over from the fictional island's food limit.
INJURY_STEPS = 12  # assumption: in two-hour steps, a day before an injured person walks normally again. Resting heals twice as fast.
TWO_HOURS_MINUTES = 120
LUCK_STREAM = 603  # Keeps who survives apart from every other random stream, so a choice of mind changes nothing else.
GALE_M_S = 17.2  # Beaufort force 8, from memory: strong enough for a person to notice and act on.
HURRICANE_M_S = 32.7  # Beaufort force 12, from memory. assumption: an unsheltered person is injured at this wind.
STORM_RAIN_MM_H = 5.  # assumption: T0 threshold; a `convention` value in the frozen event mapping.
PHASE_NAMES = {0: "unrest", 1: "escalating", 2: "erupting", 3: "fading"}
TILE_CODES = {"water": 0, "plains": 1, "forest": 2, "mountain": 3, "shelter": 4}


def _mind(mind_type: str):
    """The team's minds. The control lives with the quantum mind, and is imported only when asked for."""
    if mind_type == "classical_mixture":
        from mind.quantum_mind import classical_mixture_decide
        return classical_mixture_decide
    return contracts.quantum_decide if mind_type == "quantum" else contracts.classical_decide


class PackWorld:
    """World view with what the legacy GUI reads. Tiles and overlays derive from the pack by convention."""

    def __init__(self, pack: ScenarioPack) -> None:
        self.pack, grid = pack, pack.contract_grid
        self.width, self.height = grid.nx, grid.ny
        self.seed = pack.seed
        self.tiles = [[self._tile(row, col) for col in range(grid.nx)] for row in range(grid.ny)]
        self.zones = [[self._zone(row, col) for col in range(grid.nx)] for row in range(grid.ny)]
        self.elevation = [[pack.sample("terrain.elevation", grid.centre(row, col)) for col in range(grid.nx)] for row in range(grid.ny)]
        self.spawn_pos = self.to_tile(pack.sites["spawn"][0])
        self.vent = tuple(self.to_tile(pack.sites["vent"][0])) if pack.sites.get("vent") else None
        self.assembly_points = [tuple(self.to_tile(p)) for p in pack.sites["assembly"]]
        self.freshwater_tiles = [tuple(self.to_tile(p)) for p in pack.sites["water"]]
        self.clean_springs = self.freshwater_tiles[1:]
        self.food_tiles = [tuple(self.to_tile(p)) for p in pack.sites.get("food", ())]
        self.route_from_spawn: list[list[int]] = []  # No straight line to draw: real routes follow the terrain.
        self.scale_m_per_tile = grid.dx_m
        self.shelter_tiles: list[tuple[int, int]] = []
        self.lava, self.pdc, self.lahar = set(), set(), set()
        self.ash = 0.

    def _tile(self, row: int, col: int) -> int:
        xy = self.pack.contract_grid.centre(row, col)
        if not self.pack.sample("terrain.land_mask", xy):
            return TILE_CODES["water"]
        return TILE_CODES["mountain"] if self.pack.sample("terrain.elevation", xy) > 750 else TILE_CODES["forest"]

    def _zone(self, row: int, col: int) -> int:
        return int(self.pack.sample("terrain.zone", self.pack.contract_grid.centre(row, col)))

    def to_tile(self, xy: XY) -> list[int]:
        grid = self.pack.contract_grid
        located = grid.locate(xy)
        if located is None:
            raise InterfaceError(f"site {xy} is outside the tile grid")
        return [located[1], located[0]]

    def get_tile(self, x: int, y: int) -> int:
        return self.tiles[y][x] if 0 <= x < self.width and 0 <= y < self.height else 0

    def is_in_shelter(self, x: int, y: int) -> bool:
        return (x, y) in self.assembly_points

    def ash_at(self, x: int, y: int) -> float:
        return self.ash

    def export_dict(self) -> dict:
        grid = self.pack.contract_grid
        route = [list(self.spawn_pos), list(self.assembly_points[0])]
        return {"width": self.width, "height": self.height, "tiles": self.tiles, "map_seed": self.pack.scenario,
                "scale_m_per_tile": grid.dx_m, "elevation": [[round(v) for v in row] for row in self.elevation],
                "evacuation_map": {"zones": self.zones, "assembly_points": [list(p) for p in self.assembly_points],
                                   "routes_from_spawn": [route], "route_from_spawn": route,
                                   "clean_springs": [list(p) for p in self.clean_springs]}}


class Shared:
    """What never differs between people on one pack: the map, walking routes and hazard frames. Holds nothing about any person."""

    def __init__(self, pack: ScenarioPack) -> None:
        self.world = PackWorld(pack)
        self.fields: dict[XY, TravelField] = {}
        self.hazards: list[dict] | None = None


class PackSimulation:
    """Same surface as SimulationEngine: step(), run(), timeline(), world, agent, steps."""

    def __init__(self, pack: ScenarioPack, mind_type: str = "quantum", noise_source: str = "stub", decide_fn=None, allow_out_of_domain: bool = False, person: int = 0, shared: "Shared | None" = None) -> None:
        breaches = [k for k, v in pack.verdicts.items() if v == "OUT_OF_DOMAIN"]
        if breaches and not allow_out_of_domain:
            raise InterfaceError(f"pack is outside its models' valid range: {breaches}")
        self.pack, self.mind_type, self.noise_source = pack, mind_type.lower(), noise_source
        self.seed = pack.seed
        self.decide_fn = decide_fn or _mind(self.mind_type)
        self.shared = Shared(pack) if shared is None else shared
        self.world = self.shared.world
        self.agent = AgentBody(tuple(pack.sites["spawn"][person]), self.world.to_tile(pack.sites["spawn"][person]), pack.t0_local_hour)
        self.recent_events = ["none", "none"]
        self._fields = self.shared.fields
        self._walked = (0., 0., 0.)  # Seconds, metres and metres climbed in the current step.
        self.steps: list[dict] = []
        self.warned = False
        self.built: list[XY] = []  # Shelters this person has built. Only they use them.
        self.injury_steps_left = 0
        self.step_minutes = round(pack.time.dt_s / 60.)
        self.luck = np.random.default_rng([pack.seed, person, LUCK_STREAM])
        self.flow_met_on_step: int | None = None  # A flow is one event in a step, however many substeps it covers.
        self.roof_failed_share = 0.  # The roof failure share at this person's shelter when last checked.
        self.roof_lost = False
        self.helped = False  # Someone able-bodied is close enough to help. Set by runtime/group.py. It changes the walking only, and never reaches the mind.

    def _event(self, t_s: float) -> str:
        """One event per step, by the frozen priority, from what the agent can notice."""
        now = perceive(self.pack, self.agent.xy_m, t_s)
        previous = perceive(self.pack, self.agent.xy_m, max(0., t_s - self.pack.time.dt_s))
        if now.explosion_heard or now.flow_visible:
            return "eruption"
        if now.wind_m_s >= GALE_M_S:
            return "storm"
        if now.ash_kg_m2 > previous.ash_kg_m2:
            return "ash_fall"
        if now.felt_tremor:
            return "tremor"
        if now.gas_smell:
            return "gas_plume"
        if now.rain_mm_h >= STORM_RAIN_MM_H:
            return "storm"
        return "none"

    def _field(self, goal: XY) -> TravelField:
        """Best walking times to one site, computed once. Terrain never changes, so this reads no hazard."""
        if goal not in self._fields:
            grid = self.pack.grid
            self._fields[goal] = travel_field(self.pack.frame("terrain.elevation"), self.pack.frame("terrain.land_mask") > 0, grid.locate(goal), grid.dx_m)
        return self._fields[goal]

    def _nearest_site(self, sites: list[XY]) -> XY | None:
        cell = self.pack.grid.locate(self.agent.xy_m)
        if cell is None:
            return None
        goal = min(sites, key=lambda p: self._field(p).seconds[cell])
        return goal if np.isfinite(self._field(goal).seconds[cell]) else None

    def _walk_goal(self, action: str) -> XY | None:
        sites = self.pack.sites
        if action == "hide" and self.warned:
            return self._nearest_site(sites["assembly"])
        if action == "drink":
            return self._nearest_site(sites["water"])
        if action == "forage" and (sites.get("food") or sites.get("wood")):
            return self._nearest_site([*sites.get("food", ()), *sites.get("wood", ())])
        return None

    def _advance(self, action: str, t_s: float) -> None:
        """Walk through the step in substeps, checking hazards at each. No solver runs here."""
        goal = self._walk_goal(action)
        grid = self.pack.grid
        spare_s = 0.
        seconds, metres, climbed = 0., 0., 0.
        for minute in range(0, self.step_minutes, SUBSTEP_MINUTES):
            clock = t_s + minute * 60.
            cell = grid.locate(self.agent.xy_m)
            if goal is not None and cell is not None:
                # An injured person covers half the ground. This factor is an assumption, carried over from T0.
                budget = spare_s + SUBSTEP_MINUTES * 60. * (.5 if self.agent.injured and not self.helped else 1.)
                reached, spare_s = walk(self._field(goal), cell, budget, (grid.ny, grid.nx))
                if reached != cell:
                    start, end = self.agent.xy_m, grid.centre(*reached)
                    rise = self.pack.sample("terrain.elevation", end) - self.pack.sample("terrain.elevation", start)
                    seconds, metres, climbed = seconds + SUBSTEP_MINUTES * 60., metres + math.dist(start, end), climbed + max(0., rise)
                    self.agent.xy_m = end
            if self._killed_by_flow(clock):
                break
            if self.pack.has("lahar.depth") and self.pack.sample("lahar.depth", self.agent.xy_m, clock) > 0:
                self.agent.alive, self.agent.cause = False, "lahar"
                break
            if self.pack.has("lava.footprint") and self.pack.sample("lava.footprint", self.agent.xy_m, clock) > 0:
                self.agent.alive, self.agent.cause = False, "lava"
                break
        self._walked = (seconds, metres, climbed)
        self.agent.tile = self.world.to_tile(self.agent.xy_m)

    def _needs(self, action: str, event: str) -> None:
        """Water, food and fatigue from the balance model. Safety and stress are still labelled assumptions."""
        body = self.agent
        seconds, metres, climbed = self._walked
        speed = metres / seconds if seconds else 0.
        grade = 100. * climbed / metres if metres else 0.
        water = self._walk_goal("drink")
        body.balance = advance(body.balance, self.step_minutes / 60., seconds / 3600., pandolf_watts(speed, grade) if seconds else 0.,
                               drank=bool(action == "drink" and water and math.dist(water, body.xy_m) < DRINK_REACH_M), rested=action == "rest",
                               ate_kcal=setting("meal_energy", "kcal") if self._within("food", FOOD_REACH_M) and action == "forage" else 0.)
        self._use_materials(action)
        self._heal(action)
        self._expose_to_ash()
        if self.pack.has("storm.max_wind") and self.pack.series("storm.max_wind")[len(self.steps)] >= HURRICANE_M_S and not self._sheltered():
            self._injure()
        current = needs(body.balance)
        body.thirst, body.hunger, body.energy = current["thirst"], current["hunger"], current["energy"]
        if event in ("tremor", "gas_plume", "eruption", "ash_fall"):
            self.warned = True
            body.safety = max(0., body.safety - .1)
            body.stress = min(1., body.stress + .08)
        body.minute += self.step_minutes
        body.hour += body.minute // 60
        body.minute %= 60
        if body.hour >= 24:
            body.hour, body.day = body.hour - 24, body.day + 1
        cause = cause_of_death(body.balance)
        if body.alive and cause:
            body.alive, body.cause = False, cause

    def _killed_by_flow(self, clock: float) -> bool:
        """Not everyone caught by a flow dies, and shelter improves the odds. Survivors are injured. T-603's probabilities aren't fitted to casualty data."""
        here = self.agent.xy_m
        if not self.pack.has("pdc.arrival") or self.pack.sample("pdc.arrival", here) > clock or not self.pack.sample("pdc.active", here, clock):
            return False
        step = len(self.steps)
        if self.flow_met_on_step == step:
            return False
        self.flow_met_on_step = step
        if self.luck.random() < flow_death_probability(self._sheltered()):
            self.agent.alive, self.agent.cause = False, "pyroclastic_flow"
            return True
        self._injure()
        return False

    def _expose_to_ash(self) -> None:
        """Fresh ash tires a person, less so indoors. As it builds up on a roof, that roof may fail, which injures them and ends its use as shelter."""
        if not self.pack.has("tephra.deposit_load"):
            return
        t_s = len(self.steps) * self.pack.time.dt_s
        body, load = self.agent, self.pack.sample("tephra.deposit_load", self.agent.xy_m, t_s)
        tiredness = ash_energy_cost_per_hour(load, self._sheltered()) * self.step_minutes / 60. * setting("fatigue_span", "kcal")
        body.balance = replace(body.balance, fatigue_kcal=body.balance.fatigue_kcal + float(tiredness))
        if self.pack.has("exposure.roof_failure") and self._sheltered():
            share = self.pack.sample("exposure.roof_failure", self.agent.xy_m, t_s)
            if share > self.roof_failed_share:
                chance = (share - self.roof_failed_share) / (1. - self.roof_failed_share)
                self.roof_failed_share = share
                if self.luck.random() < chance:
                    self.roof_lost = True
                    self._injure()

    def _use_materials(self, action: str) -> None:
        """Wood is gathered by foraging near it. Two pieces build a shelter where the person stands, and one makes a tool."""
        stock = self.agent.inventory
        if action == "forage" and self._within("wood", WOOD_REACH_M) and stock["wood"] < MOST_WOOD_CARRIED:
            stock["wood"] += 1
        elif action == "build_shelter" and stock["wood"] >= WOOD_PER_SHELTER and not self._sheltered():
            stock["wood"] -= WOOD_PER_SHELTER
            self.built.append(self.agent.xy_m)
        elif action == "craft" and stock["wood"] >= 1:
            stock["wood"] -= 1
            stock["tools"] += 1

    def _injure(self) -> None:
        self.agent.injured, self.injury_steps_left = True, round(INJURY_STEPS * TWO_HOURS_MINUTES / self.step_minutes)

    def _heal(self, action: str) -> None:
        if self.agent.injured:
            self.injury_steps_left -= 2 if action == "rest" else 1
            self.agent.injured = self.injury_steps_left > 0

    def _sheltered(self) -> bool:
        return not self.roof_lost and (self._within("assembly", SHELTER_REACH_M) or any(math.dist(point, self.agent.xy_m) < SHELTER_REACH_M for point in self.built))

    def step(self) -> dict | None:
        t = len(self.steps)
        if not self.agent.alive or t >= self.pack.time.n:
            return None
        t_s = t * self.pack.time.dt_s
        event = self._event(t_s)
        self.recent_events = (self.recent_events + [event])[-3:]
        if event in ("tremor", "gas_plume", "eruption", "ash_fall") or (event == "storm" and self.pack.has("storm.max_wind")):
            self.warned = True
        state = to_state(self.agent, self.recent_events)
        contracts.validate_state(state)
        decision = self.decide_fn(state)
        contracts.validate_decision(decision)
        self._advance(decision["action"], t_s)
        self._needs(decision["action"], event)
        record = {"t": t, "state": state, "event": event, "action": decision["action"], "probs": decision["probs"],
                  "reason": decision["reason"], "pos_after": list(self.agent.tile),
                  "phase": PHASE_NAMES[int(self.pack.series("eruption.phase")[t])] if self.pack.has("eruption.phase") else "none"}
        self.steps.append(record)
        return record

    def run(self, max_steps: int | None = None) -> dict:
        limit = self.pack.time.n if max_steps is None else max_steps
        while len(self.steps) < limit and self.step() is not None:
            pass
        return self.timeline()

    def _within(self, site: str, reach_m: float) -> bool:
        return any(math.dist(point, self.agent.xy_m) < reach_m for point in self.pack.sites.get(site, ()))

    def _volcano_export(self) -> dict:
        if not self.pack.has("eruption.phase"):
            return {"vent": None, "erupts": False, "onset_step": None, "first_pdc_step": None, "phases": ["none"] * self.pack.time.n,
                    "world_events": [r["event"] for r in self.steps], "hazard_by_step": []}
        phase = self.pack.series("eruption.phase")
        erupting = np.flatnonzero(phase == 2)
        arrival = self.pack.frame("pdc.arrival") if self.pack.has("pdc.arrival") else np.array([])
        finite = arrival[np.isfinite(arrival)]
        return {"vent": list(self.world.vent), "erupts": bool(erupting.size),
                "onset_step": int(erupting[0]) if erupting.size else None,
                "first_pdc_step": int(finite.min() // self.pack.time.dt_s) if finite.size else None,
                "phases": [PHASE_NAMES[int(p)] for p in phase],
                "world_events": [r["event"] for r in self.steps],
                "hazard_by_step": self._hazards()}

    def _hazards(self) -> list[dict]:
        if self.shared.hazards is None:
            self.shared.hazards = [self._hazard_at(t) for t in range(self.pack.time.n)]
        return self.shared.hazards

    def _hazard_at(self, step: int) -> dict:
        t_s = step * self.pack.time.dt_s
        grid = self.pack.contract_grid
        flows = [[col, row] for row in range(grid.ny) for col in range(grid.nx)
                 if self.pack.sample("pdc.active", grid.centre(row, col), t_s) > 0] if self.pack.has("pdc.active") else []
        ash = round(float(self.pack.frame("tephra.deposit_load", t_s).max()), 3) if self.pack.has("tephra.deposit_load") else 0.
        return {"new_lava": [], "new_pdc": flows, "active_pdc": flows, "surge": [],
                "new_lahar": [], "active_lahar": [], "ash": ash,
                "ash_grid": ["0" * grid.nx for _ in range(grid.ny)], "wind_deg": 0.0}

    def _weather_labels(self) -> list[str]:
        return ["storm" if r >= STORM_RAIN_MM_H else "rain" if r > 0 else "calm" for r in self.pack.series("atmos.rain_rate")]

    def timeline(self) -> dict:
        volcano = self._volcano_export()
        world = self.world.export_dict()
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, initial_tiles=self.world.tiles,
                     volcano=volcano, pack_hash=self.pack.content_hash, pack_verdicts=dict(self.pack.verdicts),
                     weather=self._weather_labels())
        left = next((r["t"] for r in self.steps if self.world.zones[r["pos_after"][1]][r["pos_after"][0]] != 2), None)
        safe = next((r["t"] for r in self.steps if self.world.zones[r["pos_after"][1]][r["pos_after"][0]] == 0), None)
        pdc = volcano["first_pdc_step"]
        return {"world": world, "steps": self.steps, "outcome": "survived" if self.agent.alive else "died", "cause": self.agent.cause,
                "evacuation": {"left_danger_step": left, "reached_safe_step": safe, "first_pdc_step": pdc,
                               "margin_hours": None if safe is None or pdc is None else 2 * (pdc - safe)}}

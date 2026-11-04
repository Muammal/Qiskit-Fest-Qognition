"""Plays a precomputed pack for any mind. Mirrors engine.simulation.SimulationEngine for GUI and JSON."""
from __future__ import annotations

import math

import numpy as np

import contracts
from stranded_physics.core.api import InterfaceError, ScenarioPack, XY
from stranded_physics.runtime.body import AgentBody, to_state
from stranded_physics.runtime.perception import perceive

STEP_MINUTES = 120
SUBSTEP_MINUTES = 5  # Hazard contact is checked at this resolution along a walk.
WALK_M_PER_S = .5  # assumption: T0 speed. WS6 replaces this with Tobler over real terrain.
STORM_RAIN_MM_H = 5.  # assumption: T0 threshold; a `convention` value in the frozen event mapping.
PHASE_NAMES = {0: "unrest", 1: "escalating", 2: "erupting", 3: "fading"}
TILE_CODES = {"water": 0, "plains": 1, "forest": 2, "mountain": 3, "shelter": 4}


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
        self.vent = tuple(self.to_tile(pack.sites["vent"][0]))
        self.assembly_points = [tuple(self.to_tile(p)) for p in pack.sites["assembly"]]
        self.freshwater_tiles = [tuple(self.to_tile(p)) for p in pack.sites["water"]]
        self.clean_springs = self.freshwater_tiles[1:]
        self.food_tiles: list[tuple[int, int]] = []
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
        return self.get_tile(x, y) == TILE_CODES["shelter"]

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


class PackSimulation:
    """Same surface as SimulationEngine: step(), run(), timeline(), world, agent, steps."""

    def __init__(self, pack: ScenarioPack, mind_type: str = "quantum", noise_source: str = "stub", decide_fn=None, allow_out_of_domain: bool = False) -> None:
        breaches = [k for k, v in pack.verdicts.items() if v == "OUT_OF_DOMAIN"]
        if breaches and not allow_out_of_domain:
            raise InterfaceError(f"pack is outside its models' valid range: {breaches}")
        self.pack, self.mind_type, self.noise_source = pack, mind_type.lower(), noise_source
        self.seed = pack.seed
        self.decide_fn = decide_fn or (contracts.quantum_decide if self.mind_type == "quantum" else contracts.classical_decide)
        self.world = PackWorld(pack)
        self.agent = AgentBody(tuple(pack.sites["spawn"][0]), list(self.world.spawn_pos), pack.t0_local_hour)
        self.recent_events = ["none", "none"]
        self.steps: list[dict] = []
        self.warned = False

    def _event(self, t_s: float) -> str:
        """One event per step, by the frozen priority, from what the agent can notice."""
        now = perceive(self.pack, self.agent.xy_m, t_s)
        previous = perceive(self.pack, self.agent.xy_m, max(0., t_s - self.pack.time.dt_s))
        if now.explosion_heard or now.flow_visible:
            return "eruption"
        if now.ash_kg_m2 > previous.ash_kg_m2:
            return "ash_fall"
        if now.felt_tremor:
            return "tremor"
        if now.gas_smell:
            return "gas_plume"
        if now.rain_mm_h >= STORM_RAIN_MM_H:
            return "storm"
        return "none"

    def _walk_goal(self, action: str) -> XY | None:
        sites = self.pack.sites
        if action == "hide" and self.warned:
            return min(sites["assembly"], key=lambda p: math.dist(p, self.agent.xy_m))
        if action == "drink":
            return min(sites["water"], key=lambda p: math.dist(p, self.agent.xy_m))
        return None

    def _advance(self, action: str, t_s: float) -> None:
        """Walk through the step in substeps, checking hazards at each. No solver runs here."""
        goal = self._walk_goal(action)
        for minute in range(0, STEP_MINUTES, SUBSTEP_MINUTES):
            clock = t_s + minute * 60.
            if goal is not None:
                remaining = math.dist(goal, self.agent.xy_m)
                stride = WALK_M_PER_S * SUBSTEP_MINUTES * 60. * (.5 if self.agent.injured else 1.)
                if remaining > 1.:
                    share = min(1., stride / remaining)
                    candidate = (self.agent.xy_m[0] + (goal[0] - self.agent.xy_m[0]) * share,
                                 self.agent.xy_m[1] + (goal[1] - self.agent.xy_m[1]) * share)
                    if self.pack.sample("terrain.land_mask", candidate):
                        self.agent.xy_m = candidate
            if self.pack.sample("pdc.arrival", self.agent.xy_m) <= clock and self.pack.sample("pdc.active", self.agent.xy_m, clock):
                self.agent.alive, self.agent.cause = False, "pyroclastic_flow"
                break
            if self.pack.has("lahar.depth") and self.pack.sample("lahar.depth", self.agent.xy_m, clock) > 0:
                self.agent.alive, self.agent.cause = False, "lahar"
                break
            if self.pack.has("lava.footprint") and self.pack.sample("lava.footprint", self.agent.xy_m, clock) > 0:
                self.agent.alive, self.agent.cause = False, "lava"
                break
        self.agent.tile = self.world.to_tile(self.agent.xy_m)

    def _needs(self, action: str, event: str) -> None:
        """Placeholder rates, all `assumption`. They exist so minds can run, not to be cited."""
        body = self.agent
        body.thirst = max(0., body.thirst - 1 / 36)
        body.hunger = max(0., body.hunger - .025)
        water = self._walk_goal("drink")
        if action == "drink" and water and math.dist(water, body.xy_m) < 400:
            body.thirst = min(1., body.thirst + .65)
        if action == "rest":
            body.energy = min(1., body.energy + .3)
        else:
            body.energy = max(0., body.energy - .025)
        if event in ("tremor", "gas_plume", "eruption", "ash_fall"):
            self.warned = True
            body.safety = max(0., body.safety - .1)
            body.stress = min(1., body.stress + .08)
        body.hour += 2
        if body.hour >= 24:
            body.hour, body.day = body.hour - 24, body.day + 1
        if body.alive and body.thirst <= 1e-9:
            body.alive, body.cause = False, "dehydration"

    def step(self) -> dict | None:
        t = len(self.steps)
        if not self.agent.alive or t >= self.pack.time.n:
            return None
        t_s = t * self.pack.time.dt_s
        event = self._event(t_s)
        self.recent_events = (self.recent_events + [event])[-3:]
        if event in ("tremor", "gas_plume", "eruption", "ash_fall"):
            self.warned = True
        state = to_state(self.agent, self.recent_events)
        contracts.validate_state(state)
        decision = self.decide_fn(state)
        contracts.validate_decision(decision)
        self._advance(decision["action"], t_s)
        self._needs(decision["action"], event)
        record = {"t": t, "state": state, "event": event, "action": decision["action"], "probs": decision["probs"],
                  "reason": decision["reason"], "pos_after": list(self.agent.tile),
                  "phase": PHASE_NAMES[int(self.pack.series("eruption.phase")[t])]}
        self.steps.append(record)
        return record

    def run(self, max_steps: int | None = None) -> dict:
        limit = self.pack.time.n if max_steps is None else max_steps
        while len(self.steps) < limit and self.step() is not None:
            pass
        return self.timeline()

    def _volcano_export(self) -> dict:
        phase = self.pack.series("eruption.phase")
        erupting = np.flatnonzero(phase == 2)
        arrival = self.pack.frame("pdc.arrival")
        finite = arrival[np.isfinite(arrival)]
        return {"vent": list(self.world.vent), "erupts": bool(erupting.size),
                "onset_step": int(erupting[0]) if erupting.size else None,
                "first_pdc_step": int(finite.min() // self.pack.time.dt_s) if finite.size else None,
                "phases": [PHASE_NAMES[int(p)] for p in phase],
                "world_events": [r["event"] for r in self.steps],
                "hazard_by_step": [self._hazard_at(t) for t in range(self.pack.time.n)]}

    def _hazard_at(self, step: int) -> dict:
        t_s = step * self.pack.time.dt_s
        grid = self.pack.contract_grid
        flows = [[col, row] for row in range(grid.ny) for col in range(grid.nx)
                 if self.pack.sample("pdc.active", grid.centre(row, col), t_s) > 0]
        load = self.pack.frame("tephra.deposit_load", t_s)
        ash = round(float(load.max()), 3)
        return {"new_lava": [], "new_pdc": flows, "active_pdc": flows, "surge": [],
                "new_lahar": [], "active_lahar": [], "ash": ash,
                "ash_grid": ["0" * grid.nx for _ in range(grid.ny)], "wind_deg": 0.0}

    def timeline(self) -> dict:
        volcano = self._volcano_export()
        world = self.world.export_dict()
        world.update(seed=self.seed, mind=self.mind_type, noise_source=self.noise_source, initial_tiles=self.world.tiles,
                     volcano=volcano, pack_hash=self.pack.content_hash, pack_verdicts=dict(self.pack.verdicts),
                     weather=["storm" if r >= STORM_RAIN_MM_H else "rain" if r > 0 else "calm" for r in self.pack.series("atmos.rain_rate")])
        left = next((r["t"] for r in self.steps if self.world.zones[r["pos_after"][1]][r["pos_after"][0]] != 2), None)
        safe = next((r["t"] for r in self.steps if self.world.zones[r["pos_after"][1]][r["pos_after"][0]] == 0), None)
        pdc = volcano["first_pdc_step"]
        return {"world": world, "steps": self.steps, "outcome": "survived" if self.agent.alive else "died", "cause": self.agent.cause,
                "evacuation": {"left_danger_step": left, "reached_safe_step": safe, "first_pdc_step": pdc,
                               "margin_hours": None if safe is None or pdc is None else 2 * (pdc - safe)}}

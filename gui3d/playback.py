"""Pure-Python playback state machine (no Ursina imports).

Turns a stream of step records into smooth frame-by-frame state for the renderer:
agent position (eased along a land path), vitals, action, reason, hazards, weather, day/night
hour and one-shot event markers. The state machine is::

    WAITING --(first step arrives)--> PLAYING <--> PAUSED
    PLAYING --(all steps consumed and source finished)--> FINISHED   (``finished`` emitted ONCE)

The simulation plays uninterrupted: nothing in here ever pauses on its own. Only the user
(SPACE) toggles PAUSED; N/RIGHT advance one step while paused.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Sequence, Tuple

Vec2f = Tuple[float, float]
Tile = Tuple[int, int]

#: Seconds of wall time per simulation step for speed 1/2/3.
SPEED_SECONDS = {1: 1.6, 2: 0.8, 3: 0.35}
HOURS_PER_STEP = 2.0

NEEDS = ("hunger", "thirst", "warmth", "energy", "safety", "morale")
HAZARD_EVENTS = frozenset({"storm", "tremor", "gas_plume", "eruption", "ash_fall", "animal",
                           "injury", "cold_night"})
SHAKE_EVENTS = {"tremor": 0.35, "eruption": 1.0}

WAITING, PLAYING, PAUSED, FINISHED = "waiting", "playing", "paused", "finished"


def ease_in_out(t: float) -> float:
    """Smoothstep-style cubic ease (0..1 -> 0..1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


@dataclass(frozen=True)
class HazardSnapshot:
    """Hazard fields visible at one step (cumulative deposits + active flows)."""

    lava: FrozenSet[Tile] = frozenset()
    pdc: FrozenSet[Tile] = frozenset()
    lahar: FrozenSet[Tile] = frozenset()
    active_pdc: FrozenSet[Tile] = frozenset()
    active_lahar: FrozenSet[Tile] = frozenset()
    surge: FrozenSet[Tile] = frozenset()
    ash: float = 0.0
    wind_deg: float = 0.0
    ash_grid: Optional[Tuple[str, ...]] = None

    def ash_at(self, x: int, y: int) -> float:
        """Ash level 0..1 at a tile (0 when no grid)."""
        if not self.ash_grid or y >= len(self.ash_grid) or x >= len(self.ash_grid[y]):
            return 0.0
        ch = self.ash_grid[y][x]
        return int(ch) / 9.0 if ch.isdigit() else 0.0


@dataclass
class PlaybackEvent:
    """One-shot notification for the renderer (particles, shake, toasts, ending)."""

    kind: str  # "step" | "event" | "shelter" | "death" | "finished"
    step: int
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FrameState:
    """Everything the renderer needs for the current frame."""

    status: str
    step_index: int
    step_fraction: float
    total_steps_known: int
    horizon: int
    agent_pos: Vec2f
    agent_tile: Tile
    facing: Vec2f
    moving: bool
    needs: Dict[str, float]
    stress: float
    injured: bool
    alive: bool
    action: str
    reason: str
    event: str
    probs: Dict[str, float]
    quantum: Dict[str, Any]
    phase: str
    weather: str
    day: int
    hour: float
    hazards: HazardSnapshot
    shelters: FrozenSet[Tile]
    recent_actions: List[Tuple[int, str, str]]


# --------------------------------------------------------------------------------------------
# Helpers (pure)
# --------------------------------------------------------------------------------------------
def land_path(tiles: Sequence[Sequence[int]], a: Tile, b: Tile, limit: int = 4000) -> List[Tile]:
    """Shortest 4-neighbour path over non-water tiles from ``a`` to ``b`` (inclusive).

    Falls back to an L-shaped staircase when no land path exists (e.g. malformed grids).
    """
    a, b = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
    if a == b:
        return [a]
    h = len(tiles)
    w = len(tiles[0]) if h else 0
    prev: Dict[Tile, Optional[Tile]] = {a: None}
    dq: Deque[Tile] = deque([a])
    seen = 0
    while dq and seen < limit:
        cur = dq.popleft()
        seen += 1
        if cur == b:
            break
        x, y = cur
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            nxt = (nx, ny)
            if 0 <= nx < w and 0 <= ny < h and nxt not in prev and (tiles[ny][nx] != 0 or nxt == b):
                prev[nxt] = cur
                dq.append(nxt)
    if b in prev:
        out: List[Tile] = []
        node: Optional[Tile] = b
        while node is not None:
            out.append(node)
            node = prev[node]
        return out[::-1]
    path = [a]
    x, y = a
    while x != b[0]:
        x += 1 if b[0] > x else -1
        path.append((x, y))
    while y != b[1]:
        y += 1 if b[1] > y else -1
        path.append((x, y))
    return path


def point_on_path(path: Sequence[Tile], t: float) -> Tuple[Vec2f, Vec2f]:
    """Position and unit direction at fraction ``t`` (0..1) along a polyline of tiles."""
    if len(path) <= 1:
        p = path[0] if path else (0, 0)
        return (float(p[0]), float(p[1])), (0.0, 1.0)
    segs = len(path) - 1
    u = max(0.0, min(1.0, t)) * segs
    i = min(int(u), segs - 1)
    f = u - i
    (x0, y0), (x1, y1) = path[i], path[i + 1]
    d = (float(x1 - x0), float(y1 - y0))
    return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f), d


def build_hazard_timeline(world: Dict[str, Any], n: int) -> List[HazardSnapshot]:
    """Precompute cumulative hazard snapshots for steps 0..n-1 (empty when no volcano data)."""
    volcano = world.get("volcano") or {}
    by_step = volcano.get("hazard_by_step") or []
    lava: set = set()
    pdc: set = set()
    lahar: set = set()
    out: List[HazardSnapshot] = []
    for t in range(max(n, 0)):
        hz = by_step[t] if t < len(by_step) and isinstance(by_step[t], dict) else {}
        lava.update(tuple(p) for p in hz.get("new_lava", []) or [])
        pdc.update(tuple(p) for p in hz.get("new_pdc", []) or [])
        lahar.update(tuple(p) for p in hz.get("new_lahar", []) or [])
        grid = hz.get("ash_grid")
        out.append(HazardSnapshot(
            lava=frozenset(lava), pdc=frozenset(pdc), lahar=frozenset(lahar),
            active_pdc=frozenset(tuple(p) for p in hz.get("active_pdc", []) or []),
            active_lahar=frozenset(tuple(p) for p in hz.get("active_lahar", []) or []),
            surge=frozenset(tuple(p) for p in hz.get("surge", []) or []),
            ash=float(hz.get("ash") or 0.0), wind_deg=float(hz.get("wind_deg") or 0.0),
            ash_grid=tuple(grid) if isinstance(grid, list) else None,
        ))
    return out


def shelter_steps(world: Dict[str, Any], steps: Sequence[Dict[str, Any]]) -> Dict[int, Tile]:
    """Infer at which step each shelter tile appeared (``tiles`` vs ``initial_tiles``)."""
    tiles = world.get("tiles") or []
    initial = world.get("initial_tiles") or []
    out: Dict[int, Tile] = {}
    if not tiles:
        return out
    built = {(x, y) for y, row in enumerate(tiles) for x, v in enumerate(row)
             if v == 4 and (not initial or initial[y][x] != 4)}
    for rec in steps:
        if rec.get("action") != "build_shelter":
            continue
        pos = tuple(rec.get("pos_after") or (rec.get("state") or {}).get("pos") or ())
        if pos in built and pos not in out.values():
            out[int(rec.get("t", 0))] = pos  # type: ignore[assignment]
    return out


def initial_shelters(world: Dict[str, Any]) -> FrozenSet[Tile]:
    """Shelter tiles present before the run started."""
    grid = world.get("initial_tiles") or world.get("tiles") or []
    return frozenset((x, y) for y, row in enumerate(grid) for x, v in enumerate(row) if v == 4)


# --------------------------------------------------------------------------------------------
# State machine
# --------------------------------------------------------------------------------------------
class Playback:
    """Frame-by-frame playback of a run.

    Feed records with :meth:`push_steps` (all at once for replays, incrementally for live runs),
    call :meth:`mark_source_finished` when the source is exhausted, then call :meth:`update`
    every frame and drain :meth:`pop_events`.
    """

    def __init__(self, world: Dict[str, Any], horizon: int = 36, speed: int = 1) -> None:
        self.world = world or {}
        self.horizon = max(1, int(horizon))
        self.tiles = self.world.get("tiles") or [[1]]
        self.steps: List[Dict[str, Any]] = []
        self.speed = speed if speed in SPEED_SECONDS else 1
        self.status = WAITING
        self.index = 0          # current step being animated
        self.fraction = 0.0     # progress inside the current step (0..1)
        self.source_finished = False
        self._finished_emitted = False
        self._events: List[PlaybackEvent] = []
        self._announced = -1
        self._paths: Dict[int, List[Tile]] = {}
        self._hazards = build_hazard_timeline(self.world, self.horizon)
        self._shelter_at: Dict[int, Tile] = {}
        self._base_shelters = initial_shelters(self.world)
        self._step_requests = 0
        self.weather = list(self.world.get("weather") or [])

    # ---- feeding ---------------------------------------------------------------------------
    def push_steps(self, records: Sequence[Dict[str, Any]]) -> None:
        """Append new step records (ignored after the run finished)."""
        if self.status == FINISHED or not records:
            return
        self.steps.extend(records)
        self._shelter_at = shelter_steps(self.world, self.steps) if self.source_finished else self._shelter_at
        if self.status == WAITING:
            self.status = PLAYING

    def mark_source_finished(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Source has no more steps; optionally provide the final timeline (for shelters)."""
        self.source_finished = True
        if result and isinstance(result.get("world"), dict):
            final_world = dict(self.world)
            final_world.update(tiles=result["world"].get("tiles", self.world.get("tiles")))
            final_world.setdefault("initial_tiles", self.world.get("initial_tiles") or self.world.get("tiles"))
            self._shelter_at = shelter_steps(final_world, self.steps)
        else:
            self._shelter_at = shelter_steps(self.world, self.steps)
        if not self.steps and self.status == WAITING:
            self.status = PLAYING  # zero-step run -> finish immediately on next update

    # ---- controls --------------------------------------------------------------------------
    def set_speed(self, speed: int) -> None:
        """Speed 1, 2 or 3."""
        if speed in SPEED_SECONDS:
            self.speed = speed

    def toggle_pause(self) -> None:
        """SPACE: user pause/resume (never triggered automatically)."""
        if self.status == PLAYING:
            self.status = PAUSED
        elif self.status == PAUSED:
            self.status = PLAYING

    def step_once(self) -> None:
        """N / RIGHT: jump to the end of the current step (works paused or playing)."""
        if self.status in (PLAYING, PAUSED):
            self._step_requests += 1

    def restart(self) -> None:
        """Rewind to step 0 keeping the received records."""
        self.index, self.fraction, self._announced = 0, 0.0, -1
        self._finished_emitted = False
        self._events.clear()
        self.status = PLAYING if (self.steps or self.source_finished) else WAITING

    # ---- frame update ----------------------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self.status == FINISHED

    def update(self, dt: float) -> FrameState:
        """Advance by ``dt`` seconds of wall time and return the frame state."""
        dt = max(0.0, min(float(dt), 0.25))
        if self.status in (PLAYING, PAUSED) and self.index < len(self.steps):
            self._announce(self.index)
        if self.status == PLAYING and self.index < len(self.steps):
            self.fraction += dt / SPEED_SECONDS[self.speed]
        while self._step_requests and self.index < len(self.steps):
            self._step_requests -= 1
            self.fraction = 1.0
            self._advance_if_done(force=True)
        self._step_requests = 0
        if self.status == PLAYING:
            self._advance_if_done()
        if (self.status in (PLAYING, PAUSED) and self.source_finished
                and self.index >= len(self.steps)):
            self._finish()
        return self.frame()

    def _advance_if_done(self, force: bool = False) -> None:
        while self.fraction >= 1.0 and self.index < len(self.steps):
            rec = self.steps[self.index]
            if self.index in self._shelter_at:
                self._events.append(PlaybackEvent("shelter", self.index, {"tile": self._shelter_at[self.index]}))
            alive_next = self.index + 1 < len(self.steps) or not self.source_finished
            self.index += 1
            if self.index >= len(self.steps):
                if self.source_finished:
                    self.fraction = 1.0
                    self.index = len(self.steps)
                    if not alive_next and rec is not None:
                        pass
                    return
                # live source lagging: hold at the end of the last known step (buffering)
                self.index = len(self.steps) - 1
                self.fraction = 1.0
                return
            self.fraction = self.fraction - 1.0 if not force else 0.0
            self._announce(self.index)

    def _announce(self, i: int) -> None:
        if i <= self._announced or i >= len(self.steps):
            return
        self._announced = i
        rec = self.steps[i]
        self._events.append(PlaybackEvent("step", i, {"action": rec.get("action", "rest")}))
        ev = rec.get("event") or "none"
        if ev != "none":
            self._events.append(PlaybackEvent("event", i, {"event": ev, "shake": SHAKE_EVENTS.get(ev, 0.0)}))

    def _finish(self) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.status = FINISHED
        self.index = len(self.steps)
        self._events.append(PlaybackEvent("finished", max(0, len(self.steps) - 1), {}))

    def pop_events(self) -> List[PlaybackEvent]:
        """Drain one-shot events produced since the last call."""
        ev, self._events = self._events, []
        return ev

    # ---- frame construction -----------------------------------------------------------------
    def _path(self, i: int) -> List[Tile]:
        if i not in self._paths:
            rec = self.steps[i]
            a = tuple((rec.get("state") or {}).get("pos") or rec.get("pos_after") or (0, 0))
            b = tuple(rec.get("pos_after") or a)
            self._paths[i] = land_path(self.tiles, a, b)  # type: ignore[arg-type]
        return self._paths[i]

    def hazards_at(self, i: int) -> HazardSnapshot:
        """Hazard snapshot for step ``i`` (clamped)."""
        if not self._hazards:
            return HazardSnapshot()
        return self._hazards[max(0, min(i, len(self._hazards) - 1))]

    def frame(self) -> FrameState:
        """Build the frame for the current playhead (no time advance)."""
        n = len(self.steps)
        if n == 0:
            spawn = tuple((self.world.get("evacuation_map") or {}).get("route_from_spawn", [[20, 20]])[0]) \
                if (self.world.get("evacuation_map") or {}).get("route_from_spawn") else (20, 20)
            return FrameState(self.status, 0, 0.0, 0, self.horizon, (float(spawn[0]), float(spawn[1])),
                              (int(spawn[0]), int(spawn[1])), (0.0, 1.0), False,
                              {k: 1.0 for k in NEEDS}, 0.0, False, True, "rest", "", "none", {}, {},
                              "unrest", self.weather[0] if self.weather else "calm", 1, 8.0,
                              self.hazards_at(0), self._base_shelters, [])
        i = min(self.index, n - 1)
        frac = 1.0 if self.index >= n else self.fraction
        rec = self.steps[i]
        st = rec.get("state") or {}
        nxt_state = self.steps[i + 1].get("state") if i + 1 < n else None
        e = ease_in_out(frac)
        path = self._path(i)
        pos, d = point_on_path(path, e)
        tile = (int(round(pos[0])), int(round(pos[1])))
        needs0 = st.get("needs") or {}
        needs1 = (nxt_state or {}).get("needs") or needs0
        needs = {k: float(needs0.get(k, 1.0)) + (float(needs1.get(k, needs0.get(k, 1.0))) - float(needs0.get(k, 1.0))) * e
                 for k in NEEDS}
        stress0 = float(st.get("stress", 0.0))
        stress1 = float((nxt_state or {}).get("stress", stress0))
        died = self.source_finished and i == n - 1 and self._outcome_died()
        alive = not (died and frac >= 0.999)
        hour = float(st.get("hour", 8)) + HOURS_PER_STEP * frac
        shelters = set(self._base_shelters)
        for t, tl in self._shelter_at.items():
            if t < i or (t == i and frac >= 0.999):
                shelters.add(tl)
        recent = [(int(s.get("t", k)), s.get("action", "rest"), s.get("event", "none"))
                  for k, s in enumerate(self.steps[max(0, i - 11):i + 1], start=max(0, i - 11))]
        moving = len(path) > 1 and 0.0 < frac < 1.0
        return FrameState(
            status=self.status, step_index=i, step_fraction=frac, total_steps_known=n,
            horizon=self.horizon, agent_pos=pos, agent_tile=tile,
            facing=d if (d[0] or d[1]) else (0.0, 1.0), moving=moving, needs=needs,
            stress=stress0 + (stress1 - stress0) * e, injured=bool(st.get("injured", False)),
            alive=alive, action=str(rec.get("action", "rest")), reason=str(rec.get("reason", "")),
            event=str(rec.get("event", "none")), probs=dict(rec.get("probs") or {}),
            quantum=dict(rec.get("quantum") or {}), phase=str(rec.get("phase") or "unrest"),
            weather=self.weather[i] if i < len(self.weather) else "calm",
            day=int(st.get("day", 1)) + int(hour // 24), hour=hour % 24.0,
            hazards=self.hazards_at(i), shelters=frozenset(shelters), recent_actions=recent,
        )

    _died_flag: Optional[bool] = None

    def set_outcome(self, outcome: Optional[str]) -> None:
        """Tell playback whether the run ended in death (for the fallen pose on the last step)."""
        self._died_flag = outcome == "died"

    def _outcome_died(self) -> bool:
        return bool(self._died_flag)


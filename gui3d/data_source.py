"""Data adapter between the simulation and the 3D front-end.

The 3D code never touches engine internals: it only sees plain ``dict`` records with the
existing ``timeline.json`` schema (``world``, ``steps``, ``evacuation``, ``outcome``, ``cause``).

Two sources are provided behind one small interface (:class:`RunSource`):

* :class:`ReplaySource` - replays ``timeline.json`` / ``demo-pack/*.json`` (or an in-memory dict).
* :class:`LiveSource`   - runs :class:`engine.simulation.SimulationEngine` in-process on a single
  background worker thread and streams step records as they are produced, so the UI never stalls.

All engine work (live run, other-mind replay, N-seed batch) is serialised on ONE worker thread
because ``SimulationEngine.step`` swaps the *global* ``random`` state; running two engines at once
would make results non-deterministic. UI code must therefore use private ``random.Random``
instances (never the module-level functions).

No Ursina imports here.
"""
from __future__ import annotations

import copy
import json
import os
import queue
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HORIZON = 36
HORIZONS = (12, 24, 36)
SCENARIOS = ("island", "volcano")
MINDS = ("quantum", "classical", "classical_mixture")


def other_mind(mind: str) -> str:
    """Quantum <-> classical toggle used by the Q key and the ending comparison."""
    return "classical" if mind == "quantum" else "quantum"


@dataclass
class RunMeta:
    """What the UI needs to know about a run before/while it plays."""

    scenario: str = "volcano"
    seed: int = 101
    mind: str = "quantum"
    horizon: int = DEFAULT_HORIZON
    world: Dict[str, Any] = field(default_factory=dict)
    source_label: str = "live"


# --------------------------------------------------------------------------------------------
# Single serialised engine worker
# --------------------------------------------------------------------------------------------
class EngineWorker:
    """One daemon thread executing engine jobs in FIFO order (see module docstring)."""

    _instance: Optional["EngineWorker"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._jobs: "queue.Queue[Optional[Callable[[], None]]]" = queue.Queue()
        self._thread = threading.Thread(target=self._loop, name="gui3d-engine", daemon=True)
        self._thread.start()

    @classmethod
    def shared(cls) -> "EngineWorker":
        """Process-wide worker instance."""
        with cls._lock:
            if cls._instance is None or not cls._instance._thread.is_alive():
                cls._instance = EngineWorker()
            return cls._instance

    def submit(self, job: Callable[[], None]) -> None:
        """Queue a callable; exceptions are caught and printed, never raised into the UI."""
        self._jobs.put(job)

    def _loop(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
            try:
                job()
            except Exception:  # pragma: no cover - defensive
                traceback.print_exc()


def _make_engine(seed: int, mind: str, scenario: str):
    """Construct the engine lazily (heavy imports happen on the worker thread)."""
    from engine.simulation import SimulationEngine  # public interface only

    return SimulationEngine(seed=seed, mind_type=mind, noise_source="stub", scenario=scenario)


def run_engine_blocking(seed: int, mind: str, scenario: str, horizon: int = DEFAULT_HORIZON) -> Dict[str, Any]:
    """Run one complete simulation synchronously and return its timeline dict."""
    sim = _make_engine(seed, mind, scenario)
    return sim.run(max_steps=horizon)


# --------------------------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------------------------
class RunSource:
    """Interface every source implements."""

    meta: RunMeta

    def ready(self) -> bool:
        """True once ``meta.world`` is available (scene can be built)."""
        raise NotImplementedError

    def poll(self) -> List[Dict[str, Any]]:
        """Return step records produced since the last call (may be empty)."""
        raise NotImplementedError

    def finished(self) -> bool:
        """True when no more steps will arrive."""
        raise NotImplementedError

    def result(self) -> Optional[Dict[str, Any]]:
        """Full timeline dict once finished, else ``None``."""
        raise NotImplementedError

    def error(self) -> Optional[str]:
        """Error text if the source failed."""
        return None


def load_timeline(path: os.PathLike | str) -> Dict[str, Any]:
    """Load a timeline JSON file (``timeline.json`` or ``demo-pack/*.json``)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _infer_horizon(timeline: Dict[str, Any]) -> int:
    world = timeline.get("world") or {}
    weather = world.get("weather")
    if isinstance(weather, list) and weather:
        return len(weather)
    phases = (world.get("volcano") or {}).get("phases")
    if isinstance(phases, list) and phases:
        return len(phases)
    return max(DEFAULT_HORIZON, len(timeline.get("steps") or []))


class ReplaySource(RunSource):
    """Replay a recorded timeline. Every step is available immediately."""

    def __init__(self, timeline: Dict[str, Any] | os.PathLike | str, horizon: Optional[int] = None) -> None:
        label = "replay"
        if not isinstance(timeline, dict):
            label = Path(timeline).name
            timeline = load_timeline(timeline)
        self._timeline = timeline
        world = timeline.get("world") or {}
        self.meta = RunMeta(
            scenario=str(world.get("scenario") or "volcano"),
            seed=int(world.get("seed") or 0),
            mind=str(world.get("mind") or "quantum"),
            horizon=int(horizon or _infer_horizon(timeline)),
            world=world,
            source_label=label,
        )
        self._delivered = False

    def ready(self) -> bool:
        return True

    def poll(self) -> List[Dict[str, Any]]:
        if self._delivered:
            return []
        self._delivered = True
        return list(self._timeline.get("steps") or [])

    def finished(self) -> bool:
        return True

    def result(self) -> Dict[str, Any]:
        return self._timeline


class LiveSource(RunSource):
    """Run the engine on the shared worker thread and stream records to the UI."""

    def __init__(self, seed: int = 101, mind: str = "quantum", scenario: str = "volcano",
                 horizon: int = DEFAULT_HORIZON, worker: Optional[EngineWorker] = None) -> None:
        self.meta = RunMeta(scenario=scenario, seed=seed, mind=mind, horizon=int(horizon), source_label="live")
        self._q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._ready = threading.Event()
        self._done = threading.Event()
        self._result: Optional[Dict[str, Any]] = None
        self._error: Optional[str] = None
        self._cancel = threading.Event()
        (worker or EngineWorker.shared()).submit(self._job)

    def cancel(self) -> None:
        """Stop producing steps (used on restart / leaving the screen)."""
        self._cancel.set()

    def _job(self) -> None:
        try:
            sim = _make_engine(self.meta.seed, self.meta.mind, self.meta.scenario)
            self.meta.world = copy.deepcopy(sim.timeline()["world"])
            self._ready.set()
            horizon = min(self.meta.horizon, DEFAULT_HORIZON)
            while len(sim.steps) < horizon and not self._cancel.is_set():
                rec = sim.step()
                if rec is None:
                    break
                self._q.put(copy.deepcopy(rec))
            self._result = sim.timeline()
        except Exception as exc:  # pragma: no cover - surfaced in UI
            self._error = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
            self._ready.set()
        finally:
            self._done.set()

    def wait_ready(self, timeout: float = 30.0) -> bool:
        """Block until the world is known (tests / smoke only)."""
        return self._ready.wait(timeout)

    def wait_done(self, timeout: float = 60.0) -> bool:
        """Block until the run finished (tests only)."""
        return self._done.wait(timeout)

    def ready(self) -> bool:
        return self._ready.is_set() and bool(self.meta.world)

    def poll(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        while True:
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                return out

    def finished(self) -> bool:
        return self._done.is_set() and self._q.empty()

    def result(self) -> Optional[Dict[str, Any]]:
        return self._result if self._done.is_set() else None

    def error(self) -> Optional[str]:
        return self._error


# --------------------------------------------------------------------------------------------
# Background comparisons for the ending screen
# --------------------------------------------------------------------------------------------
class BackgroundJob:
    """A value computed on the engine worker; poll ``done``/``value`` from the UI thread."""

    def __init__(self, fn: Callable[[], Any], worker: Optional[EngineWorker] = None) -> None:
        self.value: Any = None
        self.error: Optional[str] = None
        self._done = threading.Event()
        self._cancel = threading.Event()

        def job() -> None:
            if self._cancel.is_set():
                self._done.set()
                return
            try:
                self.value = fn()
            except Exception as exc:  # pragma: no cover - surfaced in UI
                self.error = f"{type(exc).__name__}: {exc}"
            finally:
                self._done.set()

        (worker or EngineWorker.shared()).submit(job)

    @property
    def done(self) -> bool:
        return self._done.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def wait(self, timeout: float = 120.0) -> bool:
        return self._done.wait(timeout)


def other_mind_job(seed: int, mind: str, scenario: str, horizon: int) -> BackgroundJob:
    """Replay the same seed with the other mind (quantum <-> classical)."""
    return BackgroundJob(lambda: run_engine_blocking(seed, other_mind(mind), scenario, horizon))


def batch_survival(scenario: str, num_seeds: int = 8, horizon: int = DEFAULT_HORIZON,
                   start_seed: int = 100) -> Dict[str, Any]:
    """Survival rate across N seeds for Quantum vs Classical.

    Uses ``engine.batch_runner.run_batch_comparison`` when it covers the request (volcano,
    full horizon - the only configuration it exposes); otherwise runs the same paired-seed loop.
    """
    if scenario == "volcano" and horizon >= DEFAULT_HORIZON:
        try:
            import contextlib
            import io

            from engine.batch_runner import run_batch_comparison

            with contextlib.redirect_stdout(io.StringIO()):
                summary = run_batch_comparison(num_seeds=num_seeds, max_steps=horizon)
            return {
                "num_seeds": int(summary["num_seeds"]),
                "quantum_pct": float(summary["quantum_survival_rate_pct"]),
                "classical_pct": float(summary["classical_survival_rate_pct"]),
                "divergence_pct": float(summary["divergence_rate_pct"]),
                "via": "engine.batch_runner",
            }
        except Exception:
            pass
    q_alive = c_alive = div = total = 0
    for seed in range(start_seed, start_seed + num_seeds):
        rq = run_engine_blocking(seed, "quantum", scenario, horizon)
        rc = run_engine_blocking(seed, "classical", scenario, horizon)
        q_alive += rq["outcome"] == "survived"
        c_alive += rc["outcome"] == "survived"
        for a, b in zip(rq["steps"], rc["steps"]):
            total += 1
            div += a["action"] != b["action"]
    n = max(1, num_seeds)
    return {
        "num_seeds": num_seeds,
        "quantum_pct": round(100.0 * q_alive / n, 1),
        "classical_pct": round(100.0 * c_alive / n, 1),
        "divergence_pct": round(100.0 * div / max(1, total), 1),
        "via": "gui3d.paired_seed_loop",
    }


def batch_job(scenario: str, num_seeds: int = 8, horizon: int = DEFAULT_HORIZON) -> BackgroundJob:
    """Background N-seed survival comparison."""
    return BackgroundJob(lambda: batch_survival(scenario, num_seeds, horizon))


def list_demo_runs() -> List[Path]:
    """All bundled replays (``demo-pack/*.json`` and ``timeline.json``)."""
    runs = sorted((ROOT / "demo-pack").glob("*.json"))
    tl = ROOT / "timeline.json"
    if tl.exists():
        runs.append(tl)
    return runs


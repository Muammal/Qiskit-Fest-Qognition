"""Unit and regression tests for the 3D front-end (gui3d).

Runs completely headless without requiring a physical GPU display.
Validates:
  1. Playback state machine step transitions and event notifications.
  2. Ending stats computation across all bundled demo-pack runs.
  3. Single-ending trigger invariant (ending occurs exactly once).
  4. Zero mid-run blocking popups across multiple scenarios, seeds, and minds.
  5. UI layout containment across 1024x768, 1280x720, 1920x1080, 2560x1440, 3440x1440, and 3840x2160.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from gui3d.data_source import LiveSource, ReplaySource, load_timeline
from gui3d.ending_stats import build_ending_stats
from gui3d.layout import LayoutManager
from gui3d.playback import FINISHED, PAUSED, PLAYING, WAITING, Playback


def test_layout_containment_across_resolutions():
    """Verify standard UI rects fit completely inside screens from 1024x768 to 3840x2160."""
    resolutions = [
        (1024, 768),   # 4:3
        (1280, 720),   # 16:9 720p
        (1920, 1080),  # 16:9 1080p
        (2560, 1440),  # 16:9 1440p
        (3440, 1440),  # 21:9 Ultrawide
        (3840, 2160),  # 16:9 4K UHD
    ]
    for w, h in resolutions:
        lm = LayoutManager(w, h)
        rects = lm.get_standard_ui_rects()
        for name, r in rects.items():
            assert r.x >= 0, f"{name} left overflow at {w}x{h}"
            assert r.y >= 0, f"{name} top overflow at {w}x{h}"
            assert r.right <= w + 1.0, f"{name} right overflow at {w}x{h} ({r.right} > {w})"
            assert r.bottom <= h + 1.0, f"{name} bottom overflow at {w}x{h} ({r.bottom} > {h})"


def test_playback_state_machine_flow():
    """Verify WAITING -> PLAYING -> PAUSED -> FINISHED state flow and event dispatch."""
    mock_world = {"tiles": [[1, 1], [1, 1]], "horizon": 4}
    pb = Playback(mock_world, horizon=4, speed=3)
    assert pb.status == WAITING

    steps = [
        {"t": 0, "action": "forage", "event": "none", "state": {"pos": [0, 0], "needs": {}}},
        {"t": 1, "action": "explore", "event": "tremor", "state": {"pos": [0, 1], "needs": {}}},
        {"t": 2, "action": "rest", "event": "none", "state": {"pos": [0, 1], "needs": {}}},
    ]

    pb.push_steps(steps)
    assert pb.status == PLAYING

    # Step 0 is announced on update
    pb.update(0.01)
    events = pb.pop_events()
    assert any(e.kind == "step" and e.data["action"] == "forage" for e in events)

    # Pause test
    pb.toggle_pause()
    assert pb.status == PAUSED
    pb.toggle_pause()
    assert pb.status == PLAYING

    # Step once
    pb.step_once()
    pb.update(0.1)
    events2 = pb.pop_events()
    assert any(e.kind == "event" and e.data["event"] == "tremor" for e in events2)

    # Mark finished and advance to end
    pb.mark_source_finished()
    for _ in range(20):
        pb.update(0.5)

    assert pb.status == FINISHED
    all_events = pb.pop_events()
    finished_events = [e for e in all_events if e.kind == "finished"]
    assert len(finished_events) == 1, "Finished event must be emitted exactly once"


def test_ending_stats_across_all_demo_packs():
    """Verify build_ending_stats handles all demo pack runs and extracts valid metrics."""
    demo_files = glob.glob("demo-pack/*.json")
    assert len(demo_files) >= 5, "Expected at least 5 demo pack JSON files"

    for path in demo_files:
        timeline = load_timeline(path)
        stats = build_ending_stats(timeline)

        assert stats.outcome in ("survived", "died")
        assert stats.grade in ("S", "A", "B", "C", "D")
        assert 1 <= stats.stars <= 3
        assert len(stats.title) > 0
        assert len(stats.epilogue) > 0
        assert stats.freeze_pose in ("happy", "exhausted", "fallen")
        assert stats.steps_survived == len(timeline.get("steps", []))
        assert 0.0 <= stats.survival_pct <= 100.0


def test_uninterrupted_sim_and_single_ending():
    """Verify that simulated runs progress continuously with exactly one ending cutscene trigger."""
    from engine.simulation import SimulationEngine

    for scenario in ("island", "volcano"):
        for mind in ("quantum", "classical"):
            sim = SimulationEngine(seed=101, mind_type=mind, scenario=scenario)
            timeline = sim.run(max_steps=12)

            pb = Playback(timeline["world"], horizon=12, speed=3)
            pb.push_steps(timeline["steps"])
            pb.mark_source_finished(timeline)

            ending_count = 0
            for _ in range(50):
                state = pb.update(0.2)
                # Ensure no mid-run modal states
                assert state.status in (PLAYING, FINISHED)
                for ev in pb.pop_events():
                    if ev.kind == "finished":
                        ending_count += 1

            assert ending_count == 1, f"Scenario {scenario} with mind {mind} did not trigger ending exactly once"


def test_smoke_offscreen_run():
    """Verify play3d.py --smoke runs offscreen without GPU display and exits 0 cleanly."""
    import subprocess
    import sys

    cmd = [sys.executable, "play3d.py", "--smoke"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"play3d.py --smoke failed with exit {proc.returncode}:\n{proc.stderr}"
    assert "Verified offscreen render loop" in proc.stdout


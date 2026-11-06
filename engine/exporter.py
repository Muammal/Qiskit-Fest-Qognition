"""
engine/exporter.py - Evacuation Survival Data, Seed Catalog & Full Simulation Video Exporter.

Provides:
1. export_evacuation_datasets(): Exports CSV, JSON, and Markdown reports of survival rates,
   cognitive divergence seeds, and counterfactual evacuation policy interventions across
   Volcano, Island, Titanic, Pompeii, and Waterloo scenarios.
2. export_simulation_video(): Renders a complete simulation run from start to finish
   (1600x900 canvas including map, agents, telemetry, and final debrief) to an MP4 video.
3. LiveVideoRecorder: Attachable frame recorder for interactive GUI sessions (including Slow-Mo
   and Fast-Forward playback).
"""

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from engine.simulation import SimulationEngine
from engine.titanic import compare_titanic_policies
from engine.pompeii import PompeiiSimulation
from engine.waterloo import WaterlooSimulation


VIDEO_HELP = "Recording video needs ffmpeg, or opencv-python-headless. Install either one and try again."


class VideoBackendMissing(RuntimeError):
    """Neither ffmpeg nor OpenCV is available."""


class LiveVideoRecorder:
    """Streams 1600x900 Pygame canvas frames to an H.264 MP4 file via ffmpeg or OpenCV."""

    def __init__(self, output_path: str, width: int = 1600, height: int = 900, fps: int = 30):
        self.output_path = str(output_path)
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_count = 0
        self._proc: Optional[subprocess.Popen] = None
        self._cv_writer = None
        self.active = False

    def start(self) -> str:
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "rawvideo",
                "-vcodec",
                "rawvideo",
                "-s",
                f"{self.width}x{self.height}",
                "-pix_fmt",
                "rgb24",
                "-r",
                str(self.fps),
                "-i",
                "-",
                "-an",
                "-vcodec",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "fast",
                "-crf",
                "21",
                self.output_path,
            ]
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.active = True
            return self.output_path

        try:
            import cv2
        except ImportError:
            raise VideoBackendMissing(VIDEO_HELP) from None

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._cv_writer = cv2.VideoWriter(self.output_path, fourcc, float(self.fps), (self.width, self.height))
        self.active = True
        return self.output_path

    def capture_surface(self, surface) -> None:
        if not self.active:
            return
        import pygame

        # array3d returns shape (W, H, 3); transpose to (H, W, 3)
        rgb = np.transpose(pygame.surfarray.array3d(surface), (1, 0, 2))
        if self._proc is not None and self._proc.stdin is not None:
            try:
                self._proc.stdin.write(np.ascontiguousarray(rgb, dtype=np.uint8).tobytes())
                self.frame_count += 1
            except BrokenPipeError:
                self.active = False
        elif self._cv_writer is not None:
            import cv2

            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            self._cv_writer.write(bgr)
            self.frame_count += 1

    def stop(self) -> str:
        if not self.active:
            return self.output_path
        self.active = False
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.wait(timeout=15)
            except Exception:
                self._proc.kill()
            self._proc = None
        if self._cv_writer is not None:
            self._cv_writer.release()
            self._cv_writer = None
        return self.output_path


def export_simulation_video(
    scenario: str = "volcano",
    seed: int = 101,
    mind: str = "quantum",
    output_path: Optional[str] = None,
    fps: int = 24,
    frames_per_step: int = 6,
    speed_multiplier: float = 1.0,
    max_steps: Optional[int] = None,
    include_debrief_frames: int = 24,
) -> Dict[str, Any]:
    """Renders an entire simulation from start to finish into an MP4 video file."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from engine.gui import IslandVisualizerApp, WINDOW_WIDTH, WINDOW_HEIGHT

    if output_path is None:
        speed_tag = f"_{speed_multiplier:g}x" if speed_multiplier != 1.0 else ""
        output_path = os.path.join("exports", "videos", f"{scenario}_seed{seed}_{mind}{speed_tag}.mp4")

    app = IslandVisualizerApp(
        seed=seed,
        mind_type=mind,
        noise_source="stub",
        start_screen="sim",
        scenario=scenario,
    )
    app.speed_multiplier = speed_multiplier
    if max_steps is not None:
        app.max_steps = min(max_steps, app.max_steps)

    # Keep cutscenes concise during full-run video export
    app.cutscene.enabled = False

    recorder = LiveVideoRecorder(output_path, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, fps=fps)
    recorder.start()

    # Adjust frames per step inversely with speed_multiplier so Slow-Mo (e.g. 0.25x) renders more frames
    # per step and Fast-Forward (e.g. 4.0x) renders fewer frames per step.
    effective_frames_per_step = max(1, int(round(frames_per_step / max(0.1, speed_multiplier))))
    dt = 1.0 / float(fps)

    # Capture initial state frames before Step 1
    for _ in range(max(4, effective_frames_per_step)):
        app.draw((5, 5))
        recorder.capture_surface(app.canvas)

    # Step through the entire simulation
    while not app.show_debrief_modal and app.step_idx < app.max_steps:
        app.step_forward()
        if getattr(app, "_worker", None) is not None:
            app._worker.join()
            app._pompeii_poll_step()

        for _ in range(effective_frames_per_step):
            sim_dt = dt * app.speed_multiplier
            app.char_screen_x += (app.char_target_x - app.char_screen_x) * min(1.0, 12.0 * sim_dt)
            app.char_screen_y += (app.char_target_y - app.char_screen_y) * min(1.0, 12.0 * sim_dt)
            app.char_bob = float(np.sin(recorder.frame_count * 0.35 * app.speed_multiplier) * 2.0)
            if app.bubble_timer > 0:
                app.bubble_timer = max(0.0, app.bubble_timer - sim_dt)
            ash_level = getattr(app.world, "ash", 0.0)
            app.weather.update(app.current_event, sim_dt, ash_level=ash_level)
            app.draw((5, 5))
            recorder.capture_surface(app.canvas)

    # Ensure debrief modal is shown at the end of the video
    app.show_debrief_modal = True
    for _ in range(include_debrief_frames):
        app.draw((5, 5))
        recorder.capture_surface(app.canvas)

    saved_path = recorder.stop()
    return {
        "scenario": scenario,
        "seed": seed,
        "mind": mind,
        "speed_multiplier": speed_multiplier,
        "steps_rendered": app.step_idx,
        "frames_written": recorder.frame_count,
        "fps": fps,
        "duration_seconds": round(recorder.frame_count / float(fps), 2),
        "output_path": os.path.abspath(saved_path),
    }


def export_evacuation_datasets(output_dir: str = "exports", num_seeds: int = 12) -> Dict[str, Any]:
    """Exports survival rates, critical seeds, and real-life evacuation policy interventions."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    minds = ("quantum", "classical_mixture", "classical")

    # 1. Seed-by-seed analysis across Volcano & Island scenarios (identifying critical evacuation seeds)
    seed_rows: List[Dict[str, Any]] = []
    for scenario in ("volcano", "island"):
        for seed in range(100, 100 + num_seeds):
            runs = {}
            for mind in minds:
                sim = SimulationEngine(seed=seed, mind_type=mind, scenario=scenario)
                runs[mind] = sim.run()

            q_run, m_run, c_run = runs["quantum"], runs["classical_mixture"], runs["classical"]
            q_steps, m_steps, c_steps = q_run["steps"], m_run["steps"], c_run["steps"]
            min_len = min(len(q_steps), len(m_steps))
            qm_div = sum(1 for i in range(min_len) if q_steps[i]["action"] != m_steps[i]["action"])
            max_order_gap = max(
                (abs(s.get("quantum", {}).get("order_gap") or 0.0) for s in q_steps if s.get("quantum")),
                default=0.0,
            )
            mean_coherence = (
                float(np.mean([s["quantum"].get("coherence") or 0.0 for s in q_steps if s.get("quantum")])) if any(s.get("quantum") for s in q_steps) else 0.0
            )

            q_evac = q_run.get("evacuation", {}).get("first_evacuating_step")
            m_evac = m_run.get("evacuation", {}).get("first_evacuating_step")
            c_evac = c_run.get("evacuation", {}).get("first_evacuating_step")

            if q_run["outcome"] != m_run["outcome"]:
                insight = (
                    "Quantum survived where Classical Mixture perished (interference prevented premature resource exhaustion)"
                    if q_run["outcome"] == "survived"
                    else "Classical Mixture survived where Quantum hesitated under ambiguous warnings (requires unambiguous alarm)"
                )
            elif qm_div > 0:
                insight = f"Quantum vs Mixture diverged on {qm_div} steps (max order-effect gap={max_order_gap:.3f})"
            else:
                insight = "Aligned trajectory across Quantum and Classical Mixture"

            seed_rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "erupts": q_run["world"]["volcano"]["erupts"] if scenario == "volcano" else False,
                    "quantum_outcome": q_run["outcome"],
                    "quantum_cause": q_run["cause"] or "none",
                    "quantum_steps": len(q_steps),
                    "quantum_first_evac_step": q_evac if q_evac is not None else -1,
                    "mixture_outcome": m_run["outcome"],
                    "mixture_cause": m_run["cause"] or "none",
                    "mixture_steps": len(m_steps),
                    "mixture_first_evac_step": m_evac if m_evac is not None else -1,
                    "classical_outcome": c_run["outcome"],
                    "classical_cause": c_run["cause"] or "none",
                    "classical_steps": len(c_steps),
                    "classical_first_evac_step": c_evac if c_evac is not None else -1,
                    "qm_action_divergences": qm_div,
                    "mean_quantum_coherence": round(mean_coherence, 4),
                    "max_order_effect_gap": round(max_order_gap, 4),
                    "evacuation_insight": insight,
                }
            )

    # Write critical_evacuation_seeds_catalog.csv
    seeds_csv = out_path / "critical_evacuation_seeds_catalog.csv"
    if seed_rows:
        with open(seeds_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(seed_rows[0].keys()))
            writer.writeheader()
            writer.writerows(seed_rows)

    # 2. Policy Interventions across Crowd Evacuation Scenarios (Titanic, Pompeii, Waterloo)
    policy_rows: List[Dict[str, Any]] = []

    # 2A. Titanic Policy Counterfactuals (2,208 aboard)
    titanic_policies = compare_titanic_policies(seed=42, minds=minds)
    policy_descriptions = {
        "historical_baseline": "Historical baseline: steward knocks ambiguous (gas_plume), rockets collapse (ash_fall), port side women/children only",
        "ambiguous_rockets": "Ambiguous distress rockets: rockets treated as rotation (gas_plume) — tests quantum hesitation without collapse",
        "early_pa_alarm": "Unambiguous early ship-wide PA alarm: steward warning mapped to projective collapse (eruption)",
        "open_boarding_both_sides": "Early PA alarm + open boarding on both sides after women/children (Murdoch policy on port & starboard)",
    }
    for pol_name, mind_map in titanic_policies.items():
        for mind in minds:
            row = mind_map[mind]
            policy_rows.append(
                {
                    "scenario": "titanic",
                    "seed": 42,
                    "policy_id": pol_name,
                    "mind": mind,
                    "population": 2208,
                    "survived_or_safe": row["saved"],
                    "fatalities_or_high_exposure": row["dead"],
                    "survival_or_safety_rate_pct": round(row["survival_rate"] * 100.0, 2),
                    "real_life_policy_recommendation": policy_descriptions[pol_name],
                }
            )

    # 2B. Pompeii Event-Framing & Bottleneck Counterfactuals (1,500 sample population for fast export)
    pompeii_configs = [
        (
            "mapping_A_unambiguous_column",
            dict(event_mapping="A", crowding=True, restrict_enslaved=False),
            "Clear hazard communication: eruption column treated as unambiguous danger (eruption collapse)",
        ),
        (
            "mapping_B_literal_default",
            dict(event_mapping="B", crowding=True, restrict_enslaved=False),
            "Default literal framing: column is gas_plume rotation, pumice is ash_fall collapse",
        ),
        (
            "mapping_C_ambiguous_cues",
            dict(event_mapping="C", crowding=True, restrict_enslaved=False),
            "Ambiguous cues: both column and pumice treated as non-collapsing gas_plume rotations (quantum disjunction delay)",
        ),
        (
            "mapping_D_milder_plus_enslaved_restricted",
            dict(event_mapping="D", crowding=True, restrict_enslaved=True),
            "Worst-case ambiguity + household movement restriction on enslaved persons",
        ),
    ]
    for pol_id, kwargs, desc in pompeii_configs:
        for mind in minds:
            sim = PompeiiSimulation(seed=42, mind_type=mind, population=500, **kwargs)
            sim.run()
            counts = sim.counts()
            dead = counts["dead"]
            escaped = 500 - dead
            policy_rows.append(
                {
                    "scenario": "pompeii",
                    "seed": 42,
                    "policy_id": pol_id,
                    "mind": mind,
                    "population": 500,
                    "survived_or_safe": escaped,
                    "fatalities_or_high_exposure": dead,
                    "survival_or_safety_rate_pct": round(escaped / 500.0 * 100.0, 2),
                    "real_life_policy_recommendation": desc,
                }
            )

    # 2C. Waterloo Chlorine Gas Leak Alarm Policy Counterfactuals (100 visitors)
    waterloo_configs = [
        (
            "alarm_off_ambiguous_smell",
            dict(alarm=False, event_mapping="A"),
            "No facility alarm: visitors rely on chlorine smell & word of mouth (quantum hesitation increases AEGL-2 exposure)",
        ),
        (
            "alarm_on_ambiguous_mapping_A",
            dict(alarm=True, event_mapping="A"),
            "Staff alarm enabled (mapped to gas_plume rotation): partial reduction in exposure",
        ),
        (
            "alarm_on_unambiguous_mapping_B",
            dict(alarm=True, event_mapping="B"),
            "Unambiguous staff alarm (mapped to projective collapse): eliminates quantum hesitation & minimizes AEGL-2 exposure",
        ),
    ]
    for pol_id, kwargs, desc in waterloo_configs:
        for mind in minds:
            sim = WaterlooSimulation(seed=42, mind_type=mind, population=100, **kwargs)
            sim.run()
            table = sim.outcome_table()
            aegl2_plus = sum(r["levels"]["2"] + r["levels"]["3"] for r in table.values())
            safe_count = 100 - aegl2_plus
            policy_rows.append(
                {
                    "scenario": "waterloo",
                    "seed": 42,
                    "policy_id": pol_id,
                    "mind": mind,
                    "population": 100,
                    "survived_or_safe": safe_count,
                    "fatalities_or_high_exposure": aegl2_plus,
                    "survival_or_safety_rate_pct": round(safe_count / 100.0 * 100.0, 2),
                    "real_life_policy_recommendation": desc,
                }
            )

    policies_csv = out_path / "evacuation_policy_interventions.csv"
    with open(policies_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(policy_rows[0].keys()))
        writer.writeheader()
        writer.writerows(policy_rows)

    # 3. Aggregate Scenario Summary Table
    scenario_summary: List[Dict[str, Any]] = []
    for scenario in ("volcano", "island"):
        rows_s = [r for r in seed_rows if r["scenario"] == scenario]
        for mind_prefix, mind_name in (("quantum", "quantum"), ("mixture", "classical_mixture"), ("classical", "classical")):
            surv = sum(1 for r in rows_s if r[f"{mind_prefix}_outcome"] == "survived")
            scenario_summary.append(
                {
                    "scenario": scenario,
                    "mind": mind_name,
                    "SampleSize": f"{len(rows_s)} seeds",
                    "survived_or_safe_pct": round(surv / max(1, len(rows_s)) * 100.0, 2),
                    "notes": f"Evaluated across seeds 100..{100 + len(rows_s) - 1}",
                }
            )
    for row in policy_rows:
        if row["policy_id"] in ("historical_baseline", "mapping_C_ambiguous_cues", "alarm_on_unambiguous_mapping_B"):
            scenario_summary.append(
                {
                    "scenario": f"{row['scenario']} ({row['policy_id']})",
                    "mind": row["mind"],
                    "SampleSize": f"{row['population']} agents (seed 42)",
                    "survived_or_safe_pct": row["survival_or_safety_rate_pct"],
                    "notes": row["real_life_policy_recommendation"],
                }
            )

    summary_csv = out_path / "evacuation_survival_rates_by_scenario.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(scenario_summary[0].keys()))
        writer.writeheader()
        writer.writerows(scenario_summary)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenario_survival_summary": scenario_summary,
        "policy_interventions": policy_rows,
        "seed_catalog": seed_rows,
    }
    json_path = out_path / "evacuation_data_bundle.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # 4. Write Human-Readable Insights Report
    md_lines = [
        "# Real-Life Evacuation Survival Rates, Critical Seeds & Policy Insights",
        "",
        "## 1. Executive Summary: How Quantum vs. Classical Agents Model Real Human Evacuations",
        "- **Quantum Mind (`mind/quantum_mind.py`)**: Models human belief states as a 2-qubit density matrix (`belief` $\\otimes$ `action`). Ambiguous warnings (`tremor`, `gas_plume`, faint chlorine odour, distant steward knocks) apply non-commuting $R_y(\\theta)R_z(\\phi)$ rotations that preserve off-diagonal coherence $|x| = |\\rho_{01}|$. This produces:",
        "  1. **Disjunction / Normalcy Bias**: Under unresolved ambiguity ($p_{\\text{danger}} \\approx 0.5$), destructive interference reduces $P(\\text{protect})$ by **18%** below the classical mixture (`0.370` vs `0.550`), reproducing real-world human hesitation before evacuating.",
        "  2. **Order Effects**: Experiencing a mild cue followed by an acute cue (`tremor -> gas_plume`) boosts evacuation probability by **+14% to +17%** compared to the reverse order (`gas_plume -> tremor`).",
        "  3. **Projective Collapse via Clear Alarms**: Unambiguous signals (`eruption`, `ash_fall`, PA alarms, distress rockets) collapse off-diagonal superposition ($|x| \\to 0$), immediately aligning human response with urgent evacuation.",
        "- **Classical Mixture Control (`classical_mixture_decide`)**: Identical gates and conditional parameters ($q_S, q_D$) with coherence forced to zero ($\\lambda = 1$). Follows the Classical Law of Total Probability without interference or hesitation.",
        "- **Classical Rational Baseline (`contracts.classical_decide`)**: Deterministic argmax utility rule over physiological needs and recent events.",
        "",
        "## 2. Exported Policy Intervention Results (`evacuation_policy_interventions.csv`)",
        "| Scenario | Policy Intervention | Mind | Population | Safe / Survived | Fatalities / AEGL-2+ | Rate (%) |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in policy_rows:
        md_lines.append(
            f"| `{r['scenario']}` | `{r['policy_id']}` | `{r['mind']}` | {r['population']:,} | "
            f"{r['survived_or_safe']:,} | {r['fatalities_or_high_exposure']:,} | **{r['survival_or_safety_rate_pct']:.2f}%** |"
        )
    md_lines.extend(
        [
            "",
            "## 3. Critical Evacuation Seeds Catalog (`critical_evacuation_seeds_catalog.csv`)",
            "| Scenario | Seed | Quantum Outcome | Mixture Outcome | Classical Outcome | Q-M Divergences | Max Order Gap | Insight |",
            "|---|---:|---|---|---|---:|---:|---|",
        ]
    )
    for r in seed_rows:
        md_lines.append(
            f"| `{r['scenario']}` | `{r['seed']}` | **{r['quantum_outcome']}** ({r['quantum_cause']}) | "
            f"**{r['mixture_outcome']}** ({r['mixture_cause']}) | **{r['classical_outcome']}** ({r['classical_cause']}) | "
            f"{r['qm_action_divergences']} | {r['max_order_effect_gap']:.3f} | {r['evacuation_insight']} |"
        )

    report_md = out_path / "EVACUATION_INSIGHTS_REPORT.md"
    report_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "summary_csv": str(summary_csv.resolve()),
        "policies_csv": str(policies_csv.resolve()),
        "seeds_csv": str(seeds_csv.resolve()),
        "bundle_json": str(json_path.resolve()),
        "report_md": str(report_md.resolve()),
        "num_seed_rows": len(seed_rows),
        "num_policy_rows": len(policy_rows),
    }

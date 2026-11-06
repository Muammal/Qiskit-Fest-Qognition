"""Main Ursina Application for the 3D Front-end (gui3d).

Orchestrates screens (Hub, Config, Simulation, Ending Cut Scene), manages user inputs,
coordinates the camera, physics world, particle systems, and the background data adapter.
Includes --smoke headless offscreen execution mode.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, Optional

from ursina import (
    Entity,
    Ursina,
    camera,
    color,
    destroy,
    held_keys,
    mouse,
    window,
)

from gui3d.agent3d import Agent3D
from gui3d.cameras import CameraController
from gui3d.cinematics import EndingCutScene
from gui3d.data_source import LiveSource, ReplaySource, RunSource, other_mind
from gui3d.display import DisplayManager, configure_prc, get_default_window_size, setup_dpi_awareness
from gui3d.ending_stats import build_ending_stats
from gui3d.particles import ParticleManager
from gui3d.playback import Playback
from gui3d.screens import ConfigScreen, HubScreen
from gui3d.textures import prebake_all_assets
from gui3d.ui import ActionLogPanel, QuantumProbabilityPanel, SpeechBubble, TopHUD, WoodButton
from gui3d.world import World3D


class GameApp:
    """Primary application orchestrator."""

    def __init__(
        self,
        seed: int = 101,
        mind: str = "quantum",
        scenario: str = "volcano",
        quality: str = "high",
        replay_path: Optional[str] = None,
        smoke_mode: bool = False,
    ):
        self.seed = seed
        self.mind = mind
        self.scenario = scenario
        self.quality = quality
        self.replay_path = replay_path
        self.smoke_mode = smoke_mode

        # Initialize DPI and PRC variables before Ursina constructor
        setup_dpi_awareness()
        configure_prc(window_type="offscreen" if smoke_mode else "onscreen", msaa=4 if quality == "high" else 1)
        prebake_all_assets()

        init_w, init_h = get_default_window_size()
        self.app = Ursina(
            title="Quantum Cognition Simulation (3D)",
            size=(init_w, init_h) if not smoke_mode else (1024, 768),
            fullscreen=False,
            borderless=False,
            vsync=True,
            development_mode=False,
            window_type="offscreen" if smoke_mode else "onscreen",
        )

        window.color = color.rgb(143, 211, 244)  # Warm sky #8FD3F4
        self.display_mgr = DisplayManager(window)

        # Core rendering controllers
        self.camera_ctrl = CameraController()
        self.particle_mgr = ParticleManager(quality=self.quality)

        self.source: Optional[RunSource] = None
        self.playback: Optional[Playback] = None
        self.world_3d: Optional[World3D] = None
        self.agent_3d: Optional[Agent3D] = None

        # 2D UI Widgets
        self.top_hud: Optional[TopHUD] = None
        self.speech_bubble: Optional[SpeechBubble] = None
        self.quantum_panel: Optional[QuantumProbabilityPanel] = None
        self.action_log: Optional[ActionLogPanel] = None

        # Screens
        self.current_screen_name = "hub" if not replay_path else "sim"
        self.hub_screen: Optional[HubScreen] = None
        self.config_screen: Optional[ConfigScreen] = None
        self.ending_screen: Optional[EndingCutScene] = None

        self.show_evacuation = False
        self._smoke_frames = 0

        self.setup_events()

        if self.replay_path:
            self.start_simulation(self.seed, self.mind, horizon=36, replay_file=self.replay_path)
        elif not self.smoke_mode:
            self.show_hub()
        else:
            # Smoke test starts simulation immediately
            self.start_simulation(self.seed, self.mind, horizon=12)

    def setup_events(self) -> None:
        """Bind global input handlers."""
        def on_input(key):
            self.handle_input(key)

        self.input_handler = Entity(input=on_input, ignore_paused=True)

        def on_update():
            self.update()

        self.update_handler = Entity(update=on_update)

    def handle_input(self, key: str) -> None:
        """Central keyboard and mouse input router."""
        if key == "f11":
            self.display_mgr.toggle_fullscreen()
        elif key == "escape" or key == "h":
            if self.current_screen_name in ("config", "sim", "ending"):
                self.show_hub()
        elif key == "c":
            self.camera_ctrl.cycle_mode()
        elif key == "v":
            self.camera_ctrl.toggle_topdown()
        elif key == "e" and self.current_screen_name == "sim":
            self.show_evacuation = not self.show_evacuation
            if self.world_3d and self.playback:
                self.world_3d.update_hazards(self.playback.hazards_at(self.playback.index), show_evac=self.show_evacuation)
        elif key == "tab" and self.action_log:
            self.action_log.enabled = not self.action_log.enabled
        elif key == "space":
            if self.ending_screen and self.ending_screen.enabled:
                self.ending_screen.skip_animations()
            elif self.playback:
                self.playback.toggle_pause()
        elif key in ("n", "right") and self.playback and self.current_screen_name == "sim":
            self.playback.step_once()
        elif key == "q":
            if self.current_screen_name == "sim":
                # Switch mind and restart on identical seed
                self.mind = other_mind(self.mind)
                self.start_simulation(self.seed, self.mind, horizon=36)
            elif self.ending_screen and self.ending_screen.enabled:
                self.mind = other_mind(self.mind)
                self.start_simulation(self.seed, self.mind, horizon=36)
        elif key == "r" and (self.current_screen_name == "sim" or (self.ending_screen and self.ending_screen.enabled)):
            self.start_simulation(self.seed, self.mind, horizon=36)
        elif key == "1" and self.playback:
            self.playback.set_speed(1)
        elif key == "2" and self.playback:
            self.playback.set_speed(2)
        elif key == "3" and self.playback:
            self.playback.set_speed(3)

        self.camera_ctrl.handle_input(key)

    def show_hub(self) -> None:
        """Present Event Choice Hub."""
        self.cleanup_simulation()
        self.current_screen_name = "hub"
        if self.config_screen:
            destroy(self.config_screen)
            self.config_screen = None
        if self.ending_screen:
            destroy(self.ending_screen)
            self.ending_screen = None

        self.hub_screen = HubScreen(on_select_scenario=self.open_config)

    def open_config(self, scenario: str) -> None:
        """Open Configuration Modal."""
        self.scenario = scenario
        if self.hub_screen:
            destroy(self.hub_screen)
            self.hub_screen = None

        self.current_screen_name = "config"
        self.config_screen = ConfigScreen(
            scenario=self.scenario,
            seed=self.seed,
            mind=self.mind,
            horizon=36,
            on_start=lambda s, m, h: self.start_simulation(s, m, h),
            on_back=self.show_hub,
        )

    def start_simulation(self, seed: int, mind: str, horizon: int = 36, replay_file: Optional[str] = None) -> None:
        """Initialize and play simulation uninterrupted."""
        self.cleanup_simulation()
        self.seed = seed
        self.mind = mind
        self.current_screen_name = "sim"

        if replay_file:
            self.source = ReplaySource(replay_file, horizon=horizon)
        else:
            self.source = LiveSource(seed=seed, mind=mind, scenario=self.scenario, horizon=horizon)

        # Wait briefly for world if live
        if isinstance(self.source, LiveSource):
            self.source.wait_ready(timeout=2.0)

        world_meta = self.source.meta.world or {"tiles": [[1] * 40 for _ in range(40)]}
        self.playback = Playback(world_meta, horizon=horizon, speed=2)

        # 3D Scene construction
        self.world_3d = World3D(world_meta, quality=self.quality)
        self.agent_3d = Agent3D(pos=(0, 0.2, 0))

        # 2D HUD widgets
        self.top_hud = TopHUD()
        self.speech_bubble = SpeechBubble()
        self.quantum_panel = QuantumProbabilityPanel()
        self.action_log = ActionLogPanel()

    def cleanup_simulation(self) -> None:
        """Tear down 3D world entities and HUD."""
        if self.world_3d:
            destroy(self.world_3d)
            self.world_3d = None
        if self.agent_3d:
            destroy(self.agent_3d)
            self.agent_3d = None
        if self.top_hud:
            destroy(self.top_hud)
            self.top_hud = None
        if self.speech_bubble:
            destroy(self.speech_bubble)
            self.speech_bubble = None
        if self.quantum_panel:
            destroy(self.quantum_panel)
            self.quantum_panel = None
        if self.action_log:
            destroy(self.action_log)
            self.action_log = None
        if self.ending_screen:
            destroy(self.ending_screen)
            self.ending_screen = None
        if isinstance(self.source, LiveSource):
            self.source.cancel()

    def update(self) -> None:
        """Per-frame update loop."""
        import time
        from ursina import time as utime
        dt = utime.dt

        self.display_mgr.update()

        # Smoke test auto-termination
        if self.smoke_mode:
            self._smoke_frames += 1
            if self._smoke_frames > 30:
                print("[3D Smoke Test] Verified offscreen render loop. Exiting 0.")
                sys.exit(0)

        if self.current_screen_name == "sim" and self.source and self.playback:
            # Poll new steps from data adapter
            new_steps = self.source.poll()
            if new_steps:
                self.playback.push_steps(new_steps)

            if self.source.finished() and not self.playback.source_finished:
                self.playback.mark_source_finished(self.source.result())
                if self.source.result():
                    self.playback.set_outcome(self.source.result().get("outcome"))

            # Update playback state machine
            state = self.playback.update(dt)

            # Update character position and animation
            half_w = self.world_3d.width * 0.5
            half_h = self.world_3d.height * 0.5
            raw_el = self.world_3d.elevation[state.agent_tile[1]][state.agent_tile[0]] if self.world_3d.elevation else 0
            elev_y = max(0.0, float(raw_el)) * 0.005

            target_pos = (state.agent_pos[0] - half_w + 0.5, elev_y + 0.1, state.agent_pos[1] - half_h + 0.5)
            self.agent_3d.position = target_pos
            self.agent_3d.animate(dt, is_moving=state.moving)

            if state.moving:
                self.particle_mgr.emit_footstep_dust(self.agent_3d.position)

            # Update camera
            self.camera_ctrl.update(dt, agent_pos=target_pos)

            # Update environment and day/night lighting
            self.world_3d.update_daynight(state.hour)
            self.world_3d.sync_shelters(state.shelters)
            self.particle_mgr.update_atmospheric(dt, state.weather, state.hazards.ash, self.agent_3d.position)

            # Update HUD
            self.top_hud.update_vitals(state.needs, state.day, state.hour, state.step_index, state.horizon)
            self.quantum_panel.update_probabilities(state.probs, state.quantum)
            self.action_log.update_entries(state.recent_actions)

            # Process playback events
            for ev in self.playback.pop_events():
                if ev.kind == "step":
                    self.speech_bubble.position = self.agent_3d.position
                    self.speech_bubble.show_message(state.action, state.reason)
                elif ev.kind == "event":
                    shake = float(ev.data.get("shake", 0.0))
                    if shake > 0.01:
                        self.camera_ctrl.trigger_shake(shake)
                elif ev.kind == "finished":
                    self.trigger_ending_cutscene()

    def trigger_ending_cutscene(self) -> None:
        """Trigger the single cinematic ending presentation."""
        self.current_screen_name = "ending"
        full_timeline = self.source.result() or self.playback.world
        stats = build_ending_stats(full_timeline)

        self.ending_screen = EndingCutScene(
            stats=stats,
            camera_ctrl=self.camera_ctrl,
            particle_mgr=self.particle_mgr,
            agent_3d=self.agent_3d,
            on_replay=lambda: self.start_simulation(self.seed, self.mind, horizon=36),
            on_new_seed=lambda: self.start_simulation(random.randint(10, 999), self.mind, horizon=36),
            on_switch_mind=lambda: self.start_simulation(self.seed, other_mind(self.mind), horizon=36),
            on_main_menu=self.show_hub,
        )

    def run(self) -> None:
        self.app.run()


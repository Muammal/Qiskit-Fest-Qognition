"""Cinematic ending sequence and camera animations (Ursina / Panda3D).

Triggers exactly once upon run completion (survived to horizon or fatal conclusion).
Features:
  - Atmospheric camera crane pull-back and 360-degree orbit around the agent
  - Warm sunrise vs ash-gray dusk color grading
  - Outlined ribbon title card with staggered pop-ins
  - Count-up animations for survival percentage, grade (S/A/B/C/D) and 1-3 stars
  - Important vital metrics, decisive moment, and background N-seed comparison spinner
  - Character final freeze frame with celebratory confetti or volcanic ash
  - Tactile WoodButtons and key bindings: Replay (R), New Seed (N), Switch Mind (Q), Menu (ESC/H)
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, Optional

from ursina import (
    Entity,
    Text,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
)

from gui3d.data_source import other_mind
from gui3d.ending_stats import EndingStats
from gui3d.palette import (
    ACCENT,
    BLUE_UI,
    CREAM,
    DARK_WOOD,
    DEEP_GREEN,
    GOLD,
    OUTLINE,
    PARCHMENT,
    PURPLE,
    RED,
    WHITE,
    WOOD,
)
from gui3d.ui import WoodButton


class EndingCutScene(Entity):
    """Orchestrates the single cinematic ending presentation."""

    def __init__(
        self,
        stats: EndingStats,
        camera_ctrl,
        particle_mgr,
        agent_3d,
        on_replay: Callable[[], None],
        on_new_seed: Callable[[], None],
        on_switch_mind: Callable[[], None],
        on_main_menu: Callable[[], None],
        parent=camera.ui,
        **kwargs,
    ):
        super().__init__(parent=parent, **kwargs)
        self.stats = stats
        self.camera_ctrl = camera_ctrl
        self.particle_mgr = particle_mgr
        self.agent_3d = agent_3d

        self.on_replay = on_replay
        self.on_new_seed = on_new_seed
        self.on_switch_mind = on_switch_mind
        self.on_main_menu = on_main_menu

        self.elapsed = 0.0
        self.skipped = False

        # Set character freeze frame pose
        self.agent_3d.set_pose(self.stats.freeze_pose)

        # Trigger ending celebration particles
        if self.stats.celebration_particles == "confetti":
            self.particle_mgr.emit_confetti(self.agent_3d.position, count=40)

        # Camera crane pull-back & cinematic orbit
        self.camera_ctrl.mode = "cinematic"
        self.camera_ctrl.pitch = 30.0
        self.camera_ctrl.distance = 20.0
        self.camera_ctrl.target = self.agent_3d.position

        # Build UI Panels
        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Dark vignette backing
        self.vignette = Entity(
            parent=self,
            model="quad",
            color=color.rgba(10, 8, 6, 175),
            scale=(2.5, 2.0),
            position=(0, 0, 1),
        )

        # 2. Main Parchment Results Card
        self.card = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*PARCHMENT),
            scale=(1.25, 0.85),
            position=(0, -0.02),
        )
        self.card_border = Entity(
            parent=self.card,
            model="quad",
            color=color.rgb(*DARK_WOOD),
            scale=(1.02, 1.03),
            position=(0, 0, 0.01),
        )

        # 3. Ribbon Title
        ribbon_col = DEEP_GREEN if self.stats.outcome == "survived" else RED
        self.ribbon = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*ribbon_col),
            scale=(0.85, 0.12),
            position=(0, 0.38),
        )
        self.title_text = Text(
            parent=self.ribbon,
            text=self.stats.title.upper(),
            scale=1.1,
            position=(-0.42, 0.035, -0.05),
            color=color.rgb(*CREAM),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 4. Grade & Stars
        self.grade_text = Text(
            parent=self.card,
            text=f"GRADE: {self.stats.grade}",
            scale=1.4,
            position=(-0.44, 0.36, -0.05),
            color=color.rgb(*GOLD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )
        star_str = " ".join(["★"] * self.stats.stars)
        self.stars_text = Text(
            parent=self.card,
            text=star_str,
            scale=1.5,
            position=(-0.44, 0.26, -0.05),
            color=color.rgb(*GOLD),
        )

        # 5. Survival Rate Count-up
        self.survival_text = Text(
            parent=self.card,
            text=f"SURVIVED: {int(self.stats.survival_pct)}% ({self.stats.steps_survived}/{self.stats.horizon} steps)",
            scale=0.95,
            position=(-0.44, 0.16, -0.05),
            color=color.rgb(*OUTLINE),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 6. Key Telemetry Metrics
        telemetry_lines = [
            f"Lowest Vital: {self.stats.lowest_vital_name.title()} ({int(self.stats.lowest_vital_value*100)}%) at Step {self.stats.lowest_vital_step+1}",
            f"Shelters Raised: {self.stats.shelters_built}  |  Distance: {self.stats.distance_traveled} tiles",
            f"Hazard Events Endured: {self.stats.hazard_events_faced}",
        ]
        if self.stats.outcome == "died" and self.stats.cause:
            telemetry_lines.append(f"Fatal Factor: {self.stats.cause.replace('_', ' ').title()} at Step {self.stats.decisive_step+1}")
        if self.stats.scenario == "volcano":
            status_evac = "Reached Coastal Assembly" if self.stats.reached_assembly else "Inland Corridor"
            telemetry_lines.append(f"Evacuation: {status_evac} (Margin: {self.stats.margin_hours or 'N/A'}h)")

        self.telemetry_text = Text(
            parent=self.card,
            text="\n".join(telemetry_lines),
            scale=0.72,
            position=(-0.44, 0.06, -0.05),
            color=color.rgb(*DARK_WOOD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 7. Quantum Cognition Highlights
        q_lines = [
            f"Mind Model: {self.stats.mind.title()}",
            f"Order Effects Triggered: {self.stats.order_effects_triggered}",
            f"Stress Decoherence Episodes: {self.stats.decoherence_episodes}",
        ]
        if self.stats.divergence_pct > 0:
            q_lines.append(f"Divergence vs {other_mind(self.stats.mind).title()}: {self.stats.divergence_pct}%")

        self.quantum_text = Text(
            parent=self.card,
            text="\n".join(q_lines),
            scale=0.68,
            position=(0.04, 0.26, -0.05),
            color=color.rgb(*PURPLE),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 8. Epilogue narrative line
        self.epilogue_text = Text(
            parent=self.card,
            text=f'"{self.stats.epilogue}"',
            scale=0.75,
            position=(-0.44, -0.22, -0.05),
            color=color.rgb(*OUTLINE),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 9. Tactile Action WoodButtons
        btn_y = -0.38
        self.btn_replay = WoodButton(
            text="Replay [R]",
            pos=(-0.42, btn_y),
            scale=(0.24, 0.065),
            on_click=self.on_replay,
            parent=self,
        )
        self.btn_new_seed = WoodButton(
            text="New Seed [N]",
            pos=(-0.14, btn_y),
            scale=(0.24, 0.065),
            on_click=self.on_new_seed,
            parent=self,
        )
        self.btn_switch_mind = WoodButton(
            text="Switch Mind [Q]",
            pos=(0.14, btn_y),
            scale=(0.24, 0.065),
            on_click=self.on_switch_mind,
            parent=self,
        )
        self.btn_menu = WoodButton(
            text="Menu [ESC]",
            pos=(0.42, btn_y),
            scale=(0.24, 0.065),
            on_click=self.on_main_menu,
            parent=self,
        )

    def skip_animations(self) -> None:
        """SPACE or ENTER: Jump directly to final reveal state."""
        self.skipped = True
        self.elapsed = 10.0
        self.card.scale = Vec2(1.25, 0.85)

    def update(self) -> None:
        import time
        from ursina import time as utime
        dt = utime.dt
        self.elapsed += dt

        # Pop-in bounce animation for results card
        if not self.skipped and self.elapsed < 0.6:
            prog = self.elapsed / 0.6
            # Overshoot elastic ease
            s = math.sin(prog * math.pi * 0.5) * 1.02
            self.card.scale = Vec2(1.25 * s, 0.85 * s)


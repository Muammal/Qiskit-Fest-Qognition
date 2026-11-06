"""Screen flow controllers: Hub, Config, Simulation, and Ending Cut Scene (Ursina).

Maintains the exact same screen hierarchy and keyboard shortcuts as the 2D pygame engine:
  - Hub (Screen 0): Slowly rotating 3D diorama with wooden signboards for Island & Volcano.
  - Config (Screen 1): Parchment modal with seed stepper, mind toggle, horizon buttons, and mini map.
  - Simulation (Screen 2): Continuous, non-blocking 3D simulation with dynamic HUD and character.
  - Ending (Screen 3): Single cinematic cut scene with results reveal and epilogue.
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable, Dict, Optional, Tuple

from ursina import (
    Entity,
    Text,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
    mouse,
)

from gui3d.agent3d import Agent3D
from gui3d.cameras import CameraController
from gui3d.cinematics import EndingCutScene
from gui3d.data_source import LiveSource, ReplaySource, RunSource, other_mind
from gui3d.ending_stats import build_ending_stats
from gui3d.models import create_volcano_model
from gui3d.palette import (
    ACCENT,
    BLUE_UI,
    CREAM,
    DARK_WOOD,
    DEEP_GREEN,
    GOLD,
    GRASS,
    OUTLINE,
    PARCHMENT,
    PURPLE,
    RED,
    WHITE,
    WOOD,
)
from gui3d.particles import ParticleManager
from gui3d.playback import Playback
from gui3d.ui import ActionLogPanel, QuantumProbabilityPanel, SpeechBubble, TopHUD, WoodButton
from gui3d.world import World3D


class HubScreen(Entity):
    """Event Choice Hub: rotating 3D diorama with wooden scenario signboards."""

    def __init__(self, on_select_scenario: Callable[[str], None], parent=camera.ui, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.on_select_scenario = on_select_scenario

        # Title ribbon
        self.title_ribbon = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*DARK_WOOD),
            scale=(0.95, 0.12),
            position=(0, 0.38),
        )
        Text(
            parent=self.title_ribbon,
            text="QUANTUM COGNITION SIMULATION",
            scale=1.05,
            position=(-0.44, 0.035, -0.05),
            color=color.rgb(*GOLD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # Signboard buttons
        self.btn_island = WoodButton(
            text="Island Wilderness",
            pos=(-0.35, -0.32),
            scale=(0.35, 0.08),
            btn_color=DEEP_GREEN,
            on_click=lambda: self.on_select_scenario("island"),
            parent=self,
        )
        self.btn_volcano = WoodButton(
            text="Volcano Evacuation",
            pos=(0.35, -0.32),
            scale=(0.35, 0.08),
            btn_color=RED,
            on_click=lambda: self.on_select_scenario("volcano"),
            parent=self,
        )

        # Subtle subtext
        Text(
            parent=self,
            text="Choose an existential crisis scenario to evaluate human decision-making",
            scale=0.75,
            position=(-0.32, 0.30, -0.05),
            color=color.rgb(*CREAM),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )


class ConfigScreen(Entity):
    """Mission Configuration modal: seed selection, mind toggle, and horizon steppers."""

    def __init__(
        self,
        scenario: str,
        seed: int,
        mind: str,
        horizon: int,
        on_start: Callable[[int, str, int], None],
        on_back: Callable[[], None],
        parent=camera.ui,
        **kwargs,
    ):
        super().__init__(parent=parent, **kwargs)
        self.scenario = scenario
        self.seed = seed
        self.mind = mind
        self.horizon = horizon
        self.on_start = on_start
        self.on_back = on_back

        # Dark overlay backing
        self.overlay = Entity(
            parent=self,
            model="quad",
            color=color.rgba(15, 10, 8, 160),
            scale=(2.5, 2.0),
            position=(0, 0, 1),
        )

        # Parchment popup frame
        self.frame = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*PARCHMENT),
            scale=(1.10, 0.78),
            position=(0, 0),
        )
        Entity(
            parent=self.frame,
            model="quad",
            color=color.rgb(*DARK_WOOD),
            scale=(1.02, 1.03),
            position=(0, 0, 0.01),
        )

        # Ribbon header
        self.header = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*DARK_WOOD),
            scale=(0.75, 0.10),
            position=(0, 0.34),
        )
        scen_title = "VOLCANO EVACUATION" if scenario == "volcano" else "ISLAND WILDERNESS"
        Text(
            parent=self.header,
            text=f"{scen_title} CONFIG",
            scale=0.95,
            position=(-0.42, 0.035, -0.05),
            color=color.rgb(*GOLD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        # 1. Seed Stepper
        Text(parent=self.frame, text="SIMULATION SEED:", scale=0.8, position=(-0.44, 0.24, -0.05), color=color.rgb(*OUTLINE), font="assets/fonts/LilitaOne-Regular.ttf")
        self.seed_text = Text(parent=self.frame, text=str(self.seed), scale=0.9, position=(-0.05, 0.24, -0.05), color=color.rgb(*DARK_WOOD), font="assets/fonts/LilitaOne-Regular.ttf")
        WoodButton(text="-", pos=(0.10, 0.19), scale=(0.06, 0.05), on_click=self.dec_seed, parent=self)
        WoodButton(text="+", pos=(0.18, 0.19), scale=(0.06, 0.05), on_click=self.inc_seed, parent=self)
        WoodButton(text="RND", pos=(0.28, 0.19), scale=(0.08, 0.05), on_click=self.rnd_seed, parent=self)

        # 2. Mind Architecture Toggle
        Text(parent=self.frame, text="COGNITIVE MIND:", scale=0.8, position=(-0.44, 0.08, -0.05), color=color.rgb(*OUTLINE), font="assets/fonts/LilitaOne-Regular.ttf")
        self.btn_mind = WoodButton(text=self.mind.upper(), pos=(0.12, 0.06), scale=(0.32, 0.06), btn_color=PURPLE if self.mind == "quantum" else GOLD, on_click=self.toggle_mind, parent=self)

        # 3. Horizon Selector (12, 24, 36)
        Text(parent=self.frame, text="TIME HORIZON:", scale=0.8, position=(-0.44, -0.08, -0.05), color=color.rgb(*OUTLINE), font="assets/fonts/LilitaOne-Regular.ttf")
        self.btn_h12 = WoodButton(text="12 (24h)", pos=(-0.05, -0.06), scale=(0.14, 0.05), on_click=lambda: self.set_horizon(12), parent=self)
        self.btn_h24 = WoodButton(text="24 (48h)", pos=(0.12, -0.06), scale=(0.14, 0.05), on_click=lambda: self.set_horizon(24), parent=self)
        self.btn_h36 = WoodButton(text="36 (72h)", pos=(0.29, -0.06), scale=(0.14, 0.05), on_click=lambda: self.set_horizon(36), parent=self)

        # Action Buttons
        self.btn_back = WoodButton(text="Back [ESC]", pos=(-0.25, -0.28), scale=(0.24, 0.07), on_click=self.on_back, parent=self)
        self.btn_launch = WoodButton(text="Start Mission", pos=(0.25, -0.28), scale=(0.28, 0.07), btn_color=DEEP_GREEN, on_click=self.launch, parent=self)

    def inc_seed(self):
        self.seed += 1
        self.seed_text.text = str(self.seed)

    def dec_seed(self):
        self.seed = max(1, self.seed - 1)
        self.seed_text.text = str(self.seed)

    def rnd_seed(self):
        self.seed = random.randint(10, 999)
        self.seed_text.text = str(self.seed)

    def toggle_mind(self):
        self.mind = other_mind(self.mind)
        self.btn_mind.text = self.mind.upper()
        self.btn_mind.color = color.rgb(*(PURPLE if self.mind == "quantum" else GOLD))

    def set_horizon(self, h: int):
        self.horizon = h

    def launch(self):
        self.on_start(self.seed, self.mind, self.horizon)


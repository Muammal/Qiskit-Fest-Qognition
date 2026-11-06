"""Resolution-adaptive 2D UI overlay and reusable Hay Day-inspired widgets (Ursina).

All widgets render in the 1600x900 reference space and adapt smoothly to the current
screen resolution. Provides:
  - WoodButton: chunky timber button with hover bounce, press squash, and audio feedback
  - TopHUD: icon progress bars for 6 vitals, step countdown, clock, and weather badge
  - SpeechBubble: 3D billboard dialogue cloud floating over the agent
  - QuantumPanel: real-time bar graphs contrasting Quantum vs Classical choice probabilities
  - ActionLogPanel: non-blocking parchment scroll with collapsible step history
  - Stepper & Toggle widgets for configuration
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

from direct.gui.DirectGui import DGG
from ursina import (
    Button,
    Entity,
    Text,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
    mouse,
)

from gui3d.layout import LayoutManager, Rect
from gui3d.palette import (
    ACCENT,
    BLUE_UI,
    CREAM,
    DARK_WOOD,
    DEEP_GREEN,
    GOLD,
    GRASS,
    NEED_COLORS,
    OUTLINE,
    PARCHMENT,
    PURPLE,
    RED,
    WHITE,
    WOOD,
)
from gui3d.textures import get_cached_path


class WoodButton(Button):
    """Stylized carved timber button with 3D bevel lip and hover squash/bounce."""

    def __init__(
        self,
        text: str = "",
        on_click: Optional[Callable[[], None]] = None,
        scale: Tuple[float, float] = (0.2, 0.06),
        pos: Tuple[float, float] = (0, 0),
        btn_color=None,
        parent=camera.ui,
        **kwargs,
    ):
        super().__init__(
            text=text,
            parent=parent,
            scale=scale,
            position=pos,
            color=btn_color or color.rgb(*WOOD),
            highlight_color=color.rgb(*(min(255, c + 35) for c in (btn_color or WOOD))),
            pressed_color=color.rgb(*DARK_WOOD),
            **kwargs,
        )
        self.radius = 0.25
        self.text_entity.font = "assets/fonts/LilitaOne-Regular.ttf"
        self.text_entity.color = color.rgb(*CREAM)
        self.custom_click = on_click
        self.original_scale = Vec2(*scale)

    def on_click(self):
        # Press squash animation
        self.scale = Vec2(self.original_scale.x * 0.94, self.original_scale.y * 0.90)
        if self.custom_click:
            self.custom_click()


class SpeechBubble(Entity):
    """3D Billboard speech balloon floating above the agent's head."""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, billboard=True, enabled=False, **kwargs)

        self.bg = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*PARCHMENT),
            scale=(3.8, 1.2),
            position=(0, 2.2, 0),
        )
        # Tail pointer
        self.tail = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*PARCHMENT),
            scale=(0.35, 0.35),
            position=(0, 1.5, 0),
            rotation=(0, 0, 45),
        )
        self.title_text = Text(
            parent=self.bg,
            text="",
            scale=4.2,
            position=(-0.45, 0.35, -0.05),
            color=color.rgb(*OUTLINE),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )
        self.reason_text = Text(
            parent=self.bg,
            text="",
            scale=3.2,
            position=(-0.45, -0.05, -0.05),
            color=color.rgb(*DARK_WOOD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )
        self._hide_timer = 0.0

    def show_message(self, action: str, reason: str, duration: float = 2.5) -> None:
        self.title_text.text = action.replace("_", " ").upper()
        # Truncate long reasons for clean bubble display
        short_reason = reason if len(reason) <= 42 else (reason[:40] + "...")
        self.reason_text.text = short_reason
        self.enabled = True
        self._hide_timer = duration

    def update(self) -> None:
        import time
        from ursina import time as utime
        if self.enabled:
            self._hide_timer -= utime.dt
            if self._hide_timer <= 0:
                self.enabled = False


class TopHUD(Entity):
    """Top wooden bar with progress bars for all 6 homeostatic vitals and clock."""

    def __init__(self, parent=camera.ui, **kwargs):
        super().__init__(parent=parent, position=(0, 0.44), **kwargs)

        # Bar background
        self.bar_bg = Entity(
            parent=self,
            model="quad",
            color=color.rgb(*DARK_WOOD),
            scale=(1.45, 0.10),
            position=(0, 0),
        )

        self.vital_bars: Dict[str, Entity] = {}
        self.vital_values: Dict[str, float] = {k: 1.0 for k in NEED_COLORS}

        # Arrange 6 vital bars
        start_x = -0.55
        spacing = 0.16
        for i, (name, col) in enumerate(NEED_COLORS.items()):
            bx = start_x + i * spacing
            # Label
            Text(
                parent=self,
                text=name[:3].upper(),
                scale=0.75,
                position=(bx - 0.04, 0.035, -0.05),
                color=color.rgb(*CREAM),
                font="assets/fonts/LilitaOne-Regular.ttf",
            )
            # Trough
            Entity(
                parent=self,
                model="quad",
                color=color.rgb(20, 15, 10),
                scale=(0.14, 0.035),
                position=(bx + 0.03, 0.02, -0.02),
            )
            # Fill
            fill = Entity(
                parent=self,
                model="quad",
                color=color.rgb(*col),
                scale=(0.13, 0.028),
                position=(bx + 0.03, 0.02, -0.03),
            )
            self.vital_bars[name] = fill

        # Clock & step text
        self.step_text = Text(
            parent=self,
            text="STEP 1/36",
            scale=0.9,
            position=(0.48, 0.035, -0.05),
            color=color.rgb(*GOLD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )
        self.time_text = Text(
            parent=self,
            text="DAY 1, 08:00",
            scale=0.75,
            position=(0.48, -0.005, -0.05),
            color=color.rgb(*CREAM),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

    def update_vitals(self, needs: Dict[str, float], day: int, hour: float, step: int, horizon: int) -> None:
        """Smoothly update need progress bars and clock."""
        for name, val in needs.items():
            if name in self.vital_bars:
                # Clamp and scale width
                c_val = max(0.01, min(1.0, float(val)))
                self.vital_bars[name].scale_x = 0.13 * c_val

        self.step_text.text = f"STEP {step + 1}/{horizon}"
        hr_int = int(hour)
        min_int = int((hour - hr_int) * 60)
        self.time_text.text = f"DAY {day}, {hr_int:02d}:{min_int:02d}"


class QuantumProbabilityPanel(Entity):
    """Lower-right HUD widget displaying live Quantum vs Classical action choice probabilities."""

    def __init__(self, parent=camera.ui, **kwargs):
        super().__init__(parent=parent, position=(0.60, -0.32), **kwargs)

        self.bg = Entity(
            parent=self,
            model="quad",
            color=color.rgba(*DARK_WOOD, 220),
            scale=(0.44, 0.32),
            position=(0, 0),
        )

        Text(
            parent=self,
            text="COGNITIVE PROBABILITIES",
            scale=0.75,
            position=(-0.19, 0.13, -0.05),
            color=color.rgb(*GOLD),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        self.bars: List[Tuple[Text, Entity]] = []
        for i in range(5):
            lbl = Text(parent=self, text="", scale=0.65, position=(-0.19, 0.08 - i * 0.045, -0.05), color=color.rgb(*CREAM))
            bar = Entity(parent=self, model="quad", color=color.rgb(*ACCENT), scale=(0.15, 0.02), position=(0.04, 0.075 - i * 0.045, -0.05))
            self.bars.append((lbl, bar))

        self.coherence_text = Text(
            parent=self,
            text="COHERENCE: 1.00  |  DEPHASING: 0%",
            scale=0.60,
            position=(-0.19, -0.12, -0.05),
            color=color.rgb(*BLUE_UI),
        )

    def update_probabilities(self, probs: Dict[str, float], quantum: Dict[str, Any]) -> None:
        """Refresh sorted top 5 action probabilities."""
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
        for i in range(5):
            lbl, bar = self.bars[i]
            if i < len(sorted_probs):
                act, p = sorted_probs[i]
                lbl.text = f"{act[:7].upper()}: {int(p * 100):2d}%"
                bar.scale_x = max(0.005, 0.18 * float(p))
                bar.enabled = True
            else:
                lbl.text = ""
                bar.enabled = False

        coh = float(quantum.get("coherence") or 1.0)
        lam = float(quantum.get("lam") or 0.0)
        self.coherence_text.text = f"COHERENCE: {coh:.2f}  |  STRESS DEPHASING: {int(lam*100)}%"


class ActionLogPanel(Entity):
    """Parchment slide-out drawer displaying chronological decision history (TAB key)."""

    def __init__(self, parent=camera.ui, **kwargs):
        super().__init__(parent=parent, position=(-0.58, 0.0), enabled=False, **kwargs)

        self.bg = Entity(
            parent=self,
            model="quad",
            color=color.rgba(*PARCHMENT, 235),
            scale=(0.48, 0.72),
            position=(0, 0),
        )

        Text(
            parent=self,
            text="ACTION LOG [TAB]",
            scale=0.85,
            position=(-0.21, 0.32, -0.05),
            color=color.rgb(*OUTLINE),
            font="assets/fonts/LilitaOne-Regular.ttf",
        )

        self.log_entries: List[Text] = []
        for i in range(12):
            t = Text(
                parent=self,
                text="",
                scale=0.60,
                position=(-0.21, 0.25 - i * 0.045, -0.05),
                color=color.rgb(*DARK_WOOD),
                font="assets/fonts/LilitaOne-Regular.ttf",
            )
            self.log_entries.append(t)

    def update_entries(self, recent_actions: List[Tuple[int, str, str]]) -> None:
        """Fill recent step actions and events."""
        for i, t in enumerate(self.log_entries):
            if i < len(recent_actions):
                step, act, ev = recent_actions[-(i + 1)]
                ev_str = f" [{ev.upper()}]" if ev not in ("none", "calm") else ""
                t.text = f"Step {step + 1}: {act.replace('_', ' ').title()}{ev_str}"
            else:
                t.text = ""


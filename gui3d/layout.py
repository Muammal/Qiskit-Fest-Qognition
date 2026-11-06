"""Resolution-adaptive UI layout engine (pure logic, no Ursina imports).

All UI widgets are authored in a 1600x900 reference coordinate space and mapped to
real screen pixels or normalized device coordinates.

Scale factor:
    scale = min(width / 1600.0, height / 900.0)

Tested across 4:3 (1024x768), 16:9 (1280x720, 1920x1080, 2560x1440, 3840x2160),
and 21:9 ultrawide (3440x1440).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

REF_WIDTH = 1600.0
REF_HEIGHT = 900.0
MIN_WIDTH = 1024.0
MIN_HEIGHT = 576.0


@dataclass(frozen=True)
class Rect:
    """2D rectangle in pixels."""
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center_x(self) -> float:
        return self.x + self.w * 0.5

    @property
    def center_y(self) -> float:
        return self.y + self.h * 0.5

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def inside_bounds(self, screen_w: float, screen_h: float, margin: float = 0.0) -> bool:
        """True if rect is entirely inside the screen (within margin)."""
        return (
            self.x >= -margin
            and self.y >= -margin
            and self.right <= screen_w + margin
            and self.bottom <= screen_h + margin
        )


class LayoutManager:
    """Computes scale factor and UI widget placements for any window size."""

    def __init__(self, width: float = REF_WIDTH, height: float = REF_HEIGHT) -> None:
        self.width = max(MIN_WIDTH, float(width))
        self.height = max(MIN_HEIGHT, float(height))
        self.scale = min(self.width / REF_WIDTH, self.height / REF_HEIGHT)
        self.aspect_ratio = self.width / self.height

    def resize(self, width: float, height: float) -> None:
        self.width = max(MIN_WIDTH, float(width))
        self.height = max(MIN_HEIGHT, float(height))
        self.scale = min(self.width / REF_WIDTH, self.height / REF_HEIGHT)
        self.aspect_ratio = self.width / self.height

    def to_pixel(self, ref_val: float) -> float:
        """Scale a scalar dimension from reference space to pixel space."""
        return ref_val * self.scale

    def anchored_rect(
        self,
        ref_x: float,
        ref_y: float,
        ref_w: float,
        ref_h: float,
        anchor: str = "top_left",
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> Rect:
        """Compute pixel rect using reference dimensions and screen anchor.

        Supported anchors:
            'top_left', 'top_center', 'top_right',
            'center_left', 'center', 'center_right',
            'bottom_left', 'bottom_center', 'bottom_right'
        """
        w = ref_w * self.scale
        h = ref_h * self.scale
        ox = offset_x * self.scale
        oy = offset_y * self.scale

        if anchor == "top_left":
            x = ox
            y = oy
        elif anchor == "top_center":
            x = (self.width - w) * 0.5 + ox
            y = oy
        elif anchor == "top_right":
            x = self.width - w - ox
            y = oy
        elif anchor == "center_left":
            x = ox
            y = (self.height - h) * 0.5 + oy
        elif anchor == "center":
            x = (self.width - w) * 0.5 + ox
            y = (self.height - h) * 0.5 + oy
        elif anchor == "center_right":
            x = self.width - w - ox
            y = (self.height - h) * 0.5 + oy
        elif anchor == "bottom_left":
            x = ox
            y = self.height - h - oy
        elif anchor == "bottom_center":
            x = (self.width - w) * 0.5 + ox
            y = self.height - h - oy
        elif anchor == "bottom_right":
            x = self.width - w - ox
            y = self.height - h - oy
        else:
            x = ref_x * self.scale + ox
            y = ref_y * self.scale + oy

        return Rect(x=x, y=y, w=w, h=h)

    def get_standard_ui_rects(self) -> Dict[str, Rect]:
        """Returns standard layout rectangles for verification across resolutions."""
        return {
            # Top HUD: 1100x70 centered at top
            "top_hud": self.anchored_rect(0, 0, 1100, 70, anchor="top_center", offset_y=16),
            # Quantum/Classical panel: 340x260 at bottom-right
            "quantum_panel": self.anchored_rect(0, 0, 340, 260, anchor="bottom_right", offset_x=20, offset_y=20),
            # Action log: 380x480 at center-left
            "action_log": self.anchored_rect(0, 0, 380, 480, anchor="center_left", offset_x=20),
            # Speed/controls panel: 260x54 at bottom-left
            "controls_panel": self.anchored_rect(0, 0, 260, 54, anchor="bottom_left", offset_x=20, offset_y=20),
            # Config dialog: 720x580 centered
            "config_dialog": self.anchored_rect(0, 0, 720, 580, anchor="center"),
            # Ending cutscene results card: 960x620 centered
            "ending_dialog": self.anchored_rect(0, 0, 960, 620, anchor="center"),
        }


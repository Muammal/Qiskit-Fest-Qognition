"""Shared colour palette (pure data, no Ursina import).

All colours are (r, g, b) tuples in 0-255. Original palette - no third-party assets.
"""
from __future__ import annotations

from typing import Dict, Tuple

RGB = Tuple[int, int, int]


def hex_rgb(code: str) -> RGB:
    """Convert '#RRGGBB' to an (r, g, b) tuple."""
    code = code.lstrip("#")
    return int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)


GRASS = hex_rgb("#7CC24A")
DEEP_GREEN = hex_rgb("#3E8E3A")
SKY = hex_rgb("#8FD3F4")
WOOD = hex_rgb("#B9783F")
DARK_WOOD = hex_rgb("#6B3E1E")
PARCHMENT = hex_rgb("#F8EBC8")
ACCENT = hex_rgb("#FF8A2B")
OUTLINE = hex_rgb("#3B2312")

SAND = hex_rgb("#F2D48A")
WATER = hex_rgb("#3FA9E0")
DEEP_WATER = hex_rgb("#2477B8")
ROCK = hex_rgb("#9C8F86")
SNOW = hex_rgb("#F4F1EA")
LAVA = hex_rgb("#FF4A1C")
ASH = hex_rgb("#7A7570")
RED = hex_rgb("#E5483A")
GOLD = hex_rgb("#FFC93C")
WHITE = (255, 255, 255)
CREAM = hex_rgb("#FFF6DD")
BLUE_UI = hex_rgb("#4BA3E3")
PURPLE = hex_rgb("#8E6CEF")

#: Tile code -> base colour (mirrors engine.world tile codes 0..4).
TILE_COLORS: Dict[int, RGB] = {
    0: WATER,
    1: GRASS,
    2: DEEP_GREEN,
    3: ROCK,
    4: WOOD,
}

#: Need -> bar colour for the HUD.
NEED_COLORS: Dict[str, RGB] = {
    "hunger": ACCENT,
    "thirst": BLUE_UI,
    "warmth": RED,
    "energy": GOLD,
    "safety": DEEP_GREEN,
    "morale": PURPLE,
}

#: Action -> timeline strip colour.
ACTION_COLORS: Dict[str, RGB] = {
    "forage": GRASS,
    "drink": BLUE_UI,
    "build_shelter": WOOD,
    "rest": PURPLE,
    "explore": GOLD,
    "craft": DARK_WOOD,
    "hide": RED,
}

#: Day/night key-frames: hour -> (sky rgb, sun rgb, ambient rgb, sun intensity 0..1).
DAYNIGHT_KEYS = [
    (0, (24, 34, 74), (90, 110, 190), (50, 60, 110), 0.15),
    (5, (60, 60, 110), (150, 120, 170), (80, 80, 120), 0.25),
    (7, (255, 190, 140), (255, 190, 120), (170, 140, 120), 0.65),
    (12, SKY, (255, 248, 225), (175, 185, 190), 1.0),
    (17, (255, 200, 140), (255, 200, 140), (170, 150, 130), 0.8),
    (19, (250, 130, 80), (255, 140, 70), (150, 110, 100), 0.55),
    (21, (40, 50, 100), (110, 120, 200), (60, 70, 120), 0.2),
    (24, (24, 34, 74), (90, 110, 190), (50, 60, 110), 0.15),
]


def lerp_rgb(a: RGB, b: RGB, t: float) -> RGB:
    """Linear interpolation between two colours."""
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def daynight(hour: float):
    """Return (sky, sun, ambient, intensity) for a fractional hour in [0, 24)."""
    hour = hour % 24.0
    for (h0, s0, u0, a0, i0), (h1, s1, u1, a1, i1) in zip(DAYNIGHT_KEYS, DAYNIGHT_KEYS[1:]):
        if h0 <= hour <= h1:
            t = (hour - h0) / max(1e-6, h1 - h0)
            return lerp_rgb(s0, s1, t), lerp_rgb(u0, u1, t), lerp_rgb(a0, a1, t), i0 + (i1 - i0) * t
    k = DAYNIGHT_KEYS[0]
    return k[1], k[2], k[3], k[4]


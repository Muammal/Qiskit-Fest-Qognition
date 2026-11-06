"""Procedural texture and 2D UI asset generator (Pillow).

Generates original, stylized, Hay Day-inspired UI textures, icons, and material maps:
carved timber frames, warm parchment panels, glossy progress bars, and soft blob shadows.
All generated art is cached in ``gui3d/assets_cache/``.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFilter

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
    SAND,
    WATER,
    WHITE,
    WOOD,
)

CACHE_DIR = Path(__file__).resolve().parent / "assets_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.png"


def create_blob_shadow(size: int = 128) -> Path:
    """Soft elliptical radial shadow for character and buildings."""
    path = get_cached_path("blob_shadow")
    if path.exists():
        return path

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r_x, r_y = size * 0.44, size * 0.32

    for r in range(int(max(r_x, r_y)), 0, -1):
        alpha = int(140 * (1.0 - (r / max(r_x, r_y)) ** 1.5))
        rx = int(r_x * (r / max(r_x, r_y)))
        ry = int(r_y * (r / max(r_x, r_y)))
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(20, 10, 5, alpha))

    img = img.filter(ImageFilter.GaussianBlur(radius=size // 32))
    img.save(path)
    return path


def create_wood_panel_texture(w: int = 256, h: int = 128, name: str = "wood_panel") -> Path:
    """Carved timber panel with beveled borders and brass corner rivets."""
    path = get_cached_path(f"{name}_{w}_{h}")
    if path.exists():
        return path

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base carved timber
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=16, fill=WOOD, outline=OUTLINE, width=4)
    # Inner bevel
    draw.rounded_rectangle([4, 4, w - 5, h - 5], radius=12, outline=DARK_WOOD, width=3)
    # Highlight rim
    draw.line([16, 6, w - 17, 6], fill=(240, 180, 110, 200), width=2)

    # Brass corner rivets
    rivet_r = max(3, min(w, h) // 18)
    for cx, cy in [(14, 14), (w - 15, 14), (14, h - 15), (w - 15, h - 15)]:
        draw.ellipse([cx - rivet_r, cy - rivet_r, cx + rivet_r, cy + rivet_r], fill=GOLD, outline=OUTLINE, width=2)
        draw.point((cx - 1, cy - 1), fill=WHITE)

    img.save(path)
    return path


def create_parchment_panel_texture(w: int = 256, h: int = 128, name: str = "parchment_panel") -> Path:
    """Warm parchment panel for dialogue, action logs, and debrief statistics."""
    path = get_cached_path(f"{name}_{w}_{h}")
    if path.exists():
        return path

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=PARCHMENT, outline=DARK_WOOD, width=3)
    draw.rounded_rectangle([3, 3, w - 4, h - 4], radius=11, outline=CREAM, width=2)

    # Subtle warmth gradient/noise
    img.save(path)
    return path


def create_progress_bar_textures() -> Tuple[Path, Path]:
    """Generates wood trough background and glossy progress bar fill."""
    trough_path = get_cached_path("bar_trough")
    fill_path = get_cached_path("bar_fill")

    if not trough_path.exists():
        img = Image.new("RGBA", (180, 24), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, 179, 23], radius=10, fill=DARK_WOOD, outline=OUTLINE, width=2)
        draw.rounded_rectangle([2, 2, 177, 21], radius=8, fill=(30, 20, 15, 220))
        img.save(trough_path)

    if not fill_path.exists():
        img = Image.new("RGBA", (180, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, 179, 19], radius=8, fill=WHITE)
        # Specular gloss strip
        draw.line([6, 3, 173, 3], fill=(255, 255, 255, 180), width=2)
        img.save(fill_path)

    return trough_path, fill_path


def create_icon_textures() -> Dict[str, Path]:
    """Generates clean, cute 64x64 vector-style icons for all 6 vitals and survival actions."""
    icons: Dict[str, Path] = {}
    defs = {
        "hunger": (ACCENT, "bread"),
        "thirst": (BLUE_UI, "drop"),
        "warmth": (RED, "flame"),
        "energy": (GOLD, "bolt"),
        "safety": (DEEP_GREEN, "shield"),
        "morale": (PURPLE, "heart"),
        "quantum": (GOLD, "atom"),
        "star": (GOLD, "star"),
        "skull": (RED, "skull"),
    }

    for name, (col, shape) in defs.items():
        p = get_cached_path(f"icon_{name}")
        icons[name] = p
        if p.exists():
            continue

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = 32, 32

        # Outer cute badge
        draw.ellipse([2, 2, 61, 61], fill=col, outline=OUTLINE, width=3)
        draw.arc([6, 6, 57, 57], 200, 340, fill=WHITE, width=2)

        # Inner symbol
        if shape == "heart":
            draw.polygon([(cx, cy + 14), (cx - 12, cy - 2), (cx - 6, cy - 12), (cx, cy - 6), (cx + 6, cy - 12), (cx + 12, cy - 2)], fill=WHITE)
        elif shape == "drop":
            draw.polygon([(cx, cy - 14), (cx - 10, cy + 6), (cx + 10, cy + 6)], fill=WHITE)
            draw.ellipse([cx - 10, cy - 2, cx + 10, cy + 14], fill=WHITE)
        elif shape == "flame":
            draw.polygon([(cx, cy - 14), (cx - 8, cy + 2), (cx - 4, cy + 12), (cx + 4, cy + 12), (cx + 8, cy + 2)], fill=WHITE)
            draw.ellipse([cx - 4, cy + 2, cx + 4, cy + 10], fill=GOLD)
        elif shape == "bolt":
            draw.polygon([(cx + 2, cy - 14), (cx - 8, cy - 1), (cx, cy - 1), (cx - 3, cy + 14), (cx + 8, cy + 1), (cx, cy + 1)], fill=WHITE)
        elif shape == "shield":
            draw.polygon([(cx - 12, cy - 12), (cx + 12, cy - 12), (cx + 10, cy + 4), (cx, cy + 14), (cx - 10, cy + 4)], fill=WHITE)
        elif shape == "star":
            draw.polygon([(cx, cy - 14), (cx + 4, cy - 4), (cx + 14, cy - 4), (cx + 6, cy + 2), (cx + 10, cy + 12),
                          (cx, cy + 6), (cx - 10, cy + 12), (cx - 6, cy + 2), (cx - 14, cy - 4), (cx - 4, cy - 4)], fill=WHITE)
        else:
            draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=WHITE)

        img.save(p)

    return icons


def prebake_all_assets() -> None:
    """Ensure all required procedural textures and icons exist in cache."""
    create_blob_shadow(128)
    create_wood_panel_texture(320, 180, "wood_card")
    create_parchment_panel_texture(400, 300, "parchment_dialog")
    create_progress_bar_textures()
    create_icon_textures()


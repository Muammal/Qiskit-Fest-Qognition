"""engine/assets.py - Cached Asset Loader & Scale Manager.
Loads procedural or drop-in CC0 sprites with .convert_alpha(), caching
downscaled surfaces per scale factor so assets are sharp and resolution-adaptive.
"""

import os
from typing import Dict, Tuple, Optional
import pygame

from engine.display import Display

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


class AssetManager:
    """Manages sprite loading and scale-keyed caching for smooth downscaling."""

    _raw_surfaces: Dict[str, pygame.Surface] = {}
    _scaled_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}

    @classmethod
    def get_image(cls, relative_path: str) -> Optional[pygame.Surface]:
        if relative_path not in cls._raw_surfaces:
            full_path = os.path.join(ASSETS_DIR, relative_path)
            if not os.path.exists(full_path):
                return None
            try:
                surf = pygame.image.load(full_path)
                cls._raw_surfaces[relative_path] = surf.convert_alpha()
            except Exception:
                return None
        return cls._raw_surfaces[relative_path]

    @classmethod
    def get_scaled_image(cls, relative_path: str, base_w: int, base_h: int) -> Optional[pygame.Surface]:
        target_w = Display.S(base_w)
        target_h = Display.S(base_h)
        key = (relative_path, target_w, target_h)

        if key in cls._scaled_cache:
            return cls._scaled_cache[key]

        raw = cls.get_image(relative_path)
        if raw is None:
            return None

        scaled = pygame.transform.smoothscale(raw, (target_w, target_h))
        cls._scaled_cache[key] = scaled
        return scaled

    @classmethod
    def get_agent_frame(cls, frame_name: str, base_size: int = 40) -> Optional[pygame.Surface]:
        """Extracts and scales a frame from the agent spritesheet (idle, walk, hurt, happy, fallen)."""
        sheet = cls.get_image(os.path.join("sprites", "agent_sheet.png"))
        if sheet is None:
            return None

        frame_idx = {"idle": 0, "walk": 1, "hurt": 2, "happy": 3, "fallen": 4}.get(frame_name, 0)
        target_size = Display.S(base_size)
        key = (f"agent_{frame_name}", target_size, target_size)

        if key in cls._scaled_cache:
            return cls._scaled_cache[key]

        frame_surf = pygame.Surface((128, 128), pygame.SRCALPHA)
        frame_surf.blit(sheet, (0, 0), pygame.Rect(frame_idx * 128, 0, 128, 128))
        scaled = pygame.transform.smoothscale(frame_surf, (target_size, target_size))
        cls._scaled_cache[key] = scaled
        return scaled

    @classmethod
    def clear_cache(cls):
        cls._scaled_cache.clear()


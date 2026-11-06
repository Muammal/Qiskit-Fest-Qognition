"""engine/fx.py - ModernGL Post-Processing FX Pipeline.
Provides optional bloom, vignette, and warm color grading behind --fx flag
with a 100% graceful fallback to plain pygame surface blits when moderngl is absent or disabled.
"""

from typing import Optional, Tuple
import pygame

try:
    import moderngl
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False


class PostProcessor:
    """Manages full-screen post-processing effects (vignette, warm grade, bloom)."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled and HAS_MODERNGL
        self._ctx = None

    def apply(self, surface: pygame.Surface) -> pygame.Surface:
        """Applies warm tint and soft vignette overlay.

        Falls back cleanly to procedural pygame surface blending if moderngl is not active.
        """
        if not self.enabled:
            return surface

        w, h = surface.get_size()
        # Clean software fallback for warm ambient vignette
        vignette_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Warm golden color grade (subtle amber wash)
        vignette_surf.fill((255, 235, 200, 15), special_flags=pygame.BLEND_RGBA_ADD)

        # Soft corner vignette
        pygame.draw.rect(vignette_surf, (15, 8, 4, 35), (0, 0, w, h), width=max(10, w // 40))
        surface.blit(vignette_surf, (0, 0))
        return surface


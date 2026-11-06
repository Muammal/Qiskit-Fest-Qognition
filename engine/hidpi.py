"""Sharp text on a fixed logical canvas.

Everything in the GUI is laid out in 1600x900 logical units. Shapes are drawn on that
canvas and scaled to the window, but text is not: a blit of text is only recorded, and
when the frame is composed the text is rendered again at round(size * scale) at its
final position. So layout code keeps its logical numbers, and text stays crisp at any
window size.

A shape or surface drawn over recorded text removes that text, so a modal hides what is
behind it. Text drawn onto any other surface, or clipped, is an ordinary blit.
"""
import sys

import pygame

LOGICAL_W, LOGICAL_H = 1600, 900
_CACHE_LIMIT = 6000


def setup_dpi_awareness():
    """Ask Windows for real pixels, so the OS does not blur a scaled window."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def window_fit(window_w, window_h):
    """(scale, offset_x, offset_y, scaled_w, scaled_h) for the letterboxed canvas."""
    scale = min(window_w / LOGICAL_W, window_h / LOGICAL_H)
    scaled_w, scaled_h = int(LOGICAL_W * scale), int(LOGICAL_H * scale)
    return scale, (window_w - scaled_w) // 2, (window_h - scaled_h) // 2, scaled_w, scaled_h


def scale_sprite(surface, factor):
    """Integer nearest-neighbour scaling, which keeps pixel art hard-edged."""
    factor = max(1, int(factor))
    if factor == 1:
        return surface
    return pygame.transform.scale(surface, (surface.get_width() * factor, surface.get_height() * factor))


def scale_shapes(canvas, scaled_w, scaled_h):
    """Scale the logical canvas: integer nearest-neighbour first, then a smooth fit for what is left."""
    factor = int(min(scaled_w / canvas.get_width(), scaled_h / canvas.get_height()))
    source = scale_sprite(canvas, factor)
    if source.get_size() == (scaled_w, scaled_h):
        return source
    return pygame.transform.smoothscale(source, (scaled_w, scaled_h))


class TextSurface(pygame.Surface):
    """A rendered string that remembers enough to be rendered again at another size."""
    font = None
    text = ""
    color = (0, 0, 0)
    antialias = True


class ScaledFont:
    """Font with logical metrics that can also render at round(size * scale)."""

    def __init__(self, names, size, bold=False):
        self.names, self.logical_size, self.bold = names, size, bold
        self.base = pygame.font.SysFont(names, size, bold=bold)
        self._sized = {size: self.base}
        self._logical_cache = {}
        self._hires_cache = {}

    def __getattr__(self, name):
        return getattr(self.base, name)

    def size(self, text):
        return self.base.size(text)

    def render(self, text, antialias=True, color=(0, 0, 0), background=None):
        key = (text, antialias, tuple(color), background)
        cached = self._logical_cache.get(key)
        if cached is not None:
            return cached
        plain = self.base.render(text, antialias, color, background)
        surface = TextSurface(plain.get_size(), pygame.SRCALPHA)
        surface.blit(plain, (0, 0))
        surface.font, surface.text, surface.color, surface.antialias = self, text, tuple(color), antialias
        if len(self._logical_cache) > _CACHE_LIMIT:
            self._logical_cache.clear()
        self._logical_cache[key] = surface
        return surface

    def pixel_size(self, scale):
        return max(1, round(self.logical_size * scale))

    def hires(self, surface, scale):
        pixels = self.pixel_size(scale)
        key = (surface.text, surface.antialias, surface.color, pixels)
        cached = self._hires_cache.get(key)
        if cached is not None:
            return cached
        font = self._sized.get(pixels)
        if font is None:
            font = self._sized[pixels] = pygame.font.SysFont(self.names, pixels, bold=self.bold)
        rendered = font.render(surface.text, surface.antialias, surface.color)
        if len(self._hires_cache) > _CACHE_LIMIT:
            self._hires_cache.clear()
        self._hires_cache[key] = rendered
        return rendered


class UICanvas(pygame.Surface):
    """The logical canvas. Records text instead of drawing it when `defer_text` is on."""
    defer_text = False
    text_layer = ()

    def begin_frame(self, scale):
        self.defer_text = scale != 1.0
        self.text_layer = []

    def blit(self, source, dest, area=None, special_flags=0):
        if self.defer_text and isinstance(source, TextSurface) and area is None and not special_flags and source.font is not None:
            position = dest.topleft if isinstance(dest, pygame.Rect) else (dest[0], dest[1])
            rect = pygame.Rect(position, source.get_size())
            if self.get_clip().contains(rect):
                self.text_layer.append((source, position))
                return rect
        result = super().blit(source, dest, area, special_flags)
        if self.text_layer and not isinstance(source, TextSurface):
            self.cover(result)
        return result

    def fill(self, color, rect=None, special_flags=0):
        if rect is None:
            result = super().fill(color, None, special_flags)
            if self.text_layer:
                self.text_layer = []
            return result
        result = super().fill(color, rect, special_flags)
        self.cover(result)
        return result

    def cover(self, rect):
        """Drop recorded text that lies under a shape drawn after it."""
        if self.text_layer:
            rect = pygame.Rect(rect)
            self.text_layer = [(s, p) for s, p in self.text_layer if not rect.contains(pygame.Rect(p, s.get_size()))]

    def text_rects(self, scale):
        """Where recorded text lands, in window pixels before any letterbox offset. For layout tests."""
        out = []
        for surface, (x, y) in self.text_layer:
            w, h = surface.font.hires(surface, scale).get_size()
            out.append((surface.text, pygame.Rect(round(x * scale), round(y * scale), w, h)))
        return out


def compose(canvas, target):
    """Draw the finished frame on `target`, letterboxed, with text rendered at the final size."""
    scale, offset_x, offset_y, scaled_w, scaled_h = window_fit(*target.get_size())
    target.fill((5, 8, 15))
    target.blit(canvas if scale == 1.0 else scale_shapes(canvas, scaled_w, scaled_h), (offset_x, offset_y))
    for surface, (x, y) in canvas.text_layer:
        target.blit(surface.font.hires(surface, scale), (offset_x + round(x * scale), offset_y + round(y * scale)))
    return scale

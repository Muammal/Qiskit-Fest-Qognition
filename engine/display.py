"""engine/display.py - Resolution-Adaptive Display Foundation.
Supports seamless windowed and fullscreen rendering across 4:3, 16:9, and 21:9 displays
without canvas distortion, hardcoded pixel values, or blurry stretching.
"""

import sys
import ctypes
from typing import Tuple, Optional
import pygame

REFERENCE_WIDTH = 1600
REFERENCE_HEIGHT = 900
MIN_WIDTH = 1024
MIN_HEIGHT = 576


def setup_dpi_awareness():
    """Configures OS DPI awareness on Windows before pygame display initialization."""
    if sys.platform == "win32":
        try:
            # SetProcessDpiAwareness(1) -> PROCESS_SYSTEM_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


class Display:
    """Resolution-adaptive display manager that tracks native window size,

    quantized design scale factor, and debounced window resize events.
    """

    _scale: float = 1.0

    @classmethod
    def S(cls, val: float) -> int:
        """Scales a reference 1600x900 design value by the current display scale factor."""
        return max(1, int(round(val * cls._scale)))

    @classmethod
    def get_scale(cls) -> float:
        return cls._scale

    def __init__(self, title: str = "Quantum Cognition Simulation"):
        setup_dpi_awareness()
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        # Determine initial window size (~85% of primary desktop size)
        desktop_sizes = pygame.display.get_desktop_sizes()
        if desktop_sizes and len(desktop_sizes) > 0:
            desk_w, desk_h = desktop_sizes[0]
            initial_w = max(MIN_WIDTH, min(1600, int(desk_w * 0.85)))
            initial_h = max(MIN_HEIGHT, min(900, int(desk_h * 0.85)))
        else:
            initial_w, initial_h = 1366, 768

        self.window_w = initial_w
        self.window_h = initial_h
        self.saved_windowed_size = (initial_w, initial_h)
        self.is_fullscreen = False
        self.render_scale = 1.0
        self.title = title

        # Auto performance valve: render at 0.75x if screen width > 3000px
        if self.window_w > 3000:
            self.render_scale = 0.75

        # Initialize resizable display surface
        self.window_surface = pygame.display.set_mode(
            (self.window_w, self.window_h),
            pygame.RESIZABLE
        )
        pygame.display.set_caption(self.title)

        # Offscreen render canvas for render_scale < 1.0
        self._recompute_scale()
        self._rebuild_canvas()

        # Resize debouncing state (~150 ms)
        self._pending_resize_size: Optional[Tuple[int, int]] = None
        self._resize_timer: float = 0.0

    def _recompute_scale(self):
        """Quantizes scale factor to increments of 0.05 against 1600x900 design reference."""
        raw_scale = min(self.window_w / REFERENCE_WIDTH, self.window_h / REFERENCE_HEIGHT)
        quantized = round(raw_scale * 20.0) / 20.0
        Display._scale = max(0.5, quantized)

    def _rebuild_canvas(self):
        """Builds or resizes the active render canvas."""
        if abs(self.render_scale - 1.0) < 0.01:
            self.canvas = self.window_surface
        else:
            cw = max(MIN_WIDTH, int(self.window_w * self.render_scale))
            ch = max(MIN_HEIGHT, int(self.window_h * self.render_scale))
            self.canvas = pygame.Surface((cw, ch)).convert()

    def toggle_fullscreen(self):
        """Toggles native borderless fullscreen and restores previous windowed dimensions."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.saved_windowed_size = (self.window_w, self.window_h)
            desktop_sizes = pygame.display.get_desktop_sizes()
            if desktop_sizes:
                native_w, native_h = desktop_sizes[0]
            else:
                native_w, native_h = 1920, 1080
            self.window_surface = pygame.display.set_mode((native_w, native_h), pygame.FULLSCREEN)
            self.window_w, self.window_h = native_w, native_h
        else:
            self.window_w, self.window_h = self.saved_windowed_size
            self.window_surface = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

        self._recompute_scale()
        self._rebuild_canvas()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Processes display-level events (F11 fullscreen toggle and window resizing)."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.toggle_fullscreen()
            return True
        elif event.type == pygame.VIDEORESIZE:
            new_w = max(MIN_WIDTH, event.w)
            new_h = max(MIN_HEIGHT, event.h)
            self._pending_resize_size = (new_w, new_h)
            self._resize_timer = 0.150  # 150 ms debounce
            return True
        return False

    def update_resize_debounce(self, dt: float) -> bool:
        """Returns True if a debounced resize was completed and scale caches should rebuild."""
        if self._pending_resize_size is not None:
            self._resize_timer -= dt
            if self._resize_timer <= 0:
                new_w, new_h = self._pending_resize_size
                self._pending_resize_size = None
                self.window_w, self.window_h = new_w, new_h
                self.window_surface = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                self._recompute_scale()
                self._rebuild_canvas()
                return True
        return False

    def get_virtual_mouse_pos(self, real_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Translates real window mouse coordinates to offscreen canvas coordinates."""
        if self.canvas is self.window_surface:
            return real_pos
        rx = real_pos[0] * (self.canvas.get_width() / self.window_w)
        ry = real_pos[1] * (self.canvas.get_height() / self.window_h)
        return int(rx), int(ry)

    def present(self):
        """Presents the active canvas to the window surface and flips the display buffer."""
        if self.canvas is not self.window_surface:
            pygame.transform.smoothscale(self.canvas, (self.window_w, self.window_h), self.window_surface)
        pygame.display.flip()

    @property
    def width(self) -> int:
        return self.canvas.get_width()

    @property
    def height(self) -> int:
        return self.canvas.get_height()


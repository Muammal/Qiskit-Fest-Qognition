"""Resolution-adaptive display and window configuration (Ursina / Panda3D).

Sets Windows DPI awareness, configures Panda3D PRC variables before window initialization
(MSAA 4x, anisotropic filtering, mipmapping, window dimensions), handles F11 fullscreen
toggling, and dispatches debounced resize callbacks.
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
from typing import Callable, List, Optional, Tuple

from gui3d.layout import LayoutManager, MIN_HEIGHT, MIN_WIDTH, REF_HEIGHT, REF_WIDTH


def setup_dpi_awareness() -> None:
    """Enable high-DPI scaling on Windows so the window renders at native pixel resolution."""
    if sys.platform != "win32":
        return
    try:
        # Per-monitor DPI aware (v2 / v1)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_default_window_size() -> Tuple[int, int]:
    """Computes initial window dimensions at ~85% of desktop size, capped to 1920x1080."""
    w, h = 1366, 768
    try:
        import screeninfo
        monitors = screeninfo.get_monitors()
        if monitors:
            m = next((mon for mon in monitors if mon.is_primary), monitors[0])
            w = int(m.width * 0.85)
            h = int(m.height * 0.85)
    except Exception:
        pass
    w = max(int(MIN_WIDTH), min(1920, w))
    h = max(int(MIN_HEIGHT), min(1080, h))
    return w, h


def configure_prc(window_type: str = "onscreen", msaa: int = 4) -> None:
    """Pre-loads Panda3D PRC settings before Ursina or ShowBase are instantiated."""
    from panda3d.core import loadPrcFileData

    loadPrcFileData("", "notify-level-util error")
    loadPrcFileData("", "notify-level-gobj error")
    loadPrcFileData("", "notify-level-display error")
    loadPrcFileData("", "textures-auto-power-2 #t")
    loadPrcFileData("", "textures-power-2 down")

    # Anisotropic filtering & mipmapping
    loadPrcFileData("", "texture-anisotropic-degree 4")
    loadPrcFileData("", "texture-minfilter linear-mipmap-linear")
    loadPrcFileData("", "texture-magfilter linear")

    # Anti-aliasing (MSAA)
    if msaa > 1:
        loadPrcFileData("", f"framebuffer-multisample 1")
        loadPrcFileData("", f"multisamples {msaa}")

    # Synchronize video / vsync
    loadPrcFileData("", "sync-video 1")

    # Allow resizable windows
    loadPrcFileData("", "win-fixed-size 0")


class DisplayManager:
    """Manages window resizing, fullscreen state, and layout debouncing."""

    def __init__(self, app_window=None) -> None:
        self.window = app_window
        self.layout = LayoutManager(REF_WIDTH, REF_HEIGHT)
        self.is_fullscreen = False
        self.windowed_size: Tuple[int, int] = get_default_window_size()
        self._last_resize_time = 0.0
        self._pending_resize = False
        self._resize_callbacks: List[Callable[[float, float, float], None]] = []

    def register_resize_callback(self, cb: Callable[[float, float, float], None]) -> None:
        """Register a callback: cb(width, height, scale_factor)."""
        self._resize_callbacks.append(cb)

    def toggle_fullscreen(self) -> None:
        """F11: Toggles between native fullscreen and saved windowed size."""
        if not self.window:
            return
        from panda3d.core import WindowProperties
        from direct.showbase.ShowBaseGlobal import base

        wp = WindowProperties()
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            # Store windowed size
            size = base.win.getSize()
            self.windowed_size = (size.getX(), size.getY())
            wp.setFullscreen(True)
        else:
            wp.setFullscreen(False)
            wp.setSize(*self.windowed_size)

        base.win.requestProperties(wp)
        self.trigger_resize()

    def on_window_event(self) -> None:
        """Called on Panda3D window-event."""
        self._last_resize_time = time.time()
        self._pending_resize = True

    def update(self) -> None:
        """Debounce resize handling (~150 ms delay after last window event)."""
        if self._pending_resize and (time.time() - self._last_resize_time) > 0.150:
            self._pending_resize = False
            self.trigger_resize()

    def trigger_resize(self) -> None:
        """Apply current window dimensions to layout and invoke registered callbacks."""
        try:
            from direct.showbase.ShowBaseGlobal import base
            size = base.win.getSize()
            w, h = size.getX(), size.getY()
        except Exception:
            w, h = int(self.layout.width), int(self.layout.height)

        w = max(int(MIN_WIDTH), w)
        h = max(int(MIN_HEIGHT), h)
        self.layout.resize(w, h)

        for cb in self._resize_callbacks:
            try:
                cb(w, h, self.layout.scale)
            except Exception:
                pass


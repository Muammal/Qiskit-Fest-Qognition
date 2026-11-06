"""engine/ui_kit.py - Hay Day-Inspired Design System & UI Components.
Features warm, chunky, beveled wood panels, parchment cards, ribbons,
outlined text, tweened progress bars, and animated buttons with squash & overshoot.
"""

import os
import math
from typing import Tuple, Dict, Any, Optional, List, Callable
import pygame
import pytweening

from engine.display import Display

# -----------------------------------------------------------------------------
# Color Palette Constants (Hay Day Farm / Wilderness Style)
# -----------------------------------------------------------------------------
COLOR_GRASS = (124, 194, 74)         # #7CC24A
COLOR_DEEP_GREEN = (62, 142, 58)     # #3E8E3A
COLOR_SKY = (143, 211, 244)          # #8FD3F4
COLOR_WOOD = (185, 120, 63)          # #B9783F
COLOR_DARK_WOOD = (107, 62, 30)      # #6B3E1E
COLOR_PARCHMENT = (248, 235, 200)    # #F8EBC8
COLOR_ACCENT_ORANGE = (255, 138, 43) # #FF8A2B
COLOR_OUTLINE_BROWN = (59, 35, 18)   # #3B2312
COLOR_CREAM = (255, 253, 245)        # #FFFDF5
COLOR_GOLD = (255, 204, 0)           # #FFCC00
COLOR_GOLD_DARK = (212, 143, 0)      # #D48F00
COLOR_RED = (235, 65, 55)            # #EB4137
COLOR_PURPLE = (150, 70, 210)        # #9646D2
COLOR_BLUE = (50, 140, 225)          # #328CE1
COLOR_WHITE = (255, 255, 255)
COLOR_SHADOW = (20, 10, 5, 120)

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "LilitaOne-Regular.ttf")


class FontManager:
    """Caches rendered fonts at specific on-screen pixel sizes and scales."""
    _fonts: Dict[Tuple[str, int], pygame.font.Font] = {}

    @classmethod
    def get_font(cls, size: int) -> pygame.font.Font:
        scaled_size = Display.S(size)
        key = (FONT_PATH, scaled_size)
        if key not in cls._fonts:
            if os.path.exists(FONT_PATH):
                try:
                    cls._fonts[key] = pygame.font.Font(FONT_PATH, scaled_size)
                except Exception:
                    cls._fonts[key] = pygame.font.SysFont("Verdana", scaled_size, bold=True)
            else:
                cls._fonts[key] = pygame.font.SysFont("Verdana", scaled_size, bold=True)
        return cls._fonts[key]

    @classmethod
    def clear_cache(cls):
        cls._fonts.clear()


class OutlinedText:
    """Renders text with a thick dark outline and subtle drop shadow."""
    _cache: Dict[Tuple[str, int, Tuple[int, int, int], Tuple[int, int, int], int], pygame.Surface] = {}

    @classmethod
    def render(
        cls,
        text: str,
        size: int,
        color: Tuple[int, int, int] = COLOR_CREAM,
        outline_color: Tuple[int, int, int] = COLOR_OUTLINE_BROWN,
        outline_thickness: int = 3,
        shadow_offset: int = 2
    ) -> pygame.Surface:
        scaled_thick = max(1, Display.S(outline_thickness))
        scaled_shadow = max(1, Display.S(shadow_offset))
        key = (text, size, color, outline_color, scaled_thick)
        if key in cls._cache:
            return cls._cache[key]

        font = FontManager.get_font(size)
        fg_surface = font.render(text, True, color)
        outline_surface = font.render(text, True, outline_color)

        w = fg_surface.get_width() + scaled_thick * 2 + scaled_shadow
        h = fg_surface.get_height() + scaled_thick * 2 + scaled_shadow
        surface = pygame.Surface((w, h), pygame.SRCALPHA)

        # Draw drop shadow
        shadow_surf = font.render(text, True, (25, 12, 5))
        surface.blit(shadow_surf, (scaled_thick + scaled_shadow, scaled_thick + scaled_shadow))

        # Draw thick 8-direction outline
        for dx in range(-scaled_thick, scaled_thick + 1):
            for dy in range(-scaled_thick, scaled_thick + 1):
                if dx * dx + dy * dy <= scaled_thick * scaled_thick:
                    surface.blit(outline_surface, (scaled_thick + dx, scaled_thick + dy))

        # Blit primary colored foreground text
        surface.blit(fg_surface, (scaled_thick, scaled_thick))

        if len(cls._cache) > 250:
            cls._cache.clear()
        cls._cache[key] = surface
        return surface


class NineSlicePanel:
    """Renders resizable wood frames, parchment cards, and ribbon banners

    with procedural woodgrain bevels and corner rivets.
    """

    @staticmethod
    def draw_wood_frame(surface: pygame.Surface, rect: pygame.Rect, corner_radius: int = 16):
        r = Display.S(corner_radius)
        # Drop shadow
        shadow_rect = rect.move(0, Display.S(6))
        pygame.draw.rect(surface, (25, 15, 8, 140), shadow_rect, border_radius=r)

        # Outer dark wood rim
        pygame.draw.rect(surface, COLOR_DARK_WOOD, rect, border_radius=r)
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, rect, width=max(2, Display.S(3)), border_radius=r)

        # Inner warm wood surface
        inner_rect = rect.inflate(-Display.S(12), -Display.S(12))
        if inner_rect.width > 0 and inner_rect.height > 0:
            pygame.draw.rect(surface, COLOR_WOOD, inner_rect, border_radius=max(4, r - Display.S(4)))
            # Specular top highlight strip
            highlight_rect = pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width, Display.S(6))
            pygame.draw.rect(surface, (215, 150, 95), highlight_rect, border_top_left_radius=max(4, r - Display.S(4)), border_top_right_radius=max(4, r - Display.S(4)))

        # Corner golden rivets
        rivet_r = max(2, Display.S(4))
        inset = Display.S(10)
        rivets = [
            (rect.left + inset, rect.top + inset),
            (rect.right - inset, rect.top + inset),
            (rect.left + inset, rect.bottom - inset),
            (rect.right - inset, rect.bottom - inset),
        ]
        for rx, ry in rivets:
            pygame.draw.circle(surface, COLOR_OUTLINE_BROWN, (rx, ry), rivet_r + 1)
            pygame.draw.circle(surface, COLOR_GOLD, (rx, ry), rivet_r)
            pygame.draw.circle(surface, COLOR_CREAM, (rx - 1, ry - 1), max(1, rivet_r // 2))

    @staticmethod
    def draw_parchment_card(surface: pygame.Surface, rect: pygame.Rect, corner_radius: int = 12):
        r = Display.S(corner_radius)
        # Drop shadow
        shadow_rect = rect.move(0, Display.S(4))
        pygame.draw.rect(surface, (25, 15, 8, 120), shadow_rect, border_radius=r)

        # Parchment background
        pygame.draw.rect(surface, COLOR_PARCHMENT, rect, border_radius=r)
        # Warm inner border
        pygame.draw.rect(surface, (230, 212, 168), rect.inflate(-Display.S(6), -Display.S(6)), width=Display.S(2), border_radius=max(2, r - Display.S(2)))
        # Dark outline
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, rect, width=max(2, Display.S(3)), border_radius=r)

    @staticmethod
    def draw_ribbon(surface: pygame.Surface, rect: pygame.Rect, text: str, size: int = 26, color: Tuple[int, int, int] = COLOR_GOLD):
        # Ribbon tails
        tail_w = Display.S(24)
        tail_left = [
            (rect.left - tail_w, rect.centery),
            (rect.left, rect.top + Display.S(4)),
            (rect.left, rect.bottom - Display.S(4))
        ]
        tail_right = [
            (rect.right + tail_w, rect.centery),
            (rect.right, rect.top + Display.S(4)),
            (rect.right, rect.bottom - Display.S(4))
        ]
        darker = (max(0, color[0] - 50), max(0, color[1] - 50), max(0, color[2] - 50))
        pygame.draw.polygon(surface, darker, tail_left)
        pygame.draw.polygon(surface, COLOR_OUTLINE_BROWN, tail_left, Display.S(2))
        pygame.draw.polygon(surface, darker, tail_right)
        pygame.draw.polygon(surface, COLOR_OUTLINE_BROWN, tail_right, Display.S(2))

        # Main ribbon banner
        pygame.draw.rect(surface, color, rect, border_radius=Display.S(8))
        # Top specular highlight
        top_hl = pygame.Rect(rect.x, rect.y, rect.width, Display.S(5))
        pygame.draw.rect(surface, (255, 235, 120), top_hl, border_top_left_radius=Display.S(8), border_top_right_radius=Display.S(8))
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, rect, width=max(2, Display.S(3)), border_radius=Display.S(8))

        # Outlined header title
        txt_surf = OutlinedText.render(text, size, color=COLOR_CREAM, outline_color=COLOR_OUTLINE_BROWN)
        surface.blit(txt_surf, txt_surf.get_rect(center=rect.centery and rect.center))


class WoodButton:
    """Juicy Hay Day-styled wood / green button with hover glow,

    press squash (~0.92 scale), and easeOutBack release.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font_size: int = 22,
        bg_color: Tuple[int, int, int] = COLOR_DEEP_GREEN,
        accent_color: Tuple[int, int, int] = COLOR_GRASS,
        callback: Optional[Callable] = None
    ):
        self.orig_rect = rect
        self.text = text
        self.font_size = font_size
        self.bg_color = bg_color
        self.accent_color = accent_color
        self.callback = callback

        self.is_hovered = False
        self.is_pressed = False
        self.press_scale = 1.0
        self.anim_time = 0.0

    def update(self, dt: float):
        if self.is_pressed:
            target_scale = 0.92
            self.press_scale += (target_scale - self.press_scale) * min(1.0, 20.0 * dt)
        else:
            target_scale = 1.05 if self.is_hovered else 1.0
            self.press_scale += (target_scale - self.press_scale) * min(1.0, 15.0 * dt)

    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        scaled_rect = self.get_scaled_rect()
        self.is_hovered = scaled_rect.collidepoint(mouse_pos)
        return self.is_hovered

    def handle_mouse_down(self, mouse_pos: Tuple[int, int]) -> bool:
        if self.check_hover(mouse_pos):
            self.is_pressed = True
            return True
        return False

    def handle_mouse_up(self, mouse_pos: Tuple[int, int]) -> bool:
        was_pressed = self.is_pressed
        self.is_pressed = False
        hit = self.orig_rect.inflate(Display.S(8), Display.S(8)).collidepoint(mouse_pos)
        if was_pressed and hit:
            if self.callback:
                self.callback()
            return True
        return False

    def get_scaled_rect(self) -> pygame.Rect:
        r = self.orig_rect
        w = int(r.width * self.press_scale)
        h = int(r.height * self.press_scale)
        return pygame.Rect(r.centerx - w // 2, r.centery - h // 2, w, h)

    @property
    def rect(self) -> pygame.Rect:
        return self.get_scaled_rect()

    def draw(self, surface: pygame.Surface):
        rect = self.get_scaled_rect()
        br = Display.S(10)

        # 3D Bottom Lip / Shadow
        lip_rect = rect.move(0, Display.S(4))
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, lip_rect, border_radius=br)

        # Base Fill
        pygame.draw.rect(surface, self.accent_color if self.is_hovered else self.bg_color, rect, border_radius=br)

        # Specular Top Gloss Highlight
        gloss_h = max(3, rect.height // 3)
        gloss_rect = pygame.Rect(rect.x, rect.y, rect.width, gloss_h)
        gloss_surf = pygame.Surface((rect.width, gloss_h), pygame.SRCALPHA)
        pygame.draw.rect(gloss_surf, (255, 255, 255, 75 if self.is_hovered else 40), gloss_surf.get_rect(), border_top_left_radius=br, border_top_right_radius=br)
        surface.blit(gloss_surf, gloss_rect)

        # Outline
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, rect, width=max(2, Display.S(3)), border_radius=br)

        # Text
        txt_surf = OutlinedText.render(self.text, self.font_size, color=COLOR_CREAM, outline_color=COLOR_OUTLINE_BROWN)
        surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))


class IconProgressBar:
    """Trough progress bar with carved wood rim, smooth tweening, and vital icon."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        fill_color: Tuple[int, int, int],
        value: float = 1.0,
        icon_name: str = "heart"
    ):
        self.rect = rect
        self.label = label
        self.fill_color = fill_color
        self.current_value = value
        self.target_value = value
        self.icon_name = icon_name

    def set_value(self, val: float):
        self.target_value = max(0.0, min(1.0, val))

    def update(self, dt: float):
        # Smooth exponential tween
        self.current_value += (self.target_value - self.current_value) * min(1.0, 10.0 * dt)

    def draw(self, surface: pygame.Surface):
        r = self.rect
        br = Display.S(6)

        # Recessed dark trough
        pygame.draw.rect(surface, (40, 25, 15), r, border_radius=br)

        # Fill bar
        fill_w = int((r.width - Display.S(4)) * self.current_value)
        if fill_w > 0:
            fill_rect = pygame.Rect(r.x + Display.S(2), r.y + Display.S(2), fill_w, r.height - Display.S(4))
            pygame.draw.rect(surface, self.fill_color, fill_rect, border_radius=max(2, br - 2))
            # Gloss highlight on top half of fill
            gloss_rect = pygame.Rect(fill_rect.x, fill_rect.y, fill_rect.width, fill_rect.height // 2)
            pygame.draw.rect(surface, (255, 255, 255, 70), gloss_rect, border_top_left_radius=max(2, br - 2), border_top_right_radius=max(2, br - 2))

        # Golden carved bezel
        pygame.draw.rect(surface, COLOR_DARK_WOOD, r, width=max(2, Display.S(2)), border_radius=br)

        # Label & Percentage
        val_pct = int(self.current_value * 100)
        lbl_surf = OutlinedText.render(f"{self.label}: {val_pct}%", 14, color=COLOR_CREAM, outline_thickness=2)
        surface.blit(lbl_surf, (r.x + Display.S(8), r.centery - lbl_surf.get_height() // 2))


class Stepper:
    """Numeric parameter stepper (+/-1, +/-10, randomize)."""

    def __init__(self, rect: pygame.Rect, value: int = 101, min_val: int = 1, max_val: int = 99999):
        self._rect = rect
        self.value = value
        self.min_val = min_val
        self.max_val = max_val

        btn_w = Display.S(38)
        btn_h = rect.height
        self.btn_minus_10 = WoodButton(pygame.Rect(rect.x, rect.y, btn_w, btn_h), "-10", 14, bg_color=COLOR_WOOD, callback=lambda: self.adjust(-10))
        self.btn_minus_1 = WoodButton(pygame.Rect(rect.x + btn_w + Display.S(4), rect.y, btn_w, btn_h), "-1", 14, bg_color=COLOR_WOOD, callback=lambda: self.adjust(-1))
        self.btn_plus_1 = WoodButton(pygame.Rect(rect.right - btn_w * 2 - Display.S(4), rect.y, btn_w, btn_h), "+1", 14, bg_color=COLOR_WOOD, callback=lambda: self.adjust(1))
        self.btn_plus_10 = WoodButton(pygame.Rect(rect.right - btn_w, rect.y, btn_w, btn_h), "+10", 14, bg_color=COLOR_WOOD, callback=lambda: self.adjust(10))
        self._realign_buttons()

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    @rect.setter
    def rect(self, new_rect: pygame.Rect):
        self._rect = new_rect
        self._realign_buttons()

    def _realign_buttons(self):
        btn_w = Display.S(38)
        btn_h = self._rect.height
        gap = Display.S(4)
        self.btn_minus_10.orig_rect = pygame.Rect(self._rect.x, self._rect.y, btn_w, btn_h)
        self.btn_minus_1.orig_rect = pygame.Rect(self._rect.x + btn_w + gap, self._rect.y, btn_w, btn_h)
        self.btn_plus_1.orig_rect = pygame.Rect(self._rect.right - btn_w * 2 - gap, self._rect.y, btn_w, btn_h)
        self.btn_plus_10.orig_rect = pygame.Rect(self._rect.right - btn_w, self._rect.y, btn_w, btn_h)

    def adjust(self, delta: int):
        self.value = max(self.min_val, min(self.max_val, self.value + delta))

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return (self.btn_minus_10.handle_mouse_down(mouse_pos) or
                    self.btn_minus_1.handle_mouse_down(mouse_pos) or
                    self.btn_plus_1.handle_mouse_down(mouse_pos) or
                    self.btn_plus_10.handle_mouse_down(mouse_pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return (self.btn_minus_10.handle_mouse_up(mouse_pos) or
                    self.btn_minus_1.handle_mouse_up(mouse_pos) or
                    self.btn_plus_1.handle_mouse_up(mouse_pos) or
                    self.btn_plus_10.handle_mouse_up(mouse_pos))
        return False

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        for b in (self.btn_minus_10, self.btn_minus_1, self.btn_plus_1, self.btn_plus_10):
            b.check_hover(mouse_pos)
            b.update(dt)

    def draw(self, surface: pygame.Surface):
        # Draw value box in center
        center_x = self.rect.centerx
        val_surf = OutlinedText.render(str(self.value), 22, color=COLOR_GOLD)
        surface.blit(val_surf, val_surf.get_rect(center=(center_x, self.rect.centery)))

        for b in (self.btn_minus_10, self.btn_minus_1, self.btn_plus_1, self.btn_plus_10):
            b.draw(surface)


class StarRating:
    """Renders 1-3 golden stars with bounce/pop-in scale animation."""

    def __init__(self, max_stars: int = 3):
        self.max_stars = max_stars
        self.earned_stars = 0
        self.anim_progress = 0.0

    def set_rating(self, stars: int):
        self.earned_stars = max(0, min(self.max_stars, stars))
        self.anim_progress = 0.0

    def update(self, dt: float):
        self.anim_progress = min(1.0, self.anim_progress + 2.0 * dt)

    def draw(self, surface: pygame.Surface, center: Tuple[int, int], size: int = 36):
        total_w = self.max_stars * (size + Display.S(8))
        start_x = center[0] - total_w // 2
        for i in range(self.max_stars):
            cx = start_x + i * (size + Display.S(8)) + size // 2
            cy = center[1]
            earned = i < self.earned_stars
            scale = pytweening.easeOutBack(self.anim_progress) if earned else 0.8
            r = int((size // 2) * scale)

            color = COLOR_GOLD if earned else (120, 100, 80)
            pygame.draw.circle(surface, COLOR_OUTLINE_BROWN, (cx, cy), r + 2)
            pygame.draw.circle(surface, color, (cx, cy), r)
            if earned:
                pygame.draw.circle(surface, COLOR_CREAM, (cx - r // 3, cy - r // 3), max(1, r // 4))


class CountUpNumber:
    """Smooth numeric count-up animation for ending cutscene results reveal."""

    def __init__(self, target_value: float, duration: float = 1.2, is_int: bool = True, suffix: str = ""):
        self.target_value = target_value
        self.duration = duration
        self.current_value = 0.0
        self.elapsed = 0.0
        self.is_int = is_int
        self.suffix = suffix
        self.is_complete = False

    def update(self, dt: float):
        if self.is_complete:
            return
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        eased_t = pytweening.easeOutCubic(t)
        self.current_value = eased_t * self.target_value
        if t >= 1.0:
            self.current_value = self.target_value
            self.is_complete = True

    def skip(self):
        self.current_value = self.target_value
        self.is_complete = True

    def get_text(self) -> str:
        if self.is_int:
            return f"{int(round(self.current_value))}{self.suffix}"
        return f"{self.current_value:.1f}{self.suffix}"

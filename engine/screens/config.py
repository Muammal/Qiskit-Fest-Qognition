"""engine/screens/config.py - Themed Mission Configuration Screen.
Parchment popup with ribbon header, framed minimap window,
numeric seed stepper, mind toggle, step horizon selector, and big green Start button.
"""

import random
from typing import Tuple, Optional, Callable
import pygame
import pytweening

from engine.display import Display
from engine.ui_kit import (
    COLOR_GRASS, COLOR_DEEP_GREEN, COLOR_SKY, COLOR_WOOD, COLOR_DARK_WOOD,
    COLOR_PARCHMENT, COLOR_ACCENT_ORANGE, COLOR_OUTLINE_BROWN, COLOR_GOLD,
    COLOR_CREAM, COLOR_WHITE, OutlinedText, NineSlicePanel, WoodButton, Stepper
)
from engine.world import IslandWorld, MAP_SEED


class ConfigScreen:
    """Themed configuration dialog prior to launching the simulation."""

    def __init__(
        self,
        scenario: str = "volcano",
        seed: int = 101,
        mind_type: str = "quantum",
        max_steps: int = 36,
        on_start: Optional[Callable] = None,
        on_back: Optional[Callable] = None
    ):
        self.scenario = scenario
        self.seed = seed
        self.mind_type = mind_type
        self.max_steps = max_steps
        self.on_start = on_start
        self.on_back = on_back

        self.anim_scale = 0.8
        self.anim_time = 0.0

        # Cached preview map surface
        self._cached_preview_seed = None
        self._cached_preview_scenario = None
        self._preview_surface: Optional[pygame.Surface] = None

        # Interactive controls (rects placed dynamically on draw)
        self.stepper = Stepper(pygame.Rect(0, 0, 320, 38), value=seed)
        self.btn_randomize = WoodButton(pygame.Rect(0, 0, 110, 38), "Random", 16, bg_color=COLOR_WOOD, callback=self._randomize_seed)
        self.btn_mind_toggle = WoodButton(pygame.Rect(0, 0, 240, 42), f"Mind: {mind_type.capitalize()}", 18, bg_color=(120, 60, 160), callback=self._cycle_mind)

        self.btn_h12 = WoodButton(pygame.Rect(0, 0, 75, 36), "12", 16, bg_color=COLOR_WOOD, callback=lambda: self._set_horizon(12))
        self.btn_h24 = WoodButton(pygame.Rect(0, 0, 75, 36), "24", 16, bg_color=COLOR_WOOD, callback=lambda: self._set_horizon(24))
        self.btn_h36 = WoodButton(pygame.Rect(0, 0, 75, 36), "36", 16, bg_color=COLOR_DEEP_GREEN, callback=lambda: self._set_horizon(36))

        self.btn_start = WoodButton(pygame.Rect(0, 0, 280, 56), "START SIMULATION", 24, bg_color=COLOR_DEEP_GREEN, callback=self.on_start)
        self.btn_back = WoodButton(pygame.Rect(0, 0, 150, 42), "< Scenarios", 18, bg_color=COLOR_DARK_WOOD, callback=self.on_back)

        # Initial layout at reference 1600x900 resolution
        self.modal_rect = pygame.Rect(0, 0, 0, 0)
        self.map_rect = pygame.Rect(0, 0, 0, 0)
        self._layout(1600, 900)

    def _layout(self, w: int, h: int):
        modal_w = min(Display.S(960), int(w * 0.85))
        modal_h = min(Display.S(640), int(h * 0.85))
        scaled_w = int(modal_w * self.anim_scale)
        scaled_h = int(modal_h * self.anim_scale)
        self.modal_rect = pygame.Rect((w - scaled_w) // 2, (h - scaled_h) // 2, scaled_w, scaled_h)
        inner_rect = self.modal_rect.inflate(-Display.S(24), -Display.S(24))

        map_size = min(Display.S(240), inner_rect.height - Display.S(100))
        self.map_rect = pygame.Rect(inner_rect.left + Display.S(28), inner_rect.centery - map_size // 2 - Display.S(15), map_size, map_size)

        ctrl_x = self.map_rect.right + Display.S(36)
        ctrl_y = inner_rect.top + Display.S(50)
        stepper_y = ctrl_y + Display.S(28)

        self.stepper.rect = pygame.Rect(ctrl_x, stepper_y, Display.S(260), Display.S(38))
        self.btn_randomize.orig_rect = pygame.Rect(ctrl_x + Display.S(275), stepper_y, Display.S(110), Display.S(38))

        mind_y = stepper_y + Display.S(56)
        self.btn_mind_toggle.orig_rect = pygame.Rect(ctrl_x, mind_y + Display.S(28), Display.S(385), Display.S(42))

        h_y = mind_y + Display.S(86)
        self.btn_h12.orig_rect = pygame.Rect(ctrl_x, h_y + Display.S(28), Display.S(75), Display.S(36))
        self.btn_h24.orig_rect = pygame.Rect(ctrl_x + Display.S(85), h_y + Display.S(28), Display.S(75), Display.S(36))
        self.btn_h36.orig_rect = pygame.Rect(ctrl_x + Display.S(170), h_y + Display.S(28), Display.S(75), Display.S(36))

        btn_bar_y = inner_rect.bottom - Display.S(52)
        self.btn_back.orig_rect = pygame.Rect(inner_rect.left + Display.S(28), btn_bar_y, Display.S(140), Display.S(44))
        self.btn_start.orig_rect = pygame.Rect(inner_rect.right - Display.S(300), btn_bar_y - Display.S(6), Display.S(280), Display.S(50))

    def _randomize_seed(self):
        new_seed = random.randint(1, 9999)
        self.seed = new_seed
        self.stepper.value = new_seed

    def set_mind(self, mind_type: str):
        self.mind_type = mind_type
        display_names = {"quantum": "2-Qubit Quantum", "classical_mixture": "Classical Mixture", "classical": "Classical Rational"}
        self.btn_mind_toggle.text = display_names.get(self.mind_type, "Quantum")
        colors = {"quantum": (120, 60, 160), "classical_mixture": (60, 130, 200), "classical": (180, 100, 40)}
        self.btn_mind_toggle.bg_color = colors.get(self.mind_type, COLOR_WOOD)

    def _cycle_mind(self):
        cycle = {"quantum": "classical_mixture", "classical_mixture": "classical", "classical": "quantum"}
        self.set_mind(cycle.get(self.mind_type, "quantum"))

    def _set_horizon(self, h: int):
        self.max_steps = h
        self.btn_h12.bg_color = COLOR_DEEP_GREEN if h == 12 else COLOR_WOOD
        self.btn_h24.bg_color = COLOR_DEEP_GREEN if h == 24 else COLOR_WOOD
        self.btn_h36.bg_color = COLOR_DEEP_GREEN if h == 36 else COLOR_WOOD

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.anim_time += dt
        self.anim_scale = min(1.0, pytweening.easeOutBack(min(1.0, self.anim_time * 2.5)))

        self.seed = self.stepper.value
        self.stepper.update(dt, mouse_pos)

        for b in (self.btn_randomize, self.btn_mind_toggle, self.btn_h12, self.btn_h24, self.btn_h36, self.btn_start, self.btn_back):
            b.check_hover(mouse_pos)
            b.update(dt)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if self.stepper.handle_event(event, mouse_pos):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in (self.btn_randomize, self.btn_mind_toggle, self.btn_h12, self.btn_h24, self.btn_h36, self.btn_start, self.btn_back):
                if b.handle_mouse_down(mouse_pos):
                    return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for b in (self.btn_randomize, self.btn_mind_toggle, self.btn_h12, self.btn_h24, self.btn_h36, self.btn_start, self.btn_back):
                if b.handle_mouse_up(mouse_pos):
                    return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.on_start:
                    self.on_start()
                return True
            elif event.key in (pygame.K_ESCAPE, pygame.K_h):
                if self.on_back:
                    self.on_back()
                return True
            elif event.key == pygame.K_q:
                self._cycle_mind()
                return True
            elif event.key == pygame.K_1:
                self.set_mind("quantum")
                return True
            elif event.key == pygame.K_2:
                self.set_mind("classical_mixture")
                return True
            elif event.key == pygame.K_3:
                self.set_mind("classical")
                return True
        return False

    def _render_minimap(self, size: int) -> pygame.Surface:
        if (self._preview_surface is not None and
            self._cached_preview_seed == self.seed and
            self._cached_preview_scenario == self.scenario and
            self._preview_surface.get_width() == size):
            return self._preview_surface

        self._cached_preview_seed = self.seed
        self._cached_preview_scenario = self.scenario
        surf = pygame.Surface((size, size))

        try:
            mseed = MAP_SEED if self.scenario == "volcano" else self.seed
            w = IslandWorld(seed=mseed, scenario=self.scenario)
            tile_colors = {
                0: (120, 190, 235),
                1: (240, 215, 140),
                2: (85, 165, 75),
                3: (130, 125, 135),
                4: (175, 115, 60),
            }
            pix_w = size / 40.0
            for y in range(40):
                for x in range(40):
                    t = w.get_tile(x, y)
                    c = tile_colors.get(t, (100, 100, 100))
                    pygame.draw.rect(surf, c, (int(x * pix_w), int(y * pix_w), int(pix_w) + 1, int(pix_w) + 1))
        except Exception:
            surf.fill(COLOR_GRASS)

        self._preview_surface = surf
        return surf

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int, int] = (0, 0)):
        w = surface.get_width()
        h = surface.get_height()
        self._layout(w, h)

        # Dim background
        dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_surf.fill((15, 10, 5, 160))
        surface.blit(dim_surf, (0, 0))

        modal_rect = self.modal_rect
        NineSlicePanel.draw_wood_frame(surface, modal_rect, corner_radius=18)
        inner_rect = modal_rect.inflate(-Display.S(24), -Display.S(24))
        NineSlicePanel.draw_parchment_card(surface, inner_rect, corner_radius=14)

        # Header Ribbon
        ribbon_w = min(Display.S(540), int(modal_rect.width * 0.70))
        ribbon_h = Display.S(52)
        ribbon_rect = pygame.Rect((w - ribbon_w) // 2, modal_rect.top - Display.S(14), ribbon_w, ribbon_h)
        NineSlicePanel.draw_ribbon(surface, ribbon_rect, f"CONFIG: {self.scenario.upper()}", size=24, color=COLOR_GOLD)

        # Left: Framed Minimap Window
        map_rect = self.map_rect
        pygame.draw.rect(surface, COLOR_DARK_WOOD, map_rect.inflate(Display.S(10), Display.S(10)), border_radius=Display.S(8))
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, map_rect.inflate(Display.S(10), Display.S(10)), width=Display.S(3), border_radius=Display.S(8))

        minimap_surf = self._render_minimap(map_rect.width)
        surface.blit(minimap_surf, map_rect)

        map_lbl = OutlinedText.render(f"Terrain Seed: {self.seed}", 16, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(map_lbl, map_lbl.get_rect(center=(map_rect.centerx, map_rect.bottom + Display.S(18))))

        # Right: Parameters & Controls
        ctrl_x = map_rect.right + Display.S(36)
        ctrl_y = inner_rect.top + Display.S(50)

        # 1. Seed Stepper
        seed_hdr = OutlinedText.render("Environmental Hazard Seed:", 18, color=COLOR_DARK_WOOD)
        surface.blit(seed_hdr, (ctrl_x, ctrl_y))

        stepper_y = ctrl_y + Display.S(28)
        self.stepper.draw(surface)
        self.btn_randomize.draw(surface)

        # 2. Decision Mind Toggle
        mind_y = stepper_y + Display.S(56)
        mind_hdr = OutlinedText.render("Cognitive Mind Engine:", 18, color=COLOR_DARK_WOOD)
        surface.blit(mind_hdr, (ctrl_x, mind_y))
        self.btn_mind_toggle.draw(surface)

        # 3. Horizon Selector
        h_y = mind_y + Display.S(86)
        h_hdr = OutlinedText.render("Step Horizon (Turns):", 18, color=COLOR_DARK_WOOD)
        surface.blit(h_hdr, (ctrl_x, h_y))

        for b in (self.btn_h12, self.btn_h24, self.btn_h36):
            b.draw(surface)

        # 4. Action Buttons (Back & Start)
        self.btn_back.draw(surface)
        self.btn_start.draw(surface)

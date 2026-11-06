"""engine/screens/hub.py - Themed Event Choice Hub Screen.
Features two hanging wooden signboards (Island Wilderness & Volcano Evacuation)
with rope chains, metadata pill badges, hover bounce animations,
drifting clouds, and a parallax farm/island backdrop.
"""

import math
from typing import Tuple, Optional, Callable
import pygame
import pytweening

from engine.display import Display
from engine.ui_kit import (
    COLOR_GRASS, COLOR_DEEP_GREEN, COLOR_SKY, COLOR_WOOD, COLOR_DARK_WOOD,
    COLOR_PARCHMENT, COLOR_ACCENT_ORANGE, COLOR_OUTLINE_BROWN, COLOR_GOLD,
    COLOR_CREAM, COLOR_WHITE, OutlinedText, NineSlicePanel, WoodButton
)
from engine.assets import AssetManager


class EventChoiceHubScreen:
    """Themed Hay Day Hub with two hanging wooden signboards."""

    def __init__(
        self,
        on_choose_island: Callable,
        on_choose_volcano: Callable,
        on_choose_titanic: Optional[Callable] = None,
        on_choose_pompeii: Optional[Callable] = None,
        on_choose_waterloo: Optional[Callable] = None,
        on_choose_builder: Optional[Callable] = None
    ):
        self.on_choose_island = on_choose_island
        self.on_choose_volcano = on_choose_volcano
        self.on_choose_titanic = on_choose_titanic
        self.on_choose_pompeii = on_choose_pompeii
        self.on_choose_waterloo = on_choose_waterloo
        self.on_choose_builder = on_choose_builder

        self.anim_time = 0.0
        self.hover_island = False
        self.hover_volcano = False
        self.bounce_island = 0.0
        self.bounce_volcano = 0.0

        # Clouds state [(x, y, speed, scale)]
        self.clouds = [
            [-50.0, 60.0, 18.0, 0.8],
            [350.0, 110.0, 12.0, 1.1],
            [800.0, 45.0, 22.0, 0.9],
            [1250.0, 95.0, 15.0, 1.0],
        ]

        # Clickable Rects (computed on draw)
        self.card_island_rect = pygame.Rect(0, 0, 0, 0)
        self.card_volcano_rect = pygame.Rect(0, 0, 0, 0)

        # Launch CTA WoodButtons on each signboard
        self.btn_play_island = WoodButton(pygame.Rect(0, 0, 200, 50), "Select Island [1]", 20, bg_color=COLOR_DEEP_GREEN, callback=self.on_choose_island)
        self.btn_play_volcano = WoodButton(pygame.Rect(0, 0, 200, 50), "Select Volcano [2]", 20, bg_color=COLOR_ACCENT_ORANGE, callback=self.on_choose_volcano)

        # Bottom row buttons for other scenarios
        self.btn_titanic = WoodButton(pygame.Rect(0, 0, 170, 38), "Titanic 1912 [3]", 14, bg_color=(38, 92, 160), callback=self.on_choose_titanic)
        self.btn_pompeii = WoodButton(pygame.Rect(0, 0, 170, 38), "Pompeii 79 AD [4]", 14, bg_color=(150, 68, 40), callback=self.on_choose_pompeii)
        self.btn_waterloo = WoodButton(pygame.Rect(0, 0, 170, 38), "Waterloo Chlorine [5]", 14, bg_color=(68, 128, 60), callback=self.on_choose_waterloo)
        self.btn_builder = WoodButton(pygame.Rect(0, 0, 190, 38), "Scenario Builder [B]", 14, bg_color=(140, 60, 180), callback=self.on_choose_builder)

        # Initial layout at reference 1600x900 resolution
        self._layout(1600, 900)

    def _layout(self, w: int, h: int):
        board_w = min(Display.S(540), int((w - Display.S(100)) // 2))
        board_h = min(Display.S(580), int(h * 0.68))
        board_spacing = Display.S(40)
        total_w = board_w * 2 + board_spacing
        start_x = (w - total_w) // 2
        base_y = Display.S(150)

        self.card_island_rect = pygame.Rect(start_x, base_y - int(self.bounce_island), board_w, board_h)
        self.card_volcano_rect = pygame.Rect(start_x + board_w + board_spacing, base_y - int(self.bounce_volcano), board_w, board_h)

        self.btn_play_island.orig_rect = pygame.Rect(self.card_island_rect.centerx - Display.S(110), self.card_island_rect.bottom - Display.S(68), Display.S(220), Display.S(48))
        self.btn_play_volcano.orig_rect = pygame.Rect(self.card_volcano_rect.centerx - Display.S(110), self.card_volcano_rect.bottom - Display.S(68), Display.S(220), Display.S(48))

        bar_h = Display.S(54)
        bar_y = h - bar_h - Display.S(12)
        btn_w = Display.S(180)
        btn_h = Display.S(38)
        spacing = Display.S(12)
        total_btns_w = btn_w * 4 + spacing * 3
        bx = (w - total_btns_w) // 2
        by = bar_y + (bar_h - btn_h) // 2

        self.btn_titanic.orig_rect = pygame.Rect(bx, by, btn_w, btn_h)
        self.btn_pompeii.orig_rect = pygame.Rect(bx + (btn_w + spacing), by, btn_w, btn_h)
        self.btn_waterloo.orig_rect = pygame.Rect(bx + (btn_w + spacing) * 2, by, btn_w, btn_h)
        self.btn_builder.orig_rect = pygame.Rect(bx + (btn_w + spacing) * 3, by, btn_w, btn_h)

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.anim_time += dt

        # Update drifting clouds
        for c in self.clouds:
            c[0] += c[2] * dt
            if c[0] > 1800:
                c[0] = -300

        # Hover bounces (smooth ease in/out)
        self.hover_island = self.card_island_rect.collidepoint(mouse_pos)
        self.hover_volcano = self.card_volcano_rect.collidepoint(mouse_pos)
        target_bi = Display.S(12) if self.hover_island else 0.0
        target_bv = Display.S(12) if self.hover_volcano else 0.0
        self.bounce_island += (target_bi - self.bounce_island) * min(1.0, 12.0 * dt)
        self.bounce_volcano += (target_bv - self.bounce_volcano) * min(1.0, 12.0 * dt)

        for b in (self.btn_play_island, self.btn_play_volcano, self.btn_titanic, self.btn_pompeii, self.btn_waterloo, self.btn_builder):
            b.check_hover(mouse_pos)
            b.update(dt)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in (self.btn_play_island, self.btn_play_volcano, self.btn_titanic, self.btn_pompeii, self.btn_waterloo, self.btn_builder):
                if b.handle_mouse_down(mouse_pos):
                    return True
            if self.card_island_rect.collidepoint(mouse_pos):
                self.on_choose_island()
                return True
            elif self.card_volcano_rect.collidepoint(mouse_pos):
                self.on_choose_volcano()
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for b in (self.btn_play_island, self.btn_play_volcano, self.btn_titanic, self.btn_pompeii, self.btn_waterloo, self.btn_builder):
                if b.handle_mouse_up(mouse_pos):
                    return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1, pygame.K_i):
                self.on_choose_island()
                return True
            elif event.key in (pygame.K_2, pygame.K_KP2, pygame.K_v):
                self.on_choose_volcano()
                return True
            elif event.key in (pygame.K_3, pygame.K_KP3):
                if self.on_choose_titanic: self.on_choose_titanic()
                return True
            elif event.key in (pygame.K_4, pygame.K_KP4):
                if self.on_choose_pompeii: self.on_choose_pompeii()
                return True
            elif event.key in (pygame.K_5, pygame.K_KP5):
                if self.on_choose_waterloo: self.on_choose_waterloo()
                return True
            elif event.key in (pygame.K_6, pygame.K_KP6, pygame.K_b):
                if self.on_choose_builder: self.on_choose_builder()
                return True
        return False

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int, int] = (0, 0)):
        w = surface.get_width()
        h = surface.get_height()
        self._layout(w, h)

        # 1. Sky & Sunlit Gradient Backdrop
        surface.fill(COLOR_SKY)

        # Distant blue-green mountain silhouettes
        pts_mountains = [(0, h), (0, int(h * 0.55)), (int(w * 0.25), int(h * 0.42)), (int(w * 0.5), int(h * 0.48)), (int(w * 0.75), int(h * 0.38)), (w, int(h * 0.52)), (w, h)]
        pygame.draw.polygon(surface, (120, 185, 220), pts_mountains)

        # Checkerboard Emerald Lawn (Lower third)
        lawn_y = int(h * 0.62)
        pygame.draw.rect(surface, COLOR_GRASS, (0, lawn_y, w, h - lawn_y))
        # Warm grass border stripe
        pygame.draw.rect(surface, COLOR_DEEP_GREEN, (0, lawn_y, w, Display.S(8)))

        # 2. Drifting Clouds
        cloud_img = AssetManager.get_image("sprites/cloud.png")
        for c in self.clouds:
            cx, cy, _, cscale = c
            scaled_w = Display.S(int(220 * cscale))
            scaled_h = Display.S(int(110 * cscale))
            if cloud_img:
                scaled_cloud = pygame.transform.smoothscale(cloud_img, (scaled_w, scaled_h))
                surface.blit(scaled_cloud, (int(cx * (w / 1600.0)), Display.S(int(cy))))
            else:
                pygame.draw.ellipse(surface, (255, 255, 255, 220), (int(cx * (w / 1600.0)), Display.S(int(cy)), scaled_w, scaled_h))

        # 3. Top Royal Ribbon Header
        hdr_w = min(Display.S(900), int(w * 0.85))
        hdr_h = Display.S(64)
        hdr_rect = pygame.Rect((w - hdr_w) // 2, Display.S(24), hdr_w, hdr_h)
        NineSlicePanel.draw_ribbon(surface, hdr_rect, "QUANTUM COGNITION SIMULATION", size=32, color=COLOR_GOLD)

        subtitle_surf = OutlinedText.render("Select an Evacuation or Survival Scenario to Begin", 18, color=COLOR_DARK_WOOD, outline_color=COLOR_CREAM, outline_thickness=1)
        surface.blit(subtitle_surf, subtitle_surf.get_rect(center=(w // 2, Display.S(105))))

        # 4. Two Hanging Wooden Signboards
        board_w = min(Display.S(540), int((w - Display.S(100)) // 2))
        board_h = min(Display.S(580), int(h * 0.68))
        board_spacing = Display.S(40)
        total_w = board_w * 2 + board_spacing
        start_x = (w - total_w) // 2
        base_y = Display.S(150)

        # Check hovers
        self.card_island_rect = pygame.Rect(start_x, base_y - int(self.bounce_island), board_w, board_h)
        self.card_volcano_rect = pygame.Rect(start_x + board_w + board_spacing, base_y - int(self.bounce_volcano), board_w, board_h)
        self.hover_island = self.card_island_rect.collidepoint(mouse_pos)
        self.hover_volcano = self.card_volcano_rect.collidepoint(mouse_pos)

        # Draw Hanging Chains / Ropes
        chain_color = (60, 40, 25)
        for rect in (self.card_island_rect, self.card_volcano_rect):
            chain_w = Display.S(6)
            for cx in (rect.left + Display.S(45), rect.right - Display.S(45)):
                pygame.draw.line(surface, chain_color, (cx, 0), (cx, rect.top), chain_w)
                # Chain links / rings
                for link_y in range(Display.S(20), rect.top, Display.S(24)):
                    pygame.draw.circle(surface, (90, 60, 40), (cx, link_y), Display.S(5))
                    pygame.draw.circle(surface, COLOR_OUTLINE_BROWN, (cx, link_y), Display.S(5), 2)

        # --- Signboard 1: Island Wilderness ---
        self._draw_signboard(
            surface,
            self.card_island_rect,
            title="ISLAND WILDERNESS",
            subtitle="Exploration, Shelter & Storm Survival",
            tag="Survival [1]",
            pills=["1 Agent", "36 Steps (72h)", "Grover DTQW Walk", "Markov Storms"],
            thumb_asset="tiles/tile_grass.png",
            btn=self.btn_play_island,
            accent_color=COLOR_DEEP_GREEN
        )

        # --- Signboard 2: Volcano Eruption ---
        self._draw_signboard(
            surface,
            self.card_volcano_rect,
            title="VOLCANO EVACUATION",
            subtitle="La Soufrière • Pyroclastic Density Currents",
            tag="Evacuation [2]",
            pills=["1 Agent / Crowd", "36 Steps", "Non-Commuting Cues", "Tobler Dijkstra Paths"],
            thumb_asset="tiles/tile_mountain.png",
            btn=self.btn_play_volcano,
            accent_color=COLOR_ACCENT_ORANGE
        )

        # 5. Bottom Navigation Bar for other scenarios & shortcuts
        bar_h = Display.S(54)
        bar_y = h - bar_h - Display.S(12)
        btn_w = Display.S(180)
        btn_h = Display.S(38)
        spacing = Display.S(12)
        total_btns_w = btn_w * 4 + spacing * 3
        bx = (w - total_btns_w) // 2
        by = bar_y + (bar_h - btn_h) // 2

        self.btn_titanic.orig_rect = pygame.Rect(bx, by, btn_w, btn_h)
        self.btn_pompeii.orig_rect = pygame.Rect(bx + (btn_w + spacing), by, btn_w, btn_h)
        self.btn_waterloo.orig_rect = pygame.Rect(bx + (btn_w + spacing) * 2, by, btn_w, btn_h)
        self.btn_builder.orig_rect = pygame.Rect(bx + (btn_w + spacing) * 3, by, btn_w, btn_h)

        for b in (self.btn_titanic, self.btn_pompeii, self.btn_waterloo, self.btn_builder):
            b.draw(surface)

    def _draw_signboard(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        subtitle: str,
        tag: str,
        pills: list,
        thumb_asset: str,
        btn: WoodButton,
        accent_color: Tuple[int, int, int]
    ):
        # Heavy Wood Frame
        NineSlicePanel.draw_wood_frame(surface, rect, corner_radius=18)

        # Inner Parchment Inset
        inner_rect = rect.inflate(-Display.S(20), -Display.S(20))
        NineSlicePanel.draw_parchment_card(surface, inner_rect, corner_radius=12)

        # Sign Title Ribbon / Header
        title_h = Display.S(44)
        title_rect = pygame.Rect(rect.left + Display.S(16), rect.top + Display.S(16), rect.width - Display.S(32), title_h)
        NineSlicePanel.draw_ribbon(surface, title_rect, title, size=22, color=accent_color)

        # Subtitle
        sub_surf = OutlinedText.render(subtitle, 15, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(sub_surf, sub_surf.get_rect(center=(rect.centerx, title_rect.bottom + Display.S(18))))

        # Framed Scenic Illustration Box
        art_w = rect.width - Display.S(50)
        art_h = Display.S(180)
        art_rect = pygame.Rect(rect.left + Display.S(25), title_rect.bottom + Display.S(36), art_w, art_h)
        pygame.draw.rect(surface, COLOR_DARK_WOOD, art_rect, border_radius=Display.S(8))
        pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, art_rect, width=Display.S(3), border_radius=Display.S(8))

        thumb = AssetManager.get_image(thumb_asset)
        if thumb:
            scaled_thumb = pygame.transform.smoothscale(thumb, (art_rect.width - Display.S(8), art_rect.height - Display.S(8)))
            surface.blit(scaled_thumb, (art_rect.x + Display.S(4), art_rect.y + Display.S(4)))

        # Metadata Pill Badges
        pill_y = art_rect.bottom + Display.S(16)
        pill_h = Display.S(26)
        pill_w = (art_w - Display.S(12)) // 2
        for idx, pill_text in enumerate(pills):
            row = idx // 2
            col = idx % 2
            px = art_rect.left + col * (pill_w + Display.S(12))
            py = pill_y + row * (pill_h + Display.S(8))
            p_rect = pygame.Rect(px, py, pill_w, pill_h)
            pygame.draw.rect(surface, (235, 220, 185), p_rect, border_radius=Display.S(13))
            pygame.draw.rect(surface, COLOR_OUTLINE_BROWN, p_rect, width=max(1, Display.S(2)), border_radius=Display.S(13))

            p_surf = OutlinedText.render(pill_text, 13, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
            surface.blit(p_surf, p_surf.get_rect(center=p_rect.center))

        # Bottom Launch Button
        btn.orig_rect = pygame.Rect(rect.centerx - Display.S(110), rect.bottom - Display.S(68), Display.S(220), Display.S(48))
        btn.draw(surface)


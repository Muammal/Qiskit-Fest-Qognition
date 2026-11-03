"""
engine/gui.py - Interactive 2D Pygame Island Simulation, Home Screen & Debrief HUD
Owned by Tech C (Integration, Engine, Visualization).

Enhanced Suite:
  1. High-Resolution 1600x900 Widescreen Display:
     - 16:9 standard cinematic aspect ratio.
     - 900x900 high-definition island map viewport.
     - 700x900 expansive telemetry and analytics dashboard.
     - Fullscreen toggle via [Fullscreen] button or F11 key with letterboxing/pillarboxing
       and exact mouse coordinate transformation at any display resolution.
  2. Procedural Vector Iconography (Zero Broken Unicode Squares):
     - Eliminates all font-dependent unicode emojis and tofu squares.
     - Crisp, resolution-independent vector icons drawn directly with Pygame geometry
       (Fullscreen, Windows, Quantum Atom, Neural Network, Play/Pause, Step, Speed Bolt,
       Menu, Action Log, Dice, Rocket, Replay, Compare, Health Cross, and Shields).
  3. Strict Text Assembly & Border-Bound Typography:
     - Dynamic text wrapping (`wrap_text` and `render_wrapped_text`) ensuring decision rationales,
       event chains, telemetry labels, and modal metrics never spill or exceed container borders.
     - Dynamically calculated column offsets and bounded badge layouts.
  4. Interactive Home Screen (Start Menu):
     - High-resolution 300x300 procedural island mini-map preview thumbnail with terrain stats.
     - Decision Mind selection cards with formula previews (Qiskit 2-qubit vs Classical ATUS).
     - Island Presets with semantic difficulty tags + full numeric seed stepper + randomizer.
     - Step horizon selector (12, 24, 36, 48 turns).
     - Glowing Hero Launch button.
  5. 2D Island Living World Viewport:
     - Procedural 40x40 tiles with dynamic water waves, freshwater streams, shore foam,
       layered pine canopies with food berry clusters, and alpine snowcaps.
     - Dynamic lighting & weather: day ambient warmth, night navy tint (21:00-05:00),
       storm rain with lightning flashes, and cold night frost vignette with drifting snow.
     - Animated survivor avatar with walking interpolation (lerp), bobbing, condition badges,
       particle bursts, and overhead speech bubbles.
     - Hovering tile inspector tooltip near mouse cursor.
  6. Telemetry HUD & Status Screens:
     - Survivor profile with dynamic mood facial expression based on vitals.
     - 6 Need Bars with dual-layer glossy progress bars and color gradation.
     - Composite stress gauge & hardware decoherence meter.
     - Event hazard banner and chronological order-effect chain.
     - Action probability horizontal bar chart with leading action highlight.
     - Plain-language quantum reasoning quote box neatly wrapped.
  7. End-of-Event Debrief Screen & Action History Log Overlay:
     - Golden laurel or memorial banner with comprehensive 5-metric breakdown.
     - Immediate opposite mind comparison button (Quantum <-> Classical on same seed), replay run,
       and return-to-home navigation.
"""

import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pygame

# Ensure contracts and engine packages are resolvable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import contracts
from engine.world import IslandWorld
from engine.agent import SurvivalAgent
from engine.events import EventGenerator
from engine.simulation import SimulationEngine


# -----------------------------------------------------------------------------
# Configuration & High-Resolution Display Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
MAP_SIZE = 900
GRID_DIM = 40
TILE_SIZE = MAP_SIZE / GRID_DIM  # 22.5 px per tile
FPS = 60

# Palette Definitions
COLOR_BG = (10, 15, 29)          # Deep Slate / Navy
COLOR_PANEL_BG = (22, 30, 46)    # Slate 800
COLOR_PANEL_ALT = (16, 23, 38)   # Darker slate card
COLOR_CARD_BORDER = (45, 60, 85) # Slate 700 border
COLOR_CARD_HOVER = (60, 80, 115)

COLOR_TEXT_MAIN = (248, 250, 252)
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_TEXT_HINT = (100, 116, 139)

COLOR_CYAN = (6, 182, 212)
COLOR_CYAN_LIGHT = (56, 189, 248)
COLOR_PURPLE = (168, 85, 247)
COLOR_PURPLE_LIGHT = (192, 132, 252)
COLOR_GREEN = (34, 197, 94)
COLOR_GREEN_DARK = (21, 128, 61)
COLOR_YELLOW = (234, 179, 8)
COLOR_RED = (239, 68, 68)
COLOR_BLUE = (59, 130, 246)
COLOR_ORANGE = (249, 115, 22)
COLOR_GOLD = (250, 204, 21)

# Tile Base Colors
TILE_COLORS = {
    0: (27, 58, 91),    # Ocean Deep Blue
    1: (217, 175, 88),  # Plains / Coastal Sand
    2: (22, 101, 52),   # Dense Forest Pine
    3: (71, 85, 105),   # Mountain Stone
    4: (180, 83, 9)     # Shelter Timber
}

ACTION_COLORS = {
    "forage": (34, 197, 94),
    "drink": (6, 182, 212),
    "build_shelter": (249, 115, 22),
    "rest": (168, 85, 247),
    "explore": (234, 179, 8),
    "craft": (148, 163, 184),
    "hide": (239, 68, 68)
}

PRESETS = [
    {"label": "Archipelago (Seed 101)", "seed": 101, "tag": "Balanced | High Survival", "color": COLOR_GREEN},
    {"label": "Arid Crag (Seed 105)", "seed": 105, "tag": "Arid Interior | Thirst Peril", "color": COLOR_ORANGE},
    {"label": "Interference Lab (Seed 202)", "seed": 202, "tag": "Order Effect Divergence", "color": COLOR_PURPLE},
    {"label": "Heroic Haven (Seed 777)", "seed": 777, "tag": "Timber Rich | Freshwater", "color": COLOR_CYAN}
]


def set_cursor_safely(cursor_type):
    """Safely sets system mouse cursor, handling environments without window manager support."""
    try:
        pygame.mouse.set_cursor(cursor_type)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Procedural Vector Icon Drawing Library (Zero Unicode Squares)
# -----------------------------------------------------------------------------
def draw_vector_icon(surface: pygame.Surface, icon: str, x: int, y: int, size: int, color: Tuple[int, int, int]):
    """
    Renders high-definition procedural vector icons directly with Pygame geometry.
    Guarantees crisp, anti-aliased iconography with zero broken font squares.
    """
    cx = x + size // 2
    cy = y + size // 2
    pad = max(1, size // 8)

    if icon == "fullscreen":
        s = size
        arm = max(2, s // 3)
        pygame.draw.lines(surface, color, False, [(x + pad, y + pad + arm), (x + pad, y + pad), (x + pad + arm, y + pad)], 2)
        pygame.draw.lines(surface, color, False, [(x + s - pad - arm, y + pad), (x + s - pad, y + pad), (x + s - pad, y + pad + arm)], 2)
        pygame.draw.lines(surface, color, False, [(x + pad, y + s - pad - arm), (x + pad, y + s - pad), (x + pad + arm, y + s - pad)], 2)
        pygame.draw.lines(surface, color, False, [(x + s - pad - arm, y + s - pad), (x + s - pad, y + s - pad), (x + s - pad, y + s - pad - arm)], 2)

    elif icon == "windowed":
        w2 = size - pad * 3
        pygame.draw.rect(surface, color, (x + pad * 2, y + pad, w2, w2), 2)
        pygame.draw.rect(surface, (max(0, color[0] // 2), max(0, color[1] // 2), max(0, color[2] // 2)), (x + pad, y + pad * 2, w2, w2), 1)

    elif icon == "quantum":
        r = max(2, size // 6)
        pygame.draw.circle(surface, color, (cx, cy), r)
        ew = max(4, size - pad * 2)
        eh = max(3, size // 2)
        pygame.draw.ellipse(surface, color, (x + pad, cy - eh // 2, ew, eh), 1)
        pygame.draw.ellipse(surface, color, (cx - eh // 2, y + pad, eh, ew), 1)

    elif icon == "classical":
        r = max(2, size // 8)
        p_top = (cx, y + pad + r)
        p_l = (x + pad + r, y + size - pad - r)
        p_r = (x + size - pad - r, y + size - pad - r)
        pygame.draw.line(surface, color, p_top, p_l, 1)
        pygame.draw.line(surface, color, p_top, p_r, 1)
        pygame.draw.circle(surface, color, p_top, r)
        pygame.draw.circle(surface, color, p_l, r)
        pygame.draw.circle(surface, color, p_r, r)

    elif icon == "play":
        pts = [(x + pad + 2, y + pad), (x + size - pad, cy), (x + pad + 2, y + size - pad)]
        pygame.draw.polygon(surface, color, pts)

    elif icon == "pause":
        bw = max(2, size // 4)
        pygame.draw.rect(surface, color, (x + pad, y + pad, bw, size - pad * 2), border_radius=1)
        pygame.draw.rect(surface, color, (x + size - pad - bw, y + pad, bw, size - pad * 2), border_radius=1)

    elif icon == "step":
        pts = [(x + pad, y + pad), (x + size - pad - 4, cy), (x + pad, y + size - pad)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.line(surface, color, (x + size - pad, y + pad), (x + size - pad, y + size - pad), 2)

    elif icon == "speed":
        pts = [
            (cx + 2, y + pad),
            (x + pad + 1, cy + 1),
            (cx, cy + 1),
            (cx - 2, y + size - pad),
            (x + size - pad - 1, cy - 1),
            (cx, cy - 1)
        ]
        pygame.draw.polygon(surface, color, pts)

    elif icon == "menu":
        gap = max(3, (size - pad * 2) // 3)
        for i in range(3):
            ly = y + pad + i * gap + gap // 2
            pygame.draw.line(surface, color, (x + pad, ly), (x + size - pad, ly), 2)

    elif icon == "log":
        pygame.draw.rect(surface, color, (x + pad + 1, y + pad, size - (pad + 1) * 2, size - pad * 2), 1, border_radius=2)
        for i in range(3):
            ly = y + pad + 3 + (i + 1) * ((size - pad * 2) // 4)
            pygame.draw.line(surface, color, (x + pad + 4, ly), (x + size - pad - 4, ly), 1)

    elif icon == "close":
        pygame.draw.line(surface, color, (x + pad, y + pad), (x + size - pad, y + size - pad), 2)
        pygame.draw.line(surface, color, (x + size - pad, y + pad), (x + pad, y + size - pad), 2)

    elif icon in ("dice", "random"):
        pygame.draw.rect(surface, color, (x + pad, y + pad, size - pad * 2, size - pad * 2), 2, border_radius=3)
        pygame.draw.circle(surface, color, (cx, cy), max(1, size // 8))
        pygame.draw.circle(surface, color, (x + pad + 4, y + pad + 4), max(1, size // 10))
        pygame.draw.circle(surface, color, (x + size - pad - 4, y + size - pad - 4), max(1, size // 10))

    elif icon == "launch":
        pts = [
            (cx, y + pad),
            (x + size - pad, cy + 4),
            (cx + 3, y + size - pad),
            (cx, y + size - pad - 4),
            (cx - 3, y + size - pad),
            (x + pad, cy + 4)
        ]
        pygame.draw.polygon(surface, color, pts)

    elif icon == "replay":
        pygame.draw.arc(surface, color, (x + pad, y + pad, size - pad * 2, size - pad * 2), 0.5, 5.5, 2)
        arrow = [(cx + 2, y + pad - 2), (cx + 6, y + pad + 2), (cx + 1, y + pad + 4)]
        pygame.draw.polygon(surface, color, arrow)

    elif icon == "compare":
        r = max(2, size // 4)
        pygame.draw.circle(surface, color, (cx - r, cy), r, 1)
        pygame.draw.circle(surface, color, (cx + r, cy), r)

    elif icon == "heart":
        pygame.draw.rect(surface, color, (cx - 1, y + pad, 3, size - pad * 2))
        pygame.draw.rect(surface, color, (x + pad, cy - 1, size - pad * 2, 3))


# -----------------------------------------------------------------------------
# Clean Text Assembly & Dynamic Wrapping Utility
# -----------------------------------------------------------------------------
def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Wraps text strictly within max_width pixels without word breakage."""
    words = text.split()
    if not words:
        return []
    lines = []
    current_line: List[str] = []
    for word in words:
        test_line = " ".join(current_line + [word])
        w, _ = font.size(test_line)
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def render_wrapped_text(surface: pygame.Surface, text: str, font: pygame.font.Font,
                        color: Tuple[int, int, int], x: int, y: int, max_width: int,
                        line_spacing: int = 4, max_lines: Optional[int] = None) -> int:
    """
    Renders text cleanly wrapped within max_width without exceeding borders.
    Returns the total vertical height used.
    """
    lines = wrap_text(text, font, max_width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            last = lines[-1]
            while last and font.size(last + "...")[0] > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "..."

    line_h = font.get_linesize()
    curr_y = y
    for line in lines:
        surf = font.render(line, True, color)
        surface.blit(surf, (x, curr_y))
        curr_y += line_h + line_spacing
    return curr_y - y


# -----------------------------------------------------------------------------
# Tactile UI Button Component
# -----------------------------------------------------------------------------
class UIButton:
    def __init__(self, rect: Tuple[int, int, int, int], text: str, font: pygame.font.Font,
                 bg_color=COLOR_PANEL_BG, text_color=COLOR_TEXT_MAIN,
                 border_color=COLOR_CARD_BORDER, active_color=COLOR_CYAN,
                 subtext: Optional[str] = None, subfont: Optional[pygame.font.Font] = None,
                 icon: Optional[str] = None, variant: str = "default"):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.subtext = subtext
        self.font = font
        self.subfont = subfont
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color
        self.active_color = active_color
        self.icon = icon
        self.variant = variant

        self.is_hovered = False
        self.is_pressed = False
        self.is_active = False
        self.ripple_timer = 0.0

    def check_hover(self, pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def trigger_click(self):
        self.ripple_timer = 0.25

    def draw(self, surface: pygame.Surface, dt: float = 0.016):
        if self.ripple_timer > 0:
            self.ripple_timer = max(0.0, self.ripple_timer - dt)

        dy = 1 if self.is_pressed else 0
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + dy, self.rect.width, self.rect.height)

        # 1. Drop shadow
        if not self.is_pressed:
            shadow_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), (0, 0, self.rect.width, self.rect.height), border_radius=6)
            surface.blit(shadow_surf, (self.rect.x, self.rect.y + 2))

        # 2. Body fill and borders
        if self.is_active:
            bg = (min(255, self.active_color[0] // 3 + self.bg_color[0]),
                  min(255, self.active_color[1] // 3 + self.bg_color[1]),
                  min(255, self.active_color[2] // 3 + self.bg_color[2]))
            border = self.active_color
            border_w = 2
        elif self.is_hovered:
            bg = (min(255, self.bg_color[0] + 20), min(255, self.bg_color[1] + 20), min(255, self.bg_color[2] + 26))
            border = COLOR_CYAN_LIGHT
            border_w = 2
        else:
            bg = self.bg_color
            border = self.border_color
            border_w = 1

        pygame.draw.rect(surface, bg, draw_rect, border_radius=6)

        # Outer glow on active/hover
        if self.is_active or self.is_hovered:
            glow_surf = pygame.Surface((draw_rect.width + 4, draw_rect.height + 4), pygame.SRCALPHA)
            glow_col = (*border[:3], 45)
            pygame.draw.rect(glow_surf, glow_col, (0, 0, draw_rect.width + 4, draw_rect.height + 4), border_radius=8)
            surface.blit(glow_surf, (draw_rect.x - 2, draw_rect.y - 2))

        pygame.draw.rect(surface, border, draw_rect, border_w, border_radius=6)

        # Click ripple flash
        if self.ripple_timer > 0:
            alpha = int((self.ripple_timer / 0.25) * 120)
            rip_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            rip_surf.fill((255, 255, 255, alpha))
            surface.blit(rip_surf, (draw_rect.x, draw_rect.y))

        # Text & Vector Icon Assembly
        txt_col = COLOR_TEXT_MAIN if (self.is_active or self.is_hovered) else self.text_color
        
        # Check text length against button width
        display_text = self.text
        max_txt_w = draw_rect.width - (36 if self.icon else 14)
        if self.font.size(display_text)[0] > max_txt_w:
            while display_text and self.font.size(display_text + "...")[0] > max_txt_w:
                display_text = display_text[:-1]
            display_text = display_text.rstrip() + "..."
        txt_surf = self.font.render(display_text, True, txt_col)

        icon_sz = min(20, draw_rect.height - 12) if self.icon else 0
        total_content_w = txt_surf.get_width() + (icon_sz + 8 if self.icon else 0)

        if self.subtext and self.subfont:
            total_h = txt_surf.get_height() + 16
            content_x = draw_rect.x + max(8, (draw_rect.width - total_content_w) // 2)
            content_y = draw_rect.y + (draw_rect.height - total_h) // 2

            if self.icon:
                draw_vector_icon(surface, self.icon, content_x, content_y + (txt_surf.get_height() - icon_sz) // 2, icon_sz, border)
                tx = content_x + icon_sz + 8
            else:
                tx = content_x
            surface.blit(txt_surf, (tx, content_y))

            sub_col = self.active_color if self.is_active else COLOR_TEXT_MUTED
            sub_w = draw_rect.width - 16
            sub_display = self.subtext
            if self.subfont.size(sub_display)[0] > sub_w:
                while sub_display and self.subfont.size(sub_display + "...")[0] > sub_w:
                    sub_display = sub_display[:-1]
                sub_display = sub_display.rstrip() + "..."
            sub_surf = self.subfont.render(sub_display, True, sub_col)
            sx = draw_rect.x + max(8, (draw_rect.width - sub_surf.get_width()) // 2)
            surface.blit(sub_surf, (sx, content_y + txt_surf.get_height() + 3))

        else:
            content_x = draw_rect.x + max(6, (draw_rect.width - total_content_w) // 2)
            content_y = draw_rect.y + (draw_rect.height - txt_surf.get_height()) // 2

            if self.icon:
                icon_y = draw_rect.y + (draw_rect.height - icon_sz) // 2
                draw_vector_icon(surface, self.icon, content_x, icon_y, icon_sz, border)
                tx = content_x + icon_sz + 8
            else:
                tx = content_x
            surface.blit(txt_surf, (tx, content_y))


# -----------------------------------------------------------------------------
# Weather & Particle Systems
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Dynamic Weather, Lighting & Particle Systems
# -----------------------------------------------------------------------------
class WeatherSystem:
    def __init__(self, bounds: Tuple[int, int]):
        self.max_x, self.max_y = bounds
        self.rain_drops = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(13, 20)]
            for _ in range(160)
        ]
        self.rain_splashes: List[List[float]] = []  # [x, y, radius, life, max_life]
        self.snow_flakes = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(1.2, 3.2), random.uniform(0.6, 1.8)]
            for _ in range(95)
        ]
        self.sparks: List[List[float]] = []
        self.lightning_flash: float = 0.0

        # Drifting Cloud Shadows
        self.clouds = [
            {"x": -100.0, "y": 80.0, "w": 380, "h": 160, "speed": 16.0},
            {"x": 350.0, "y": 420.0, "w": 460, "h": 200, "speed": 22.0},
            {"x": 800.0, "y": 700.0, "w": 320, "h": 140, "speed": 14.0}
        ]

        # Atmospheric Fireflies
        self.fireflies = [
            [random.uniform(40, self.max_x - 40), random.uniform(40, self.max_y - 40), random.uniform(0, math.pi * 2), random.uniform(0.8, 2.2)]
            for _ in range(22)
        ]

        # Campfire Smoke Particles: [x, y, dx, dy, size, max_size, life, max_life]
        self.smoke_particles: List[List[float]] = []

        # Breath Vapor: [x, y, dx, dy, size, life, max_life]
        self.breath_particles: List[List[float]] = []

        # Stress Sweat Drops: [x, y, dx, dy, life, max_life]
        self.sweat_particles: List[List[float]] = []

    def update(self, event: str, dt: float, hour: int = 12):
        # Update clouds
        for c in self.clouds:
            c["x"] += c["speed"] * dt
            if c["x"] > self.max_x + 200:
                c["x"] = -c["w"] - 100
                c["y"] = random.uniform(40, self.max_y - 200)

        # Update fireflies
        for ff in self.fireflies:
            ff[2] += ff[3] * dt
            ff[0] += math.cos(ff[2]) * 0.8 * (dt * 60)
            ff[1] += math.sin(ff[2] * 0.7) * 0.6 * (dt * 60)
            if ff[0] < 20: ff[0] = self.max_x - 30
            elif ff[0] > self.max_x - 20: ff[0] = 30
            if ff[1] < 20: ff[1] = self.max_y - 30
            elif ff[1] > self.max_y - 20: ff[1] = 30

        # Update smoke
        kept_smoke = []
        for sm in self.smoke_particles:
            sm[0] += sm[2] * (dt * 60)
            sm[1] += sm[3] * (dt * 60)
            sm[4] = min(sm[5], sm[4] + dt * 6.0)
            sm[6] -= dt
            if sm[6] > 0:
                kept_smoke.append(sm)
        self.smoke_particles = kept_smoke

        # Update breath vapor
        kept_breath = []
        for bp in self.breath_particles:
            bp[0] += bp[2] * (dt * 60)
            bp[1] += bp[3] * (dt * 60)
            bp[4] += dt * 3.0
            bp[5] -= dt
            if bp[5] > 0:
                kept_breath.append(bp)
        self.breath_particles = kept_breath

        # Update sweat drops
        kept_sweat = []
        for sw in self.sweat_particles:
            sw[0] += sw[2] * (dt * 60)
            sw[1] += sw[3] * (dt * 60)
            sw[4] -= dt
            if sw[4] > 0:
                kept_sweat.append(sw)
        self.sweat_particles = kept_sweat

        # Storm rain & splashes
        if event == "storm":
            if self.lightning_flash > 0:
                self.lightning_flash = max(0.0, self.lightning_flash - dt * 2.5)
            elif random.random() < 0.008:
                self.lightning_flash = 0.55

            for drop in self.rain_drops:
                drop[0] -= 5.0 * (dt * 60)
                drop[1] += drop[2] * (dt * 60)
                if drop[1] > self.max_y:
                    if random.random() < 0.25:
                        self.rain_splashes.append([drop[0], self.max_y - random.uniform(0, 10), 1.0, 0.25, 0.25])
                    drop[1] = 0
                    drop[0] = random.uniform(0, self.max_x + 100)
                if drop[0] < 0:
                    drop[0] = self.max_x

            kept_splashes = []
            for sp in self.rain_splashes:
                sp[2] += dt * 14.0
                sp[3] -= dt
                if sp[3] > 0:
                    kept_splashes.append(sp)
            self.rain_splashes = kept_splashes

        # Cold night snow
        if event == "cold_night":
            for flake in self.snow_flakes:
                flake[0] += math.sin(flake[1] * 0.05) * 1.3 * (dt * 60)
                flake[1] += flake[3] * (dt * 60)
                if flake[1] > self.max_y:
                    flake[1] = 0
                    flake[0] = random.uniform(0, self.max_x)

        kept_sparks = []
        for s in self.sparks:
            s[0] += s[2] * (dt * 60)
            s[1] += s[3] * (dt * 60)
            s[4] -= dt
            if s[4] > 0:
                kept_sparks.append(s)
        self.sparks = kept_sparks

    def add_action_particles(self, x: float, y: float, action: str):
        color = ACTION_COLORS.get(action, COLOR_CYAN)
        count = 16 if action in ("build_shelter", "forage", "drink") else 10
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 4.5)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed - 1.5
            life = random.uniform(0.5, 1.1)
            self.sparks.append([x, y, dx, dy, life, life, color])

    def add_smoke_puff(self, x: float, y: float):
        if len(self.smoke_particles) < 35:
            dx = random.uniform(-0.3, 0.5)
            dy = random.uniform(-1.2, -0.6)
            life = random.uniform(1.2, 2.0)
            self.smoke_particles.append([x, y, dx, dy, 2.0, 9.0, life, life])

    def add_breath_puff(self, x: float, y: float):
        if len(self.breath_particles) < 15:
            dx = random.uniform(0.4, 0.9)
            dy = random.uniform(-0.6, -0.2)
            life = random.uniform(0.8, 1.4)
            self.breath_particles.append([x, y, dx, dy, 2.0, life, life])

    def add_sweat_drop(self, x: float, y: float):
        if len(self.sweat_particles) < 8:
            dx = random.uniform(0.5, 1.2)
            dy = random.uniform(0.8, 1.6)
            self.sweat_particles.append([x, y, dx, dy, 0.45, 0.45])

    def draw_cloud_shadows(self, surface: pygame.Surface):
        for c in self.clouds:
            cloud_surf = pygame.Surface((c["w"], c["h"]), pygame.SRCALPHA)
            # Soft layered cloud ellipses
            pygame.draw.ellipse(cloud_surf, (0, 0, 0, 30), (0, 0, c["w"], c["h"]))
            pygame.draw.ellipse(cloud_surf, (0, 0, 0, 20), (int(c["w"] * 0.15), int(c["h"] * 0.15), int(c["w"] * 0.7), int(c["h"] * 0.7)))
            surface.blit(cloud_surf, (int(c["x"]), int(c["y"])))

    def draw_fireflies(self, surface: pygame.Surface, is_dark: bool):
        if not is_dark:
            return
        t_time = time.time()
        for ff in self.fireflies:
            glow = (math.sin(t_time * 4.0 + ff[2]) + 1.0) * 0.5
            if glow > 0.2:
                alpha = int(glow * 220)
                fx, fy = int(ff[0]), int(ff[1])
                glow_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (220, 252, 60, alpha // 2), (6, 6), 5)
                pygame.draw.circle(glow_surf, (254, 240, 138, alpha), (6, 6), 2)
                surface.blit(glow_surf, (fx - 6, fy - 6))

    def draw_particles(self, surface: pygame.Surface, event: str):
        # Campfire smoke
        for sm in self.smoke_particles:
            ratio = sm[6] / sm[7]
            alpha = int(ratio * 90)
            sz = int(sm[4])
            if sz > 0 and alpha > 0:
                sm_surf = pygame.Surface((sz * 2 + 4, sz * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(sm_surf, (200, 210, 220, alpha), (sz + 2, sz + 2), sz)
                surface.blit(sm_surf, (int(sm[0]) - sz, int(sm[1]) - sz))

        # Breath vapor
        for bp in self.breath_particles:
            ratio = bp[5] / bp[6]
            alpha = int(ratio * 110)
            sz = max(1, int(bp[4]))
            b_surf = pygame.Surface((sz * 2 + 2, sz * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(b_surf, (240, 245, 255, alpha), (sz + 1, sz + 1), sz)
            surface.blit(b_surf, (int(bp[0]) - sz, int(bp[1]) - sz))

        # Sweat drops
        for sw in self.sweat_particles:
            alpha = int((sw[4] / sw[5]) * 240)
            sw_surf = pygame.Surface((6, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(sw_surf, (56, 189, 248, alpha), (0, 0, 4, 6))
            surface.blit(sw_surf, (int(sw[0]), int(sw[1])))

        # Lightning Flash
        if event == "storm" and self.lightning_flash > 0:
            flash_surf = pygame.Surface((self.max_x, self.max_y), pygame.SRCALPHA)
            alpha = int(self.lightning_flash * 190)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, (0, 0))

        # Storm rain & water ripples
        if event == "storm":
            for drop in self.rain_drops:
                x, y = int(drop[0]), int(drop[1])
                pygame.draw.line(surface, (160, 205, 250, 190), (x, y), (x - 4, y + 11), 1)

            for sp in self.rain_splashes:
                alpha = int((sp[3] / sp[4]) * 170)
                r = int(sp[2])
                if r > 1:
                    sp_surf = pygame.Surface((r * 2 + 4, r + 4), pygame.SRCALPHA)
                    pygame.draw.ellipse(sp_surf, (186, 230, 253, alpha), (2, 2, r * 2, r), 1)
                    surface.blit(sp_surf, (int(sp[0]) - r, int(sp[1]) - r // 2))

        # Cold night swirling snow
        elif event == "cold_night":
            for flake in self.snow_flakes:
                x, y = int(flake[0]), int(flake[1])
                pygame.draw.circle(surface, (245, 250, 255, 220), (x, y), int(flake[2]))

        # Action Sparks
        for s in self.sparks:
            color = s[6]
            size = max(1, int((s[4] / s[5]) * 4))
            pygame.draw.circle(surface, color, (int(s[0]), int(s[1])), size)


class IslandVisualizerApp:
    def __init__(self, seed: int = 101, mind_type: str = "quantum", noise_source: str = "ibm_hardware", start_screen: str = "home"):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Stranded: 2D Quantum Island & Survival Engine")

        # Query physical desktop resolution before window creation
        display_info = pygame.display.Info()
        self.desktop_w = max(1024, display_info.current_w)
        self.desktop_h = max(720, display_info.current_h)

        # Select optimal windowed resolution fitting comfortably within desktop workspace
        if self.desktop_w >= 1800 and self.desktop_h >= 1050:
            self.window_w, self.window_h = 1600, 900
        elif self.desktop_w >= 1500 and self.desktop_h >= 860:
            self.window_w, self.window_h = 1440, 810
        else:
            self.window_w, self.window_h = 1280, 720

        # Virtual Canvas Setup
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Crisp High-DPI Typography
        self.font_hero = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 30, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 18, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 14, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13)
        self.font_mono = pygame.font.SysFont("Consolas, Courier New, monospace", 12)
        self.font_bubble = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 12, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 11)

        # Flow States: "home" | "sim"
        self.app_state = start_screen
        self.show_debrief_modal = False
        self.show_history_overlay = False

        # Config Parameters
        self.seed = seed
        self.mind_type = mind_type
        self.noise_source = noise_source
        self.max_steps = 24

        # Simulation Runtime State
        self.step_idx = 0
        self.is_paused = False
        self.step_delay = 0.8
        self.last_step_time = time.time()
        self.speed_multiplier = 1.0

        # Simulation & Reconnaissance Mini-Map
        self._init_simulation()
        self.preview_mini_map = self._generate_mini_map(self.seed, size=300)

        # Visuals & Micro-Animation Dynamics
        self.weather = WeatherSystem((MAP_SIZE, MAP_SIZE))
        self.char_screen_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2.0)
        self.char_screen_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2.0)
        self.char_bob = 0.0
        self.facing_dir = "down"  # "left" | "right" | "up" | "down"
        self.walk_phase = 0.0
        self.footsteps: List[List[float]] = []  # [x, y, birth_time, is_snow]
        self.breath_timer = 0.0
        self.sweat_timer = 0.0
        self.smoke_timer = 0.0
        self.bubble_text = "Awakening on uncharted shores..."
        self.bubble_timer = 3.5
        self.selected_tile: Optional[Tuple[int, int]] = None

        # Build Interactive Button Layouts
        self._build_home_buttons()
        self._build_sim_buttons()

    def toggle_fullscreen(self):
        """Toggles between Windowed and Fullscreen modes with automatic aspect-ratio scaling."""
        self.is_fullscreen = not self.is_fullscreen
        try:
            if self.is_fullscreen:
                # Use native desktop resolution (0, 0) for true borderless fullscreen
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        except Exception:
            try:
                if self.is_fullscreen:
                    self.screen = pygame.display.set_mode((self.desktop_w, self.desktop_h), pygame.FULLSCREEN)
                else:
                    self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
            except Exception:
                pass

    def get_virtual_mouse_pos(self) -> Tuple[int, int]:
        """Maps physical window/fullscreen mouse coordinates back into the virtual 1600x900 canvas."""
        raw_x, raw_y = pygame.mouse.get_pos()
        sw, sh = self.screen.get_size()
        if sw == WINDOW_WIDTH and sh == WINDOW_HEIGHT:
            return raw_x, raw_y

        scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
        if scale <= 0:
            return raw_x, raw_y

        scaled_w = int(WINDOW_WIDTH * scale)
        scaled_h = int(WINDOW_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2

        virt_x = int((raw_x - offset_x) / scale)
        virt_y = int((raw_y - offset_y) / scale)
        return max(0, min(WINDOW_WIDTH - 1, virt_x)), max(0, min(WINDOW_HEIGHT - 1, virt_y))

    def _generate_mini_map(self, seed: int, size: int = 300) -> pygame.Surface:
        surf = pygame.Surface((size, size))
        surf.fill((20, 48, 80))  # Deep rich ocean
        w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=seed)
        t_sz = size / GRID_DIM

        # Draw shallow reef buffer around coastlines
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = w.get_tile(x, y)
                rx, ry = int(x * t_sz), int(y * t_sz)
                rw = math.ceil(t_sz)
                if tile == 0:
                    has_land = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and w.get_tile(x + dx, y + dy) != 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if (x, y) in w.freshwater_tiles:
                        pygame.draw.rect(surf, (56, 189, 248), (rx, ry, rw, rw))
                    elif has_land:
                        pygame.draw.rect(surf, (38, 142, 178), (rx, ry, rw, rw))
                elif tile == 1:
                    has_water = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and w.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    pygame.draw.rect(surf, (224, 182, 110) if has_water else (92, 165, 58), (rx, ry, rw, rw))
                elif tile == 2:
                    pygame.draw.rect(surf, (24, 105, 48), (rx, ry, rw, rw))
                elif tile == 3:
                    pygame.draw.rect(surf, (120, 135, 155), (rx, ry, rw, rw))
                elif tile == 4:
                    pygame.draw.rect(surf, (195, 125, 30), (rx, ry, rw, rw))

        # Spawn indicator (red dot with white border)
        sx, sy = int(w.spawn_pos[0] * t_sz), int(w.spawn_pos[1] * t_sz)
        pygame.draw.circle(surf, COLOR_RED, (sx, sy), 6)
        pygame.draw.circle(surf, COLOR_TEXT_MAIN, (sx, sy), 4)
        return surf

    def _build_home_buttons(self):
        col2_x = 480
        top_y = 115

        # Fullscreen Toggle Button on Home Screen
        self.btn_home_fs = UIButton(
            (WINDOW_WIDTH - 170, 24, 140, 36), "Fullscreen", self.font_body,
            bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen"
        )

        # 1. Mind Toggle Cards
        card_w = 515
        self.btn_mind_quantum = UIButton(
            (col2_x + 24, top_y + 36, card_w, 80), "2-Qubit Quantum Mind", self.font_title,
            subtext="Non-commuting belief rotations + real delay decoherence under stress",
            subfont=self.font_small, active_color=COLOR_PURPLE, icon="quantum"
        )
        self.btn_mind_classical = UIButton(
            (col2_x + 555, top_y + 36, card_w, 80), "Classical Rational Mind", self.font_title,
            subtext="Deterministic utility argmax derived from published ATUS summary tables",
            subfont=self.font_small, active_color=COLOR_BLUE, icon="classical"
        )

        # 2. Preset Island Map Buttons (2x2 Grid)
        self.preset_buttons: List[UIButton] = []
        p_y = top_y + 165
        for i, preset in enumerate(PRESETS):
            px = col2_x + 24 + (i % 2) * 531
            py = p_y + (i // 2) * 56
            btn = UIButton((px, py, card_w, 48), preset["label"], self.font_sub,
                           subtext=preset["tag"], subfont=self.font_small, active_color=preset["color"])
            self.preset_buttons.append(btn)

        # 3. Seed Steppers
        s_y = top_y + 300
        self.btn_seed_m100 = UIButton((col2_x + 24, s_y, 65, 38), "-100", self.font_body)
        self.btn_seed_m10 = UIButton((col2_x + 95, s_y, 55, 38), "-10", self.font_body)
        self.btn_seed_m1 = UIButton((col2_x + 156, s_y, 45, 38), "-1", self.font_body)
        self.btn_seed_p1 = UIButton((col2_x + 575, s_y, 45, 38), "+1", self.font_body)
        self.btn_seed_p10 = UIButton((col2_x + 626, s_y, 55, 38), "+10", self.font_body)
        self.btn_seed_p100 = UIButton((col2_x + 687, s_y, 65, 38), "+100", self.font_body)
        self.btn_seed_rand = UIButton((col2_x + 768, s_y, 270, 38), "Random Island", self.font_sub,
                                      active_color=COLOR_YELLOW, icon="random")

        # 4. Step Number Buttons
        self.step_buttons: List[UIButton] = []
        step_choices = [12, 24, 36, 48]
        st_y = top_y + 395
        btn_w = 250
        for i, steps in enumerate(step_choices):
            sx = col2_x + 24 + i * (btn_w + 15)
            btn = UIButton((sx, st_y, btn_w, 44), f"{steps} Steps ({steps*2}h)", self.font_sub, active_color=COLOR_CYAN)
            self.step_buttons.append(btn)

        # 5. Launch Button
        self.btn_launch = UIButton(
            (col2_x + 24, top_y + 490, 1046, 68), "LAUNCH SURVIVAL SIMULATION", self.font_hero,
            bg_color=(21, 128, 61), active_color=COLOR_GREEN, icon="launch"
        )

    def _build_sim_buttons(self):
        # Map view top navigation bar buttons
        self.btn_nav_home = UIButton((14, 10, 105, 32), "Menu", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="menu")
        self.btn_nav_pause = UIButton((127, 10, 100, 32), "Pause", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_YELLOW, icon="pause")
        self.btn_nav_step = UIButton((235, 10, 100, 32), "Step >", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_GREEN, icon="step")
        self.btn_nav_speed = UIButton((343, 10, 120, 32), "Speed 1.0x", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="speed")
        self.btn_nav_mind = UIButton((471, 10, 130, 32), "Quantum", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_PURPLE, icon="quantum")
        self.btn_nav_log = UIButton((609, 10, 130, 32), "Action Log", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="log")
        self.btn_nav_fs = UIButton((747, 10, 138, 32), "Fullscreen", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen")

        # Debrief modal buttons
        mx = WINDOW_WIDTH // 2
        my = WINDOW_HEIGHT // 2
        self.btn_modal_replay = UIButton((mx - 270, my + 175, 160, 46), "Replay Run", self.font_sub, bg_color=(37, 99, 235), icon="replay")
        self.btn_modal_switch = UIButton((mx - 95, my + 175, 190, 46), "Compare Mind", self.font_sub, bg_color=COLOR_PURPLE, icon="compare")
        self.btn_modal_home = UIButton((mx + 110, my + 175, 160, 46), "Home Menu", self.font_sub, bg_color=(51, 65, 85), icon="menu")
        self.btn_modal_close = UIButton((mx + 360, my - 225, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

        # History log modal close
        self.btn_hist_close = UIButton((WINDOW_WIDTH // 2 + 500, 45, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

    def _init_simulation(self):
        self.world = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=self.seed)
        self.agent = SurvivalAgent(start_pos=self.world.spawn_pos)
        self.event_gen = EventGenerator(seed=self.seed)
        self.decide_fn = contracts.quantum_decide if self.mind_type == "quantum" else contracts.classical_decide
        self.history: List[Dict[str, Any]] = []
        self.current_decision: Dict[str, Any] = {
            "action": "none",
            "probs": {a: 1.0 / len(contracts.ACTIONS) for a in contracts.ACTIONS},
            "reason": "Initial baseline belief state."
        }
        self.current_event = "none"
        self.step_idx = 0
        self.show_debrief_modal = False
        self.show_history_overlay = False
        self.is_paused = False

    def step_forward(self):
        """Advances the simulation by one 2-hour step."""
        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            return

        # 1. State snapshot
        decision_state = self.agent.get_state()
        in_shelter = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])

        # 2. Environmental Hazard
        event = self.event_gen.step_event(
            day=self.agent.day,
            hour=self.agent.hour,
            current_pos=self.agent.pos,
            in_shelter=in_shelter,
            injured=self.agent.injured
        )
        self.current_event = event
        self.agent.apply_event(event, in_shelter=in_shelter)

        # 3. Decision
        decision = self.decide_fn(self.agent.get_state())
        contracts.validate_decision(decision)
        self.current_decision = decision
        action = decision["action"]

        # 4. Action Execution
        narrative = self.agent.execute_action(action, self.world)
        in_shelter_after = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])
        self.agent.step_decay(in_shelter=in_shelter_after)

        # 5. Visual Particles & Speech Bubble
        self.weather.add_action_particles(self.char_screen_x, self.char_screen_y, action)
        clean_narrative = narrative.split(';')[0]
        self.bubble_text = f"{action.upper()}: {clean_narrative}"
        self.bubble_timer = 2.8

        # 6. Record
        self.step_idx += 1
        self.history.append({
            "t": self.step_idx,
            "state": self.agent.get_state(),
            "event": event,
            "action": action,
            "decision": decision,
            "narrative": narrative
        })

        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            now = time.time()
            virt_pos = self.get_virtual_mouse_pos()

            any_hovered = self._update_hovers(virt_pos)
            if any_hovered:
                set_cursor_safely(pygame.SYSTEM_CURSOR_HAND)
            else:
                set_cursor_safely(pygame.SYSTEM_CURSOR_ARROW)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

                elif ev.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:
                        self.window_w = max(960, ev.w)
                        self.window_h = max(540, ev.h)
                        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_F11 or (ev.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_ALT):
                        self.toggle_fullscreen()

                    elif self.app_state == "home":
                        if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self._init_simulation()
                            self.app_state = "sim"
                    else:
                        if ev.key == pygame.K_SPACE and not self.show_debrief_modal:
                            self.is_paused = not self.is_paused
                        elif ev.key in (pygame.K_RIGHT, pygame.K_n) and not self.show_debrief_modal:
                            self.step_forward()
                        elif ev.key in (pygame.K_ESCAPE, pygame.K_h):
                            self.app_state = "home"
                        elif ev.key in (pygame.K_TAB, pygame.K_l):
                            self.show_history_overlay = not self.show_history_overlay
                        elif ev.key == pygame.K_r:
                            self._init_simulation()
                        elif ev.key == pygame.K_q:
                            self.mind_type = "classical" if self.mind_type == "quantum" else "quantum"
                            self.decide_fn = contracts.quantum_decide if self.mind_type == "quantum" else contracts.classical_decide
                        elif ev.key == pygame.K_1:
                            self.speed_multiplier = 1.0
                        elif ev.key == pygame.K_2:
                            self.speed_multiplier = 2.5
                        elif ev.key == pygame.K_3:
                            self.speed_multiplier = 6.0

                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        if self.app_state == "home":
                            self._handle_home_click(virt_pos)
                        else:
                            self._handle_sim_click(virt_pos)

            # Auto-stepping logic
            if self.app_state == "sim" and not self.is_paused and not self.show_debrief_modal and not self.show_history_overlay:
                if self.agent.is_alive and self.step_idx < self.max_steps:
                    effective_delay = self.step_delay / self.speed_multiplier
                    if now - self.last_step_time >= effective_delay:
                        self.step_forward()
                        self.last_step_time = now

            # Smooth Character Interpolation, Facing & Micro-Particles
            if self.app_state == "sim":
                target_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2.0)
                target_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2.0)
                dx = target_x - self.char_screen_x
                dy = target_y - self.char_screen_y
                dist = math.hypot(dx, dy)

                if dist > 1.2:
                    self.char_bob = math.sin(self.walk_phase) * 1.8
                    self.walk_phase += dt * 14.0
                    # Determine directional facing
                    if abs(dx) > abs(dy) * 0.8:
                        self.facing_dir = "right" if dx > 0 else "left"
                    else:
                        self.facing_dir = "down" if dy > 0 else "up"

                    # Add environmental footsteps
                    tile_at_char = self.world.get_tile(int(self.char_screen_x / TILE_SIZE), int(self.char_screen_y / TILE_SIZE))
                    if tile_at_char in (1, 3):  # Sand beach or mountain snow
                        if not self.footsteps or math.hypot(self.char_screen_x - self.footsteps[-1][0], self.char_screen_y - self.footsteps[-1][1]) > 14.0:
                            is_snow = (tile_at_char == 3)
                            self.footsteps.append([self.char_screen_x, self.char_screen_y, time.time(), 1.0 if is_snow else 0.0])
                            if len(self.footsteps) > 40:
                                self.footsteps.pop(0)
                else:
                    self.char_bob = math.sin(now * 3.0) * 0.6

                self.char_screen_x += dx * min(1.0, 10.0 * dt)
                self.char_screen_y += dy * min(1.0, 10.0 * dt)

                # Micro-particle timers
                # Campfire smoke from shelters
                self.smoke_timer -= dt
                if self.smoke_timer <= 0:
                    self.smoke_timer = 0.35
                    for sy in range(GRID_DIM):
                        for sx in range(GRID_DIM):
                            if self.world.get_tile(sx, sy) == 4:
                                s_px = sx * TILE_SIZE + TILE_SIZE / 2.0
                                s_py = sy * TILE_SIZE + TILE_SIZE / 2.0 - 4
                                self.weather.add_smoke_puff(s_px, s_py)

                # Cold breath vapor
                if self.agent.needs.get("warmth", 1.0) < 0.35 or self.current_event == "cold_night":
                    self.breath_timer -= dt
                    if self.breath_timer <= 0:
                        self.breath_timer = random.uniform(1.2, 2.0)
                        self.weather.add_breath_puff(self.char_screen_x + (4 if self.facing_dir != "left" else -4), self.char_screen_y - 12)

                # Stress sweat droplets
                if self.agent.stress > 0.65:
                    self.sweat_timer -= dt
                    if self.sweat_timer <= 0:
                        self.sweat_timer = random.uniform(0.8, 1.5)
                        self.weather.add_sweat_drop(self.char_screen_x + (5 if self.facing_dir != "left" else -5), self.char_screen_y - 10)

                self.weather.update(self.current_event, dt, hour=self.agent.hour)
                if self.bubble_timer > 0:
                    self.bubble_timer -= dt

            self.draw(virt_pos)
            self.present()

        pygame.quit()

    def _update_hovers(self, pos: Tuple[int, int]) -> bool:
        hovered = False
        if self.app_state == "home":
            buttons = [self.btn_home_fs, self.btn_mind_quantum, self.btn_mind_classical,
                       self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1,
                       self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100,
                       self.btn_seed_rand, self.btn_launch] + self.preset_buttons + self.step_buttons
            for b in buttons:
                if b.check_hover(pos):
                    hovered = True
        else:
            if self.show_history_overlay:
                if self.btn_hist_close.check_hover(pos):
                    hovered = True
            elif self.show_debrief_modal:
                buttons = [self.btn_modal_replay, self.btn_modal_switch, self.btn_modal_home, self.btn_modal_close]
                for b in buttons:
                    if b.check_hover(pos):
                        hovered = True
            else:
                buttons = [self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step,
                           self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_log, self.btn_nav_fs]
                for b in buttons:
                    if b.check_hover(pos):
                        hovered = True
        return hovered

    def present(self):
        """Scales the 1600x900 virtual canvas to physical screen maintaining aspect ratio with letterboxing."""
        sw, sh = self.screen.get_size()
        scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
        if scale <= 0:
            scale = 1.0
        scaled_w = int(WINDOW_WIDTH * scale)
        scaled_h = int(WINDOW_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2

        if sw == WINDOW_WIDTH and sh == WINDOW_HEIGHT:
            self.screen.blit(self.canvas, (0, 0))
        else:
            scaled_surf = pygame.transform.smoothscale(self.canvas, (scaled_w, scaled_h))
            self.screen.fill((5, 8, 18))
            self.screen.blit(scaled_surf, (offset_x, offset_y))
        pygame.display.flip()

    # -------------------------------------------------------------------------
    # Input Handling Helpers
    # -------------------------------------------------------------------------
    def _handle_home_click(self, pos: Tuple[int, int]):
        if self.btn_home_fs.check_hover(pos):
            self.btn_home_fs.trigger_click()
            self.toggle_fullscreen()
            return

        if self.btn_mind_quantum.check_hover(pos):
            self.btn_mind_quantum.trigger_click()
            self.mind_type = "quantum"
        elif self.btn_mind_classical.check_hover(pos):
            self.btn_mind_classical.trigger_click()
            self.mind_type = "classical"

        for i, p_btn in enumerate(self.preset_buttons):
            if p_btn.check_hover(pos):
                p_btn.trigger_click()
                self.seed = PRESETS[i]["seed"]
                self.preview_mini_map = self._generate_mini_map(self.seed, size=300)

        seed_changed = False
        if self.btn_seed_m100.check_hover(pos):
            self.btn_seed_m100.trigger_click()
            self.seed = max(1, self.seed - 100)
            seed_changed = True
        elif self.btn_seed_m10.check_hover(pos):
            self.btn_seed_m10.trigger_click()
            self.seed = max(1, self.seed - 10)
            seed_changed = True
        elif self.btn_seed_m1.check_hover(pos):
            self.btn_seed_m1.trigger_click()
            self.seed = max(1, self.seed - 1)
            seed_changed = True
        elif self.btn_seed_p1.check_hover(pos):
            self.btn_seed_p1.trigger_click()
            self.seed += 1
            seed_changed = True
        elif self.btn_seed_p10.check_hover(pos):
            self.btn_seed_p10.trigger_click()
            self.seed += 10
            seed_changed = True
        elif self.btn_seed_p100.check_hover(pos):
            self.btn_seed_p100.trigger_click()
            self.seed += 100
            seed_changed = True
        elif self.btn_seed_rand.check_hover(pos):
            self.btn_seed_rand.trigger_click()
            self.seed = random.randint(10, 9999)
            seed_changed = True

        if seed_changed:
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)

        step_choices = [12, 24, 36, 48]
        for i, s_btn in enumerate(self.step_buttons):
            if s_btn.check_hover(pos):
                s_btn.trigger_click()
                self.max_steps = step_choices[i]

        if self.btn_launch.check_hover(pos):
            self.btn_launch.trigger_click()
            self._init_simulation()
            self.app_state = "sim"

    def _handle_sim_click(self, pos: Tuple[int, int]):
        if self.show_history_overlay:
            if self.btn_hist_close.check_hover(pos):
                self.btn_hist_close.trigger_click()
                self.show_history_overlay = False
            return

        if self.show_debrief_modal:
            if self.btn_modal_replay.check_hover(pos):
                self.btn_modal_replay.trigger_click()
                self._init_simulation()
            elif self.btn_modal_switch.check_hover(pos):
                self.btn_modal_switch.trigger_click()
                self.mind_type = "classical" if self.mind_type == "quantum" else "quantum"
                self._init_simulation()
            elif self.btn_modal_home.check_hover(pos):
                self.btn_modal_home.trigger_click()
                self.app_state = "home"
            elif self.btn_modal_close.check_hover(pos):
                self.btn_modal_close.trigger_click()
                self.show_debrief_modal = False
            return

        # Top Nav Bar Clicks
        if self.btn_nav_home.check_hover(pos):
            self.btn_nav_home.trigger_click()
            self.app_state = "home"
            return
        elif self.btn_nav_pause.check_hover(pos):
            self.btn_nav_pause.trigger_click()
            self.is_paused = not self.is_paused
            return
        elif self.btn_nav_step.check_hover(pos):
            self.btn_nav_step.trigger_click()
            self.step_forward()
            return
        elif self.btn_nav_speed.check_hover(pos):
            self.btn_nav_speed.trigger_click()
            speeds = [1.0, 2.5, 6.0]
            curr_idx = speeds.index(self.speed_multiplier) if self.speed_multiplier in speeds else 0
            self.speed_multiplier = speeds[(curr_idx + 1) % len(speeds)]
            return
        elif self.btn_nav_mind.check_hover(pos):
            self.btn_nav_mind.trigger_click()
            self.mind_type = "classical" if self.mind_type == "quantum" else "quantum"
            self.decide_fn = contracts.quantum_decide if self.mind_type == "quantum" else contracts.classical_decide
            return
        elif self.btn_nav_log.check_hover(pos):
            self.btn_nav_log.trigger_click()
            self.show_history_overlay = True
            return
        elif self.btn_nav_fs.check_hover(pos):
            self.btn_nav_fs.trigger_click()
            self.toggle_fullscreen()
            return

        # Map Clicks
        mx, my = pos
        if mx < MAP_SIZE and my < MAP_SIZE:
            tx, ty = int(mx / TILE_SIZE), int(my / TILE_SIZE)
            if 0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM:
                self.selected_tile = (tx, ty)

    def draw(self, mouse_pos: Tuple[int, int] = (0, 0)):
        if self.app_state == "home":
            self.draw_home_screen(mouse_pos)
        else:
            self.draw_sim_screen(mouse_pos)

    # -------------------------------------------------------------------------
    # Render Home Screen (State 1)
    # -------------------------------------------------------------------------
    def draw_home_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)
        t_time = time.time()

        # Background subtle ambient ocean waves
        for y in range(0, WINDOW_HEIGHT, 36):
            shift = math.sin(t_time * 1.6 + y * 0.08) * 18
            pygame.draw.line(self.canvas, (18, 28, 48), (0, y + shift), (WINDOW_WIDTH, y + shift), 1)

        # Fullscreen Toggle Button on Home Screen
        self.btn_home_fs.text = "Windowed" if self.is_fullscreen else "Fullscreen"
        self.btn_home_fs.icon = "windowed" if self.is_fullscreen else "fullscreen"
        self.btn_home_fs.check_hover(mouse_pos)
        self.btn_home_fs.draw(self.canvas)

        # Header Title
        title_surf = self.font_hero.render("STRANDED: QUANTUM SURVIVAL ENGINE", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 22))

        sub_str = "Qiskit 2.x  |  2-Qubit Non-Commuting Cognition  |  IBM Hardware Decoherence Modeling"
        sub_surf = self.font_sub.render(sub_str, True, COLOR_CYAN)
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 62))

        # Left Reconnaissance Card: Live Island Mini-Map (430 x 755)
        col1_x = 32
        col1_y = 96
        col1_w = 430
        col1_h = 760
        self.draw_card(col1_x, col1_y, col1_w, col1_h)

        c1_title = self.font_title.render("ISLAND RECONNAISSANCE", True, COLOR_YELLOW)
        self.canvas.blit(c1_title, (col1_x + 22, col1_y + 18))

        # Mini-map container (300 x 300)
        map_box = pygame.Rect(col1_x + (col1_w - 300) // 2, col1_y + 54, 300, 300)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, map_box, 2, border_radius=6)
        self.canvas.blit(self.preview_mini_map, (map_box.x, map_box.y))

        # Spawn dot legend with procedural drawing (Zero unicode squares)
        leg_y = col1_y + 368
        pygame.draw.circle(self.canvas, COLOR_RED, (col1_x + 36, leg_y + 7), 5)
        pygame.draw.circle(self.canvas, COLOR_TEXT_MAIN, (col1_x + 36, leg_y + 7), 3)
        leg_surf = self.font_small.render("Red dot: Initial survivor drop-in spawn coordinate", True, COLOR_TEXT_MUTED)
        self.canvas.blit(leg_surf, (col1_x + 50, leg_y))

        # Terrain Statistics
        stat_y = col1_y + 400
        stats_box = pygame.Rect(col1_x + 20, stat_y, col1_w - 40, 335)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, stats_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, stats_box, 1, border_radius=8)

        temp_w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=self.seed)
        land_tiles = sum(1 for row in temp_w.tiles for t in row if t in (1, 2, 3, 4))
        forest_tiles = sum(1 for row in temp_w.tiles for t in row if t == 2)
        streams = len(temp_w.freshwater_tiles)
        land_pct = int(land_tiles / (GRID_DIM * GRID_DIM) * 100)
        forest_pct = int(forest_tiles / max(1, land_tiles) * 100)

        lines = [
            f"World Seed:       #{self.seed}",
            f"Grid Geometry:    40x40 (1,600 Tiles)",
            f"Land Coverage:    {land_pct}% (Usable Mass)",
            f"Forest Density:   {forest_pct}% (Timber & Food)",
            f"Freshwater:       {str(streams) + ' tiles' if streams > 0 else 'Arid / Sparse'}",
            f"Starting Spawn:   [{temp_w.spawn_pos[0]}, {temp_w.spawn_pos[1]}] (Coastline)",
            f"Decoherence Rate: IBM Hardware Noise",
            f"Contract Engine:  contracts.py (Frozen)"
        ]
        for i, line in enumerate(lines):
            col = COLOR_CYAN if i == 0 else (COLOR_GREEN if i in (2, 3) else COLOR_TEXT_MUTED)
            self.canvas.blit(self.font_mono.render(line, True, col), (stats_box.x + 18, stats_box.y + 18 + i * 36))

        # Right Configuration Card (1088 x 760)
        col2_x = 480
        col2_y = 96
        col2_w = 1088
        col2_h = 760
        self.draw_card(col2_x, col2_y, col2_w, col2_h)

        # 1. Decision Mind Selection
        m_lbl = self.font_title.render("1. Select Cognitive Mind Model", True, COLOR_TEXT_MAIN)
        self.canvas.blit(m_lbl, (col2_x + 24, col2_y + 16))

        self.btn_mind_quantum.is_active = (self.mind_type == "quantum")
        self.btn_mind_classical.is_active = (self.mind_type == "classical")
        self.btn_mind_quantum.check_hover(mouse_pos)
        self.btn_mind_classical.check_hover(mouse_pos)
        self.btn_mind_quantum.draw(self.canvas)
        self.btn_mind_classical.draw(self.canvas)

        # 2. Island Presets & Custom Stepper
        p_lbl = self.font_title.render("2. Select Island Preset or Custom World Seed", True, COLOR_TEXT_MAIN)
        self.canvas.blit(p_lbl, (col2_x + 24, col2_y + 138))

        for i, p_btn in enumerate(self.preset_buttons):
            p_btn.is_active = (self.seed == PRESETS[i]["seed"])
            p_btn.check_hover(mouse_pos)
            p_btn.draw(self.canvas)

        seed_box = pygame.Rect(col2_x + 215, col2_y + 300, 345, 38)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, seed_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, seed_box, 1, border_radius=6)
        seed_txt = self.font_title.render(f"Island World Seed:  #{self.seed}", True, COLOR_YELLOW)
        self.canvas.blit(seed_txt, (seed_box.x + (seed_box.width - seed_txt.get_width()) // 2, seed_box.y + 8))

        for s_btn in (self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1, self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100, self.btn_seed_rand):
            s_btn.check_hover(mouse_pos)
            s_btn.draw(self.canvas)

        # 3. Simulation Duration
        st_lbl = self.font_title.render("3. Simulation Step Horizon (2 Hours per Turn)", True, COLOR_TEXT_MAIN)
        self.canvas.blit(st_lbl, (col2_x + 24, col2_y + 365))

        step_choices = [12, 24, 36, 48]
        for i, st_btn in enumerate(self.step_buttons):
            st_btn.is_active = (self.max_steps == step_choices[i])
            st_btn.check_hover(mouse_pos)
            st_btn.draw(self.canvas)

        # 4. Hero Launch Button
        self.btn_launch.check_hover(mouse_pos)
        self.btn_launch.draw(self.canvas)

        # Quick Reference Hints
        hints_box = pygame.Rect(col2_x + 24, col2_y + 578, 1046, 155)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, hints_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, hints_box, 1, border_radius=8)

        h_title = self.font_sub.render("SIMULATION DYNAMICS & QUANTUM HARDWARE SPECIFICATION", True, COLOR_CYAN)
        self.canvas.blit(h_title, (hints_box.x + 18, hints_box.y + 14))

        bullet_lines = [
            "  * Quantum Mind: Belief states represented as 2-qubit amplitudes with non-commuting projection angles.",
            "  * Order Effect: Experiencing [Storm -> Find Food] yields distinct survival actions compared to [Find Food -> Storm].",
            "  * Hardware Stress: Physiological stress increases delay-gate duration, driving real IBM quantum physical decoherence.",
            "  * Survival Metric: Dehydration triggers lethal failure at 24h, Starvation at 72h. Maintain shelter to reduce exposure."
        ]
        for i, bl in enumerate(bullet_lines):
            self.canvas.blit(self.font_body.render(bl, True, COLOR_TEXT_MUTED), (hints_box.x + 18, hints_box.y + 40 + i * 26))

        tip_str = "Press [ENTER] to Launch  |  [F11] Fullscreen  |  [Q] Toggle Mind Model  |  Decoherence Modeling Active"
        self.canvas.blit(self.font_sub.render(tip_str, True, COLOR_TEXT_HINT), (WINDOW_WIDTH // 2 - 320, WINDOW_HEIGHT - 28))

    # -------------------------------------------------------------------------
    # Render Simulation Screen (State 2)
    # -------------------------------------------------------------------------
    def draw_sim_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)

        # 1. Map Surface (900 x 900)
        self.draw_island_map()

        # 2. Weather & Lighting
        self.draw_atmosphere()

        # 3. Survivor Character & Overhead Bubble
        self.draw_character()

        # 4. Top Map Bar Controls
        self.draw_map_navigation_bar(mouse_pos)

        # 5. Telemetry & Analytics Dashboard (700 x 900)
        self.draw_dashboard()

        # 6. Floating Tile Inspector Tooltip
        self.draw_tile_tooltip(mouse_pos)

        # 7. Modals: Full Action Log Overlay or Debrief Modal
        if self.show_history_overlay:
            self.draw_history_overlay(mouse_pos)
        elif self.show_debrief_modal:
            self.draw_debrief_modal(mouse_pos)

    def draw_map_navigation_bar(self, mouse_pos: Tuple[int, int]):
        bar_bg = pygame.Surface((MAP_SIZE, 52), pygame.SRCALPHA)
        bar_bg.fill((15, 23, 42, 225))
        self.canvas.blit(bar_bg, (0, 0))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (0, 52), (MAP_SIZE, 52), 1)

        self.btn_nav_pause.text = "Play" if self.is_paused else "Pause"
        self.btn_nav_pause.icon = "play" if self.is_paused else "pause"

        self.btn_nav_speed.text = f"Speed {self.speed_multiplier}x"
        self.btn_nav_mind.text = "Quantum" if self.mind_type == "quantum" else "Classical"
        self.btn_nav_mind.icon = "quantum" if self.mind_type == "quantum" else "classical"
        self.btn_nav_mind.active_color = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE

        self.btn_nav_fs.text = "Window" if self.is_fullscreen else "Fullscreen"
        self.btn_nav_fs.icon = "windowed" if self.is_fullscreen else "fullscreen"

        for btn in (self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step, self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_log, self.btn_nav_fs):
            btn.check_hover(mouse_pos)
            btn.draw(self.canvas)

    def draw_island_map(self):
        t_time = time.time()
        # 1. Base Deep Ocean Canvas Fill
        ocean_bg = pygame.Rect(0, 0, MAP_SIZE, MAP_SIZE)
        pygame.draw.rect(self.canvas, (20, 48, 80), ocean_bg)

        # Gentle ambient ocean wave shimmer ribbons
        for wy in range(0, MAP_SIZE, 36):
            w_shift = math.sin(t_time * 1.8 + wy * 0.06) * 14
            pygame.draw.line(self.canvas, (28, 64, 102), (0, wy + w_shift), (MAP_SIZE, wy + w_shift), 1)

        # Pass 1: Ground Terrains, Shallow Reef Lagoons & Shoreline Foam
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = self.world.get_tile(x, y)
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                rect = pygame.Rect(rx, ry, rw, rh)

                if tile == 0:  # Water
                    is_fresh = (x, y) in self.world.freshwater_tiles
                    if is_fresh:
                        # Freshwater stream with animated flow
                        flow = math.sin(t_time * 4.0 + x * 0.6 + y * 0.6) * 22
                        c_stream = (56, max(0, min(255, 189 + int(flow))), 248)
                        pygame.draw.rect(self.canvas, c_stream, rect)
                        pygame.draw.line(self.canvas, (224, 242, 254), (rx + 4, ry + rh // 2), (rx + rw - 4, ry + rh // 2), 2)
                    else:
                        # Check coastal lagoon adjacency
                        has_land = any(
                            0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) != 0
                            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                        )
                        if has_land:
                            # Shallow turquoise lagoon
                            pygame.draw.rect(self.canvas, (38, 142, 178), rect)
                            # Animated shoreline foam tide
                            foam_osc = (math.sin(t_time * 3.0 + x * 0.8 + y * 0.8) + 1.0) * 0.5
                            foam_h = max(2, int(foam_osc * 5))
                            pygame.draw.rect(self.canvas, (225, 248, 255), (rx, ry, rw, foam_h), border_radius=1)

                elif tile == 1:  # Sand / Meadow Plains
                    has_water = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if has_water:
                        # Golden sand beach
                        pygame.draw.rect(self.canvas, (224, 182, 110), rect)
                        # Darker moist tidal edge
                        pygame.draw.rect(self.canvas, (182, 142, 82), (rx, ry, rw, 2))
                        # Shell / pebble specks
                        pygame.draw.rect(self.canvas, (245, 235, 215), (rx + 6, ry + 8, 2, 2))
                    else:
                        # Lush meadow plains
                        pygame.draw.rect(self.canvas, (92, 165, 58), rect)
                        # Grassy texture strokes
                        pygame.draw.line(self.canvas, (115, 188, 72), (rx + 4, ry + 14), (rx + 6, ry + 8), 1)
                        pygame.draw.line(self.canvas, (115, 188, 72), (rx + 14, ry + 16), (rx + 16, ry + 10), 1)
                        # Wildflower micro-dots
                        if (x * 7 + y * 13) % 5 == 0:
                            pygame.draw.circle(self.canvas, (250, 204, 21), (rx + 8, ry + 6), 1)

                elif tile == 2:  # Forest underlay
                    pygame.draw.rect(self.canvas, (65, 128, 48), rect)

                elif tile == 3:  # Mountain foundation
                    pygame.draw.rect(self.canvas, (82, 95, 114), rect)

                elif tile == 4:  # Shelter clearing
                    pygame.draw.rect(self.canvas, (88, 152, 54), rect)

        # Pass 2: Fading Environmental Footstep Tracks
        curr_t = time.time()
        for fs in self.footsteps:
            age = curr_t - fs[2]
            if age < 8.0:
                alpha = int((1.0 - age / 8.0) * 110)
                is_snow = (fs[3] > 0.5)
                f_col = (190, 215, 235, alpha) if is_snow else (160, 125, 70, alpha)
                f_surf = pygame.Surface((4, 6), pygame.SRCALPHA)
                pygame.draw.ellipse(f_surf, f_col, (0, 0, 3, 5))
                self.canvas.blit(f_surf, (int(fs[0]) - 3, int(fs[1]) + 4))
                self.canvas.blit(f_surf, (int(fs[0]) + 1, int(fs[1]) + 4))

        # Pass 3: 2.5D Layered Foliage, Mountain Crags & Shelters (Y-sorted depth)
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = self.world.get_tile(x, y)
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                cx = rx + rw // 2
                cy = ry + rh // 2

                if tile == 2:  # 2.5D Pine Trees with Wind Sway
                    # Ground shadow
                    pygame.draw.ellipse(self.canvas, (0, 0, 0, 65), (cx - 7, cy + 4, 16, 7))
                    # Trunk
                    pygame.draw.rect(self.canvas, (75, 45, 20), (cx - 2, cy + 1, 4, 7), border_radius=1)
                    # Wind sway
                    sway = math.sin(t_time * 2.5 + x * 0.6 + y * 0.4) * 1.8
                    # Tier 1 (Bottom wide dark pine)
                    p_b = [(cx, cy - 4), (cx - 9, cy + 4), (cx + 9, cy + 4)]
                    pygame.draw.polygon(self.canvas, (18, 78, 38), p_b)
                    # Tier 2 (Middle pine)
                    p_m = [(cx + int(sway * 0.5), cy - 9), (cx - 7, cy - 1), (cx + 7, cy - 1)]
                    pygame.draw.polygon(self.canvas, (26, 108, 50), p_m)
                    # Tier 3 (Top sunlit tip)
                    p_t = [(cx + int(sway), cy - 15), (cx - 5, cy - 6), (cx + 5, cy - 6)]
                    pygame.draw.polygon(self.canvas, (40, 142, 68), p_t)

                    # Food Berry Bush
                    if (x, y) in self.world.food_tiles:
                        pygame.draw.circle(self.canvas, (32, 120, 52), (cx + 8, cy + 4), 4)
                        pygame.draw.circle(self.canvas, (220, 38, 38), (cx + 6, cy + 3), 2)
                        pygame.draw.circle(self.canvas, (220, 38, 38), (cx + 9, cy + 2), 2)
                        pygame.draw.circle(self.canvas, (220, 38, 38), (cx + 8, cy + 5), 2)
                        pygame.draw.circle(self.canvas, (254, 202, 202), (cx + 6, cy + 2), 1)

                elif tile == 3:  # 2.5D Shaded Mountain Crags & Alpine Snow
                    # Ground shadow
                    pygame.draw.ellipse(self.canvas, (0, 0, 0, 75), (cx - 6, cy + 5, 20, 8))
                    # Cliff Faces: NW Sunlit / SE Shaded
                    peak = (cx, ry + 1)
                    p_left = (rx + 2, ry + rh - 2)
                    p_right = (rx + rw - 1, ry + rh - 2)
                    p_mid = (cx + 2, ry + rh - 2)
                    # Shaded East Face
                    pygame.draw.polygon(self.canvas, (50, 62, 78), [peak, p_mid, p_right])
                    # Sunlit West Face
                    pygame.draw.polygon(self.canvas, (122, 138, 160), [peak, p_left, p_mid])
                    # Alpine Glacial Snowcap
                    p_snow_l = (cx - 5, ry + 8)
                    p_snow_r = (cx + 6, ry + 8)
                    pygame.draw.polygon(self.canvas, (245, 250, 255), [peak, p_snow_l, (cx, ry + 10), p_snow_r])
                    pygame.draw.polygon(self.canvas, (200, 225, 245), [peak, (cx, ry + 10), p_snow_r])

                elif tile == 4:  # Timber A-Frame Shelter & Campfire
                    # Ground shadow
                    pygame.draw.ellipse(self.canvas, (0, 0, 0, 85), (cx - 8, cy + 3, 20, 8))
                    # Log crossbeams
                    pygame.draw.polygon(self.canvas, (110, 60, 22), [(cx, ry + 2), (rx + 2, ry + rh - 3), (rx + rw - 2, ry + rh - 3)])
                    # Thatched Palm Roof
                    pygame.draw.polygon(self.canvas, (195, 125, 30), [(cx, ry + 4), (rx + 4, ry + rh - 4), (cx + 1, ry + rh - 4)])
                    pygame.draw.polygon(self.canvas, (170, 105, 22), [(cx, ry + 4), (cx + 1, ry + rh - 4), (rx + rw - 4, ry + rh - 4)])
                    # Stone Firepit
                    pygame.draw.circle(self.canvas, (90, 102, 118), (cx, ry + rh - 4), 5)
                    pygame.draw.circle(self.canvas, (45, 52, 62), (cx, ry + rh - 4), 3)
                    # Animated Embers & Flame
                    ember_flicker = int(math.sin(t_time * 10.0) * 45)
                    flame_y = ry + rh - 5 - int(math.sin(t_time * 14.0) * 2)
                    pygame.draw.circle(self.canvas, (245, max(0, min(255, 150 + ember_flicker)), 10), (cx, ry + rh - 4), 3)
                    pygame.draw.polygon(self.canvas, (255, 220, 40), [(cx, flame_y - 3), (cx - 2, flame_y + 1), (cx + 2, flame_y + 1)])

        # Selected Tile Reticle
        if self.selected_tile:
            tx, ty = self.selected_tile
            s_rect = pygame.Rect(int(tx * TILE_SIZE), int(ty * TILE_SIZE), int(TILE_SIZE), int(TILE_SIZE))
            pygame.draw.rect(self.canvas, COLOR_CYAN, s_rect, 2, border_radius=3)
            # Corner brackets
            csz = 4
            pygame.draw.lines(self.canvas, COLOR_TEXT_MAIN, False, [(s_rect.x, s_rect.y + csz), (s_rect.x, s_rect.y), (s_rect.x + csz, s_rect.y)], 2)
            pygame.draw.lines(self.canvas, COLOR_TEXT_MAIN, False, [(s_rect.right - csz, s_rect.y), (s_rect.right, s_rect.y), (s_rect.right, s_rect.y + csz)], 2)
            pygame.draw.lines(self.canvas, COLOR_TEXT_MAIN, False, [(s_rect.x, s_rect.bottom - csz), (s_rect.x, s_rect.bottom), (s_rect.x + csz, s_rect.bottom)], 2)
            pygame.draw.lines(self.canvas, COLOR_TEXT_MAIN, False, [(s_rect.right - csz, s_rect.bottom), (s_rect.right, s_rect.bottom - csz), (s_rect.right, s_rect.bottom)], 2)

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 2)

    def draw_atmosphere(self):
        hour = self.agent.hour

        # 1. Solar Day/Night Color Grading
        if 5 <= hour < 8:  # Dawn: warm golden-amber sunrise glow
            dawn_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            dawn_surf.fill((245, 175, 75, 24))
            self.canvas.blit(dawn_surf, (0, 0))
        elif 17 <= hour < 20:  # Dusk: rich violet-crimson twilight
            dusk_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            dusk_surf.fill((95, 45, 125, 45))
            self.canvas.blit(dusk_surf, (0, 0))
        elif hour >= 20 or hour < 5:  # Night: midnight obsidian navy with radial lighting mask
            # Darkness layer
            light_mask = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            light_mask.fill((10, 18, 38, 145))

            # Carve out campfire light at shelters
            camp_torch = pygame.Surface((200, 200), pygame.SRCALPHA)
            for r in range(95, 0, -6):
                a = int(145 * (1.0 - r / 95.0))
                pygame.draw.circle(camp_torch, (0, 0, 0, a), (100, 100), r)

            for sy in range(GRID_DIM):
                for sx in range(GRID_DIM):
                    if self.world.get_tile(sx, sy) == 4:
                        s_cx = int(sx * TILE_SIZE + TILE_SIZE / 2.0)
                        s_cy = int(sy * TILE_SIZE + TILE_SIZE / 2.0)
                        light_mask.blit(camp_torch, (s_cx - 100, s_cy - 100), special_flags=pygame.BLEND_RGBA_SUB)

            # Carve out survivor torch/lantern pool
            surv_torch = pygame.Surface((160, 160), pygame.SRCALPHA)
            for r in range(75, 0, -5):
                a = int(145 * (1.0 - r / 75.0))
                pygame.draw.circle(surv_torch, (0, 0, 0, a), (80, 80), r)
            cx, cy = int(self.char_screen_x), int(self.char_screen_y)
            light_mask.blit(surv_torch, (cx - 80, cy - 80), special_flags=pygame.BLEND_RGBA_SUB)

            self.canvas.blit(light_mask, (0, 0))

            # Warm amber radial glow over carved areas
            glow_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (254, 180, 60, 45), (cx, cy), 55)
            for sy in range(GRID_DIM):
                for sx in range(GRID_DIM):
                    if self.world.get_tile(sx, sy) == 4:
                        s_cx = int(sx * TILE_SIZE + TILE_SIZE / 2.0)
                        s_cy = int(sy * TILE_SIZE + TILE_SIZE / 2.0)
                        pygame.draw.circle(glow_surf, (249, 115, 22, 60), (s_cx, s_cy), 70)
            self.canvas.blit(glow_surf, (0, 0))

        # 2. Drifting Cumulus Cloud Shadows
        self.weather.draw_cloud_shadows(self.canvas)

        # 3. Night Bioluminescent Fireflies
        is_dark = (hour >= 18 or hour <= 5)
        self.weather.draw_fireflies(self.canvas, is_dark)

        # 4. Cold Night Frost Vignette
        if self.current_event == "cold_night":
            frost_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            frost_surf.fill((148, 197, 245, 45))
            self.canvas.blit(frost_surf, (0, 0))

        # 5. Particle Systems (Rain, Splashes, Snow, Smoke, Breath, Sweat)
        self.weather.draw_particles(self.canvas, self.current_event)

    def draw_character(self):
        cx = int(self.char_screen_x)
        cy = int(self.char_screen_y + self.char_bob)

        # Micro-reaction: cold shivering jitter
        if self.agent.needs.get("warmth", 1.0) < 0.35 or self.current_event == "cold_night":
            cx += int(math.sin(time.time() * 32.0) * 1.0)

        # 1. Ground Drop Shadow
        shadow_surf = pygame.Surface((28, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 95), (0, 0, 26, 12))
        self.canvas.blit(shadow_surf, (cx - 13, cy + 7))

        # 2. Animated Legs & Boots (Walking Cycle)
        leg_offset = math.sin(self.walk_phase) * 3.5 if hasattr(self, "walk_phase") else 0.0
        boot_color = (65, 42, 24)
        if self.facing_dir in ("down", "up"):
            # Left leg
            pygame.draw.rect(self.canvas, (55, 65, 81), (cx - 5, cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx - 6, cy + 8 + int(leg_offset), 4, 3), border_radius=1)
            # Right leg
            pygame.draw.rect(self.canvas, (55, 65, 81), (cx + 2, cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx + 2, cy + 8 - int(leg_offset), 4, 3), border_radius=1)
        elif self.facing_dir == "right":
            pygame.draw.rect(self.canvas, (55, 65, 81), (cx - 3 + int(leg_offset), cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx - 3 + int(leg_offset), cy + 8, 4, 3), border_radius=1)
            pygame.draw.rect(self.canvas, (40, 50, 65), (cx + 1 - int(leg_offset), cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx + 1 - int(leg_offset), cy + 8, 4, 3), border_radius=1)
        else:  # left
            pygame.draw.rect(self.canvas, (40, 50, 65), (cx - 2 + int(leg_offset), cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx - 3 + int(leg_offset), cy + 8, 4, 3), border_radius=1)
            pygame.draw.rect(self.canvas, (55, 65, 81), (cx + 2 - int(leg_offset), cy + 4, 3, 5))
            pygame.draw.rect(self.canvas, boot_color, (cx + 1 - int(leg_offset), cy + 8, 4, 3), border_radius=1)

        # 3. Backpack (Drawn behind if facing down/right, or on back)
        inv_count = sum(self.agent.inventory.values())
        bp_w = max(5, min(9, 5 + inv_count // 3))
        if self.facing_dir == "right":
            pygame.draw.rect(self.canvas, (115, 60, 20), (cx - 9, cy - 6, bp_w, 11), border_radius=2)
            pygame.draw.rect(self.canvas, (140, 80, 25), (cx - 9, cy - 7, bp_w, 3), border_radius=1)
        elif self.facing_dir == "left":
            pygame.draw.rect(self.canvas, (115, 60, 20), (cx + 4, cy - 6, bp_w, 11), border_radius=2)
            pygame.draw.rect(self.canvas, (140, 80, 25), (cx + 4, cy - 7, bp_w, 3), border_radius=1)
        elif self.facing_dir == "up":
            pygame.draw.rect(self.canvas, (115, 60, 20), (cx - 5, cy - 7, 10, 12), border_radius=2)
            pygame.draw.rect(self.canvas, (140, 80, 25), (cx - 6, cy - 9, 12, 3), border_radius=1)

        # 4. Torso & Explorer Jacket
        torso_color = (217, 119, 6) if not self.agent.injured else (185, 28, 28)
        pygame.draw.rect(self.canvas, torso_color, (cx - 5, cy - 6, 10, 11), border_radius=2)
        # Leather belt with buckle
        pygame.draw.rect(self.canvas, (75, 45, 20), (cx - 5, cy + 2, 10, 2))
        pygame.draw.rect(self.canvas, (245, 200, 30), (cx - 1, cy + 2, 2, 2))

        # Injury Medical Bandage Wrap
        if self.agent.injured:
            pygame.draw.line(self.canvas, (254, 242, 242), (cx - 5, cy - 3), (cx + 4, cy + 1), 2)
            pygame.draw.circle(self.canvas, COLOR_RED, (cx - 8, cy - 14), 5)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 10, cy - 14), (cx - 6, cy - 14), 2)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 8, cy - 16), (cx - 8, cy - 12), 2)

        # 5. Arms & Hand Survival Tool
        arm_swing = math.sin(self.walk_phase) * 2.5 if hasattr(self, "walk_phase") else 0.0
        if self.facing_dir == "right":
            pygame.draw.rect(self.canvas, torso_color, (cx + 3, cy - 4 - int(arm_swing), 3, 6), border_radius=1)
            hx, hy = cx + 6, cy - 5 - int(arm_swing)
            pygame.draw.line(self.canvas, (90, 50, 25), (hx, hy + 5), (hx + 2, hy - 4), 2)
            pygame.draw.polygon(self.canvas, (203, 213, 225), [(hx + 2, hy - 4), (hx + 6, hy - 6), (hx + 4, hy - 2)])
        elif self.facing_dir == "left":
            pygame.draw.rect(self.canvas, torso_color, (cx - 6, cy - 4 + int(arm_swing), 3, 6), border_radius=1)
            hx, hy = cx - 6, cy - 5 + int(arm_swing)
            pygame.draw.line(self.canvas, (90, 50, 25), (hx, hy + 5), (hx - 2, hy - 4), 2)
            pygame.draw.polygon(self.canvas, (203, 213, 225), [(hx - 2, hy - 4), (hx - 6, hy - 6), (hx - 4, hy - 2)])
        else:
            pygame.draw.rect(self.canvas, torso_color, (cx - 7, cy - 4 + int(arm_swing), 3, 6), border_radius=1)
            pygame.draw.rect(self.canvas, torso_color, (cx + 4, cy - 4 - int(arm_swing), 3, 6), border_radius=1)

        # 6. Head & Explorer Cap
        head_skin = (254, 215, 170)
        pygame.draw.circle(self.canvas, head_skin, (cx, cy - 11), 6)
        if self.facing_dir == "right":
            pygame.draw.circle(self.canvas, (67, 56, 202), (cx, cy - 13), 6)
            pygame.draw.rect(self.canvas, (49, 46, 129), (cx + 1, cy - 13, 6, 3), border_radius=1)
            pygame.draw.circle(self.canvas, (30, 41, 59), (cx + 3, cy - 10), 1)
        elif self.facing_dir == "left":
            pygame.draw.circle(self.canvas, (67, 56, 202), (cx, cy - 13), 6)
            pygame.draw.rect(self.canvas, (49, 46, 129), (cx - 7, cy - 13, 6, 3), border_radius=1)
            pygame.draw.circle(self.canvas, (30, 41, 59), (cx - 3, cy - 10), 1)
        elif self.facing_dir == "up":
            pygame.draw.circle(self.canvas, (67, 56, 202), (cx, cy - 13), 6)
        else:  # down
            pygame.draw.circle(self.canvas, (67, 56, 202), (cx, cy - 13), 6)
            pygame.draw.rect(self.canvas, (49, 46, 129), (cx - 4, cy - 11, 8, 3), border_radius=1)
            pygame.draw.circle(self.canvas, (30, 41, 59), (cx - 2, cy - 9), 1)
            pygame.draw.circle(self.canvas, (30, 41, 59), (cx + 2, cy - 9), 1)

        # 7. Shelter Shield Indicator
        if self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1]):
            pygame.draw.polygon(self.canvas, COLOR_GREEN, [(cx, cy - 25), (cx - 7, cy - 18), (cx + 7, cy - 18)])

        # 8. Overhead Thought/Speech Bubble
        if self.bubble_timer > 0 and self.bubble_text:
            text_surf = self.font_bubble.render(self.bubble_text, True, (15, 23, 42))
            tw, th = text_surf.get_width() + 18, text_surf.get_height() + 10
            bx = max(10, min(MAP_SIZE - tw - 10, cx - tw // 2))
            by = cy - 50

            shadow_rect = pygame.Rect(bx, by + 2, tw, th)
            b_sh = pygame.Surface((tw, th), pygame.SRCALPHA)
            pygame.draw.rect(b_sh, (0, 0, 0, 60), (0, 0, tw, th), border_radius=6)
            self.canvas.blit(b_sh, (bx, by + 2))

            b_rect = pygame.Rect(bx, by, tw, th)
            pygame.draw.rect(self.canvas, (241, 245, 249), b_rect, border_radius=6)
            pygame.draw.rect(self.canvas, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE, b_rect, 2, border_radius=6)
            pygame.draw.polygon(self.canvas, (241, 245, 249), [(cx - 4, by + th), (cx + 4, by + th), (cx, by + th + 5)])
            self.canvas.blit(text_surf, (bx + 9, by + 5))

    def draw_tile_tooltip(self, mouse_pos: Tuple[int, int]):
        mx, my = mouse_pos
        if mx >= MAP_SIZE or my >= MAP_SIZE or my < 52:
            return

        tx, ty = int(mx / TILE_SIZE), int(my / TILE_SIZE)
        if not (0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM):
            return

        tile_type = self.world.get_tile(tx, ty)
        tile_name = contracts.TILE_TYPES.get(tile_type, "Unknown").capitalize()
        is_fresh = (tx, ty) in self.world.freshwater_tiles
        is_food = (tx, ty) in self.world.food_tiles

        desc = "Freshwater Stream" if is_fresh else ("Berry Forage Grove" if is_food else f"{tile_name} Terrain")
        tt_str = f"[{tx}, {ty}] {tile_name}  |  {desc}"
        txt_surf = self.font_small.render(tt_str, True, COLOR_TEXT_MAIN)

        tt_w, tt_h = txt_surf.get_width() + 18, txt_surf.get_height() + 10
        tt_x = max(10, min(MAP_SIZE - tt_w - 10, mx + 14))
        tt_y = max(58, min(MAP_SIZE - tt_h - 10, my - 28))

        tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
        pygame.draw.rect(self.canvas, (15, 23, 42), tt_rect, border_radius=5)
        pygame.draw.rect(self.canvas, COLOR_CYAN, tt_rect, 1, border_radius=5)
        self.canvas.blit(txt_surf, (tt_x + 9, tt_y + 5))

    def draw_dashboard(self):
        panel_x = MAP_SIZE + 16
        panel_w = WINDOW_WIDTH - MAP_SIZE - 32
        curr_y = 12

        # Card 1: Survivor Profile & Physiological Vitals (width = 668, height = 230)
        card1_h = 230
        self.draw_card(panel_x, curr_y, panel_w, card1_h)

        mood_str = "Resilient"
        mood_col = COLOR_GREEN
        if not self.agent.is_alive:
            mood_str = "Perished"
            mood_col = COLOR_RED
        elif self.agent.injured:
            mood_str = "Injured"
            mood_col = COLOR_RED
        elif self.agent.stress > 0.65:
            mood_str = "Anxious"
            mood_col = COLOR_ORANGE
        elif self.agent.needs["warmth"] < 0.3:
            mood_str = "Freezing"
            mood_col = COLOR_CYAN

        header_surf = self.font_sub.render(f"SURVIVOR STATUS  [{mood_str.upper()}]", True, mood_col)
        self.canvas.blit(header_surf, (panel_x + 16, curr_y + 12))

        step_txt = f"Day {self.agent.day}  |  {self.agent.hour:02d}:00  (Step {self.step_idx}/{self.max_steps})"
        step_surf = self.font_mono.render(step_txt, True, COLOR_TEXT_MUTED)
        self.canvas.blit(step_surf, (panel_x + panel_w - step_surf.get_width() - 16, curr_y + 12))

        needs = self.agent.needs
        need_items = [
            ("Hunger", needs["hunger"], COLOR_YELLOW),
            ("Thirst", needs["thirst"], COLOR_CYAN),
            ("Warmth", needs["warmth"], COLOR_ORANGE),
            ("Energy", needs["energy"], COLOR_GREEN),
            ("Safety", needs["safety"], COLOR_BLUE),
            ("Morale", needs["morale"], COLOR_PURPLE)
        ]

        bar_w = (panel_w - 48) // 2
        for idx, (lbl, val, bar_color) in enumerate(need_items):
            col = idx % 2
            row = idx // 2
            bx = panel_x + 16 + col * (bar_w + 16)
            by = curr_y + 44 + row * 28
            self.draw_progress_bar(bx, by, bar_w, 15, lbl, val, bar_color)

        stress_y = curr_y + 138
        self.draw_progress_bar(
            panel_x + 16, stress_y, bar_w, 17,
            "Stress", self.agent.stress, COLOR_RED if self.agent.stress > 0.6 else COLOR_YELLOW
        )

        decoherence_pct = 0.0
        if self.agent.stress > 0.4:
            decoherence_pct = min(1.0, (self.agent.stress - 0.4) / 0.5)
        self.draw_progress_bar(
            panel_x + 32 + bar_w, stress_y, bar_w, 17,
            "Decoherence", decoherence_pct, COLOR_PURPLE
        )

        inv = self.agent.inventory
        inv_str = f"RESOURCES:   Timber: {inv.get('wood', 0)}   |   Rations: {inv.get('food', 0)}   |   Crafted Tools: {inv.get('tools', 0)}"
        self.canvas.blit(self.font_body.render(inv_str, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 185))

        curr_y += card1_h + 12

        # Card 2: Environment Hazard & Chronology (width = 668, height = 135)
        card2_h = 135
        self.draw_card(panel_x, curr_y, panel_w, card2_h)
        header_env = self.font_sub.render("ENVIRONMENTAL HAZARD & EVENT CHRONOLOGY", True, COLOR_YELLOW)
        self.canvas.blit(header_env, (panel_x + 16, curr_y + 12))

        ev_upper = self.current_event.upper()
        ev_color = COLOR_RED if ev_upper in ("STORM", "INJURY", "ANIMAL") else (COLOR_CYAN if ev_upper == "COLD_NIGHT" else COLOR_GREEN)
        self.draw_badge(panel_x + 16, curr_y + 38, f"ACTIVE HAZARD: {ev_upper}", ev_color)

        px, py = self.agent.pos
        tile_name = contracts.TILE_TYPES.get(self.world.get_tile(px, py), "Unknown").capitalize()
        pos_txt = f"Coordinates: [{px}, {py}]  |  Biome: {tile_name}  |  Shelter: {'Sheltered' if self.world.is_in_shelter(px, py) else 'Exposed'}"
        self.canvas.blit(self.font_body.render(pos_txt, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 72))

        clean_events = [e.upper() for e in self.agent.recent_events if e != "none"] or ["NONE"]
        history_str = " -> ".join(clean_events)
        hist_display = f"Event Order Effect: [ {history_str} ]"
        max_h_w = panel_w - 32
        if self.font_mono.size(hist_display)[0] > max_h_w:
            while hist_display and self.font_mono.size(hist_display + "... ]")[0] > max_h_w:
                hist_display = hist_display[:-1]
            hist_display = hist_display.rstrip() + "... ]"
        self.canvas.blit(self.font_mono.render(hist_display, True, COLOR_CYAN), (panel_x + 16, curr_y + 100))

        curr_y += card2_h + 12

        # Card 3: Quantum Superposition & Probabilities (width = 668, height = 370)
        card3_h = 370
        self.draw_card(panel_x, curr_y, panel_w, card3_h)

        mind_title = "2-QUBIT QUANTUM BELIEF STATE" if self.mind_type == "quantum" else "CLASSICAL RATIONAL UTILITY"
        self.canvas.blit(self.font_sub.render(mind_title, True, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE), (panel_x + 16, curr_y + 12))

        chosen_act = self.current_decision.get("action", "none").upper()
        self.draw_badge(panel_x + 16, curr_y + 38, f"EXECUTED ACTION: {chosen_act}", ACTION_COLORS.get(chosen_act.lower(), COLOR_GREEN))

        probs = self.current_decision.get("probs", {})
        chart_y = curr_y + 72
        actions_list = contracts.ACTIONS
        chart_w = panel_w - 190

        max_act = max(probs.items(), key=lambda it: it[1])[0] if probs else "none"

        for act in actions_list:
            p = probs.get(act, 0.0)
            act_color = ACTION_COLORS.get(act, COLOR_CYAN)
            is_top = (act == max_act)

            lbl_txt = f"> {act[:10]}" if is_top else f"  {act[:10]}"
            lbl_col = COLOR_GOLD if is_top else COLOR_TEXT_MAIN
            self.canvas.blit(self.font_mono.render(f"{lbl_txt:12s}", True, lbl_col), (panel_x + 16, chart_y))

            bar_rect = pygame.Rect(panel_x + 125, chart_y + 3, chart_w, 12)
            pygame.draw.rect(self.canvas, (15, 23, 42), bar_rect, border_radius=3)
            fill_w = max(2, int(p * chart_w))
            pygame.draw.rect(self.canvas, act_color, (panel_x + 125, chart_y + 3, fill_w, 12), border_radius=3)

            pct_lbl = self.font_mono.render(f"{p*100:4.1f}%", True, COLOR_TEXT_MUTED)
            self.canvas.blit(pct_lbl, (panel_x + 135 + chart_w, chart_y))
            chart_y += 22

        # Cognitive Reasoning Quote Box (Assembled Neatly Inside Borders)
        reason_rect = pygame.Rect(panel_x + 16, chart_y + 10, panel_w - 32, 95)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, reason_rect, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, reason_rect, 1, border_radius=6)

        reason_txt = self.current_decision.get("reason", "Baseline cognitive evaluation.")
        render_wrapped_text(
            surface=self.canvas,
            text=reason_txt,
            font=self.font_body,
            color=COLOR_CYAN,
            x=reason_rect.x + 14,
            y=reason_rect.y + 12,
            max_width=reason_rect.width - 28,
            line_spacing=5,
            max_lines=3
        )

        curr_y += card3_h + 12

        # Card 4: Quick Controls Cheat Sheet (width = 668, height = 115)
        card4_h = 115
        self.draw_card(panel_x, curr_y, panel_w, card4_h)
        controls_lbl = self.font_sub.render("SIMULATION SHORTCUTS & INTERACTION CONTROLS", True, COLOR_TEXT_MAIN)
        self.canvas.blit(controls_lbl, (panel_x + 16, curr_y + 12))

        c_line1 = "[SPACE] Play / Pause   |   [RIGHT] Advance Step   |   [F11] Fullscreen Toggle"
        c_line2 = "[Q] Switch Mind Model  |   [TAB] Action History Log   |   [ESC] Return to Menu"
        self.canvas.blit(self.font_body.render(c_line1, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 44))
        self.canvas.blit(self.font_body.render(c_line2, True, COLOR_CYAN), (panel_x + 16, curr_y + 72))

    # -------------------------------------------------------------------------
    # Render End-of-Event Debrief Screen Modal
    # -------------------------------------------------------------------------
    def draw_debrief_modal(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 30, 205))
        self.canvas.blit(dim_surf, (0, 0))

        mw, mh = 860, 520
        mx, my = (WINDOW_WIDTH - mw) // 2, (WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, m_rect, border_radius=12)

        survived = self.agent.is_alive
        border_col = COLOR_GOLD if survived else COLOR_RED
        pygame.draw.rect(self.canvas, border_col, m_rect, 2, border_radius=12)

        m_title = "MISSION COMPLETE: 48h SURVIVAL MASTERED!" if survived else f"MISSION OVER: SURVIVOR PERISHED ({str(self.agent.cause_of_death).upper()})"
        m_color = COLOR_GOLD if survived else COLOR_RED
        t_surf = self.font_hero.render(m_title, True, m_color)
        self.canvas.blit(t_surf, (mx + (mw - t_surf.get_width()) // 2, my + 28))

        dur_str = f"Endured {self.step_idx}/{self.max_steps} Steps ({self.step_idx * 2} Game Hours in Procedural Island Wilderness)"
        d_surf = self.font_sub.render(dur_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(d_surf, (mx + (mw - d_surf.get_width()) // 2, my + 74))

        box_rect = pygame.Rect(mx + 36, my + 115, mw - 72, 230)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box_rect, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box_rect, 1, border_radius=8)

        engine_name = "2-Qubit Quantum Mind (Qiskit 2.x)" if self.mind_type == "quantum" else "Classical ATUS Rational Utility (Argmax)"
        engine_col = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE

        lines = [
            ("Decision Engine:", engine_name, engine_col),
            ("World Environment:", f"Seed #{self.seed} (Island Terrain, 40x40 Grid, 1600 Tiles)", COLOR_YELLOW),
            ("Final Stress & Noise:", f"{int(self.agent.stress*100)}% Stress  |  Decoherence: {int(max(0, self.agent.stress - 0.4)/0.5 * 100)}% off-diagonal decay", COLOR_CYAN),
            ("Physiological State:", f"Hunger: {int(self.agent.needs['hunger']*100)}% | Thirst: {int(self.agent.needs['thirst']*100)}% | Warmth: {int(self.agent.needs['warmth']*100)}%", COLOR_TEXT_MAIN),
            ("Resource Harvest:", f"Gathered {self.agent.inventory.get('wood',0)} Timber | Consumed Rations | Crafted Tools: {self.agent.inventory.get('tools',0)}", COLOR_TEXT_MUTED)
        ]

        for i, (k, v, col) in enumerate(lines):
            ky = box_rect.y + 16 + i * 42
            self.canvas.blit(self.font_sub.render(k, True, COLOR_TEXT_HINT), (box_rect.x + 22, ky))
            # Text strictly assembled within column bounds
            render_wrapped_text(
                surface=self.canvas,
                text=v,
                font=self.font_mono,
                color=col,
                x=box_rect.x + 215,
                y=ky + 1,
                max_width=box_rect.width - 235,
                max_lines=1
            )

        self.btn_modal_replay.check_hover(mouse_pos)
        self.btn_modal_switch.check_hover(mouse_pos)
        self.btn_modal_home.check_hover(mouse_pos)
        self.btn_modal_close.check_hover(mouse_pos)

        self.btn_modal_replay.draw(self.canvas)
        self.btn_modal_switch.draw(self.canvas)
        self.btn_modal_home.draw(self.canvas)
        self.btn_modal_close.draw(self.canvas)

    # -------------------------------------------------------------------------
    # Render Full Action History Overlay (Tab / Log Key)
    # -------------------------------------------------------------------------
    def draw_history_overlay(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 30, 220))
        self.canvas.blit(dim_surf, (0, 0))

        hw, hh = 1100, 750
        hx, hy = (WINDOW_WIDTH - hw) // 2, (WINDOW_HEIGHT - hh) // 2
        h_rect = pygame.Rect(hx, hy, hw, hh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, h_rect, border_radius=12)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, h_rect, 2, border_radius=12)

        t_surf = self.font_hero.render("CHRONOLOGICAL ACTION HISTORY LOG", True, COLOR_CYAN)
        self.canvas.blit(t_surf, (hx + 30, hy + 24))

        self.btn_hist_close.check_hover(mouse_pos)
        self.btn_hist_close.draw(self.canvas)

        log_y = hy + 80
        col_t = hx + 30
        col_ev = hx + 110
        col_act = hx + 270
        col_prob = hx + 440
        col_reason = hx + 560

        self.canvas.blit(self.font_sub.render("Turn", True, COLOR_GOLD), (col_t, log_y))
        self.canvas.blit(self.font_sub.render("Hazard Event", True, COLOR_GOLD), (col_ev, log_y))
        self.canvas.blit(self.font_sub.render("Decision Action", True, COLOR_GOLD), (col_act, log_y))
        self.canvas.blit(self.font_sub.render("Probability", True, COLOR_GOLD), (col_prob, log_y))
        self.canvas.blit(self.font_sub.render("Cognitive Reasoning", True, COLOR_GOLD), (col_reason, log_y))

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (hx + 30, log_y + 28), (hx + hw - 30, log_y + 28), 1)

        row_y = log_y + 40
        visible_records = self.history[-16:]
        for rec in visible_records:
            t_num = f"#{rec['t']:02d}"
            ev = rec["event"].upper()
            act = rec["action"].upper()
            probs = rec["decision"].get("probs", {})
            top_p = max(probs.values()) if probs else 0.0
            p_str = f"{top_p*100:4.1f}%"
            reason_raw = rec["decision"].get("reason", "")

            act_col = ACTION_COLORS.get(rec["action"], COLOR_TEXT_MAIN)

            self.canvas.blit(self.font_mono.render(t_num, True, COLOR_CYAN), (col_t, row_y))
            self.canvas.blit(self.font_mono.render(ev[:14], True, COLOR_YELLOW), (col_ev, row_y))
            self.canvas.blit(self.font_mono.render(act[:14], True, act_col), (col_act, row_y))
            self.canvas.blit(self.font_mono.render(p_str, True, COLOR_TEXT_MUTED), (col_prob, row_y))

            # Reason bound strictly to avoid exceeding right modal border
            max_r_w = hx + hw - col_reason - 36
            r_display = reason_raw
            if self.font_mono.size(r_display)[0] > max_r_w:
                while r_display and self.font_mono.size(r_display + "...")[0] > max_r_w:
                    r_display = r_display[:-1]
                r_display = r_display.rstrip() + "..."
            self.canvas.blit(self.font_mono.render(r_display, True, COLOR_TEXT_MAIN), (col_reason, row_y))

            row_y += 32

        tip = self.font_small.render("Press [TAB] or [ESC] to return to simulation view", True, COLOR_TEXT_HINT)
        self.canvas.blit(tip, (hx + 30, hy + hh - 34))

    # -------------------------------------------------------------------------
    # UI Utility Helpers
    # -------------------------------------------------------------------------
    def draw_card(self, x: int, y: int, w: int, h: int):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, rect, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, rect, 1, border_radius=8)

    def draw_badge(self, x: int, y: int, text: str, color: Tuple[int, int, int]):
        txt_surf = self.font_sub.render(text, True, color)
        bg_rect = pygame.Rect(x, y, txt_surf.get_width() + 16, txt_surf.get_height() + 8)
        badge_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        badge_surf.fill((color[0], color[1], color[2], 35))
        self.canvas.blit(badge_surf, (x, y))
        pygame.draw.rect(self.canvas, color, bg_rect, 1, border_radius=5)
        self.canvas.blit(txt_surf, (x + 8, y + 4))

    def draw_progress_bar(self, x: int, y: int, w: int, h: int, label: str, value: float, color: Tuple[int, int, int]):
        lbl_surf = self.font_mono.render(f"{label:11s}", True, COLOR_TEXT_MAIN)
        self.canvas.blit(lbl_surf, (x, y))

        bar_x = x + 95
        bar_w = w - 145
        track_rect = pygame.Rect(bar_x, y + 2, bar_w, h - 4)
        pygame.draw.rect(self.canvas, (15, 23, 42), track_rect, border_radius=3)

        fill_w = max(0, min(bar_w, int(value * bar_w)))
        if fill_w > 0:
            pygame.draw.rect(self.canvas, color, (bar_x, y + 2, fill_w, h - 4), border_radius=3)

        val_surf = self.font_mono.render(f"{int(value * 100):3d}%", True, COLOR_TEXT_MUTED)
        self.canvas.blit(val_surf, (bar_x + bar_w + 8, y))


def launch_gui(seed: int = 101, mind: str = "quantum", noise: str = "ibm_hardware", start_screen: str = "home"):
    """Launches the complete Pygame Island Simulation starting at the Home Screen."""
    app = IslandVisualizerApp(seed=seed, mind_type=mind, noise_source=noise, start_screen=start_screen)
    app.run()


if __name__ == "__main__":
    launch_gui()

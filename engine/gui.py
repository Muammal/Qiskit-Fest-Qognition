"""
engine/gui.py - Interactive 2D Pygame Island Simulation, Home Screen & Debrief HUD
Owned by Tech C (Integration, Engine, Visualization).

Enhanced Graphics & Production Visual Suite:
  1. 2.5D Organic Terrain & Shoreline Foam:
     - Organic coastal surf with dynamic white wave foam lapping on beaches.
     - Multi-tiered pine trees with ground drop shadows, wind sway, and wild ruby berry clusters.
     - Chiseled 3D mountain peaks with illuminated northwest cliffs and alpine snowcaps.
     - Cozy survivor log cabin with thatched roof, stone campfire ring, flickering flames, and rising ember sparks.
  2. Dynamic Lighting & Atmospheric Engine:
     - Time-of-day solar cycle: Golden hour dawn/dusk, crystal noon daylight, and night darkness overlay.
     - Dynamic radial point lights: Survivor lantern and campfire clearing holes with warm additive glow.
     - Soft cumulus cloud shadows drifting across the island from west to east.
     - Weather systems: Storm rain with lightning flashes, and drifting cold night snowflakes.
  3. Stylized 2.5D Survivor Avatar:
     - Directional facing (flips smoothly when walking left vs right).
     - Procedural walking stride cycle with swinging limbs.
     - Adventurer explorer hat, jacket, belt, boots, and bulging backpack.
     - Expressive condition FX: Shivering breath vapor in freezing weather, bandage pulse when injured, sweat when stressed.
     - Fading footstep trails in sand and snow.
     - Quantum superposition ghost silhouettes during decision formulation.
  4. 3D Quantum Bloch Sphere Hologram (HUD Card 3):
     - Real-time rotating wireframe Bloch sphere with equator, meridian, and Z-axis (|0>, |1>).
     - Quantum belief state vector |ψ⟩ pointing dynamically based on priors and non-commuting event rotations.
     - IBM Quantum hardware decoherence static noise scanlines under elevated stress.
  5. High-Resolution Display & Adaptive Fullscreen:
     - Standard 16:9 canvas (1600x900) scaling seamlessly to 1080p, 1440p, 4K, and 16:10 laptop screens.
     - True borderless native fullscreen via (0, 0) with zero display mode errors.
     - Procedural vector icons (zero unicode squares) and dynamic border-bounded text wrapping.
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
    0: (22, 54, 88),    # Ocean Deep Blue
    1: (217, 180, 95),  # Plains / Coastal Sand
    2: (20, 95, 48),    # Dense Forest Pine
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
    """Renders high-definition procedural vector icons directly with Pygame geometry."""
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
    """Renders text cleanly wrapped within max_width without exceeding borders."""
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
# 3D Quantum Bloch Sphere Hologram Renderer
# -----------------------------------------------------------------------------
def draw_bloch_sphere(surface: pygame.Surface, cx: int, cy: int, radius: int,
                      theta: float, phi: float, rot_angle: float = 0.0,
                      stress: float = 0.0, font: Optional[pygame.font.Font] = None):
    """
    Renders an animated 3D wireframe Bloch sphere with state vector projection.
    Visualizes quantum amplitudes and decoherence in real time.
    """
    tilt = 0.36

    # 1. Outer rim & depth glow
    pygame.draw.circle(surface, (16, 26, 44), (cx, cy), radius + 2)
    pygame.draw.circle(surface, (45, 65, 105), (cx, cy), radius, 2)

    # 2. Equator (X-Y plane) & Meridian (X-Z plane)
    pygame.draw.ellipse(surface, (32, 48, 80), (cx - radius, cy - int(radius * tilt), radius * 2, int(radius * tilt * 2)), 1)
    pygame.draw.ellipse(surface, (32, 48, 80), (cx - int(radius * tilt), cy - radius, int(radius * tilt * 2), radius * 2), 1)

    # 3. Z-axis (|0> on top, |1> on bottom)
    pygame.draw.line(surface, (70, 95, 140), (cx, cy - radius - 6), (cx, cy + radius + 6), 1)
    if font:
        lbl0 = font.render("|0>", True, (148, 163, 184))
        lbl1 = font.render("|1>", True, (148, 163, 184))
        surface.blit(lbl0, (cx - lbl0.get_width() // 2, cy - radius - 16))
        surface.blit(lbl1, (cx - lbl1.get_width() // 2, cy + radius + 4))

    # 4. State vector calculation with 3D projection
    effective_phi = phi + rot_angle
    vx = radius * math.sin(theta) * math.cos(effective_phi)
    vy = radius * math.sin(theta) * math.sin(effective_phi)
    vz = radius * math.cos(theta)

    # Physical Hardware Noise Jitter under decoherence
    if stress > 0.4:
        jitter_amp = (stress - 0.4) * 5.0
        vx += random.uniform(-jitter_amp, jitter_amp)
        vy += random.uniform(-jitter_amp, jitter_amp)

    px = cx + int(vx)
    py = cy - int(vz + vy * tilt)

    # Phase projection onto equatorial plane
    proj_py = cy - int(vy * tilt)
    pygame.draw.line(surface, (60, 80, 115), (px, py), (px, proj_py), 1)
    pygame.draw.circle(surface, (60, 80, 115), (px, proj_py), 2)

    # 5. Glowing Quantum State Vector |ψ⟩
    pygame.draw.line(surface, (168, 85, 247), (cx, cy), (px, py), 3)
    pygame.draw.circle(surface, (192, 132, 252), (px, py), 6)
    pygame.draw.circle(surface, (56, 189, 248), (px, py), 4)
    pygame.draw.circle(surface, (255, 255, 255), (px, py), 2)


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

        if not self.is_pressed:
            shadow_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), (0, 0, self.rect.width, self.rect.height), border_radius=6)
            surface.blit(shadow_surf, (self.rect.x, self.rect.y + 2))

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

        if self.is_active or self.is_hovered:
            glow_surf = pygame.Surface((draw_rect.width + 4, draw_rect.height + 4), pygame.SRCALPHA)
            glow_col = (*border[:3], 45)
            pygame.draw.rect(glow_surf, glow_col, (0, 0, draw_rect.width + 4, draw_rect.height + 4), border_radius=8)
            surface.blit(glow_surf, (draw_rect.x - 2, draw_rect.y - 2))

        pygame.draw.rect(surface, border, draw_rect, border_w, border_radius=6)

        if self.ripple_timer > 0:
            alpha = int((self.ripple_timer / 0.25) * 120)
            rip_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            rip_surf.fill((255, 255, 255, alpha))
            surface.blit(rip_surf, (draw_rect.x, draw_rect.y))

        txt_col = COLOR_TEXT_MAIN if (self.is_active or self.is_hovered) else self.text_color
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
# Weather, Atmosphere & Dynamic Particle System
# -----------------------------------------------------------------------------
class WeatherSystem:
    def __init__(self, bounds: Tuple[int, int]):
        self.max_x, self.max_y = bounds
        self.rain_drops = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(13, 20)]
            for _ in range(160)
        ]
        self.snow_flakes = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(1.2, 3.2), random.uniform(0.6, 1.8)]
            for _ in range(100)
        ]
        self.sparks: List[List[float]] = []
        self.campfire_embers: List[List[float]] = []
        self.lightning_flash: float = 0.0

    def update(self, event: str, dt: float):
        if event == "storm":
            if self.lightning_flash > 0:
                self.lightning_flash = max(0.0, self.lightning_flash - dt * 2.8)
            elif random.random() < 0.009:
                self.lightning_flash = 0.6

            for drop in self.rain_drops:
                drop[0] -= 5.0 * (dt * 60)
                drop[1] += drop[2] * (dt * 60)
                if drop[1] > self.max_y:
                    drop[1] = 0
                    drop[0] = random.uniform(0, self.max_x + 100)
                if drop[0] < 0:
                    drop[0] = self.max_x

        if event == "cold_night":
            for flake in self.snow_flakes:
                flake[0] += math.sin(flake[1] * 0.05) * 1.4 * (dt * 60)
                flake[1] += flake[3] * (dt * 60)
                if flake[1] > self.max_y:
                    flake[1] = 0
                    flake[0] = random.uniform(0, self.max_x)

        # Action spark particles
        kept_sparks = []
        for s in self.sparks:
            s[0] += s[2] * (dt * 60)
            s[1] += s[3] * (dt * 60)
            s[4] -= dt
            if s[4] > 0:
                kept_sparks.append(s)
        self.sparks = kept_sparks

        # Campfire rising embers
        kept_embers = []
        for e in self.campfire_embers:
            e[0] += math.sin(e[1] * 0.1) * 0.5 * (dt * 60)
            e[1] -= e[2] * (dt * 60)
            e[3] -= dt
            if e[3] > 0:
                kept_embers.append(e)
        self.campfire_embers = kept_embers

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

    def spawn_campfire_ember(self, x: float, y: float):
        if len(self.campfire_embers) < 30 and random.random() < 0.35:
            speed = random.uniform(0.8, 2.2)
            life = random.uniform(0.6, 1.4)
            color = random.choice([(255, 160, 40), (255, 200, 60), (245, 100, 20)])
            self.campfire_embers.append([x + random.uniform(-4, 4), y - 2, speed, life, life, color])

    def draw(self, surface: pygame.Surface, event: str):
        if event == "storm" and self.lightning_flash > 0:
            flash_surf = pygame.Surface((self.max_x, self.max_y), pygame.SRCALPHA)
            alpha = int(self.lightning_flash * 190)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, (0, 0))

        if event == "storm":
            for drop in self.rain_drops:
                x, y = int(drop[0]), int(drop[1])
                pygame.draw.line(surface, (148, 197, 245, 190), (x, y), (x - 3, y + 10), 1)

        elif event == "cold_night":
            for flake in self.snow_flakes:
                x, y = int(flake[0]), int(flake[1])
                pygame.draw.circle(surface, (241, 245, 249, 215), (x, y), int(flake[2]))

        # Draw campfire embers
        for e in self.campfire_embers:
            size = max(1, int((e[3] / e[4]) * 3))
            pygame.draw.circle(surface, e[5], (int(e[0]), int(e[1])), size)

        # Draw action sparks
        for s in self.sparks:
            color = s[6]
            size = max(1, int((s[4] / s[5]) * 4))
            pygame.draw.circle(surface, color, (int(s[0]), int(s[1])), size)


# -----------------------------------------------------------------------------
# Island Pygame Viewer Application
# -----------------------------------------------------------------------------
class IslandVisualizerApp:
    def __init__(self, seed: int = 101, mind_type: str = "quantum", noise_source: str = "ibm_hardware", start_screen: str = "home"):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Stranded: 2D Quantum Island & Survival Engine")

        # Query physical desktop display resolution before window creation
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

        # Micro-Atmosphere & Lighting Systems
        self.weather = WeatherSystem((MAP_SIZE, MAP_SIZE))
        self.char_screen_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2.0)
        self.char_screen_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2.0)
        self.last_char_x = self.char_screen_x
        self.char_bob = 0.0
        self.walk_cycle = 0.0
        self.facing_right = True
        self.bubble_text = "Awakening on uncharted shores..."
        self.bubble_timer = 3.5
        self.selected_tile: Optional[Tuple[int, int]] = None

        # Pre-baked dynamic light textures (radial smooth falloff)
        self.torch_mask = self._create_light_mask(radius=100, max_alpha=160)
        self.torch_glow = self._create_light_glow(radius=100, color=(255, 195, 80), max_alpha=40)
        self.campfire_mask = self._create_light_mask(radius=140, max_alpha=160)
        self.campfire_glow = self._create_light_glow(radius=140, color=(255, 160, 40), max_alpha=55)

        # Drifting atmospheric clouds
        self.clouds = [
            [random.uniform(-100, MAP_SIZE), random.uniform(0, MAP_SIZE), random.uniform(220, 320), random.uniform(110, 160), random.uniform(10.0, 18.0)]
            for _ in range(4)
        ]

        # Footstep tracks that fade gently
        self.footsteps: List[List[float]] = []

        # Hologram rotation angle
        self.bloch_rot = 0.0

        # Build Interactive Button Layouts
        self._build_home_buttons()
        self._build_sim_buttons()

    def _create_light_mask(self, radius: int, max_alpha: int = 160) -> pygame.Surface:
        """Pre-bakes a smooth radial falloff mask for light hole subtraction."""
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            alpha = int(max_alpha * (1.0 - (r / radius) ** 1.6))
            pygame.draw.circle(surf, (0, 0, 0, alpha), (radius, radius), r)
        return surf

    def _create_light_glow(self, radius: int, color: Tuple[int, int, int], max_alpha: int = 45) -> pygame.Surface:
        """Pre-bakes an additive warm atmospheric glow around light sources."""
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -3):
            alpha = int(max_alpha * (1.0 - (r / radius) ** 2.0))
            pygame.draw.circle(surf, (*color[:3], alpha), (radius, radius), r)
        return surf

    def toggle_fullscreen(self):
        """Toggles between Windowed and Fullscreen modes with automatic aspect-ratio scaling."""
        self.is_fullscreen = not self.is_fullscreen
        try:
            if self.is_fullscreen:
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
        w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=seed)
        t_sz = size / GRID_DIM

        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = w.get_tile(x, y)
                if tile == 0 and (x, y) in w.freshwater_tiles:
                    col = COLOR_CYAN_LIGHT
                else:
                    col = TILE_COLORS.get(tile, COLOR_BG)
                rect = (int(x * t_sz), int(y * t_sz), math.ceil(t_sz), math.ceil(t_sz))
                pygame.draw.rect(surf, col, rect)

        sx, sy = int(w.spawn_pos[0] * t_sz), int(w.spawn_pos[1] * t_sz)
        pygame.draw.circle(surf, COLOR_RED, (sx, sy), 6)
        pygame.draw.circle(surf, COLOR_TEXT_MAIN, (sx, sy), 4)
        return surf

    def _build_home_buttons(self):
        col2_x = 480
        top_y = 115

        self.btn_home_fs = UIButton(
            (WINDOW_WIDTH - 170, 24, 140, 36), "Fullscreen", self.font_body,
            bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen"
        )

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

        self.preset_buttons: List[UIButton] = []
        p_y = top_y + 165
        for i, preset in enumerate(PRESETS):
            px = col2_x + 24 + (i % 2) * 531
            py = p_y + (i // 2) * 56
            btn = UIButton((px, py, card_w, 48), preset["label"], self.font_sub,
                           subtext=preset["tag"], subfont=self.font_small, active_color=preset["color"])
            self.preset_buttons.append(btn)

        s_y = top_y + 300
        self.btn_seed_m100 = UIButton((col2_x + 24, s_y, 65, 38), "-100", self.font_body)
        self.btn_seed_m10 = UIButton((col2_x + 95, s_y, 55, 38), "-10", self.font_body)
        self.btn_seed_m1 = UIButton((col2_x + 156, s_y, 45, 38), "-1", self.font_body)
        self.btn_seed_p1 = UIButton((col2_x + 575, s_y, 45, 38), "+1", self.font_body)
        self.btn_seed_p10 = UIButton((col2_x + 626, s_y, 55, 38), "+10", self.font_body)
        self.btn_seed_p100 = UIButton((col2_x + 687, s_y, 65, 38), "+100", self.font_body)
        self.btn_seed_rand = UIButton((col2_x + 768, s_y, 270, 38), "Random Island", self.font_sub,
                                      active_color=COLOR_YELLOW, icon="random")

        self.step_buttons: List[UIButton] = []
        step_choices = [12, 24, 36, 48]
        st_y = top_y + 395
        btn_w = 250
        for i, steps in enumerate(step_choices):
            sx = col2_x + 24 + i * (btn_w + 15)
            btn = UIButton((sx, st_y, btn_w, 44), f"{steps} Steps ({steps*2}h)", self.font_sub, active_color=COLOR_CYAN)
            self.step_buttons.append(btn)

        self.btn_launch = UIButton(
            (col2_x + 24, top_y + 490, 1046, 68), "LAUNCH SURVIVAL SIMULATION", self.font_hero,
            bg_color=(21, 128, 61), active_color=COLOR_GREEN, icon="launch"
        )

    def _build_sim_buttons(self):
        self.btn_nav_home = UIButton((14, 10, 105, 32), "Menu", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="menu")
        self.btn_nav_pause = UIButton((127, 10, 100, 32), "Pause", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_YELLOW, icon="pause")
        self.btn_nav_step = UIButton((235, 10, 100, 32), "Step >", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_GREEN, icon="step")
        self.btn_nav_speed = UIButton((343, 10, 120, 32), "Speed 1.0x", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="speed")
        self.btn_nav_mind = UIButton((471, 10, 130, 32), "Quantum", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_PURPLE, icon="quantum")
        self.btn_nav_log = UIButton((609, 10, 130, 32), "Action Log", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="log")
        self.btn_nav_fs = UIButton((747, 10, 138, 32), "Fullscreen", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen")

        mx = WINDOW_WIDTH // 2
        my = WINDOW_HEIGHT // 2
        self.btn_modal_replay = UIButton((mx - 270, my + 175, 160, 46), "Replay Run", self.font_sub, bg_color=(37, 99, 235), icon="replay")
        self.btn_modal_switch = UIButton((mx - 95, my + 175, 190, 46), "Compare Mind", self.font_sub, bg_color=COLOR_PURPLE, icon="compare")
        self.btn_modal_home = UIButton((mx + 110, my + 175, 160, 46), "Home Menu", self.font_sub, bg_color=(51, 65, 85), icon="menu")
        self.btn_modal_close = UIButton((mx + 360, my - 225, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

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
        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            return

        in_shelter = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])
        event = self.event_gen.step_event(
            day=self.agent.day,
            hour=self.agent.hour,
            current_pos=self.agent.pos,
            in_shelter=in_shelter,
            injured=self.agent.injured
        )
        self.current_event = event
        self.agent.apply_event(event, in_shelter=in_shelter)

        decision = self.decide_fn(self.agent.get_state())
        contracts.validate_decision(decision)
        self.current_decision = decision
        action = decision["action"]

        narrative = self.agent.execute_action(action, self.world)
        in_shelter_after = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])
        self.agent.step_decay(in_shelter=in_shelter_after)

        self.weather.add_action_particles(self.char_screen_x, self.char_screen_y, action)
        clean_narrative = narrative.split(';')[0]
        self.bubble_text = f"{action.upper()}: {clean_narrative}"
        self.bubble_timer = 2.8

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

            if self.app_state == "sim" and not self.is_paused and not self.show_debrief_modal and not self.show_history_overlay:
                if self.agent.is_alive and self.step_idx < self.max_steps:
                    effective_delay = self.step_delay / self.speed_multiplier
                    if now - self.last_step_time >= effective_delay:
                        self.step_forward()
                        self.last_step_time = now

            # Smooth Character Interpolation, Bobbing & Walk Cycle
            if self.app_state == "sim":
                target_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2.0)
                target_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2.0)
                dist = math.hypot(target_x - self.char_screen_x, target_y - self.char_screen_y)

                if dist > 1.2:
                    self.char_bob += dt * 14.0
                    self.walk_cycle += dt * 12.0
                    self.facing_right = (target_x >= self.char_screen_x)
                    # Spawn footstep in sand or snow
                    if random.random() < 0.2:
                        cur_tile = self.world.get_tile(self.agent.pos[0], self.agent.pos[1])
                        is_snow = (cur_tile == 3) or (self.current_event == "cold_night")
                        self.footsteps.append([self.char_screen_x, self.char_screen_y + 8, 1.0, is_snow])
                else:
                    self.char_bob = math.sin(time.time() * 3.0) * 0.8
                    self.walk_cycle = 0.0

                self.char_screen_x += (target_x - self.char_screen_x) * min(1.0, 10.0 * dt)
                self.char_screen_y += (target_y - self.char_screen_y) * min(1.0, 10.0 * dt)
                self.weather.update(self.current_event, dt)

                # Update fading footsteps
                kept_fs = []
                for fs in self.footsteps:
                    fs[2] -= dt * 0.06
                    if fs[2] > 0:
                        kept_fs.append(fs)
                self.footsteps = kept_fs[-25:]

                # Update drifting cloud masses
                for c in self.clouds:
                    c[0] += c[4] * dt
                    if c[0] > MAP_SIZE + 250:
                        c[0] = -320
                        c[1] = random.uniform(0, MAP_SIZE)

                # Update hologram rotation angle
                self.bloch_rot += dt * 0.75

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

        for y in range(0, WINDOW_HEIGHT, 36):
            shift = math.sin(t_time * 1.6 + y * 0.08) * 18
            pygame.draw.line(self.canvas, (18, 28, 48), (0, y + shift), (WINDOW_WIDTH, y + shift), 1)

        self.btn_home_fs.text = "Windowed" if self.is_fullscreen else "Fullscreen"
        self.btn_home_fs.icon = "windowed" if self.is_fullscreen else "fullscreen"
        self.btn_home_fs.check_hover(mouse_pos)
        self.btn_home_fs.draw(self.canvas)

        title_surf = self.font_hero.render("STRANDED: QUANTUM SURVIVAL ENGINE", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 22))

        sub_str = "Qiskit 2.x  |  2-Qubit Non-Commuting Cognition  |  IBM Hardware Decoherence Modeling"
        sub_surf = self.font_sub.render(sub_str, True, COLOR_CYAN)
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 62))

        col1_x = 32
        col1_y = 96
        col1_w = 430
        col1_h = 760
        self.draw_card(col1_x, col1_y, col1_w, col1_h)

        c1_title = self.font_title.render("ISLAND RECONNAISSANCE", True, COLOR_YELLOW)
        self.canvas.blit(c1_title, (col1_x + 22, col1_y + 18))

        map_box = pygame.Rect(col1_x + (col1_w - 300) // 2, col1_y + 54, 300, 300)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, map_box, 2, border_radius=6)
        self.canvas.blit(self.preview_mini_map, (map_box.x, map_box.y))

        leg_y = col1_y + 368
        pygame.draw.circle(self.canvas, COLOR_RED, (col1_x + 36, leg_y + 7), 5)
        pygame.draw.circle(self.canvas, COLOR_TEXT_MAIN, (col1_x + 36, leg_y + 7), 3)
        leg_surf = self.font_small.render("Red dot: Initial survivor drop-in spawn coordinate", True, COLOR_TEXT_MUTED)
        self.canvas.blit(leg_surf, (col1_x + 50, leg_y))

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

        col2_x = 480
        col2_y = 96
        col2_w = 1088
        col2_h = 760
        self.draw_card(col2_x, col2_y, col2_w, col2_h)

        m_lbl = self.font_title.render("1. Select Cognitive Mind Model", True, COLOR_TEXT_MAIN)
        self.canvas.blit(m_lbl, (col2_x + 24, col2_y + 16))

        self.btn_mind_quantum.is_active = (self.mind_type == "quantum")
        self.btn_mind_classical.is_active = (self.mind_type == "classical")
        self.btn_mind_quantum.check_hover(mouse_pos)
        self.btn_mind_classical.check_hover(mouse_pos)
        self.btn_mind_quantum.draw(self.canvas)
        self.btn_mind_classical.draw(self.canvas)

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

        st_lbl = self.font_title.render("3. Simulation Step Horizon (2 Hours per Turn)", True, COLOR_TEXT_MAIN)
        self.canvas.blit(st_lbl, (col2_x + 24, col2_y + 365))

        step_choices = [12, 24, 36, 48]
        for i, st_btn in enumerate(self.step_buttons):
            st_btn.is_active = (self.max_steps == step_choices[i])
            st_btn.check_hover(mouse_pos)
            st_btn.draw(self.canvas)

        self.btn_launch.check_hover(mouse_pos)
        self.btn_launch.draw(self.canvas)

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

        # 1. Map Surface (900 x 900) - 2.5D Organic Terrain & Depth
        self.draw_island_map()

        # 2. Footstep prints & micro-trails
        self.draw_footsteps()

        # 3. Dynamic Survivor Avatar & Quantum Superposition Echoes
        self.draw_character()

        # 4. Atmosphere, Radial Lights & Drifting Cloud Shadows
        self.draw_atmosphere()

        # 5. Top Map Bar Controls
        self.draw_map_navigation_bar(mouse_pos)

        # 6. Telemetry & Analytics Dashboard (700 x 900)
        self.draw_dashboard()

        # 7. Floating Tile Inspector Tooltip
        self.draw_tile_tooltip(mouse_pos)

        # 8. Modals: Full Action Log Overlay or Debrief Modal
        if self.show_history_overlay:
            self.draw_history_overlay(mouse_pos)
        elif self.show_debrief_modal:
            self.draw_debrief_modal(mouse_pos)

    def draw_map_navigation_bar(self, mouse_pos: Tuple[int, int]):
        bar_bg = pygame.Surface((MAP_SIZE, 52), pygame.SRCALPHA)
        bar_bg.fill((15, 23, 42, 230))
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

    def draw_footsteps(self):
        """Draws fading survivor footsteps in sand or mountain snow."""
        for fs in self.footsteps:
            x, y, alpha, is_snow = fs
            col = (220, 235, 255) if is_snow else (160, 125, 60)
            alpha_val = max(10, int(alpha * 110))
            surf = pygame.Surface((6, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (*col, alpha_val), (0, 0, 6, 4))
            self.canvas.blit(surf, (int(x - 3), int(y - 2)))

    def draw_island_map(self):
        """Renders 2.5D organic terrain with animated coastal surf and depth."""
        t_time = time.time()
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = self.world.get_tile(x, y)
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                rect = pygame.Rect(rx, ry, rw, rh)
                cx = rx + rw // 2
                cy = ry + rh // 2

                # ---------------------------------------------------------
                # 0: Ocean & Animated Coastal Surf
                # ---------------------------------------------------------
                if tile == 0:
                    is_fresh = (x, y) in self.world.freshwater_tiles
                    if is_fresh:
                        # Flowing freshwater stream
                        flow = math.sin(t_time * 4.0 + x * 0.7 + y * 0.7) * 20
                        base = (45, max(0, min(255, 190 + int(flow))), 240)
                        pygame.draw.rect(self.canvas, base, rect)
                        # Stream river sparkles
                        pygame.draw.circle(self.canvas, (215, 245, 255), (cx, cy), 3)
                        pygame.draw.line(self.canvas, (180, 235, 255), (rx + 4, cy), (rx + rw - 4, cy), 1)
                    else:
                        # Check if water tile is coastal (adjacent to land)
                        is_coastal = any(
                            0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) != 0
                            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                        )
                        if is_coastal:
                            # Shallow turquoise lagoon water
                            lagoon = (30, 140, 180)
                            pygame.draw.rect(self.canvas, lagoon, rect)
                            # Animated breathing shore foam
                            foam_breathe = math.sin(t_time * 3.2 + x * 0.6 + y * 0.6)
                            if foam_breathe > 0.1:
                                foam_w = max(2, int(foam_breathe * 4))
                                pygame.draw.circle(self.canvas, (230, 248, 255), (cx, cy), foam_w)
                        else:
                            # Deep ocean blue with ambient swell waves
                            wave = math.sin(t_time * 2.2 + x * 0.35 + y * 0.45) * 14
                            c = (20, max(0, min(255, 52 + int(wave))), 90)
                            pygame.draw.rect(self.canvas, c, rect)
                            if (x + y) % 5 == 0:
                                pygame.draw.line(self.canvas, (35, 75, 120), (rx + 3, cy), (rx + rw - 3, cy), 1)

                # ---------------------------------------------------------
                # 1: Sand Beach & Coastal Plains
                # ---------------------------------------------------------
                elif tile == 1:
                    has_water_adj = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if has_water_adj:
                        # Coastal beach sand
                        pygame.draw.rect(self.canvas, (225, 185, 105), rect)
                        pygame.draw.rect(self.canvas, (200, 155, 80), (rx + 4, ry + 4, 3, 3))
                        pygame.draw.rect(self.canvas, (240, 205, 130), (rx + rw - 6, ry + rh - 6, 2, 2))
                    else:
                        # Lush inland grassy plains
                        pygame.draw.rect(self.canvas, (115, 185, 45), rect)
                        pygame.draw.rect(self.canvas, (95, 160, 35), (rx + 5, ry + 5, 3, 4))
                        # Small wildflower dot
                        if (x * 7 + y * 13) % 9 == 0:
                            pygame.draw.circle(self.canvas, (250, 220, 90), (cx + 2, cy - 2), 2)

                # ---------------------------------------------------------
                # 2: Dense Pine Forest (Layered 2.5D Trees)
                # ---------------------------------------------------------
                elif tile == 2:
                    # Forest floor grass
                    pygame.draw.rect(self.canvas, (20, 85, 40), rect)

                    # Southeast ground shadow
                    pygame.draw.ellipse(self.canvas, (0, 0, 0, 70), (cx - 7, cy + 3, 16, 7))

                    # Wind sway horizontal offset
                    sway = math.sin(t_time * 2.0 + x * 0.4 + y * 0.6) * 1.5

                    # Timber trunk
                    pygame.draw.rect(self.canvas, (105, 55, 25), (cx - 2, cy + 1, 4, 7))

                    # 3 Overlapping Canopy Tiers (Base to Top)
                    t_cx = cx + sway
                    # Tier 1 (Bottom wide canopy)
                    pygame.draw.polygon(self.canvas, (18, 95, 46), [(t_cx, cy - 4), (t_cx - 8, cy + 4), (t_cx + 8, cy + 4)])
                    # Tier 2 (Middle canopy with sunlit highlight)
                    pygame.draw.polygon(self.canvas, (22, 115, 52), [(t_cx, cy - 8), (t_cx - 6, cy - 1), (t_cx + 6, cy - 1)])
                    pygame.draw.polygon(self.canvas, (32, 145, 65), [(t_cx, cy - 8), (t_cx - 6, cy - 1), (t_cx, cy - 1)])
                    # Tier 3 (Pine peak tip)
                    pygame.draw.polygon(self.canvas, (28, 138, 62), [(t_cx, cy - 12), (t_cx - 4, cy - 6), (t_cx + 4, cy - 6)])

                    # Wild Foraging Berry Node
                    if (x, y) in self.world.food_tiles:
                        pygame.draw.circle(self.canvas, (235, 35, 35), (int(t_cx - 5), cy - 2), 3)
                        pygame.draw.circle(self.canvas, (235, 35, 35), (int(t_cx + 4), cy - 1), 3)
                        pygame.draw.circle(self.canvas, (255, 180, 180), (int(t_cx - 6), cy - 3), 1)

                # ---------------------------------------------------------
                # 3: Chiseled 3D Mountain Peaks
                # ---------------------------------------------------------
                elif tile == 3:
                    # Mountain base foothills
                    pygame.draw.rect(self.canvas, (60, 72, 88), rect)

                    peak = (cx, ry + 2)
                    left_base = (rx + 2, ry + rh - 2)
                    right_base = (rx + rw - 2, ry + rh - 2)
                    center_ridge = (cx + 2, ry + rh - 2)

                    # Lit Northwest rock face
                    pygame.draw.polygon(self.canvas, (120, 138, 160), [peak, left_base, center_ridge])
                    # Shadowed Southeast rock face
                    pygame.draw.polygon(self.canvas, (55, 68, 85), [peak, center_ridge, right_base])

                    # Alpine Glacial Snowcap
                    snow_l = (cx - 4, ry + 8)
                    snow_r = (cx + 4, ry + 8)
                    snow_c = (cx + 1, ry + 9)
                    pygame.draw.polygon(self.canvas, (250, 252, 255), [peak, snow_l, snow_c])
                    pygame.draw.polygon(self.canvas, (195, 215, 235), [peak, snow_c, snow_r])

                # ---------------------------------------------------------
                # 4: Survivor Log Cabin & Campfire
                # ---------------------------------------------------------
                elif tile == 4:
                    # Ground grass
                    pygame.draw.rect(self.canvas, (90, 155, 40), rect)

                    # Cabin drop shadow
                    pygame.draw.ellipse(self.canvas, (0, 0, 0, 75), (rx + 2, ry + rh - 6, rw - 4, 6))

                    # Timber cabin wall
                    pygame.draw.rect(self.canvas, (115, 65, 25), (rx + 3, ry + 8, rw - 6, rh - 10), border_radius=2)
                    # Door opening
                    pygame.draw.rect(self.canvas, (35, 20, 10), (cx - 2, ry + 12, 5, rh - 14))

                    # Thatched pitched A-frame roof
                    p_roof = [(cx, ry + 2), (rx + 1, ry + 9), (rx + rw - 1, ry + 9)]
                    pygame.draw.polygon(self.canvas, (165, 90, 20), p_roof)
                    pygame.draw.line(self.canvas, (190, 115, 35), (cx, ry + 2), (cx, ry + 9), 1)

                    # Campfire outside shelter
                    fire_x = cx + 6
                    fire_y = ry + rh - 4
                    # Stone circle
                    pygame.draw.circle(self.canvas, (100, 110, 125), (fire_x, fire_y), 5, 1)
                    # Flickering flame
                    flame_h = max(2, int(4 + math.sin(t_time * 12.0) * 3))
                    pygame.draw.polygon(self.canvas, (245, 120, 20), [
                        (fire_x, fire_y - flame_h),
                        (fire_x - 3, fire_y + 1),
                        (fire_x + 3, fire_y + 1)
                    ])
                    pygame.draw.circle(self.canvas, (255, 220, 60), (fire_x, fire_y - 1), 2)
                    self.weather.spawn_campfire_ember(fire_x, fire_y)

        # Selected Tile Cursor Highlight
        if self.selected_tile:
            tx, ty = self.selected_tile
            s_rect = pygame.Rect(int(tx * TILE_SIZE), int(ty * TILE_SIZE), int(TILE_SIZE), int(TILE_SIZE))
            pygame.draw.rect(self.canvas, COLOR_CYAN, s_rect, 2)

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 2)

    def draw_atmosphere(self):
        """Renders time-of-day dynamic solar lighting, torch cutouts, and cloud shadows."""
        hour = self.agent.hour
        t_time = time.time()

        # 1. Drifting cumulus cloud shadows (moving from west to east)
        for c in self.clouds:
            c_surf = pygame.Surface((int(c[2]), int(c[3])), pygame.SRCALPHA)
            pygame.draw.ellipse(c_surf, (0, 0, 0, 35), (0, 0, int(c[2]), int(c[3])))
            self.canvas.blit(c_surf, (int(c[0]), int(c[1])))

        # 2. Solar Day / Night Lighting Mask
        # Determine darkness alpha based on hour
        darkness = 0
        if hour >= 21 or hour <= 4:
            darkness = 160  # Deep Night
        elif hour in (5, 20):
            darkness = 95   # Dawn / Dusk Twilight
        elif hour in (6, 19):
            darkness = 45   # Golden Hour

        if darkness > 0:
            dark_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            dark_surf.fill((10, 15, 35, darkness))

            # Carve out torchlight hole around survivor using BLEND_RGBA_SUB
            survivor_x = int(self.char_screen_x)
            survivor_y = int(self.char_screen_y)
            dark_surf.blit(self.torch_mask, (survivor_x - 100, survivor_y - 100), special_flags=pygame.BLEND_RGBA_SUB)

            # Carve out campfire light holes around shelters
            for (sx, sy) in self.world.shelter_tiles:
                sc_x = int(sx * TILE_SIZE + TILE_SIZE / 2)
                sc_y = int(sy * TILE_SIZE + TILE_SIZE / 2)
                dark_surf.blit(self.campfire_mask, (sc_x - 140, sc_y - 140), special_flags=pygame.BLEND_RGBA_SUB)

            self.canvas.blit(dark_surf, (0, 0))

            # Add warm golden/amber additive light glow on top
            self.canvas.blit(self.torch_glow, (survivor_x - 100, survivor_y - 100), special_flags=pygame.BLEND_RGBA_ADD)
            for (sx, sy) in self.world.shelter_tiles:
                sc_x = int(sx * TILE_SIZE + TILE_SIZE / 2)
                sc_y = int(sy * TILE_SIZE + TILE_SIZE / 2)
                self.canvas.blit(self.campfire_glow, (sc_x - 140, sc_y - 140), special_flags=pygame.BLEND_RGBA_ADD)

        # 3. Cold Night Frost Vignette
        if self.current_event == "cold_night":
            frost_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            frost_surf.fill((148, 197, 245, 50))
            self.canvas.blit(frost_surf, (0, 0))

        # 4. Weather Systems (Rain, Lightning, Snow)
        self.weather.draw(self.canvas, self.current_event)

    def draw_character(self):
        """Renders stylized 2.5D survivor avatar with walking animations and quantum superposition echoes."""
        cx = int(self.char_screen_x)
        cy = int(self.char_screen_y + self.char_bob)
        t_time = time.time()

        # -------------------------------------------------------------
        # Quantum Superposition Ghost Silhouettes (Entropy Visualizer)
        # -------------------------------------------------------------
        if self.mind_type == "quantum":
            probs = self.current_decision.get("probs", {})
            # If multiple actions have significant probability, render superposition echoes
            high_prob_actions = [a for a, p in probs.items() if p > 0.18]
            if len(high_prob_actions) >= 2:
                ghost_offset = math.sin(t_time * 6.0) * 10
                ghost_surf = pygame.Surface((28, 32), pygame.SRCALPHA)
                # Cyan ghost
                pygame.draw.rect(ghost_surf, (56, 189, 248, 45), (6, 6, 12, 14), border_radius=3)
                pygame.draw.circle(ghost_surf, (56, 189, 248, 45), (12, 6), 6)
                self.canvas.blit(ghost_surf, (cx - 14 + int(ghost_offset), cy - 16))
                # Purple ghost
                ghost_surf_p = pygame.Surface((28, 32), pygame.SRCALPHA)
                pygame.draw.rect(ghost_surf_p, (168, 85, 247, 45), (6, 6, 12, 14), border_radius=3)
                pygame.draw.circle(ghost_surf_p, (168, 85, 247, 45), (12, 6), 6)
                self.canvas.blit(ghost_surf_p, (cx - 14 - int(ghost_offset), cy - 16))

        # Ground Shadow
        pygame.draw.ellipse(self.canvas, (0, 0, 0, 85), (cx - 12, cy + 8, 24, 10))

        # Shivering jitter under extreme cold
        jx = int(random.uniform(-1, 1)) if (self.current_event == "cold_night" or self.agent.needs["warmth"] < 0.3) else 0
        cx += jx

        # Procedural Walking Strides (Legs & Boots)
        leg_stride = math.sin(self.walk_cycle) * 3
        # Left Leg
        pygame.draw.rect(self.canvas, (35, 45, 60), (cx - 5, cy + 3 + int(leg_stride), 4, 8))
        pygame.draw.rect(self.canvas, (75, 45, 20), (cx - 6 if self.facing_right else cx - 5, cy + 9 + int(leg_stride), 5, 4))
        # Right Leg
        pygame.draw.rect(self.canvas, (35, 45, 60), (cx + 1, cy + 3 - int(leg_stride), 4, 8))
        pygame.draw.rect(self.canvas, (75, 45, 20), (cx + 1 if self.facing_right else cx, cy + 9 - int(leg_stride), 5, 4))

        # Torso & Explorer Jacket
        body_col = (215, 120, 20) if not self.agent.injured else (185, 28, 28)
        pygame.draw.rect(self.canvas, body_col, (cx - 6, cy - 8, 12, 13), border_radius=3)
        # Utility Belt & Gold Buckle
        pygame.draw.rect(self.canvas, (45, 30, 15), (cx - 6, cy + 1, 12, 3))
        pygame.draw.rect(self.canvas, (234, 179, 8), (cx - 2, cy + 1, 4, 3))

        # Adventurer Leather Backpack (Facing-Aware)
        bp_x = cx - 9 if self.facing_right else cx + 4
        pygame.draw.rect(self.canvas, (115, 60, 20), (bp_x, cy - 7, 5, 10), border_radius=2)
        # Bedroll on top of backpack
        pygame.draw.rect(self.canvas, (65, 80, 100), (bp_x - 1, cy - 10, 7, 4), border_radius=2)

        # Arms & Handheld Explorer Equipment
        arm_swing = math.sin(self.walk_cycle) * 2
        arm_x = cx + 5 if self.facing_right else cx - 7
        pygame.draw.rect(self.canvas, body_col, (arm_x, cy - 6 + int(arm_swing), 3, 8), border_radius=1)
        # Walking staff / torch held in hand
        pygame.draw.line(self.canvas, (105, 65, 30), (arm_x + 1, cy - 12 + int(arm_swing)), (arm_x + 1, cy + 10 + int(arm_swing)), 2)
        # Torch flame tip
        pygame.draw.circle(self.canvas, (255, 180, 50), (arm_x + 1, cy - 13 + int(arm_swing)), 3)

        # Head & Explorer Hat
        pygame.draw.circle(self.canvas, (254, 215, 170), (cx, cy - 13), 6)
        # Hat Brim & Crown
        pygame.draw.ellipse(self.canvas, (55, 65, 85), (cx - 9, cy - 18, 18, 6))
        pygame.draw.rect(self.canvas, (70, 80, 105), (cx - 5, cy - 23, 10, 6), border_radius=2)
        # Hat band
        pygame.draw.rect(self.canvas, (190, 80, 20), (cx - 5, cy - 19, 10, 2))

        # Eye gazing direction
        eye_x = cx + 2 if self.facing_right else cx - 3
        pygame.draw.circle(self.canvas, (20, 30, 50), (eye_x, cy - 13), 1)

        # Condition FX: Shivering Breath Puff in Cold Weather
        if (self.current_event == "cold_night" or self.agent.needs["warmth"] < 0.3) and random.random() < 0.15:
            breath_x = cx + 7 if self.facing_right else cx - 7
            pygame.draw.circle(self.canvas, (220, 240, 255, 180), (breath_x, cy - 12), random.randint(2, 4))

        # Condition FX: Injury Pulse Badge
        if self.agent.injured:
            pulse = math.sin(t_time * 8.0) * 2
            pygame.draw.circle(self.canvas, COLOR_RED, (cx - 10, cy - 18), int(6 + pulse))
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 13, cy - 18), (cx - 7, cy - 18), 2)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 10, cy - 21), (cx - 10, cy - 15), 2)

        # Condition FX: Stress Sweat Droplet
        if self.agent.stress > 0.65 and random.random() < 0.25:
            pygame.draw.circle(self.canvas, (56, 189, 248), (cx - 6, cy - 15), 2)

        # Shelter Shield Indicator
        if self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1]):
            pygame.draw.polygon(self.canvas, COLOR_GREEN, [(cx, cy - 27), (cx - 7, cy - 20), (cx + 7, cy - 20)])

        # Overhead Dialogue / Action Bubble
        if self.bubble_timer > 0 and self.bubble_text:
            text_surf = self.font_bubble.render(self.bubble_text, True, (15, 23, 42))
            tw, th = text_surf.get_width() + 18, text_surf.get_height() + 10
            bx = max(10, min(MAP_SIZE - tw - 10, cx - tw // 2))
            by = cy - 54

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

        # Card 3: 2-Qubit Quantum Belief State & 3D Bloch Sphere Hologram (width = 668, height = 370)
        card3_h = 370
        self.draw_card(panel_x, curr_y, panel_w, card3_h)

        mind_title = "2-QUBIT QUANTUM BELIEF STATE" if self.mind_type == "quantum" else "CLASSICAL RATIONAL UTILITY"
        self.canvas.blit(self.font_sub.render(mind_title, True, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE), (panel_x + 16, curr_y + 12))

        chosen_act = self.current_decision.get("action", "none").upper()
        self.draw_badge(panel_x + 16, curr_y + 38, f"EXECUTED ACTION: {chosen_act}", ACTION_COLORS.get(chosen_act.lower(), COLOR_GREEN))

        probs = self.current_decision.get("probs", {})
        chart_y = curr_y + 72
        actions_list = contracts.ACTIONS
        chart_w = 260  # Compacted to accommodate the 3D Bloch sphere on the right

        max_act = max(probs.items(), key=lambda it: it[1])[0] if probs else "none"

        # Render 7 Action Probability Bars on Left Side
        for act in actions_list:
            p = probs.get(act, 0.0)
            act_color = ACTION_COLORS.get(act, COLOR_CYAN)
            is_top = (act == max_act)

            lbl_txt = f"> {act[:9]}" if is_top else f"  {act[:9]}"
            lbl_col = COLOR_GOLD if is_top else COLOR_TEXT_MAIN
            self.canvas.blit(self.font_mono.render(f"{lbl_txt:11s}", True, lbl_col), (panel_x + 16, chart_y))

            bar_rect = pygame.Rect(panel_x + 115, chart_y + 3, chart_w, 12)
            pygame.draw.rect(self.canvas, (15, 23, 42), bar_rect, border_radius=3)
            fill_w = max(2, int(p * chart_w))
            pygame.draw.rect(self.canvas, act_color, (panel_x + 115, chart_y + 3, fill_w, 12), border_radius=3)

            pct_lbl = self.font_mono.render(f"{p*100:4.1f}%", True, COLOR_TEXT_MUTED)
            self.canvas.blit(pct_lbl, (panel_x + 123 + chart_w, chart_y))
            chart_y += 22

        # -------------------------------------------------------------
        # 3D Quantum Bloch Sphere Hologram on Right Side of Card 3
        # -------------------------------------------------------------
        bloch_box = pygame.Rect(panel_x + 440, curr_y + 38, 212, 195)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, bloch_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, bloch_box, 1, border_radius=6)

        bloch_title = self.font_small.render("Bloch Sphere Hologram |ψ⟩", True, COLOR_GOLD)
        self.canvas.blit(bloch_title, (bloch_box.x + (bloch_box.width - bloch_title.get_width()) // 2, bloch_box.y + 8))

        # Dynamic state angles derived from belief priorities
        forage_p = probs.get("forage", 0.15)
        drink_p = probs.get("drink", 0.15)
        shelter_p = probs.get("build_shelter", 0.15)
        theta_val = math.pi * (1.0 - max(0.05, min(0.95, forage_p + drink_p)))
        phi_val = (shelter_p * 4.0 * math.pi) + len(self.agent.recent_events) * 0.8

        bloch_cx = bloch_box.x + bloch_box.width // 2
        bloch_cy = bloch_box.y + 115
        draw_bloch_sphere(
            surface=self.canvas,
            cx=bloch_cx,
            cy=bloch_cy,
            radius=48,
            theta=theta_val,
            phi=phi_val,
            rot_angle=self.bloch_rot,
            stress=self.agent.stress,
            font=self.font_small
        )

        coord_str = f"θ:{theta_val:.2f}  φ:{phi_val % (2*math.pi):.2f}"
        coord_surf = self.font_mono.render(coord_str, True, COLOR_CYAN)
        self.canvas.blit(coord_surf, (bloch_box.x + (bloch_box.width - coord_surf.get_width()) // 2, bloch_box.y + bloch_box.height - 20))

        # Hardware Noise static scanlines on Card 3 when decohering
        if self.mind_type == "quantum" and self.agent.stress > 0.45:
            for _ in range(3):
                ny = curr_y + random.randint(20, card3_h - 20)
                pygame.draw.line(self.canvas, (168, 85, 247, 60), (panel_x + 16, ny), (panel_x + panel_w - 16, ny), 1)

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

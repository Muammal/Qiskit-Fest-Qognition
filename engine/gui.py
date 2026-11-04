"""engine/gui.py - Interactive 2D Pygame Island Simulation, Home Screen & Debrief HUD
Quantum Cognition Simulation Engine
Tech C Deliverable (Integration, Engine, Visualization).

Enhanced Suite:
  1. High-Resolution 1600x900 Widescreen Display:
     - 16:9 standard cinematic aspect ratio.
     - 900x900 high-definition island map viewport.
     - 700x900 expansive telemetry and analytics dashboard.
     - Fullscreen toggle via [Fullscreen] button or F11 key with letterboxing/pillarboxing
       and exact mouse coordinate transformation at any display resolution.
  2. Event Choice Screen (First Screen):
     - Prominently choose between Island Wilderness Survival and Volcano Eruption Evacuation.
  3. Procedural Vector Iconography (Zero Broken Unicode Squares):
     - Eliminates all font-dependent unicode emojis and tofu squares.
     - Crisp, resolution-independent vector icons drawn directly with Pygame geometry
       (Fullscreen, Windows, Quantum Atom, Neural Network, Play/Pause, Step, Speed Bolt,
       Menu, Action Log, Dice, Rocket, Replay, Compare, Health Cross, and Shields).
  4. Strict Text Assembly & Border-Bound Typography:
     - Dynamic text wrapping (`wrap_text` and `render_wrapped_text`) ensuring decision rationales,
       event chains, telemetry labels, and modal metrics never spill or exceed container borders.
     - Dynamically calculated column offsets and bounded badge layouts.
  5. Interactive Home Screen (Start Menu):
     - High-resolution 300x300 procedural island mini-map preview thumbnail with terrain stats.
     - Decision Mind selection cards with formula previews (Qiskit 2-qubit vs Classical ATUS).
     - Scenario Presets with semantic difficulty tags + full numeric seed stepper + randomizer.
     - Step horizon selector (12, 24, 36, 48 turns).
     - Glowing Hero Launch button.
  6. 2D Island & Volcano Living World Viewport:
     - Procedural 40x40 tiles with dynamic water waves, freshwater streams, shore foam,
       layered pine canopies with food berry clusters, and alpine snowcaps.
     - Volcano caldera, dynamic molten lava meanders, pyroclastic flow corridors, lahars,
       atmospheric ash fallout, and evacuation zone overlays (toggleable via 'E' key).
     - Dynamic lighting & weather: day ambient warmth, night navy tint (21:00-05:00),
       storm rain with lightning flashes, and cold night frost vignette with drifting snow.
     - Animated survivor avatar with walking interpolation (lerp), bobbing, condition badges,
       particle bursts, and overhead speech bubbles.
     - Hovering tile inspector tooltip near mouse cursor.
  7. Telemetry HUD & Status Screens:
     - Survivor profile with dynamic mood facial expression based on vitals.
     - 6 Need Bars with dual-layer glossy progress bars and color gradation.
     - Composite stress gauge & hardware decoherence meter.
     - Event hazard banner and chronological order-effect chain.
     - Action probability horizontal bar chart with leading action highlight.
     - Plain-language quantum reasoning quote box neatly wrapped.
  8. End-of-Event Debrief Screen & Action History Log Overlay:
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
from engine.world import IslandWorld, MAP_SEED
from engine.agent import SurvivalAgent
from engine.events import EventGenerator, VOLCANIC
from engine.simulation import SimulationEngine, DEFAULT_STEPS

try:
    from mind.decoherence import decoherence_strength
except ImportError:
    def decoherence_strength(stress):
        return min(1.0, max(0.0, (stress - 0.4) / 0.5))


# -----------------------------------------------------------------------------
# Configuration & High-Resolution Display Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
MAP_SIZE = 900
GRID_DIM = 40
TILE_SIZE = MAP_SIZE / GRID_DIM  # 22.5 px per tile
FPS = 60

# Palette Definitions - Grounded, Human-Native Research & Tactical Survival Palette
COLOR_BG = (17, 20, 26)           # Deep Graphite Base (Matte, comfortable to eyes)
COLOR_PANEL_BG = (25, 30, 38)     # Tactical Slate Console Surface
COLOR_PANEL_ALT = (20, 24, 31)    # Recessed Sub-panel / Cavity
COLOR_CARD_BORDER = (44, 52, 64)  # 1px Technical Hairline Border
COLOR_CARD_HOVER = (68, 78, 94)   # Clean Steel Edge Highlight (Non-neon)

COLOR_TEXT_MAIN = (240, 244, 248) # Off-white Titanium (readable, zero glare)
COLOR_TEXT_MUTED = (152, 164, 178)# Slate Technical Grey
COLOR_TEXT_HINT = (100, 112, 126) # Metadata & Coordinate Grey

# Human-Native Semantic Accents (Organic Earth, Foliage & Mineral)
COLOR_GREEN = (46, 139, 87)       # Deep Forest Sea-Green (Pine / Life / Survival)
COLOR_GREEN_DARK = (28, 88, 56)   # Dense Moss / Canopy
COLOR_CYAN = (64, 136, 178)       # Mineral Hydration Blue (Natural water, non-neon)
COLOR_CYAN_LIGHT = (100, 168, 208)# Clear Alpine Spring
COLOR_PURPLE = (110, 100, 170)    # SMR Cobalt / Deep Indigo (Quantum math, non-neon)
COLOR_PURPLE_LIGHT = (145, 135, 200)
COLOR_YELLOW = (205, 148, 42)     # Warm Field Amber (Caution / Nutrition)
COLOR_RED = (188, 54, 54)         # Rust Iron Crimson (Lethal Hazard / Critical)
COLOR_BLUE = (68, 108, 168)       # Classical Rational Slate-Blue
COLOR_ORANGE = (212, 94, 46)      # Volcanic Terracotta / Magma
COLOR_GOLD = (214, 162, 54)       # Sun / Timber Ochre

# Tile Base Colors - Organic Earth & Satellite Cartography
TILE_COLORS = {
    0: (22, 44, 70),     # Deep Ocean Mineral Navy
    1: (182, 156, 104),  # Coastal Sands / Sunlit Grassland
    2: (32, 82, 52),     # Dense Pine Forest Canopy
    3: (78, 86, 96),     # Granite & Basalt Rock Crag
    4: (152, 94, 46)     # Handcrafted Cedar Shelter
}

ACTION_COLORS = {
    "forage": (46, 139, 87),         # Forest Green
    "drink": (64, 136, 178),         # Mineral Blue
    "build_shelter": (180, 110, 48), # Timber Cedar
    "rest": (110, 100, 170),         # Deep Indigo
    "explore": (205, 148, 42),       # Earth Amber
    "craft": (140, 150, 164),        # Tool Steel
    "hide": (188, 54, 54)            # Alert Rust
}

ISLAND_PRESETS = [
    {"label": "Archipelago (Seed 101)", "seed": 101, "tag": "Balanced | High Survival", "color": COLOR_GREEN},
    {"label": "Arid Crag (Seed 105)", "seed": 105, "tag": "Arid Interior | Thirst Peril", "color": COLOR_ORANGE},
    {"label": "Interference Lab (Seed 202)", "seed": 202, "tag": "Order Effect Divergence", "color": COLOR_PURPLE},
    {"label": "Heroic Haven (Seed 777)", "seed": 777, "tag": "Timber Rich | Freshwater", "color": COLOR_CYAN}
]

VOLCANO_PRESETS = [
    {"label": "Event Seed 101", "seed": 101, "tag": "Standard Unrest | Timed Pulse", "color": COLOR_CYAN},
    {"label": "Event Seed 105", "seed": 105, "tag": "Rapid Escalation | Fast Lava", "color": COLOR_ORANGE},
    {"label": "Event Seed 202", "seed": 202, "tag": "Order Effect Divergence", "color": COLOR_PURPLE},
    {"label": "Event Seed 777", "seed": 777, "tag": "Severe PDC Surge | Eruption", "color": COLOR_RED}
]


def set_cursor_safely(cursor_type):
    """Safely sets system mouse cursor, handling environments without window manager support."""
    try:
        pygame.mouse.set_cursor(cursor_type)
    except Exception:
        pass


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

    elif icon == "menu" or icon == "home":
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

    elif icon == "shield":
        pts = [(cx - size // 3, cy - size // 3), (cx + size // 3, cy - size // 3),
               (cx + size // 3, cy), (cx, cy + size // 3), (cx - size // 3, cy)]
        pygame.draw.polygon(surface, color, pts, 2)

    elif icon == "volcano":
        pts = [(x + pad, y + size - pad), (cx - size // 6, cy - size // 4),
               (cx + size // 6, cy - size // 4), (x + size - pad, y + size - pad)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.circle(surface, COLOR_YELLOW, (cx, cy - size // 4), max(2, size // 6))

    elif icon == "tree":
        pygame.draw.rect(surface, (139, 69, 19), (cx - 1, cy + 2, 3, size // 3))
        pygame.draw.polygon(surface, color, [(cx - size // 3, cy + 2), (cx + size // 3, cy + 2), (cx, cy - size // 3)])

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
    current_line = []
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
                        line_spacing: int = 4, max_lines: int = 4) -> int:
    """Renders text strictly wrapped inside container boundaries, returns bottom y."""
    lines = wrap_text(text, font, max_width)
    curr_y = y
    for i, line in enumerate(lines[:max_lines]):
        if i == max_lines - 1 and len(lines) > max_lines:
            line_str = line + "..."
            while line_str and font.size(line_str)[0] > max_width:
                line_str = line_str[:-4] + "..."
            txt_surf = font.render(line_str, True, color)
        else:
            txt_surf = font.render(line, True, color)
        surface.blit(txt_surf, (x, curr_y))
        curr_y += font.get_linesize() + line_spacing
    return curr_y


# -----------------------------------------------------------------------------
# UI Component Classes
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

        # 1. Subtle drop shadow
        if not self.is_pressed:
            shadow_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 90), (0, 0, self.rect.width, self.rect.height), border_radius=4)
            surface.blit(shadow_surf, (self.rect.x, self.rect.y + 1))

        # 2. Body fill and borders (Tactile, non-AI styling)
        if self.is_active:
            bg = (min(255, self.active_color[0] // 4 + self.bg_color[0]),
                  min(255, self.active_color[1] // 4 + self.bg_color[1]),
                  min(255, self.active_color[2] // 4 + self.bg_color[2]))
            border = self.active_color
            border_w = 1
        elif self.is_hovered:
            bg = (min(255, self.bg_color[0] + 16), min(255, self.bg_color[1] + 16), min(255, self.bg_color[2] + 20))
            border = COLOR_CARD_HOVER
            border_w = 1
        else:
            bg = self.bg_color
            border = self.border_color
            border_w = 1

        pygame.draw.rect(surface, bg, draw_rect, border_radius=4)
        pygame.draw.rect(surface, border, draw_rect, border_w, border_radius=4)

        # Click ripple flash
        if self.ripple_timer > 0:
            alpha = int((self.ripple_timer / 0.25) * 80)
            rip_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            rip_surf.fill((255, 255, 255, alpha))
            surface.blit(rip_surf, (draw_rect.x, draw_rect.y))

        # Text & Vector Icon Assembly
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
# Weather & Particle Systems
# -----------------------------------------------------------------------------
class WeatherSystem:
    def __init__(self, bounds: Tuple[int, int]):
        self.bounds = bounds
        self.rain_drops: List[List[float]] = []
        self.snow_flakes: List[List[float]] = []
        self.ash_flakes: List[List[float]] = []
        self.particles: List[List[Any]] = []

        for _ in range(110):
            self.rain_drops.append([random.uniform(0, bounds[0]), random.uniform(0, bounds[1]), random.uniform(500, 750)])
        for _ in range(85):
            self.snow_flakes.append([random.uniform(0, bounds[0]), random.uniform(0, bounds[1]), random.uniform(30, 70), random.uniform(1.2, 2.5)])
        for _ in range(95):
            self.ash_flakes.append([random.uniform(0, bounds[0]), random.uniform(0, bounds[1]), random.uniform(40, 80), random.uniform(1.0, 2.2)])

    def update(self, event: str, dt: float, ash_level: float = 0.0):
        if event == "storm":
            for drop in self.rain_drops:
                drop[1] += drop[2] * dt
                drop[0] += drop[2] * 0.25 * dt
                if drop[1] > self.bounds[1]:
                    drop[1] = 0
                    drop[0] = random.uniform(0, self.bounds[0])

        elif event == "cold_night":
            for flake in self.snow_flakes:
                flake[1] += flake[2] * dt
                flake[0] += math.sin(flake[1] * 0.04) * 20 * dt
                if flake[1] > self.bounds[1]:
                    flake[1] = 0
                    flake[0] = random.uniform(0, self.bounds[0])

        if ash_level > 0.02:
            for ash in self.ash_flakes:
                ash[1] += ash[2] * dt
                ash[0] += math.cos(ash[1] * 0.03) * 15 * dt
                if ash[1] > self.bounds[1]:
                    ash[1] = 0
                    ash[0] = random.uniform(0, self.bounds[0])

        # Action Particles
        alive_particles = []
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] > 0:
                alive_particles.append(p)
        self.particles = alive_particles

    def add_action_particles(self, x: float, y: float, action: str):
        color = ACTION_COLORS.get(action, COLOR_CYAN)
        for _ in range(14):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 130)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.3, 0.7)
            size = random.uniform(2, 4.5)
            self.particles.append([x, y, vx, vy, life, size, color])

    def draw(self, surface: pygame.Surface, event: str, ash_level: float = 0.0):
        if event == "storm":
            for drop in self.rain_drops:
                x1, y1 = int(drop[0]), int(drop[1])
                x2, y2 = x1 + 2, y1 + 7
                pygame.draw.line(surface, (148, 197, 253, 140), (x1, y1), (x2, y2), 1)

        elif event == "cold_night":
            for flake in self.snow_flakes:
                pygame.draw.circle(surface, (241, 245, 249, 180), (int(flake[0]), int(flake[1])), int(flake[3]))

        if ash_level > 0.02:
            for ash in self.ash_flakes:
                alpha = int(min(220, 100 + ash_level * 120))
                pygame.draw.circle(surface, (80, 80, 80, alpha), (int(ash[0]), int(ash[1])), int(ash[3]))

        for p in self.particles:
            alpha = max(0, min(255, int((p[4] / 0.7) * 255)))
            p_surf = pygame.Surface((int(p[5] * 2), int(p[5] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*p[6][:3], alpha), (int(p[5]), int(p[5])), int(p[5]))
            surface.blit(p_surf, (int(p[0] - p[5]), int(p[1] - p[5])))


# -----------------------------------------------------------------------------
# Island Pygame Viewer Application
# -----------------------------------------------------------------------------
class IslandVisualizerApp:
    def __init__(self, seed: int = 101, mind_type: str = "quantum", noise_source: str = "stub",
                 start_screen: str = "event_choice", scenario: str = "volcano"):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Quantum Cognition Simulation")

        # Determine desktop size for aspect-ratio fit
        info = pygame.display.Info()
        self.desktop_w = info.current_w or 1600
        self.desktop_h = info.current_h or 900

        # Choose initial windowed size
        if self.desktop_w >= 1680 and self.desktop_h >= 980:
            self.window_w, self.window_h = 1600, 900
        elif self.desktop_w >= 1480 and self.desktop_h >= 860:
            self.window_w, self.window_h = 1440, 810
        else:
            self.window_w, self.window_h = 1280, 720

        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False

        # Fonts: Authentic Engineered / Field Simulation Typography
        # Uses Bahnschrift (DIN-spec engineering font) with clean fallbacks
        self.font_hero = pygame.font.SysFont("bahnschrift, trebuchetms, segoeui", 23, bold=True)
        self.font_title = pygame.font.SysFont("bahnschrift, trebuchetms, segoeui", 17, bold=True)
        self.font_sub = pygame.font.SysFont("bahnschrift, trebuchetms, segoeui", 13, bold=True)
        self.font_body = pygame.font.SysFont("segoeuivariable, segoeui, calibri, arial", 13)
        self.font_small = pygame.font.SysFont("segoeuivariable, segoeui, calibri, arial", 11)
        self.font_mono = pygame.font.SysFont("cascadiamono, consolas, courier", 12)
        self.font_bubble = pygame.font.SysFont("segoeui, calibri", 12, bold=True)

        # Simulation Parameters
        self.app_state = start_screen   # "event_choice", "home", "sim"
        self.scenario = scenario         # "island" or "volcano"
        self.seed = seed
        self.mind_type = mind_type.lower()
        self.noise_source = noise_source
        self.max_steps = DEFAULT_STEPS
        self.step_speed = 0.4
        self.speed_multiplier = 1.0
        self.auto_step_timer = 0.0
        self.is_paused = False

        # Build Interactive Buttons
        self._build_event_choice_buttons()
        self._build_home_buttons()
        self._build_sim_buttons()

        # Overlays
        self.show_evacuation_map = True
        self.show_history_overlay = False
        self.show_debrief_modal = False

        # Initialize Simulation Engine
        self._init_simulation()

        # Visual Systems
        self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
        self.weather = WeatherSystem((MAP_SIZE, MAP_SIZE))
        self.char_screen_x = self.world.spawn_pos[0] * TILE_SIZE + TILE_SIZE / 2
        self.char_screen_y = self.world.spawn_pos[1] * TILE_SIZE + TILE_SIZE / 2
        self.char_target_x = self.char_screen_x
        self.char_target_y = self.char_screen_y
        self.char_bob = 0.0
        self.bubble_text = ""
        self.bubble_timer = 0.0
        self.selected_tile: Optional[Tuple[int, int]] = None

    def toggle_fullscreen(self):
        """Native hardware fullscreen toggle mapping to native resolution."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

    def get_virtual_mouse_pos(self) -> Tuple[int, int]:
        """Maps physical window mouse coordinates to 1600x900 virtual coordinates."""
        real_x, real_y = pygame.mouse.get_pos()
        sw, sh = self.screen.get_size()
        scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
        scaled_w = int(WINDOW_WIDTH * scale)
        scaled_h = int(WINDOW_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2

        vx = (real_x - offset_x) / scale
        vy = (real_y - offset_y) / scale
        return int(max(0, min(WINDOW_WIDTH - 1, vx))), int(max(0, min(WINDOW_HEIGHT - 1, vy)))

    def _generate_mini_map(self, seed: int, size: int = 300) -> pygame.Surface:
        surf = pygame.Surface((size, size))
        w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=seed, scenario=self.scenario)
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

        if self.scenario == "volcano":
            # Vent
            vx, vy = int(w.vent[0] * t_sz), int(w.vent[1] * t_sz)
            pygame.draw.circle(surf, COLOR_RED, (vx, vy), 6)
            pygame.draw.circle(surf, COLOR_YELLOW, (vx, vy), 3)
            # Assembly points
            for ax, ay in w.assembly_points:
                pygame.draw.circle(surf, COLOR_GREEN, (int(ax * t_sz), int(ay * t_sz)), 5)

        # Spawn indicator (red dot with white border)
        sx, sy = int(w.spawn_pos[0] * t_sz), int(w.spawn_pos[1] * t_sz)
        pygame.draw.circle(surf, COLOR_RED, (sx, sy), 6)
        pygame.draw.circle(surf, COLOR_TEXT_MAIN, (sx, sy), 4)
        return surf

    def _build_event_choice_buttons(self):
        """Constructs buttons for the Event Choice Hub."""
        c1_x, c2_x = 170, 850
        card_w, card_y, card_h = 580, 135, 600
        btn_y = card_y + card_h - 68
        btn_w = card_w - 70

        self.card1_rect = pygame.Rect(c1_x, card_y, card_w, card_h)
        self.card2_rect = pygame.Rect(c2_x, card_y, card_w, card_h)

        self.btn_choice_island = UIButton(
            (c1_x + 35, btn_y, btn_w, 48),
            "INITIATE ISLAND SURVIVAL  →", self.font_title,
            bg_color=(28, 64, 44), active_color=COLOR_GREEN, icon="tree"
        )
        self.btn_choice_volcano = UIButton(
            (c2_x + 35, btn_y, btn_w, 48),
            "INITIATE VOLCANO EVACUATION  →", self.font_title,
            bg_color=(118, 46, 32), active_color=COLOR_ORANGE, icon="volcano"
        )

    def _build_home_buttons(self):
        col2_x = 480
        top_y = 115

        # Navigation / Fullscreen Toggle on Home Screen
        self.btn_home_back_scenario = UIButton(
            (32, 24, 180, 36), "< Change Scenario", self.font_sub,
            bg_color=COLOR_PANEL_ALT, active_color=COLOR_GOLD, icon="menu"
        )
        self.btn_home_fs = UIButton(
            (WINDOW_WIDTH - 170, 24, 140, 36), "Fullscreen", self.font_body,
            bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen"
        )

        # 1. Mind Toggle Cards
        card_w = 515
        self.btn_mind_quantum = UIButton(
            (col2_x + 24, top_y + 36, card_w, 80), "2-Qubit Quantum Mind", self.font_title,
            subtext="Non-commuting belief rotations + simulated dephasing (stress model)",
            subfont=self.font_small, active_color=COLOR_PURPLE, icon="quantum"
        )
        self.btn_mind_classical = UIButton(
            (col2_x + 555, top_y + 36, card_w, 80), "Classical Rational Mind", self.font_title,
            subtext="Deterministic utility argmax derived from published ATUS summary tables",
            subfont=self.font_small, active_color=COLOR_BLUE, icon="classical"
        )

        # 2. Preset Buttons (2x2 Grid)
        self.preset_buttons: List[UIButton] = []
        p_y = top_y + 165
        presets = VOLCANO_PRESETS if self.scenario == "volcano" else ISLAND_PRESETS
        for i, preset in enumerate(presets):
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
        rand_label = "Random Events" if self.scenario == "volcano" else "Random Island"
        self.btn_seed_rand = UIButton((col2_x + 768, s_y, 270, 38), rand_label, self.font_sub,
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
        self.btn_hero_launch = self.btn_launch

    def _build_sim_buttons(self):
        # Map view top navigation bar buttons
        self.btn_nav_home = UIButton((14, 10, 95, 32), "Menu", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="menu")
        self.btn_nav_pause = UIButton((115, 10, 90, 32), "Pause", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_YELLOW, icon="pause")
        self.btn_nav_step = UIButton((211, 10, 85, 32), "Step >", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_GREEN, icon="step")
        self.btn_nav_speed = UIButton((302, 10, 110, 32), "Speed 1.0x", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="speed")
        self.btn_nav_mind = UIButton((418, 10, 115, 32), "Quantum", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_PURPLE, icon="quantum")
        self.btn_nav_evac = UIButton((539, 10, 105, 32), "Evac (E)", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_ORANGE, icon="shield")
        self.btn_nav_log = UIButton((650, 10, 115, 32), "Action Log", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="log")
        self.btn_nav_fs = UIButton((771, 10, 115, 32), "Fullscreen", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen")

        # Debrief modal buttons
        mx = WINDOW_WIDTH // 2
        my = WINDOW_HEIGHT // 2
        self.btn_modal_replay = UIButton((mx - 340, my + 175, 150, 46), "Replay Run", self.font_sub, bg_color=(36, 68, 96), active_color=COLOR_CYAN, icon="replay")
        self.btn_modal_switch = UIButton((mx - 175, my + 175, 175, 46), "Compare Mind", self.font_sub, bg_color=(56, 48, 84), active_color=COLOR_PURPLE, icon="compare")
        self.btn_modal_scenario = UIButton((mx + 15, my + 175, 175, 46), "Change Scenario", self.font_sub, bg_color=(84, 52, 36), active_color=COLOR_ORANGE, icon="menu")
        self.btn_modal_home = UIButton((mx + 205, my + 175, 135, 46), "Settings", self.font_sub, bg_color=(36, 42, 52), active_color=COLOR_CARD_HOVER, icon="home")
        self.btn_modal_close = UIButton((mx + 390, my - 225, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

        # History log modal close
        self.btn_hist_close = UIButton((WINDOW_WIDTH // 2 + 500, 45, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

    def _init_simulation(self):
        self.engine = SimulationEngine(
            seed=self.seed,
            mind_type=self.mind_type,
            noise_source=self.noise_source,
            scenario=self.scenario
        )
        self.world = self.engine.world
        self.agent = self.engine.agent
        self.event_gen = self.engine.event_gen
        self.decide_fn = self.engine.decide_fn
        self.history: List[Dict[str, Any]] = []
        self.current_decision: Dict[str, Any] = {
            "action": "none",
            "probs": {a: 1.0 / len(contracts.ACTIONS) for a in contracts.ACTIONS},
            "reason": "Initial baseline belief state."
        }
        self.current_event = "none"
        self.current_weather = "calm"
        self.wind_deg = 0.0
        self.step_idx = 0
        self.history_scroll = 0
        self.show_debrief_modal = False
        self.show_history_overlay = False
        self.is_paused = False
        self.bubble_text = ""
        self.bubble_timer = 0.0
        self.char_screen_x = (self.agent.pos[0] + 0.5) * TILE_SIZE
        self.char_screen_y = (self.agent.pos[1] + 0.5) * TILE_SIZE
        self.char_target_x = self.char_screen_x
        self.char_target_y = self.char_screen_y
        if hasattr(self, "weather"):
            self.weather.particles.clear()

    def step_forward(self):
        """Advances the simulation by one 2-hour step."""
        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            return

        record = self.engine.step()
        if record is None:
            self.show_debrief_modal = True
            return

        self.step_idx += 1
        event, action = record["event"], record["action"]
        self.current_event = event
        self.current_weather = self.event_gen.weather[self.step_idx - 1]
        self.wind_deg = self.engine.volcano.hazard_by_step[self.step_idx - 1].get("wind_deg", 0.0)
        self.current_decision = record

        # Smooth avatar position target
        self.char_target_x = self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2
        self.char_target_y = self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2

        # Particles & Thought bubble
        self.weather.add_action_particles(self.char_screen_x, self.char_screen_y, action)
        reason = record.get("reason", "")
        clean_reason = reason.split(";")[0] if ";" in reason else reason[:36]
        self.bubble_text = f"{action.upper()}: {clean_reason}"
        self.bubble_timer = 2.8

        self.history.append({
            "t": self.step_idx,
            "state": record["state"],
            "event": event,
            "action": action,
            "decision": record,
            "narrative": reason
        })
        self.history_scroll = max(0, len(self.history) - 16)

        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True

    def handle_event(self, event, v_mouse: Optional[Tuple[int, int]] = None) -> bool:
        if v_mouse is None:
            v_mouse = self.get_virtual_mouse_pos()
        if event.type == pygame.QUIT:
            return False

        elif event.type == pygame.VIDEORESIZE:
            if not self.is_fullscreen:
                self.window_w, self.window_h = max(800, event.w), max(450, event.h)
                self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

        elif event.type == pygame.MOUSEWHEEL and self.show_history_overlay:
            self.history_scroll = max(0, min(max(0, len(self.history) - 7), self.history_scroll - event.y))

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif self.app_state == "event_choice":
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self._handle_event_choice_click(self.btn_choice_island.rect.center)
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    self._handle_event_choice_click(self.btn_choice_volcano.rect.center)
            elif event.key == pygame.K_SPACE and self.app_state == "sim":
                self.is_paused = not self.is_paused
            elif event.key in (pygame.K_RIGHT, pygame.K_n) and self.app_state == "sim":
                self.step_forward()
            elif event.key == pygame.K_q and self.app_state == "sim":
                self._toggle_mind()
            elif event.key == pygame.K_e:
                self.show_evacuation_map = not self.show_evacuation_map
            elif event.key == pygame.K_TAB and self.app_state == "sim":
                self.show_history_overlay = not self.show_history_overlay
            elif event.key == pygame.K_ESCAPE:
                if self.show_history_overlay:
                    self.show_history_overlay = False
                elif self.show_debrief_modal:
                    self.show_debrief_modal = False
                elif self.app_state == "sim":
                    self.app_state = "home"
                elif self.app_state == "home":
                    self.app_state = "event_choice"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.app_state == "event_choice":
                self._handle_event_choice_click(v_mouse)
            elif self.app_state == "home":
                self._handle_home_click(v_mouse)
            elif self.app_state == "sim":
                self._handle_sim_click(v_mouse)
        return True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            # Auto-stepping during unpaused simulation
            if self.app_state == "sim" and not self.is_paused and not self.show_debrief_modal and not self.show_history_overlay:
                self.auto_step_timer += dt * self.speed_multiplier
                if self.auto_step_timer >= self.step_speed:
                    self.auto_step_timer = 0.0
                    self.step_forward()

            v_mouse = self.get_virtual_mouse_pos()
            hover_any = self._update_hovers(v_mouse)
            if hover_any:
                set_cursor_safely(pygame.SYSTEM_CURSOR_HAND)
            else:
                set_cursor_safely(pygame.SYSTEM_CURSOR_ARROW)

            for event in pygame.event.get():
                if self.handle_event(event, v_mouse) is False:
                    running = False

            # Character Smooth Interpolation (Lerp)
            self.char_screen_x += (self.char_target_x - self.char_screen_x) * 12.0 * dt
            self.char_screen_y += (self.char_target_y - self.char_screen_y) * 12.0 * dt
            self.char_bob = math.sin(time.time() * 8.0) * 2.0

            if self.bubble_timer > 0:
                self.bubble_timer = max(0.0, self.bubble_timer - dt)

            ash_level = getattr(self.world, "ash", 0.0)
            self.weather.update(self.current_event, dt, ash_level=ash_level)

            # Render Scene
            self.draw(v_mouse)
            self.present()

        pygame.quit()

    def _toggle_mind(self):
        cycle = {"quantum": "classical_mixture", "classical_mixture": "classical", "classical": "quantum"}
        self.mind_type = cycle.get(self.mind_type, "quantum")
        self.engine.mind_type = self.mind_type
        if self.mind_type == "quantum":
            self.engine.decide_fn = contracts.quantum_decide
            self.btn_nav_mind.text = "Quantum"
            self.btn_nav_mind.active_color = COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            try:
                from mind.quantum_mind import classical_mixture_decide
                self.engine.decide_fn = classical_mixture_decide
            except ImportError:
                self.engine.decide_fn = contracts.classical_decide
            self.btn_nav_mind.text = "Mixture"
            self.btn_nav_mind.active_color = COLOR_CYAN
        else:
            self.engine.decide_fn = contracts.classical_decide
            self.btn_nav_mind.text = "Classical"
            self.btn_nav_mind.active_color = COLOR_BLUE
        self.decide_fn = self.engine.decide_fn

    def _update_hovers(self, pos: Tuple[int, int]) -> bool:
        hovered = False
        if self.app_state == "event_choice":
            c1_h = hasattr(self, 'card1_rect') and self.card1_rect.collidepoint(pos)
            c2_h = hasattr(self, 'card2_rect') and self.card2_rect.collidepoint(pos)
            return self.btn_choice_island.check_hover(pos) or self.btn_choice_volcano.check_hover(pos) or c1_h or c2_h

        elif self.app_state == "home":
            btns = [
                self.btn_home_back_scenario, self.btn_home_fs,
                self.btn_mind_quantum, self.btn_mind_classical,
                self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1,
                self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100, self.btn_seed_rand,
                self.btn_launch
            ] + self.preset_buttons + self.step_buttons
            for btn in btns:
                hovered = btn.check_hover(pos) or hovered
            return hovered

        elif self.app_state == "sim":
            if self.show_debrief_modal:
                return (self.btn_modal_replay.check_hover(pos) or self.btn_modal_switch.check_hover(pos) or
                        self.btn_modal_scenario.check_hover(pos) or self.btn_modal_home.check_hover(pos) or
                        self.btn_modal_close.check_hover(pos))
            if self.show_history_overlay:
                return self.btn_hist_close.check_hover(pos)

            nav_btns = [
                self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step,
                self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_evac,
                self.btn_nav_log, self.btn_nav_fs
            ]
            for btn in nav_btns:
                hovered = btn.check_hover(pos) or hovered
            return hovered

        return False

    def present(self):
        """Draws virtual canvas centered on physical window with letterboxing."""
        sw, sh = self.screen.get_size()
        scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
        scaled_w = int(WINDOW_WIDTH * scale)
        scaled_h = int(WINDOW_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2

        self.screen.fill((5, 8, 15))
        if scale == 1.0:
            self.screen.blit(self.canvas, (offset_x, offset_y))
        else:
            scaled_surf = pygame.transform.smoothscale(self.canvas, (scaled_w, scaled_h))
            self.screen.blit(scaled_surf, (offset_x, offset_y))
        pygame.display.flip()

    def _handle_mouse_click(self, pos: Tuple[int, int]):
        """Dispatches mouse clicks according to the active app state."""
        if self.app_state == "event_choice":
            self._handle_event_choice_click(pos)
        elif self.app_state == "home":
            self._handle_home_click(pos)
        elif self.app_state == "sim":
            self._handle_sim_click(pos)

    def _handle_event_choice_click(self, pos: Tuple[int, int]):
        c1_hit = self.btn_choice_island.check_hover(pos) or (hasattr(self, 'card1_rect') and self.card1_rect.collidepoint(pos))
        c2_hit = self.btn_choice_volcano.check_hover(pos) or (hasattr(self, 'card2_rect') and self.card2_rect.collidepoint(pos))
        if c1_hit:
            self.scenario = "island"
            self._build_home_buttons()
            self._init_simulation()
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            self.app_state = "home"
        elif c2_hit:
            self.scenario = "volcano"
            self._build_home_buttons()
            self._init_simulation()
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            self.app_state = "home"

    def _handle_home_click(self, pos: Tuple[int, int]):
        if self.btn_home_back_scenario.check_hover(pos):
            self.app_state = "event_choice"
            return
        if self.btn_home_fs.check_hover(pos):
            self.toggle_fullscreen()
            return
        if self.btn_mind_quantum.check_hover(pos):
            self.mind_type = "quantum"
            self.btn_mind_quantum.trigger_click()
            return
        if self.btn_mind_classical.check_hover(pos):
            self.mind_type = "classical"
            self.btn_mind_classical.trigger_click()
            return

        presets = VOLCANO_PRESETS if self.scenario == "volcano" else ISLAND_PRESETS
        for i, btn in enumerate(self.preset_buttons):
            if btn.check_hover(pos):
                self.seed = presets[i]["seed"]
                self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
                btn.trigger_click()
                return

        prev_seed = self.seed
        if self.btn_seed_m100.check_hover(pos):
            self.seed = max(1, self.seed - 100)
        elif self.btn_seed_m10.check_hover(pos):
            self.seed = max(1, self.seed - 10)
        elif self.btn_seed_m1.check_hover(pos):
            self.seed = max(1, self.seed - 1)
        elif self.btn_seed_p1.check_hover(pos):
            self.seed += 1
        elif self.btn_seed_p10.check_hover(pos):
            self.seed += 10
        elif self.btn_seed_p100.check_hover(pos):
            self.seed += 100
        elif self.btn_seed_rand.check_hover(pos):
            self.seed = random.randint(10, 999)

        if self.seed != prev_seed:
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            return

        step_choices = [12, 24, 36, 48]
        for i, btn in enumerate(self.step_buttons):
            if btn.check_hover(pos):
                self.max_steps = step_choices[i]
                btn.trigger_click()
                return

        if self.btn_launch.check_hover(pos):
            self._init_simulation()
            self.char_screen_x = self.world.spawn_pos[0] * TILE_SIZE + TILE_SIZE / 2
            self.char_screen_y = self.world.spawn_pos[1] * TILE_SIZE + TILE_SIZE / 2
            self.char_target_x = self.char_screen_x
            self.char_target_y = self.char_screen_y
            self.app_state = "sim"

    def _handle_sim_click(self, pos: Tuple[int, int]):
        if self.show_debrief_modal:
            if self.btn_modal_replay.check_hover(pos):
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_switch.check_hover(pos):
                self._toggle_mind()
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_scenario.check_hover(pos):
                self.app_state = "event_choice"
            elif self.btn_modal_home.check_hover(pos) or self.btn_modal_close.check_hover(pos):
                self.app_state = "home"
            return

        if self.show_history_overlay:
            if self.btn_hist_close.check_hover(pos):
                self.show_history_overlay = False
            return

        if self.btn_nav_home.check_hover(pos):
            self.app_state = "home"
        elif self.btn_nav_pause.check_hover(pos):
            self.is_paused = not self.is_paused
            self.btn_nav_pause.trigger_click()
        elif self.btn_nav_step.check_hover(pos):
            self.step_forward()
            self.btn_nav_step.trigger_click()
        elif self.btn_nav_speed.check_hover(pos):
            speeds = [0.5, 1.0, 2.0, 4.0]
            curr_idx = speeds.index(self.speed_multiplier) if self.speed_multiplier in speeds else 1
            self.speed_multiplier = speeds[(curr_idx + 1) % len(speeds)]
            self.btn_nav_speed.trigger_click()
        elif self.btn_nav_mind.check_hover(pos):
            self._toggle_mind()
            self.btn_nav_mind.trigger_click()
        elif self.btn_nav_evac.check_hover(pos):
            self.show_evacuation_map = not self.show_evacuation_map
            self.btn_nav_evac.trigger_click()
        elif self.btn_nav_log.check_hover(pos):
            self.show_history_overlay = True
            self.btn_nav_log.trigger_click()
        elif self.btn_nav_fs.check_hover(pos):
            self.toggle_fullscreen()
            self.btn_nav_fs.trigger_click()

        # Map tile click inspector
        elif pos[0] < MAP_SIZE and pos[1] >= 52:
            tx = int(pos[0] / TILE_SIZE)
            ty = int(pos[1] / TILE_SIZE)
            if 0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM:
                self.selected_tile = (tx, ty)

    def draw(self, mouse_pos: Tuple[int, int] = (0, 0)):
        if self.app_state == "event_choice":
            self.draw_event_choice_screen(mouse_pos)
        elif self.app_state == "home":
            self.draw_home_screen(mouse_pos)
        elif self.app_state == "sim":
            self.draw_sim_screen(mouse_pos)

    # -------------------------------------------------------------------------
    # Render Event Choice Screen (State 0) - Tactical Research Dossier Style
    # -------------------------------------------------------------------------
    def draw_event_choice_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)

        # Header Navigation Strip
        header_y = 28
        title_surf = self.font_hero.render("QUANTUM COGNITION SIMULATION", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, header_y))

        sub_str = "SURVIVAL DEPLOYMENT SELECTOR  •  COGNITIVE ARCHITECTURE UNDER CRISIS"
        sub_surf = self.font_sub.render(sub_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, header_y + 36))

        # 1px Subtle divider line
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (170, header_y + 70), (WINDOW_WIDTH - 170, header_y + 70), 1)

        # Scenario Cards Setup
        c1_x, c2_x = 170, 850
        card_w, c_y, card_h = 580, 125, 620

        hover_c1 = (hasattr(self, 'card1_rect') and self.card1_rect.collidepoint(mouse_pos)) or self.btn_choice_island.check_hover(mouse_pos)
        hover_c2 = (hasattr(self, 'card2_rect') and self.card2_rect.collidepoint(mouse_pos)) or self.btn_choice_volcano.check_hover(mouse_pos)

        # -------------------------------------------------------------
        # Card 1: Archipelago Survival (Island Wilderness)
        # -------------------------------------------------------------
        c1_border = COLOR_GREEN if hover_c1 else COLOR_CARD_BORDER
        self.draw_card(c1_x, c_y, card_w, card_h, border_color=c1_border, border_width=1)

        # Corner Sector Badge
        self.draw_badge(c1_x + 28, c_y + 24, "SECTOR 01: ARCHIPELAGO", COLOR_GREEN)
        self.canvas.blit(self.font_title.render("ISLAND WILDERNESS SURVIVAL", True, COLOR_TEXT_MAIN), (c1_x + 28, c_y + 56))
        self.canvas.blit(self.font_small.render("Procedural Terrain  •  Resource Extraction  •  Shelter Dynamics", True, COLOR_TEXT_MUTED), (c1_x + 28, c_y + 82))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (c1_x + 24, c_y + 108), (c1_x + card_w - 24, c_y + 108), 1)

        desc1 = (
            "An uncharted island generated from procedural noise. The survivor must balance caloric hunger, "
            "hydration, and hypothermia against stochastic maritime gales and predator fauna, harvesting timber "
            "to construct shelters before sub-zero nightfall."
        )
        render_wrapped_text(self.canvas, desc1, self.font_body, COLOR_TEXT_MUTED, c1_x + 28, c_y + 125, card_w - 56, line_spacing=5, max_lines=4)

        # Parameter Specifications Table
        f_y = c_y + 235
        self.canvas.blit(self.font_sub.render("TECHNICAL SPECIFICATIONS", True, COLOR_GOLD), (c1_x + 28, f_y))
        f_y += 28
        specs1 = [
            ("Grid Matrix", "40 × 40 cells (100 km² coverage | 250m scale)", COLOR_CYAN),
            ("Topography", "Pine canopy, freshwater streams, alpine snowcaps", COLOR_GREEN),
            ("Environment", "Maritime storms, freezing nights, territorial fauna", COLOR_YELLOW),
            ("Cognitive Model", "2-qubit belief state interference & exploration walk", COLOR_PURPLE)
        ]
        for label, val, dot_col in specs1:
            pygame.draw.circle(self.canvas, dot_col, (c1_x + 36, f_y + 8), 3)
            lbl_surf = self.font_mono.render(f"{label:16s}", True, COLOR_TEXT_MAIN)
            self.canvas.blit(lbl_surf, (c1_x + 48, f_y))
            val_surf = self.font_small.render(val, True, COLOR_TEXT_MUTED)
            self.canvas.blit(val_surf, (c1_x + 48 + lbl_surf.get_width(), f_y + 1))
            f_y += 30

        self.btn_choice_island.check_hover(mouse_pos)
        self.btn_choice_island.draw(self.canvas)

        # -------------------------------------------------------------
        # Card 2: Caldera Evacuation (Volcano Hazard)
        # -------------------------------------------------------------
        c2_border = COLOR_ORANGE if hover_c2 else COLOR_CARD_BORDER
        self.draw_card(c2_x, c_y, card_w, card_h, border_color=c2_border, border_width=1)

        # Corner Sector Badge
        self.draw_badge(c2_x + 28, c_y + 24, "SECTOR 02: CALDERA", COLOR_ORANGE)
        self.canvas.blit(self.font_title.render("VOLCANO ERUPTION EVACUATION", True, COLOR_TEXT_MAIN), (c2_x + 28, c_y + 56))
        self.canvas.blit(self.font_small.render("Calibrated Topography  •  Seismic Unrest  •  Emergency Routing", True, COLOR_TEXT_MUTED), (c2_x + 28, c_y + 82))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (c2_x + 24, c_y + 108), (c2_x + card_w - 24, c_y + 108), 1)

        desc2 = (
            "A calibrated stratovolcano enters rapid precursory unrest. The agent must interpret tremor and "
            "gas warnings, navigate around expanding lava flows and toxic ash deposition, and execute "
            "shortest-path routes to designated coastal assembly zones."
        )
        render_wrapped_text(self.canvas, desc2, self.font_body, COLOR_TEXT_MUTED, c2_x + 28, c_y + 125, card_w - 56, line_spacing=5, max_lines=4)

        # Parameter Specifications Table
        f_y2 = c_y + 235
        self.canvas.blit(self.font_sub.render("TECHNICAL SPECIFICATIONS", True, COLOR_GOLD), (c2_x + 28, f_y2))
        f_y2 += 28
        specs2 = [
            ("Grid Matrix", "40 × 40 cells (Calibrated basalt topography)", COLOR_CYAN),
            ("Corridors", "Central caldera, radial valleys & coastal assembly", COLOR_ORANGE),
            ("Hazards", "Advancing lava, ash deposition, lethal PDCs & lahars", COLOR_RED),
            ("Cognitive Model", "Stress-induced decoherence & threat prioritization", COLOR_PURPLE)
        ]
        for label, val, dot_col in specs2:
            pygame.draw.circle(self.canvas, dot_col, (c2_x + 36, f_y2 + 8), 3)
            lbl_surf = self.font_mono.render(f"{label:16s}", True, COLOR_TEXT_MAIN)
            self.canvas.blit(lbl_surf, (c2_x + 48, f_y2))
            val_surf = self.font_small.render(val, True, COLOR_TEXT_MUTED)
            self.canvas.blit(val_surf, (c2_x + 48 + lbl_surf.get_width(), f_y2 + 1))
            f_y2 += 30

        self.btn_choice_volcano.check_hover(mouse_pos)
        self.btn_choice_volcano.draw(self.canvas)

        # -------------------------------------------------------------
        # Footer Technical Shortcut Bar
        # -------------------------------------------------------------
        footer_w, footer_h = 620, 32
        footer_x = (WINDOW_WIDTH - footer_w) // 2
        footer_y = WINDOW_HEIGHT - 54
        foot_rect = pygame.Rect(footer_x, footer_y, footer_w, footer_h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, foot_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, foot_rect, 1, border_radius=4)

        tip_str = "[ 1 ] Initiate Island Survey       [ 2 ] Initiate Volcano Evacuation       [ F11 ] Fullscreen"
        hint_surf = self.font_mono.render(tip_str, True, COLOR_TEXT_HINT)
        self.canvas.blit(hint_surf, (footer_x + (footer_w - hint_surf.get_width()) // 2, footer_y + (footer_h - hint_surf.get_height()) // 2))

    # -------------------------------------------------------------------------
    # Render Home Screen (State 1) - Field Mission Planning Console
    # -------------------------------------------------------------------------
    def draw_home_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)

        # Back to Scenario Hub Button
        self.btn_home_back_scenario.check_hover(mouse_pos)
        self.btn_home_back_scenario.draw(self.canvas)

        # Fullscreen Toggle Button on Home Screen
        self.btn_home_fs.text = "Windowed" if self.is_fullscreen else "Fullscreen"
        self.btn_home_fs.icon = "windowed" if self.is_fullscreen else "fullscreen"
        self.btn_home_fs.check_hover(mouse_pos)
        self.btn_home_fs.draw(self.canvas)

        # Header Title
        title_surf = self.font_hero.render("QUANTUM COGNITION SIMULATION", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 22))

        scen_tag = "VOLCANO ERUPTION EVACUATION" if self.scenario == "volcano" else "ISLAND WILDERNESS SURVIVAL"
        sub_str = f"DEPLOYMENT: {scen_tag}  •  2-QUBIT COGNITIVE ENGINE  •  QISKIT 2.x"
        sub_surf = self.font_sub.render(sub_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 58))

        # Left Reconnaissance Card: Live Island Mini-Map (430 x 760)
        col1_x = 32
        col1_y = 96
        col1_w = 430
        col1_h = 760
        self.draw_card(col1_x, col1_y, col1_w, col1_h)

        c1_title = self.font_title.render("TOPOGRAPHIC RECONNAISSANCE", True, COLOR_YELLOW)
        self.canvas.blit(c1_title, (col1_x + 22, col1_y + 18))

        # Mini-map container (300 x 300)
        map_box = pygame.Rect(col1_x + (col1_w - 300) // 2, col1_y + 54, 300, 300)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, map_box, 2, border_radius=6)
        self.canvas.blit(self.preview_mini_map, (map_box.x, map_box.y))

        # Spawn dot legend with procedural drawing
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

        temp_w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=self.seed, scenario=self.scenario)
        land_tiles = sum(1 for row in temp_w.tiles for t in row if t in (1, 2, 3, 4))
        forest_tiles = sum(1 for row in temp_w.tiles for t in row if t == 2)
        streams = len(temp_w.freshwater_tiles)
        land_pct = int(land_tiles / (GRID_DIM * GRID_DIM) * 100)
        forest_pct = int(forest_tiles / max(1, land_tiles) * 100)

        lines = [
            f"Active Seed:      #{self.seed}",
            f"Grid Geometry:    40x40 (1,600 Tiles)",
            f"Land Coverage:    {land_pct}% (Usable Mass)",
            f"Forest Density:   {forest_pct}% (Timber & Food)",
            f"Freshwater:       {str(streams) + ' tiles' if streams > 0 else 'Arid / Sparse'}",
            f"Starting Spawn:   [{temp_w.spawn_pos[0]}, {temp_w.spawn_pos[1]}]",
            f"Scenario Horizon: {self.scenario.upper()}",
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

        # 2. Presets & Custom Stepper
        preset_title = "2. Select Scenario Preset or Custom Seed"
        p_lbl = self.font_title.render(preset_title, True, COLOR_TEXT_MAIN)
        self.canvas.blit(p_lbl, (col2_x + 24, col2_y + 138))

        presets = VOLCANO_PRESETS if self.scenario == "volcano" else ISLAND_PRESETS
        for i, p_btn in enumerate(self.preset_buttons):
            p_btn.is_active = (self.seed == presets[i]["seed"])
            p_btn.check_hover(mouse_pos)
            p_btn.draw(self.canvas)

        seed_box = pygame.Rect(col2_x + 215, col2_y + 300, 345, 38)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, seed_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, seed_box, 1, border_radius=6)
        seed_txt = self.font_title.render(f"Simulation Seed:  #{self.seed}", True, COLOR_YELLOW)
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

        h_title = self.font_sub.render("SIMULATION DYNAMICS & COGNITIVE MODEL SPECIFICATION", True, COLOR_CYAN)
        self.canvas.blit(h_title, (hints_box.x + 18, hints_box.y + 14))

        bullet_lines = [
            "  * Quantum Mind: Belief states represented as 2-qubit amplitudes with non-commuting projection angles.",
            "  * Order Effect: Experiencing [Storm -> Find Food] yields distinct actions compared to [Find Food -> Storm].",
            "  * Stress Model: Physiological stress maps to a simulated dephasing channel (stress model); no hardware decoherence is driven live.",
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

        # 2. Dynamic Weather & Lighting Overlays
        self.draw_atmosphere()

        # 3. Dynamic Animated Character
        self.draw_character()

        # 4. Top Navigation Bar (Integrated Over Map)
        self.draw_map_navigation_bar(mouse_pos)

        # 5. Tile Inspector Tooltip (Hover)
        self.draw_tile_tooltip(mouse_pos)

        # 6. Telemetry & Analytics Dashboard (700 x 900)
        self.draw_dashboard()

        # 7. Action History Overlay Modal
        if self.show_history_overlay:
            self.draw_history_overlay(mouse_pos)

        # 8. End-of-Event Debrief Screen Modal
        if self.show_debrief_modal:
            self.draw_debrief_modal(mouse_pos)

    def draw_map_navigation_bar(self, mouse_pos: Tuple[int, int]):
        bar_bg = pygame.Surface((MAP_SIZE, 52), pygame.SRCALPHA)
        bar_bg.fill((16, 23, 38, 235))
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

        for btn in (self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step, self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_evac, self.btn_nav_log, self.btn_nav_fs):
            btn.check_hover(mouse_pos)
            btn.draw(self.canvas)

    def draw_island_map(self):
        t_time = time.time()
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = self.world.get_tile(x, y)
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                rect = pygame.Rect(rx, ry, rw, rh)

                if tile == 0:
                    is_fresh = (x, y) in self.world.freshwater_tiles
                    if is_fresh:
                        flow = math.sin(t_time * 3.5 + x * 0.5 + y * 0.5) * 12
                        base = (54, max(40, min(145, 118 + int(flow))), 154)
                        pygame.draw.rect(self.canvas, base, rect)
                        pygame.draw.circle(self.canvas, (170, 210, 235), (rx + rw // 2, ry + rh // 2), 2)
                    else:
                        wave = math.sin(t_time * 1.8 + x * 0.35 + y * 0.45) * 6
                        c = (22, max(36, min(56, int(44 + wave))), 70)
                        pygame.draw.rect(self.canvas, c, rect)

                elif tile == 1:
                    has_water_adj = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if has_water_adj:
                        # Coastal dunes / beach sand
                        color = (186, 164, 122)
                        speck = (166, 144, 102)
                    else:
                        # Prairie grassland / meadow
                        color = (96, 126, 74)
                        speck = (82, 110, 62)
                    pygame.draw.rect(self.canvas, color, rect)
                    pygame.draw.rect(self.canvas, speck, (rx + 4, ry + 4, 3, 3))

                elif tile == 2:
                    # Forest canopy
                    pygame.draw.rect(self.canvas, (32, 82, 52), rect)
                    pygame.draw.circle(self.canvas, (24, 70, 42), (rx + rw // 2, ry + rh // 2), rw // 2 - 1)
                    if (x, y) in self.world.food_tiles:
                        pygame.draw.circle(self.canvas, (178, 54, 54), (rx + 6, ry + 6), 3)
                        pygame.draw.circle(self.canvas, (178, 54, 54), (rx + 15, ry + 8), 3)

                elif tile == 3:
                    # Mountain granite crag & snow peak
                    pygame.draw.rect(self.canvas, (78, 86, 96), rect)
                    p1 = (rx + rw // 2, ry + 3)
                    p2 = (rx + 3, ry + rh - 3)
                    p3 = (rx + rw - 3, ry + rh - 3)
                    pygame.draw.polygon(self.canvas, (62, 70, 80), [p1, p2, p3])
                    pygame.draw.polygon(self.canvas, (224, 228, 234), [p1, (rx + rw // 2 - 4, ry + 8), (rx + rw // 2 + 4, ry + 8)])

                elif tile == 4:
                    # Crafted cedar shelter
                    pygame.draw.rect(self.canvas, (82, 110, 62), rect)
                    p_roof = [(rx + rw // 2, ry + 2), (rx + 2, ry + rh - 3), (rx + rw - 2, ry + rh - 3)]
                    pygame.draw.polygon(self.canvas, (142, 92, 54), p_roof)
                    ember_glow = int(math.sin(t_time * 5.0) * 25)
                    pygame.draw.circle(self.canvas, (214, max(80, min(160, 128 + ember_glow)), 48), (rx + rw // 2, ry + rh - 5), 3)

        # Volcano Caldera & Hazards (if volcano scenario)
        if self.scenario == "volcano":
            vx, vy = self.world.vent
            vrx = int(vx * TILE_SIZE + TILE_SIZE / 2)
            vry = int(vy * TILE_SIZE + TILE_SIZE / 2)
            pygame.draw.circle(self.canvas, (48, 38, 38), (vrx, vry), 15)
            pygame.draw.circle(self.canvas, (188, 54, 42), (vrx, vry), 10)
            pygame.draw.circle(self.canvas, (214, 112, 46), (vrx, vry), 5)

            # Evacuation Map Overlay
            if self.show_evacuation_map:
                overlay = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                colors = ((46, 120, 68, 35), (185, 135, 35, 45), (180, 50, 40, 65))
                for y, row in enumerate(self.world.zones):
                    for x, zone in enumerate(row):
                        if self.world.get_tile(x, y):
                            rx = int(round(x * TILE_SIZE))
                            ry = int(round(y * TILE_SIZE))
                            rw = int(round((x + 1) * TILE_SIZE)) - rx
                            rh = int(round((y + 1) * TILE_SIZE)) - ry
                            pygame.draw.rect(overlay, colors[zone], (rx, ry, rw, rh))

                points = [(int(x * TILE_SIZE + TILE_SIZE // 2), int(y * TILE_SIZE + TILE_SIZE // 2)) for x, y in self.world.route_from_spawn]
                if len(points) > 1:
                    pygame.draw.lines(overlay, (90, 165, 210, 200), False, points, 2)

                for x, y in self.world.assembly_points:
                    pygame.draw.circle(overlay, (52, 148, 88), (int(x * TILE_SIZE + TILE_SIZE // 2), int(y * TILE_SIZE + TILE_SIZE // 2)), 7)
                    pygame.draw.circle(overlay, (240, 244, 248), (int(x * TILE_SIZE + TILE_SIZE // 2), int(y * TILE_SIZE + TILE_SIZE // 2)), 3)
                self.canvas.blit(overlay, (0, 0))

            # Active Hazards: Lava, PDC, Lahar
            hazard_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            for x, y in getattr(self.world, "lava", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pulse = math.sin(t_time * 3.5 + x + y) * 15
                pygame.draw.rect(hazard_surf, (204, max(50, min(110, int(72 + pulse))), 32, 160), (rx, ry, rw, rh))

            for x, y in getattr(self.world, "pdc", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pygame.draw.rect(hazard_surf, (70, 66, 68, 140), (rx, ry, rw, rh))

            for x, y in getattr(self.world, "lahar", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pygame.draw.rect(hazard_surf, (88, 62, 38, 140), (rx, ry, rw, rh))

            ash_val = getattr(self.world, "ash", 0.0)
            if ash_val > 0.02:
                ash_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                ash_surf.fill((120, 120, 120, int(60 * ash_val)))
                hazard_surf.blit(ash_surf, (0, 0))

            self.canvas.blit(hazard_surf, (0, 0))

        # Cartographic Scale & Minimalist Compass Overlays
        # Bottom-left Scale bar
        scale_box = pygame.Rect(14, MAP_SIZE - 32, 150, 22)
        pygame.draw.rect(self.canvas, (17, 20, 26, 210), scale_box, border_radius=3)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, scale_box, 1, border_radius=3)
        self.canvas.blit(self.font_small.render("SCALE: 1 TILE = 250m", True, COLOR_TEXT_HINT), (scale_box.x + 8, scale_box.y + 3))

        # Top-right Compass indicator
        comp_box = pygame.Rect(MAP_SIZE - 68, 60, 56, 22)
        pygame.draw.rect(self.canvas, (17, 20, 26, 210), comp_box, border_radius=3)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, comp_box, 1, border_radius=3)
        self.canvas.blit(self.font_small.render("N  ▲", True, COLOR_TEXT_MUTED), (comp_box.x + 14, comp_box.y + 3))

        # Selected tile reticle (tactical corner brackets, not neon cyan)
        if self.selected_tile:
            tx, ty = self.selected_tile
            sx = int(tx * TILE_SIZE)
            sy = int(ty * TILE_SIZE)
            sw = int(TILE_SIZE)
            sh = int(TILE_SIZE)
            s_rect = pygame.Rect(sx, sy, sw, sh)
            pygame.draw.rect(self.canvas, COLOR_CARD_HOVER, s_rect, 1)
            # Corner ticks
            c_len = 4
            pygame.draw.lines(self.canvas, COLOR_GOLD, False, [(sx, sy + c_len), (sx, sy), (sx + c_len, sy)], 1)
            pygame.draw.lines(self.canvas, COLOR_GOLD, False, [(sx + sw - c_len, sy), (sx + sw, sy), (sx + sw, sy + c_len)], 1)
            pygame.draw.lines(self.canvas, COLOR_GOLD, False, [(sx, sy + sh - c_len), (sx, sy + sh), (sx + c_len, sy + sh)], 1)
            pygame.draw.lines(self.canvas, COLOR_GOLD, False, [(sx + sw - c_len, sy + sh), (sx + sw, sy + sh), (sx + sw, sy + sh - c_len)], 1)

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 1)

    def draw_atmosphere(self):
        hour = self.agent.hour
        if hour >= 21 or hour <= 5:
            night_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            night_surf.fill((10, 15, 30, 115))
            self.canvas.blit(night_surf, (0, 0))

        if self.current_event == "cold_night":
            frost_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            frost_surf.fill((140, 180, 220, 38))
            self.canvas.blit(frost_surf, (0, 0))

        ash_val = getattr(self.world, "ash", 0.0)
        self.weather.draw(self.canvas, self.current_event, ash_level=ash_val)

    def draw_character(self):
        cx, cy = int(self.char_screen_x), int(self.char_screen_y + self.char_bob)

        # Ground Shadow
        shadow_surf = pygame.Surface((26, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 85), (0, 0, 26, 12))
        self.canvas.blit(shadow_surf, (cx - 13, cy + 7))

        # Torso & Clothing (Field Parka)
        body_color = (192, 112, 42) if not self.agent.injured else (172, 48, 48)
        pygame.draw.rect(self.canvas, body_color, (cx - 6, cy - 7, 12, 14), border_radius=2)

        # Head & Watch Cap
        pygame.draw.circle(self.canvas, (244, 204, 164), (cx, cy - 12), 7)
        pygame.draw.circle(self.canvas, (48, 64, 96), (cx, cy - 14), 7, 2)
        # Satchel
        pygame.draw.rect(self.canvas, (110, 68, 36), (cx + 4, cy - 5, 5, 8), border_radius=1)

        # Injury Cross
        if self.agent.injured:
            pygame.draw.circle(self.canvas, COLOR_RED, (cx - 10, cy - 16), 6)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 13, cy - 16), (cx - 7, cy - 16), 2)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 10, cy - 19), (cx - 10, cy - 13), 2)

        # Shelter Shield
        if self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1]):
            pygame.draw.polygon(self.canvas, COLOR_GREEN, [(cx, cy - 25), (cx - 7, cy - 18), (cx + 7, cy - 18)])

        # Speech / Thought Bubble (Tactical readout bubble)
        if self.bubble_timer > 0 and self.bubble_text:
            text_surf = self.font_bubble.render(self.bubble_text, True, COLOR_TEXT_MAIN)
            tw, th = text_surf.get_width() + 18, text_surf.get_height() + 10
            bx = max(10, min(MAP_SIZE - tw - 10, cx - tw // 2))
            by = cy - 50

            b_rect = pygame.Rect(bx, by, tw, th)
            pygame.draw.rect(self.canvas, COLOR_PANEL_BG, b_rect, border_radius=4)
            b_border = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE
            pygame.draw.rect(self.canvas, b_border, b_rect, 1, border_radius=4)
            pygame.draw.polygon(self.canvas, COLOR_PANEL_BG, [(cx - 4, by + th), (cx + 4, by + th), (cx, by + th + 5)])
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
        if self.scenario == "volcano" and hasattr(self.world, "zones"):
            zone_names = {0: "Safe", 1: "Caution", 2: "Danger"}
            desc += f" | Zone: {zone_names.get(self.world.zones[ty][tx], 'Unknown')}"

        tt_str = f"[{tx:02d}, {ty:02d}] {tile_name}  |  {desc}"
        txt_surf = self.font_small.render(tt_str, True, COLOR_TEXT_MAIN)

        tt_w, tt_h = txt_surf.get_width() + 18, txt_surf.get_height() + 10
        tt_x = max(10, min(MAP_SIZE - tt_w - 10, mx + 14))
        tt_y = max(58, min(MAP_SIZE - tt_h - 10, my - 28))

        tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, tt_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, tt_rect, 1, border_radius=4)
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
            mood_str = f"Perished ({str(self.agent.cause_of_death).upper()})"
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
            ("Safety", needs["safety"], (110, 126, 148)),
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

        decoherence_pct = decoherence_strength(self.agent.stress)
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
        ev_color = COLOR_RED if ev_upper in ("STORM", "INJURY", "ANIMAL", "ERUPTION") else (COLOR_CYAN if ev_upper in ("COLD_NIGHT", "TREMOR") else COLOR_GREEN)
        self.draw_badge(panel_x + 16, curr_y + 38, f"ACTIVE HAZARD: {ev_upper}", ev_color)

        if self.scenario == "volcano" and hasattr(self.engine, "volcano"):
            phase = self.engine.volcano.phases[max(0, self.step_idx - 1)]
            phase_col = COLOR_RED if phase == "erupting" else (COLOR_ORANGE if phase == "escalating" else COLOR_GREEN)
            self.draw_badge(panel_x + 240, curr_y + 38, f"PHASE: {phase.upper()}", phase_col)

        px, py = self.agent.pos
        tile_name = contracts.TILE_TYPES.get(self.world.get_tile(px, py), "Unknown").capitalize()
        pos_txt = f"Sector: [{px:02d}, {py:02d}]  |  Biome: {tile_name}  |  Shelter: {'Sheltered' if self.world.is_in_shelter(px, py) else 'Exposed'}"
        self.canvas.blit(self.font_body.render(pos_txt, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 72))

        clean_events = [e.upper() for e in self.agent.recent_events if e != "none"] or ["NONE"]
        history_str = " -> ".join(clean_events)
        hist_display = f"Order Effect Chain: [ {history_str} ]"
        max_h_w = panel_w - 32
        if self.font_mono.size(hist_display)[0] > max_h_w:
            while hist_display and self.font_mono.size(hist_display + "... ]")[0] > max_h_w:
                hist_display = hist_display[:-1]
            hist_display = hist_display.rstrip() + "... ]"
        self.canvas.blit(self.font_mono.render(hist_display, True, COLOR_TEXT_MAIN), (panel_x + 16, curr_y + 100))

        curr_y += card2_h + 12

        # Card 3: Quantum Superposition & Probabilities (width = 668, height = 370)
        card3_h = 370
        self.draw_card(panel_x, curr_y, panel_w, card3_h)

        if self.mind_type == "quantum":
            mind_title, mind_col = "2-QUBIT QUANTUM BELIEF STATE", COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            mind_title, mind_col = "CLASSICAL MIXTURE CONTROL (λ=1)", COLOR_CYAN
        else:
            mind_title, mind_col = "CLASSICAL RATIONAL UTILITY", COLOR_BLUE
        self.canvas.blit(self.font_sub.render(mind_title, True, mind_col), (panel_x + 16, curr_y + 12))

        chosen_act = self.current_decision.get("action", "none").upper()
        self.draw_badge(panel_x + 16, curr_y + 38, f"EXECUTED ACTION: {chosen_act}", ACTION_COLORS.get(chosen_act.lower(), COLOR_GREEN))

        q_diag = self.current_decision.get("quantum")
        if q_diag:
            q_str = f"P(danger)={q_diag.get('p_danger',0):.2f} | P(prot)={q_diag.get('p_protect',0):.2f} | |x|={q_diag.get('coherence',0):.2f}"
            self.canvas.blit(self.font_mono.render(q_str, True, COLOR_TEXT_MUTED), (panel_x + 260, curr_y + 42))

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
            pygame.draw.rect(self.canvas, (17, 20, 26), bar_rect, border_radius=2)
            fill_w = max(2, int(p * chart_w))
            pygame.draw.rect(self.canvas, act_color, (panel_x + 125, chart_y + 3, fill_w, 12), border_radius=2)

            pct_lbl = self.font_mono.render(f"{p*100:4.1f}%", True, COLOR_TEXT_MUTED)
            self.canvas.blit(pct_lbl, (panel_x + 135 + chart_w, chart_y))
            chart_y += 22

        # Cognitive Reasoning Quote Box (Assembled Neatly Inside Borders)
        reason_rect = pygame.Rect(panel_x + 16, chart_y + 10, panel_w - 32, 95)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, reason_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, reason_rect, 1, border_radius=4)

        reason_txt = self.current_decision.get("reason", "Baseline cognitive evaluation.")
        render_wrapped_text(
            surface=self.canvas,
            text=reason_txt,
            font=self.font_body,
            color=COLOR_TEXT_MAIN,
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
        c_line2 = "[Q] Switch Mind Model  |   [E] Evacuation Map     |   [TAB] Action History Log"
        self.canvas.blit(self.font_body.render(c_line1, True, COLOR_TEXT_MAIN), (panel_x + 16, curr_y + 44))
        self.canvas.blit(self.font_body.render(c_line2, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 72))

    # -------------------------------------------------------------------------
    # Render End-of-Event Debrief Screen Modal
    # -------------------------------------------------------------------------
    def draw_debrief_modal(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 26, 215))
        self.canvas.blit(dim_surf, (0, 0))

        mw, mh = 860, 520
        mx, my = (WINDOW_WIDTH - mw) // 2, (WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, m_rect, border_radius=6)

        survived = self.agent.is_alive
        border_col = COLOR_GOLD if survived else COLOR_RED
        pygame.draw.rect(self.canvas, border_col, m_rect, 1, border_radius=6)

        m_title = "MISSION COMPLETE: 72h SURVIVAL MASTERED" if survived else f"MISSION OVER: SURVIVOR PERISHED ({str(self.agent.cause_of_death).upper()})"
        m_color = COLOR_GOLD if survived else COLOR_RED
        t_surf = self.font_hero.render(m_title, True, m_color)
        self.canvas.blit(t_surf, (mx + (mw - t_surf.get_width()) // 2, my + 28))

        scen_str = "Volcano Evacuation" if self.scenario == "volcano" else "Island Wilderness"
        dur_str = f"Endured {self.step_idx}/{self.max_steps} Steps ({self.step_idx * 2} Game Hours in {scen_str})"
        d_surf = self.font_sub.render(dur_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(d_surf, (mx + (mw - d_surf.get_width()) // 2, my + 74))

        box_rect = pygame.Rect(mx + 36, my + 115, mw - 72, 230)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box_rect, 1, border_radius=4)

        if self.mind_type == "quantum":
            engine_name, engine_col = "2-Qubit Quantum Deliberation (Validated Unitary Model)", COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            engine_name, engine_col = "Classical Mixture Control (λ=1, Zero Coherence)", COLOR_CYAN
        else:
            engine_name, engine_col = "Classical ATUS Rational Utility (Argmax)", COLOR_BLUE

        lines = [
            ("Decision Engine:", engine_name, engine_col),
            ("World Environment:", f"Seed #{self.seed} ({scen_str}, 40x40 Grid, 1600 Tiles)", COLOR_TEXT_MAIN),
            ("Final Stress & Noise:", f"{int(self.agent.stress*100)}% Stress  |  Decoherence: {int(decoherence_strength(self.agent.stress) * 100)}% off-diagonal decay (stress model)", COLOR_CYAN),
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
        self.btn_modal_scenario.check_hover(mouse_pos)
        self.btn_modal_home.check_hover(mouse_pos)
        self.btn_modal_close.check_hover(mouse_pos)

        self.btn_modal_replay.draw(self.canvas)
        self.btn_modal_switch.draw(self.canvas)
        self.btn_modal_scenario.draw(self.canvas)
        self.btn_modal_home.draw(self.canvas)
        self.btn_modal_close.draw(self.canvas)

    # -------------------------------------------------------------------------
    # Render Full Action History Overlay (Tab / Log Key)
    # -------------------------------------------------------------------------
    def draw_history_overlay(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 26, 225))
        self.canvas.blit(dim_surf, (0, 0))

        hw, hh = 1100, 750
        hx, hy = (WINDOW_WIDTH - hw) // 2, (WINDOW_HEIGHT - hh) // 2
        h_rect = pygame.Rect(hx, hy, hw, hh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, h_rect, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_HOVER, h_rect, 1, border_radius=6)

        t_surf = self.font_title.render("ACTION & COGNITIVE DECISION HISTORY LOG", True, COLOR_TEXT_MAIN)
        self.canvas.blit(t_surf, (hx + 30, hy + 24))

        self.btn_hist_close.check_hover(mouse_pos)
        self.btn_hist_close.draw(self.canvas)

        col_t = hx + 30
        col_ev = hx + 105
        col_act = hx + 240
        col_prob = hx + 380
        col_reason = hx + 480

        log_y = hy + 64
        self.canvas.blit(self.font_sub.render("Step", True, COLOR_TEXT_MUTED), (col_t, log_y))
        self.canvas.blit(self.font_sub.render("Event Hazard", True, COLOR_TEXT_MUTED), (col_ev, log_y))
        self.canvas.blit(self.font_sub.render("Chosen Action", True, COLOR_TEXT_MUTED), (col_act, log_y))
        self.canvas.blit(self.font_sub.render("Top Prob", True, COLOR_TEXT_MUTED), (col_prob, log_y))
        self.canvas.blit(self.font_sub.render("Cognitive Reasoning", True, COLOR_TEXT_MUTED), (col_reason, log_y))

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (hx + 30, log_y + 28), (hx + hw - 30, log_y + 28), 1)

        row_y = log_y + 40
        visible_records = self.history[self.history_scroll : self.history_scroll + 16]
        for rec in visible_records:
            t_num = f"#{rec['t']:02d}"
            ev = rec["event"].upper()
            act = rec["action"].upper()
            probs = rec["decision"].get("probs", {})
            top_p = max(probs.values()) if probs else 0.0
            p_str = f"{top_p*100:4.1f}%"
            reason_raw = rec["decision"].get("reason", "")

            act_col = ACTION_COLORS.get(rec["action"], COLOR_TEXT_MAIN)

            self.canvas.blit(self.font_mono.render(t_num, True, COLOR_TEXT_HINT), (col_t, row_y))
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
    def draw_card(self, x: int, y: int, w: int, h: int, border_color: Optional[Tuple[int, int, int]] = None, border_width: int = 1):
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, (x, y, w, h), border_radius=4)
        pygame.draw.rect(self.canvas, border_color or COLOR_CARD_BORDER, (x, y, w, h), border_width, border_radius=4)

    def draw_pill_tag(self, x: int, y: int, text: str, color: Tuple[int, int, int]) -> int:
        txt_surf = self.font_small.render(text, True, color)
        pw = txt_surf.get_width() + 20
        ph = 26
        pill_rect = pygame.Rect(x, y, pw, ph)
        pill_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pill_surf.fill((color[0], color[1], color[2], 25))
        self.canvas.blit(pill_surf, (x, y))
        pygame.draw.rect(self.canvas, color, pill_rect, 1, border_radius=13)
        self.canvas.blit(txt_surf, (x + 10, y + (ph - txt_surf.get_height()) // 2))
        return pw

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

        fill_w = max(0, min(bar_w, int(bar_w * value)))
        if fill_w > 0:
            pygame.draw.rect(self.canvas, color, (bar_x, y + 2, fill_w, h - 4), border_radius=3)

        val_surf = self.font_mono.render(f"{int(value * 100):3d}%", True, COLOR_TEXT_MUTED)
        self.canvas.blit(val_surf, (bar_x + bar_w + 8, y))


def launch_gui(seed: int = 101, mind: str = "quantum", noise: str = "stub", start_screen: str = "event_choice"):
    """Launches the complete Pygame Quantum Cognition Simulation starting at the Event Choice Screen."""
    app = IslandVisualizerApp(seed=seed, mind_type=mind, noise_source=noise, start_screen=start_screen)
    app.run()

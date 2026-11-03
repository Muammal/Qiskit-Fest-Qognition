"""engine/gui.py - Interactive 2D Pygame Island Simulation, Event Hub, Home Screen & Debrief HUD
Quantum Cognition Simulation Engine
Tech C Deliverable (Integration, Engine, Visualization).

Enhanced Suite:
  1. High-Resolution 1600x900 Widescreen Display:
     - 16:9 standard cinematic aspect ratio.
     - 900x900 high-definition island & volcano map viewport.
     - 700x900 expansive telemetry and analytics dashboard.
     - Fullscreen toggle via [Fullscreen] button or F11 key with letterboxing/pillarboxing
       and exact mouse coordinate transformation at any display resolution.
  2. Event Choice Hub (First user screen):
     - Select between "Island Wilderness Survival" and "Volcano Eruption Evacuation".
  3. Procedural Vector Iconography (Zero Broken Unicode Squares):
     - Eliminates all font-dependent unicode emojis and tofu squares.
     - Crisp, resolution-independent vector icons drawn directly with Pygame geometry.
  4. Strict Text Assembly & Border-Bound Typography:
     - Dynamic text wrapping (`wrap_text` and `render_wrapped_text`) ensuring decision rationales,
       event chains, telemetry labels, and modal metrics never spill or exceed container borders.
  5. 2D Island & Volcano Living World Viewport:
     - Procedural 40x40 tiles with dynamic water waves, freshwater streams, shore foam,
       layered pine canopies with food berry clusters, and alpine snowcaps.
     - Central volcanic caldera with glowing molten lava meanders, pyroclastic flow corridors,
       lahars, and atmospheric ash fallout.
     - Evacuation zone overlays (Safe, Caution, Danger) and route pathing to assembly points.
     - Dynamic lighting & weather: day ambient warmth, night navy tint (21:00-05:00),
       storm rain with lightning flashes, and cold night frost vignette with drifting snow.
     - Animated survivor avatar with walking interpolation (lerp), bobbing, condition badges,
       particle bursts, and overhead speech bubbles.
  6. Telemetry HUD & Status Screens:
     - Survivor profile with dynamic mood facial expression based on vitals.
     - 6 Need Bars with dual-layer glossy progress bars and color gradation.
     - Composite stress gauge & hardware decoherence meter.
     - Interactive 3D Bloch sphere representation.
     - Volcanic status badges & evacuation indicators.
     - Live mind toggle button between Quantum and Classical.
"""

import math
import os
import random
import sys
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import contracts
from engine.world import IslandWorld, MAP_SEED
from engine.simulation import SimulationEngine, DEFAULT_STEPS
from engine.agent import SurvivalAgent
from engine.events import EventGenerator, VOLCANIC


# -----------------------------------------------------------------------------
# Configuration & Virtual Display Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
MAP_SIZE = 900
GRID_DIM = 40
TILE_SIZE = MAP_SIZE / GRID_DIM  # 22.5 px per tile
FPS = 60

# Palette Definitions
COLOR_BG = (10, 14, 23)
COLOR_PANEL_BG = (15, 23, 42)
COLOR_PANEL_ALT = (23, 32, 54)
COLOR_CARD_BORDER = (45, 62, 95)
COLOR_BORDER_FOCUS = (56, 189, 248)

COLOR_TEXT_MAIN = (241, 245, 249)
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_TEXT_HINT = (100, 116, 139)

COLOR_CYAN = (6, 182, 212)
COLOR_PURPLE = (168, 85, 247)
COLOR_BLUE = (59, 130, 246)
COLOR_GREEN = (34, 197, 94)
COLOR_YELLOW = (234, 179, 8)
COLOR_ORANGE = (249, 115, 22)
COLOR_RED = (239, 68, 68)
COLOR_GOLD = (250, 204, 21)

# Tile Base Colors
TILE_COLORS = {
    0: (14, 116, 144),   # Water: Ocean / deep sea
    1: (202, 138, 4),    # Plains: Sandy beaches & dry savanna
    2: (21, 128, 61),    # Forest: Lush temperate pines
    3: (71, 85, 105),    # Mountain: Slate rock / crags
    4: (168, 85, 247)    # Shelter: Purple safety beacon
}

ACTION_COLORS = {
    "forage": COLOR_GREEN,
    "drink": COLOR_CYAN,
    "build_shelter": COLOR_PURPLE,
    "rest": COLOR_YELLOW,
    "hide": COLOR_ORANGE,
    "explore": (192, 132, 252),
    "idle": COLOR_TEXT_MUTED
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


def set_cursor_hand():
    try:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    except Exception:
        pass


def set_cursor_arrow():
    try:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    except Exception:
        pass


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Strictly wraps a string into lines that do not exceed max_width pixels."""
    if not text:
        return []
    words = text.split(" ")
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
                # Word is longer than max_width, truncate with ellipsis
                clipped = word
                while clipped and font.size(clipped + "...")[0] > max_width:
                    clipped = clipped[:-1]
                lines.append(clipped + "...")
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def render_wrapped_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    rect: pygame.Rect,
    line_spacing: int = 4,
    max_lines: int = 10
) -> int:
    """Renders text strictly wrapped inside `rect` boundaries, returns bottom y coordinate."""
    lines = wrap_text(text, font, rect.width)
    y = rect.y
    rendered_count = 0
    for line in lines:
        if rendered_count >= max_lines or (y + font.get_linesize() > rect.bottom):
            break
        txt_surf = font.render(line, True, color)
        surface.blit(txt_surf, (rect.x, y))
        y += font.get_linesize() + line_spacing
        rendered_count += 1
    return y


def draw_vector_icon(surface: pygame.Surface, icon_name: str, rect: pygame.Rect, color: Tuple[int, int, int], filled: bool = True):
    """Draws resolution-independent vector iconography using Pygame geometry."""
    cx, cy = rect.centerx, rect.centery
    r = min(rect.width, rect.height) // 2

    if icon_name == "fullscreen":
        s = r - 1
        pygame.draw.lines(surface, color, False, [(cx - s, cy - s + 5), (cx - s, cy - s), (cx - s + 5, cy - s)], 2)
        pygame.draw.lines(surface, color, False, [(cx + s - 5, cy - s), (cx + s, cy - s), (cx + s, cy - s + 5)], 2)
        pygame.draw.lines(surface, color, False, [(cx - s, cy + s - 5), (cx - s, cy + s), (cx - s + 5, cy + s)], 2)
        pygame.draw.lines(surface, color, False, [(cx + s - 5, cy + s), (cx + s, cy + s), (cx + s, cy + s - 5)], 2)

    elif icon_name == "windowed":
        s = r - 2
        pygame.draw.rect(surface, color, (cx - s, cy - s, s * 2, s * 2), 2)
        pygame.draw.line(surface, color, (cx - s, cy - s + 4), (cx + s, cy - s + 4), 1)

    elif icon_name == "atom":
        pygame.draw.circle(surface, color, (cx, cy), max(2, r // 4))
        pygame.draw.ellipse(surface, color, (cx - r, cy - r // 2, r * 2, r), 1)
        pygame.draw.ellipse(surface, color, (cx - r // 2, cy - r, r, r * 2), 1)

    elif icon_name == "network":
        nodes = [(cx - r + 3, cy), (cx, cy - r + 3), (cx, cy + r - 3), (cx + r - 3, cy)]
        for n1 in nodes:
            for n2 in nodes:
                if n1 != n2:
                    pygame.draw.line(surface, (color[0], color[1], color[2], 120), n1, n2, 1)
        for n in nodes:
            pygame.draw.circle(surface, color, n, 3)

    elif icon_name == "play":
        pts = [(cx - r // 2, cy - r), (cx + r, cy), (cx - r // 2, cy + r)]
        pygame.draw.polygon(surface, color, pts)

    elif icon_name == "pause":
        w = max(2, r // 3)
        pygame.draw.rect(surface, color, (cx - r // 2 - w // 2, cy - r, w, r * 2))
        pygame.draw.rect(surface, color, (cx + r // 2 - w // 2, cy - r, w, r * 2))

    elif icon_name == "step":
        pts = [(cx - r, cy - r), (cx + r // 3, cy), (cx - r, cy + r)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.rect(surface, color, (cx + r // 2, cy - r, max(2, r // 3), r * 2))

    elif icon_name == "speed":
        pts = [(cx + 2, cy - r), (cx - r + 2, cy + 2), (cx, cy + 2), (cx - 2, cy + r), (cx + r - 2, cy - 2), (cx, cy - 2)]
        pygame.draw.polygon(surface, color, pts)

    elif icon_name == "home" or icon_name == "menu":
        pts = [(cx, cy - r), (cx + r, cy), (cx - r, cy)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.rect(surface, color, (cx - r * 2 // 3, cy, r * 4 // 3, r))
        pygame.draw.rect(surface, COLOR_PANEL_BG, (cx - r // 3, cy + r // 3, r * 2 // 3, r * 2 // 3))

    elif icon_name == "log" or icon_name == "history":
        pygame.draw.rect(surface, color, (cx - r + 2, cy - r, r * 2 - 4, r * 2), 2)
        for dy in (-r // 2, 0, r // 2):
            pygame.draw.line(surface, color, (cx - r + 6, cy + dy), (cx + r - 6, cy + dy), 2)

    elif icon_name == "dice":
        pygame.draw.rect(surface, color, (cx - r, cy - r, r * 2, r * 2), 2, border_radius=3)
        pygame.draw.circle(surface, color, (cx - r // 2, cy - r // 2), 2)
        pygame.draw.circle(surface, color, (cx, cy), 2)
        pygame.draw.circle(surface, color, (cx + r // 2, cy + r // 2), 2)

    elif icon_name == "rocket":
        pts = [(cx, cy - r), (cx + r // 2, cy), (cx + r // 2, cy + r // 2), (cx - r // 2, cy + r // 2), (cx - r // 2, cy)]
        pygame.draw.polygon(surface, color, pts)
        fin_l = [(cx - r // 2, cy + r // 4), (cx - r, cy + r * 3 // 4), (cx - r // 2, cy + r // 2)]
        fin_r = [(cx + r // 2, cy + r // 4), (cx + r, cy + r * 3 // 4), (cx + r // 2, cy + r // 2)]
        pygame.draw.polygon(surface, color, fin_l)
        pygame.draw.polygon(surface, color, fin_r)

    elif icon_name == "replay":
        pygame.draw.arc(surface, color, (cx - r, cy - r, r * 2, r * 2), 0.5, 5.5, 2)
        arrow = [(cx + r - 4, cy - 4), (cx + r + 3, cy + 2), (cx + r - 5, cy + 6)]
        pygame.draw.polygon(surface, color, arrow)

    elif icon_name == "compare":
        pygame.draw.rect(surface, color, (cx - r, cy - r, r - 1, r * 2), 2)
        pygame.draw.rect(surface, color, (cx + 1, cy - r, r - 1, r * 2), 2)
        pygame.draw.line(surface, COLOR_YELLOW, (cx, cy - r), (cx, cy + r), 2)

    elif icon_name == "shield":
        pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surface, color, pts, 2 if not filled else 0)

    elif icon_name == "volcano":
        pts = [(cx - r, cy + r), (cx - r // 3, cy - r // 2), (cx + r // 3, cy - r // 2), (cx + r, cy + r)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.circle(surface, COLOR_YELLOW, (cx, cy - r // 2), r // 3)
        pygame.draw.circle(surface, COLOR_RED, (cx, cy - r // 2 - 2), 3)

    elif icon_name == "tree":
        pygame.draw.rect(surface, (139, 69, 19), (cx - 2, cy + 2, 4, r - 2))
        for layer in range(3):
            ly = cy + 2 - layer * (r // 2)
            lw = r - layer * 3
            pygame.draw.polygon(surface, color, [(cx - lw, ly), (cx + lw, ly), (cx, ly - r // 2)])

    else:
        # Default circle
        pygame.draw.circle(surface, color, (cx, cy), r, 2)


# -----------------------------------------------------------------------------
# UI Component Classes
# -----------------------------------------------------------------------------
class UIButton:
    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        text: str,
        font: pygame.font.Font,
        bg_color: Tuple[int, int, int] = COLOR_PANEL_ALT,
        hover_color: Tuple[int, int, int] = (30, 41, 59),
        active_color: Tuple[int, int, int] = COLOR_CYAN,
        text_color: Tuple[int, int, int] = COLOR_TEXT_MAIN,
        border_radius: int = 6,
        icon: Optional[str] = None
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.active_color = active_color
        self.text_color = text_color
        self.border_radius = border_radius
        self.icon = icon
        self.is_hovered = False
        self.is_active = False

    def check_hover(self, pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def trigger_click(self):
        """Programmatically triggers button click feedback."""
        self.is_active = True

    def draw(self, surface: pygame.Surface):
        col = self.hover_color if self.is_hovered else self.bg_color
        border_col = self.active_color if (self.is_hovered or self.is_active) else COLOR_CARD_BORDER

        pygame.draw.rect(surface, col, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, border_col, self.rect, 2, border_radius=self.border_radius)

        txt_offset_x = 0
        if self.icon:
            icon_rect = pygame.Rect(self.rect.x + 8, self.rect.centery - 8, 16, 16)
            icon_col = self.active_color if (self.is_hovered or self.is_active) else self.text_color
            draw_vector_icon(surface, self.icon, icon_rect, icon_col)
            txt_offset_x = 24

        if self.text:
            txt_surf = self.font.render(self.text, True, self.text_color)
            if self.icon:
                txt_x = self.rect.x + txt_offset_x
                txt_y = self.rect.centery - txt_surf.get_height() // 2
            else:
                txt_x = self.rect.centerx - txt_surf.get_width() // 2
                txt_y = self.rect.centery - txt_surf.get_height() // 2
            surface.blit(txt_surf, (txt_x, txt_y))


class UISelectionCard:
    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        title: str,
        subtext: str,
        font_title: pygame.font.Font,
        font_sub: pygame.font.Font,
        color_active: Tuple[int, int, int] = COLOR_CYAN,
        icon: Optional[str] = None
    ):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.subtext = subtext
        self.font_title = font_title
        self.font_sub = font_sub
        self.color_active = color_active
        self.icon = icon
        self.is_selected = False
        self.is_hovered = False

    def check_hover(self, pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def draw(self, surface: pygame.Surface):
        bg = (23, 37, 84) if self.is_selected else ((30, 41, 59) if self.is_hovered else COLOR_PANEL_ALT)
        border_col = self.color_active if (self.is_selected or self.is_hovered) else COLOR_CARD_BORDER
        border_width = 2 if self.is_selected else 1

        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, border_col, self.rect, border_width, border_radius=8)

        content_x = self.rect.x + 14
        if self.icon:
            icon_rect = pygame.Rect(self.rect.x + 12, self.rect.y + 12, 22, 22)
            draw_vector_icon(surface, self.icon, icon_rect, self.color_active)
            content_x += 28

        t_surf = self.font_title.render(self.title, True, COLOR_TEXT_MAIN)
        surface.blit(t_surf, (content_x, self.rect.y + 12))

        # Strict text wrapping for card descriptions
        desc_rect = pygame.Rect(self.rect.x + 14, self.rect.y + 40, self.rect.width - 28, self.rect.height - 48)
        render_wrapped_text(surface, self.subtext, self.font_sub, COLOR_TEXT_MUTED, desc_rect, line_spacing=2)


# -----------------------------------------------------------------------------
# Particle and Atmosphere Systems
# -----------------------------------------------------------------------------
class ParticleBurst:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], count: int = 12):
        self.particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.0, 3.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.4, 0.8)
            size = random.uniform(2, 4)
            self.particles.append([x, y, vx, vy, life, size, color])

    def update(self, dt: float) -> bool:
        alive = False
        for p in self.particles:
            if p[4] > 0:
                p[0] += p[2]
                p[1] += p[3]
                p[4] -= dt
                alive = True
        return alive

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            if p[4] > 0:
                alpha = max(0, min(255, int(255 * (p[4] / 0.8))))
                col = (p[6][0], p[6][1], p[6][2], alpha)
                s = pygame.Surface((int(p[5] * 2), int(p[5] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(s, col, (int(p[5]), int(p[5])), int(p[5]))
                surface.blit(s, (int(p[0] - p[5]), int(p[1] - p[5])))


class FootstepTrail:
    def __init__(self, max_length: int = 24):
        self.trail = deque(maxlen=max_length)

    def add_step(self, pos: Tuple[int, int]):
        if not self.trail or self.trail[-1] != pos:
            self.trail.append(pos)

    def draw(self, surface: pygame.Surface):
        if len(self.trail) < 2:
            return
        pts = list(self.trail)
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            alpha = int(140 * ((i + 1) / len(pts)))
            color = (250, 204, 21, alpha)
            s = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            x1 = int(p1[0] * TILE_SIZE + TILE_SIZE / 2)
            y1 = int(p1[1] * TILE_SIZE + TILE_SIZE / 2)
            x2 = int(p2[0] * TILE_SIZE + TILE_SIZE / 2)
            y2 = int(p2[1] * TILE_SIZE + TILE_SIZE / 2)
            pygame.draw.line(s, color, (x1, y1), (x2, y2), 2)
            pygame.draw.circle(s, color, (x2, y2), 2)
            surface.blit(s, (0, 0))


class DynamicAvatar:
    def __init__(self, pos: List[int]):
        self.pos = list(pos)
        self.visual_x = float(pos[0])
        self.visual_y = float(pos[1])
        self.facing = "south"
        self.walk_cycle = 0.0
        self.is_moving = False
        self.bob_phase = 0.0

    def update(self, target_pos: List[int], dt: float):
        self.bob_phase += dt * 4.0
        tx, ty = float(target_pos[0]), float(target_pos[1])
        dx = tx - self.visual_x
        dy = ty - self.visual_y
        dist = math.hypot(dx, dy)

        if dist > 0.05:
            self.is_moving = True
            self.walk_cycle += dt * 10.0
            if abs(dx) > abs(dy):
                self.facing = "east" if dx > 0 else "west"
            else:
                self.facing = "south" if dy > 0 else "north"
            speed = 6.0
            self.visual_x += dx * min(1.0, speed * dt)
            self.visual_y += dy * min(1.0, speed * dt)
        else:
            self.is_moving = False
            self.visual_x = tx
            self.visual_y = ty
            self.pos = list(target_pos)

    def draw(self, surface: pygame.Surface, agent: SurvivalAgent):
        screen_x = self.visual_x * TILE_SIZE + TILE_SIZE / 2
        screen_y = self.visual_y * TILE_SIZE + TILE_SIZE / 2
        bob = math.sin(self.bob_phase) * 1.5 if not self.is_moving else math.sin(self.walk_cycle) * 2.5
        cy = screen_y + bob

        # Directional character rendering
        head_col = (254, 215, 170)
        body_col = (59, 130, 246)
        limbs_col = (30, 58, 138)

        # Shadow
        shadow_surf = pygame.Surface((20, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (0, 0, 20, 10))
        surface.blit(shadow_surf, (screen_x - 10, screen_y + 6))

        # Body
        pygame.draw.rect(surface, body_col, (screen_x - 5, cy - 4, 10, 10), border_radius=2)
        # Head
        pygame.draw.circle(surface, head_col, (int(screen_x), int(cy - 8)), 5)

        # Facing details
        eye_col = (15, 23, 42)
        if self.facing == "south":
            pygame.draw.circle(surface, eye_col, (int(screen_x - 2), int(cy - 8)), 1)
            pygame.draw.circle(surface, eye_col, (int(screen_x + 2), int(cy - 8)), 1)
        elif self.facing == "north":
            # Back of head hair
            pygame.draw.circle(surface, (120, 53, 15), (int(screen_x), int(cy - 9)), 4)
        elif self.facing == "east":
            pygame.draw.circle(surface, eye_col, (int(screen_x + 2), int(cy - 8)), 1)
        elif self.facing == "west":
            pygame.draw.circle(surface, eye_col, (int(screen_x - 2), int(cy - 8)), 1)

        # Backpack indicator if items carried
        items_count = agent.inventory.get("food", 0) + agent.inventory.get("wood", 0)
        if items_count > 0:
            bp_w = min(6, 3 + items_count)
            pygame.draw.rect(surface, (139, 69, 19), (screen_x - bp_w // 2, cy - 2, bp_w, 6), border_radius=1)

        # Injury / Limp bandage
        if agent.injured:
            pygame.draw.rect(surface, COLOR_RED, (screen_x - 3, cy + 3, 6, 2))

        # Cold shiver breath vapor
        if agent.needs["warmth"] < 0.35 and (agent.hour >= 21 or agent.hour <= 5):
            breath_alpha = int(120 + 80 * math.sin(self.bob_phase * 2))
            b_surf = pygame.Surface((12, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(b_surf, (224, 242, 254, breath_alpha), (0, 0, 12, 6))
            surface.blit(b_surf, (screen_x + 3, cy - 12))


class WeatherSystem:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.rain_drops = [[random.uniform(0, width), random.uniform(0, height), random.uniform(8, 14)] for _ in range(120)]
        self.snow_flakes = [[random.uniform(0, width), random.uniform(0, height), random.uniform(0.5, 1.8)] for _ in range(80)]
        self.ash_flakes = [[random.uniform(0, width), random.uniform(0, height), random.uniform(0.8, 2.2)] for _ in range(100)]
        self.lightning_flash = 0.0

    def update(self, event: str, dt: float, ash_level: float = 0.0):
        if event == "storm":
            for d in self.rain_drops:
                d[1] += d[2] * 40 * dt
                d[0] += 5 * dt
                if d[1] > self.height:
                    d[1] = 0
                    d[0] = random.uniform(0, self.width)
            if random.random() < 0.015:
                self.lightning_flash = 0.2
        if self.lightning_flash > 0:
            self.lightning_flash = max(0.0, self.lightning_flash - dt)

        if event == "cold_night":
            for s in self.snow_flakes:
                s[1] += s[2] * 20 * dt
                s[0] += math.sin(s[1] * 0.05) * 12 * dt
                if s[1] > self.height:
                    s[1] = 0
                    s[0] = random.uniform(0, self.width)

        if ash_level > 0.05:
            for a in self.ash_flakes:
                a[1] += a[2] * 15 * dt
                a[0] += math.cos(a[1] * 0.04) * 8 * dt
                if a[1] > self.height:
                    a[1] = 0
                    a[0] = random.uniform(0, self.width)

    def draw(self, surface: pygame.Surface, event: str, ash_level: float = 0.0):
        if event == "storm" and self.lightning_flash > 0:
            flash_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            alpha = int(self.lightning_flash / 0.2 * 180)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, (0, 0))

        if event == "storm":
            for d in self.rain_drops:
                pygame.draw.line(surface, (147, 197, 253, 140), (d[0], d[1]), (d[0] + 1, d[1] + 6), 1)

        elif event == "cold_night":
            for s in self.snow_flakes:
                pygame.draw.circle(surface, (241, 245, 249, 180), (int(s[0]), int(s[1])), 2)

        if ash_level > 0.05:
            for a in self.ash_flakes:
                pygame.draw.circle(surface, (80, 80, 80, int(min(220, 120 + ash_level * 100))), (int(a[0]), int(a[1])), 2)


# -----------------------------------------------------------------------------
# Island Visualizer Application
# -----------------------------------------------------------------------------
class IslandVisualizerApp:
    def __init__(
        self,
        seed: int = 101,
        mind_type: str = "quantum",
        noise_source: str = "stub",
        start_screen: str = "event_choice",
        scenario: str = "volcano"
    ):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Quantum Cognition Simulation")

        # Native display information
        disp_info = pygame.display.Info()
        self.screen_width = disp_info.current_w or 1600
        self.screen_height = disp_info.current_h or 900

        # Choose comfortable windowed resolution
        if self.screen_width >= 1650 and self.screen_height >= 950:
            self.window_w, self.window_h = 1600, 900
        elif self.screen_width >= 1440 and self.screen_height >= 850:
            self.window_w, self.window_h = 1440, 810
        else:
            self.window_w, self.window_h = 1280, 720

        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False

        # Typography
        self.font_hero = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI", 14, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI", 13)
        self.font_small = pygame.font.SysFont("Segoe UI", 11)
        self.font_mono = pygame.font.SysFont("Consolas", 12)

        # Simulation States
        self.app_state = start_screen  # "event_choice", "home", "sim"
        self.scenario = scenario        # "island" or "volcano"
        self.seed = seed
        self.mind_type = mind_type.lower()
        self.noise_source = noise_source
        self.max_steps = DEFAULT_STEPS

        # Initialize Simulation Engine
        self._init_simulation()

        # Visual Systems
        self.avatar = DynamicAvatar(self.world.spawn_pos)
        self.footsteps = FootstepTrail()
        self.weather = WeatherSystem(MAP_SIZE, MAP_SIZE)
        self.particles: List[ParticleBurst] = []
        self.wave_time = 0.0

        # Overlays
        self.show_evacuation_map = True
        self.show_history_overlay = False
        self.show_debrief_modal = False
        self.auto_play = False
        self.step_speed_idx = 1
        self.step_speeds = [0.5, 0.25, 0.1]
        self.auto_timer = 0.0

        # Build Interactive UI Layouts
        self._init_ui_components()

    def _init_simulation(self):
        """Initializes or resets the active simulation engine."""
        self.engine = SimulationEngine(
            seed=self.seed,
            mind_type=self.mind_type,
            noise_source=self.noise_source,
            scenario=self.scenario
        )
        self.world = self.engine.world
        self.agent = self.engine.agent
        self.event_gen = self.engine.event_gen
        self.step_idx = 0
        self.history: List[Dict[str, Any]] = []
        self.current_event = "none"
        self.current_narrative = "Simulation initialized. Standby for first step."
        self.show_debrief_modal = False

    def _init_ui_components(self):
        """Builds all button and selection card geometries."""
        # ---------------------------------------------------------------------
        # 1. Event Choice Screen Components
        # ---------------------------------------------------------------------
        card_w, card_h = 680, 520
        c1_x = 100
        c2_x = 820
        card_y = 200

        self.btn_choice_island = UIButton(
            (c1_x + 40, card_y + 430, card_w - 80, 48),
            "ENTER ISLAND WILDERNESS",
            self.font_title,
            bg_color=(13, 148, 136),
            active_color=COLOR_CYAN,
            icon="tree"
        )
        self.btn_choice_volcano = UIButton(
            (c2_x + 40, card_y + 430, card_w - 80, 48),
            "ENTER VOLCANO EVACUATION",
            self.font_title,
            bg_color=(185, 28, 28),
            active_color=COLOR_ORANGE,
            icon="volcano"
        )

        # ---------------------------------------------------------------------
        # 2. Home / Configuration Screen Components
        # ---------------------------------------------------------------------
        self.btn_home_back_scenario = UIButton(
            (36, 26, 170, 36),
            " < Change Scenario",
            self.font_sub,
            bg_color=COLOR_PANEL_ALT,
            active_color=COLOR_GOLD,
            icon="home"
        )

        # Mind Selector Cards
        self.card_mind_q = UISelectionCard(
            (570, 100, 480, 115),
            "2-Qubit Quantum Cognition (Qiskit 2.x)",
            "Non-commuting unitary rotations, constructive belief interference, and stress decoherence.",
            self.font_title, self.font_body, COLOR_PURPLE, icon="atom"
        )
        self.card_mind_c = UISelectionCard(
            (1070, 100, 480, 115),
            "Classical Rational Baseline (ATUS Priors)",
            "Deterministic utility maximization from empirical American Time Use Survey tables.",
            self.font_title, self.font_body, COLOR_BLUE, icon="network"
        )
        self.card_mind_q.is_selected = (self.mind_type == "quantum")
        self.card_mind_c.is_selected = (self.mind_type == "classical")

        # Preset Buttons
        self.btn_presets = []
        p_x, p_y = 570, 265
        presets = VOLCANO_PRESETS if self.scenario == "volcano" else ISLAND_PRESETS
        for i, pr in enumerate(presets):
            bx = p_x + (i % 2) * 495
            by = p_y + (i // 2) * 58
            btn = UIButton((bx, by, 485, 48), pr["label"], self.font_sub, bg_color=COLOR_PANEL_ALT, active_color=pr["color"])
            self.btn_presets.append((btn, pr))

        # Seed Stepper Controls
        s_y = 410
        self.btn_seed_minus = UIButton((570, s_y, 44, 38), "-", self.font_title)
        self.btn_seed_plus = UIButton((620, s_y, 44, 38), "+", self.font_title)
        self.btn_seed_rand = UIButton((675, s_y, 160, 38), " Random Seed", self.font_sub, icon="dice")

        # Step Horizon Buttons
        h_y = 500
        self.btn_horizons = []
        for i, turns in enumerate([12, 24, 36, 48]):
            bx = 570 + i * 110
            btn = UIButton((bx, h_y, 98, 38), f"{turns} Steps", self.font_sub, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)
            if turns == self.max_steps:
                btn.is_active = True
            self.btn_horizons.append((btn, turns))

        # Hero Launch Button
        self.btn_hero_launch = UIButton(
            (570, 580, 980, 60),
            "INITIATE SIMULATION MISSION",
            self.font_hero,
            bg_color=(13, 148, 136),
            active_color=COLOR_CYAN,
            icon="rocket"
        )

        # ---------------------------------------------------------------------
        # 3. Live Simulation Screen Navigation Controls
        # ---------------------------------------------------------------------
        nav_y = 12
        self.btn_nav_scenario = UIButton((915, nav_y, 90, 32), " Hub", self.font_sub, icon="home")
        self.btn_nav_pause = UIButton((1012, nav_y, 88, 32), " Run", self.font_sub, icon="play")
        self.btn_nav_step = UIButton((1106, nav_y, 80, 32), " Step", self.font_sub, icon="step")
        self.btn_nav_speed = UIButton((1192, nav_y, 76, 32), " 1.0x", self.font_sub, icon="speed")
        self.btn_nav_mind = UIButton((1274, nav_y, 110, 32), " Quantum", self.font_sub, bg_color=COLOR_PURPLE, active_color=COLOR_PURPLE, icon="atom")
        self.btn_nav_evac = UIButton((1390, nav_y, 95, 32), " Evac (E)", self.font_sub, icon="shield")
        self.btn_nav_log = UIButton((1491, nav_y, 50, 32), "", self.font_sub, icon="history")
        self.btn_nav_fs = UIButton((1547, nav_y, 44, 32), "", self.font_sub, icon="fullscreen")

        # ---------------------------------------------------------------------
        # 4. Debrief Modal Buttons
        # ---------------------------------------------------------------------
        dm_w, dm_h = 760, 480
        dm_x = (WINDOW_WIDTH - dm_w) // 2
        dm_y = (WINDOW_HEIGHT - dm_h) // 2
        btn_y = dm_y + dm_h - 70

        self.btn_modal_replay = UIButton((dm_x + 36, btn_y, 150, 44), " Replay Run", self.font_sub, icon="replay")
        self.btn_modal_compare = UIButton((dm_x + 198, btn_y, 195, 44), " Compare Minds", self.font_sub, icon="compare")
        self.btn_modal_scenario = UIButton((dm_x + 405, btn_y, 170, 44), " Change Scenario", self.font_sub, icon="home")
        self.btn_modal_home = UIButton((dm_x + 587, btn_y, 137, 44), " Settings", self.font_sub)

    def toggle_fullscreen(self):
        """Native hardware fullscreen toggle mapping to (0, 0)."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

    def get_virtual_mouse_pos(self) -> Tuple[int, int]:
        """Translates real display mouse coordinates to the 1600x900 virtual canvas."""
        real_x, real_y = pygame.mouse.get_pos()
        sw, sh = self.screen.get_size()
        scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
        scaled_w = int(WINDOW_WIDTH * scale)
        scaled_h = int(WINDOW_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2

        vx = (real_x - offset_x) / scale
        vy = (real_y - offset_y) / scale
        return int(max(0, min(WINDOW_WIDTH, vx))), int(max(0, min(WINDOW_HEIGHT, vy)))

    def step_forward(self):
        """Advances the simulation by one turn (2 hours)."""
        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            self.auto_play = False
            return

        prev_pos = list(self.agent.pos)
        record = self.engine.step()
        if record is None:
            self.show_debrief_modal = True
            self.auto_play = False
            return

        self.step_idx += 1
        event, action = record["event"], record["action"]
        self.current_event = event
        self.current_narrative = record.get("reason", f"Selected action: {action}")

        # Update visuals
        self.avatar.update(self.agent.pos, 0.2)
        self.footsteps.add_step(tuple(self.agent.pos))

        # Action feedback particles
        if prev_pos != self.agent.pos:
            px = self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2
            py = self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2
            col = ACTION_COLORS.get(action, COLOR_CYAN)
            self.particles.append(ParticleBurst(px, py, col, count=14))

        self.history.append({
            "t": record["t"],
            "event": event,
            "action": action,
            "decision": record,
            "state": record["state"]
        })

        if not self.agent.is_alive or self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            self.auto_play = False

    def run(self):
        """Main game loop executing at 60 FPS."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.wave_time += dt

            # Auto-play tick
            if self.auto_play and self.app_state == "sim" and not self.show_debrief_modal:
                self.auto_timer += dt
                speed_thresh = self.step_speeds[self.step_speed_idx]
                if self.auto_timer >= speed_thresh:
                    self.auto_timer = 0.0
                    self.step_forward()

            # Event handling
            v_mouse = self.get_virtual_mouse_pos()
            hover_any = False

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif ev.key == pygame.K_SPACE:
                        if self.app_state == "sim":
                            self.auto_play = not self.auto_play
                    elif ev.key == pygame.K_RIGHT:
                        if self.app_state == "sim":
                            self.step_forward()
                    elif ev.key == pygame.K_q:
                        if self.app_state == "sim":
                            self._toggle_mind()
                    elif ev.key == pygame.K_e:
                        self.show_evacuation_map = not self.show_evacuation_map
                    elif ev.key == pygame.K_TAB:
                        if self.app_state == "sim":
                            self.show_history_overlay = not self.show_history_overlay
                    elif ev.key == pygame.K_ESCAPE:
                        if self.show_history_overlay:
                            self.show_history_overlay = False
                        elif self.show_debrief_modal:
                            self.show_debrief_modal = False
                        elif self.app_state == "sim":
                            self.app_state = "home"
                        elif self.app_state == "home":
                            self.app_state = "event_choice"

                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self._handle_mouse_click(v_mouse)

            # Update visual systems
            if self.app_state == "sim":
                self.avatar.update(self.agent.pos, dt)
                ash_level = getattr(self.world, "ash", 0.0)
                self.weather.update(self.current_event, dt, ash_level=ash_level)
                self.particles = [p for p in self.particles if p.update(dt)]

            # Cursor updates
            if self._check_hover_all(v_mouse):
                set_cursor_hand()
            else:
                set_cursor_arrow()

            # Render canvas & present to screen
            self.draw()
            self.present()

        pygame.quit()

    def _toggle_mind(self):
        """Toggles decision engine live between Quantum and Classical."""
        self.mind_type = "classical" if self.mind_type == "quantum" else "quantum"
        self.engine.mind_type = self.mind_type
        self.engine.decide_fn = contracts.classical_decide if self.mind_type == "classical" else contracts.quantum_decide
        self.btn_nav_mind.text = " Quantum" if self.mind_type == "quantum" else " Classical"
        self.btn_nav_mind.bg_color = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE
        self.btn_nav_mind.active_color = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE

    def _check_hover_all(self, pos: Tuple[int, int]) -> bool:
        if self.app_state == "event_choice":
            return self.btn_choice_island.check_hover(pos) or self.btn_choice_volcano.check_hover(pos)

        elif self.app_state == "home":
            h = self.btn_home_back_scenario.check_hover(pos)
            h |= self.card_mind_q.check_hover(pos) or self.card_mind_c.check_hover(pos)
            for btn, _ in self.btn_presets:
                h |= btn.check_hover(pos)
            h |= self.btn_seed_minus.check_hover(pos) or self.btn_seed_plus.check_hover(pos) or self.btn_seed_rand.check_hover(pos)
            for btn, _ in self.btn_horizons:
                h |= btn.check_hover(pos)
            h |= self.btn_hero_launch.check_hover(pos)
            return h

        elif self.app_state == "sim":
            if self.show_debrief_modal:
                return (
                    self.btn_modal_replay.check_hover(pos) or
                    self.btn_modal_compare.check_hover(pos) or
                    self.btn_modal_scenario.check_hover(pos) or
                    self.btn_modal_home.check_hover(pos)
                )
            navs = [
                self.btn_nav_scenario, self.btn_nav_pause, self.btn_nav_step,
                self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_evac,
                self.btn_nav_log, self.btn_nav_fs
            ]
            return any(b.check_hover(pos) for b in navs)
        return False

    def _handle_mouse_click(self, pos: Tuple[int, int]):
        if self.app_state == "event_choice":
            if self.btn_choice_island.check_hover(pos):
                self.scenario = "island"
                self._update_presets_for_scenario()
                self._init_simulation()
                self.app_state = "home"
            elif self.btn_choice_volcano.check_hover(pos):
                self.scenario = "volcano"
                self._update_presets_for_scenario()
                self._init_simulation()
                self.app_state = "home"

        elif self.app_state == "home":
            if self.btn_home_back_scenario.check_hover(pos):
                self.app_state = "event_choice"
            elif self.card_mind_q.check_hover(pos):
                self.mind_type = "quantum"
                self.card_mind_q.is_selected = True
                self.card_mind_c.is_selected = False
            elif self.card_mind_c.check_hover(pos):
                self.mind_type = "classical"
                self.card_mind_q.is_selected = False
                self.card_mind_c.is_selected = True

            for btn, pr in self.btn_presets:
                if btn.check_hover(pos):
                    self.seed = pr["seed"]
                    self._init_simulation()

            if self.btn_seed_minus.check_hover(pos):
                self.seed = max(1, self.seed - 1)
                self._init_simulation()
            elif self.btn_seed_plus.check_hover(pos):
                self.seed += 1
                self._init_simulation()
            elif self.btn_seed_rand.check_hover(pos):
                self.seed = random.randint(10, 999)
                self._init_simulation()

            for btn, turns in self.btn_horizons:
                if btn.check_hover(pos):
                    self.max_steps = turns
                    for b, _ in self.btn_horizons:
                        b.is_active = False
                    btn.is_active = True

            if self.btn_hero_launch.check_hover(pos):
                self._init_simulation()
                self.app_state = "sim"

        elif self.app_state == "sim":
            self._handle_sim_click(pos)

    def _update_presets_for_scenario(self):
        """Updates preset buttons according to the active scenario."""
        self.btn_presets = []
        p_x, p_y = 570, 265
        presets = VOLCANO_PRESETS if self.scenario == "volcano" else ISLAND_PRESETS
        for i, pr in enumerate(presets):
            bx = p_x + (i % 2) * 495
            by = p_y + (i // 2) * 58
            btn = UIButton((bx, by, 485, 48), pr["label"], self.font_sub, bg_color=COLOR_PANEL_ALT, active_color=pr["color"])
            self.btn_presets.append((btn, pr))

    def _handle_sim_click(self, pos: Tuple[int, int]):
        if self.show_debrief_modal:
            if self.btn_modal_replay.check_hover(pos):
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_compare.check_hover(pos):
                self._toggle_mind()
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_scenario.check_hover(pos):
                self.app_state = "event_choice"
            elif self.btn_modal_home.check_hover(pos):
                self.app_state = "home"
            return

        if self.show_history_overlay:
            # Click anywhere outside or escape
            self.show_history_overlay = False
            return

        if self.btn_nav_scenario.check_hover(pos):
            self.app_state = "home"
        elif self.btn_nav_pause.check_hover(pos):
            self.auto_play = not self.auto_play
        elif self.btn_nav_step.check_hover(pos):
            self.step_forward()
        elif self.btn_nav_speed.check_hover(pos):
            self.step_speed_idx = (self.step_speed_idx + 1) % len(self.step_speeds)
            sp_labels = [" 0.5x", " 1.0x", " 2.0x"]
            self.btn_nav_speed.text = sp_labels[self.step_speed_idx]
        elif self.btn_nav_mind.check_hover(pos):
            self._toggle_mind()
        elif self.btn_nav_evac.check_hover(pos):
            self.show_evacuation_map = not self.show_evacuation_map
        elif self.btn_nav_log.check_hover(pos):
            self.show_history_overlay = not self.show_history_overlay
        elif self.btn_nav_fs.check_hover(pos):
            self.toggle_fullscreen()

    # -------------------------------------------------------------------------
    # Screen Rendering Pipelines
    # -------------------------------------------------------------------------
    def draw(self):
        self.canvas.fill(COLOR_BG)

        if self.app_state == "event_choice":
            self.draw_event_choice_screen()
        elif self.app_state == "home":
            self.draw_home_screen()
        elif self.app_state == "sim":
            self.draw_sim_screen()
            if self.show_history_overlay:
                self.draw_history_overlay()
            if self.show_debrief_modal:
                self.draw_debrief_modal()

    def present(self):
        """Presents virtual 1600x900 canvas to screen with letterboxing."""
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

    # -------------------------------------------------------------------------
    # 1. Event Choice Screen
    # -------------------------------------------------------------------------
    def draw_event_choice_screen(self):
        # Header Banner
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 140))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (0, 140), (WINDOW_WIDTH, 140), 2)

        # App Logo & Title
        draw_vector_icon(self.canvas, "atom", pygame.Rect(48, 36, 44, 44), COLOR_CYAN)
        title_surf = self.font_hero.render("QUANTUM COGNITION SIMULATION", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (106, 34))

        sub_surf = self.font_sub.render(
            "Cognitive Architecture Lab & Multi-Scenario Survival Simulator  |  Antigravity 2.0  •  Qiskit 2.x",
            True, COLOR_TEXT_MUTED
        )
        self.canvas.blit(sub_surf, (106, 72))

        # Prompt Banner
        prompt_txt = self.font_hero.render("CHOOSE SIMULATION SCENARIO", True, COLOR_GOLD)
        self.canvas.blit(prompt_txt, ((WINDOW_WIDTH - prompt_txt.get_width()) // 2, 155))

        # Scenario Cards
        self._draw_scenario_card(
            100, 205, 680, 560,
            title="ISLAND WILDERNESS SURVIVAL",
            tagline="Procedural Archipelago  •  Resource Foraging  •  Wildlife & Storms",
            desc=(
                "Stranded across an uncharted procedural island. Balance caloric hunger, dehydration, "
                "hypothermia, fatigue, and sanity against stochastic storms, territorial wild boars, and "
                "injuries using quantum belief interference. Craft tools, erect shelters, and explore land."
            ),
            features=[
                "Procedural 40x40 Map generated from seed",
                "Organic coastline harmonics, pine forests & alpine snowcaps",
                "Markov weather, nighttime frost, and predator encounters",
                "Full resource economy: foraging, timber crafting & shelters"
            ],
            accent_col=COLOR_CYAN,
            icon_name="tree",
            button=self.btn_choice_island
        )

        self._draw_scenario_card(
            820, 205, 680, 560,
            title="VOLCANO ERUPTION EVACUATION",
            tagline="Cataclysmic Escalation  •  Pyroclastic Surges  •  Emergency Routing",
            desc=(
                "Evacuate a calibrated 40x40 volcanic topography under accelerating seismic unrest. "
                "Decipher precursory tremors and gas plumes, navigate around molten lava flows, survive toxic "
                "ash fallout, and execute BFS shortest-path routes to reach designated safety assembly points."
            ),
            features=[
                "Calibrated 40x40 Volcanic Topography with central caldera",
                "Seeded hidden unrest, explosive eruptions, or false alarms",
                "Fast pyroclastic density currents (PDCs), lava & lahars",
                "Dynamic evacuation zoning (Safe / Caution / Danger) & BFS route"
            ],
            accent_col=COLOR_ORANGE,
            icon_name="volcano",
            button=self.btn_choice_volcano
        )

        # Footer Help
        hint = self.font_small.render("Press [1] Island Wilderness  |  [2] Volcano Evacuation  |  [F11] Fullscreen Toggle", True, COLOR_TEXT_HINT)
        self.canvas.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, WINDOW_HEIGHT - 36))

    def _draw_scenario_card(
        self,
        x: int, y: int, w: int, h: int,
        title: str,
        tagline: str,
        desc: str,
        features: List[str],
        accent_col: Tuple[int, int, int],
        icon_name: str,
        button: UIButton
    ):
        card_rect = pygame.Rect(x, y, w, h)
        is_hovered = card_rect.collidepoint(self.get_virtual_mouse_pos())
        bg_col = (20, 30, 50) if is_hovered else COLOR_PANEL_BG
        border_col = accent_col if is_hovered else COLOR_CARD_BORDER

        pygame.draw.rect(self.canvas, bg_col, card_rect, border_radius=12)
        pygame.draw.rect(self.canvas, border_col, card_rect, 2 if is_hovered else 1, border_radius=12)

        # Header Icon + Title
        icon_rect = pygame.Rect(x + 28, y + 26, 36, 36)
        draw_vector_icon(self.canvas, icon_name, icon_rect, accent_col)

        t_surf = self.font_title.render(title, True, COLOR_TEXT_MAIN)
        self.canvas.blit(t_surf, (x + 76, y + 24))

        tag_surf = self.font_small.render(tagline, True, accent_col)
        self.canvas.blit(tag_surf, (x + 76, y + 48))

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (x + 28, y + 78), (x + w - 28, y + 78), 1)

        # Description
        desc_rect = pygame.Rect(x + 28, y + 92, w - 56, 110)
        render_wrapped_text(self.canvas, desc, self.font_body, COLOR_TEXT_MUTED, desc_rect, line_spacing=4)

        # Feature Highlights
        feat_y = y + 215
        f_lbl = self.font_sub.render("SIMULATION ATTRIBUTES:", True, COLOR_GOLD)
        self.canvas.blit(f_lbl, (x + 28, feat_y))
        feat_y += 28

        for f in features:
            pygame.draw.circle(self.canvas, accent_col, (x + 36, feat_y + 8), 3)
            f_surf = self.font_body.render(f, True, COLOR_TEXT_MAIN)
            self.canvas.blit(f_surf, (x + 48, feat_y))
            feat_y += 26

        # Interactive Button
        button.rect.x = x + 36
        button.rect.y = y + h - 68
        button.rect.width = w - 72
        button.draw(self.canvas)

    # -------------------------------------------------------------------------
    # 2. Home / Mission Configuration Screen
    # -------------------------------------------------------------------------
    def draw_home_screen(self):
        # Header Banner
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 80))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (0, 80), (WINDOW_WIDTH, 80), 1)

        self.btn_home_back_scenario.draw(self.canvas)

        scen_title = "VOLCANO ERUPTION EVACUATION" if self.scenario == "volcano" else "ISLAND WILDERNESS SURVIVAL"
        scen_col = COLOR_ORANGE if self.scenario == "volcano" else COLOR_CYAN

        h_surf = self.font_hero.render("QUANTUM COGNITION SIMULATION", True, COLOR_TEXT_MAIN)
        self.canvas.blit(h_surf, (220, 24))

        badge_x = 220 + h_surf.get_width() + 18
        self.draw_badge(badge_x, 26, f"SCENARIO: {scen_title}", scen_col)

        # Left Panel: Topographic Reconnaissance (Mini-Map)
        self.draw_recon_panel()

        # Right Panel: Mission Parameters
        self.draw_params_panel()

    def draw_recon_panel(self):
        panel_rect = pygame.Rect(40, 100, 490, 750)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, panel_rect, border_radius=10)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, panel_rect, 1, border_radius=10)

        r_title = self.font_title.render("TOPOGRAPHIC RECONNAISSANCE", True, COLOR_GOLD)
        self.canvas.blit(r_title, (60, 120))

        sub_info = "Fixed 40x40 Evacuation Topography" if self.scenario == "volcano" else f"Procedural Island (Seed #{self.seed})"
        self.canvas.blit(self.font_sub.render(sub_info, True, COLOR_TEXT_MUTED), (60, 146))

        # Mini-map canvas 360x360
        mini_size = 360
        mini_surf = pygame.Surface((mini_size, mini_size))
        mini_tile = mini_size / GRID_DIM

        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                t = self.world.get_tile(x, y)
                col = TILE_COLORS.get(t, (14, 116, 144))
                pygame.draw.rect(mini_surf, col, (x * mini_tile, y * mini_tile, math.ceil(mini_tile), math.ceil(mini_tile)))

        # Mini-map overlays for volcano
        if self.scenario == "volcano":
            # Caldera
            vx, vy = self.world.vent
            pygame.draw.circle(mini_surf, COLOR_RED, (int(vx * mini_tile), int(vy * mini_tile)), 6)
            pygame.draw.circle(mini_surf, COLOR_YELLOW, (int(vx * mini_tile), int(vy * mini_tile)), 3)
            # Assembly point
            for ax, ay in self.world.assembly_points:
                pygame.draw.circle(mini_surf, COLOR_GREEN, (int(ax * mini_tile), int(ay * mini_tile)), 5)

        # Spawn point
        sx, sy = self.world.spawn_pos
        pygame.draw.circle(mini_surf, COLOR_GOLD, (int(sx * mini_tile), int(sy * mini_tile)), 5)

        self.canvas.blit(mini_surf, (105, 185))
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, (105, 185, mini_size, mini_size), 2)

        # Terrain Statistics
        stats_y = 570
        land_tiles = sum(1 for row in self.world.tiles for tile in row if tile in (1, 2, 3, 4))
        water_tiles = sum(1 for row in self.world.tiles for tile in row if tile == 0)
        forest_tiles = sum(1 for row in self.world.tiles for tile in row if tile == 2)
        fresh_sources = len(self.world.freshwater_tiles)

        stats = [
            ("Grid Resolution:", "40 x 40 (1,600 Tiles)", COLOR_TEXT_MAIN),
            ("Land Coverage:", f"{land_tiles} Tiles ({int(land_tiles/1600*100)}%)", COLOR_CYAN),
            ("Timber & Forage:", f"{forest_tiles} Forest Canopies", COLOR_GREEN),
            ("Freshwater Sources:", f"{fresh_sources} Springs / Streams", COLOR_YELLOW),
            ("Hazard Scale:", "250m / Tile • 2h / Turn", COLOR_ORANGE)
        ]

        for k, v, col in stats:
            self.canvas.blit(self.font_sub.render(k, True, COLOR_TEXT_MUTED), (65, stats_y))
            self.canvas.blit(self.font_sub.render(v, True, col), (275, stats_y))
            stats_y += 30

    def draw_params_panel(self):
        # 1. Cognitive Decision Engine
        lbl1 = self.font_title.render("1. SELECT COGNITIVE DECISION ENGINE", True, COLOR_GOLD)
        self.canvas.blit(lbl1, (570, 70))
        self.card_mind_q.draw(self.canvas)
        self.card_mind_c.draw(self.canvas)

        # 2. Scenario Presets & Event Seed
        lbl2 = self.font_title.render("2. MISSION PRESETS & EVENT SEED", True, COLOR_GOLD)
        self.canvas.blit(lbl2, (570, 235))

        for btn, pr in self.btn_presets:
            btn.draw(self.canvas)

        # Stepper Controls
        s_y = 410
        self.btn_seed_minus.draw(self.canvas)
        self.btn_seed_plus.draw(self.canvas)
        self.btn_seed_rand.draw(self.canvas)

        seed_label = self.font_title.render(f"ACTIVE SEED:  #{self.seed:04d}", True, COLOR_GOLD)
        self.canvas.blit(seed_label, (860, s_y + 8))

        # 3. Horizon Selector
        lbl3 = self.font_title.render("3. SIMULATION HORIZON (TIME-STEPS)", True, COLOR_GOLD)
        self.canvas.blit(lbl3, (570, 470))
        for btn, turns in self.btn_horizons:
            btn.is_active = (turns == self.max_steps)
            btn.draw(self.canvas)

        # 4. Hero Button
        self.btn_hero_launch.draw(self.canvas)

    # -------------------------------------------------------------------------
    # 3. Live 2D Simulation Viewport & Telemetry HUD
    # -------------------------------------------------------------------------
    def draw_sim_screen(self):
        # 900x900 Map Viewport on the left
        self.draw_viewport()

        # 700x900 Telemetry Dashboard on the right
        self.draw_telemetry_hud()

    def draw_viewport(self):
        # Base Terrain
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                t = self.world.get_tile(x, y)
                rx = x * TILE_SIZE
                ry = y * TILE_SIZE

                if t == 0:
                    # Ocean waves
                    pygame.draw.rect(self.canvas, (14, 116, 144), (rx, ry, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))
                    wave_off = math.sin(self.wave_time * 2.0 + x * 0.5 + y * 0.3) * 2.0
                    pygame.draw.line(self.canvas, (6, 182, 212, 110), (rx + 2, ry + 10 + wave_off), (rx + TILE_SIZE - 2, ry + 10 + wave_off), 1)

                elif t == 1:
                    # Plains
                    pygame.draw.rect(self.canvas, (202, 138, 4), (rx, ry, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))

                elif t == 2:
                    # Forest with swaying pines
                    pygame.draw.rect(self.canvas, (22, 101, 52), (rx, ry, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))
                    sway = math.sin(self.wave_time * 3.0 + x) * 1.5
                    tree_pts = [(rx + TILE_SIZE / 2 + sway, ry + 3), (rx + 4, ry + TILE_SIZE - 2), (rx + TILE_SIZE - 4, ry + TILE_SIZE - 2)]
                    pygame.draw.polygon(self.canvas, (34, 197, 94), tree_pts)

                elif t == 3:
                    # Mountain crag with snowcap
                    pygame.draw.rect(self.canvas, (51, 65, 85), (rx, ry, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))
                    crag_pts = [(rx + TILE_SIZE / 2, ry + 2), (rx + 3, ry + TILE_SIZE - 2), (rx + TILE_SIZE - 3, ry + TILE_SIZE - 2)]
                    pygame.draw.polygon(self.canvas, (100, 116, 139), crag_pts)
                    # Snowcap
                    snow_pts = [(rx + TILE_SIZE / 2, ry + 2), (rx + TILE_SIZE / 2 - 4, ry + 8), (rx + TILE_SIZE / 2 + 4, ry + 8)]
                    pygame.draw.polygon(self.canvas, (241, 245, 249), snow_pts)

                elif t == 4:
                    # Shelter
                    pygame.draw.rect(self.canvas, (168, 85, 247), (rx, ry, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))
                    pygame.draw.polygon(self.canvas, COLOR_GOLD, [(rx + TILE_SIZE / 2, ry + 3), (rx + 3, ry + TILE_SIZE - 3), (rx + TILE_SIZE - 3, ry + TILE_SIZE - 3)])

        # Volcano Caldera & Hazards (if volcano scenario)
        if self.scenario == "volcano":
            vx, vy = self.world.vent
            vrx = vx * TILE_SIZE + TILE_SIZE / 2
            vry = vy * TILE_SIZE + TILE_SIZE / 2
            pygame.draw.circle(self.canvas, (185, 28, 28), (int(vrx), int(vry)), 14)
            pygame.draw.circle(self.canvas, COLOR_ORANGE, (int(vrx), int(vry)), 8)
            pygame.draw.circle(self.canvas, COLOR_YELLOW, (int(vrx), int(vry)), 4)

            # Evacuation Map Overlay
            if self.show_evacuation_map:
                overlay = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                zone_colors = ((34, 197, 94, 30), (234, 179, 8, 45), (239, 68, 68, 65))
                for y, row in enumerate(self.world.zones):
                    for x, zone in enumerate(row):
                        if self.world.get_tile(x, y):
                            pygame.draw.rect(overlay, zone_colors[zone], (x * TILE_SIZE, y * TILE_SIZE, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))

                # Evacuation Route
                pts = [(x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2) for x, y in self.world.route_from_spawn]
                if len(pts) > 1:
                    pygame.draw.lines(overlay, (56, 189, 248, 210), False, pts, 2)

                # Assembly Points
                for ax, ay in self.world.assembly_points:
                    pygame.draw.circle(overlay, (34, 197, 94), (int(ax * TILE_SIZE + TILE_SIZE / 2), int(ay * TILE_SIZE + TILE_SIZE / 2)), 8)
                    pygame.draw.circle(overlay, (241, 245, 249), (int(ax * TILE_SIZE + TILE_SIZE / 2), int(ay * TILE_SIZE + TILE_SIZE / 2)), 4)
                self.canvas.blit(overlay, (0, 0))

            # Active Hazards: Lava, PDC, Lahar
            hazard_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            for x, y in getattr(self.world, "lava", set()):
                # Molten lava pulse
                pulse = math.sin(self.wave_time * 4.0 + x + y) * 25
                lava_col = (255, max(0, min(255, int(90 + pulse))), 0, 180)
                pygame.draw.rect(hazard_surf, lava_col, (x * TILE_SIZE, y * TILE_SIZE, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))

            for x, y in getattr(self.world, "pdc", set()):
                # Pyroclastic flow surge
                pygame.draw.rect(hazard_surf, (100, 90, 90, 140), (x * TILE_SIZE, y * TILE_SIZE, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))

            for x, y in getattr(self.world, "lahar", set()):
                # Lahar mud flow
                pygame.draw.rect(hazard_surf, (110, 65, 25, 150), (x * TILE_SIZE, y * TILE_SIZE, math.ceil(TILE_SIZE), math.ceil(TILE_SIZE)))

            # Ash Fallout Tint
            ash_val = getattr(self.world, "ash", 0.0)
            if ash_val > 0.02:
                ash_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                ash_surf.fill((140, 140, 140, int(min(120, ash_val * 90))))
                hazard_surf.blit(ash_surf, (0, 0))

            self.canvas.blit(hazard_surf, (0, 0))

        # Footsteps & Character
        self.footsteps.draw(self.canvas)
        self.avatar.draw(self.canvas, self.agent)

        # Weather & Particles
        self.weather.draw(self.canvas, self.current_event, ash_level=getattr(self.world, "ash", 0.0))
        for p in self.particles:
            p.draw(self.canvas)

        # Day/Night Tint
        hour = self.agent.hour
        if hour >= 21 or hour <= 5:
            night_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            night_surf.fill((10, 15, 35, 120))
            self.canvas.blit(night_surf, (0, 0))

        # Viewport Separation Line
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 2)

    def draw_telemetry_hud(self):
        px = MAP_SIZE + 24
        pw = WINDOW_WIDTH - MAP_SIZE - 48

        # Navigation Controls Bar
        self.btn_nav_scenario.draw(self.canvas)
        self.btn_nav_pause.text = " Pause" if self.auto_play else " Run"
        self.btn_nav_pause.icon = "pause" if self.auto_play else "play"
        self.btn_nav_pause.draw(self.canvas)
        self.btn_nav_step.draw(self.canvas)
        self.btn_nav_speed.draw(self.canvas)
        self.btn_nav_mind.draw(self.canvas)
        self.btn_nav_evac.draw(self.canvas)
        self.btn_nav_log.draw(self.canvas)
        self.btn_nav_fs.draw(self.canvas)

        y = 60
        # Scenario & Time Header
        scen_title = "VOLCANO EVACUATION" if self.scenario == "volcano" else "ISLAND WILDERNESS"
        scen_col = COLOR_ORANGE if self.scenario == "volcano" else COLOR_CYAN

        h_surf = self.font_title.render("QUANTUM COGNITION SIMULATION", True, COLOR_TEXT_MAIN)
        self.canvas.blit(h_surf, (px, y))
        self.draw_badge(px + h_surf.get_width() + 14, y - 2, f"SCENARIO: {scen_title}", scen_col)

        y += 34
        time_str = f"STEP: #{self.step_idx:02d}/{self.max_steps}  |  DAY {self.agent.day:02d}  •  {self.agent.hour:02d}:00 HRS  |  SEED #{self.seed}"
        self.canvas.blit(self.font_sub.render(time_str, True, COLOR_GOLD), (px, y))

        y += 28
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (px, y), (px + pw, y), 1)

        y += 14
        # Event & Volcanic Phase Banner
        banner_rect = pygame.Rect(px, y, pw, 46)
        ev_col = COLOR_YELLOW if self.current_event != "none" else COLOR_CARD_BORDER
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, banner_rect, border_radius=6)
        pygame.draw.rect(self.canvas, ev_col, banner_rect, 1, border_radius=6)

        ev_upper = self.current_event.upper()
        self.canvas.blit(self.font_title.render(f"EVENT:  {ev_upper}", True, ev_col), (px + 14, y + 12))

        if self.scenario == "volcano":
            volcano_phase = self.engine.volcano.phases[max(0, self.step_idx - 1)] if hasattr(self.engine, "volcano") else "UNREST"
            phase_col = COLOR_RED if volcano_phase == "erupting" else (COLOR_ORANGE if volcano_phase == "escalating" else COLOR_GREEN)
            self.draw_badge(px + pw - 180, y + 9, f"PHASE: {volcano_phase.upper()}", phase_col)

        y += 58
        # Survivor Needs Progress Bars (6 vitals)
        n_box = pygame.Rect(px, y, pw, 180)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, n_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, n_box, 1, border_radius=8)

        self.canvas.blit(self.font_sub.render("SURVIVOR PHYSIOLOGICAL VITALS", True, COLOR_GOLD), (px + 14, y + 10))

        bar_y = y + 36
        needs = self.agent.needs
        self.draw_progress_bar(px + 14, bar_y, pw - 28, 16, "Hunger", needs["hunger"], COLOR_ORANGE)
        self.draw_progress_bar(px + 14, bar_y + 24, pw - 28, 16, "Thirst", needs["thirst"], COLOR_CYAN)
        self.draw_progress_bar(px + 14, bar_y + 48, pw - 28, 16, "Warmth", needs["warmth"], COLOR_RED)
        self.draw_progress_bar(px + 14, bar_y + 72, pw - 28, 16, "Energy", needs["energy"], COLOR_YELLOW)
        self.draw_progress_bar(px + 14, bar_y + 96, pw - 28, 16, "Safety", needs["safety"], COLOR_GREEN)
        self.draw_progress_bar(px + 14, bar_y + 120, pw - 28, 16, "Morale", needs["morale"], COLOR_PURPLE)

        y += 194
        # Stress & Decoherence Gauge + 3D Bloch Sphere
        m_box = pygame.Rect(px, y, pw, 120)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, m_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, m_box, 1, border_radius=8)

        self.canvas.blit(self.font_sub.render("QUANTUM COGNITIVE STATE & DECOHERENCE", True, COLOR_GOLD), (px + 14, y + 10))

        # Stress & Decoherence text
        stress_val = self.agent.stress
        decohere_val = max(0.0, stress_val - 0.4) / 0.5
        self.draw_progress_bar(px + 14, y + 40, pw - 150, 16, "Stress", stress_val, COLOR_RED)
        self.draw_progress_bar(px + 14, y + 68, pw - 150, 16, "Decoherence", min(1.0, decohere_val), COLOR_PURPLE)

        # 3D Bloch Sphere
        bx = px + pw - 65
        by = y + 60
        self.draw_bloch_sphere(bx, by, radius=32, theta=stress_val * math.pi, phi=self.wave_time)

        y += 134
        # Action Probabilities Distribution
        p_box = pygame.Rect(px, y, pw, 230)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, p_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, p_box, 1, border_radius=8)

        mind_label = "2-QUBIT QUANTUM COGNITION" if self.mind_type == "quantum" else "CLASSICAL ATUS RATIONALITY"
        self.canvas.blit(self.font_sub.render(f"ACTION BELIEF PROBABILITIES ({mind_label})", True, COLOR_GOLD), (px + 14, y + 10))

        # Current Decision Probabilities
        probs = self.history[-1]["decision"].get("probs", {}) if self.history else {}
        top_action = self.history[-1]["action"] if self.history else "none"

        act_y = y + 36
        for action in contracts.ACTIONS:
            p_val = probs.get(action, 0.0)
            col = ACTION_COLORS.get(action, COLOR_TEXT_MAIN)
            is_chosen = (action == top_action)
            lbl = f"> {action.upper()}" if is_chosen else f"  {action}"
            self.draw_progress_bar(px + 14, act_y, pw - 28, 14, lbl[:14], p_val, col)
            act_y += 24

        y += 244
        # Cognitive Rationale Box
        r_box = pygame.Rect(px, y, pw, 100)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, r_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, r_box, 1, border_radius=8)

        self.canvas.blit(self.font_sub.render("EXPLAINABILITY & DECISION RATIONALE:", True, COLOR_GOLD), (px + 14, y + 10))
        quote_rect = pygame.Rect(px + 14, y + 32, pw - 28, 60)
        render_wrapped_text(self.canvas, f'"{self.current_narrative}"', self.font_body, COLOR_TEXT_MAIN, quote_rect, line_spacing=3)

    def draw_bloch_sphere(self, cx: int, cy: int, radius: int, theta: float, phi: float):
        """Renders 3D Bloch sphere vector projection on Pygame canvas."""
        pygame.draw.circle(self.canvas, (30, 41, 59), (cx, cy), radius)
        pygame.draw.circle(self.canvas, COLOR_CARD_BORDER, (cx, cy), radius, 1)

        # Axes
        pygame.draw.line(self.canvas, (71, 85, 105), (cx, cy - radius), (cx, cy + radius), 1)
        pygame.draw.line(self.canvas, (71, 85, 105), (cx - radius, cy), (cx + radius, cy), 1)

        # State vector on sphere
        vx = cx + radius * math.sin(theta) * math.cos(phi)
        vy = cy - radius * math.cos(theta)
        pygame.draw.line(self.canvas, COLOR_CYAN, (cx, cy), (int(vx), int(vy)), 2)
        pygame.draw.circle(self.canvas, COLOR_GOLD, (int(vx), int(vy)), 3)

    # -------------------------------------------------------------------------
    # Modals & Overlays
    # -------------------------------------------------------------------------
    def draw_debrief_modal(self):
        # Translucent backdrop
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((5, 8, 15, 200))
        self.canvas.blit(dim, (0, 0))

        mw, mh = 760, 480
        mx = (WINDOW_WIDTH - mw) // 2
        my = (WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)

        survived = self.agent.is_alive
        border_col = COLOR_GOLD if survived else COLOR_RED
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, m_rect, border_radius=12)
        pygame.draw.rect(self.canvas, border_col, m_rect, 2, border_radius=12)

        # Banner Title
        title_txt = "MISSION ACCOMPLISHED: SURVIVAL MASTERED!" if survived else f"MISSION OVER: SURVIVOR PERISHED ({str(self.agent.cause_of_death).upper()})"
        t_surf = self.font_hero.render(title_txt, True, border_col)
        self.canvas.blit(t_surf, (mx + (mw - t_surf.get_width()) // 2, my + 28))

        sub_txt = f"Endured {self.step_idx}/{self.max_steps} Steps ({self.step_idx * 2} Game Hours)  |  Seed #{self.seed}"
        s_surf = self.font_sub.render(sub_txt, True, COLOR_TEXT_MUTED)
        self.canvas.blit(s_surf, (mx + (mw - s_surf.get_width()) // 2, my + 68))

        # Metrics Breakdown Box
        box_rect = pygame.Rect(mx + 36, my + 105, mw - 72, 260)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box_rect, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box_rect, 1, border_radius=8)

        mind_desc = "2-Qubit Quantum Cognition (Non-commuting Unitary Rotations)" if self.mind_type == "quantum" else "Classical Rational Utility (ATUS Empirical Priors)"
        metrics = [
            ("Decision Mind Engine:", mind_desc, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE),
            ("Scenario Environment:", f"{'Volcano Evacuation' if self.scenario == 'volcano' else 'Island Wilderness'} (Seed #{self.seed})", COLOR_YELLOW),
            ("Final Stress & Noise:", f"{int(self.agent.stress*100)}% Stress  |  Decoherence: {int(max(0, self.agent.stress - 0.4)/0.5 * 100)}%", COLOR_CYAN),
            ("Physiological State:", f"Hunger: {int(self.agent.needs['hunger']*100)}% | Thirst: {int(self.agent.needs['thirst']*100)}% | Warmth: {int(self.agent.needs['warmth']*100)}%", COLOR_TEXT_MAIN),
            ("Resource Harvest:", f"Gathered {self.agent.inventory.get('wood', 0)} Timber | Consumed Rations | Crafted Tools: {self.agent.inventory.get('tools', 0)}", COLOR_TEXT_MUTED)
        ]

        row_y = my + 120
        for label, val, col in metrics:
            self.canvas.blit(self.font_sub.render(label, True, COLOR_TEXT_MUTED), (mx + 54, row_y))
            self.canvas.blit(self.font_sub.render(val, True, col), (mx + 260, row_y))
            row_y += 34

        # Action Buttons
        self.btn_modal_replay.draw(self.canvas)
        self.btn_modal_compare.draw(self.canvas)
        self.btn_modal_scenario.draw(self.canvas)
        self.btn_modal_home.draw(self.canvas)

    def draw_history_overlay(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((5, 8, 15, 210))
        self.canvas.blit(dim, (0, 0))

        hw, hh = 1200, 700
        hx = (WINDOW_WIDTH - hw) // 2
        hy = (WINDOW_HEIGHT - hh) // 2
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, (hx, hy, hw, hh), border_radius=10)
        pygame.draw.rect(self.canvas, COLOR_CYAN, (hx, hy, hw, hh), 2, border_radius=10)

        t_surf = self.font_title.render("ACTION & COGNITIVE DECISION HISTORY LOG", True, COLOR_GOLD)
        self.canvas.blit(t_surf, (hx + 30, hy + 24))

        # Header Columns
        col_y = hy + 64
        self.canvas.blit(self.font_sub.render("Step", True, COLOR_TEXT_MUTED), (hx + 30, col_y))
        self.canvas.blit(self.font_sub.render("Event Hazard", True, COLOR_TEXT_MUTED), (hx + 100, col_y))
        self.canvas.blit(self.font_sub.render("Chosen Action", True, COLOR_TEXT_MUTED), (hx + 240, col_y))
        self.canvas.blit(self.font_sub.render("Top Prob", True, COLOR_TEXT_MUTED), (hx + 380, col_y))
        self.canvas.blit(self.font_sub.render("Cognitive Reasoning & Explainability", True, COLOR_TEXT_MUTED), (hx + 480, col_y))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (hx + 30, col_y + 26), (hx + hw - 30, col_y + 26), 1)

        row_y = col_y + 36
        visible_records = self.history[-16:]
        for rec in visible_records:
            t_num = f"#{rec['t']:02d}"
            ev = rec["event"].upper()
            act = rec["action"].upper()
            probs = rec["decision"].get("probs", {})
            top_p = max(probs.values()) if probs else 0.0
            p_str = f"{top_p * 100:4.1f}%"
            reason = rec["decision"].get("reason", "")[:55] + "..."

            act_col = ACTION_COLORS.get(rec["action"], COLOR_TEXT_MAIN)
            self.canvas.blit(self.font_mono.render(t_num, True, COLOR_CYAN), (hx + 30, row_y))
            self.canvas.blit(self.font_mono.render(ev[:12], True, COLOR_YELLOW), (hx + 100, row_y))
            self.canvas.blit(self.font_mono.render(act[:12], True, act_col), (hx + 240, row_y))
            self.canvas.blit(self.font_mono.render(p_str, True, COLOR_TEXT_MUTED), (hx + 380, row_y))
            self.canvas.blit(self.font_mono.render(reason, True, COLOR_TEXT_MAIN), (hx + 480, row_y))
            row_y += 32

        tip = self.font_small.render("Press [TAB] or [ESC] to return to simulation view", True, COLOR_TEXT_HINT)
        self.canvas.blit(tip, (hx + 30, hy + hh - 36))

    # -------------------------------------------------------------------------
    # Utility Helpers
    # -------------------------------------------------------------------------
    def draw_badge(self, x: int, y: int, text: str, color: Tuple[int, int, int]):
        txt_surf = self.font_sub.render(text, True, color)
        bg_rect = pygame.Rect(x, y, txt_surf.get_width() + 16, txt_surf.get_height() + 8)
        badge_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        badge_surf.fill((color[0], color[1], color[2], 35))
        self.canvas.blit(badge_surf, (x, y))
        pygame.draw.rect(self.canvas, color, bg_rect, 1, border_radius=5)
        self.canvas.blit(txt_surf, (x + 8, y + 4))

    def draw_progress_bar(self, x: int, y: int, w: int, h: int, label: str, value: float, color: Tuple[int, int, int]):
        lbl_surf = self.font_mono.render(f"{label:12s}", True, COLOR_TEXT_MAIN)
        self.canvas.blit(lbl_surf, (x, y))

        bar_x = x + 105
        bar_w = w - 160
        track_rect = pygame.Rect(bar_x, y + 2, bar_w, h - 4)
        pygame.draw.rect(self.canvas, (15, 23, 42), track_rect, border_radius=3)

        fill_w = max(0, min(bar_w, int(bar_w * value)))
        if fill_w > 0:
            pygame.draw.rect(self.canvas, color, (bar_x, y + 2, fill_w, h - 4), border_radius=3)

        val_surf = self.font_mono.render(f"{int(value * 100):3d}%", True, COLOR_TEXT_MUTED)
        self.canvas.blit(val_surf, (bar_x + bar_w + 10, y))


def launch_gui(seed: int = 101, mind: str = "quantum", noise: str = "stub", start_screen: str = "event_choice"):
    """Launches the complete Pygame Quantum Cognition Simulation starting at the Event Choice Screen."""
    app = IslandVisualizerApp(seed=seed, mind_type=mind, noise_source=noise, start_screen=start_screen)
    app.run()

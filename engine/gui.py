"""
engine/gui.py - Interactive 2D Pygame Island Simulation, Home Screen & Debrief HUD
Owned by Tech C (Integration, Engine, Visualization).

Enhanced Suite:
  1. Fullscreen & High-DPI Resolution Scaling:
     - Instant fullscreen toggle via [⛶ Fullscreen] button or F11 / F key.
     - Virtual canvas rendering with letterboxing/pillarboxing maintaining exact aspect ratio
       and pixel-perfect mouse coordinate transformation at any display resolution.
  2. Tactile, Modern UI Buttons:
     - Native system hand cursor on hover (pygame.SYSTEM_CURSOR_HAND).
     - Visual depth: subtle drop shadows, 1px mechanical press displacement, outer glow on hover,
       and click ripple animation.
     - Specialized button variants: Primary Emerald, Quantum Purple, Classical Blue,
       Reconnaissance Cyan, Danger Crimson, and Minimalist Ghost.
  3. Interactive Home Screen (Start Menu):
     - Real-time procedural island mini-map preview thumbnail with terrain stats (land %, forest %, streams).
     - Decision Mind selection cards with formula previews (Qiskit 2-qubit vs Classical ATUS).
     - Island Presets with semantic difficulty tags + full numeric seed stepper (-100 to +100) + randomizer.
     - Step horizon selector (12, 24, 36, 48 turns).
     - Glowing Hero Launch button.
  4. 2D Island Living World Viewport:
     - Procedural 40x40 tiles with dynamic water waves, sparkling freshwater streams, shore foam,
       layered pine canopies with food berry clusters, and alpine snowcaps.
     - Dynamic lighting & weather: day ambient warmth, night navy tint (21:00-05:00),
       storm rain with lightning flashes, and cold night frost vignette with drifting snow.
     - Animated survivor avatar with walking interpolation (lerp), walking bobbing,
       condition badges, particle bursts, and overhead speech bubbles.
     - Hovering tile inspector tooltip near mouse cursor.
  5. Telemetry HUD & Status Screens:
     - Survivor profile with dynamic mood facial expression based on vitals.
     - 6 Need Bars with dual-layer glossy progress bars and color gradation.
     - Composite stress gauge & hardware decoherence meter.
     - Event hazard banner and chronological order-effect chain.
     - Action probability horizontal bar chart with leading action star highlight.
     - Plain-language quantum reasoning quote box.
  6. End-of-Event Debrief Screen & Action History Log Overlay:
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
# Configuration & Virtual Display Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 760
MAP_SIZE = 760
GRID_DIM = 40
TILE_SIZE = MAP_SIZE // GRID_DIM  # 19 px per tile
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
    {"label": "Archipelago (Seed 101)", "seed": 101, "tag": "Balanced • High Survival", "color": COLOR_GREEN},
    {"label": "Arid Crag (Seed 105)", "seed": 105, "tag": "Arid Interior • Thirst Peril", "color": COLOR_ORANGE},
    {"label": "Interference Lab (Seed 202)", "seed": 202, "tag": "Order Effect Divergence", "color": COLOR_PURPLE},
    {"label": "Heroic Haven (Seed 777)", "seed": 777, "tag": "Timber Rich • Freshwater", "color": COLOR_CYAN}
]


def set_cursor_safely(cursor_type):
    """Safely sets system mouse cursor, handling environments without window manager support."""
    try:
        pygame.mouse.set_cursor(cursor_type)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Tactile UI Button Component
# -----------------------------------------------------------------------------
class UIButton:
    def __init__(self, rect: Tuple[int, int, int, int], text: str, font: pygame.font.Font,
                 bg_color=COLOR_PANEL_BG, text_color=COLOR_TEXT_MAIN,
                 border_color=COLOR_CARD_BORDER, active_color=COLOR_CYAN,
                 subtext: Optional[str] = None, subfont: Optional[pygame.font.Font] = None,
                 variant: str = "default"):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.subtext = subtext
        self.font = font
        self.subfont = subfont
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color
        self.active_color = active_color
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
        # Update ripple
        if self.ripple_timer > 0:
            self.ripple_timer = max(0.0, self.ripple_timer - dt)

        # Mechanical press displacement
        dy = 1 if self.is_pressed else 0
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + dy, self.rect.width, self.rect.height)

        # 1. Subtle Drop Shadow
        if not self.is_pressed:
            shadow_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), (0, 0, self.rect.width, self.rect.height), border_radius=6)
            surface.blit(shadow_surf, (self.rect.x, self.rect.y + 2))

        # 2. Determine Fill and Border Colors
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

        # Draw button body
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

        # Text Rendering
        txt_col = COLOR_TEXT_MAIN if (self.is_active or self.is_hovered) else self.text_color
        txt_surf = self.font.render(self.text, True, txt_col)

        if self.subtext and self.subfont:
            total_h = txt_surf.get_height() + 14
            tx = draw_rect.x + (draw_rect.width - txt_surf.get_width()) // 2
            ty = draw_rect.y + (draw_rect.height - total_h) // 2
            surface.blit(txt_surf, (tx, ty))

            sub_col = self.active_color if self.is_active else COLOR_TEXT_MUTED
            sub_surf = self.subfont.render(self.subtext, True, sub_col)
            sx = draw_rect.x + (draw_rect.width - sub_surf.get_width()) // 2
            surface.blit(sub_surf, (sx, ty + txt_surf.get_height() + 2))
        else:
            tx = draw_rect.x + (draw_rect.width - txt_surf.get_width()) // 2
            ty = draw_rect.y + (draw_rect.height - txt_surf.get_height()) // 2
            surface.blit(txt_surf, (tx, ty))


# -----------------------------------------------------------------------------
# Weather & Particle Systems
# -----------------------------------------------------------------------------
class WeatherSystem:
    def __init__(self, bounds: Tuple[int, int]):
        self.max_x, self.max_y = bounds
        self.rain_drops = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(11, 17)]
            for _ in range(130)
        ]
        self.snow_flakes = [
            [random.uniform(0, self.max_x), random.uniform(0, self.max_y), random.uniform(1.2, 3.2), random.uniform(0.6, 1.8)]
            for _ in range(85)
        ]
        self.sparks: List[List[float]] = []
        self.lightning_flash: float = 0.0

    def update(self, event: str, dt: float):
        if event == "storm":
            if self.lightning_flash > 0:
                self.lightning_flash = max(0.0, self.lightning_flash - dt * 2.5)
            elif random.random() < 0.008:
                self.lightning_flash = 0.5

            for drop in self.rain_drops:
                drop[0] -= 4.5 * (dt * 60)
                drop[1] += drop[2] * (dt * 60)
                if drop[1] > self.max_y:
                    drop[1] = 0
                    drop[0] = random.uniform(0, self.max_x + 100)
                if drop[0] < 0:
                    drop[0] = self.max_x

        if event == "cold_night":
            for flake in self.snow_flakes:
                flake[0] += math.sin(flake[1] * 0.05) * 1.2 * (dt * 60)
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
        count = 14 if action in ("build_shelter", "forage", "drink") else 8
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.2, 4.0)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed - 1.4
            life = random.uniform(0.5, 1.0)
            self.sparks.append([x, y, dx, dy, life, life, color])

    def draw(self, surface: pygame.Surface, event: str):
        if event == "storm" and self.lightning_flash > 0:
            flash_surf = pygame.Surface((self.max_x, self.max_y), pygame.SRCALPHA)
            alpha = int(self.lightning_flash * 180)
            flash_surf.fill((255, 255, 255, alpha))
            surface.blit(flash_surf, (0, 0))

        if event == "storm":
            for drop in self.rain_drops:
                x, y = int(drop[0]), int(drop[1])
                pygame.draw.line(surface, (148, 197, 245, 180), (x, y), (x - 3, y + 9), 1)

        elif event == "cold_night":
            for flake in self.snow_flakes:
                x, y = int(flake[0]), int(flake[1])
                pygame.draw.circle(surface, (241, 245, 249, 210), (x, y), int(flake[2]))

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

        # Window & Virtual Canvas Setup
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Typography
        self.font_hero = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 28, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 16, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 12)
        self.font_mono = pygame.font.SysFont("Consolas, Courier New, monospace", 11)
        self.font_bubble = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 11, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 10)

        # Flow States: "home" | "sim"
        self.app_state = start_screen
        self.show_debrief_modal = False
        self.show_history_overlay = False

        # Config Parameters
        self.seed = seed
        self.mind_type = mind_type  # "quantum" | "classical"
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
        self.preview_mini_map = self._generate_mini_map(self.seed, size=240)

        # Visuals
        self.weather = WeatherSystem((MAP_SIZE, MAP_SIZE))
        self.char_screen_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE // 2)
        self.char_screen_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE // 2)
        self.char_bob = 0.0
        self.bubble_text = "Awakening on uncharted shores..."
        self.bubble_timer = 3.5
        self.selected_tile: Optional[Tuple[int, int]] = None

        # Build Interactive Button Layouts
        self._build_home_buttons()
        self._build_sim_buttons()

    def toggle_fullscreen(self):
        """Toggles between Windowed and Fullscreen modes with automatic aspect-ratio scaling."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            info = pygame.display.Info()
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

    def get_virtual_mouse_pos(self) -> Tuple[int, int]:
        """Maps physical window/fullscreen mouse coordinates back into the virtual 1280x760 canvas."""
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

    def _generate_mini_map(self, seed: int, size: int = 240) -> pygame.Surface:
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

        # Spawn indicator
        sx, sy = int(w.spawn_pos[0] * t_sz), int(w.spawn_pos[1] * t_sz)
        pygame.draw.circle(surf, COLOR_RED, (sx, sy), 5)
        pygame.draw.circle(surf, COLOR_TEXT_MAIN, (sx, sy), 3)
        return surf

    def _build_home_buttons(self):
        card_x = 420
        top_y = 110

        # Fullscreen Toggle Button on Home Screen
        self.btn_home_fs = UIButton((WINDOW_WIDTH - 145, 24, 120, 32), "⛶ Fullscreen", self.font_body,
                                    bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)

        # 1. Mind Toggle Cards
        self.btn_mind_quantum = UIButton(
            (card_x + 20, top_y + 45, 380, 68), "⚛  2-Qubit Quantum Mind", self.font_title,
            subtext="Non-commuting rotations $R_y, R_z$ + delay decoherence under stress",
            subfont=self.font_small, active_color=COLOR_PURPLE
        )
        self.btn_mind_classical = UIButton(
            (card_x + 415, top_y + 45, 380, 68), "🧠  Classical Rational Mind", self.font_title,
            subtext="Deterministic utility argmax from published ATUS summary tables",
            subfont=self.font_small, active_color=COLOR_BLUE
        )

        # 2. Preset Island Map Buttons
        self.preset_buttons: List[UIButton] = []
        p_y = top_y + 155
        for i, preset in enumerate(PRESETS):
            px = card_x + 20 + (i % 2) * 395
            py = p_y + (i // 2) * 50
            btn = UIButton((px, py, 380, 42), preset["label"], self.font_sub,
                           subtext=preset["tag"], subfont=self.font_small, active_color=preset["color"])
            self.preset_buttons.append(btn)

        # 3. Seed Steppers
        s_y = top_y + 280
        self.btn_seed_m100 = UIButton((card_x + 20, s_y, 50, 34), "-100", self.font_body)
        self.btn_seed_m10 = UIButton((card_x + 75, s_y, 45, 34), "-10", self.font_body)
        self.btn_seed_m1 = UIButton((card_x + 125, s_y, 40, 34), "-1", self.font_body)
        self.btn_seed_p1 = UIButton((card_x + 475, s_y, 40, 34), "+1", self.font_body)
        self.btn_seed_p10 = UIButton((card_x + 520, s_y, 45, 34), "+10", self.font_body)
        self.btn_seed_p100 = UIButton((card_x + 570, s_y, 50, 34), "+100", self.font_body)
        self.btn_seed_rand = UIButton((card_x + 635, s_y, 160, 34), "🎲  Random Island", self.font_sub, active_color=COLOR_YELLOW)

        # 4. Step Number Buttons
        self.step_buttons: List[UIButton] = []
        step_choices = [12, 24, 36, 48]
        st_y = top_y + 365
        for i, steps in enumerate(step_choices):
            sx = card_x + 20 + i * 194
            btn = UIButton((sx, st_y, 185, 38), f"{steps} Steps ({steps*2}h)", self.font_sub, active_color=COLOR_CYAN)
            self.step_buttons.append(btn)

        # 5. Launch Button
        self.btn_launch = UIButton(
            (card_x + 20, top_y + 445, 775, 54), "🚀  LAUNCH SURVIVAL SIMULATION", self.font_hero,
            bg_color=(21, 128, 61), active_color=COLOR_GREEN
        )

    def _build_sim_buttons(self):
        # Map view top navigation bar buttons
        self.btn_nav_home = UIButton((14, 10, 95, 30), "🏠 Menu", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)
        self.btn_nav_pause = UIButton((115, 10, 85, 30), "⏸ Pause", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_YELLOW)
        self.btn_nav_step = UIButton((206, 10, 85, 30), "⏭ Step", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_GREEN)
        self.btn_nav_speed = UIButton((297, 10, 85, 30), "⚡ 1.0x", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)
        self.btn_nav_mind = UIButton((388, 10, 110, 30), "⚛ Quantum", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_PURPLE)
        self.btn_nav_log = UIButton((504, 10, 110, 30), "📋 Action Log", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)
        self.btn_nav_fs = UIButton((620, 10, 126, 30), "⛶ Fullscreen", self.font_body, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN)

        # Debrief modal buttons
        mx = WINDOW_WIDTH // 2
        my = WINDOW_HEIGHT // 2
        self.btn_modal_replay = UIButton((mx - 240, my + 140, 140, 42), "🔄 Replay Run", self.font_sub, bg_color=(37, 99, 235))
        self.btn_modal_switch = UIButton((mx - 85, my + 140, 170, 42), "⚛/🧠 Compare Mind", self.font_sub, bg_color=COLOR_PURPLE)
        self.btn_modal_home = UIButton((mx + 100, my + 140, 140, 42), "🏠 Home Screen", self.font_sub, bg_color=(51, 65, 85))
        self.btn_modal_close = UIButton((mx + 255, my - 185, 32, 32), "✕", self.font_title, bg_color=COLOR_PANEL_BG)

        # History log modal close
        self.btn_hist_close = UIButton((WINDOW_WIDTH // 2 + 360, 45, 32, 32), "✕", self.font_title, bg_color=COLOR_PANEL_BG)

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
        self.bubble_text = f"{action.upper()}: {narrative.split(';')[0]}"
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

            # Hover detection and cursor update
            any_hovered = self._update_hovers(virt_pos)
            if any_hovered:
                set_cursor_safely(pygame.SYSTEM_CURSOR_HAND)
            else:
                set_cursor_safely(pygame.SYSTEM_CURSOR_ARROW)

            # Process Events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

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

            # Smooth Character Interpolation & Bobbing
            if self.app_state == "sim":
                target_x = float(self.agent.pos[0] * TILE_SIZE + TILE_SIZE // 2)
                target_y = float(self.agent.pos[1] * TILE_SIZE + TILE_SIZE // 2)
                dist = math.hypot(target_x - self.char_screen_x, target_y - self.char_screen_y)
                if dist > 1.0:
                    self.char_bob += dt * 15.0
                else:
                    self.char_bob = math.sin(time.time() * 3.0) * 0.8

                self.char_screen_x += (target_x - self.char_screen_x) * min(1.0, 10.0 * dt)
                self.char_screen_y += (target_y - self.char_screen_y) * min(1.0, 10.0 * dt)
                self.weather.update(self.current_event, dt)
                if self.bubble_timer > 0:
                    self.bubble_timer -= dt

            # Draw Viewport onto Virtual Canvas
            self.draw(virt_pos)

            # Present Virtual Canvas with Aspect-Preserving Scaling & Letterboxing
            self.present()

        pygame.quit()

    def _update_hovers(self, pos: Tuple[int, int]) -> bool:
        """Updates hover states for all interactive UI buttons and returns True if any button is hovered."""
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
        """Scales the 1280x760 virtual canvas to the physical window/fullscreen maintaining aspect ratio."""
        sw, sh = self.screen.get_size()
        if sw == WINDOW_WIDTH and sh == WINDOW_HEIGHT:
            self.screen.blit(self.canvas, (0, 0))
        else:
            scale = min(sw / WINDOW_WIDTH, sh / WINDOW_HEIGHT)
            scaled_w = int(WINDOW_WIDTH * scale)
            scaled_h = int(WINDOW_HEIGHT * scale)
            offset_x = (sw - scaled_w) // 2
            offset_y = (sh - scaled_h) // 2

            scaled_surf = pygame.transform.smoothscale(self.canvas, (scaled_w, scaled_h))
            self.screen.fill((5, 8, 18))  # Dark letterbox fill
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
                self.preview_mini_map = self._generate_mini_map(self.seed, size=240)

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
            self.preview_mini_map = self._generate_mini_map(self.seed, size=240)

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
            tx, ty = mx // TILE_SIZE, my // TILE_SIZE
            if 0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM:
                self.selected_tile = (tx, ty)

    def draw(self, mouse_pos: Tuple[int, int] = (0, 0)):
        """Draws current view onto the virtual canvas."""
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
        self.btn_home_fs.text = "🗗 Windowed" if self.is_fullscreen else "⛶ Fullscreen"
        self.btn_home_fs.check_hover(mouse_pos)
        self.btn_home_fs.draw(self.canvas)

        # Header Title
        title_surf = self.font_hero.render("STRANDED: QUANTUM SURVIVAL ENGINE", True, COLOR_TEXT_MAIN)
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 24))

        sub_str = "Qiskit 2.x • 2-Qubit Non-Commuting Cognition • IBM Hardware Decoherence Modeling"
        sub_surf = self.font_sub.render(sub_str, True, COLOR_CYAN)
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 62))

        # Left Reconnaissance Card: Live Island Mini-Map ($370 x 530)
        col1_x = 24
        col1_y = 96
        col1_w = 370
        col1_h = 530
        self.draw_card(col1_x, col1_y, col1_w, col1_h)

        c1_title = self.font_title.render("ISLAND RECONNAISSANCE", True, COLOR_YELLOW)
        self.canvas.blit(c1_title, (col1_x + 18, col1_y + 16))

        # Mini-map container ($240 x 240)
        map_box = pygame.Rect(col1_x + (col1_w - 240) // 2, col1_y + 48, 240, 240)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, map_box, 2, border_radius=4)
        self.canvas.blit(self.preview_mini_map, (map_box.x, map_box.y))

        # Terrain Statistics
        stat_y = col1_y + 304
        stats_box = pygame.Rect(col1_x + 18, stat_y, col1_w - 36, 150)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, stats_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, stats_box, 1, border_radius=6)

        temp_w = IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=self.seed)
        land_tiles = sum(1 for row in temp_w.tiles for t in row if t in (1, 2, 3, 4))
        forest_tiles = sum(1 for row in temp_w.tiles for t in row if t == 2)
        streams = len(temp_w.freshwater_tiles)
        land_pct = int(land_tiles / (GRID_DIM * GRID_DIM) * 100)
        forest_pct = int(forest_tiles / max(1, land_tiles) * 100)

        lines = [
            f"World Seed:       #{self.seed}",
            f"Land Coverage:    {land_pct}% (Usable Mass)",
            f"Forest Density:   {forest_pct}% (Timber & Food)",
            f"Freshwater:       {'Available (' + str(streams) + ' tiles)' if streams > 0 else 'Arid / Sparse'}",
            f"Starting Spawn:   [{temp_w.spawn_pos[0]}, {temp_w.spawn_pos[1]}] (Sheltered Coast)"
        ]
        for i, line in enumerate(lines):
            col = COLOR_CYAN if i == 0 else (COLOR_GREEN if i in (1, 2) else COLOR_TEXT_MUTED)
            self.canvas.blit(self.font_mono.render(line, True, col), (stats_box.x + 14, stats_box.y + 14 + i * 26))

        leg_surf = self.font_small.render("● Red dot: Initial survivor drop-in spawn point", True, COLOR_RED)
        self.canvas.blit(leg_surf, (col1_x + 24, col1_y + 468))

        # Right Configuration Card ($848 x 530)
        col2_x = 408
        col2_y = 96
        col2_w = 848
        col2_h = 530
        self.draw_card(col2_x, col2_y, col2_w, col2_h)

        # 1. Decision Mind Selection
        m_lbl = self.font_title.render("1. Select Cognitive Mind Model", True, COLOR_TEXT_MAIN)
        self.canvas.blit(m_lbl, (col2_x + 20, col2_y + 16))

        self.btn_mind_quantum.is_active = (self.mind_type == "quantum")
        self.btn_mind_classical.is_active = (self.mind_type == "classical")
        self.btn_mind_quantum.check_hover(mouse_pos)
        self.btn_mind_classical.check_hover(mouse_pos)
        self.btn_mind_quantum.draw(self.canvas)
        self.btn_mind_classical.draw(self.canvas)

        # 2. Island Presets & Custom Stepper
        p_lbl = self.font_title.render("2. Select Island Preset or Custom World Seed", True, COLOR_TEXT_MAIN)
        self.canvas.blit(p_lbl, (col2_x + 20, col2_y + 128))

        for i, p_btn in enumerate(self.preset_buttons):
            p_btn.is_active = (self.seed == PRESETS[i]["seed"])
            p_btn.check_hover(mouse_pos)
            p_btn.draw(self.canvas)

        seed_box = pygame.Rect(col2_x + 175, col2_y + 280, 290, 34)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, seed_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, seed_box, 1, border_radius=6)
        seed_txt = self.font_title.render(f"Island Seed:  {self.seed}", True, COLOR_YELLOW)
        self.canvas.blit(seed_txt, (seed_box.x + (seed_box.width - seed_txt.get_width()) // 2, seed_box.y + 6))

        for s_btn in (self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1, self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100, self.btn_seed_rand):
            s_btn.check_hover(mouse_pos)
            s_btn.draw(self.canvas)

        # 3. Simulation Duration
        st_lbl = self.font_title.render("3. Simulation Step Horizon (2 Hours per Turn)", True, COLOR_TEXT_MAIN)
        self.canvas.blit(st_lbl, (col2_x + 20, col2_y + 332))

        step_choices = [12, 24, 36, 48]
        for i, st_btn in enumerate(self.step_buttons):
            st_btn.is_active = (self.max_steps == step_choices[i])
            st_btn.check_hover(mouse_pos)
            st_btn.draw(self.canvas)

        # 4. Hero Launch Button
        self.btn_launch.check_hover(mouse_pos)
        self.btn_launch.draw(self.canvas)

        tip_str = "Press [ENTER] to Launch  •  [F11] Fullscreen  •  [Q] Toggle Mind Model  •  Decoherence Active"
        self.canvas.blit(self.font_sub.render(tip_str, True, COLOR_TEXT_HINT), (WINDOW_WIDTH // 2 - 275, WINDOW_HEIGHT - 32))

    # -------------------------------------------------------------------------
    # Render Simulation Screen (State 2)
    # -------------------------------------------------------------------------
    def draw_sim_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)

        # 1. Map Surface
        self.draw_island_map()

        # 2. Weather & Lighting
        self.draw_atmosphere()

        # 3. Survivor Character & Overhead Bubble
        self.draw_character()

        # 4. Top Map Bar Controls
        self.draw_map_navigation_bar(mouse_pos)

        # 5. Telemetry & Analytics Dashboard
        self.draw_dashboard()

        # 6. Floating Tile Inspector Tooltip
        self.draw_tile_tooltip(mouse_pos)

        # 7. Modals: Full Action Log Overlay or Debrief Modal
        if self.show_history_overlay:
            self.draw_history_overlay(mouse_pos)
        elif self.show_debrief_modal:
            self.draw_debrief_modal(mouse_pos)

    def draw_map_navigation_bar(self, mouse_pos: Tuple[int, int]):
        bar_bg = pygame.Surface((MAP_SIZE, 50), pygame.SRCALPHA)
        bar_bg.fill((15, 23, 42, 215))
        self.canvas.blit(bar_bg, (0, 0))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (0, 50), (MAP_SIZE, 50), 1)

        self.btn_nav_pause.text = "▶ Play" if self.is_paused else "⏸ Pause"
        self.btn_nav_speed.text = f"⚡ {self.speed_multiplier}x"
        self.btn_nav_mind.text = "⚛ Quantum" if self.mind_type == "quantum" else "🧠 Classical"
        self.btn_nav_mind.active_color = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE
        self.btn_nav_fs.text = "🗗 Window" if self.is_fullscreen else "⛶ Fullscreen"

        for btn in (self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step, self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_log, self.btn_nav_fs):
            btn.check_hover(mouse_pos)
            btn.draw(self.canvas)

    def draw_island_map(self):
        t_time = time.time()
        for y in range(GRID_DIM):
            for x in range(GRID_DIM):
                tile = self.world.get_tile(x, y)
                rx, ry = x * TILE_SIZE, y * TILE_SIZE
                rect = pygame.Rect(rx, ry, TILE_SIZE, TILE_SIZE)

                if tile == 0:
                    is_fresh = (x, y) in self.world.freshwater_tiles
                    if is_fresh:
                        flow = math.sin(t_time * 4.0 + x * 0.6 + y * 0.6) * 22
                        base = (56, max(0, min(255, 189 + int(flow))), 248)
                        pygame.draw.rect(self.canvas, base, rect)
                        pygame.draw.circle(self.canvas, (224, 242, 254), (rx + TILE_SIZE // 2, ry + TILE_SIZE // 2), 2)
                    else:
                        wave = math.sin(t_time * 2.2 + x * 0.35 + y * 0.45) * 16
                        c = (27, max(0, min(255, 58 + int(wave))), 91)
                        pygame.draw.rect(self.canvas, c, rect)

                elif tile == 1:
                    has_water_adj = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    color = (234, 179, 8) if has_water_adj else (132, 204, 22)
                    pygame.draw.rect(self.canvas, color, rect)
                    speck = (202, 138, 4) if has_water_adj else (101, 163, 13)
                    pygame.draw.rect(self.canvas, speck, (rx + 4, ry + 4, 3, 3))

                elif tile == 2:
                    pygame.draw.rect(self.canvas, (22, 101, 52), rect)
                    pygame.draw.circle(self.canvas, (21, 128, 61), (rx + TILE_SIZE // 2, ry + TILE_SIZE // 2), TILE_SIZE // 2 - 1)
                    if (x, y) in self.world.food_tiles:
                        pygame.draw.circle(self.canvas, COLOR_RED, (rx + 5, ry + 5), 2)
                        pygame.draw.circle(self.canvas, COLOR_RED, (rx + 12, ry + 6), 2)

                elif tile == 3:
                    pygame.draw.rect(self.canvas, (71, 85, 105), rect)
                    p1 = (rx + TILE_SIZE // 2, ry + 2)
                    p2 = (rx + 2, ry + TILE_SIZE - 2)
                    p3 = (rx + TILE_SIZE - 2, ry + TILE_SIZE - 2)
                    pygame.draw.polygon(self.canvas, (100, 116, 139), [p1, p2, p3])
                    pygame.draw.polygon(self.canvas, (248, 250, 252), [p1, (rx + TILE_SIZE // 2 - 3, ry + 6), (rx + TILE_SIZE // 2 + 3, ry + 6)])

                elif tile == 4:
                    pygame.draw.rect(self.canvas, (101, 163, 13), rect)
                    p_roof = [(rx + TILE_SIZE // 2, ry + 1), (rx + 1, ry + TILE_SIZE - 2), (rx + TILE_SIZE - 2, ry + TILE_SIZE - 2)]
                    pygame.draw.polygon(self.canvas, (180, 83, 9), p_roof)
                    ember_glow = int(math.sin(t_time * 6.0) * 40)
                    pygame.draw.circle(self.canvas, (245, max(0, min(255, 158 + ember_glow)), 11), (rx + TILE_SIZE // 2, ry + TILE_SIZE - 4), 3)

        if self.selected_tile:
            tx, ty = self.selected_tile
            s_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(self.canvas, COLOR_CYAN, s_rect, 2)

        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 2)

    def draw_atmosphere(self):
        hour = self.agent.hour
        if hour >= 21 or hour <= 5:
            night_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            night_surf.fill((10, 15, 35, 125))
            self.canvas.blit(night_surf, (0, 0))

        if self.current_event == "cold_night":
            frost_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            frost_surf.fill((148, 197, 245, 45))
            self.canvas.blit(frost_surf, (0, 0))

        self.weather.draw(self.canvas, self.current_event)

    def draw_character(self):
        cx, cy = int(self.char_screen_x), int(self.char_screen_y + self.char_bob)

        # Ground Shadow
        shadow_surf = pygame.Surface((22, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 95), (0, 0, 22, 10))
        self.canvas.blit(shadow_surf, (cx - 11, cy + 6))

        # Torso & Clothing
        body_color = (217, 119, 6) if not self.agent.injured else (185, 28, 28)
        pygame.draw.rect(self.canvas, body_color, (cx - 5, cy - 6, 10, 12), border_radius=2)

        # Head & Blue Cap
        pygame.draw.circle(self.canvas, (254, 215, 170), (cx, cy - 10), 6)
        pygame.draw.circle(self.canvas, (67, 56, 202), (cx, cy - 12), 6, 2)
        # Satchel
        pygame.draw.rect(self.canvas, (120, 53, 15), (cx + 3, cy - 4, 4, 7), border_radius=1)

        # Injury Cross
        if self.agent.injured:
            pygame.draw.circle(self.canvas, COLOR_RED, (cx - 8, cy - 14), 5)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 10, cy - 14), (cx - 6, cy - 14), 2)
            pygame.draw.line(self.canvas, COLOR_TEXT_MAIN, (cx - 8, cy - 16), (cx - 8, cy - 12), 2)

        # Shelter Shield
        if self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1]):
            pygame.draw.polygon(self.canvas, COLOR_GREEN, [(cx, cy - 22), (cx - 6, cy - 16), (cx + 6, cy - 16)])

        # Speech / Thought Bubble
        if self.bubble_timer > 0 and self.bubble_text:
            text_surf = self.font_bubble.render(self.bubble_text, True, (15, 23, 42))
            tw, th = text_surf.get_width() + 16, text_surf.get_height() + 8
            bx = max(10, min(MAP_SIZE - tw - 10, cx - tw // 2))
            by = cy - 44

            b_rect = pygame.Rect(bx, by, tw, th)
            pygame.draw.rect(self.canvas, (241, 245, 249), b_rect, border_radius=6)
            pygame.draw.rect(self.canvas, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE, b_rect, 2, border_radius=6)
            pygame.draw.polygon(self.canvas, (241, 245, 249), [(cx - 4, by + th), (cx + 4, by + th), (cx, by + th + 4)])
            self.canvas.blit(text_surf, (bx + 8, by + 4))

    def draw_tile_tooltip(self, mouse_pos: Tuple[int, int]):
        mx, my = mouse_pos
        if mx >= MAP_SIZE or my >= MAP_SIZE or my < 50:
            return

        tx, ty = mx // TILE_SIZE, my // TILE_SIZE
        if not (0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM):
            return

        tile_type = self.world.get_tile(tx, ty)
        tile_name = contracts.TILE_TYPES.get(tile_type, "Unknown").capitalize()
        is_fresh = (tx, ty) in self.world.freshwater_tiles
        is_food = (tx, ty) in self.world.food_tiles

        desc = "Freshwater Stream" if is_fresh else ("Berry Forage Grove" if is_food else f"{tile_name} Terrain")
        tt_str = f"[{tx}, {ty}] {tile_name} • {desc}"
        txt_surf = self.font_small.render(tt_str, True, COLOR_TEXT_MAIN)

        tt_w, tt_h = txt_surf.get_width() + 16, txt_surf.get_height() + 8
        tt_x = max(10, min(MAP_SIZE - tt_w - 10, mx + 12))
        tt_y = max(55, min(MAP_SIZE - tt_h - 10, my - 24))

        tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
        pygame.draw.rect(self.canvas, (15, 23, 42), tt_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CYAN, tt_rect, 1, border_radius=4)
        self.canvas.blit(txt_surf, (tt_x + 8, tt_y + 4))

    def draw_dashboard(self):
        panel_x = MAP_SIZE + 16
        panel_w = WINDOW_WIDTH - MAP_SIZE - 32
        curr_y = 12

        # Card 1: Survivor Profile & Vitals ($500 x 175)
        card1_h = 175
        self.draw_card(panel_x, curr_y, panel_w, card1_h)

        mood_str = "😊 Resilient"
        mood_col = COLOR_GREEN
        if not self.agent.is_alive:
            mood_str = "💀 Perished"
            mood_col = COLOR_RED
        elif self.agent.injured:
            mood_str = "🤕 Injured"
            mood_col = COLOR_RED
        elif self.agent.stress > 0.65:
            mood_str = "😰 Anxious"
            mood_col = COLOR_ORANGE
        elif self.agent.needs["warmth"] < 0.3:
            mood_str = "🥶 Freezing"
            mood_col = COLOR_CYAN

        header_surf = self.font_sub.render(f"SURVIVOR STATUS  [{mood_str}]", True, mood_col)
        self.canvas.blit(header_surf, (panel_x + 14, curr_y + 10))

        step_txt = f"Day {self.agent.day} • {self.agent.hour:02d}:00  (Step {self.step_idx}/{self.max_steps})"
        self.canvas.blit(self.font_mono.render(step_txt, True, COLOR_TEXT_MUTED), (panel_x + panel_w - 210, curr_y + 10))

        needs = self.agent.needs
        need_items = [
            ("Hunger", needs["hunger"], COLOR_YELLOW),
            ("Thirst", needs["thirst"], COLOR_CYAN),
            ("Warmth", needs["warmth"], COLOR_ORANGE),
            ("Energy", needs["energy"], COLOR_GREEN),
            ("Safety", needs["safety"], COLOR_BLUE),
            ("Morale", needs["morale"], COLOR_PURPLE)
        ]

        bar_w = (panel_w - 36) // 2
        for idx, (lbl, val, bar_color) in enumerate(need_items):
            col = idx % 2
            row = idx // 2
            bx = panel_x + 14 + col * (bar_w + 12)
            by = curr_y + 36 + row * 25
            self.draw_progress_bar(bx, by, bar_w, 13, lbl, val, bar_color)

        stress_y = curr_y + 115
        self.draw_progress_bar(
            panel_x + 14, stress_y, bar_w, 15,
            "Stress", self.agent.stress, COLOR_RED if self.agent.stress > 0.6 else COLOR_YELLOW
        )

        decoherence_pct = 0.0
        if self.agent.stress > 0.4:
            decoherence_pct = min(1.0, (self.agent.stress - 0.4) / 0.5)
        self.draw_progress_bar(
            panel_x + 26 + bar_w, stress_y, bar_w, 15,
            "Decoherence", decoherence_pct, COLOR_PURPLE
        )

        inv = self.agent.inventory
        inv_str = f"🎒 Resources:   Timber: {inv.get('wood', 0)}   •   Rations: {inv.get('food', 0)}   •   Tools: {inv.get('tools', 0)}"
        self.canvas.blit(self.font_body.render(inv_str, True, COLOR_TEXT_MUTED), (panel_x + 14, curr_y + 146))

        curr_y += card1_h + 10

        # Card 2: Environment Hazard & Chronology ($500 x 105)
        card2_h = 105
        self.draw_card(panel_x, curr_y, panel_w, card2_h)
        header_env = self.font_sub.render("ENVIRONMENTAL HAZARD & EVENT CHRONOLOGY", True, COLOR_YELLOW)
        self.canvas.blit(header_env, (panel_x + 14, curr_y + 10))

        ev_upper = self.current_event.upper()
        ev_color = COLOR_RED if ev_upper in ("STORM", "INJURY", "ANIMAL") else (COLOR_CYAN if ev_upper == "COLD_NIGHT" else COLOR_GREEN)
        self.draw_badge(panel_x + 14, curr_y + 34, f"ACTIVE HAZARD: {ev_upper}", ev_color)

        px, py = self.agent.pos
        tile_name = contracts.TILE_TYPES.get(self.world.get_tile(px, py), "Unknown").capitalize()
        pos_txt = f"Coordinates: [{px}, {py}]  |  Biome: {tile_name}  |  Shelter: {'Yes' if self.world.is_in_shelter(px, py) else 'No'}"
        self.canvas.blit(self.font_body.render(pos_txt, True, COLOR_TEXT_MUTED), (panel_x + 14, curr_y + 60))

        history_str = " ➔ ".join([e.upper() for e in self.agent.recent_events if e != "none"] or ["None"])
        self.canvas.blit(self.font_mono.render(f"Event Order Effect: [ {history_str} ]", True, COLOR_CYAN), (panel_x + 14, curr_y + 82))

        curr_y += card2_h + 10

        # Card 3: Quantum Superposition & Probabilities ($500 x 240)
        card3_h = 240
        self.draw_card(panel_x, curr_y, panel_w, card3_h)

        mind_title = "2-QUBIT QUANTUM BELIEF STATE" if self.mind_type == "quantum" else "CLASSICAL RATIONAL UTILITY"
        self.canvas.blit(self.font_sub.render(mind_title, True, COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE), (panel_x + 14, curr_y + 10))

        chosen_act = self.current_decision.get("action", "none").upper()
        self.draw_badge(panel_x + 14, curr_y + 32, f"EXECUTED ACTION: {chosen_act}", ACTION_COLORS.get(chosen_act.lower(), COLOR_GREEN))

        probs = self.current_decision.get("probs", {})
        chart_y = curr_y + 60
        actions_list = contracts.ACTIONS
        chart_w = panel_w - 120

        max_act = max(probs.items(), key=lambda it: it[1])[0] if probs else "none"

        for act in actions_list:
            p = probs.get(act, 0.0)
            act_color = ACTION_COLORS.get(act, COLOR_CYAN)
            is_top = (act == max_act)

            lbl_txt = f"★ {act[:8]}" if is_top else f"  {act[:8]}"
            lbl_col = COLOR_GOLD if is_top else COLOR_TEXT_MAIN
            self.canvas.blit(self.font_mono.render(f"{lbl_txt:10s}", True, lbl_col), (panel_x + 14, chart_y))

            bar_rect = pygame.Rect(panel_x + 95, chart_y + 2, chart_w, 10)
            pygame.draw.rect(self.canvas, (15, 23, 42), bar_rect, border_radius=2)
            fill_w = max(2, int(p * chart_w))
            pygame.draw.rect(self.canvas, act_color, (panel_x + 95, chart_y + 2, fill_w, 10), border_radius=2)

            pct_lbl = self.font_mono.render(f"{p*100:4.1f}%", True, COLOR_TEXT_MUTED)
            self.canvas.blit(pct_lbl, (panel_x + 102 + chart_w, chart_y))
            chart_y += 16

        reason_txt = self.current_decision.get("reason", "")
        reason_rect = pygame.Rect(panel_x + 14, chart_y + 6, panel_w - 28, 52)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, reason_rect, border_radius=5)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, reason_rect, 1, border_radius=5)

        words = reason_txt.split()
        line1 = " ".join(words[:11])
        line2 = " ".join(words[11:23])
        line3 = " ".join(words[23:])
        self.canvas.blit(self.font_body.render(line1, True, COLOR_CYAN), (panel_x + 20, chart_y + 10))
        if line2:
            self.canvas.blit(self.font_body.render(line2, True, COLOR_TEXT_MUTED), (panel_x + 20, chart_y + 24))
        if line3:
            self.canvas.blit(self.font_body.render(line3, True, COLOR_TEXT_HINT), (panel_x + 20, chart_y + 38))

        curr_y += card3_h + 10

        # Card 4: Quick Controls Cheat Sheet ($500 x 85)
        card4_h = 85
        self.draw_card(panel_x, curr_y, panel_w, card4_h)
        controls_lbl = self.font_sub.render("SIMULATION CONTROLS & SHORTCUTS", True, COLOR_TEXT_MAIN)
        self.canvas.blit(controls_lbl, (panel_x + 14, curr_y + 10))

        c_line1 = "[SPACE] Play/Pause   •   [RIGHT] Step Next   •   [F11] Fullscreen"
        c_line2 = f"[Q] Toggle Mind   •   [TAB] Action Log   •   [ESC] Home Menu"
        self.canvas.blit(self.font_body.render(c_line1, True, COLOR_TEXT_MUTED), (panel_x + 14, curr_y + 34))
        self.canvas.blit(self.font_body.render(c_line2, True, COLOR_CYAN), (panel_x + 14, curr_y + 54))

    # -------------------------------------------------------------------------
    # Render End-of-Event Debrief Screen Modal
    # -------------------------------------------------------------------------
    def draw_debrief_modal(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 30, 195))
        self.canvas.blit(dim_surf, (0, 0))

        mw, mh = 640, 420
        mx, my = (WINDOW_WIDTH - mw) // 2, (WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, m_rect, border_radius=12)

        survived = self.agent.is_alive
        border_col = COLOR_GOLD if survived else COLOR_RED
        pygame.draw.rect(self.canvas, border_col, m_rect, 2, border_radius=12)

        m_title = "🏆  MISSION COMPLETE: 48h SURVIVAL MASTERED!" if survived else f"💀  SURVIVOR PERISHED: {str(self.agent.cause_of_death).upper()}"
        m_color = COLOR_GOLD if survived else COLOR_RED
        t_surf = self.font_hero.render(m_title, True, m_color)
        self.canvas.blit(t_surf, (mx + (mw - t_surf.get_width()) // 2, my + 24))

        dur_str = f"Endured {self.step_idx}/{self.max_steps} Steps ({self.step_idx * 2} Game Hours on Island Wilderness)"
        d_surf = self.font_sub.render(dur_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(d_surf, (mx + (mw - d_surf.get_width()) // 2, my + 68))

        box_rect = pygame.Rect(mx + 30, my + 100, mw - 60, 185)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box_rect, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box_rect, 1, border_radius=8)

        lines = [
            ("Decision Engine:", "2-Qubit Quantum Mind (Qiskit 2.x)" if self.mind_type == "quantum" else "Classical ATUS Rational Argmax", COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE),
            ("World Environment:", f"Seed #{self.seed} (Island Terrain, 40x40 Grid)", COLOR_YELLOW),
            ("Final Stress & Noise:", f"{int(self.agent.stress*100)}% Stress  •  Decoherence: {int(max(0, self.agent.stress - 0.4)/0.5 * 100)}% off-diagonal decay", COLOR_CYAN),
            ("Physiological State:", f"Hunger: {int(self.agent.needs['hunger']*100)}% | Thirst: {int(self.agent.needs['thirst']*100)}% | Warmth: {int(self.agent.needs['warmth']*100)}%", COLOR_TEXT_MAIN),
            ("Resource Harvest:", f"Gathered {self.agent.inventory.get('wood',0)} Timber, Consumed Food Rations, Tools Crafted: {self.agent.inventory.get('tools',0)}", COLOR_TEXT_MUTED)
        ]

        for i, (k, v, col) in enumerate(lines):
            ky = box_rect.y + 14 + i * 32
            self.canvas.blit(self.font_sub.render(k, True, COLOR_TEXT_HINT), (box_rect.x + 18, ky))
            self.canvas.blit(self.font_mono.render(v, True, col), (box_rect.x + 180, ky + 2))

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
        dim_surf.fill((10, 15, 30, 210))
        self.canvas.blit(dim_surf, (0, 0))

        hw, hh = 780, 640
        hx, hy = (WINDOW_WIDTH - hw) // 2, (WINDOW_HEIGHT - hh) // 2
        h_rect = pygame.Rect(hx, hy, hw, hh)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, h_rect, border_radius=10)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, h_rect, 2, border_radius=10)

        t_surf = self.font_hero.render("CHRONOLOGICAL ACTION HISTORY LOG", True, COLOR_CYAN)
        self.canvas.blit(t_surf, (hx + 24, hy + 20))

        self.btn_hist_close.check_hover(mouse_pos)
        self.btn_hist_close.draw(self.canvas)

        log_y = hy + 75
        header_str = f"{'Step':5s}  {'Event':12s}  {'Action':14s}  {'Top Prob':10s}  {'Cognitive Reason'}"
        self.canvas.blit(self.font_sub.render(header_str, True, COLOR_GOLD), (hx + 24, log_y))
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (hx + 24, log_y + 24), (hx + hw - 24, log_y + 24), 1)

        row_y = log_y + 34
        visible_records = self.history[-13:]
        for rec in visible_records:
            t_num = f"#{rec['t']:02d}"
            ev = rec["event"].upper()
            act = rec["action"].upper()
            probs = rec["decision"].get("probs", {})
            top_p = max(probs.values()) if probs else 0.0
            p_str = f"{top_p*100:4.1f}%"
            reason = rec["decision"].get("reason", "")[:35] + "..."

            r_str = f"{t_num:5s}  {ev:12s}  {act:14s}  {p_str:10s}  {reason}"
            act_col = ACTION_COLORS.get(rec["action"], COLOR_TEXT_MAIN)
            self.canvas.blit(self.font_mono.render(r_str, True, act_col), (hx + 24, row_y))
            row_y += 24

        tip = self.font_small.render("Press [TAB] or [ESC] to return to simulation", True, COLOR_TEXT_HINT)
        self.canvas.blit(tip, (hx + 24, hy + hh - 30))

    # -------------------------------------------------------------------------
    # UI Utility Helpers
    # -------------------------------------------------------------------------
    def draw_card(self, x: int, y: int, w: int, h: int):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, rect, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, rect, 1, border_radius=8)

    def draw_badge(self, x: int, y: int, text: str, color: Tuple[int, int, int]):
        txt_surf = self.font_sub.render(text, True, color)
        bg_rect = pygame.Rect(x, y, txt_surf.get_width() + 14, txt_surf.get_height() + 6)
        badge_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        badge_surf.fill((color[0], color[1], color[2], 35))
        self.canvas.blit(badge_surf, (x, y))
        pygame.draw.rect(self.canvas, color, bg_rect, 1, border_radius=4)
        self.canvas.blit(txt_surf, (x + 7, y + 3))

    def draw_progress_bar(self, x: int, y: int, w: int, h: int, label: str, value: float, color: Tuple[int, int, int]):
        lbl_surf = self.font_mono.render(f"{label:11s}", True, COLOR_TEXT_MAIN)
        self.canvas.blit(lbl_surf, (x, y))

        bar_x = x + 85
        bar_w = w - 120
        track_rect = pygame.Rect(bar_x, y + 2, bar_w, h - 4)
        pygame.draw.rect(self.canvas, (15, 23, 42), track_rect, border_radius=3)

        fill_w = max(0, min(bar_w, int(value * bar_w)))
        if fill_w > 0:
            pygame.draw.rect(self.canvas, color, (bar_x, y + 2, fill_w, h - 4), border_radius=3)

        val_surf = self.font_mono.render(f"{int(value * 100):3d}%", True, COLOR_TEXT_MUTED)
        self.canvas.blit(val_surf, (bar_x + bar_w + 6, y))


def launch_gui(seed: int = 101, mind: str = "quantum", noise: str = "ibm_hardware", start_screen: str = "home"):
    """Launches the complete Pygame Island Simulation starting at the Home Screen."""
    app = IslandVisualizerApp(seed=seed, mind_type=mind, noise_source=noise, start_screen=start_screen)
    app.run()


if __name__ == "__main__":
    launch_gui()

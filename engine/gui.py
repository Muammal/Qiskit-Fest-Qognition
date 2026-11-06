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

import json
import math
import os
import random
import sys
import threading
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
from engine.ship import DECK_ROWS, ShipWorld
from engine.titanic import TitanicSimulation, STORY_TEXT
from engine.flood import HORIZON as TITANIC_STEPS
from engine.lifeboats import TOTAL_SEATS
from engine.gui_ship import ShipView, mini_map, next_role_person
from engine.city import CityWorld
from engine.pompeii import HORIZON as POMPEII_STEPS, STORY_TEXT as POMPEII_STORY, PompeiiSimulation
from engine.gui_city import CityView, SplitPanels, clock_text, mini_map as city_mini_map, next_role_citizen
from engine.scenes_pompeii import PompeiiCutscenes
from engine.site import SiteWorld
from engine.waterloo import HORIZON as WATERLOO_STEPS, STORY_TEXT as WATERLOO_STORY, WaterlooSimulation
from engine.gui_site import SitePanels, SiteView, clock_text as site_clock, mini_map as site_mini_map, next_role_patron
from engine.scenes_waterloo import WaterlooCutscenes
from engine.cutscenes import CutscenePlayer
from engine.citizens import ACTION_LABELS as POMPEII_ACTION_LABELS
from engine.crowd import ACTION_LABELS as TITANIC_ACTION_LABELS
from engine.flood import SINK_STEP
from engine.patrons import ACTION_LABELS as WATERLOO_ACTION_LABELS
from engine.debrief import MODEL_FOOTER, PairedResult, crowd_line, first_hide, paired_text, run_title
from engine.gui_quantum import QuantumPanel
from engine.report import CUE_TRANSLATIONS, DEFAULT_DIR, build_report, export_report, key_lines, paired_rows, report_name
from engine.hidpi import ScaledFont, UICanvas, compose, setup_dpi_awareness, window_fit

try:
    from mind.decoherence import decoherence_strength
except ImportError:
    def decoherence_strength(stress):
        return min(1.0, max(0.0, (stress - 0.4) / 0.5))


def saved_volcano_batch():
    """The 200-seed line for the volcano debrief, read from the generated results file."""
    path = os.path.join(BASE_DIR, "docs", "results", "scenario_numbers.json")
    try:
        with open(path, encoding="utf-8") as stream:
            volcano = json.load(stream)["volcano"]
    except (OSError, ValueError, KeyError):
        return None
    survival, delay = volcano["survival"], volcano["paired_delay_steps"]
    return (f"Across {volcano['seeds']} seeds: survival {survival['quantum'] * 100:.1f}% quantum, {survival['classical_mixture'] * 100:.1f}% control. "
            f"Paired delay {delay['mean']:+.2f} steps (SE {delay['se']:.2f}).")


def order_effect_hint():
    """The order-effect line for the config screen, computed from the mind, never typed in."""
    try:
        from mind.quantum_mind import order_gap_at_lambda
    except ImportError:
        return "  * Order Effect: unavailable without the mind package."
    state = SurvivalAgent().get_state()
    coherent, control = (abs(order_gap_at_lambda(state, lam=lam)) for lam in (0.0, 1.0))
    return (f"  * Order Effect: From the default start, [Tremor -> Gas] and [Gas -> Tremor] differ in "
            f"P(protect) by {coherent:.2f} at λ=0, against {control:.2f} at λ=1.")


# -----------------------------------------------------------------------------
# Configuration & High-Resolution Display Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
MAP_SIZE = 900
GRID_DIM = 40
TILE_SIZE = MAP_SIZE / GRID_DIM  # 22.5 px per tile
FPS = 60

# Palette Definitions - Clash of Clans / Hay Day Tactile Village & Island Game Palette
COLOR_BG = (62, 40, 22)           # Carved Oak & Warm Timber Backdrop
COLOR_PANEL_BG = (250, 239, 212)  # Sunlit Cream Parchment Card Surface
COLOR_PANEL_ALT = (234, 216, 178) # Recessed Sand-Parchment Sub-panel
COLOR_CARD_BORDER = (106, 64, 28) # Chunky Carved Walnut Frame
COLOR_CARD_HOVER = (224, 148, 24) # Royal Trophy Gold Highlight

COLOR_TEXT_MAIN = (54, 32, 14)    # Deep Espresso Timber Ink (High contrast on parchment)
COLOR_TEXT_MUTED = (78, 48, 20)   # Warm Chestnut Brown
COLOR_TEXT_HINT = (92, 58, 26)    # Caramel Wood Grain

# Supercell Village & Elixir Accents
COLOR_GREEN = (62, 168, 32)       # Clash Emerald / Hay Day Meadow Green
COLOR_GREEN_DARK = (30, 96, 16)   # Deep Orchard Canopy
COLOR_CYAN = (10, 96, 146)        # Crystal Lagoon / Elixir Blue
COLOR_CYAN_LIGHT = (88, 192, 242) # Sparkling Spring Water
COLOR_PURPLE = (146, 58, 196)     # Quantum Elixir Amethyst
COLOR_PURPLE_LIGHT = (182, 108, 226)
COLOR_YELLOW = (138, 80, 4)       # Clash Gold Coin Amber
COLOR_RED = (172, 34, 26)         # Dragon Fire Ruby
COLOR_BLUE = (44, 108, 184)       # Royal Banner Blue
COLOR_ORANGE = (224, 96, 24)      # Harvest Pumpkin / Lava Ember
COLOR_GOLD = (132, 76, 4)         # Royal Trophy Gold

# Tile Base Colors - Hay Day / Clash of Clans Lush Island Diorama
TILE_COLORS = {
    0: (48, 168, 214),   # Sparkling Turquoise Lagoon
    1: (122, 196, 64),   # Sunlit Village Meadow Lawn
    2: (58, 152, 38),    # Lush Orchard & Pine Canopy
    3: (146, 132, 116),  # Stepped Highland Stone Crag
    4: (212, 82, 42)     # Cozy Red-Roofed Village Hut
}

ACTION_COLORS = {
    "forage": (62, 168, 32),         # Harvest Green
    "drink": (28, 146, 208),         # Crystal Spring Blue
    "build_shelter": (212, 118, 34), # Carpenter Gold-Timber
    "rest": (146, 58, 196),          # Elixir Amethyst
    "explore": (218, 134, 14),       # Compass Gold
    "craft": (118, 96, 76),          # Blacksmith Iron-Wood
    "hide": (212, 48, 38)            # Red Alert Shield
}

ISLAND_PRESETS = [
    {"label": "Island Seed 101", "seed": 101, "tag": "All minds survive", "color": COLOR_GREEN},
    {"label": "Island Seed 105", "seed": 105, "tag": "All minds survive", "color": COLOR_ORANGE},
    {"label": "Island Seed 202", "seed": 202, "tag": "All minds survive", "color": COLOR_PURPLE},
    {"label": "Island Seed 777", "seed": 777, "tag": "All minds die", "color": COLOR_CYAN}
]

TITANIC_PRESETS = [
    {"label": "Third-Class Passenger", "seed": 105, "tag": "Far from the boats | Lower decks", "color": COLOR_CYAN},
    {"label": "First-Class Passenger", "seed": 106, "tag": "Near the boat deck | Upper decks", "color": COLOR_GOLD},
    {"label": "Server / Steward", "seed": 107, "tag": "Warns the cabins | Works the corridors", "color": COLOR_PURPLE},
    {"label": "Evacuation Worker", "seed": 108, "tag": "Loads the lifeboats | Told early", "color": COLOR_RED}
]

POMPEII_PRESETS = [
    {"label": "Resident", "seed": 105, "tag": "Follow a resident | Random panels", "color": COLOR_CYAN},
    {"label": "Enslaved Person", "seed": 106, "tag": "Follow an enslaved person | Random panels", "color": COLOR_PURPLE},
    {"label": "Merchant", "seed": 107, "tag": "Follow a merchant | Random panels", "color": COLOR_GREEN},
    {"label": "Council Member", "seed": 108, "tag": "Follow a council member | Random panels", "color": COLOR_GOLD}
]
POMPEII_SETTINGS = (  # (key, label, options); each changes results, so each is visible before launch
    # The first option in each row is the default, so B comes first: the user's chosen mapping.
    ("event_mapping", "Mapping", ("B", "C", "D", "A")), ("population", "People", (11_500, 20_000)),
    ("date", "Date", ("august", "autumn")), ("quake", "Quake", (True, False)),
    ("restrict_enslaved", "Enslaved held", (False, True)), ("crowding", "Crowding", (True, False)),
)

WATERLOO_PRESETS = [
    {"label": "Child", "seed": 104, "tag": "Follow a child | Random panels", "color": COLOR_GOLD},
    {"label": "Adult", "seed": 105, "tag": "Follow an adult | Random panels", "color": COLOR_CYAN},
    {"label": "Lifeguard or Instructor", "seed": 106, "tag": "Follow a lifeguard | Random panels", "color": COLOR_RED},
    {"label": "Front Desk or Maintenance", "seed": 107, "tag": "Follow front desk staff | Random panels", "color": COLOR_GREEN}
]
WATERLOO_SETTINGS = (  # first option is the default; A is the user's chosen mapping
    ("event_mapping", "Mapping", ("A", "B", "C")), ("population", "People", (100, 40, 300)),
    ("leak_site", "Leak", ("pool_side", "north_end", "deck")), ("source_ppm", "Source ppm", (22.0, 11.0, 110.0)),
    ("leak_minutes", "Leak min", (15.0, 5.0, 60.0)), ("alarm", "Alarm", (True, False)),
)
CROWD_SCENARIOS = ("pompeii", "waterloo")
TITANIC_DEFAULT_MAPPING = "default"
# What the panels call the mind's seven actions: each engine's own words, so no island concept reaches a ship.
ACTION_NAMES = {"titanic": TITANIC_ACTION_LABELS, "pompeii": POMPEII_ACTION_LABELS, "waterloo": WATERLOO_ACTION_LABELS}

VOLCANO_PRESETS = [
    {"label": "Event Seed 101", "seed": 101, "tag": "Erupts at +20 h | First flow +30 h", "color": COLOR_CYAN},
    {"label": "Event Seed 105", "seed": 105, "tag": "No eruption | Unrest fades", "color": COLOR_ORANGE},
    {"label": "Event Seed 202", "seed": 202, "tag": "No eruption | Unrest fades", "color": COLOR_PURPLE},
    {"label": "Event Seed 777", "seed": 777, "tag": "Erupts at +36 h | First flow +46 h", "color": COLOR_RED}
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

        dy = 2 if self.is_pressed else 0
        draw_rect = pygame.Rect(self.rect.x, self.rect.y + dy, self.rect.width, self.rect.height)

        # Determine button fill & 3D bottom bevel color (Supercell chunky tactile style)
        if self.is_active:
            bg = (
                max(60, min(255, int(self.active_color[0] * 0.22 + 248 * 0.78))),
                max(60, min(255, int(self.active_color[1] * 0.22 + 236 * 0.78))),
                max(60, min(255, int(self.active_color[2] * 0.22 + 202 * 0.78))),
            )
            border = self.active_color
            lip_col = (max(0, border[0] - 45), max(0, border[1] - 45), max(0, border[2] - 45))
            border_w = 3
        elif self.is_hovered:
            bg = (min(255, self.bg_color[0] + 12), min(255, self.bg_color[1] + 10), min(255, self.bg_color[2] + 8))
            border = COLOR_CARD_HOVER
            lip_col = (138, 84, 18)
            border_w = 2
        else:
            bg = self.bg_color
            border = self.border_color
            lip_col = (max(0, bg[0] - 55), max(0, bg[1] - 50), max(0, bg[2] - 45))
            border_w = 2

        # 1. Chunky 3D bottom bevel lip
        if not self.is_pressed:
            lip_rect = pygame.Rect(self.rect.x, self.rect.y + 3, self.rect.width, self.rect.height)
            pygame.draw.rect(surface, lip_col, lip_rect, border_radius=10)

        # 2. Main button body & top glossy specular strip
        pygame.draw.rect(surface, bg, draw_rect, border_radius=10)
        gloss_h = max(4, draw_rect.height // 2 - 2)
        gloss_surf = pygame.Surface(( max(1, draw_rect.width - 8), gloss_h), pygame.SRCALPHA)
        gloss_surf.fill((255, 255, 255, 65))
        surface.blit(gloss_surf, (draw_rect.x + 4, draw_rect.y + 3))
        pygame.draw.rect(surface, border, draw_rect, border_w, border_radius=10)

        # Click ripple flash
        if self.ripple_timer > 0:
            alpha = int((self.ripple_timer / 0.25) * 90)
            rip_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            rip_surf.fill((255, 255, 255, alpha))
            surface.blit(rip_surf, (draw_rect.x, draw_rect.y))

        # Auto-contrast text color (bright cream text on dark/vivid action buttons, espresso ink on parchment)
        lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
        txt_col = (255, 250, 238) if lum < 155 else COLOR_TEXT_MAIN
        icon_col = (255, 240, 190) if lum < 155 else (self.active_color if self.is_active else border)

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
                draw_vector_icon(surface, self.icon, content_x, content_y + (txt_surf.get_height() - icon_sz) // 2, icon_sz, icon_col)
                tx = content_x + icon_sz + 8
            else:
                tx = content_x
            surface.blit(txt_surf, (tx, content_y))

            sub_col = self.active_color if self.is_active else ((245, 230, 200) if lum < 155 else COLOR_TEXT_MUTED)
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
                draw_vector_icon(surface, self.icon, content_x, icon_y, icon_sz, icon_col)
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
                 start_screen: str = "event_choice", scenario: str = "volcano", builder_factory=None):
        setup_dpi_awareness()
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Qognition")

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
        self.canvas = UICanvas((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False

        # Fonts: Authentic Engineered / Field Simulation Typography
        # Uses Bahnschrift (DIN-spec engineering font) with clean fallbacks
        self.font_hero = ScaledFont("bahnschrift, trebuchetms, segoeui", 26, bold=True)
        self.font_title = ScaledFont("bahnschrift, trebuchetms, segoeui", 19, bold=True)
        self.font_sub = ScaledFont("bahnschrift, trebuchetms, segoeui", 15, bold=True)
        self.font_body = ScaledFont("segoeuivariable, segoeui, calibri, arial", 14)
        self.font_small = ScaledFont("segoeuivariable, segoeui, calibri, arial", 13)
        self.font_mono = ScaledFont("cascadiamono, consolas, courier", 13)
        self.font_bubble = ScaledFont("segoeui, calibri", 13, bold=True)

        # Simulation Parameters
        self.app_state = start_screen   # "event_choice", "home", "sim"
        self.scenario = scenario         # "island" or "volcano"
        self.seed = seed
        self.mind_type = mind_type.lower()
        self.noise_source = noise_source
        self.max_steps = self._horizon_for(scenario)
        self.cutscene = self._cutscene_player(scenario)
        self.pompeii_settings = {key: options[0] for key, _, options in POMPEII_SETTINGS}
        self.waterloo_settings = {key: options[0] for key, _, options in WATERLOO_SETTINGS}
        self.titanic_mapping = TITANIC_DEFAULT_MAPPING
        self.last_mouse = (0, 0)
        self.quantum_panel = QuantumPanel()
        self.paired = PairedResult()
        self.report_dir = DEFAULT_DIR
        self.report_status, self.report_thread = "", None
        self._worker, self._worker_result = None, None
        self.city_view, self.split_panels, self.show_split_panels = None, None, True
        self.custom_game = None  # A scenario file being played. None means one of the built-in scenarios.
        self.before_custom_game = (seed, self.mind_type)  # Put back on leaving it.
        self.builder = None
        self.builder_factory = builder_factory  # Handed in by main.py, so this package never depends on the physics engine.
        self.notice = ""
        self.step_speed = 0.4
        self.speed_choices = [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
        self.speed_multiplier = 1.0
        self.auto_step_timer = 0.0
        self.bob_phase = 0.0
        self.is_paused = False
        self.video_recorder = None

        # Build Interactive Buttons
        self._build_event_choice_buttons()
        self._build_home_buttons()
        self._build_sim_buttons()

        # Overlays
        self.show_evacuation_map = True
        self.show_history_overlay = False
        self.show_debrief_modal = False

        # Visual Systems
        self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
        self.weather = WeatherSystem((MAP_SIZE, MAP_SIZE))
        self.char_bob = 0.0
        self.bubble_text = ""
        self.bubble_timer = 0.0
        self.selected_tile: Optional[Tuple[int, int]] = None

        # Initialize Simulation Engine (sets initial character position accurately per scenario)
        self._init_simulation()

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
        if self.scenario == "titanic":
            return mini_map(ShipWorld(seed=seed), size)
        if self.scenario == "pompeii":
            return city_mini_map(CityWorld(seed=seed), size)
        if self.scenario == "waterloo":
            return site_mini_map(SiteWorld(seed=seed), size)
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
        c1_x, c2_x, c3_x, c4_x = 26, 416, 806, 1196
        card_w, card_y, card_h = 378, 112, 628
        btn_y = card_y + card_h - 66
        btn_w = card_w - 70

        self.card1_rect = pygame.Rect(c1_x, card_y, card_w, card_h)
        self.card2_rect = pygame.Rect(c2_x, card_y, card_w, card_h)
        self.card3_rect = pygame.Rect(c3_x, card_y, card_w, card_h)
        self.card4_rect = pygame.Rect(c4_x, card_y, card_w, card_h)

        self.btn_choice_island = UIButton(
            (c1_x + 35, btn_y, btn_w, 48),
            "ISLAND SURVIVAL  >>", self.font_sub,
            bg_color=(56, 158, 28), active_color=COLOR_GREEN, icon="tree"
        )
        self.btn_choice_volcano = UIButton(
            (c2_x + 35, btn_y, btn_w, 48),
            "VOLCANO EVACUATION  >>", self.font_sub,
            bg_color=(214, 78, 24), active_color=COLOR_ORANGE, icon="volcano"
        )
        self.btn_choice_titanic = UIButton(
            (c3_x + 35, btn_y, btn_w, 48),
            "TITANIC EVACUATION  >>", self.font_sub,
            bg_color=(28, 84, 148), active_color=COLOR_BLUE, icon="launch"
        )
        self.btn_choice_pompeii = UIButton(
            (c4_x + 35, btn_y, btn_w, 48),
            "POMPEII EVACUATION  >>", self.font_sub,
            bg_color=(140, 66, 40), active_color=COLOR_RED, icon="volcano"
        )
        # The bottom row is shared: the Waterloo banner on the left, the scenario builder on the right.
        self.card5_rect = pygame.Rect(26, 752, 1010, 84)
        self.btn_choice_waterloo = UIButton(
            (self.card5_rect.right - btn_w - 24, 770, btn_w, 48),
            "WATERLOO LEAK  >>", self.font_sub,
            bg_color=(70, 120, 60), active_color=COLOR_GREEN, icon="launch"
        )
        self.card_build_rect = pygame.Rect(self.card5_rect.right + 16, 752, WINDOW_WIDTH - 26 - self.card5_rect.right - 16, 84)
        self.btn_choice_build = UIButton(
            (self.card_build_rect.centerx - 230, 770, 460, 48),
            "BUILD YOUR OWN SCENARIO  >>", self.font_sub,
            bg_color=(146, 58, 196), active_color=COLOR_PURPLE, icon="menu"
        )

    def _presets(self):
        return {"volcano": VOLCANO_PRESETS, "titanic": TITANIC_PRESETS, "pompeii": POMPEII_PRESETS, "waterloo": WATERLOO_PRESETS}.get(self.scenario, ISLAND_PRESETS)

    @staticmethod
    def _horizon_for(scenario):
        return {"titanic": TITANIC_STEPS, "pompeii": POMPEII_STEPS, "waterloo": WATERLOO_STEPS}.get(scenario, DEFAULT_STEPS)

    def _cutscene_player(self, scenario):
        player = {"pompeii": PompeiiCutscenes, "waterloo": WaterlooCutscenes}.get(scenario, CutscenePlayer)
        return player(self.font_hero, self.font_small)

    def _scenario_settings(self):
        if self.scenario == "waterloo":
            return WATERLOO_SETTINGS, self.waterloo_settings
        return POMPEII_SETTINGS, self.pompeii_settings

    def _setting_text(self, key, label):
        value = self._scenario_settings()[1][key]
        if isinstance(value, bool):
            value = "On" if value else "Off"
        elif isinstance(value, int):
            value = f"{value:,}"
        elif isinstance(value, float):
            value = f"{value:g}"
        return f"{label}: {str(value).replace('_', ' ').capitalize()}"

    def _build_pompeii_setting_buttons(self, top_y, col2_x):
        """Replaces the step-length row: Pompeii always runs its whole 32-hour timeline.
        event_mapping keeps its slot in the list, but its selector is the cue translation row."""
        self.step_buttons = []
        rows = self._scenario_settings()[0]
        shown = [key for key, _, _ in rows if key != "event_mapping"]
        width = (1046 - 9 * (len(shown) - 1)) // len(shown)
        for key, label, _ in rows:
            slot = shown.index(key) if key in shown else 0
            rect = (col2_x + 24 + slot * (width + 9), top_y + 333, width, 40)
            self.step_buttons.append(UIButton(rect, self._setting_text(key, label), self.font_small, active_color=COLOR_CYAN))

    def _visible_step_buttons(self):
        """(index, button) pairs for the settings row, leaving out the mapping."""
        if self.scenario not in CROWD_SCENARIOS:
            return list(enumerate(self.step_buttons))
        rows = self._scenario_settings()[0]
        return [(i, b) for i, b in enumerate(self.step_buttons) if rows[i][0] != "event_mapping"]

    def _cue_rows(self):
        return CUE_TRANSLATIONS.get(self.scenario, ())

    def _current_mapping(self):
        if self.scenario == "titanic":
            return self.titanic_mapping
        if self.scenario in CROWD_SCENARIOS:
            return self._scenario_settings()[1]["event_mapping"]
        return None

    def _set_mapping(self, value):
        if self.scenario == "titanic":
            self.titanic_mapping = value
        else:
            self._scenario_settings()[1]["event_mapping"] = value

    def _build_cue_buttons(self, col2_x, y):
        self.cue_buttons = []
        for i, (letter, value, _text) in enumerate(self._cue_rows()):
            button = UIButton((col2_x + 276 + i * 58, y, 50, 36), letter, self.font_sub, active_color=COLOR_ORANGE)
            button.mapping_value = value
            self.cue_buttons.append(button)

    def _cycle_pompeii_setting(self, index):
        rows, values = self._scenario_settings()
        key, label, options = rows[index]
        current = options.index(values[key])
        values[key] = options[(current + 1) % len(options)]
        self.step_buttons[index].text = self._setting_text(key, label)

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

        # 1. Mind Toggle Cards (3-Way Comparative Architecture)
        mind_card_w = 338
        self.btn_mind_quantum = UIButton(
            (col2_x + 24, top_y + 34, mind_card_w, 76), "2-Qubit Quantum Mind", self.font_title,
            subtext="Non-commuting rotations, stress dephasing",
            subfont=self.font_small, active_color=COLOR_PURPLE, icon="quantum"
        )
        self.btn_mind_mixture = UIButton(
            (col2_x + 378, top_y + 34, mind_card_w, 76), "Classical Mixture Control", self.font_title,
            subtext="Same gates, with all coherence removed (λ=1)",
            subfont=self.font_small, active_color=COLOR_CYAN, icon="quantum"
        )
        self.btn_mind_classical = UIButton(
            (col2_x + 732, top_y + 34, mind_card_w, 76), "Classical Rational Mind", self.font_title,
            subtext="Deterministic utility from hand-set weights",
            subfont=self.font_small, active_color=COLOR_BLUE, icon="classical"
        )

        # 2. Preset Buttons (2x2 Grid)
        card_w = 515
        self.preset_buttons: List[UIButton] = []
        p_y = top_y + 150
        presets = self._presets()
        for i, preset in enumerate(presets):
            px = col2_x + 24 + (i % 2) * 531
            py = p_y + (i // 2) * 54
            btn = UIButton((px, py, card_w, 48), preset["label"], self.font_sub,
                           subtext=preset["tag"], subfont=self.font_small, active_color=preset["color"])
            self.preset_buttons.append(btn)

        # 3. Seed Steppers
        s_y = top_y + 256
        self.btn_seed_m100 = UIButton((col2_x + 24, s_y, 65, 38), "-100", self.font_body)
        self.btn_seed_m10 = UIButton((col2_x + 95, s_y, 55, 38), "-10", self.font_body)
        self.btn_seed_m1 = UIButton((col2_x + 156, s_y, 45, 38), "-1", self.font_body)
        self.btn_seed_p1 = UIButton((col2_x + 575, s_y, 45, 38), "+1", self.font_body)
        self.btn_seed_p10 = UIButton((col2_x + 626, s_y, 55, 38), "+10", self.font_body)
        self.btn_seed_p100 = UIButton((col2_x + 687, s_y, 65, 38), "+100", self.font_body)
        rand_label = "Random Island" if self.scenario == "island" else "Random Events"
        self.btn_seed_rand = UIButton((col2_x + 768, s_y, 270, 38), rand_label, self.font_sub,
                                      active_color=COLOR_YELLOW, icon="random")

        # 4. Step Number Buttons
        self.step_buttons: List[UIButton] = []
        step_choices = [6, 12, 24, 36]  # The engine stops at 36 steps.
        st_y = top_y + 333
        btn_w = 250
        for i, steps in enumerate(step_choices):
            sx = col2_x + 24 + i * (btn_w + 15)
            span = f"{steps * 5} min" if self.scenario == "titanic" else f"{steps*2}h"
            btn = UIButton((sx, st_y, btn_w, 40), f"{steps} Steps ({span})", self.font_sub, active_color=COLOR_CYAN)
            self.step_buttons.append(btn)

        launch_text = f"LAUNCH {self.scenario.upper()} SIMULATION"
        if self.scenario in CROWD_SCENARIOS:
            self._build_pompeii_setting_buttons(top_y, col2_x)
        self._build_cue_buttons(col2_x, top_y + 389)

        # 5. Launch Button
        self.btn_launch = UIButton(
            (col2_x + 24, top_y + 443, 1046, 58), launch_text, self.font_hero,
            bg_color=(56, 164, 28), active_color=COLOR_GREEN, icon="launch"
        )
        self.btn_hero_launch = self.btn_launch

    def _build_sim_buttons(self):
        # Map view top navigation bar buttons
        self.btn_nav_home = UIButton((10, 10, 82, 32), "Menu", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="menu")
        self.btn_nav_pause = UIButton((97, 10, 82, 32), "Pause", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_YELLOW, icon="pause")
        self.btn_nav_step = UIButton((184, 10, 78, 32), "Step >", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_GREEN, icon="step")
        self.btn_nav_speed = UIButton((267, 10, 114, 32), "Speed 1.0x", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="speed")
        self.btn_nav_mind = UIButton((386, 10, 104, 32), "Quantum", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_PURPLE, icon="quantum")
        self.btn_nav_evac = UIButton((495, 10, 94, 32), "Evac (E)", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_ORANGE, icon="shield")
        self.btn_nav_log = UIButton((594, 10, 98, 32), "Log (Tab)", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="log")
        self.btn_nav_rec = UIButton((697, 10, 94, 32), "Record", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_RED, icon="play")
        self.btn_nav_fs = UIButton((796, 10, 94, 32), "Full", self.font_small, bg_color=COLOR_PANEL_ALT, active_color=COLOR_CYAN, icon="fullscreen")

        # Quantum panel. Position matches draw_dashboard's fourth widget.
        self.btn_order_swap = UIButton((1458, 633, 104, 32), "Swap cues", self.font_small, bg_color=COLOR_PANEL_BG, active_color=COLOR_PURPLE)

        # Debrief modal buttons
        mx = WINDOW_WIDTH // 2
        my = WINDOW_HEIGHT // 2
        self.btn_modal_replay = UIButton((mx - 405, my + 256, 146, 46), "Replay Run", self.font_sub, bg_color=(36, 138, 198), active_color=COLOR_CYAN, icon="replay")
        self.btn_modal_switch = UIButton((mx - 250, my + 256, 166, 46), "Compare Mind", self.font_sub, bg_color=(138, 56, 186), active_color=COLOR_PURPLE, icon="compare")
        self.btn_modal_report = UIButton((mx - 75, my + 256, 170, 46), "Export Report", self.font_sub, bg_color=(30, 120, 70), active_color=COLOR_GREEN, icon="log")
        self.btn_modal_scenario = UIButton((mx + 104, my + 256, 176, 46), "Change Scenario", self.font_sub, bg_color=(214, 96, 28), active_color=COLOR_ORANGE, icon="menu")
        self.btn_modal_home = UIButton((mx + 289, my + 256, 116, 46), "Settings", self.font_sub, bg_color=(112, 74, 38), active_color=COLOR_CARD_HOVER, icon="home")
        self.btn_modal_close = UIButton((mx + 390, my - 316, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

        # History log modal close
        self.btn_hist_close = UIButton((WINDOW_WIDTH // 2 + 500, 45, 34, 34), "X", self.font_title, bg_color=COLOR_PANEL_BG)

    def _init_simulation(self):
        self._finish_worker()
        if self.custom_game is not None:
            self.engine = self.custom_game.simulation(self.mind_type)
            self.max_steps = self.engine.pack.time.n
        else:
            engine_class = {"titanic": TitanicSimulation, "pompeii": PompeiiSimulation, "waterloo": WaterlooSimulation}.get(self.scenario, SimulationEngine)
            extra = dict(self._scenario_settings()[1]) if self.scenario in CROWD_SCENARIOS else {}
            if self.scenario == "titanic":
                extra["event_mapping"] = self.titanic_mapping
            self.engine = engine_class(
                seed=self.seed,
                mind_type=self.mind_type,
                noise_source=self.noise_source,
                scenario=self.scenario,
                **extra
            )
        self.world = self.engine.world
        self.agent = self.engine.agent
        self.event_gen = self.engine.event_gen
        self.decide_fn = self.engine.decide_fn
        self.ship_view = ShipView(self) if self.scenario == "titanic" else None
        self.city_view = {"pompeii": CityView, "waterloo": SiteView}[self.scenario](self) if self.scenario in CROWD_SCENARIOS else None
        self.split_panels = {"pompeii": SplitPanels, "waterloo": SitePanels}[self.scenario](self.engine) if self.scenario in CROWD_SCENARIOS else None
        self.show_split_panels = True
        wanted_player = {"pompeii": PompeiiCutscenes, "waterloo": WaterlooCutscenes}.get(self.scenario, CutscenePlayer)
        if type(self.cutscene) is not wanted_player:
            enabled = self.cutscene.enabled
            self.cutscene = wanted_player(self.font_hero, self.font_small)
            self.cutscene.enabled = enabled
        self.cutscene.reset()
        self.quantum_panel.reset()
        self._report_cache = None
        self.report_status = ""
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
        view = self.ship_view or self.city_view
        if view is not None:
            self.char_screen_x, self.char_screen_y = view.focus_xy(self.engine)
        else:
            self.char_screen_x = (self.agent.pos[0] + 0.5) * TILE_SIZE
            self.char_screen_y = (self.agent.pos[1] + 0.5) * TILE_SIZE
        self.char_target_x = self.char_screen_x
        self.char_target_y = self.char_screen_y
        if hasattr(self, "weather"):
            self.weather.particles.clear()

    def step_forward(self):
        """Advances the simulation by one 2-hour step."""
        if self.scenario == "titanic":
            return self._titanic_step_forward()
        if self.scenario in CROWD_SCENARIOS:
            return self._pompeii_start_step()
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
        self.quantum_panel.record(record.get("state"))

        # Smooth avatar position target
        self.char_target_x = self.agent.pos[0] * TILE_SIZE + TILE_SIZE / 2
        self.char_target_y = self.agent.pos[1] * TILE_SIZE + TILE_SIZE / 2

        # Particles & Thought bubble
        self.weather.add_action_particles(self.char_screen_x, self.char_screen_y, action)
        reason = record.get("reason", "")
        self.bubble_text = action.replace("_", " ").capitalize()
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

    def _titanic_step_forward(self):
        """One five-minute step for everyone aboard; the panels follow the focused person."""
        if self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            return
        record = self.engine.step()
        if record is None:
            self.show_debrief_modal = True
            return
        self.step_idx += 1
        self.current_event = record["event"]
        self.current_weather = "calm"
        self.current_decision = record
        self._sync_titanic_focus()
        self.weather.add_action_particles(self.char_screen_x, self.char_screen_y, record["action"])
        self.bubble_text = record["action_label"]
        self.bubble_timer = 2.8
        self.quantum_panel.record(record.get("state"))
        if self.step_idx >= self.max_steps:
            self.show_debrief_modal = True

    def _pompeii_start_step(self):
        """Compute the next step on a separate thread, so the window keeps drawing."""
        if self._worker is not None:
            return
        if self.step_idx >= self.max_steps:
            self.show_debrief_modal = True
            return
        engine = self.engine

        def work():
            self._worker_result = (engine, engine.step())

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _pompeii_poll_step(self):
        """Show a finished background step. Called from the main loop."""
        if self._worker is None or self._worker.is_alive():
            return
        self._worker = None
        engine, record = self._worker_result
        if engine is not self.engine:
            return
        if record is None:
            self.show_debrief_modal = True
            return
        self.step_idx += 1
        self.current_event = record["event"]
        self.current_weather = "calm"
        self.current_decision = record
        self._sync_titanic_focus()
        self.bubble_text = record["action_label"]
        self.bubble_timer = 2.8
        self.quantum_panel.record(record.get("state"))
        if self.step_idx >= self.max_steps:
            self.show_debrief_modal = True

    def _finish_worker(self):
        """Wait for any running step before the simulation is replaced."""
        if getattr(self, "_worker", None) is not None:
            self._worker.join()
            self._worker = None

    def _sync_titanic_focus(self):
        """Point the panels at the followed person and rebuild their personal log."""
        self.agent = self.engine.agent
        log = self.agent.log if self.scenario == "titanic" else self.engine.logs.get(self.agent.id, [])
        self.history = [{"t": r["t"] + 1, "state": r["state"], "event": r["event"], "action": r["action"],
                         "decision": r, "narrative": r["reason"]} for r in log]
        self.history_scroll = max(0, len(self.history) - 16)
        if log:
            self.current_decision = log[-1]
            self.current_event = log[-1]["event"]
        view = self.ship_view or self.city_view
        self.char_target_x, self.char_target_y = view.focus_xy(self.engine)

    def _follow(self, person):
        self.engine.set_focus(person)
        self._sync_titanic_focus()
        self.bubble_text = person.label
        self.bubble_timer = 2.8

    def handle_event(self, event, v_mouse: Optional[Tuple[int, int]] = None) -> bool:
        if v_mouse is None:
            v_mouse = self.get_virtual_mouse_pos()
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.DROPFILE:
            self.open_sim(event.file)
            return True

        if self.cutscene.active and (event.type == pygame.KEYDOWN or
                                     (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
            self.cutscene.skip()
            return True

        elif event.type == pygame.VIDEORESIZE:
            if not self.is_fullscreen:
                self.window_w, self.window_h = max(800, event.w), max(450, event.h)
                self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

        elif self.app_state == "builder" and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL) and getattr(event, "key", None) != pygame.K_F11:
            self.builder.handle_event(event, v_mouse)

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
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    self._handle_event_choice_click(self.btn_choice_titanic.rect.center)
                elif event.key in (pygame.K_4, pygame.K_KP4):
                    self._handle_event_choice_click(self.btn_choice_pompeii.rect.center)
                elif event.key in (pygame.K_5, pygame.K_KP5):
                    self._handle_event_choice_click(self.btn_choice_waterloo.rect.center)
                elif event.key in (pygame.K_6, pygame.K_KP6, pygame.K_b):
                    self._handle_event_choice_click(self.btn_choice_build.rect.center)
            elif self.app_state == "home" and event.key == pygame.K_RETURN:
                self._handle_home_click(self.btn_launch.rect.center)
            elif self.app_state == "sim" and event.key == pygame.K_r:
                self._init_simulation()
            elif self.app_state == "sim" and event.key == pygame.K_h:
                self.app_state = self._menu_state()
            elif self.app_state == "sim" and event.key == pygame.K_p and self.custom_game is not None:
                self._next_person()
            elif event.key == pygame.K_f and self.app_state == "sim" and self.scenario in ("titanic", "pompeii", "waterloo"):
                self._follow({"pompeii": next_role_citizen, "waterloo": next_role_patron}.get(self.scenario, next_role_person)(self.engine))
            elif event.key == pygame.K_m and self.app_state == "sim" and self.scenario == "pompeii":
                self.city_view.toggle()
            elif event.key == pygame.K_p and self.app_state == "sim" and self.scenario in CROWD_SCENARIOS:
                self.show_split_panels = not self.show_split_panels
            elif event.key == pygame.K_SPACE and self.app_state == "sim":
                self.is_paused = not self.is_paused
            elif event.key in (pygame.K_RIGHT, pygame.K_n) and self.app_state == "sim":
                self.step_forward()
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_LEFTBRACKET) and self.app_state == "sim":
                self._shift_speed(-1)
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_RIGHTBRACKET) and self.app_state == "sim":
                self._shift_speed(1)
            elif event.key == pygame.K_v and self.app_state == "sim":
                self._toggle_video_recording()
            elif event.key == pygame.K_k and self.app_state == "sim" and self.show_debrief_modal:
                self.export_report()
            elif event.key == pygame.K_k and self.app_state == "sim":
                self._export_current_data()
            elif event.key == pygame.K_q and self.app_state in ("sim", "home"):
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
                    self.app_state = self._menu_state()
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

    def _shift_speed(self, delta: int):
        """Shifts speed_multiplier down into Slow-Mo (0.1x..0.5x) or up into Fast-Forward (2.0x..8.0x)."""
        speeds = self.speed_choices
        curr_idx = speeds.index(self.speed_multiplier) if self.speed_multiplier in speeds else 3
        new_idx = max(0, min(len(speeds) - 1, curr_idx + delta))
        self.speed_multiplier = speeds[new_idx]
        self.bubble_text = f"Time Speed: {self.speed_multiplier:g}x ({'SLOW-MO' if self.speed_multiplier < 1.0 else ('FAST-FWD' if self.speed_multiplier > 1.0 else 'NORMAL')})"
        self.bubble_timer = 1.8

    def _toggle_video_recording(self):
        """Starts or stops live MP4 video recording of the simulation canvas."""
        from engine.exporter import LiveVideoRecorder
        if self.video_recorder is not None and self.video_recorder.active:
            saved = self.video_recorder.stop()
            self.video_recorder = None
            self.bubble_text = f"Saved video: {os.path.basename(saved)}"
            self.bubble_timer = 3.0
        else:
            out_file = os.path.join(
                "exports", "videos",
                f"{self.scenario}_seed{self.seed}_{self.mind_type}_{int(time.time())}.mp4"
            )
            self.video_recorder = LiveVideoRecorder(out_file, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, fps=FPS)
            self.video_recorder.start()
            self.bubble_text = f"Recording MP4: {os.path.basename(out_file)}"
            self.bubble_timer = 2.5

    def _export_current_data(self):
        """Exports the current simulation timeline and evacuation survival dataset."""
        from engine.exporter import export_evacuation_datasets
        os.makedirs("exports", exist_ok=True)
        if hasattr(self.engine, "timeline"):
            tl_path = os.path.join("exports", f"timeline_{self.scenario}_seed{self.seed}_{self.mind_type}.json")
            with open(tl_path, "w", encoding="utf-8") as f:
                json.dump(self.engine.timeline(), f, indent=2)
        export_evacuation_datasets(output_dir="exports", num_seeds=5)
        self.bubble_text = "Exported survival & policy data to exports/"
        self.bubble_timer = 3.0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            sim_dt = dt * self.speed_multiplier

            # Auto-stepping during unpaused simulation (scaled by Slow-Mo / Fast-Forward multiplier)
            self.cutscene.update(sim_dt)
            if self.scenario in CROWD_SCENARIOS:
                self._pompeii_poll_step()
            if self.app_state == "sim" and not self.is_paused and not self.show_debrief_modal and not self.show_history_overlay \
                    and not self.cutscene.active:
                self.auto_step_timer += sim_dt
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

            # Character Smooth Interpolation (Lerp scaled by sim_dt for Slow-Mo & Fast-Forward)
            lerp_alpha = min(1.0, 12.0 * sim_dt)
            self.char_screen_x += (self.char_target_x - self.char_screen_x) * lerp_alpha
            self.char_screen_y += (self.char_target_y - self.char_screen_y) * lerp_alpha
            self.bob_phase += 8.0 * sim_dt
            self.char_bob = math.sin(self.bob_phase) * 2.0

            if self.bubble_timer > 0:
                self.bubble_timer = max(0.0, self.bubble_timer - dt)

            ash_level = getattr(self.world, "ash", 0.0)
            self.weather.update(self.current_event, sim_dt, ash_level=ash_level)

            # Render Scene
            self.draw(v_mouse)
            if self.video_recorder is not None and self.video_recorder.active:
                self.video_recorder.capture_surface(self.recording_frame())
            self.present()

        if self.video_recorder is not None and self.video_recorder.active:
            self.video_recorder.stop()
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
            if self.btn_choice_titanic.check_hover(pos) or self.card3_rect.collidepoint(pos):
                return True
            if self.btn_choice_pompeii.check_hover(pos) or self.card4_rect.collidepoint(pos):
                return True
            if self.btn_choice_waterloo.check_hover(pos) or self.card5_rect.collidepoint(pos):
                return True
            if self.btn_choice_build.check_hover(pos) or (hasattr(self, 'card_build_rect') and self.card_build_rect.collidepoint(pos)):
                return True
            return self.btn_choice_island.check_hover(pos) or self.btn_choice_volcano.check_hover(pos) or c1_h or c2_h

        elif self.app_state == "home":
            btns = [
                self.btn_home_back_scenario, self.btn_home_fs,
                self.btn_mind_quantum, self.btn_mind_mixture, self.btn_mind_classical,
                self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1,
                self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100, self.btn_seed_rand,
                self.btn_launch
            ] + self.preset_buttons + [b for _, b in self._visible_step_buttons()] + self.cue_buttons
            for btn in btns:
                hovered = btn.check_hover(pos) or hovered
            return hovered

        elif self.app_state == "sim":
            if self.show_debrief_modal:
                return (self.btn_modal_replay.check_hover(pos) or self.btn_modal_switch.check_hover(pos) or self.btn_modal_report.check_hover(pos) or
                        self.btn_modal_scenario.check_hover(pos) or self.btn_modal_home.check_hover(pos) or
                        self.btn_modal_close.check_hover(pos))
            if self.show_history_overlay:
                return self.btn_hist_close.check_hover(pos)

            nav_btns = [
                self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step,
                self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_evac,
                self.btn_nav_log, self.btn_nav_rec, self.btn_nav_fs
            ]
            for btn in nav_btns:
                hovered = btn.check_hover(pos) or hovered
            return hovered

        elif self.app_state == "builder":
            return self.builder.hover(pos)

        return False

    def present(self):
        """Scales shapes to the window and renders text at its final size."""
        compose(self.canvas, self.screen)
        pygame.display.flip()

    def recording_frame(self):
        """The finished 1600x900 frame, text included, for the video recorder."""
        frame = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        compose(self.canvas, frame)
        return frame

    def _handle_mouse_click(self, pos: Tuple[int, int]):
        """Dispatches mouse clicks according to the active app state."""
        if self.app_state == "event_choice":
            self._handle_event_choice_click(pos)
        elif self.app_state == "home":
            self._handle_home_click(pos)
        elif self.app_state == "sim":
            self._handle_sim_click(pos)

    def _menu_state(self) -> str:
        """Where the menu buttons lead: a scenario file came from the builder, so they go back there."""
        return "builder" if self.custom_game is not None else "home"

    def _leave_custom_game(self):
        if self.custom_game is not None:
            self.custom_game, self.max_steps = None, DEFAULT_STEPS
            self.seed, self.mind_type = self.before_custom_game
            self._show_mind_on_button()

    def open_sim(self, source):
        """A sim file or link, from dropping a file on the window or from --open."""
        self._open_builder()
        if self.app_state == "builder":
            self.builder.open_source(source)

    def _open_builder(self):
        if self.builder_factory is None:
            self.notice = "The builder isn't available here. Start the game with: python main.py --gui"
            return
        try:
            if self.builder is None:
                self.builder = self.builder_factory(self)
        except ImportError as error:
            self.notice = f"The builder needs requirements-physics.txt installed: {error}"
            return
        except Exception as error:  # The original scenarios must stay playable whatever is wrong with the builder's files.
            self.notice = f"The builder couldn't start: {error}"
            return
        self.notice = ""
        self.app_state = "builder"

    def _follow_person(self):
        """Starts the person the game is following, with the mind the scenario gave them."""
        self.mind_type = self.custom_game.person.mind
        self._show_mind_on_button()
        self._init_simulation()

    def _show_mind_on_button(self):
        names = {"quantum": ("Quantum", COLOR_PURPLE), "classical_mixture": ("Mixture", COLOR_CYAN), "classical": ("Classical", COLOR_BLUE)}
        self.btn_nav_mind.text, self.btn_nav_mind.active_color = names[self.mind_type]

    def start_custom_game(self, game):
        """Plays a scenario the builder has built."""
        if self.custom_game is None:
            self.before_custom_game = (self.seed, self.mind_type)
        self.custom_game, self.scenario, self.seed = game, "volcano", game.pack.seed
        self._follow_person()
        self.app_state = "sim"

    def _next_person(self):
        self.custom_game.next_person()
        self._follow_person()

    def _handle_event_choice_click(self, pos: Tuple[int, int]):
        if self.btn_choice_build.check_hover(pos):
            self._open_builder()
            return
        c1_hit = self.btn_choice_island.check_hover(pos) or (hasattr(self, 'card1_rect') and self.card1_rect.collidepoint(pos))
        c2_hit = self.btn_choice_volcano.check_hover(pos) or (hasattr(self, 'card2_rect') and self.card2_rect.collidepoint(pos))
        c3_hit = self.btn_choice_titanic.check_hover(pos) or self.card3_rect.collidepoint(pos)
        c4_hit = self.btn_choice_pompeii.check_hover(pos) or self.card4_rect.collidepoint(pos)
        c5_hit = self.btn_choice_waterloo.check_hover(pos) or self.card5_rect.collidepoint(pos)
        if c1_hit or c2_hit or c3_hit or c4_hit or c5_hit:
            self._leave_custom_game()
            self.max_steps = self._horizon_for("titanic" if c3_hit else "pompeii" if c4_hit else "waterloo" if c5_hit else "other")
        if c5_hit:
            self.scenario = "waterloo"
            self._build_home_buttons()
            self._init_simulation()
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            self.app_state = "home"
        elif c4_hit:
            self.scenario = "pompeii"
            self._build_home_buttons()
            self._init_simulation()
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            self.app_state = "home"
        elif c3_hit:
            self.scenario = "titanic"
            self._build_home_buttons()
            self._init_simulation()
            self.preview_mini_map = self._generate_mini_map(self.seed, size=300)
            self.app_state = "home"
        elif c1_hit:
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
            self._show_mind_on_button()
            self.btn_mind_quantum.trigger_click()
            return
        if self.btn_mind_mixture.check_hover(pos):
            self.mind_type = "classical_mixture"
            self._show_mind_on_button()
            self.btn_mind_mixture.trigger_click()
            return
        if self.btn_mind_classical.check_hover(pos):
            self.mind_type = "classical"
            self._show_mind_on_button()
            self.btn_mind_classical.trigger_click()
            return

        presets = self._presets()
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

        for button in self.cue_buttons:
            if button.check_hover(pos):
                self._set_mapping(button.mapping_value)
                button.trigger_click()
                return

        step_choices = [6, 12, 24, 36]  # The engine stops at 36 steps.
        for i, btn in self._visible_step_buttons():
            if btn.check_hover(pos):
                if self.scenario in CROWD_SCENARIOS:
                    self._cycle_pompeii_setting(i)
                else:
                    self.max_steps = step_choices[i]
                btn.trigger_click()
                return

        if self.btn_launch.check_hover(pos):
            self._init_simulation()
            self.app_state = "sim"

    def _handle_sim_click(self, pos: Tuple[int, int]):
        if self.show_debrief_modal:
            if self.btn_modal_report.check_hover(pos):
                self.export_report()
                self.btn_modal_report.trigger_click()
            elif self.btn_modal_replay.check_hover(pos):
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_switch.check_hover(pos):
                self._toggle_mind()
                self._init_simulation()
                self.show_debrief_modal = False
            elif self.btn_modal_scenario.check_hover(pos):
                self.app_state = "event_choice"
            elif self.btn_modal_home.check_hover(pos) or self.btn_modal_close.check_hover(pos):
                self.app_state = self._menu_state()
            return

        if self.show_history_overlay:
            if self.btn_hist_close.check_hover(pos):
                self.show_history_overlay = False
            return

        if self.btn_nav_home.check_hover(pos):
            self.app_state = self._menu_state()
        elif self.btn_nav_pause.check_hover(pos):
            self.is_paused = not self.is_paused
            self.btn_nav_pause.trigger_click()
        elif self.btn_nav_step.check_hover(pos):
            self.step_forward()
            self.btn_nav_step.trigger_click()
        elif self.btn_nav_speed.check_hover(pos):
            speeds = self.speed_choices
            curr_idx = speeds.index(self.speed_multiplier) if self.speed_multiplier in speeds else 3
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
        elif self.btn_nav_rec.check_hover(pos):
            self._toggle_video_recording()
            self.btn_nav_rec.trigger_click()
        elif self.btn_nav_fs.check_hover(pos):
            self.toggle_fullscreen()
            self.btn_nav_fs.trigger_click()
        elif self._quantum_panel_visible() and self.btn_order_swap.check_hover(pos):
            self.quantum_panel.swap()
            self.btn_order_swap.trigger_click()

        # Map tile click inspector
        elif pos[0] < MAP_SIZE and pos[1] >= 52 and self.scenario == "titanic":
            person = self.ship_view.pick_person(self.engine, pos, max(0, self.step_idx - 1))
            if person is not None:
                self._follow(person)
        elif pos[0] < MAP_SIZE and pos[1] >= 52 and self.scenario in CROWD_SCENARIOS:
            person = self.city_view.pick_person(self.engine, pos)
            if person is not None:
                self.split_panels.replace(person)
                self._follow(person)
        elif pos[0] < MAP_SIZE and pos[1] >= 52:
            tx = int(pos[0] / TILE_SIZE)
            ty = int(pos[1] / TILE_SIZE)
            if 0 <= tx < GRID_DIM and 0 <= ty < GRID_DIM:
                self.selected_tile = (tx, ty)

    def draw(self, mouse_pos: Tuple[int, int] = (0, 0)):
        self.canvas.begin_frame(window_fit(*self.screen.get_size())[0])
        self.last_mouse = mouse_pos
        if self.app_state == "event_choice":
            self.draw_event_choice_screen(mouse_pos)
        elif self.app_state == "home":
            self.draw_home_screen(mouse_pos)
        elif self.app_state == "sim":
            self.draw_sim_screen(mouse_pos)
            self.cutscene.draw(self.canvas)
        elif self.app_state == "builder":
            self.builder.draw(mouse_pos)
            if self.app_state == "sim":  # The build finished this frame.
                self.draw_sim_screen(mouse_pos)

    # -------------------------------------------------------------------------
    # Render Event Choice Screen (State 0) - Tactical Research Dossier Style
    # -------------------------------------------------------------------------
    def draw_event_choice_screen(self, mouse_pos: Tuple[int, int]):
        self.canvas.fill(COLOR_BG)

        # Supercell-Style Golden Wood Ribbon Header
        header_y = 18
        rib_rect = pygame.Rect(WINDOW_WIDTH // 2 - 390, header_y, 780, 74)
        pygame.draw.rect(self.canvas, (94, 54, 22), (rib_rect.x, rib_rect.y + 4, rib_rect.width, rib_rect.height), border_radius=14)
        pygame.draw.rect(self.canvas, (244, 188, 58), rib_rect, border_radius=14)
        pygame.draw.rect(self.canvas, (118, 68, 24), rib_rect, 3, border_radius=14)
        title_surf = self.font_hero.render("QOGNITION", True, (58, 32, 10))
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, header_y + 9))

        sub_str = "QUANTUM AGAINST CLASSICAL MINDS IN AN EVACUATION  •  A MODEL, NOT A PREDICTION"
        sub_surf = self.font_sub.render(sub_str, True, (72, 42, 12))
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, header_y + 44))

        # 1px Subtle divider line
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (170, header_y + 70), (WINDOW_WIDTH - 170, header_y + 70), 1)

        # Scenario Cards Setup
        c1_x, c2_x, c3_x, c4_x = 26, 416, 806, 1196
        card_w, c_y, card_h = 378, 112, 628
        for x, card in zip((c1_x, c2_x, c3_x, c4_x), self._hub_cards()):
            self._draw_scenario_card(x, c_y, card_w, card_h, mouse_pos, **card)
        self._draw_waterloo_banner(mouse_pos)
        self._draw_build_card(mouse_pos)

        # -------------------------------------------------------------
        # Footer Technical Shortcut Bar
        # -------------------------------------------------------------
        footer_w, footer_h = 1120, 34
        footer_x = (WINDOW_WIDTH - footer_w) // 2
        footer_y = WINDOW_HEIGHT - 54
        foot_rect = pygame.Rect(footer_x, footer_y, footer_w, footer_h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, foot_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, foot_rect, 1, border_radius=4)

        tip_str = "[ 1 ] Island   [ 2 ] Volcano   [ 3 ] Titanic   [ 4 ] Pompeii   [ 5 ] Waterloo   [ B ] Build   [ F11 ] Fullscreen"
        hint_surf = self.font_mono.render(tip_str, True, COLOR_TEXT_HINT)
        self.canvas.blit(hint_surf, (footer_x + (footer_w - hint_surf.get_width()) // 2, footer_y + (footer_h - hint_surf.get_height()) // 2))

    def _draw_waterloo_banner(self, mouse_pos: Tuple[int, int]):
        rect = self.card5_rect
        hover = rect.collidepoint(mouse_pos) or self.btn_choice_waterloo.check_hover(mouse_pos)
        self.draw_card(rect.x, rect.y, rect.width, rect.height, border_color=COLOR_GREEN if hover else COLOR_CARD_BORDER, border_width=1)
        self.draw_badge(rect.x + 24, rect.y + 12, "LOCAL: WATERLOO, ONTARIO", COLOR_GREEN)
        self.canvas.blit(self.font_sub.render("MOSES SPRINGER CHLORINE LEAK", True, COLOR_TEXT_MAIN), (rect.x + 290, rect.y + 16))
        text_width = self.btn_choice_waterloo.rect.x - rect.x - 48
        render_wrapped_text(self.canvas, "A hypothetical evacuation at a real site. Most details of the 30 July 2012 leak are unknown, so the leak and head-count are labelled settings.",
                            self.font_small, COLOR_TEXT_MUTED, rect.x + 24, rect.y + 42, text_width, line_spacing=2, max_lines=2)
        self.btn_choice_waterloo.check_hover(mouse_pos)
        self.btn_choice_waterloo.draw(self.canvas)

    def _draw_build_card(self, mouse_pos: Tuple[int, int]):
        rect = self.card_build_rect
        hover = self.btn_choice_build.check_hover(mouse_pos)
        self.draw_card(rect.x, rect.y, rect.width, rect.height, border_color=COLOR_PURPLE if hover else COLOR_CARD_BORDER, border_width=1)
        self.btn_choice_build.draw(self.canvas)
        if self.notice:
            render_wrapped_text(self.canvas, self.notice, self.font_small, COLOR_RED, rect.x + 16, rect.bottom - 18, rect.width - 32, line_spacing=2, max_lines=1)

    def _hub_cards(self):
        return (
            dict(badge="SECTOR 01: ARCHIPELAGO", color=COLOR_GREEN_DARK, title="ISLAND WILDERNESS", rect=self.card1_rect, button=self.btn_choice_island,
                 subtitle="Procedural terrain  •  Resources  •  Shelter",
                 shows="The baseline: one person, everyday needs, and no crowd.",
                 desc="A generated island. One survivor balances food, water and warmth against storms and animals, gathering timber to build a shelter before the cold nights.",
                 specs=(("Grid", "40 × 40 cells, 250 m each", COLOR_CYAN), ("Terrain", "Forest, streams, peaks", COLOR_GREEN_DARK),
                        ("Hazards", "Storms, cold nights, animals", COLOR_YELLOW), ("Mind", "2-qubit belief interference", COLOR_PURPLE))),
            dict(badge="SECTOR 02: CALDERA", color=COLOR_ORANGE, title="VOLCANO EVACUATION", rect=self.card2_rect, button=self.btn_choice_volcano,
                 subtitle="Fictional island  •  Unrest  •  Emergency routes",
                 shows="Cue order and stress change when the person leaves.",
                 desc="A fictional volcano enters unrest. The person must read tremor and gas signs, avoid lava and ash, and walk the routes to the coastal assembly points.",
                 specs=(("Grid", "40 × 40 cells, assumed rates", COLOR_CYAN), ("Routes", "Valleys to coastal assembly", COLOR_ORANGE),
                        ("Hazards", "Lava, ash, flows, lahars", COLOR_RED), ("Mind", "Stress as dephasing", COLOR_PURPLE))),
            dict(badge="HISTORICAL: APRIL 1912", color=COLOR_BLUE, title="TITANIC EVACUATION", rect=self.card3_rect, button=self.btn_choice_titanic,
                 subtitle="Flooding  •  Lifeboats  •  Whole crowd",
                 shows="One mind, with deck position setting who hears what, and when.",
                 desc="Everyone aboard shares one mind. Each person hears different warnings in a different order, while water climbs through the hull and lifeboats leave at their recorded times.",
                 specs=(("People", "2,208 with crew roles", COLOR_CYAN), ("Lifeboats", f"20 boats, {TOTAL_SEATS:,} seats", COLOR_ORANGE),
                        ("Time step", "5 minutes, 23:30 to 03:30", COLOR_RED), ("Mind", "Same mind for everyone", COLOR_PURPLE))),
            dict(badge="HISTORICAL: AD 79", color=COLOR_RED, title="POMPEII EVACUATION", rect=self.card4_rect, button=self.btn_choice_pompeii,
                 subtitle="Two maps  •  Pumice and flows  •  Split screens",
                 shows="How far deaths move with the cue translation you assume.",
                 desc="A whole town shares one mind. News spreads by distance, chance and household servants while pumice builds on the roofs. The default settings overstate escape.",
                 specs=(("People", "11,500, or 20,000", COLOR_CYAN), ("Maps", "City, and region to Vesuvius", COLOR_ORANGE),
                        ("Time step", "15 minutes, about 32 hours", COLOR_RED), ("Mind", "Same mind for everyone", COLOR_PURPLE))),
        )

    def _draw_scenario_card(self, x, y, w, h, mouse_pos, badge, color, title, rect, button, subtitle, desc, specs, shows):
        """One hub card. Each block starts where the last one ended, so longer text cannot collide."""
        hover = rect.collidepoint(mouse_pos) or button.check_hover(mouse_pos)
        self.draw_card(x, y, w, h, border_color=color if hover else COLOR_CARD_BORDER, border_width=1)
        inner_x, inner_w = x + 26, w - 52
        self.draw_badge(inner_x, y + 22, badge, color)
        cursor = y + 60
        self.canvas.blit(self.font_title.render(title, True, COLOR_TEXT_MAIN), (inner_x, cursor))
        cursor += self.font_title.get_height() + 6
        self.canvas.blit(self.font_small.render(subtitle, True, COLOR_TEXT_MUTED), (inner_x, cursor))
        cursor += self.font_small.get_height() + 12
        pygame.draw.line(self.canvas, COLOR_CARD_BORDER, (x + 22, cursor), (x + w - 22, cursor), 1)
        cursor += 16
        block_top = cursor
        for line in wrap_text(desc, self.font_body, inner_w):
            self.canvas.blit(self.font_body.render(line, True, COLOR_TEXT_MUTED), (inner_x, cursor))
            cursor += self.font_body.get_height() + 7
        cursor = max(cursor, block_top + 4 * (self.font_body.get_height() + 7)) + 18
        self.canvas.blit(self.font_sub.render("TECHNICAL SPECIFICATIONS", True, COLOR_GOLD), (inner_x, cursor))
        cursor += self.font_sub.get_height() + 12
        for label, value, dot_color in specs:
            pygame.draw.circle(self.canvas, dot_color, (inner_x + 6, cursor + 9), 4)
            self.canvas.blit(self.font_sub.render(label, True, COLOR_TEXT_MAIN), (inner_x + 20, cursor))
            self.canvas.blit(self.font_body.render(value, True, COLOR_TEXT_MUTED), (inner_x + 112, cursor))
            cursor += 32
        cursor += 14
        self.canvas.blit(self.font_sub.render("WHAT THIS ONE SHOWS", True, COLOR_GOLD), (inner_x, cursor))
        cursor += self.font_sub.get_height() + 10
        for line in wrap_text(shows, self.font_body, inner_w):
            self.canvas.blit(self.font_body.render(line, True, COLOR_TEXT_MAIN), (inner_x, cursor))
            cursor += self.font_body.get_height() + 7
        button.check_hover(mouse_pos)
        button.draw(self.canvas)

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

        # Header Ribbon
        rib_rect = pygame.Rect(WINDOW_WIDTH // 2 - 410, 12, 820, 72)
        pygame.draw.rect(self.canvas, (94, 54, 22), (rib_rect.x, rib_rect.y + 4, rib_rect.width, rib_rect.height), border_radius=12)
        pygame.draw.rect(self.canvas, (244, 188, 58), rib_rect, border_radius=12)
        pygame.draw.rect(self.canvas, (118, 68, 24), rib_rect, 3, border_radius=12)
        title_surf = self.font_hero.render("QOGNITION", True, (58, 32, 10))
        self.canvas.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 17))

        scen_tag = {"volcano": "VOLCANO ERUPTION EVACUATION", "titanic": "TITANIC EVACUATION, APRIL 1912",
                    "pompeii": "POMPEII EVACUATION, AD 79", "waterloo": "WATERLOO CHLORINE LEAK (HYPOTHETICAL)"}.get(self.scenario, "ISLAND WILDERNESS SURVIVAL")
        sub_str = f"{scen_tag}  •  A MODEL, NOT A PREDICTION"
        sub_surf = self.font_sub.render(sub_str, True, (72, 42, 12))
        self.canvas.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 52))

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
        legend_text = {"pompeii": "Walled town. Each gate leads on to the region map", "waterloo": "Real outlines. Doors, fence and inside are assumed"}.get(self.scenario, "Red dot: where the person starts")
        leg_surf = self.font_small.render(legend_text, True, COLOR_TEXT_MUTED)
        self.canvas.blit(leg_surf, (col1_x + 50, leg_y))

        # Terrain Statistics
        stat_y = col1_y + 400
        stats_box = pygame.Rect(col1_x + 20, stat_y, col1_w - 40, 335)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, stats_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, stats_box, 1, border_radius=8)

        if self.scenario == "pompeii":
            temp_w = CityWorld(seed=self.seed)
        elif self.scenario == "waterloo":
            temp_w = SiteWorld(seed=self.seed)
        else:
            temp_w = ShipWorld(seed=self.seed) if self.scenario == "titanic" else IslandWorld(width=GRID_DIM, height=GRID_DIM, seed=self.seed, scenario=self.scenario)
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
        if self.scenario == "titanic":
            lines = [
                f"Active Seed:      #{self.seed}",
                "Grid Geometry:    40x40 Ship Cutaway",
                "People Aboard:    2,208",
                f"Lifeboat Seats:   {TOTAL_SEATS:,}",
                "Compartments:     6 of 16 Breached",
                "Time Span:        23:30 to 03:30",
                "Scenario Horizon: TITANIC",
                "Contract Engine:  contracts.py (Frozen)"
            ]
        if self.scenario == "pompeii":
            lines = [
                f"Active Seed:      #{self.seed}",
                "Grid Geometry:    Two 40x40 Maps",
                f"People:           {self.pompeii_settings['population']:,}",
                "Gates:            7",
                f"Event Mapping:    {self.pompeii_settings['event_mapping']}",
                "Time Span:        About 32 Hours",
                "Scenario Horizon: POMPEII",
                "Contract Engine:  contracts.py (Frozen)"
            ]
        if self.scenario == "waterloo":
            lines = [
                f"Active Seed:      #{self.seed}",
                "Grid Geometry:    40x40, 5 m per tile",
                f"People:           {self.waterloo_settings['population']}",
                f"Leak:             {self.waterloo_settings['leak_site'].replace('_', ' ').capitalize()}",
                f"Event Mapping:    {self.waterloo_settings['event_mapping']}",
                "Time Span:        Up to 2 Hours",
                "Scenario Horizon: WATERLOO",
                "Contract Engine:  contracts.py (Frozen)"
            ]
        for i, line in enumerate(lines):
            col = COLOR_CYAN if i == 0 else (COLOR_GREEN_DARK if i in (2, 3) else COLOR_TEXT_MUTED)
            self.canvas.blit(self.font_mono.render(line, True, col), (stats_box.x + 18, stats_box.y + 16 + i * 38))

        # Right Configuration Card (1088 x 760)
        col2_x = 480
        col2_y = 96
        col2_w = 1088
        col2_h = 760
        self.draw_card(col2_x, col2_y, col2_w, col2_h)

        # 1. Decision Mind Selection
        m_lbl = self.font_title.render("1. Select Cognitive Mind Model", True, COLOR_TEXT_MAIN)
        self.canvas.blit(m_lbl, (col2_x + 24, col2_y + 14))

        self.btn_mind_quantum.is_active = (self.mind_type == "quantum")
        self.btn_mind_mixture.is_active = (self.mind_type == "classical_mixture")
        self.btn_mind_classical.is_active = (self.mind_type == "classical")
        self.btn_mind_quantum.check_hover(mouse_pos)
        self.btn_mind_mixture.check_hover(mouse_pos)
        self.btn_mind_classical.check_hover(mouse_pos)
        self.btn_mind_quantum.draw(self.canvas)
        self.btn_mind_mixture.draw(self.canvas)
        self.btn_mind_classical.draw(self.canvas)

        # 2. Presets & Custom Stepper
        preset_title = "2. Select Scenario Preset or Custom Seed"
        p_lbl = self.font_title.render(preset_title, True, COLOR_TEXT_MAIN)
        self.canvas.blit(p_lbl, (col2_x + 24, col2_y + 140))

        presets = self._presets()
        for i, p_btn in enumerate(self.preset_buttons):
            p_btn.is_active = (self.seed == presets[i]["seed"])
            p_btn.check_hover(mouse_pos)
            p_btn.draw(self.canvas)

        seed_box = pygame.Rect(col2_x + 215, col2_y + 275, 345, 38)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, seed_box, border_radius=6)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, seed_box, 1, border_radius=6)
        seed_txt = self.font_title.render(f"Simulation Seed:  #{self.seed}", True, COLOR_YELLOW)
        self.canvas.blit(seed_txt, (seed_box.x + (seed_box.width - seed_txt.get_width()) // 2, seed_box.y + 6))

        for s_btn in (self.btn_seed_m100, self.btn_seed_m10, self.btn_seed_m1, self.btn_seed_p1, self.btn_seed_p10, self.btn_seed_p100, self.btn_seed_rand):
            s_btn.check_hover(mouse_pos)
            s_btn.draw(self.canvas)

        # 3. Simulation Duration
        step_length = "5 Minutes" if self.scenario == "titanic" else "2 Hours"
        st_text = "3. Scenario Settings (Each One Changes Results)" if self.scenario in CROWD_SCENARIOS else f"3. Simulation Step Horizon ({step_length} per Turn)"
        st_lbl = self.font_title.render(st_text, True, COLOR_TEXT_MAIN)
        self.canvas.blit(st_lbl, (col2_x + 24, col2_y + 322))

        step_choices = [6, 12, 24, 36]  # The engine stops at 36 steps.
        for i, st_btn in self._visible_step_buttons():
            st_btn.is_active = self.scenario not in CROWD_SCENARIOS and (self.max_steps == step_choices[i])
            st_btn.check_hover(mouse_pos)
            st_btn.draw(self.canvas)

        # 4. Hero Launch Button
        self.btn_launch.check_hover(mouse_pos)
        self.btn_launch.draw(self.canvas)

        # Quick Reference Hints
        self._draw_cue_row(mouse_pos, col2_x, col2_y)
        hints_box = pygame.Rect(col2_x + 24, col2_y + 536, 1046, 208)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, hints_box, border_radius=8)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, hints_box, 1, border_radius=8)

        h_title = self.font_sub.render("HOW THIS RUN WORKS", True, COLOR_CYAN)
        self.canvas.blit(h_title, (hints_box.x + 18, hints_box.y + 10))

        bullet_lines = [
            "  * Quantum Mind: Belief states represented as 2-qubit amplitudes with non-commuting projection angles.",
            order_effect_hint(),
            "  * Stress Model: Physiological stress maps to a simulated dephasing channel (stress model); no hardware decoherence is driven live.",
            "  * Survival: Without water, death comes at about 58 h. All rates are assumed. Maintain shelter to reduce exposure."
        ]
        if self.scenario == "titanic":
            bullet_lines = [
                "  * Same Mind: All 2,208 aboard run the same unedited mind. Role and class are never passed to it.",
                "  * Perception: Collision shudder, steward knocks, rockets, trim and rising water reach people by deck and position.",
                "  * Lifeboats: 20 boats (1,178 seats) launch on Wormstedt's schedule; boarding follows port/starboard rules.",
                "  * Historical Context: 712 of 2,208 survived historically. See docs/TITANIC_MODEL.md."
            ]
        if self.scenario == "pompeii":
            bullet_lines = [
                "  * Same Mind: Everyone uses the same unedited mind. Role and status are never passed to it.",
                "  * News: What people notice depends on distance, being indoors, visibility, chance and household servants.",
                "  * Mapping: The column and falling pumice are translated into the mind's events. Results depend strongly on this.",
                "  * Caution: The default settings overstate escape. A demonstration, not a reconstruction. See docs/POMPEII_SOURCES.md."
            ]
        if self.scenario == "waterloo":
            bullet_lines = [
                "  * Same Mind: Everyone uses the same unedited mind. Role is never passed to it. Each person decides once a minute.",
                "  * Warning: People learn by smell, from people nearby, from others hurrying, and from an alarm a staff member triggers.",
                "  * Exposure: Reported against EPA planning levels. These do not predict injury, and nobody is scripted to die.",
                "  * Caution: A hypothetical at a real site, not a reconstruction. Leak, head-count and inside are assumed. See docs/WATERLOO_SOURCES.md."
            ]
        for i, bl in enumerate(bullet_lines):
            self.canvas.blit(self.font_small.render(bl.strip()[2:], True, COLOR_TEXT_MUTED), (hints_box.x + 18, hints_box.y + 42 + i * 38))

        tip_str = "Press [ENTER] to Launch  |  [F11] Fullscreen  |  [Q] Toggle Mind Model"
        tip_surf = self.font_small.render(tip_str, True, (246, 232, 200))
        self.canvas.blit(tip_surf, (WINDOW_WIDTH // 2 - tip_surf.get_width() // 2, WINDOW_HEIGHT - 28))

    def _draw_cue_row(self, mouse_pos, col2_x, col2_y):
        """The cue translation: an assumption the audience can change, and watch the result move."""
        y = col2_y + 408
        rows = self._cue_rows()
        if not rows:
            note = self.font_small.render("Cue translation: not needed here. These events reach the mind under their own names.", True, COLOR_TEXT_MUTED)
            self.canvas.blit(note, (col2_x + 24, y + 8))
            return
        label = self.font_title.render("4. Cue Translation", True, COLOR_TEXT_MAIN)
        self.canvas.blit(label, (col2_x + 24, y + 4))
        current = self._current_mapping()
        for button in self.cue_buttons:
            button.is_active = button.mapping_value == current
            button.check_hover(mouse_pos)
            button.draw(self.canvas)
        meaning = next(text for _, value, text in rows if value == current)
        note = self.font_small.render(f"Assumption: {meaning}", True, COLOR_TEXT_MUTED)
        self.canvas.blit(note, (col2_x + 24 + 252 + len(rows) * 58 + 16, y + 10))

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
        if self.scenario == "waterloo":
            if self.agent.status == "site":
                self.draw_character()
        elif self.scenario != "pompeii" or self._focus_is_on_shown_map():
            self.draw_character()

        # 4. Top Navigation Bar (Integrated Over Map)
        self.draw_map_navigation_bar(mouse_pos)
        if self.custom_game is not None:
            self.draw_custom_game_label()

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

    def draw_custom_game_label(self):
        game = self.custom_game
        label = f"{game.title}  |  Following {game.person.name} ({game.index + 1} of {len(game.people)})  |  [P] next person"
        shown = self.font_small.render(label, True, COLOR_TEXT_MAIN)
        box = pygame.Rect(14, 56, min(shown.get_width() + 20, MAP_SIZE - 28), 24)
        pygame.draw.rect(self.canvas, (248, 234, 198), box, border_radius=6)
        pygame.draw.rect(self.canvas, (106, 64, 28), box, 2, border_radius=6)
        self.canvas.blit(shown, (box.x + 10, box.y + 4), (0, 0, box.width - 20, shown.get_height()))

    def _focus_is_on_shown_map(self):
        """The followed person's avatar only belongs on the map they are actually on."""
        agent = self.agent
        return agent.is_alive and agent.status == ("road" if self.city_view.show_region else "city")

    def draw_map_navigation_bar(self, mouse_pos: Tuple[int, int]):
        bar_bg = pygame.Surface((MAP_SIZE, 52), pygame.SRCALPHA)
        bar_bg.fill((78, 48, 24, 242))
        self.canvas.blit(bar_bg, (0, 0))
        pygame.draw.line(self.canvas, (228, 174, 58), (0, 50), (MAP_SIZE, 50), 2)
        pygame.draw.line(self.canvas, (52, 30, 14), (0, 52), (MAP_SIZE, 52), 2)

        self.btn_nav_pause.text = "Play" if self.is_paused else "Pause"
        self.btn_nav_pause.icon = "play" if self.is_paused else "pause"

        if self.speed_multiplier < 1.0:
            self.btn_nav_speed.text = f"Slow {self.speed_multiplier:g}x"
            self.btn_nav_speed.active_color = COLOR_CYAN
        elif self.speed_multiplier > 1.0:
            self.btn_nav_speed.text = f"Fast {self.speed_multiplier:g}x"
            self.btn_nav_speed.active_color = COLOR_ORANGE
        else:
            self.btn_nav_speed.text = "Speed 1.0x"
            self.btn_nav_speed.active_color = COLOR_GREEN

        rec_active = self.video_recorder is not None and self.video_recorder.active
        self.btn_nav_rec.text = "Stop Rec" if rec_active else "Rec Video"
        self.btn_nav_rec.is_active = rec_active

        if self.mind_type == "quantum":
            self.btn_nav_mind.text = "Quantum"
            self.btn_nav_mind.icon = "quantum"
            self.btn_nav_mind.active_color = COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            self.btn_nav_mind.text = "Mixture"
            self.btn_nav_mind.icon = "quantum"
            self.btn_nav_mind.active_color = COLOR_CYAN
        else:
            self.btn_nav_mind.text = "Classical"
            self.btn_nav_mind.icon = "classical"
            self.btn_nav_mind.active_color = COLOR_BLUE

        self.btn_nav_fs.text = "Window" if self.is_fullscreen else "Fullscreen"
        self.btn_nav_fs.icon = "windowed" if self.is_fullscreen else "fullscreen"

        for btn in (self.btn_nav_home, self.btn_nav_pause, self.btn_nav_step, self.btn_nav_speed, self.btn_nav_mind, self.btn_nav_evac, self.btn_nav_log, self.btn_nav_rec, self.btn_nav_fs):
            btn.check_hover(mouse_pos)
            btn.draw(self.canvas)

    def draw_island_map(self):
        if self.scenario == "titanic":
            self.ship_view.draw(self)
            return
        if self.scenario in CROWD_SCENARIOS:
            self.city_view.draw(self)
            return
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
                        flow = math.sin(t_time * 3.5 + x * 0.5 + y * 0.5) * 10
                        base = (52, max(150, min(225, 192 + int(flow))), 242)
                        pygame.draw.rect(self.canvas, base, rect)
                        pygame.draw.circle(self.canvas, (225, 248, 255), (rx + rw // 2, ry + rh // 2), 3)
                    else:
                        wave = math.sin(t_time * 2.0 + x * 0.4 + y * 0.4) * 8
                        c = (38, max(135, min(185, int(162 + wave))), 212)
                        pygame.draw.rect(self.canvas, c, rect)
                        if (x + y) % 5 == 0:
                            pygame.draw.line(self.canvas, (145, 222, 248), (rx + 4, ry + rh // 2), (rx + rw - 5, ry + rh // 2), 1)

                elif tile == 1:
                    has_water_adj = any(
                        0 <= x + dx < GRID_DIM and 0 <= y + dy < GRID_DIM and self.world.get_tile(x + dx, y + dy) == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if has_water_adj:
                        # Golden Hay Day / Clash Beach Sand with warm shoreline lip
                        color = (244, 214, 142) if (x + y) % 2 == 0 else (236, 204, 132)
                        speck = (218, 182, 108)
                    else:
                        # Signature Clash of Clans / Hay Day Checkerboard Emerald Meadow
                        color = (126, 202, 68) if (x + y) % 2 == 0 else (114, 190, 58)
                        speck = (96, 168, 44)
                    pygame.draw.rect(self.canvas, color, rect)
                    pygame.draw.circle(self.canvas, speck, (rx + 6, ry + 6), 2)
                    if not has_water_adj and (x * 7 + y * 13) % 11 == 0:
                        # Tiny sunlit village wildflower
                        pygame.draw.circle(self.canvas, (255, 232, 92), (rx + rw - 6, ry + rh - 6), 2)

                elif tile == 2:
                    # Lush Hay Day Puffy Orchard / Pine Tree on Checkerboard Grass
                    grass = (118, 194, 62) if (x + y) % 2 == 0 else (108, 182, 54)
                    pygame.draw.rect(self.canvas, grass, rect)
                    # Drop shadow & trunk
                    pygame.draw.ellipse(self.canvas, (72, 128, 34), (rx + 3, ry + rh - 7, rw - 6, 5))
                    pygame.draw.rect(self.canvas, (124, 76, 36), (rx + rw // 2 - 2, ry + rh - 8, 4, 5))
                    # Layered puffy foliage crowns
                    pygame.draw.circle(self.canvas, (44, 136, 32), (rx + rw // 2, ry + rh // 2), rw // 2 - 2)
                    pygame.draw.circle(self.canvas, (72, 174, 46), (rx + rw // 2 - 1, ry + rh // 2 - 2), rw // 2 - 4)
                    pygame.draw.circle(self.canvas, (112, 208, 72), (rx + rw // 2 - 2, ry + rh // 2 - 4), max(2, rw // 4))
                    if (x, y) in self.world.food_tiles:
                        # Bright ruby & gold harvest fruit clusters
                        pygame.draw.circle(self.canvas, (232, 52, 42), (rx + 6, ry + 7), 3)
                        pygame.draw.circle(self.canvas, (248, 196, 42), (rx + rw - 6, ry + 8), 3)

                elif tile == 3:
                    # 3D Stepped Highland Rock & Terracotta Crag
                    pygame.draw.rect(self.canvas, (102, 168, 52), rect)
                    pygame.draw.rect(self.canvas, (118, 102, 88), (rx + 1, ry + 4, rw - 2, rh - 3), border_radius=4)
                    p1 = (rx + rw // 2, ry + 2)
                    p2 = (rx + 2, ry + rh - 3)
                    p3 = (rx + rw - 2, ry + rh - 3)
                    pygame.draw.polygon(self.canvas, (154, 138, 122), [p1, p2, p3])
                    pygame.draw.polygon(self.canvas, (248, 244, 236), [p1, (rx + rw // 2 - 4, ry + 8), (rx + rw // 2 + 4, ry + 8)])

                elif tile == 4:
                    # Cozy Clash / Hay Day Timber Cottage with Red Tile Roof & Golden Window
                    pygame.draw.rect(self.canvas, (122, 196, 64), rect)
                    pygame.draw.rect(self.canvas, (198, 146, 84), (rx + 3, ry + 8, rw - 6, rh - 10), border_radius=2)
                    pygame.draw.rect(self.canvas, (108, 66, 30), (rx + 3, ry + 8, rw - 6, rh - 10), 1, border_radius=2)
                    p_roof = [(rx + rw // 2, ry + 1), (rx + 1, ry + 10), (rx + rw - 1, ry + 10)]
                    pygame.draw.polygon(self.canvas, (218, 68, 38), p_roof)
                    pygame.draw.polygon(self.canvas, (128, 36, 18), p_roof, 1)
                    ember_glow = int(math.sin(t_time * 5.0) * 20)
                    pygame.draw.rect(self.canvas, (255, max(190, min(245, 220 + ember_glow)), 92), (rx + rw // 2 - 2, ry + 11, 5, 5), border_radius=1)

        # Volcano Caldera & Hazards (if volcano scenario)
        if self.scenario == "volcano":
            if self.world.vent:  # A scenario file may hold no eruption.
                vx, vy = self.world.vent
                vrx = int(vx * TILE_SIZE + TILE_SIZE / 2)
                vry = int(vy * TILE_SIZE + TILE_SIZE / 2)
                pygame.draw.circle(self.canvas, (82, 54, 42), (vrx, vry), 17)
                pygame.draw.circle(self.canvas, (218, 62, 32), (vrx, vry), 11)
                pygame.draw.circle(self.canvas, (255, 196, 48), (vrx, vry), 6)

            # Evacuation Map Overlay
            if self.show_evacuation_map:
                overlay = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                colors = ((62, 168, 32, 28), (228, 152, 24, 42), (218, 52, 38, 62))
                for y, row in enumerate(self.world.zones if self.world.vent else ()):  # Danger zones are measured from the vent.
                    for x, zone in enumerate(row):
                        if self.world.get_tile(x, y):
                            rx = int(round(x * TILE_SIZE))
                            ry = int(round(y * TILE_SIZE))
                            rw = int(round((x + 1) * TILE_SIZE)) - rx
                            rh = int(round((y + 1) * TILE_SIZE)) - ry
                            pygame.draw.rect(overlay, colors[zone], (rx, ry, rw, rh))

                points = [(int(x * TILE_SIZE + TILE_SIZE // 2), int(y * TILE_SIZE + TILE_SIZE // 2)) for x, y in self.world.route_from_spawn]
                if len(points) > 1:
                    pygame.draw.lines(overlay, (255, 238, 120, 230), False, points, 3)

                for x, y in self.world.assembly_points:
                    ax_px = int(x * TILE_SIZE + TILE_SIZE // 2)
                    ay_px = int(y * TILE_SIZE + TILE_SIZE // 2)
                    pygame.draw.circle(overlay, (56, 168, 32), (ax_px, ay_px), 8)
                    pygame.draw.circle(overlay, (255, 244, 198), (ax_px, ay_px), 8, 2)
                    pygame.draw.circle(overlay, (255, 244, 198), (ax_px, ay_px), 3)
                self.canvas.blit(overlay, (0, 0))

            # Active Hazards: Lava, PDC, Lahar
            hazard_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            for x, y in getattr(self.world, "lava", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pulse = math.sin(t_time * 3.5 + x + y) * 18
                pygame.draw.rect(hazard_surf, (238, max(70, min(145, int(105 + pulse))), 24, 190), (rx, ry, rw, rh), border_radius=3)

            for x, y in getattr(self.world, "pdc", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pygame.draw.rect(hazard_surf, (92, 78, 74, 155), (rx, ry, rw, rh))

            for x, y in getattr(self.world, "lahar", set()):
                rx = int(round(x * TILE_SIZE))
                ry = int(round(y * TILE_SIZE))
                rw = int(round((x + 1) * TILE_SIZE)) - rx
                rh = int(round((y + 1) * TILE_SIZE)) - ry
                pygame.draw.rect(hazard_surf, (118, 82, 48, 160), (rx, ry, rw, rh))

            ash_val = getattr(self.world, "ash", 0.0)
            if ash_val > 0.02:
                ash_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
                ash_surf.fill((110, 102, 94, int(65 * ash_val)))
                hazard_surf.blit(ash_surf, (0, 0))

            self.canvas.blit(hazard_surf, (0, 0))

        # Village Wooden Signpost Scale & Compass Overlays
        scale_box = pygame.Rect(14, MAP_SIZE - 34, 156, 24)
        pygame.draw.rect(self.canvas, (248, 234, 198), scale_box, border_radius=6)
        pygame.draw.rect(self.canvas, (106, 64, 28), scale_box, 2, border_radius=6)
        self.canvas.blit(self.font_small.render(f"SCALE: 1 TILE = {getattr(self.world, 'scale_m_per_tile', 250):.0f}m", True, COLOR_TEXT_MAIN), (scale_box.x + 10, scale_box.y + 4))

        comp_box = pygame.Rect(MAP_SIZE - 72, 60, 60, 24)
        pygame.draw.rect(self.canvas, (248, 234, 198), comp_box, border_radius=6)
        pygame.draw.rect(self.canvas, (106, 64, 28), comp_box, 2, border_radius=6)
        self.canvas.blit(self.font_small.render("N  ▲", True, COLOR_TEXT_MAIN), (comp_box.x + 16, comp_box.y + 4))

        if self.selected_tile:
            tx, ty = self.selected_tile
            sx = int(tx * TILE_SIZE)
            sy = int(ty * TILE_SIZE)
            sw = int(TILE_SIZE)
            sh = int(TILE_SIZE)
            s_rect = pygame.Rect(sx, sy, sw, sh)
            pygame.draw.rect(self.canvas, (255, 215, 48), s_rect, 2, border_radius=3)

        pygame.draw.line(self.canvas, (94, 54, 22), (MAP_SIZE, 0), (MAP_SIZE, WINDOW_HEIGHT), 4)

    def draw_atmosphere(self):
        hour = self.agent.hour
        if hour >= 21 or hour <= 5:
            night_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            night_surf.fill((18, 28, 58, 95))
            self.canvas.blit(night_surf, (0, 0))

        if self.current_event == "cold_night":
            frost_surf = pygame.Surface((MAP_SIZE, MAP_SIZE), pygame.SRCALPHA)
            frost_surf.fill((160, 210, 245, 42))
            self.canvas.blit(frost_surf, (0, 0))

        ash_val = getattr(self.world, "ash", 0.0)
        self.weather.draw(self.canvas, self.current_event, ash_level=ash_val)

    def draw_character(self):
        cx, cy = int(self.char_screen_x), int(self.char_screen_y + self.char_bob)

        # Ground Drop Shadow
        shadow_surf = pygame.Surface((28, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 95), (0, 0, 28, 12))
        self.canvas.blit(shadow_surf, (cx - 14, cy + 7))

        # Boots
        pygame.draw.circle(self.canvas, (92, 52, 22), (cx - 4, cy + 8), 3)
        pygame.draw.circle(self.canvas, (92, 52, 22), (cx + 4, cy + 8), 3)

        # Villager Tunic (Royal Blue/Emerald or Ruby when injured) with Gold Belt
        body_color = (48, 136, 214) if not self.agent.injured else (212, 48, 38)
        pygame.draw.rect(self.canvas, body_color, (cx - 7, cy - 7, 14, 14), border_radius=4)
        pygame.draw.rect(self.canvas, (62, 36, 16), (cx - 7, cy - 7, 14, 14), 1, border_radius=4)
        pygame.draw.line(self.canvas, (244, 192, 52), (cx - 6, cy + 1), (cx + 6, cy + 1), 2)

        # Villager Head & Sunlit Straw/Explorer Hat
        pygame.draw.circle(self.canvas, (252, 214, 174), (cx, cy - 12), 7)
        pygame.draw.circle(self.canvas, (82, 48, 22), (cx, cy - 12), 7, 1)
        pygame.draw.circle(self.canvas, (52, 32, 16), (cx - 2, cy - 12), 1)
        pygame.draw.circle(self.canvas, (52, 32, 16), (cx + 2, cy - 12), 1)
        # Hat brim & crown
        pygame.draw.ellipse(self.canvas, (238, 188, 72), (cx - 10, cy - 20, 20, 6))
        pygame.draw.ellipse(self.canvas, (112, 68, 24), (cx - 10, cy - 20, 20, 6), 1)

        # Injury Cross Badge
        if self.agent.injured:
            pygame.draw.circle(self.canvas, COLOR_RED, (cx - 11, cy - 16), 6)
            pygame.draw.line(self.canvas, (255, 255, 255), (cx - 14, cy - 16), (cx - 8, cy - 16), 2)
            pygame.draw.line(self.canvas, (255, 255, 255), (cx - 11, cy - 19), (cx - 11, cy - 13), 2)

        # Shelter Shield Badge
        if self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1]):
            pygame.draw.polygon(self.canvas, COLOR_GREEN, [(cx, cy - 27), (cx - 7, cy - 20), (cx + 7, cy - 20)])

        # Supercell Parchment Speech Bubble
        if self.bubble_timer > 0 and self.bubble_text:
            text_surf = self.font_bubble.render(self.bubble_text, True, COLOR_TEXT_MAIN)
            tw, th = text_surf.get_width() + 20, text_surf.get_height() + 12
            bx = max(10, min(MAP_SIZE - tw - 10, cx - tw // 2))
            by = cy - 54

            b_rect = pygame.Rect(bx, by, tw, th)
            pygame.draw.rect(self.canvas, (252, 244, 220), b_rect, border_radius=8)
            b_border = COLOR_PURPLE if self.mind_type == "quantum" else COLOR_BLUE
            pygame.draw.rect(self.canvas, b_border, b_rect, 2, border_radius=8)
            pygame.draw.polygon(self.canvas, (252, 244, 220), [(cx - 5, by + th), (cx + 5, by + th), (cx, by + th + 6)])
            self.canvas.blit(text_surf, (bx + 10, by + 6))

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
        if self.scenario == "pompeii":
            if self.city_view.show_region:
                return
            tile_name = {0: "Outside or wall", 1: "Street or open", 2: "Garden", 4: "Building"}.get(tile_type, "Unknown")
            desc = f"{round(self.world.elevation[ty][tx])} m above the sea"
        if self.scenario == "waterloo":
            tile_name = "Pool" if (tx, ty) in self.world.pool_tiles else {0: "Creek", 1: "Open ground", 3: "Wall, fence or building", 4: "Indoors"}.get(tile_type, "Unknown")
            desc = f"{self.engine.chlorine.ppm_at(max(0, self.step_idx - 1), (tx, ty)):.2f} ppm chlorine"
        if self.scenario == "titanic":
            tile_name = {0: "Sea or hull", 1: "Open deck", 3: "Stairs", 4: "Interior"}.get(tile_type, "Unknown")
            desc = "Flooded" if (tx, ty) in self.world.flooded else f"{round(self.world.elevation[ty][tx])} m above the sea"
        if self.scenario == "volcano" and hasattr(self.world, "zones"):
            zone_names = {0: "Safe", 1: "Caution", 2: "Danger"}
            desc += f" | Zone: {zone_names.get(self.world.zones[ty][tx], 'Unknown')}"

        tt_str = f"[{tx:02d}, {ty:02d}] {tile_name}  |  {desc}"
        txt_surf = self.font_small.render(tt_str, True, COLOR_TEXT_MAIN)

        tt_w, tt_h = txt_surf.get_width() + 18, txt_surf.get_height() + 10
        tt_x = max(10, min(MAP_SIZE - tt_w - 10, mx + 14))
        tt_y = max(58, min(MAP_SIZE - tt_h - 10, my - 28))

        tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
        self.canvas.cover(tt_rect)
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, tt_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, tt_rect, 1, border_radius=4)
        self.canvas.blit(txt_surf, (tt_x + 9, tt_y + 5))

    def _quantum_panel_visible(self):
        return not (self.scenario in CROWD_SCENARIOS and self.show_split_panels) and not self.show_debrief_modal and not self.show_history_overlay

    def _vitals(self):
        """Six bars that mean something in this scenario. Crowd counts are worked out once per step."""
        needs = self.agent.needs
        if self.scenario not in ACTION_NAMES:
            return [("Hunger", needs["hunger"], COLOR_YELLOW), ("Thirst", needs["thirst"], COLOR_CYAN),
                    ("Warmth", needs["warmth"], COLOR_ORANGE), ("Energy", needs["energy"], COLOR_GREEN),
                    ("Safety", needs["safety"], (110, 126, 148)), ("Morale", needs["morale"], COLOR_PURPLE)]
        cached = getattr(self, "_crowd_bars", None)
        if cached is None or cached[0] != self.step_idx or cached[1] is not self.engine:
            total = max(1, len(self.engine.people))
            counts = self.engine.counts()
            if self.scenario == "titanic":
                boats = self.engine.boats
                used = sum(len(b.aboard) for b in boats.boats + boats.floating)
                bars = [("Seats left", 1 - used / TOTAL_SEATS, COLOR_CYAN), ("Ship afloat", max(0., 1 - self.step_idx / SINK_STEP), COLOR_BLUE)]
            elif self.scenario == "pompeii":
                bars = [("Left town", (counts["on_roads"] + counts["escaped"]) / total, COLOR_CYAN), ("Town alive", 1 - counts["dead"] / total, COLOR_GREEN_DARK)]
            else:
                bars = [("Off site", counts["off_site"] / total, COLOR_CYAN), ("Know of leak", counts["knows"] / total, COLOR_ORANGE)]
            self._crowd_bars = cached = (self.step_idx, self.engine, bars)
        return [("Warmth", needs["warmth"], COLOR_ORANGE), ("Energy", needs["energy"], COLOR_GREEN),
                ("Safety", needs["safety"], (110, 126, 148)), ("Morale", needs["morale"], COLOR_PURPLE)] + cached[2]

    def draw_dashboard(self):
        panel_x = MAP_SIZE + 16
        panel_w = WINDOW_WIDTH - MAP_SIZE - 32
        if self.scenario in CROWD_SCENARIOS and self.show_split_panels:
            self.split_panels.draw(self.canvas, panel_x, 12, panel_w, WINDOW_HEIGHT - 24,
                                   (self.font_title, self.font_body, self.font_small))
            return
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
        if self.scenario == "pompeii":
            step_txt = f"{clock_text(max(0, self.step_idx - 1))}  (Step {self.step_idx}/{self.max_steps})"
        if self.scenario == "waterloo":
            step_txt = f"{site_clock(max(0, self.step_idx - 1))}  (Step {self.step_idx}/{self.max_steps})"
        if self.scenario == "titanic":
            minutes = 23 * 60 + 30 + max(0, self.step_idx - 1) * 5
            step_txt = f"{minutes // 60 % 24:02d}:{minutes % 60:02d} ship's time  (Step {self.step_idx}/{self.max_steps})"
        step_surf = self.font_mono.render(step_txt, True, COLOR_TEXT_MUTED)
        self.canvas.blit(step_surf, (panel_x + panel_w - step_surf.get_width() - 30, curr_y + 12))

        need_items = self._vitals()

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
        if self.scenario == "titanic":
            inv_str = f"{self.agent.label}   |   Lifebelt: {'Yes' if inv.get('lifebelt') else 'No'}"
        if self.scenario == "pompeii":
            inv_str = f"{self.agent.label}   |   Knows of danger: {'Yes' if self.agent.knows_danger else 'No'}"
        if self.scenario == "waterloo":
            inv_str = f"{self.agent.label}   |   Knows of danger: {'Yes' if self.agent.knows_danger else 'No'}"
        self.canvas.blit(self.font_body.render(inv_str, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 185))

        curr_y += card1_h + 12

        # Card 2: Environment Hazard & Chronology (width = 668, height = 135)
        card2_h = 135
        self.draw_card(panel_x, curr_y, panel_w, card2_h)
        header_env = self.font_sub.render("ENVIRONMENTAL HAZARD & EVENT CHRONOLOGY", True, COLOR_YELLOW)
        self.canvas.blit(header_env, (panel_x + 16, curr_y + 12))

        ev_upper = self.current_event.upper()
        if self.scenario == "titanic":
            ev_upper = STORY_TEXT.get(self.agent.story_event, "NOTHING NEW").upper()
        if self.scenario == "pompeii":
            ev_upper = POMPEII_STORY.get(self.agent.story_event, "NOTHING NEW").upper()
        if self.scenario == "waterloo":
            ev_upper = WATERLOO_STORY.get(self.agent.story_event, "NOTHING NEW").upper()
        ev_color = COLOR_RED if ev_upper in ("STORM", "INJURY", "ANIMAL", "ERUPTION") else (COLOR_CYAN if ev_upper in ("COLD_NIGHT", "TREMOR") else COLOR_GREEN)
        hazard_text = f"NOW: {ev_upper}"
        self.draw_badge(panel_x + 16, curr_y + 38, hazard_text, ev_color)
        phase_x = panel_x + 16 + self.font_sub.size(hazard_text)[0] + 40

        if self.scenario in ("volcano", "titanic", "pompeii", "waterloo") and hasattr(self.engine, "volcano"):
            phase = self.engine.volcano.phases[max(0, self.step_idx - 1)]
            phase_col = COLOR_RED if phase == "erupting" else (COLOR_ORANGE if phase == "escalating" else COLOR_GREEN)
            self.draw_badge(phase_x, curr_y + 38, f"PHASE: {phase.upper()}", phase_col)

        px, py = self.agent.pos
        tile_name = contracts.TILE_TYPES.get(self.world.get_tile(px, py), "Unknown").capitalize()
        pos_txt = f"Sector: [{px:02d}, {py:02d}]  |  Biome: {tile_name}  |  Shelter: {'Sheltered' if self.world.is_in_shelter(px, py) else 'Exposed'}"
        if self.scenario == "titanic":
            place = {"boat": f"Lifeboat {self.agent.boat_id}", "water": "In the water"}.get(self.agent.status)
            if place is None:
                deck = next((n.upper() for n, row in DECK_ROWS.items() if row == py), "Stairs")
                place = f"Deck: {deck}"
            pos_txt = f"{place}  |  {self.current_decision.get('action_label', 'Waiting')}"
        if self.scenario == "pompeii":
            place = {"city": "In town", "road": "On the roads", "escaped": "Escaped"}[self.agent.status]
            pos_txt = f"{place}  |  {self.current_decision.get('action_label', 'Waiting')}"
        if self.scenario == "waterloo":
            place = "Off the site" if self.agent.status == "out" else "On the site"
            pos_txt = f"{place}  |  {self.current_decision.get('action_label', 'Waiting')}"
        self.canvas.blit(self.font_body.render(pos_txt, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 72))

        clean_events = [e.upper() for e in self.agent.recent_events if e != "none"] or ["NONE"]
        history_str = " -> ".join(clean_events)
        hist_display = f"Order Effect Chain: [ {history_str} ]"
        if self.scenario == "titanic":
            hist_display = f"Mind Inputs: [ {history_str} ]"
        if self.scenario in CROWD_SCENARIOS:
            hist_display = f"Mind Inputs: [ {history_str} ]"
        max_h_w = panel_w - 32
        if self.font_mono.size(hist_display)[0] > max_h_w:
            while hist_display and self.font_mono.size(hist_display + "... ]")[0] > max_h_w:
                hist_display = hist_display[:-1]
            hist_display = hist_display.rstrip() + "... ]"
        self.canvas.blit(self.font_mono.render(hist_display, True, COLOR_TEXT_MAIN), (panel_x + 16, curr_y + 100))

        curr_y += card2_h + 12

        # Card 3: Quantum Superposition & Probabilities (width = 668, height = 370)
        card3_h = 370  # title row, action row, seven bars, then the widget row
        self.draw_card(panel_x, curr_y, panel_w, card3_h)

        if self.mind_type == "quantum":
            mind_title, mind_col = "2-QUBIT QUANTUM BELIEF STATE", COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            mind_title, mind_col = "CLASSICAL MIXTURE CONTROL (λ=1)", COLOR_CYAN
        else:
            mind_title, mind_col = "CLASSICAL RATIONAL UTILITY", COLOR_BLUE
        self.canvas.blit(self.font_sub.render(mind_title, True, mind_col), (panel_x + 16, curr_y + 12))

        names = ACTION_NAMES.get(self.scenario, {})
        chosen = self.current_decision.get("action", "none")
        chosen_text = self.current_decision.get("action_label") or names.get(chosen, chosen.replace("_", " ")).capitalize()
        self.draw_badge(panel_x + 16, curr_y + 34, f"ACTION: {chosen_text.upper()}", ACTION_COLORS.get(chosen, COLOR_GREEN_DARK))

        q_diag = self.current_decision.get("quantum")
        if q_diag:
            q_str = f"P(danger) {q_diag.get('p_danger',0):.2f}  P(protect) {q_diag.get('p_protect',0):.2f}"
            q_surf = self.font_mono.render(q_str, True, COLOR_TEXT_MUTED)
            self.canvas.blit(q_surf, (panel_x + panel_w - q_surf.get_width() - 30, curr_y + 12))

        probs = self.current_decision.get("probs", {})
        chart_y = curr_y + 68
        label_w = 170 if names else 110
        chart_w = panel_w - label_w - 80
        max_act = max(probs.items(), key=lambda it: it[1])[0] if probs else "none"

        for act in contracts.ACTIONS:
            p = probs.get(act, 0.0)
            act_color = ACTION_COLORS.get(act, COLOR_CYAN)
            label = names.get(act, act.replace("_", " ").capitalize())
            self.canvas.blit(self.font_small.render(label, True, COLOR_GOLD if act == max_act else COLOR_TEXT_MAIN), (panel_x + 16, chart_y - 1))
            bar_x = panel_x + 16 + label_w
            pygame.draw.rect(self.canvas, (68, 42, 22), (bar_x, chart_y + 2, chart_w, 12), border_radius=5)
            fill_w = max(3, int(p * chart_w))
            pygame.draw.rect(self.canvas, act_color, (bar_x, chart_y + 2, fill_w, 12), border_radius=5)
            pct_lbl = self.font_mono.render(f"{p*100:4.1f}%", True, COLOR_TEXT_MUTED)
            self.canvas.blit(pct_lbl, (bar_x + chart_w + 8, chart_y - 1))
            chart_y += 19

        # The paper's claims as pictures: timeline, belief path, stress dial, order swap.
        widget_y, widget_h = curr_y + 204, 158
        x = panel_x + 16
        self.quantum_panel.draw_timeline(self.canvas, pygame.Rect(x, widget_y, 236, widget_h), self.font_small)
        self.quantum_panel.draw_bloch(self.canvas, pygame.Rect(x + 244, widget_y, 136, widget_h), self.font_small)
        self.quantum_panel.draw_dial(self.canvas, pygame.Rect(x + 388, widget_y, 124, widget_h), self.font_small)
        swap_box = pygame.Rect(x + 520, widget_y, 116, widget_h)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, swap_box, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, swap_box, 1, border_radius=4)
        self.canvas.blit(self.font_small.render("Order swap", True, COLOR_TEXT_MAIN), (swap_box.x + 8, swap_box.y + 5))
        self.btn_order_swap.check_hover(self.last_mouse)
        self.btn_order_swap.draw(self.canvas)
        render_wrapped_text(self.canvas, self.quantum_panel.swap_result or "Swap the last two cues and see ΔP.", self.font_small, COLOR_TEXT_MUTED,
                            swap_box.x + 8, swap_box.y + 68, swap_box.width - 14, line_spacing=2, max_lines=4)

        curr_y += card3_h + 12

        # Card 4: Quick Controls Cheat Sheet (width = 668, height = 115)
        card4_h = 115
        self.draw_card(panel_x, curr_y, panel_w, card4_h)
        controls_lbl = self.font_sub.render("SIMULATION SHORTCUTS & INTERACTION CONTROLS", True, COLOR_TEXT_MAIN)
        self.canvas.blit(controls_lbl, (panel_x + 16, curr_y + 12))

        c_line1 = "[SPACE] Play/Pause  |  [-/+] Slow-Mo / Fast-Fwd  |  [RIGHT] Step  |  [F11] Fullscreen"
        c_line2 = "[Q] Switch Mind     |  [V] Rec MP4 Video         |  [K] Export Data |  [TAB] Log"
        self.canvas.blit(self.font_body.render(c_line1, True, COLOR_TEXT_MAIN), (panel_x + 16, curr_y + 44))
        self.canvas.blit(self.font_body.render(c_line2, True, COLOR_TEXT_MUTED), (panel_x + 16, curr_y + 72))

    # -------------------------------------------------------------------------
    # Render End-of-Event Debrief Screen Modal
    # -------------------------------------------------------------------------
    def draw_debrief_modal(self, mouse_pos: Tuple[int, int]):
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((10, 15, 26, 215))
        self.canvas.blit(dim_surf, (0, 0))

        mw, mh = 860, 680
        mx, my = (WINDOW_WIDTH - mw) // 2, (WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)
        survived = self.agent.is_alive
        border_col = COLOR_GOLD if survived else COLOR_RED
        self.draw_card(mx, my, mw, mh, border_color=border_col, border_width=3)

        self._draw_debrief_summary(mx, my, mw, mh)
        if self.scenario == "titanic":
            return self._draw_titanic_debrief(mouse_pos, mx, my, mw, mh, border_col)
        if self.scenario == "pompeii":
            return self._draw_pompeii_debrief(mouse_pos, mx, my, mw, mh, border_col)
        if self.scenario == "waterloo":
            return self._draw_waterloo_debrief(mouse_pos, mx, my, mw, mh, border_col)

        m_title = run_title(self.agent.is_alive, self.step_idx, self.max_steps, self.agent.cause_of_death, self.scenario)
        m_color = COLOR_GOLD if survived else COLOR_RED
        t_surf = self.font_hero.render(m_title, True, m_color)
        self.canvas.blit(t_surf, (mx + (mw - t_surf.get_width()) // 2, my + 28))

        scen_str = self.custom_game.title if self.custom_game is not None else "Volcano Evacuation" if self.scenario == "volcano" else "Island Wilderness"
        dur_str = f"Endured {self.step_idx}/{self.max_steps} Steps ({self.step_idx * 2} Game Hours in {scen_str})"
        d_surf = self.font_sub.render(dur_str, True, COLOR_TEXT_MUTED)
        self.canvas.blit(d_surf, (mx + (mw - d_surf.get_width()) // 2, my + 74))

        box_rect = pygame.Rect(mx + 36, my + 106, mw - 72, 226)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box_rect, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box_rect, 1, border_radius=4)

        if self.mind_type == "quantum":
            engine_name, engine_col = "NumPy closed form; verified offline against Qiskit Aer", COLOR_PURPLE
        elif self.mind_type == "classical_mixture":
            engine_name, engine_col = "Classical Mixture Control (λ=1, Zero Coherence)", COLOR_CYAN
        else:
            engine_name, engine_col = "Classical Rule-Based Utility (Argmax)", COLOR_BLUE

        lines = [
            ("Decision Engine:", engine_name, engine_col),
            ("World Environment:", f"Seed #{self.seed} ({scen_str}, 40x40 Grid, 1600 Tiles)", COLOR_TEXT_MAIN),
            ("Final Stress & Noise:", f"{int(self.agent.stress*100)}% Stress  |  Decoherence: {int(decoherence_strength(self.agent.stress) * 100)}% off-diagonal decay (stress model)", COLOR_CYAN),
            ("Physiological State:", f"Hunger: {int(self.agent.needs['hunger']*100)}% | Thirst: {int(self.agent.needs['thirst']*100)}% | Warmth: {int(self.agent.needs['warmth']*100)}%", COLOR_TEXT_MAIN),
            ("Resource Harvest:", f"Gathered {self.agent.inventory.get('wood',0)} Timber | Consumed Rations | Crafted Tools: {self.agent.inventory.get('tools',0)}", COLOR_TEXT_MUTED)
        ]

        for i, (k, v, col) in enumerate(lines):
            ky = box_rect.y + 12 + i * 42
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
        self.btn_modal_report.check_hover(mouse_pos)
        self.btn_modal_scenario.check_hover(mouse_pos)
        self.btn_modal_home.check_hover(mouse_pos)
        self.btn_modal_close.check_hover(mouse_pos)

        self.btn_modal_replay.draw(self.canvas)
        self.btn_modal_switch.draw(self.canvas)
        self.btn_modal_report.draw(self.canvas)
        self.btn_modal_scenario.draw(self.canvas)
        self.btn_modal_home.draw(self.canvas)
        self.btn_modal_close.draw(self.canvas)

    # -------------------------------------------------------------------------
    # Render Full Action History Overlay (Tab / Log Key)
    # -------------------------------------------------------------------------
    def _report_title(self):
        return self.custom_game.title if self.custom_game is not None else None

    def _cached_report(self):
        """The report for this finished run, built once however many frames the debrief is open."""
        key = (id(self.engine), self.step_idx)
        if self._report_cache is None or self._report_cache[0] != key:
            report = build_report(self.scenario, self.engine, self.mind_type, self.seed, title=self._report_title(), horizon=self.max_steps)
            self._report_cache = (key, report)
        return self._report_cache[1]

    def export_report(self):
        """Writes the Excel workbook and the CSVs. Waits for the paired run on a thread, so the window keeps drawing."""
        if self.report_thread is not None and self.report_thread.is_alive():
            return
        report = dict(self._cached_report())
        name = report_name(self.scenario, self.seed, self.mind_type, self.engine)
        pending = self.paired.thread if self.custom_game is None else None
        out_dir = self.report_dir
        self.report_status = "Saving the report..."

        def work():
            if pending is not None:
                pending.join()
            report["Paired run"] = paired_rows(self.paired.value if pending is not None else None)
            try:
                workbook, folder = export_report(report, name, out_dir)
            except OSError as error:  # for example the workbook is open in Excel
                self.report_status = f"Report not saved: {error}"
                return
            self.report_status = f"Saved {os.path.basename(workbook)} and CSVs in {os.path.basename(str(out_dir))}/"

        self.report_thread = threading.Thread(target=work, daemon=True)
        self.report_thread.start()

    def _debrief_settings(self):
        if self.scenario == "titanic":
            return dict(event_mapping=self.titanic_mapping)
        return dict(self._scenario_settings()[1]) if self.scenario in CROWD_SCENARIOS else {}

    def _draw_debrief_summary(self, mx, my, mw, mh):
        """Survivors against deaths, the paired run on this seed, and the footer. Shared by every scenario."""
        lines = []
        if self.custom_game is None:
            self.paired.request(self.scenario, self.seed, self.mind_type, self._debrief_settings())
        if self.scenario in ACTION_NAMES:
            mine = crowd_line(self.scenario, self.engine)
            if mine["deaths"] is None:
                lines.append(f"Off the site: {mine['survivors']} of {mine['total']} ({mine['survivors'] / mine['total'] * 100:.0f}%).")
            else:
                lines.append(f"Survived: {mine['survivors']:,} of {mine['total']:,} ({mine['survivors'] / mine['total'] * 100:.1f}%). Died: {mine['deaths']:,}.")
            if self.custom_game is None:
                lines.append(paired_text(mine, self.paired.value))
        else:
            delay = first_hide(self.engine.steps)
            lines.append(f"This run: {'survived' if self.agent.is_alive else 'died'} at step {self.step_idx} of {self.max_steps}, "
                         + ("never hid." if delay is None else f"hid {delay} step{'' if delay == 1 else 's'} after the first sign."))
            if self.custom_game is None:
                lines.append(paired_text(None, self.paired.value))
            batch = saved_volcano_batch() if self.scenario == "volcano" else None
            if batch:
                lines.append(batch)
        lines += key_lines(self._cached_report())
        y = my + 372
        for line in lines:
            surface = self.font_small.render(line, True, COLOR_TEXT_MAIN)
            self.canvas.blit(surface, (mx + (mw - surface.get_width()) // 2, y))
            y += 22
        if self.report_status:
            status = self.font_small.render(self.report_status, True, COLOR_GREEN_DARK)
            self.canvas.blit(status, (mx + (mw - status.get_width()) // 2, my + mh - 122))
        footer = self.font_small.render(MODEL_FOOTER, True, COLOR_TEXT_HINT)
        self.canvas.blit(footer, (mx + (mw - footer.get_width()) // 2, my + mh - 24))

    def _draw_waterloo_debrief(self, mouse_pos, mx, my, mw, mh, border_col):
        focus, engine = self.agent, self.engine
        counts, table, timing = engine.counts(), engine.outcome_table(), engine.timing()
        title = f"{focus.label} LEFT THE SITE" if focus.status == "out" else f"{focus.label} IS STILL ON SITE"
        surf = self.font_hero.render(title, True, border_col)
        self.canvas.blit(surf, (mx + (mw - surf.get_width()) // 2, my + 22))
        sub = self.font_sub.render(f"This run: {counts['off_site']} of {len(engine.people)} off the site.  Mapping {engine.event_mapping}.  "
                                   f"Mind {self.mind_type}.  Seed #{self.seed}.", True, COLOR_TEXT_MUTED)
        self.canvas.blit(sub, (mx + (mw - sub.get_width()) // 2, my + 58))
        box = pygame.Rect(mx + 36, my + 84, mw - 72, 268)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box, 1, border_radius=4)
        head = self.font_mono.render(f"{'Role':26s}{'Off site':12s}{'AEGL-1':8s}{'AEGL-2':8s}{'AEGL-3':8s}", True, COLOR_TEXT_HINT)
        self.canvas.blit(head, (box.x + 22, box.y + 10))
        y = box.y + 32
        for role, row in table.items():
            levels = row["levels"]
            line = f"{role.capitalize():26s}{str(row['off_site']) + ' of ' + str(row['total']):12s}{levels['1']:<8d}{levels['2']:<8d}{levels['3']:<8d}"
            self.canvas.blit(self.font_mono.render(line, True, COLOR_TEXT_MAIN), (box.x + 22, y))
            y += 20
        def seconds(value):
            return "not reached" if value is None else f"{value} s"
        line = f"After the leak starts: first knew {seconds(timing['first_knew'])}, alarm {seconds(timing['alarm'])}, half off site {seconds(timing['half_off_site'])}"
        self.canvas.blit(self.font_small.render(line, True, COLOR_TEXT_MUTED), (box.x + 22, y + 8))
        self.canvas.blit(self.font_small.render("AEGL columns count people whose highest level was that one. EPA planning limits, not predictions of injury.",
                                                True, COLOR_TEXT_HINT), (box.x + 22, y + 34))
        self.canvas.blit(self.font_small.render("A hypothetical at a real site, not a reconstruction. The real head-count, leak and injuries are unknown; see docs/WATERLOO_SOURCES.md.",
                                                True, COLOR_TEXT_HINT), (box.x + 22, y + 54))
        for button in (self.btn_modal_replay, self.btn_modal_switch, self.btn_modal_report, self.btn_modal_scenario, self.btn_modal_home):
            button.check_hover(mouse_pos)
            button.draw(self.canvas)
        self.btn_modal_close.check_hover(mouse_pos)
        self.btn_modal_close.draw(self.canvas)

    def _draw_pompeii_debrief(self, mouse_pos, mx, my, mw, mh, border_col):
        focus, engine = self.agent, self.engine
        counts, table, deaths = engine.counts(), engine.outcome_table(), engine.death_breakdown()
        title = f"{focus.label} SURVIVED" if focus.is_alive else f"{focus.label} DIED ({str(focus.cause_of_death).upper()})"
        surf = self.font_hero.render(title, True, border_col)
        self.canvas.blit(surf, (mx + (mw - surf.get_width()) // 2, my + 22))
        sub = self.font_sub.render(f"This run: {counts['dead']:,} deaths of {len(engine.people):,}.  Mapping {engine.event_mapping}.  "
                                   f"Mind {self.mind_type}.  Seed #{self.seed}.", True, COLOR_TEXT_MUTED)
        self.canvas.blit(sub, (mx + (mw - sub.get_width()) // 2, my + 58))
        box = pygame.Rect(mx + 36, my + 84, mw - 72, 268)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box, 1, border_radius=4)
        head = self.font_mono.render(f"{'Role':24s}{'Survived':16s}", True, COLOR_TEXT_HINT)
        self.canvas.blit(head, (box.x + 22, box.y + 10))
        y = box.y + 32
        for role, row in table.items():
            line = f"{role.replace('_', ' ').capitalize():24s}{str(row['survived']) + ' of ' + str(row['total']):16s}"
            self.canvas.blit(self.font_mono.render(line, True, COLOR_TEXT_MAIN), (box.x + 22, y))
            y += 20
        causes = deaths["causes"]
        line = f"Roof collapse {causes.get('roof_collapse', 0):,}   Pyroclastic flow {causes.get('pyroclastic_flow', 0):,}"
        self.canvas.blit(self.font_mono.render(line, True, COLOR_TEXT_MUTED), (box.x + 22, y + 6))
        self.canvas.blit(self.font_small.render("History: about 1,150 bodies found on site, 38% of known victims in the pumice phase. Not a total death toll.",
                                                True, COLOR_TEXT_HINT), (box.x + 22, y + 32))
        self.canvas.blit(self.font_small.render("A demonstration, not a reconstruction. The default settings overstate escape; see docs/POMPEII_SOURCES.md.",
                                                True, COLOR_TEXT_HINT), (box.x + 22, y + 52))
        for button in (self.btn_modal_replay, self.btn_modal_switch, self.btn_modal_report, self.btn_modal_scenario, self.btn_modal_home):
            button.check_hover(mouse_pos)
            button.draw(self.canvas)
        self.btn_modal_close.check_hover(mouse_pos)
        self.btn_modal_close.draw(self.canvas)

    def _draw_titanic_debrief(self, mouse_pos, mx, my, mw, mh, border_col):
        focus, table = self.agent, self.engine.outcome_table()
        counts = self.engine.counts()
        saved = counts["boats"]
        title = (f"{focus.label} SURVIVED" if focus.is_alive else f"{focus.label} DIED ({str(focus.cause_of_death).upper()})")
        surf = self.font_hero.render(title, True, border_col)
        self.canvas.blit(surf, (mx + (mw - surf.get_width()) // 2, my + 26))
        sub = self.font_sub.render(f"This run: {saved:,} of {len(self.engine.people):,} survived.  History: about 712 of 2,208.",
                                   True, COLOR_TEXT_MUTED)
        self.canvas.blit(sub, (mx + (mw - sub.get_width()) // 2, my + 66))
        box = pygame.Rect(mx + 36, my + 100, mw - 72, 245)
        pygame.draw.rect(self.canvas, COLOR_PANEL_ALT, box, border_radius=4)
        pygame.draw.rect(self.canvas, COLOR_CARD_BORDER, box, 1, border_radius=4)
        names = [("first", "First-class passengers", 324, 201), ("second", "Second-class passengers", 284, 118),
                 ("third", "Third-class passengers", 709, 181)]
        crew_keys = ("captain", "officer", "evac_worker", "server", "engine_worker")
        crew_aboard = sum(table[k]["aboard"] for k in crew_keys)
        crew_saved = sum(table[k]["saved"] for k in crew_keys)
        rows = [(label, table[k]["saved"], table[k]["aboard"], past) for k, label, _, past in names]
        rows.append(("Crew", crew_saved, crew_aboard, 212))
        head = self.font_mono.render(f"{'Group':30s}{'This run':14s}{'History':14s}", True, COLOR_TEXT_HINT)
        self.canvas.blit(head, (box.x + 22, box.y + 14))
        for i, (label, s, aboard, past) in enumerate(rows):
            line = f"{label:30s}{f'{s} of {aboard}':14s}{f'{past} of {aboard}':14s}"
            self.canvas.blit(self.font_mono.render(line, True, COLOR_TEXT_MAIN), (box.x + 22, box.y + 46 + i * 30))
        boats = self.engine.boats
        used = sum(len(b.aboard) for b in boats.boats + boats.floating)
        note = f"Lifeboat seats used: {used:,} of {TOTAL_SEATS:,}.  Mind: {self.mind_type}.  Seed #{self.seed}."
        self.canvas.blit(self.font_mono.render(note, True, COLOR_TEXT_MUTED), (box.x + 22, box.y + 180))
        hint = "A compressed demonstration, not a reconstruction. Compare Mind reruns this night with another mind."
        self.canvas.blit(self.font_small.render(hint, True, COLOR_TEXT_HINT), (box.x + 22, box.y + 212))
        for button in (self.btn_modal_replay, self.btn_modal_switch, self.btn_modal_report, self.btn_modal_scenario, self.btn_modal_home):
            button.check_hover(mouse_pos)
            button.draw(self.canvas)
        self.btn_modal_close.check_hover(mouse_pos)
        self.btn_modal_close.draw(self.canvas)

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
    # UI Utility Helpers - Clash of Clans / Hay Day Carved Wood & Parchment Style
    # -------------------------------------------------------------------------
    def draw_card(self, x: int, y: int, w: int, h: int, border_color: Optional[Tuple[int, int, int]] = None, border_width: int = 2):
        self.canvas.cover(pygame.Rect(x, y, w, h))
        # 1. Warm drop shadow
        pygame.draw.rect(self.canvas, (38, 22, 10), (x + 2, y + 4, w, h), border_radius=12)
        # 2. Outer carved oak border & golden inner trim
        outer_col = border_color or COLOR_CARD_BORDER
        pygame.draw.rect(self.canvas, outer_col, (x, y, w, h), border_radius=12)
        pygame.draw.rect(self.canvas, (232, 184, 72), (x + 3, y + 3, w - 6, h - 6), border_radius=10)
        # 3. Sunlit cream parchment interior
        pygame.draw.rect(self.canvas, COLOR_PANEL_BG, (x + 5, y + 5, w - 10, h - 10), border_radius=8)
        # 4. Corner brass rivets
        for rx_c, ry_c in ((x + 10, y + 10), (x + w - 10, y + 10), (x + 10, y + h - 10), (x + w - 10, y + h - 10)):
            pygame.draw.circle(self.canvas, (124, 76, 30), (rx_c, ry_c), 3)
            pygame.draw.circle(self.canvas, (244, 198, 76), (rx_c - 1, ry_c - 1), 2)

    def draw_pill_tag(self, x: int, y: int, text: str, color: Tuple[int, int, int]) -> int:
        txt_surf = self.font_small.render(text, True, (255, 250, 240))
        pw = txt_surf.get_width() + 20
        ph = 26
        pill_rect = pygame.Rect(x, y, pw, ph)
        pygame.draw.rect(self.canvas, color, pill_rect, border_radius=13)
        pygame.draw.rect(self.canvas, (72, 42, 18), pill_rect, 2, border_radius=13)
        self.canvas.blit(txt_surf, (x + 10, y + (ph - txt_surf.get_height()) // 2))
        return pw

    def draw_badge(self, x: int, y: int, text: str, color: Tuple[int, int, int]):
        txt_surf = self.font_sub.render(text, True, (255, 252, 242))
        bg_rect = pygame.Rect(x, y, txt_surf.get_width() + 18, txt_surf.get_height() + 8)
        pygame.draw.rect(self.canvas, (68, 40, 18), (bg_rect.x, bg_rect.y + 2, bg_rect.width, bg_rect.height), border_radius=7)
        pygame.draw.rect(self.canvas, color, bg_rect, border_radius=7)
        pygame.draw.rect(self.canvas, (255, 232, 168), bg_rect, 1, border_radius=7)
        self.canvas.blit(txt_surf, (x + 9, y + 4))

    def draw_progress_bar(self, x: int, y: int, w: int, h: int, label: str, value: float, color: Tuple[int, int, int]):
        lbl_surf = self.font_mono.render(f"{label:11s}", True, COLOR_TEXT_MAIN)
        self.canvas.blit(lbl_surf, (x, y))

        bar_x = x + 95
        bar_w = w - 145
        track_rect = pygame.Rect(bar_x, y + 2, bar_w, h - 2)
        # Carved dark wood trough with gold rim
        pygame.draw.rect(self.canvas, (68, 42, 22), track_rect, border_radius=6)
        pygame.draw.rect(self.canvas, (148, 98, 44), track_rect, 1, border_radius=6)

        fill_w = max(0, min(bar_w - 2, int((bar_w - 2) * value)))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x + 1, y + 3, fill_w, h - 4)
            pygame.draw.rect(self.canvas, color, fill_rect, border_radius=5)
            # Supercell glossy top highlight strip
            gloss_rect = pygame.Rect(bar_x + 2, y + 4, max(1, fill_w - 2), max(2, (h - 4) // 2))
            gloss_s = pygame.Surface((gloss_rect.width, gloss_rect.height), pygame.SRCALPHA)
            gloss_s.fill((255, 255, 255, 95))
            self.canvas.blit(gloss_s, (gloss_rect.x, gloss_rect.y))

        val_surf = self.font_mono.render(f"{int(value * 100):3d}%", True, COLOR_TEXT_MAIN)
        self.canvas.blit(val_surf, (bar_x + bar_w + 8, y))


def launch_gui(seed: int = 101, mind: str = "quantum", noise: str = "stub", start_screen: str = "event_choice",
               scenario: str = "volcano", builder_factory=None, open_sim=None):
    """Launches the complete Pygame Quantum Cognition Simulation starting at the Event Choice Screen."""
    app = IslandVisualizerApp(seed=seed, mind_type=mind, noise_source=noise, start_screen=start_screen,
                              scenario=scenario, builder_factory=builder_factory)
    if open_sim:
        app.open_sim(open_sim)
    app.run()

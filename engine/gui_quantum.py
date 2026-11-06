"""The quantum panel: the paper's claims as pictures, in place of a paragraph of text.

    timeline   quantum against control P(protect) on this seed
    bloch      the belief's path in the x-z plane, with a |x| coherence bar
    order swap swaps the last two cues and shows the change in P(protect)
    dial       stress mapped to dephasing

Numbers come from the mind, never from this file. The control line is the mixture mind
evaluated on the same state at each step, so the two lines share one world.
"""
import math

import pygame

try:
    from mind.quantum_mind import _decide, classical_mixture_decide, quantum_decide
except ImportError:
    _decide = classical_mixture_decide = quantum_decide = None

INK = (54, 32, 14)
MUTED = (78, 48, 20)
TRACK = (234, 216, 178)
FRAME = (106, 64, 28)
QUANTUM = (146, 58, 196)
CONTROL = (16, 108, 160)
DANGER = (190, 40, 30)
HISTORY_LIMIT = 200
MAX_RENDERED_PATH = 24


def swap_last_two(events):
    """The events with the last two real cues swapped, or None if there are fewer than two."""
    cues = [i for i, event in enumerate(events) if event != "none"]
    if len(cues) < 2:
        return None
    swapped = list(events)
    swapped[cues[-1]], swapped[cues[-2]] = swapped[cues[-2]], swapped[cues[-1]]
    return swapped


def order_swap_delta(state):
    """(swapped events, P(protect) after the swap minus before), or None if there is nothing to swap."""
    swapped = swap_last_two(state["recent_events"])
    if swapped is None or swapped == list(state["recent_events"]):
        return None
    before = quantum_decide(state)["quantum"]["p_protect"]
    after = quantum_decide(dict(state, recent_events=swapped))["quantum"]["p_protect"]
    return swapped, after - before


class QuantumPanel:
    def __init__(self):
        self.reset()

    def reset(self):
        self.series = []  # (p_quantum, p_control)
        self.path = []  # (x, z) belief points
        self.lam = 0.0
        self.stress = 0.0
        self.coherence = 0.0
        self.state = None
        self.swap_result = None

    def record(self, state):
        """Evaluate both minds on this step's state."""
        if quantum_decide is None or state is None:
            return
        quantum = quantum_decide(state)["quantum"]
        control = classical_mixture_decide(state)["quantum"]
        self.series = (self.series + [(quantum["p_protect"], control["p_protect"])])[-HISTORY_LIMIT:]
        x, _y, z = quantum["bloch"]
        self.path = (self.path + [(x, z)])[-HISTORY_LIMIT:]
        self.lam, self.stress, self.coherence = quantum["lam"], state["stress"], quantum["coherence"]
        self.state = state
        self.swap_result = None

    def swap(self):
        """The order-swap button. Reports what it did, including when there is nothing to swap."""
        if self.state is None:
            self.swap_result = "No cues yet"
            return self.swap_result
        result = order_swap_delta(self.state)
        if result is None:
            self.swap_result = "Needs two different cues"
            return self.swap_result
        swapped, delta = result
        cues = [e.replace("_", " ") for e in swapped if e != "none"][-2:]
        self.swap_result = f"{cues[0]} > {cues[1]}: ΔP {delta:+.3f}"
        return self.swap_result

    # -- drawing, in logical units ---------------------------------------------

    def draw_timeline(self, surface, rect, font):
        pygame.draw.rect(surface, TRACK, rect, border_radius=4)
        pygame.draw.rect(surface, FRAME, rect, 1, border_radius=4)
        surface.blit(font.render("P(protect): quantum against control", True, INK), (rect.x + 8, rect.y + 5))
        plot = pygame.Rect(rect.x + 10, rect.y + 28, rect.width - 20, rect.height - 54)
        pygame.draw.line(surface, FRAME, plot.bottomleft, plot.bottomright)
        pygame.draw.line(surface, FRAME, (plot.left, plot.centery), (plot.right, plot.centery))
        if len(self.series) >= 2:
            steps = len(self.series) - 1
            for index, color in ((1, CONTROL), (0, QUANTUM)):
                points = [(plot.left + plot.width * i / steps, plot.bottom - plot.height * row[index]) for i, row in enumerate(self.series)]
                pygame.draw.lines(surface, color, False, points, 3 if index == 0 else 2)
        pygame.draw.line(surface, QUANTUM, (rect.x + 10, rect.bottom - 13), (rect.x + 34, rect.bottom - 13), 3)
        surface.blit(font.render("quantum", True, INK), (rect.x + 40, rect.bottom - 22))
        pygame.draw.line(surface, CONTROL, (rect.x + 120, rect.bottom - 13), (rect.x + 144, rect.bottom - 13), 2)
        surface.blit(font.render("control", True, INK), (rect.x + 150, rect.bottom - 22))

    def draw_bloch(self, surface, rect, font):
        pygame.draw.rect(surface, TRACK, rect, border_radius=4)
        pygame.draw.rect(surface, FRAME, rect, 1, border_radius=4)
        surface.blit(font.render("Belief, x-z", True, INK), (rect.x + 8, rect.y + 5))
        radius = min(rect.width // 2 - 14, (rect.height - 54) // 2)
        center = (rect.centerx, rect.y + 28 + radius)
        pygame.draw.circle(surface, (250, 239, 212), center, radius)
        pygame.draw.circle(surface, FRAME, center, radius, 1)
        pygame.draw.line(surface, FRAME, (center[0] - radius, center[1]), (center[0] + radius, center[1]))
        pygame.draw.line(surface, FRAME, (center[0], center[1] - radius), (center[0], center[1] + radius))
        points = [(center[0] + x * radius, center[1] - z * radius) for x, z in self.path[-MAX_RENDERED_PATH:]]
        if len(points) >= 2:
            pygame.draw.lines(surface, QUANTUM, False, points, 2)
        if points:
            pygame.draw.circle(surface, DANGER, (round(points[-1][0]), round(points[-1][1])), 4)
        bar = pygame.Rect(rect.x + 10, rect.bottom - 20, rect.width - 58, 10)
        pygame.draw.rect(surface, (68, 42, 22), bar, border_radius=4)
        pygame.draw.rect(surface, QUANTUM, (bar.x, bar.y, round(bar.width * min(1.0, self.coherence)), bar.height), border_radius=4)
        surface.blit(font.render(f"|x| {self.coherence:.2f}", True, INK), (bar.right + 4, bar.y - 4))

    def draw_dial(self, surface, rect, font):
        pygame.draw.rect(surface, TRACK, rect, border_radius=4)
        pygame.draw.rect(surface, FRAME, rect, 1, border_radius=4)
        surface.blit(font.render("Stress to λ", True, INK), (rect.x + 8, rect.y + 5))
        radius = rect.width // 2 - 22
        center = (rect.centerx, rect.y + 34 + radius)
        steps = 24
        points = [(center[0] - radius * math.cos(math.pi * i / steps), center[1] - radius * math.sin(math.pi * i / steps)) for i in range(steps + 1)]
        pygame.draw.lines(surface, FRAME, False, points, 7)
        filled = max(2, round(steps * min(1.0, self.lam)) + 1)
        pygame.draw.lines(surface, QUANTUM, False, points[:filled], 7)
        angle = math.pi * min(1.0, self.lam)
        tip = (center[0] - (radius - 8) * math.cos(angle), center[1] - (radius - 8) * math.sin(angle))
        pygame.draw.line(surface, INK, center, tip, 3)
        pygame.draw.circle(surface, INK, center, 4)
        text = font.render(f"stress {self.stress:.2f}  λ {self.lam:.2f}", True, INK)
        surface.blit(text, (rect.centerx - text.get_width() // 2, center[1] + 8))
